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
def warn(message: str) -> None:
    print(f"  WARNING: {message}")


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
    args = parser.parse_args()

    global SKIP_EXPORT
    SKIP_EXPORT = args.skip_export
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


if __name__ == "__main__":
    main()
