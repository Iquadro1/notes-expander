"""Lint a lesson Markdown file without rendering (mechanical checks only).

    uv run lint-md output/<course>/01.md [--fix] [--strict]

Runs the same validators render-html runs — lesson header, ambiguous ***,
shortcode file resolution, box syntax + ink placement — and reports them
without writing HTML. --fix rewrites the file with render-html's blank-line
normalization (safe: whitespace around shortcodes/lists only).

Escaping of prose `_` and math tokenization stay render-html's job at build
time; this tool tells the author what would warn before paying for a render.
"""

from __future__ import annotations

import argparse
import io
from contextlib import redirect_stdout
from pathlib import Path

import src.render as render


def main() -> None:
    parser = argparse.ArgumentParser(description="Lint lesson Markdown (no HTML written)")
    parser.add_argument("input_file", help="Markdown file to lint")
    parser.add_argument("--course", default=None, help="Course slug (default: ACTIVE_COURSE)")
    parser.add_argument("--fix", action="store_true",
                        help="Rewrite file with blank-line normalization")
    parser.add_argument("--strict", action="store_true",
                        help="Exit 1 when any WARNING is emitted")
    args = parser.parse_args()

    render.configure(args.course)
    path = Path(args.input_file)
    md_text = path.read_text(encoding="utf-8")

    if args.fix:
        fixed = render.normalize_markdown(md_text)
        if fixed != md_text:
            path.write_text(fixed, encoding="utf-8")
            print(f"Normalized blank lines in {path}")
            md_text = fixed
        else:
            print("Blank lines already normalized.")

    buf = io.StringIO()
    render.reset_warnings()
    with redirect_stdout(buf):
        render.check_lesson_header(md_text, render.COURSE_TITLE)
        # Full shortcode + box + ink validation (uses the render-html
        # asset cache, so it is fast after the first render).
        render.parse_markdown(md_text)
    out = buf.getvalue().strip()
    if out:
        print(out)
    if render.WARNING_COUNT:
        print(f"{render.WARNING_COUNT} warning(s).")
        if args.strict:
            raise SystemExit(1)
    else:
        print(f"OK: {path} passes all checks.")


if __name__ == "__main__":
    main()
