"""Keep Plan.md embedded code in sync with the real files.

    uv run sync-docs [--check]

Single source of truth: src/extract.py, src/search.py, src/render.py and
templates/layout.html.
Plan.md embeds copies under "### 2./3./4." (```python fences)
and "### 5. Layout Template" (```html fence); this tool replaces those fences
with the current file contents. --check exits 1 when Plan.md is stale
instead of rewriting (for CI).
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

PLAN = Path("Plan.md")
EXTRACT = Path("src/extract.py")
SEARCH = Path("src/search.py")
RENDER = Path("src/render.py")
LAYOUT = Path("templates/layout.html")

ANCHOR_EXTRACT = "### 2. Knowledge Base Extraction"
ANCHOR_SEARCH = "### 3. Local Search Utility"
ANCHOR_RENDER = "### 4. Markdown Rendering UI"
ANCHOR_LAYOUT = "### 5. Layout Template"


def replace_fence(text: str, anchor: str, lang: str, body: str) -> str:
    start = text.index(anchor)
    fence_open = text.index(f"```{lang}", start)
    fence_close = text.index("```", fence_open + len(f"```{lang}"))
    # Keep the language tag line, swap the body; ensure trailing newline.
    body = body.rstrip() + "\n"
    return text[:fence_open + len(f"```{lang}\n")] + body + text[fence_close:]


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync Plan.md code with src files")
    parser.add_argument("--check", action="store_true",
                        help="Exit 1 if Plan.md differs (no rewrite)")
    args = parser.parse_args()

    plan = PLAN.read_text(encoding="utf-8")

    updated = replace_fence(plan, ANCHOR_EXTRACT, "python",
                            EXTRACT.read_text(encoding="utf-8"))
    updated = replace_fence(updated, ANCHOR_SEARCH, "python",
                            SEARCH.read_text(encoding="utf-8"))
    updated = replace_fence(updated, ANCHOR_RENDER, "python",
                            RENDER.read_text(encoding="utf-8"))
    updated = replace_fence(updated, ANCHOR_LAYOUT, "html",
                            LAYOUT.read_text(encoding="utf-8"))

    if updated == plan:
        print("Plan.md already in sync.")
        return
    if args.check:
        print("Plan.md is stale (run `uv run sync-docs`).")
        raise SystemExit(1)
    PLAN.write_text(updated, encoding="utf-8")
    print("Plan.md synced from src/*.py + templates/layout.html.")


if __name__ == "__main__":
    main()
