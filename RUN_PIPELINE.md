# Process New Notes Workflow

Hello AI! Please execute the **Runtime Execution Pipeline** (Phase 2) as defined in `AGENTS.md`.

## Task Instructions:
1. **Check the Inbox**: List the contents of the `data/raw_notes/` directory.
2. **Evaluate State**: 
   - If the folder is empty, simply reply with "No new notes to process." and end your turn.
   - If there are images present, begin processing them following the strict 5-step sequence in `AGENTS.md` (Ingestion, RAG Search, Drafting, Rendering, Archiving).
3. **Important Reminder for Step 5**: Make sure you actually execute the `mv` command to move the images from `data/raw_notes/` to `data/processed_notes/` when you are done so they aren't processed again next time.
