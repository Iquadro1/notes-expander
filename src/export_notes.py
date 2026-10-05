"""Export raw_note scans to viewable PNGs (Step 1 helper).

Replaces the copy-pasted `python -c "import pymupdf..."` one-liner with a
course-aware CLI:

    uv run export-notes [--course <slug>] [--out-dir /tmp/opencode] [name ...]

- Lists images directly (viewable as-is).
- Rasterizes PDFs page by page at 2x into <out-dir>/<stem>/page-N.png.
- Prints page counts and output paths for the agent to view.

Never touches output/<course>/assets (that's render-html's cache).
"""

from __future__ import annotations

import argparse
from pathlib import Path

import src.render as render

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}

RASTER_ZOOM = 2.0


def export_pdf(pdf_path: Path, out_dir: Path) -> list[Path]:
    import pymupdf

    stem = pdf_path.stem
    dest = out_dir / stem
    dest.mkdir(parents=True, exist_ok=True)
    made: list[Path] = []
    with pymupdf.open(pdf_path) as doc:
        matrix = pymupdf.Matrix(RASTER_ZOOM, RASTER_ZOOM)
        for i, page in enumerate(doc):
            out = dest / f"page-{i + 1}.png"
            # Re-export when source is newer (cheap cache like render.py).
            if out.exists() and out.stat().st_mtime >= pdf_path.stat().st_mtime:
                made.append(out)
                continue
            page.get_pixmap(matrix=matrix, alpha=False).save(out)
            made.append(out)
        print(f"{pdf_path.name}: {doc.page_count} page(s)")
    for p in made:
        print(f"  {p}")
    return made


def main() -> None:
    parser = argparse.ArgumentParser(description="Export raw scans to viewable PNGs")
    parser.add_argument("names", nargs="*", help="Specific files in raw_notes (default: all)")
    parser.add_argument("--course", default=None, help="Course slug (default: ACTIVE_COURSE)")
    parser.add_argument("--out-dir", default="/tmp/opencode",
                        help="Where to write PNGs (default: /tmp/opencode)")
    parser.add_argument("--list", action="store_true", help="Only list inbox contents")
    args = parser.parse_args()

    slug = render.resolve_course(args.course)
    inbox = render.COURSES_DIR / slug / "raw_notes"
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not inbox.is_dir():
        raise SystemExit(f"ERROR: inbox {inbox} does not exist.")

    files = sorted(p for p in inbox.iterdir() if p.is_file())
    if args.names:
        wanted = set(args.names)
        files = [p for p in files if p.name in wanted]
        missing = wanted - {p.name for p in files}
        if missing:
            print(f"WARNING: not in {inbox}: {', '.join(sorted(missing))}")

    if not files:
        print("No new notes to process.")
        return

    for path in files:
        ext = path.suffix.lower()
        if args.list:
            print(f"{path.name} ({path.stat().st_size} bytes)")
        elif ext == ".pdf":
            export_pdf(path, out_dir)
        elif ext in IMAGE_EXTS:
            print(f"{path.name}: image, view directly at {path}")
        else:
            print(f"{path.name}: unsupported extension {ext!r} (expected PDF or image)")


if __name__ == "__main__":
    main()
