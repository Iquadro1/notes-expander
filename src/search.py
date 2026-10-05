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
