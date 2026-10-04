# AI Notes Expander

## Project Description
The **AI Notes Expander** is an agent-driven, local pipeline designed to transform raw, handwritten mathematical notes into comprehensive, well-formatted digital documents. Instead of relying on traditional, error-prone OCR like Tesseract, this project leverages advanced AI agents (like Google Antigravity) with native vision capabilities to read handwritten notes. 

The system acts as a local Retrieval-Augmented Generation (RAG) tool. When the AI agent encounters abbreviated or unclear concepts or missing proofs in the handwritten notes, it uses built-in Python CLI tools to search a local vector/BM25 database of reference textbooks (PDFs) and past notes. The agent then synthesizes the transcribed notes with the retrieved formal definitions, outputting a complete Markdown document enriched with LaTeX mathematics. Finally, a rendering script converts this Markdown into an interactive, dual-pane HTML interface that synchronizes the expanded text with the original source images and reference context as the user scrolls.

## Key Features
*   **Agent-Native Transcription:** Bypasses standard OCR by utilizing the AI agent's multimodal vision to accurately parse complex handwritten mathematical notation.
*   **Local RAG Context Retrieval:** Uses `pymupdf` and `rank_bm25` to index and search local PDF textbooks, allowing the agent to pull formal definitions without sending entire books to an LLM.
*   **Markdown + LaTeX Support:** Full support for mathematical formatting using MathJax ($ for inline, $$ for block equations).
*   **Custom Synchronization Syntax:** Uses lightweight shortcodes (`[source: image.jpg]` and `[ref: book.pdf]`) to link text sections to their visual origins.
*   **Interactive Dual-Pane UI:** A custom HTML/JS renderer that uses the `IntersectionObserver` API to dynamically update an image viewer pane based on the user's scroll position in the text.
*   **Modular CLI Architecture:** Built with `uv` for fast dependency management, turning Python scripts into accessible terminal tools for the AI agent.

---

## Directory Structure

```text
ai-notes-expander/
├── pyproject.toml
├── AGENTS.md
├── data/
│   ├── raw_notes/        # Target note images to transcribe (Inbox queue)
│   ├── processed_notes/  # Successfully transcribed note images (Archive)
│   ├── reference_books/  # PDF textbooks
│   └── reference_notes/  # Previously transcribed notes (.md)
├── db/
│   └── index.json        # Serialized corpus for local search
├── src/
│   ├── __init__.py
│   ├── extract.py        # Parses PDFs and MD files to build index
│   ├── search.py         # BM25 search utility
│   └── render.py         # HTML generation and regex parsing
├── templates/
│   └── layout.html       # Jinja2 template with UI and MathJax
└── output/               # Final rendered .md and .html files
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
import os
import json
import fitz  # PyMuPDF
from pathlib import Path

def extract_pdf_chunks(pdf_path):
    doc = fitz.open(pdf_path)
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
```

### 3. Local Search Utility (`src/search.py`)
The AI agent uses this script to fetch context for mathematical expansions.

```python
import json
import argparse
import re
from pathlib import Path
from rank_bm25 import BM25Okapi

def main():
    parser = argparse.ArgumentParser(description="Search reference texts.")
    parser.add_argument("query", type=str, help="Mathematical concept to search")
    parser.add_argument("--top_k", type=int, default=3, help="Number of results")
    args = parser.parse_args()

    index_path = Path("db/index.json")
    if not index_path.exists():
        print("Index not found. Run extract-refs first.")
        return

    with open(index_path, "r", encoding='utf-8') as f:
        corpus = json.load(f)

    if not corpus:
        print("Corpus is empty.")
        return

    # Improved tokenizer: strips punctuation to improve BM25 matching
    tokenized_corpus = [re.findall(r'\w+', doc["text"].lower()) for doc in corpus]
    bm25 = BM25Okapi(tokenized_corpus)
    
    tokenized_query = re.findall(r'\w+', args.query.lower())
    top_n = bm25.get_top_n(tokenized_query, corpus, n=args.top_k)

    for i, doc in enumerate(top_n):
        print(f"\n--- Result {i+1} ---")
        print(f"Source: {doc['source']} | Page: {doc['page']}")
        print(f"Text:\n{doc['text']}\n")

if __name__ == "__main__":
    main()
```

### 4. Markdown Rendering UI (`src/render.py`)
Converts the agent's tagged Markdown into interactive HTML.

```python
import re
import argparse
from pathlib import Path
import markdown
from jinja2 import Environment, FileSystemLoader

def parse_markdown(md_text):
    html = re.sub(
        r'\[source:\s*(.+?)\]', 
        r'<div class="sync-marker" data-img="\1"></div>', 
        md_text
    )
    html = re.sub(
        r'\[ref:\s*(.+?)\]', 
        r'<div class="sync-marker ref-marker" data-ref="\1"></div>', 
        html
    )
    return markdown.markdown(html, extensions=['fenced_code', 'tables'])

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_file", type=str, help="Markdown file to render")
    args = parser.parse_args()

    input_path = Path(args.input_file)
    with open(input_path, "r", encoding="utf-8") as f:
        md_text = f.read()

    html_content = parse_markdown(md_text)

    env = Environment(loader=FileSystemLoader('templates'))
    template = env.get_template('layout.html')
    
    final_html = template.render(html_content=html_content)
    
    output_path = Path("output") / f"{input_path.stem}.html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(final_html)
        
    print(f"Rendered HTML saved to {output_path}")

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
<title>Notes Viewer</title>
<style>
  body { margin: 0; font-family: system-ui, -apple-system, sans-serif; line-height: 1.6; }
  .container { display: flex; height: 100vh; }
  .text-pane { width: 50%; padding: 2rem 4rem; overflow-y: auto; font-size: 1.1rem; }
  .viewer-pane { width: 50%; background: #f8f9fa; padding: 2rem; position: sticky; top: 0; display: flex; flex-direction: column; }
  .viewer-img { max-width: 100%; max-height: 80vh; object-fit: contain; box-shadow: 0 4px 12px rgba(0,0,0,0.1); border-radius: 4px; }
  .sync-marker { height: 1px; margin: 2rem 0; }
  .ref-text { margin-top: 1rem; padding: 1rem; background: #e9ecef; border-radius: 4px; font-family: monospace; }
</style>
<script>
  MathJax = {
    tex: { inlineMath: [['$', '$'], ['\\(', '\\)']], displayMath: [['$$', '$$'], ['\\[', '\\]']] }
  };
</script>
<script src="https://polyfill.io/v3/polyfill.min.js?features=es6"></script>
<script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
</head>
<body>
<div class="container">
  <div class="text-pane">
    {{ html_content }}
  </div>
  <div class="viewer-pane">
    <img id="primary-viewer" class="viewer-img" src="" alt="Source Note Image">
    <div id="ref-viewer-text" class="ref-text">Awaiting synchronization...</div>
  </div>
</div>
<script>
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        if (entry.target.dataset.img) {
          document.getElementById('primary-viewer').src = `../data/raw_notes/${entry.target.dataset.img}`;
          document.getElementById('ref-viewer-text').innerText = `Source Image: ${entry.target.dataset.img}`;
        }
        if (entry.target.dataset.ref) {
          document.getElementById('ref-viewer-text').innerText = `Reference Context: ${entry.target.dataset.ref}`;
        }
      }
    });
  }, { root: document.querySelector('.text-pane'), rootMargin: '-50% 0px -50% 0px' });
  
  document.querySelectorAll('.sync-marker').forEach(marker => observer.observe(marker));
</script>
</body>
</html>
```