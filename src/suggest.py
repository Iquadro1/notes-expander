"""Suggest highlight-box edges from the ink profile (Step 1/3 helper).

    uv run suggest-boxes 01.pdf --page 1 [--course <slug>] [--bins 60]

Deterministic replacement for the throwaway per-lesson scripts that counted
dark pixels per row (previously /tmp bands.json / bandview-*.png). Uses the
same ink definition as render-html's validator (src/render.py `_is_ink`),
so suggested edges pass `check_box_ink` instead of tripping it:

- Loads the rasterized page from output/<course>/assets (rendering it first
  if missing, via the render-html cache).
- Computes per-row ink fraction, finds blank gaps (ink < threshold).
- Prints an ASCII ink map + gap list with midpoints in 0..1 coordinates.

The LLM still decides the *semantic* split (which lines = one theorem);
this tool reports *where the blank gaps are* so box top/bottom edges land
in them. Convention enforced downstream: full-width boxes (x=0, w=1).
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import src.render as render


def load_page_png(source: str, page: int) -> tuple[Path, object]:
    """Resolve `source` like render-html, ensure its page PNG exists, load it."""
    import pymupdf

    path = render.resolve_file(source, render.SOURCE_DIRS)
    if path is None:
        searched = ", ".join(str(d) for d in render.SOURCE_DIRS)
        raise SystemExit(f"ERROR: [{source}] not found (searched: {searched})")
    if path.suffix.lower() in render.IMAGE_EXTENSIONS:
        pix = pymupdf.Pixmap(path)
        return path, pix
    if path.suffix.lower() != ".pdf":
        raise SystemExit(f"ERROR: {source} is neither image nor PDF.")
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", path.stem).strip("._") or "document"
    asset_dir = render.ASSETS_DIR / stem
    png = asset_dir / f"page-{page}.png"
    if not png.is_file():
        # Rasterize through the render-html cache (also validates page range).
        render.export_pdf_pages(path, [page])
    if not png.is_file():
        raise SystemExit(f"ERROR: page {page} of {source} could not be rasterized.")
    return png, pymupdf.Pixmap(png)


def row_ink_profile(pix, step: int = 2) -> tuple[list[float], int, int]:
    """Fraction of ink pixels per image row (0..1)."""
    W, H, s, n = pix.width, pix.height, pix.samples, pix.n
    profile: list[float] = []
    for row in range(0, H, step):
        base = row * W * n
        ink = 0
        total = 0
        for col in range(0, W, step):
            total += 1
            if render._is_ink(s[base + col * n], s[base + col * n + 1], s[base + col * n + 2]):
                ink += 1
        profile.append(ink / max(1, total))
    return profile, W, H


def find_gaps(profile: list[float], thresh: float, min_rows: int = 2) -> list[tuple[int, int]]:
    """Runs of sampled rows with ink < thresh (in sampled-row units)."""
    gaps: list[tuple[int, int]] = []
    start: int | None = None
    for i, v in enumerate(profile):
        if v < thresh:
            if start is None:
                start = i
        elif start is not None:
            if i - start >= min_rows:
                gaps.append((start, i - 1))
            start = None
    if start is not None and len(profile) - start >= min_rows:
        gaps.append((start, len(profile) - 1))
    return gaps


def main() -> None:
    parser = argparse.ArgumentParser(description="Suggest box edges from ink gaps")
    parser.add_argument("source", help="Scan file, e.g. 01.pdf or photo.jpg")
    parser.add_argument("--page", type=int, default=1, help="1-based page (PDFs)")
    parser.add_argument("--course", default=None, help="Course slug (default: ACTIVE_COURSE)")
    parser.add_argument("--bins", type=int, default=60, help="ASCII map rows (default: 60)")
    parser.add_argument("--threshold", type=float, default=0.04,
                        help="Max ink fraction for a blank row (default: 0.04)")
    args = parser.parse_args()

    render.configure(args.course)
    png, pix = load_page_png(args.source, args.page)
    profile, W, H = row_ink_profile(pix, step=render.INK_STEP)
    gaps = find_gaps(profile, thresh=args.threshold)
    n = len(profile)

    def y_of(sample_row: int) -> float:
        return round((sample_row * render.INK_STEP) / H, 4)

    print(f"Page image: {png} ({W}x{H})")
    print(f"Ink rows: {sum(1 for v in profile if v >= args.threshold)}/{n} "
          f"(threshold {args.threshold})")

    # ASCII map: '#' = ink band, '.' = blank gap.
    stride = max(1, n // args.bins)
    print("Map (top→bottom, #=ink, .=gap):")
    for i in range(0, n, stride):
        chunk = profile[i:i + stride]
        ink = sum(1 for v in chunk if v >= args.threshold)
        bar = "#" * round(40 * ink / max(1, len(chunk)))
        print(f"  y={y_of(i):.3f} {'.' if not bar else bar}")

    print("Gaps (blank y-ranges, edge midpoints for box= coordinates):")
    if not gaps:
        print("  (none — page looks dense; omit box or split by content)")
    for a, b in gaps:
        top, bot = y_of(a), y_of(min(b + 1, n - 1))
        mid = round((top + bot) / 2, 4)
        print(f"  y {top:.4f}..{bot:.4f}  mid {mid:.4f}")
    print("Tip: neighboring sections share a gap — one's bottom edge and the")
    print("next one's top edge both sit inside it. Full-width: box=0,<top>,1,<h>.")


if __name__ == "__main__":
    main()
