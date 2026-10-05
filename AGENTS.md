# AI Notes Expander - System Instructions

## Project Overview
The **AI Notes Expander** is a local Python-based pipeline designed to help you, the AI agent, transcribe handwritten mathematical notes, retrieve contextual expansions from PDF textbooks via a local BM25 search database, and generate an interactive HTML document that synchronizes the transcribed text with its source images.

**Key Features of the Pipeline:**
- **Agent-Driven Transcription:** You use your multimodal vision to read and transcribe handwritten math notes accurately (from image files *or* scanned PDFs placed in the active course's `raw_notes/` folder).
- **Local RAG Integration:** You can search a local index of textbooks (`uv run search-refs`) to fetch formal theorems or definitions to expand the notes.
- **Source Synchronization UI:** Custom Markdown shortcodes (`[source: ...]`, `[ref: ...]`) that are parsed into an interactive split-screen web view. The left pane holds the rewritten notes; hovering a section instantly shows the corresponding source page in the right pane and **draws a highlighted box around the exact region** that section was transcribed from.
- **Page-level linking:** Shortcodes accept `#page=N` (which page of a PDF) and `&box=x,y,w,h` (which region of that page) so the link is precise, not just "this file".
- **Rasterized viewers:** `render-html` exports PDF pages to `output/<course>/assets/<stem>/page-N.png` automatically, because a native PDF plugin cannot be overlaid with a highlight box.
- **LaTeX Math Rendering:** Complete support for `$` and `$$` LaTeX math equations (rendered by MathJax).
- **Multi-Course Workspaces:** every course lives in `data/courses/<slug>/` with its own inbox, archive, and `output/<slug>/` folder; a one-line `ACTIVE_COURSE` file in the project root tells you — and the renderer — which course is being processed right now.
- **Language Fidelity:** The rendered document is written **strictly in the language of the original notes**, no matter what language the reference books are in — reference material is translated/paraphrased into the notes' language.

You are the orchestration engine for this project. Your function is twofold: first, build the local CLI infrastructure (if it is missing), and second, act as the primary processor for all mathematical notes.

---

## Phase 1: Construction (If project is empty)
If the user provides an empty workspace, you must build the infrastructure:
1. Initialize the project using `uv init`.
2. Add dependencies: `pymupdf`, `rank_bm25`, `markdown`, `jinja2`.
3. Create the directory structure: `data/courses/<slug>/raw_notes`, `data/courses/<slug>/processed_notes` (for the first course), `data/reference_books`, `data/reference_notes`, `src`, `templates`, `output`, `db`, plus an `ACTIVE_COURSE` file containing that course's slug and a `data/courses/<slug>/course.txt` file containing the course display name (one line, e.g. `Elementi di Topologia Algebrica` — every lesson document starts with it as H1).
4. Read `Plan.md` to understand the architecture and retrieve the source code.
5. Write the scripts (`src/extract.py`, `src/search.py`, `src/render.py`) and the template (`templates/layout.html`) using the code provided in `Plan.md`.
6. Update `pyproject.toml` with the tool entry points (`extract-refs`, `search-refs`, `render-html`).
7. Add `output/*/assets/` to `.gitignore` (generated page images) and run `uv run extract-refs` if any reference PDFs exist in `data/reference_books/` to build the initial search index.

---

## Phase 2: Runtime Execution Pipeline
When a user requests you to process new mathematical notes, execute the following strict sequence.

### Step 0: Resolve the Active Course
Read the course slug from the `ACTIVE_COURSE` file in the project root (first non-comment line; it names a directory under `data/courses/`). Every path below derives from it (`<course>` = that slug):
- **inbox:** `data/courses/<course>/raw_notes/`
- **archive:** `data/courses/<course>/processed_notes/`
- **output:** `output/<course>/`

If the file is missing or names a non-existent course, list `data/courses/` and ask the user which course to work on — never guess, and never mix files from two courses in one document. Switching courses later = editing that one line in `ACTIVE_COURSE`.

### Step 1: Ingestion & Vision
Read the note files located in the active course's inbox (`data/courses/<course>/raw_notes/`) using your native multimodal vision capabilities and extract theorems, definitions, proofs, and raw equations.

- **Image files (`.jpg`, `.png`, …):** view them directly. Remember which image each section came from, and estimate its **bounding box** (see "Bounding boxes" below).
- **Scanned PDFs (`.pdf`):** export every page to PNG first so you can see them (replace `<course>` with the slug from `ACTIVE_COURSE`), e.g.:
  ```bash
  uv run python -c "import pymupdf; d=pymupdf.open('data/courses/<course>/raw_notes/01.pdf'); [p.get_pixmap(matrix=pymupdf.Matrix(2,2), alpha=False).save(f'/tmp/opencode/01_page-{i+1}.png') for i,p in enumerate(d)]"
  ```
  Then view each PNG. **Track the 1-based page number** of every section you transcribe.

**Language detection:** first determine which language the notes are written in (e.g. Italian). That language is **mandatory for the entire output** of Step 3 — headings, prose, and reference expansions alike.

**Bounding boxes:** while transcribing, estimate where each section sits on the page:
`box = x,y,w,h` — left/top/width/height as **fractions of the page width/height (0–1), origin at the top-left**.
Round to 2 decimals. If you cannot estimate reliably, omit the box — the viewer still shows the correct page (just without the box).

**Box convention (mandatory — this is where past runs failed):**
- **Full width:** always `x=0, w=1`. The viewer draws a thin outline *inside* the rectangle, so an inset box leaves part of the line outside the highlight while its side borders can clip edge writing.
- **Top/bottom edges in blank gaps:** the box must cover the section's *whole* height, with its top edge in the blank gap *above* the section's first ink line and its bottom edge in the blank gap *below* its last ink line — never across handwriting. A border drawn through a text line visibly strikes through the writing.
- **How to place edges reliably:** after exporting the page PNGs, measure the ink bands (e.g. with a small script that counts dark/saturated pixels per row) and put each edge in the middle of the gap between two bands. Neighboring sections share the gap: one's bottom edge and the next one's top edge both sit inside it.
- **Self-check:** `render-html` scans the rasterized page around every box edge and prints `WARNING: [file] box <edge> border crosses ink` when an edge hits writing — fix the coordinates and re-render until it is silent.

### Step 2: Mathematical Context Retrieval
Identify logical gaps, abbreviated concepts, or sketched proofs in the handwritten mathematical notes.
Open the terminal and execute the search utility to find formalized definitions or proofs from the reference library:
```bash
uv run search-refs "Cauchy-Riemann equations"
```
Read the standard output (it includes the **source page number** of each hit) and mentally incorporate the formal definitions and rigorous proofs found in the references to expand the abbreviated handwritten notes.

### Step 3: Drafting the Output (`output/<course>/notes_name.md`)
Write a complete Markdown document combining the transcription and the retrieved references. Adhere strictly to the following formatting contract — the renderer and the UI depend on it:

**0. Document header (strict):** every lesson document starts with the course display name as the H1, followed within a couple of lines by a subtitle carrying the lesson number **in the notes' language**:
```markdown
[source: 01.pdf#page=1&box=0,0,1,0.4]
# Elementi di Topologia Algebrica
## Lezione 1
```
- The H1 is exactly the content of `data/courses/<course>/course.txt` (create that file when a course has none yet — one line, the display name). The renderer warns when the header is wrong, and uses the H1 as the HTML `<title>`.
- The subtitle is localized: `Lezione 1` for Italian notes, `Lesson 1` for English notes, etc. — it always ends with the lesson number.

**1. Language (strict):** write everything **in the original notes' language**. The reference books are often in English (or another language) — do **not** copy their language: translate/paraphrase the formal definitions and proofs into the notes' language. Keep only proper names (`Munkres`), established notation/commands (`diagram chasing` if the notes themselves use it), and terms the original notes already write in another language.

**2. Synchronization tags (the viewer groups text by tags):**
- `[source: filename]` opens a new *source* section; `[ref: filename]` opens a new *reference* section. Everything up to the **next** tag belongs to the previous one.
- Insert a `[source: ...]` tag **before every contiguous chunk of transcribed notes** — not just once at the top. Whenever the page changes, emit a new tag with the new page. If you emit only one tag at the top, all later note sections will be grouped under the first `[ref:]` and hovering them will show the textbook instead of your notes.
- Full syntax: `[source: notes.pdf#page=2&box=0,0.3,1,0.15]`
  - `#page=N` — 1-based page of a multi-page source (strongly recommended for PDFs).
  - `&box=x,y,w,h` — highlight region on that page: always full-width (`x=0, w=1`), top/bottom edges in the blank gaps between lines (see Step 1). The renderer warns when a border crosses ink.
- Reference tags: always include the page from `search-refs`: `[ref: book.pdf#page=42]` (rendered as a crisp page image; without `#page` the whole book is embedded instead).

**3. Markdown hygiene (the renderer normalizes what it can, but do it right):**
- Put a **blank line before and after every shortcode** and **before and after every list** (the renderer inserts them if you forget, but be consistent).
- `$...$` for inline math, `$$...$$` for block math. Use LaTeX environments exclusively for math.
- Prose `_` or `*` (e.g. `Top_*`, `H_*`) must be **escaped** (`Top\_*`, `H\_*`) **or written as math** (`$Top_*$`). Never write three consecutive unescaped asterisks (`**Top_***`) — Markdown cannot parse it; write `**Top\_\***` instead. The renderer warns about this.
- In `cases`/`aligned` environments, use `\\` for row breaks.

**Structure:** use standard Markdown headers for Theorems, Lemmas, Proofs, and Definitions.

**Example Output** (the notes here are in Italian, so the whole document is Italian — the output language always follows the original notes, never the reference book's language; note the course-name header + `Lezione N` subtitle, and the full-width boxes):
```markdown
[source: calc_lezione_01.jpg#box=0,0.06,1,0.35]
# Analisi 1
## Lezione 1

## Continuità e limiti
Le note indicano la definizione base di continuità in un punto $x_0$.

[ref: spivak_calculus.pdf#page=51]
Formalmente, una funzione $f$ è continua in $x_0$ se per ogni $\epsilon > 0$ esiste un $\delta > 0$ tale che:
$$ |x - x_0| < \delta \implies |f(x) - f(x_0)| < \epsilon $$

[source: calc_lezione_02.pdf#page=2&box=0,0.12,1,0.4]
## Dimostrazione del Teorema 1
Sia $f(x)$ definita come...
```

### Step 4: Rendering
After generating and saving the `.md` file, compile the final user interface by running:
```bash
uv run render-html output/<course>/notes_name.md
```
The renderer reads `ACTIVE_COURSE` itself (override with `--course <slug>` if needed). Then **verify**:
- The command prints **no WARNING lines** (fix the `.md` and re-render if it does).
- The output HTML exists and is **newer than `templates/layout.html` and `src/render.py`** — if you edited the template or renderer, you must re-render, otherwise the browser shows a stale build (this exact bug happened before).
- Preview/open `output/<course>/notes_name.html` and confirm the split view works: hovering a section shows the right page and the highlight box lands on the transcribed region.

### Step 5: Archiving
Once the rendering is complete, move the transcribed source file(s) from the course inbox to its archive so they are not processed again:
```bash
mv data/courses/<course>/raw_notes/01.pdf data/courses/<course>/processed_notes/
```
This is safe **after** rendering: the renderer resolves source paths across both of the active course's directories, so future re-renders still find the files. Inform the user that the processing is complete.
