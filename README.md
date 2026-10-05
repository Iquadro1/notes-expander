# AI Notes Expander

Local pipeline: handwritten math notes → transcribed Markdown with LaTeX → interactive split-view HTML synced with source pages.

Start here: `AGENTS.md` (agent workflow, Steps 0–5), `RUN_PIPELINE.md` (task prompt), `Plan.md` (architecture; code fences regenerated from `src/` via `uv run sync-docs`).

## CLI tools (`uv run <tool> --help`)

| Tool | Purpose |
|---|---|
| `extract-refs` | Build `db/index.json` from shared + per-course reference books/notes |
| `search-refs` | BM25 search (`--top_k`, `--json`, `--batch queries.txt`) |
| `export-notes` | Inbox scans → viewable PNGs in `/tmp/opencode` (`--list` to inspect) |
| `suggest-boxes` | Ink-gap midpoints for highlight-box edges (`<file> --page N`) |
| `new-lesson` | Scaffold `output/<course>/NN.md` from any inbox filename (`--from`, `--lang`) |
| `lint-md` | Same checks as render, no HTML (`--fix`, `--strict`) |
| `render-html` | Markdown → HTML viewer (`--strict` exits 1 on warnings) |
| `verify-html` | Freshness + assets + JS check + headless chromium hover test (`--no-browser`) |
| `archive-lesson` | Guarded `raw_notes/` → `processed_notes/` (needs fresh HTML) |
| `sync-docs` | Regenerate `Plan.md` code from `src/` + `templates/` (`--check` for CI) |

Typical lesson: `export-notes` → transcribe → `search-refs` → `new-lesson` → draft → `lint-md` → `render-html --strict` → `verify-html` → `archive-lesson`.

Browser check needs `chromium` and `puppeteer-core` (`npm i puppeteer-core` where `scripts/verify-hover.js` can require it); without them `verify-html` runs static checks and reports SKIP.
