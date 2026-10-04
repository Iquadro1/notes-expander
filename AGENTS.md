# AI Notes Expander - System Instructions

## Project Overview
The **AI Notes Expander** is a local Python-based pipeline designed to help you, the AI agent, transcribe handwritten mathematical notes, retrieve contextual expansions from PDF textbooks via a local BM25 search database, and generate an interactive HTML document that synchronizes the transcribed text with its source images.

**Key Features of the Pipeline:**
- **Agent-Driven Transcription:** You use your multimodal vision to read and transcribe handwritten math notes accurately.
- **Local RAG Integration:** You can search a local index of textbooks (`uv run search-refs`) to fetch formal theorems or definitions to expand the notes.
- **Source Synchronization UI:** Custom Markdown shortcodes (`[source: ...]`, `[ref: ...]`) that are parsed into an interactive split-screen web view where text scrolling updates a dynamic image/reference viewer.
- **LaTeX Math Rendering:** Complete support for $ and $$ LaTeX math equations.

You are the orchestration engine for this project. Your function is twofold: first, build the local CLI infrastructure (if it is missing), and second, act as the primary processor for all mathematical notes.

---

## Phase 1: Construction (If project is empty)
If the user provides an empty workspace, you must build the infrastructure:
1. Initialize the project using `uv init`.
2. Add dependencies: `pymupdf`, `rank_bm25`, `markdown`, `jinja2`.
3. Create the directory structure: `data/raw_notes`, `data/processed_notes`, `data/reference_books`, `data/reference_notes`, `src`, `templates`, `output`, `db`.
4. Read `Plan.md` to understand the architecture and retrieve the source code.
5. Write the scripts (`src/extract.py`, `src/search.py`, `src/render.py`) and the template (`templates/layout.html`) using the code provided in `Plan.md`.
6. Update `pyproject.toml` with the tool entry points.
7. Run `uv run extract-refs` if any reference PDFs exist in `data/reference_books/` to build the initial search index.

---

## Phase 2: Runtime Execution Pipeline
When a user requests you to process new mathematical notes, execute the following strict sequence.

### Step 1: Ingestion & Vision
Read the image files located in `data/raw_notes/` using your native multimodal vision capabilities. Extract theorems, definitions, proofs, and raw equations.

### Step 2: Mathematical Context Retrieval
Identify logical gaps, abbreviated concepts, or sketched proofs in the handwritten mathematical notes.
Open the terminal and execute the search utility to find formalized definitions or proofs from the reference library:
```bash
uv run search-refs "Cauchy-Riemann equations"
```
Read the standard output. Mentally incorporate the formal definitions and rigorous proofs found in the references to expand the abbreviated handwritten notes.

### Step 3: Drafting the Output (`output/notes_name.md`)
Write a complete Markdown document combining the transcription and the retrieved references. Adhere strictly to the following formatting requirements:

*   **Synchronization Tags:** 
    *   Insert `[source: filename.ext]` on a new line *before* transcribing content from a specific raw note image.
    *   Insert `[ref: filename.ext]` on a new line *before* writing expanded content sourced from a textbook or reference note.
*   **Mathematical Notation:** Use LaTeX environments exclusively.
    *   Use `$` for inline variables and equations (e.g., $f(z) = u(x,y) + iv(x,y)$).
    *   Use `$$` for block equations and step-by-step derivations.
*   **Structure:** Use standard Markdown headers for Theorems, Lemmas, Proofs, and Definitions.

**Example Output:**
```markdown
[source: calc_lecture_01.jpg]
# Continuity and Limits
The notes indicate a basic definition of continuity at a point $x_0$. 

[ref: spivak_calculus.pdf]
Formally, a function $f$ is continuous at $x_0$ if for every $\epsilon > 0$, there exists a $\delta > 0$ such that:
$$ |x - x_0| < \delta \implies |f(x) - f(x_0)| < \epsilon $$

[source: calc_lecture_02.jpg]
## Proof of Theorem 1
Let $f(x)$ be defined as...
```

### Step 4: Rendering
After generating and saving the `.md` file, compile the final user interface by running:
```bash
uv run render-html output/notes_name.md
```
Verify the output HTML file exists in the `output/` directory.

### Step 5: Archiving
Once the rendering is complete, run a terminal command to move the transcribed image file(s) from `data/raw_notes/` to `data/processed_notes/`. Inform the user that the processing is complete.