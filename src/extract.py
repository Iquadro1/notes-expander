import os
import json
import pymupdf
from pathlib import Path

def extract_pdf_chunks(pdf_path):
    doc = pymupdf.open(pdf_path)
    chunks = []
    
    for page_num, page in enumerate(doc):
        # Extract by blocks (paragraphs) to maintain semantic context better than naive word counts
        blocks = page.get_text("blocks")
        for block in blocks:
            text = block[4].strip()
            if len(text) > 20: # filter out tiny artifacts
                chunks.append({
                    "source": os.path.basename(pdf_path),
                    "page": page_num + 1,
                    "text": text
                })
    return chunks

def extract_md_chunks(md_path):
    with open(md_path, 'r', encoding='utf-8') as f:
        paragraphs = f.read().split('\n\n')
    
    return [{
        "source": os.path.basename(md_path),
        "page": "N/A",
        "text": p.strip()
    } for p in paragraphs if len(p.strip()) > 20]

def main():
    db_path = Path("db")
    db_path.mkdir(exist_ok=True)
    corpus = []
    
    pdf_dir = Path("data/reference_books")
    if pdf_dir.exists():
        for pdf_file in pdf_dir.glob("*.pdf"):
            corpus.extend(extract_pdf_chunks(pdf_file))
            
    notes_dir = Path("data/reference_notes")
    if notes_dir.exists():
        for md_file in notes_dir.glob("*.md"):
            corpus.extend(extract_md_chunks(md_file))
            
    with open(db_path / "index.json", "w", encoding='utf-8') as f:
        json.dump(corpus, f, indent=2)
    print(f"Indexed {len(corpus)} chunks.")

if __name__ == "__main__":
    main()
