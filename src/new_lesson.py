"""Scaffold a new lesson Markdown file with the strict header (Step 3 helper).

    uv run new-lesson --lesson 2 --from 01.pdf
    uv run new-lesson --lesson 2 --from 2026-10-04_topologia.jpg --from 2026-10-05.jpg --lang it
    uv run new-lesson --name lezione-2 --lesson 2 --from notes.pdf --force

The *mapping* (date-named photo → lesson number, language) stays an LLM
decision — filenames may be NN.pdf today and date.jpg tomorrow, so this tool
takes the source filename(s) verbatim via --from and only templates the
mechanical header:

    [source: <first>  (#page=1 for PDFs)]
    # <course.txt line 1>
    ## Lezione N  (localized subtitle)

Output stays lesson-ordered (output/<slug>/NN.md) even when sources are
date-named; only the [source:] target uses the real filename.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import src.render as render

SUBTITLES = {
    "it": "Lezione",
    "en": "Lesson",
    "fr": "Leçon",
    "es": "Lección",
    "de": "Lektion",
}


def subtitle(lang: str, n: int) -> str:
    return f"## {SUBTITLES.get(lang.lower(), 'Lesson')} {n}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Scaffold a lesson Markdown file")
    parser.add_argument("--lesson", type=int, required=True, help="Lesson number")
    parser.add_argument("--from", dest="sources", action="append", default=[],
                        help="Source file in raw_notes/processed_notes (repeatable)")
    parser.add_argument("--name", default=None,
                        help="Output stem (default: zero-padded lesson, e.g. 02)")
    parser.add_argument("--lang", default="it", help="Subtitle language code (default: it)")
    parser.add_argument("--course", default=None, help="Course slug (default: ACTIVE_COURSE)")
    parser.add_argument("--force", action="store_true", help="Overwrite existing file")
    args = parser.parse_args()

    slug = render.configure(args.course)
    if render.COURSE_TITLE is None:
        raise SystemExit(f"ERROR: {render.COURSES_DIR / slug / 'course.txt'} missing — "
                         "create it with the course display name first.")

    stem = args.name or f"{args.lesson:02d}"
    out = render.OUTPUT_ROOT / slug / f"{stem}.md"
    if out.exists() and not args.force:
        raise SystemExit(f"ERROR: {out} exists (pass --force to overwrite).")

    # Validate --from files resolve like render-html would (warn, don't fail:
    # the scan may arrive after scaffolding).
    tags: list[str] = []
    for src in args.sources:
        found = render.resolve_file(src, render.SOURCE_DIRS)
        if found is None:
            print(f"WARNING: source {src!r} not in raw_notes/processed_notes yet — "
                  "tag kept, render-html will flag it until the file arrives.")
        frag = "#page=1" if src.lower().endswith(".pdf") else ""
        tags.append(f"[source: {src}{frag}]" if frag else f"[source: {src}]")

    lines = []
    if tags:
        lines.append(tags[0])
        lines.append("")
    lines.append(f"# {render.COURSE_TITLE}")
    lines.append(subtitle(args.lang, args.lesson))
    lines.append("")
    if len(tags) > 1:
        lines.append("")
        lines.append(tags[1] if len(tags) > 1 else "")
        lines.append("")
    lines.append("## ")
    lines.append("")

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Created {out} (course: {slug})")
    if args.sources:
        print(f"Sources: {', '.join(args.sources)} — add one [source:] tag per section, "
              "with #page + &box per the box convention.")


if __name__ == "__main__":
    main()
