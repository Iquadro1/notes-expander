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
