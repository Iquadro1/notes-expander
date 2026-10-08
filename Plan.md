# AI Notes Expander

## Project Description
The **AI Notes Expander** is an agent-driven, local pipeline designed to transform raw, handwritten mathematical notes into comprehensive, well-formatted digital documents. Instead of relying on traditional, error-prone OCR like Tesseract, this project leverages advanced AI agents (like Google Antigravity) with native vision capabilities to read handwritten notes. 

The system acts as a local Retrieval-Augmented Generation (RAG) tool. When the AI agent encounters abbreviated or unclear concepts or missing proofs in the handwritten notes, it uses built-in Python CLI tools to search a local vector/BM25 database of reference textbooks (PDFs) and past notes. The agent then synthesizes the transcribed notes with the retrieved formal definitions, outputting a complete Markdown document enriched with LaTeX mathematics and source tags (`#page` + `box` region coordinates). Finally, a rendering script converts this Markdown into an interactive, dual-pane HTML interface that synchronizes the expanded text with the original source pages: hovering a section shows its source page and draws a highlight box around the exact region it came from.

## Key Features
*   **Agent-Native Transcription:** Bypasses standard OCR by utilizing the AI agent's multimodal vision to accurately parse complex handwritten mathematical notation.
*   **Local RAG Context Retrieval:** Uses `pymupdf` and `rank_bm25` to index and search local PDF textbooks, allowing the agent to pull formal definitions without sending entire books to an LLM.
*   **Markdown + LaTeX Support:** Full support for mathematical formatting using MathJax ($ for inline, $$ for block equations). Math is tokenized before the Markdown pass so `\_`, `&`, `<` inside formulas survive untouched.
*   **Custom Synchronization Syntax:** Uses lightweight shortcodes (`[source: notes.pdf#page=2&box=x,y,w,h]`, `[ref: book.pdf#page=42]`) to link text sections to the exact page and region of their visual origins.
*   **Interactive Dual-Pane UI:** A custom HTML/JS renderer that groups the text into hoverable sections; hovering a section instantly loads its source page in the viewer pane and draws a pulsing highlight box over the transcribed region (multi-page sources get prev/next page navigation).
*   **Rasterized Source Pages:** `render-html` exports PDF pages to `output/<course>/assets/<stem>/page-N.png` (PyMuPDF) so a highlight box can be overlaid — a native PDF `<object>` plugin cannot be overlaid.
*   **Language Fidelity:** the rendered document is written strictly in the language of the original notes; reference material from books in other languages (e.g. English textbooks) is translated/paraphrased into the notes' language.
*   **Multi-Course Workspaces:** every course lives in `data/courses/<slug>/` with its own inbox, archive, and `output/<slug>/` folder; the one-line `ACTIVE_COURSE` file in the project root selects the course currently being processed (sources resolve inside it, so identical filenames like `01.pdf` never collide).
*   **Modular CLI Architecture:** Built with `uv` for fast dependency management, turning Python scripts into accessible terminal tools for the AI agent.
    `extract-refs` / `search-refs` (index + BM25, `--json`/`--batch`), `export-notes` (inbox → viewable PNGs),
    `suggest-boxes` (ink-gap edges for highlight boxes), `new-lesson` (lesson scaffold for any inbox filename),
    `lint-md` (checks without rendering, `--fix`), `render-html` (`--strict` fails on warnings),
    `verify-html` (freshness + assets + headless chromium hover test), `archive-lesson` (guarded inbox → archive),
    `sync-docs` (regenerates this doc's code from `src/` + `templates/`, `--check` for CI).

---

## Shortcode Syntax

Shortcodes appear on their own line (blank line before/after) and open a new viewer section; everything until the *next* shortcode belongs to it.

```text
[source: notes.pdf]                       whole source document, page 1
[source: notes.pdf#page=2]                page 2 of a scanned source PDF
[source: scan.jpg#box=0,0.3,1,0.15]       image + highlight region
[source: notes.pdf#page=3&box=0,0.2,1,0.1]
[ref: book.pdf#page=42]                   that book page, rasterized to PNG
[ref: book.pdf]                           whole book, embedded PDF viewer
```

*   `box` = `x,y,w,h` as fractions of page width/height (0–1), origin top-left.
*   **Box convention:** source boxes span the full page width (`x=0, w=1`); the top/bottom edges sit in the blank gaps between handwriting lines, never across ink. The viewer draws a thin outline *inside* the rectangle (`box-sizing: border-box`), so the coordinates are the outer rectangle.
*   `render-html` validates placement and warns when a border crosses ink (`[name] box <edge> border crosses ink`) — fix the coordinates and re-render.
*   Source files are searched in the active course's `raw_notes/` **and** `processed_notes/` (`data/courses/<slug>/`); references in the course's `reference_books/` first, then the shared `data/reference_books/` and `data/reference_notes/`.
*   Source PDFs are rasterized to `output/<course>/assets/<stem>/page-N.png` at render time (cached; `--skip-export` reuses existing PNGs).
*   Missing files produce a `WARNING` at render time and a visible error state in the UI.
*   **Document header:** every lesson starts with the course display name from `data/courses/<slug>/course.txt` as the H1, followed by a subtitle with the lesson number in the notes' language (`# <course>` / `## Lezione 1`); the H1 is also the HTML `<title>`. `render-html` warns when the header is wrong.


---

## Directory Structure

```text
ai-notes-expander/
├── pyproject.toml
├── AGENTS.md
├── ACTIVE_COURSE          # slug of the course being processed (one line)
├── data/
│   ├── courses/
│   │   └── <slug>/        # one workspace per course
│   │       ├── raw_notes/         # Target note images/scans to transcribe (Inbox)
│   │       ├── processed_notes/   # Successfully transcribed sources (Archive)
│   │       ├── reference_books/   # optional course-specific textbooks
│   │       └── reference_notes/   # optional course-specific transcriptions
│   ├── reference_books/   # PDF textbooks (shared across courses)
│   └── reference_notes/   # Previously transcribed notes (.md, shared)
├── db/
│   └── index.json         # Serialized corpus for local search (shared)
├── src/
│   ├── __init__.py
│   ├── extract.py         # Builds db/index.json (shared + per-course refs)
│   ├── search.py          # BM25 search utility (--json, --batch)
│   ├── render.py          # HTML generation, regex parsing (course-aware, --strict)
│   ├── export_notes.py    # Inbox PDFs -> viewable PNGs (export-notes)
│   ├── suggest.py         # Ink-gap box edges (suggest-boxes)
│   ├── new_lesson.py      # Lesson scaffold for any inbox filename (new-lesson)
│   ├── lint.py            # Checks without rendering (lint-md --fix)
│   ├── verify.py          # Freshness + assets + headless hover test (verify-html)
│   ├── archive.py         # Guarded raw_notes -> processed_notes (archive-lesson)
│   └── sync_docs.py       # Regenerates Plan.md code fences (sync-docs)
├── scripts/
│   └── verify-hover.js    # Puppeteer hover test used by verify-html
├── templates/
│   └── layout.html        # Jinja2 template with hover UI, box overlay, MathJax
└── output/
    └── <slug>/            # Final rendered .md and .html files per course
        └── assets/        # PNG pages rasterized from source PDFs (generated, gitignored)
```

---

## Phase-by-Phase Implementation & Code Snippets

### 1. Project Configuration (`pyproject.toml`)
Initialize the project with `uv init ai-notes-expander` and use this configuration to set up the CLI entry points.

```toml
[project]
name = "ai-notes-expander"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "markdown>=3.7",
    "pymupdf>=1.24",
    "rank-bm25>=0.2",
    "jinja2>=3.1",
]

[project.scripts]
extract-refs = "src.extract:main"
search-refs = "src.search:main"
render-html = "src.render:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src"]
```

### 2. Knowledge Base Extraction (`src/extract.py`)
This script builds the searchable local index from your reference materials.

> [!NOTE]
> **Future Improvement - Math Extraction:** Currently, `PyMuPDF` extracts text reasonably well but can mangle complex LaTeX formulas into broken Unicode. While BM25 will still find surrounding keywords, the displayed context may have messy math. In the future, replacing `PyMuPDF` with a vision-based math OCR tool like `nougat` or `marker` would provide high-fidelity LaTeX extraction from reference PDFs.

```python
"""Build the BM25 search index from reference PDFs and notes.

Indexes (shared + per-course, so the searchable set matches what
render-html can resolve):
    data/reference_books/*.pdf          (shared, course="")
    data/reference_notes/*.md           (shared, course="")
    data/courses/<slug>/reference_books/*.pdf
    data/courses/<slug>/reference_notes/*.md

Each chunk: {source, page, text, course, path}.
`source` stays the basename (backward compatible with search-refs output).
"""

import os
import json
import pymupdf
from pathlib import Path


def extract_pdf_chunks(pdf_path, course=""):
    doc = pymupdf.open(pdf_path)
    chunks = []

    for page_num, page in enumerate(doc):
        # Extract by blocks (paragraphs) to maintain semantic context better than naive word counts
        blocks = page.get_text("blocks")
        for block in blocks:
            text = block[4].strip()
            if len(text) > 20:  # filter out tiny artifacts
                chunks.append({
                    "source": os.path.basename(pdf_path),
                    "page": page_num + 1,
                    "text": text,
                    "course": course,
                    "path": str(pdf_path),
                })
    return chunks


def extract_md_chunks(md_path, course=""):
    with open(md_path, 'r', encoding='utf-8') as f:
        paragraphs = f.read().split('\n\n')

    return [{
        "source": os.path.basename(md_path),
        "page": "N/A",
        "text": p.strip(),
        "course": course,
        "path": str(md_path),
    } for p in paragraphs if len(p.strip()) > 20]


def index_dir(pdf_dir, md_dir, course, corpus):
    if pdf_dir.is_dir():
        for pdf_file in sorted(pdf_dir.glob("*.pdf")):
            corpus.extend(extract_pdf_chunks(pdf_file, course))
    if md_dir.is_dir():
        for md_file in sorted(md_dir.glob("*.md")):
            corpus.extend(extract_md_chunks(md_file, course))


def main():
    db_path = Path("db")
    db_path.mkdir(exist_ok=True)
    corpus = []

    # Shared library first (course="" keeps old consumers working).
    index_dir(Path("data/reference_books"), Path("data/reference_notes"), "", corpus)

    # Per-course libraries (matches render-html REFERENCE_DIRS).
    courses_dir = Path("data/courses")
    if courses_dir.is_dir():
        for entry in sorted(courses_dir.iterdir()):
            if entry.is_dir():
                index_dir(entry / "reference_books", entry / "reference_notes",
                          entry.name, corpus)

    with open(db_path / "index.json", "w", encoding='utf-8') as f:
        json.dump(corpus, f, indent=2)
    print(f"Indexed {len(corpus)} chunks.")


if __name__ == "__main__":
    main()
```

### 3. Local Search Utility (`src/search.py`)
The AI agent uses this script to fetch context for mathematical expansions.

```python
"""BM25 search over the local reference index.

Usage:
    uv run search-refs "Cauchy-Riemann equations"
    uv run search-refs "functor" --top_k 5 --json
    uv run search-refs --batch queries.txt --top_k 3

--json prints machine-readable results (for scripts / batch pipelines).
--batch runs one query per non-empty line of a file.
"""

import json
import argparse
import re
from pathlib import Path
from rank_bm25 import BM25Okapi


def load_corpus():
    index_path = Path("db/index.json")
    if not index_path.exists():
        raise SystemExit("Index not found. Run extract-refs first.")
    with open(index_path, "r", encoding="utf-8") as f:
        corpus = json.load(f)
    if not corpus:
        raise SystemExit("Corpus is empty.")
    return corpus


def build_bm25(corpus):
    tokenized_corpus = [re.findall(r"\w+", doc["text"].lower()) for doc in corpus]
    return BM25Okapi(tokenized_corpus)


def search(corpus, bm25, query, top_k):
    tokenized_query = re.findall(r"\w+", query.lower())
    return bm25.get_top_n(tokenized_query, corpus, n=top_k)


def print_human(query, docs):
    print(f"\n=== Query: {query} ===")
    for i, doc in enumerate(docs):
        course = doc.get("course", "")
        tag = f" | Course: {course}" if course else ""
        print(f"\n--- Result {i+1} ---")
        print(f"Source: {doc['source']} | Page: {doc['page']}{tag}")
        print(f"Text:\n{doc['text']}\n")


def main():
    parser = argparse.ArgumentParser(description="Search reference texts.")
    parser.add_argument("query", type=str, nargs="?", help="Mathematical concept to search")
    parser.add_argument("--top_k", type=int, default=3, help="Number of results")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of human text")
    parser.add_argument("--batch", type=str, default=None, help="File with one query per line")
    args = parser.parse_args()

    queries: list[str] = []
    if args.batch:
        queries = [
            line.strip()
            for line in Path(args.batch).read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        if not queries:
            raise SystemExit(f"ERROR: no queries in {args.batch}")
    elif args.query:
        queries = [args.query]
    else:
        raise SystemExit("ERROR: give a query or --batch <file>.")

    corpus = load_corpus()
    bm25 = build_bm25(corpus)

    all_results = []
    for q in queries:
        docs = search(corpus, bm25, q, args.top_k)
        if args.json:
            all_results.append({"query": q, "results": docs})
        else:
            print_human(q, docs)

    if args.json:
        print(json.dumps(all_results if args.batch else all_results[0]["results"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
```

### 4. Markdown Rendering UI (`src/render.py`)
Converts the agent's tagged Markdown into interactive HTML.

```python
"""Render tagged Markdown notes into the interactive split-view HTML viewer.

Pipeline:
    1. Extract LaTeX math into opaque tokens so python-markdown cannot
       mangle ``_`` / ``*`` / ``&`` / ``<`` inside formulas.
    2. Normalize the Markdown: guarantee blank lines around
       ``[source: ...]`` / ``[ref: ...]`` shortcodes and around
       bullet/numbered lists (python-markdown needs them).
    3. Expand shortcodes into viewer markers, resolving the file across
       the active course's ``raw_notes`` + ``processed_notes`` (sources)
       and the course's / shared ``reference_books`` + ``reference_notes``
       (references).
    4. Materialize viewer assets: source PDFs are rasterized to
       ``output/<course>/assets/<stem>/page-N.png`` so the UI can draw a
       highlight box on the page image (a ``<object>`` PDF viewer cannot
       be overlaid). Reference PDFs given as ``#page=N`` get that one
       page rasterized.
    5. Escape stray prose underscores, run Markdown, restore math.
    6. Fill ``templates/layout.html`` and write
       ``output/<course>/<name>.html``.

Course selection
----------------
The course being worked on is read from the ``ACTIVE_COURSE`` file in the
project root (first non-comment line = slug of a directory under
``data/courses/``), or passed explicitly with ``--course <slug>``.
Everything derives from it:

    data/courses/<slug>/raw_notes/          incoming scans (inbox)
    data/courses/<slug>/processed_notes/    archived sources
    output/<slug>/<name>.html               rendered document
    output/<slug>/assets/<stem>/page-N.png  rasterized pages

Shortcode syntax
----------------
    [source: notes.pdf]                        whole document, page 1
    [source: notes.pdf#page=2]                 page 2 of a scanned PDF
    [source: scan.jpg#box=0,0.3,1,0.15]        highlight region
    [source: notes.pdf#page=3&box=0,0.2,1,0.1]
    [ref: book.pdf#page=42]                    rasterize that book page
    [ref: book.pdf]                            embed the whole book

``box`` is ``x,y,w,h`` as fractions of the page width/height,
origin at the top-left corner (values clamped to 0..1).

Box convention (enforced with warnings, see ``check_box_ink``):
source boxes span the full page width (``x=0, w=1``) and their top and
bottom edges sit in the blank gaps between handwriting lines - never
across ink. The viewer draws the outline *inside* the rectangle with a
thin border, so coordinates are the outer rectangle.

Document header (enforced with warnings, see ``check_lesson_header``):
every lesson document starts with the course display name (read from
``data/courses/<slug>/course.txt``) as the H1, followed within a couple
of lines by a subtitle carrying the lesson number in the notes'
language, e.g.::

    # Elementi di Topologia Algebrica
    ## Lezione 1

The H1 is also used as the HTML ``<title>``.
"""

from __future__ import annotations

import argparse
import html as html_lib
import os
import re
from pathlib import Path
from urllib.parse import quote

import markdown
from jinja2 import Environment, FileSystemLoader

# --- Locations -------------------------------------------------------------
# SOURCE_DIRS / OUTPUT_DIR / ASSETS_DIR are overridden by configure() for the
# active course; the defaults below are only used if parse_markdown() is called
# without it (e.g. from tests).
COURSES_DIR = Path("data/courses")
ACTIVE_COURSE_FILE = Path("ACTIVE_COURSE")
OUTPUT_ROOT = Path("output")

SOURCE_DIRS = (Path("data/raw_notes"), Path("data/processed_notes"))
REFERENCE_DIRS = (Path("data/reference_books"), Path("data/reference_notes"))
OUTPUT_DIR = OUTPUT_ROOT
ASSETS_DIR = OUTPUT_DIR / "assets"
TEMPLATE_DIR = Path("templates")

# Display name of the active course (data/courses/<slug>/course.txt).
# Used to validate the document header (`# <course name>` + `## Lezione N`)
# and as the HTML <title>; None when the file does not exist yet.
COURSE_TITLE: str | None = None

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
MAX_SOURCE_PAGES = 100   # safety valve when rasterizing scanned PDFs
RASTER_ZOOM = 2.0        # 2x scale for exported page images
SKIP_EXPORT = False      # set by --skip-export (reuse existing output/<course>/assets)

# --- Regexes ---------------------------------------------------------------
SHORTCODE_LINE_RE = re.compile(r"^\s*\[(source|ref):\s*([^\]]+)\]\s*$")
SHORTCODE_RE = re.compile(r"\[(source|ref):\s*([^\]]+)\]")
LIST_ITEM_RE = re.compile(r"^\s*(?:[-*+] |\d+[.)] )")
DISPLAY_MATH_RE = re.compile(r"\$\$.+?\$\$", re.S)
INLINE_MATH_RE = re.compile(r"(?<!\$)\$(?!\$).+?(?<!\$)\$(?!\$)", re.S)
MATH_TOKEN_RE = re.compile(r"MathZzZ(\d+)ZzZmath")

# Opaque, alphanumeric token: immune to Markdown emphasis/escaping.
MATH_TOKEN_FMT = "MathZzZ{}ZzZmath"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
WARNING_COUNT = 0


def warn(message: str) -> None:
    global WARNING_COUNT
    WARNING_COUNT += 1
    print(f"  WARNING: {message}")


def reset_warnings() -> None:
    global WARNING_COUNT
    WARNING_COUNT = 0


def resolve_file(name: str, dirs: tuple[Path, ...]) -> Path | None:
    """Find `name` in one of `dirs` (or as a direct path)."""
    direct = Path(name)
    if direct.is_file():
        return direct
    for folder in dirs:
        candidate = folder / name
        if candidate.is_file():
            return candidate
    return None


def rel_url(path: Path) -> str:
    """Path of `path` relative to the output/ folder, as a URL (encoded)."""
    rel = os.path.relpath(path.resolve(), OUTPUT_DIR.resolve())
    return quote(rel.replace(os.sep, "/"))


def extract_math(text: str) -> tuple[str, list[str]]:
    """Replace LaTeX spans with opaque tokens (order: display, then inline)."""
    store: list[str] = []

    def repl(match: re.Match) -> str:
        store.append(match.group(0))
        return MATH_TOKEN_FMT.format(len(store) - 1)

    text = DISPLAY_MATH_RE.sub(repl, text)
    text = INLINE_MATH_RE.sub(repl, text)
    return text, store


def restore_math(html_text: str, store: list[str]) -> str:
    """Put math back (HTML-escaped so the browser hands MathJax the raw text)."""

    def repl(match: re.Match) -> str:
        return html_lib.escape(store[int(match.group(1))], quote=False)

    return MATH_TOKEN_RE.sub(repl, html_text)


def normalize_markdown(text: str) -> str:
    """Ensure blank lines before/after shortcodes and around lists."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")
    out: list[str] = []

    for line in lines:
        prev = out[-1] if out else None
        if prev is not None and prev.strip():
            is_shortcode = bool(SHORTCODE_LINE_RE.match(line))
            is_list = bool(LIST_ITEM_RE.match(line))
            prev_shortcode = bool(SHORTCODE_LINE_RE.match(prev))
            prev_list = bool(LIST_ITEM_RE.match(prev))
            need_blank = (
                is_shortcode
                or prev_shortcode
                or (is_list and not prev_list)
                or (prev_list and not is_list)
            )
            if need_blank:
                out.append("")
        out.append(line)

    while out and not out[-1].strip():
        out.pop()
    return "\n".join(out) + "\n"


def escape_prose_underscores(text: str) -> str:
    """Escape ``_`` outside HTML tags so Markdown cannot open <em> tags.

    Math is already tokenized at this point and shortcode markers are raw
    HTML tags, so file paths and formulas are left untouched. Already
    escaped ``\\_`` is left alone to avoid double-escaping.
    """
    parts = re.split(r"(<[^>]+>)", text)
    for i in range(0, len(parts), 2):  # even indexes = text outside tags
        parts[i] = re.sub(r"(?<!\\)_", r"\_", parts[i])
    return "".join(parts)


# ---------------------------------------------------------------------------
# Assets
# ---------------------------------------------------------------------------
def export_pdf_pages(pdf_path: Path, wanted: list[int] | None) -> tuple[Path, list[int], int]:
    """Rasterize PDF pages to ``output/<course>/assets/<stem>/page-N.png`` (cached).

    `wanted=None` exports every page (capped at MAX_SOURCE_PAGES).
    Returns (asset_dir, exported_page_numbers, total_pages_in_pdf).
    """
    import pymupdf

    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", pdf_path.stem).strip("._") or "document"
    asset_dir = ASSETS_DIR / stem
    asset_dir.mkdir(parents=True, exist_ok=True)

    with pymupdf.open(pdf_path) as doc:
        total = doc.page_count
        if wanted is None:
            pages = list(range(1, min(total, MAX_SOURCE_PAGES) + 1))
            if total > MAX_SOURCE_PAGES:
                warn(f"{pdf_path.name}: only first {MAX_SOURCE_PAGES} of {total} pages exported")
        else:
            pages = [p for p in wanted if 1 <= p <= total]
            for p in wanted:
                if not 1 <= p <= total:
                    warn(f"{pdf_path.name}: page {p} out of range (1..{total})")

        if SKIP_EXPORT:
            return asset_dir, pages, total

        pdf_mtime = pdf_path.stat().st_mtime
        matrix = pymupdf.Matrix(RASTER_ZOOM, RASTER_ZOOM)
        for page_no in pages:
            out_png = asset_dir / f"page-{page_no}.png"
            if out_png.exists() and out_png.stat().st_mtime >= pdf_mtime:
                continue
            pix = doc[page_no - 1].get_pixmap(matrix=matrix, alpha=False)
            pix.save(out_png)

    return asset_dir, pages, total


# ---------------------------------------------------------------------------
# Shortcodes -> viewer markers
# ---------------------------------------------------------------------------
def parse_box(raw: str) -> str | None:
    try:
        values = [float(v) for v in raw.split(",")]
        if len(values) != 4:
            raise ValueError("expected 4 numbers")
    except ValueError:
        warn(f"bad box value {raw!r} (expected x,y,w,h in 0..1) - ignored")
        return None
    clamped = [min(max(v, 0.0), 1.0) for v in values]
    if clamped != values:
        warn(f"box {raw!r} clamped to {clamped}")
    return ",".join(f"{v:.4f}" for v in clamped)


def check_ambiguous_stars(text: str) -> None:
    """Warn about `***` sequences in prose (Markdown emphasis is ambiguous)."""
    for lineno, line in enumerate(text.split("\n"), start=1):
        if re.search(r"(?<!\\)\*{3,}", line):
            warn(
                f"line {lineno}: three consecutive `*` found - write `**bold with "
                r"\* or \_**` (or use $...$ math) instead of `**...***`"
            )


# --- Box placement check ---------------------------------------------------
# A highlight box is drawn as a thin CSS outline *inside* its x,y,w,h
# rectangle, so a border drawn across handwriting visibly strikes through
# the text. These helpers scan the rasterized page around the four edges
# and warn when an edge crosses ink instead of blank space.
EDGE_STRIP = 0.004  # half-height/width (page fraction) scanned around a box edge
INK_RUN_FRAC = 0.04  # an edge strip row/col with more ink than this warns
INK_STEP = 2  # pixel sampling stride when scanning edge strips

_pixmap_cache: dict[str, "pymupdf.Pixmap | None"] = {}


def _cached_pixmap(png: Path) -> "pymupdf.Pixmap | None":
    """Load a rasterized page image once (None when the file is missing)."""
    import pymupdf

    key = str(png)
    if key not in _pixmap_cache:
        _pixmap_cache[key] = pymupdf.Pixmap(png) if png.is_file() else None
    return _pixmap_cache[key]


def _is_ink(r: int, g: int, b: int) -> bool:
    """Ink pixel: saturated pen strokes and dark print, but not grid lines."""
    mx = max(r, g, b)
    return (mx - min(r, g, b) > 70 and mx < 245) or mx < 170


def check_box_ink(name: str, pix: "pymupdf.Pixmap", box: str) -> None:
    """Warn when a highlight-box border crosses ink instead of blank space."""
    try:
        x, y, w, h = (float(v) for v in box.split(","))
    except ValueError:
        return
    if pix.n < 3:
        return
    W, H, s, n = pix.width, pix.height, pix.samples, pix.n
    step = INK_STEP
    x0, x1 = int(x * W), int((x + w) * W)
    y0, y1 = int(y * H), int((y + h) * H)
    cx0, cx1 = max(0, x0), min(W, x1)
    cols = max(1, (cx1 - cx0) // step)
    strip = max(1, int(EDGE_STRIP * H))

    def row_ink(row: int) -> int:
        if not 0 <= row < H or cx0 >= cx1:
            return 0
        base = row * W * n
        return sum(
            1
            for cx in range(cx0, cx1, step)
            if _is_ink(s[base + cx * n], s[base + cx * n + 1], s[base + cx * n + 2])
        )

    for edge, rows in (
        ("top", range(y0 - strip, y0 + strip + 1)),
        ("bottom", range(y1 - strip, y1 + strip + 1)),
    ):
        if any(row_ink(r) > INK_RUN_FRAC * cols for r in rows):
            warn(
                f"[{name}] box {edge} border crosses ink ({box}) - "
                "move the edge into the blank gap between lines"
            )
            return

    # Side borders only matter for inset boxes; full-width boxes (x=0, w=1)
    # put their sides on the page edge where handwriting may legitimately
    # run off the paper.
    cy0, cy1 = max(0, y0), min(H, y1)
    rows_n = max(1, (cy1 - cy0) // step)

    def col_ink(col: int) -> int:
        if not 0 <= col < W or cy0 >= cy1:
            return 0
        return sum(
            1
            for ry in range(cy0, cy1, step)
            if _is_ink(
                s[(ry * W + col) * n],
                s[(ry * W + col) * n + 1],
                s[(ry * W + col) * n + 2],
            )
        )

    strip_x = max(1, int(EDGE_STRIP * W))
    sides = []
    if x0 > strip_x:
        sides.append(("left", range(x0 - strip_x, x0 + strip_x + 1)))
    if x1 < W - strip_x:
        sides.append(("right", range(x1 - strip_x, x1 + strip_x + 1)))
    for edge, cols_range in sides:
        if any(col_ink(c) > INK_RUN_FRAC * rows_n for c in cols_range):
            warn(
                f"[{name}] box {edge} border crosses ink ({box}) - "
                "widen the box to the page edge (x=0, w=1) or move the edge"
            )
            return


def check_lesson_header(text: str, course_title: str | None) -> None:
    """Warn unless the document starts with `# <course name>` + a lesson subtitle.

    The contract (AGENTS.md, Step 3.0) is::

        [source: 01.pdf#page=1&box=...]
        # Elementi di Topologia Algebrica
        ## Lezione 1

    i.e. the course display name from ``data/courses/<slug>/course.txt`` as the
    H1, then (within a couple of lines) a subtitle that ends with the lesson
    number - localized to the notes' language (``Lezione 1``, ``Lesson 1``, ...).
    """
    lines = text.split("\n")
    headings = [(i, line.strip()) for i, line in enumerate(lines)
                if re.match(r"^#{1,6}\s", line.strip())]
    if not headings:
        warn("no heading found - start the document with `# <course name>` "
             "and a `## Lezione N` subtitle")
        return

    first_idx, first = headings[0]
    title = re.match(r"^#\s+(.+)$", first)
    if course_title:
        if not title or title.group(1).strip().casefold() != course_title.strip().casefold():
            warn(f"document should start with `# {course_title}` (found: {first!r}) - "
                 "the course name lives in data/courses/<slug>/course.txt")
    elif not title:
        warn(f"first heading should be the course name `# <course name>` (found: {first!r})")

    # The lesson subtitle must follow the title almost immediately.
    if len(headings) > 1 and headings[1][0] - first_idx <= 4:
        subtitle = headings[1][1]
        if not re.match(r"^#{1,6}\s+\D*\d\s*$", subtitle):
            warn(f"expected a lesson subtitle right after the course title "
                 f"(e.g. `## Lezione 1`, in the notes' language), found: {subtitle!r}")
    else:
        warn("missing lesson subtitle right after the course title "
             "(e.g. `## Lezione 1`, in the notes' language)")


def build_marker(kind: str, spec: str) -> str:
    """Turn one shortcode into an empty <div> marker carrying viewer data."""
    is_ref = kind == "ref"
    name, _, fragment = spec.strip().partition("#")
    name = name.strip()

    opts: dict[str, str] = {}
    for pair in fragment.split("&") if fragment else []:
        if "=" in pair:
            key, value = pair.split("=", 1)
            opts[key.strip().lower()] = value.strip()

    page: int | None = None
    if "page" in opts:
        try:
            page = max(1, int(opts["page"]))
        except ValueError:
            warn(f"bad page value {opts['page']!r} in [{kind}: {spec}] - ignored")

    box = parse_box(opts["box"]) if "box" in opts else None

    attrs: dict[str, str] = {
        "class": "sync-marker" + (" ref-marker" if is_ref else ""),
        "data-title": name,
        "data-kind": "none",
    }

    path = resolve_file(name, REFERENCE_DIRS if is_ref else SOURCE_DIRS)
    if path is None:
        searched = ", ".join(str(d) for d in (REFERENCE_DIRS if is_ref else SOURCE_DIRS))
        warn(f"[{kind}: {name}] not found (searched: {searched})")
        attrs["data-kind"] = "missing"
    else:
        ext = path.suffix.lower()
        if ext in IMAGE_EXTENSIONS:
            attrs["data-kind"] = "image"
            attrs["data-src"] = rel_url(path)
            if box:
                attrs["data-box"] = box
                attrs["data-page"] = "1"
                pix = _cached_pixmap(path)
                if pix is not None:
                    check_box_ink(name, pix, box)
        elif ext == ".pdf":
            if is_ref and page is None:
                # Whole reference book: shown in the native PDF viewer.
                attrs["data-kind"] = "doc"
                attrs["data-file"] = rel_url(path)
            elif is_ref:
                # Single book page -> PNG so it renders (and highlights) everywhere.
                asset_dir, pages, total = export_pdf_pages(path, [page])
                if pages:
                    attrs["data-kind"] = "page"
                    attrs["data-src"] = rel_url(asset_dir / f"page-{page}.png")
                    attrs["data-file"] = rel_url(path)
                    attrs["data-page"] = str(page)
                    attrs["data-total"] = str(total)
                    if box:
                        attrs["data-box"] = box
                        pix = _cached_pixmap(asset_dir / f"page-{page}.png")
                        if pix is not None:
                            check_box_ink(name, pix, box)
            else:
                # Source notes PDF: every page becomes a PNG (browsable).
                asset_dir, pages, total = export_pdf_pages(path, None)
                if page and page not in pages:
                    warn(f"{name}: #page={page} not available (1..{total}) - starting at page 1")
                attrs["data-kind"] = "pages"
                attrs["data-base"] = rel_url(asset_dir / "page")
                attrs["data-count"] = str(len(pages))
                attrs["data-page"] = str(page if page in pages else 1)
                attrs["data-file"] = rel_url(path)
                if box:
                    attrs["data-box"] = box
                    shown = page if page in pages else 1
                    pix = _cached_pixmap(asset_dir / f"page-{shown}.png")
                    if pix is not None:
                        check_box_ink(name, pix, box)
        else:
            warn(f"[{kind}: {name}] is neither an image nor a PDF - only linked")
            attrs["data-kind"] = "link"
            attrs["data-file"] = rel_url(path)

    rendered = " ".join(
        f'{key}="{html_lib.escape(value, quote=True)}"'
        for key, value in attrs.items()
        if value != ""
    )
    return f"<div {rendered}></div>"


def parse_markdown(md_text: str) -> str:
    text, math_store = extract_math(md_text)
    text = normalize_markdown(text)
    check_ambiguous_stars(text)
    text = SHORTCODE_RE.sub(lambda m: build_marker(m.group(1), m.group(2)), text)
    text = escape_prose_underscores(text)
    html_text = markdown.markdown(text, extensions=["fenced_code", "tables"])
    return restore_math(html_text, math_store)


# ---------------------------------------------------------------------------
# Course configuration (multi-course workspaces, see ACTIVE_COURSE)
# ---------------------------------------------------------------------------
def available_courses() -> list[str]:
    if not COURSES_DIR.is_dir():
        return []
    return sorted(entry.name for entry in COURSES_DIR.iterdir() if entry.is_dir())


def resolve_course(course: str | None) -> str:
    """Pick the active course: --course flag, else the ACTIVE_COURSE file."""
    if course is None:
        if not ACTIVE_COURSE_FILE.is_file():
            raise SystemExit(
                f"ERROR: no course given and {ACTIVE_COURSE_FILE} not found. "
                f"Create it with a course slug (available: "
                f"{', '.join(available_courses()) or 'none'}) or pass --course <slug>."
            )
        lines = [
            line.strip()
            for line in ACTIVE_COURSE_FILE.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        if not lines:
            raise SystemExit(f"ERROR: {ACTIVE_COURSE_FILE} is empty - put a course slug in it.")
        course = lines[0]
    if not (COURSES_DIR / course).is_dir():
        raise SystemExit(
            f"ERROR: unknown course {course!r} (no {COURSES_DIR / course}). "
            f"Available: {', '.join(available_courses()) or 'none'}"
        )
    return course


def configure(course: str | None) -> str:
    """Point SOURCE_DIRS / REFERENCE_DIRS / OUTPUT_DIR / ASSETS_DIR at a course."""
    global SOURCE_DIRS, REFERENCE_DIRS, OUTPUT_DIR, ASSETS_DIR, COURSE_TITLE
    slug = resolve_course(course)
    course_dir = COURSES_DIR / slug
    SOURCE_DIRS = (course_dir / "raw_notes", course_dir / "processed_notes")
    REFERENCE_DIRS = (
        course_dir / "reference_books",    # optional, course-specific books
        course_dir / "reference_notes",
        Path("data/reference_books"),      # shared library + BM25 index
        Path("data/reference_notes"),
    )
    OUTPUT_DIR = OUTPUT_ROOT / slug
    ASSETS_DIR = OUTPUT_DIR / "assets"
    title_file = course_dir / "course.txt"
    if title_file.is_file():
        COURSE_TITLE = title_file.read_text(encoding="utf-8").strip() or None
    else:
        COURSE_TITLE = None
        warn(f"{title_file} not found - cannot validate the course title in the header")
    return slug


# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description="Render tagged notes to HTML")
    parser.add_argument("input_file", type=str, help="Markdown file to render")
    parser.add_argument(
        "--course",
        type=str,
        default=None,
        help="Course slug under data/courses/ (default: contents of ACTIVE_COURSE)",
    )
    parser.add_argument(
        "--skip-export",
        action="store_true",
        help="Do not rasterize PDF pages (reuse existing output/<course>/assets)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with code 1 when any WARNING was emitted (for CI / archive guard)",
    )
    args = parser.parse_args()

    global SKIP_EXPORT
    SKIP_EXPORT = args.skip_export
    reset_warnings()
    slug = configure(args.course)

    input_path = Path(args.input_file)
    with open(input_path, "r", encoding="utf-8") as handle:
        md_text = handle.read()

    check_lesson_header(md_text, COURSE_TITLE)
    html_content = parse_markdown(md_text)

    match = re.search(r"^#\s+(.+)$", md_text, re.M)
    doc_title = (match.group(1).strip() if match else input_path.stem)

    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    template = env.get_template("layout.html")
    final_html = template.render(html_content=html_content, title=doc_title)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{input_path.stem}.html"
    with open(output_path, "w", encoding="utf-8") as handle:
        handle.write(final_html)

    print(f"Rendered HTML saved to {output_path} (course: {slug})")
    if WARNING_COUNT:
        print(f"{WARNING_COUNT} warning(s) emitted.")
        if args.strict:
            raise SystemExit(1)
    else:
        print("OK: no warnings.")


if __name__ == "__main__":
    main()
```


### 5. Layout Template (`templates/layout.html`)

> [!NOTE]
> **Future Improvement - 100% Offline Mode:** The current template relies on a CDN to load `MathJax` (requiring an active internet connection). For a fully offline, air-gapped local RAG experience, you could download the MathJax library locally and serve it via a local path or embed it directly.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ title }}</title>
<style>
  :root {
    --accent: #007bff;
    --accent-soft: rgba(0, 123, 255, 0.18);
  }
  body { margin: 0; font-family: system-ui, -apple-system, sans-serif; line-height: 1.6; background: #fff; }
  .container { display: flex; height: 100vh; overflow: hidden; }

  /* ---- Left pane: transcribed / rewritten notes ---- */
  .text-wrap { flex: 0 0 50%; min-width: 0; position: relative; display: flex; min-height: 0; }
  .text-pane { flex: 1 1 auto; width: 100%; padding: 2rem; overflow-y: auto; box-sizing: border-box; font-size: 1.05rem; }
  .content-section {
    padding: 0.75rem 1.25rem;
    margin: 0.75rem 0;
    border-radius: 8px;
    border-left: 4px solid transparent;
    transition: background 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
    cursor: default;
  }
  .content-section.active {
    background: #f5f9ff;
    border-left-color: var(--accent);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  }

  /* ---- Right pane: source viewer ---- */
  .viewer-pane {
    flex: 1 1 auto;
    min-width: 0;
    background: #eceff1;
    padding: 1.5rem;
    box-sizing: border-box;
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }
  .viewer-container {
    position: relative;
    flex: 1 1 auto;
    min-height: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background: #fff;
    border: 2px solid #adb5bd;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    overflow: hidden;
    transition: border-color 0.2s ease, box-shadow 0.3s ease;
  }
  .viewer-container.active-view {
    border-color: var(--accent);
    box-shadow: 0 0 0 4px var(--accent), 0 4px 12px rgba(0, 0, 0, 0.1);
  }
  .viewer-el { display: none; }
  #viewer-obj { width: 100%; height: 100%; border: none; }

  /* Image sized to its natural box so the overlay's % coords match the page.
     The outer .img-wrap is the zoom viewport (scrolls when zoomed); the
     inner .zoom-inner shrink-wraps the image so the overlay's % coords
     stay aligned at any zoom level. No border here: the gray/blue frame
     is the .viewer-container border above. */
  .img-wrap {
    position: relative;
    display: block;
    max-width: 100%;
    max-height: calc(100vh - 11rem);
    overflow: auto;
  }
  .img-wrap.zoomed { cursor: grab; }
  .img-wrap.panning { cursor: grabbing; }
  .zoom-inner { position: relative; display: inline-block; max-width: 100%; }
  #viewer-img { display: block; max-width: 100%; max-height: calc(100vh - 12rem); width: auto; height: auto; object-fit: contain; }
  .img-wrap.zoomed .zoom-inner { max-width: none; }
  .img-wrap.zoomed #viewer-img { max-width: none; max-height: none; width: 100%; }

  .box-overlay {
    position: absolute;
    display: none;
    /* border-box: the md's x,y,w,h IS the outer rectangle, so the border
       stays where the agent placed it. */
    box-sizing: border-box;
    border: 4px solid var(--accent);
    background: var(--accent-soft);
    border-radius: 6px;
    pointer-events: none;
    animation: boxpulse 1.2s ease-in-out infinite alternate;
  }
  @keyframes boxpulse {
    from { box-shadow: 0 0 0 rgba(0, 123, 255, 0); }
    to   { box-shadow: 0 0 12px rgba(0, 123, 255, 0.6); }
  }

  /* Draggable split divider between the two panes */
  #splitter {
    flex: 0 0 8px;
    cursor: col-resize;
    background: #dee2e6;
    position: relative;
    touch-action: none;
    transition: background 0.15s ease;
  }
  #splitter::after {
    content: '';
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 2px;
    height: 2.5rem;
    border-radius: 2px;
    background: #adb5bd;
  }
  #splitter:hover, #splitter.dragging { background: var(--accent-soft); }
  #splitter:hover::after, #splitter.dragging::after { background: var(--accent); }

  /* Floating per-pane zoom buttons (same steps as Ctrl+wheel) */
  .zoom-bar {
    position: absolute;
    display: flex;
    align-items: center;
    gap: 0.3rem;
    background: rgba(255, 255, 255, 0.95);
    border: 1px solid #dee2e6;
    border-radius: 999px;
    padding: 0.2rem 0.4rem;
    font-size: 0.8rem;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08);
    z-index: 5;
  }
  .zoom-bar button {
    border: 1px solid #ced4da;
    background: #fff;
    border-radius: 6px;
    min-width: 1.8rem;
    height: 1.8rem;
    line-height: 1;
    cursor: pointer;
    font-size: 0.9rem;
  }
  .zoom-bar button:disabled { opacity: 0.35; cursor: default; }
  .zoom-bar .zoom-level { min-width: 2.6rem; text-align: center; color: #495057; }
  #text-zoom { top: 0.6rem; right: 0.8rem; }
  #img-zoom { top: 0.6rem; left: 0.8rem; }
  #img-zoom { display: none; }
  #img-zoom.visible { display: flex; }

  .pane-msg { color: #6c757d; text-align: center; padding: 1.5rem; max-width: 32rem; }
  .pane-msg.warning { color: #c0392b; }

  #page-nav {
    position: absolute;
    bottom: 0.6rem;
    left: 50%;
    transform: translateX(-50%);
    display: none;
    align-items: center;
    gap: 0.6rem;
    background: rgba(255, 255, 255, 0.95);
    border: 1px solid #dee2e6;
    border-radius: 999px;
    padding: 0.25rem 0.75rem;
    font-size: 0.85rem;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08);
  }
  #page-nav.visible { display: flex; }
  #page-nav button {
    border: 1px solid #ced4da;
    background: #fff;
    border-radius: 6px;
    width: 1.8rem;
    height: 1.8rem;
    line-height: 1;
    cursor: pointer;
  }
  #page-nav button:disabled { opacity: 0.35; cursor: default; }
  #page-nav a { color: var(--accent); text-decoration: none; white-space: nowrap; }
  #page-nav a:hover { text-decoration: underline; }

  .ref-text {
    flex: 0 0 auto;
    margin: 0;
    padding: 0.75rem 1rem;
    background: #fff;
    border-radius: 8px;
    font-family: ui-monospace, monospace;
    font-size: 0.85rem;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    border-left: 4px solid #6c757d;
    overflow-wrap: anywhere;
  }
  .ref-text.source { border-left-color: #28a745; }
  .ref-text.reference { border-left-color: #ffc107; }
  .ref-text.missing { border-left-color: #dc3545; color: #dc3545; }

  /* Markers are structural only; never visible */
  .sync-marker { display: none; }
</style>
<script>
  MathJax = {
    tex: { inlineMath: [['$', '$'], ['\\(', '\\)']], displayMath: [['$$', '$$'], ['\\[', '\\]']] }
  };
</script>
<script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
</head>
<body>
<div class="container">
  <div class="text-wrap">
    <div class="text-pane" id="text-pane">
      {{ html_content }}
    </div>
    <div class="zoom-bar" id="text-zoom" title="Zoom transcribed notes">
      <button id="text-zoom-out" title="Zoom out notes">−</button>
      <span class="zoom-level" id="text-zoom-level">100%</span>
      <button id="text-zoom-in" title="Zoom in notes">+</button>
      <button id="text-zoom-reset" title="Reset notes zoom">⟲</button>
    </div>
  </div>
  <div id="splitter" title="Drag to resize panes"></div>
  <div class="viewer-pane">
    <div class="viewer-container" id="viewer-container">
      <div class="img-wrap" id="img-wrap">
        <div class="zoom-inner" id="zoom-inner">
          <img id="viewer-img" class="viewer-el" alt="Source note page">
          <div class="box-overlay" id="box-overlay"></div>
        </div>
      </div>
      <object id="viewer-obj" class="viewer-el" type="application/pdf"></object>
      <div id="empty-state" class="pane-msg">Hover over a section on the left to view its source.</div>
      <div id="missing-state" class="pane-msg warning" style="display:none;"></div>
      <div id="link-state" class="pane-msg" style="display:none;"></div>
      <div id="page-nav">
        <button id="prev-page" title="Previous page">&#8249;</button>
        <span id="page-label">1 / 1</span>
        <button id="next-page" title="Next page">&#8250;</button>
      </div>
      <div class="zoom-bar" id="img-zoom" title="Zoom source image">
        <button id="img-zoom-out" title="Zoom out image">−</button>
        <span class="zoom-level" id="img-zoom-level">100%</span>
        <button id="img-zoom-in" title="Zoom in image">+</button>
        <button id="img-zoom-reset" title="Reset image zoom">⟲</button>
      </div>
    </div>
    <div id="ref-viewer-text" class="ref-text">Awaiting synchronization...</div>
  </div>
</div>
<script>
document.addEventListener('DOMContentLoaded', () => {
  /* ---------------------------------------------------------------
   * 1. Group the document into hoverable sections.
   *    Every [source:]/[ref:] marker opens a new section; content
   *    before the first marker becomes a section without a source.
   * ------------------------------------------------------------- */
  const textPane = document.getElementById('text-pane');
  const wrappers = [];
  let currentWrapper = null;

  Array.from(textPane.children).forEach(child => {
    if (child.classList && child.classList.contains('sync-marker')) {
      currentWrapper = document.createElement('section');
      currentWrapper.className = 'content-section';
      Object.keys(child.dataset).forEach(key => {
        currentWrapper.dataset[key] = child.dataset[key];
      });
      currentWrapper.dataset.side = child.classList.contains('ref-marker') ? 'ref' : 'source';
      currentWrapper.dataset.idx = String(wrappers.length);
      textPane.insertBefore(currentWrapper, child);
      child.style.display = 'none';
      currentWrapper.appendChild(child);
      wrappers.push(currentWrapper);
    } else if (currentWrapper) {
      currentWrapper.appendChild(child);
    } else {
      currentWrapper = document.createElement('section');
      currentWrapper.className = 'content-section';
      currentWrapper.dataset.kind = 'none';
      currentWrapper.dataset.side = 'source';
      currentWrapper.dataset.idx = String(wrappers.length);
      textPane.insertBefore(currentWrapper, child);
      wrappers.push(currentWrapper);
      currentWrapper.appendChild(child);
    }
  });

  /* ---------------------------------------------------------------
   * 2. Viewer state and helpers.
   * ------------------------------------------------------------- */
  const img = document.getElementById('viewer-img');
  const obj = document.getElementById('viewer-obj');
  const box = document.getElementById('box-overlay');
  const emptyState = document.getElementById('empty-state');
  const missingState = document.getElementById('missing-state');
  const linkState = document.getElementById('link-state');
  const nav = document.getElementById('page-nav');
  const prevBtn = document.getElementById('prev-page');
  const nextBtn = document.getElementById('next-page');
  const pageLabel = document.getElementById('page-label');
  const chip = document.getElementById('ref-viewer-text');
  const container = document.getElementById('viewer-container');
  const viewerPane = document.querySelector('.viewer-pane');
  const imgWrap = document.getElementById('img-wrap');
  const zoomInner = document.getElementById('zoom-inner');
  const imgZoomBar = document.getElementById('img-zoom');
  const imgZoomIn = document.getElementById('img-zoom-in');
  const imgZoomOut = document.getElementById('img-zoom-out');
  const imgZoomReset = document.getElementById('img-zoom-reset');
  const imgZoomLevel = document.getElementById('img-zoom-level');
  const textZoomIn = document.getElementById('text-zoom-in');
  const textZoomOut = document.getElementById('text-zoom-out');
  const textZoomReset = document.getElementById('text-zoom-reset');
  const textZoomLevel = document.getElementById('text-zoom-level');
  const textWrap = document.querySelector('.text-wrap');
  const splitContainer = document.querySelector('.container');
  const splitter = document.getElementById('splitter');

  const view = { key: '', kind: 'none', base: '', count: 0, page: 1, file: '', box: null, boxPage: 0 };

  /* Per-pane zoom state. Left = font scale, right = image width scale.
     Ctrl+wheel over a pane zooms that pane only (and suppresses the
     browser's whole-page zoom); plain wheel keeps scrolling. */
  const BASE_FONT = 1.05;
  let textZoom = 1;
  let imgZoom = 1;
  const IMG_MIN = 1, IMG_MAX = 5;

  function isImageView() {
    return (view.kind === 'image' || view.kind === 'page' || view.kind === 'pages')
      && img.style.display !== 'none';
  }

  function applyImgZoom() {
    if (!isImageView()) { imgWrap.classList.remove('zoomed'); return; }
    if (imgZoom <= 1.01) {
      zoomInner.style.width = '';
      imgWrap.classList.remove('zoomed');
    } else {
      const baseW = Math.max(imgWrap.clientWidth, 50);
      zoomInner.style.width = (baseW * imgZoom) + 'px';
      imgWrap.classList.add('zoomed');
    }
    updateZoomUI();
  }

  function resetImgZoom() {
    imgZoom = 1;
    if (imgWrap) { imgWrap.scrollTop = 0; imgWrap.scrollLeft = 0; }
    applyImgZoom();
  }

  function updateZoomUI() {
    textZoomLevel.textContent = Math.round(textZoom * 100) + '%';
    imgZoomLevel.textContent = Math.round(imgZoom * 100) + '%';
    const imgView = isImageView();
    imgZoomBar.classList.toggle('visible', imgView);
    imgZoomIn.disabled = !imgView || imgZoom >= IMG_MAX - 1e-9;
    imgZoomOut.disabled = !imgView || imgZoom <= IMG_MIN + 1e-9;
    imgZoomReset.disabled = !imgView;
  }

  function hideAll() {
    img.style.display = 'none';
    imgWrap.style.display = 'none';
    obj.style.display = 'none';
    emptyState.style.display = 'none';
    missingState.style.display = 'none';
    linkState.style.display = 'none';
    box.style.display = 'none';
    nav.classList.remove('visible');
  }

  function setBox() {
    if (view.box && view.page === view.boxPage) {
      const [x, y, w, h] = view.box.split(',').map(Number);
      box.style.left = (x * 100) + '%';
      box.style.top = (y * 100) + '%';
      box.style.width = (w * 100) + '%';
      box.style.height = (h * 100) + '%';
      box.style.display = 'block';
    } else {
      box.style.display = 'none';
    }
  }

  function setPage(page) {
    view.page = Math.min(Math.max(page, 1), view.count);
    imgWrap.style.display = 'block';
    img.style.display = 'block';
    img.src = view.base + '-' + view.page + '.png';
    pageLabel.textContent = view.page + ' / ' + view.count;
    prevBtn.disabled = view.page <= 1;
    nextBtn.disabled = view.page >= view.count;
    setBox();
    applyImgZoom();
  }

  function chipText(side, title, suffix) {
    chip.textContent = '';
    const strong = document.createElement('strong');
    strong.textContent = side + ':';
    chip.append(strong, ' ' + title + (suffix || ''));
  }

  /* ---------------------------------------------------------------
   * 3. Show the source that belongs to one section.
   * ------------------------------------------------------------- */
  function show(section) {
    const d = section.dataset;
    const key = [d.idx, d.kind, d.src || '', d.base || '', d.file || '',
                 d.page || '', d.box || '', d.title || ''].join('|');
    if (key === view.key) return;
    view.key = key;

    hideAll();
    imgZoom = 1;
    zoomInner.style.width = '';
    imgWrap.classList.remove('zoomed');
    imgWrap.scrollTop = 0; imgWrap.scrollLeft = 0;
    const side = d.side === 'ref' ? 'Reference' : 'Source Note';

    switch (d.kind) {
      case 'image': {
        view.kind = 'image';
        view.count = 1;
        view.page = 1;
        view.file = '';
        view.box = d.box || null;
        view.boxPage = 1;
        imgWrap.style.display = 'block';
        img.src = d.src;
        img.style.display = 'block';
        setBox();
        chipText(side, d.title, d.box ? ' (highlighted region)' : '');
        break;
      }
      case 'page': {
        // A single rasterized page of a reference PDF.
        view.kind = 'page';
        view.count = 1;
        view.page = Number(d.page) || 1;
        view.file = d.file || '';
        view.box = d.box || null;
        view.boxPage = view.page;
        imgWrap.style.display = 'block';
        img.src = d.src;
        img.style.display = 'block';
        setBox();
        chipText(side, d.title, ' - page ' + view.page + ' / ' + (d.total || '?'));
        break;
      }
      case 'pages': {
        // Every page of a source PDF was rasterized: browsable + box overlay.
        view.kind = 'pages';
        view.base = d.base;
        view.count = Number(d.count) || 1;
        view.file = d.file || '';
        view.box = d.box || null;
        view.boxPage = Number(d.page) || 1;
        img.style.display = 'block';
        nav.classList.add('visible');
        setPage(view.boxPage);
        chipText(side, d.title);
        break;
      }
      case 'doc': {
        // Whole reference book in the browser's native PDF viewer.
        view.kind = 'doc';
        view.count = 0;
        view.page = 1;
        view.file = d.file;
        view.box = null;
        if (obj.getAttribute('data') !== d.file) obj.setAttribute('data', d.file);
        obj.style.display = 'block';
        chipText(side, d.title);
        break;
      }
      case 'link': {
        view.kind = 'link';
        linkState.textContent = '';
        const anchor = document.createElement('a');
        anchor.href = d.file;
        anchor.target = '_blank';
        anchor.rel = 'noopener';
        anchor.textContent = 'Open ' + d.title;
        linkState.append(anchor);
        linkState.style.display = 'block';
        chipText(side, d.title);
        break;
      }
      case 'missing': {
        view.kind = 'missing';
        missingState.textContent = 'File not found: ' + d.title;
        missingState.style.display = 'block';
        chip.className = 'ref-text missing';
        chip.textContent = 'Missing file: ' + d.title;
        updateZoomUI();
        return;
      }
      default: {
        // Section without a linked source.
        view.kind = 'none';
        emptyState.textContent = 'This section has no linked source.';
        emptyState.style.display = 'block';
        chip.className = 'ref-text';
        chip.textContent = 'No source linked.';
        updateZoomUI();
        return;
      }
    }

    chip.className = 'ref-text ' + (d.side === 'ref' ? 'reference' : 'source');
    updateZoomUI();
  }

  /* ---------------------------------------------------------------
   * 4. Wire up hover + page navigation.
   * ------------------------------------------------------------- */
  wrappers.forEach(wrapper => {
    wrapper.addEventListener('mouseenter', () => {
      wrappers.forEach(w => w.classList.remove('active'));
      wrapper.classList.add('active');
      show(wrapper);
    });
  });
  prevBtn.addEventListener('click', () => setPage(view.page - 1));
  nextBtn.addEventListener('click', () => setPage(view.page + 1));

  /* ---------------------------------------------------------------
   * 5. Per-pane zoom + cursor-driven frame. Page nav, click-to-open
   *    overlay, hover sync and box overlay are unchanged; the old
   *    flash-on-hover is gone, the frame now follows the cursor side.
   * ------------------------------------------------------------- */
  // Left pane: Ctrl+wheel scales the transcribed-notes font.
  textPane.addEventListener('wheel', (e) => {
    if (!e.ctrlKey && !e.metaKey) return;
    e.preventDefault();
    textZoom = Math.min(2.0, Math.max(0.7, textZoom * (e.deltaY < 0 ? 1.1 : 0.9)));
    textPane.style.fontSize = (BASE_FONT * textZoom).toFixed(3) + 'rem';
    updateZoomUI();
  }, { passive: false });
  textPane.addEventListener('dblclick', () => {
    textZoom = 1;
    textPane.style.fontSize = '';
    updateZoomUI();
  });

  // Right pane: Ctrl+wheel anywhere inside the viewer frame (image or the
  // white space between frame and image) scales the page image (1x..5x).
  // Plain wheel scrolls the zoomed image; drag-to-pan works when zoomed.
  container.addEventListener('wheel', (e) => {
    if (!isImageView()) return;
    if (!e.ctrlKey && !e.metaKey) return;
    e.preventDefault();
    imgZoom = Math.min(IMG_MAX, Math.max(IMG_MIN, imgZoom * (e.deltaY < 0 ? 1.15 : 0.87)));
    applyImgZoom();
  }, { passive: false });
  imgWrap.addEventListener('dblclick', () => resetImgZoom());
  img.addEventListener('load', () => applyImgZoom());

  let panning = false, panX = 0, panY = 0, panL = 0, panT = 0;
  imgWrap.addEventListener('mousedown', (e) => {
    if (!imgWrap.classList.contains('zoomed')) return;
    panning = true;
    panX = e.clientX; panY = e.clientY;
    panL = imgWrap.scrollLeft; panT = imgWrap.scrollTop;
    imgWrap.classList.add('panning');
    e.preventDefault();
  });
  window.addEventListener('mousemove', (e) => {
    if (!panning) return;
    imgWrap.scrollLeft = panL - (e.clientX - panX);
    imgWrap.scrollTop = panT - (e.clientY - panY);
  });
  window.addEventListener('mouseup', () => {
    panning = false;
    imgWrap.classList.remove('panning');
  });

  // Left pane buttons: same steps as the wheel (x1.1 in, x0.9 out).
  textZoomIn.addEventListener('click', () => {
    textZoom = Math.min(2.0, textZoom * 1.1);
    textPane.style.fontSize = (BASE_FONT * textZoom).toFixed(3) + 'rem';
    updateZoomUI();
  });
  textZoomOut.addEventListener('click', () => {
    textZoom = Math.max(0.7, textZoom * 0.9);
    textPane.style.fontSize = (BASE_FONT * textZoom).toFixed(3) + 'rem';
    updateZoomUI();
  });
  textZoomReset.addEventListener('click', () => {
    textZoom = 1;
    textPane.style.fontSize = '';
    updateZoomUI();
  });

  // Right pane buttons: same steps as the wheel (x1.15 in, x0.87 out).
  imgZoomIn.addEventListener('click', () => {
    if (!isImageView()) return;
    imgZoom = Math.min(IMG_MAX, imgZoom * 1.15);
    applyImgZoom();
  });
  imgZoomOut.addEventListener('click', () => {
    if (!isImageView()) return;
    imgZoom = Math.max(IMG_MIN, imgZoom * 0.87);
    applyImgZoom();
  });
  imgZoomReset.addEventListener('click', () => resetImgZoom());

  // Gray/blue frame on the existing viewer border: blue while the cursor
  // is on the right side, gray otherwise.
  if (viewerPane) {
    viewerPane.addEventListener('mouseenter', () => container.classList.add('active-view'));
    viewerPane.addEventListener('mouseleave', () => container.classList.remove('active-view'));
  }

  /* ---------------------------------------------------------------
   * 6. Draggable split divider: drag to widen one pane at the expense
   *    of the other (clamped 15-85%); double-click resets to 50/50.
   * ------------------------------------------------------------- */
  let splitting = false;
  splitter.addEventListener('pointerdown', (e) => {
    splitting = true;
    splitter.classList.add('dragging');
    try { splitter.setPointerCapture(e.pointerId); } catch (_) {}
    document.body.style.userSelect = 'none';
    e.preventDefault();
  });
  splitter.addEventListener('pointermove', (e) => {
    if (!splitting) return;
    const rect = splitContainer.getBoundingClientRect();
    if (rect.width <= 0) return;
    const pct = Math.min(85, Math.max(15, (e.clientX - rect.left) / rect.width * 100));
    textWrap.style.flexBasis = pct.toFixed(2) + '%';
  });
  function endSplit() {
    splitting = false;
    splitter.classList.remove('dragging');
    document.body.style.userSelect = '';
  }
  splitter.addEventListener('pointerup', endSplit);
  splitter.addEventListener('pointercancel', endSplit);
  splitter.addEventListener('dblclick', () => {
    textWrap.style.flexBasis = '50%';
  });

  hideAll();
  const first = wrappers.find(w => w.dataset.kind && w.dataset.kind !== 'none') || wrappers[0];
  if (first) {
    first.classList.add('active');
    show(first);
  } else {
    emptyState.style.display = 'block';
  }
});
</script>
</body>
</html>
```
