# Process New Notes Workflow

Hello AI! Please execute the **Runtime Execution Pipeline** (Phase 2) as defined in `AGENTS.md`.

## Task Instructions:
1. **Resolve the active course**: read the course slug from the `ACTIVE_COURSE` file in the project root. Every path below derives from it (`<course>` = slug). If the file is missing or names a non-existent directory under `data/courses/`, ask the user which course to work on — never guess, and never mix two courses in one document.
2. **Check the Inbox**: List the contents of `data/courses/<course>/raw_notes/` (it may contain images **or** scanned PDFs).
3. **Evaluate State**: 
   - If the folder is empty, simply reply with "No new notes to process." and end your turn.
   - If notes are present, begin processing them following the strict sequence in `AGENTS.md` (Steps 0–5: Course resolution, Ingestion, RAG Search, Drafting, Rendering, Archiving).
4. **Drafting reminders** (full contract in AGENTS.md Step 3):
   - **Header (strict):** start with `# <course name>` (exactly `data/courses/<course>/course.txt`) then a localized lesson subtitle (`## Lezione N` for Italian notes, `## Lesson N` for English, …). The renderer warns otherwise and uses the H1 as the HTML title.
   - **Language (strict):** write the whole document in the language of the original notes — translate any reference material (English textbooks, etc.) into it; keep only proper names, notation, and terms the notes themselves use.
   - Emit a `[source: file#page=N&box=0,Y,1,H]` tag **before every section** of the notes (not just once at the top), with the 1-based page number and a **full-width** box whose top/bottom edges sit in the blank gaps between handwriting lines (never across ink). `render-html` warns (`box <edge> border crosses ink`) when an edge hits writing — fix and re-render until silent.
   - Emit `[ref: book.pdf#page=N]` with the page returned by `search-refs`.
   - Blank line before/after every tag and list; escape `_`/`*` in prose or write them as math.
5. **Rendering reminder (AGENTS.md Step 4)**: run `uv run render-html output/<course>/<name>.md` (the renderer reads `ACTIVE_COURSE` itself), confirm it prints **no WARNINGs**, and confirm the HTML file is newer than `templates/layout.html`. Never show a stale build.
6. **Archiving reminder (AGENTS.md Step 5)**: make sure you actually execute the `mv` command to move the images/PDFs from `data/courses/<course>/raw_notes/` to `data/courses/<course>/processed_notes/` when you are done so they aren't processed again next time.

**To switch courses**: edit `ACTIVE_COURSE` to the new slug (create `data/courses/<slug>/{raw_notes,processed_notes}` first if the course doesn't exist yet). Output from other courses stays untouched in `output/<slug>/`.
