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
