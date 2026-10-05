"""Archive transcribed sources raw_notes/ → processed_notes/ with guards.

    uv run archive-lesson 01.pdf [--course <slug>] [--html output/<slug>/01.html] [--force]

Guards (skip with --force):
- The matching HTML exists (inferred from the source stem unless --html).
- The HTML is newer than templates/layout.html and src/render.py (no stale build).
- The HTML contains no `data-kind="missing"` markers (all files resolved).

Safe after rendering: render-html resolves sources across both inbox and
archive, so future re-renders still find moved files.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import src.render as render

TEMPLATE = Path("templates/layout.html")
RENDER_SRC = Path("src/render.py")


def html_for_source(out_dir: Path, stem: str) -> Path:
    return out_dir / f"{stem}.html"


def main() -> None:
    parser = argparse.ArgumentParser(description="Archive raw notes after rendering")
    parser.add_argument("names", nargs="+", help="Files to move from raw_notes/")
    parser.add_argument("--course", default=None, help="Course slug (default: ACTIVE_COURSE)")
    parser.add_argument("--html", default=None, help="Rendered HTML guard (default: inferred)")
    parser.add_argument("--force", action="store_true", help="Move even if guards fail")
    args = parser.parse_args()

    slug = render.resolve_course(args.course)
    course_dir = render.COURSES_DIR / slug
    inbox, archive = course_dir / "raw_notes", course_dir / "processed_notes"
    out_dir = render.OUTPUT_ROOT / slug

    problems: list[str] = []
    html = Path(args.html) if args.html else None
    if html is None:
        # Infer from first source stem (01.pdf -> 01.html); require explicit
        # --html when archiving several lessons at once.
        stem = Path(args.names[0]).stem
        html = html_for_source(out_dir, stem)

    if not html.is_file():
        problems.append(f"HTML {html} missing — render first.")
    else:
        for dep in (TEMPLATE, RENDER_SRC):
            if dep.is_file() and html.stat().st_mtime < dep.stat().st_mtime:
                problems.append(f"HTML older than {dep} — re-render (stale build).")
        text = html.read_text(encoding="utf-8", errors="replace")
        missing = sorted(set(re.findall(r'data-kind="missing"[^>]*data-title="([^"]+)"', text)
                               + re.findall(r'data-title="([^"]+)"[^>]*data-kind="missing"', text)))
        if missing or 'data-kind="missing"' in text:
            problems.append(f"HTML has missing-file markers{f': {missing}' if missing else ''}.")

    moves: list[tuple[Path, Path]] = []
    for name in args.names:
        src = inbox / Path(name).name
        dst = archive / Path(name).name
        if not src.is_file():
            already = archive / Path(name).name
            if already.is_file():
                print(f"Skip {name}: already in processed_notes/.")
                continue
            problems.append(f"{src} not found in inbox.")
            continue
        moves.append((src, dst))

    if problems and not args.force:
        print("Refusing to archive:")
        for p in problems:
            print(f"  - {p}")
        raise SystemExit(1)
    if problems:
        print("WARNING: --force overrides:")
        for p in problems:
            print(f"  - {p}")

    archive.mkdir(parents=True, exist_ok=True)
    for src, dst in moves:
        src.rename(dst)
        print(f"Archived {src} -> {dst}")
    print("Done. Re-renders still resolve moved files via processed_notes/.")


if __name__ == "__main__":
    main()
