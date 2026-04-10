"""
eval_stage_a.py

Stage A evaluation: compares retrieval quality of BM25 and
5 embedding-based search methods using Precision@K, Recall@K,
F1@K, and NDCG@K metrics.

Retrieval methods evaluated:
  - BM25                  : keyword search on readme_summary field
  - embedding             : repo-level embedding (3072 dims, code+doc+req+readme)
  - embedding_code        : code-level embedding (768 dims)
  - embedding_doc         : doc-level embedding (768 dims)
  - embedding_requirement : requirement-level embedding (768 dims)
  - embedding_readme      : readme-level embedding (768 dims)

Ground truth: repos sharing the same category as the reference repo.
If a reference repo belongs to multiple categories, ground truth is
the union of all repos in those categories.

Usage:
  python eval_stage_a.py
"""

from __future__ import annotations

import math
import pickle
from collections import defaultdict
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from elasticsearch import Elasticsearch
from tqdm import tqdm

from config import ES_URL, ES_API_KEY, INDEX, PKL_PATH, K_VALUES, REFERENCE_REPOS

load_dotenv()

RESULTS_DIR = Path("results")
RESULTS_DIR.mkdir(exist_ok=True)

# Retrieval methods: (method_name, es_field)
RETRIEVAL_METHODS = [
    ("BM25", None),
    ("embedding", "embedding"),
    ("embedding_code", "embedding_code"),
    ("embedding_doc", "embedding_doc"),
    ("embedding_requirement", "embedding_requirement"),
    ("embedding_readme", "embedding_readme"),
]

# ── ES client ─────────────────────────────────────────────────────────────────


def get_es_client() -> Elasticsearch:
    return Elasticsearch(ES_URL, api_key=ES_API_KEY)


# ── Retrieval ─────────────────────────────────────────────────────────────────


def bm25_search(es: Elasticsearch, query_text: str, topk: int, exclude_id: str) -> list[str]:
    """BM25 keyword search on readme_summary field."""
    resp = es.search(index=INDEX,
                     body={
                         "query": {
                             "bool": {
                                 "must": {
                                     "match": {
                                         "readme_summary": query_text
                                     }
                                 },
                                 "must_not": {
                                     "term": {
                                         "_id": exclude_id
                                     }
                                 }
                             }
                         },
                         "size": topk,
                         "_source": False,
                     })
    return [hit["_id"] for hit in resp["hits"]["hits"]]


def embedding_search(es: Elasticsearch, query_vector: list[float], field: str, topk: int, exclude_id: str) -> list[str]:
    """Cosine similarity search on a dense_vector field."""
    resp = es.search(index=INDEX,
                     body={
                         "query": {
                             "script_score": {
                                 "query": {
                                     "bool": {
                                         "must": {
                                             "exists": {
                                                 "field": field
                                             }
                                         },
                                         "must_not": {
                                             "term": {
                                                 "_id": exclude_id
                                             }
                                         }
                                     }
                                 },
                                 "script": {
                                     "source": f"cosineSimilarity(params.query_vector, '{field}') + 1.0",
                                     "params": {
                                         "query_vector": query_vector
                                     }
                                 }
                             }
                         },
                         "size": topk,
                         "_source": False,
                     })
    return [hit["_id"] for hit in resp["hits"]["hits"]]


# ── Metrics ───────────────────────────────────────────────────────────────────


def precision_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    top_k = retrieved[:k]
    return len([r for r in top_k if r in relevant]) / k if k > 0 else 0.0


def recall_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    if not relevant:
        return 0.0
    top_k = retrieved[:k]
    return len([r for r in top_k if r in relevant]) / len(relevant)


def f1_at_k(precision: float, recall: float) -> float:
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def ndcg_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    top_k = retrieved[:k]
    dcg = sum(1.0 / math.log2(i + 2) for i, r in enumerate(top_k) if r in relevant)
    ideal_hits = min(len(relevant), k)
    idcg = sum(1.0 / math.log2(i + 2) for i in range(ideal_hits))
    return dcg / idcg if idcg > 0 else 0.0


# ── Main ──────────────────────────────────────────────────────────────────────


def main():
    es = get_es_client()
    print(f"ES: {es.info()['version']['number']}")

    # Load category mapping: {repo_id: [category, ...]}
    with open(PKL_PATH, "rb") as f:
        repos_dict = pickle.load(f)

    # Build category -> {repo_ids} mapping
    cat_repos = defaultdict(set)
    for repo_id, cats in repos_dict.items():
        for cat in cats:
            cat_repos[cat].add(repo_id)

    max_k = max(K_VALUES)
    all_rows = []

    for ref_repo in tqdm(REFERENCE_REPOS, desc="Evaluating"):

        # Ground truth: union of all repos in the same categories
        ref_cats = repos_dict.get(ref_repo, [])
        relevant = set()
        for cat in ref_cats:
            relevant.update(cat_repos[cat])
        relevant.discard(ref_repo)

        if not relevant:
            tqdm.write(f"  [SKIP] {ref_repo} — no relevant repos found")
            continue

        # Fetch reference repo document from ES
        try:
            doc = es.get(index=INDEX, id=ref_repo)["_source"]
        except Exception as e:
            tqdm.write(f"  [ERROR] {ref_repo} — ES fetch failed: {e}")
            continue

        query_text = doc.get("readme_summary", "")

        for method_name, field in RETRIEVAL_METHODS:
            try:
                if method_name == "BM25":
                    if not query_text:
                        tqdm.write(f"  [SKIP] {ref_repo} BM25 — no readme_summary")
                        continue
                    retrieved = bm25_search(es, query_text, max_k, ref_repo)
                else:
                    query_vector = doc.get(field)
                    if not query_vector:
                        tqdm.write(f"  [SKIP] {ref_repo} {method_name} — no embedding")
                        continue
                    retrieved = embedding_search(es, query_vector, field, max_k, ref_repo)

                for k in K_VALUES:
                    p = precision_at_k(retrieved, relevant, k)
                    r = recall_at_k(retrieved, relevant, k)
                    f1 = f1_at_k(p, r)
                    ndcg = ndcg_at_k(retrieved, relevant, k)

                    all_rows.append({
                        "repo": ref_repo,
                        "method": method_name,
                        "k": k,
                        "precision": round(p, 4),
                        "recall": round(r, 4),
                        "f1": round(f1, 4),
                        "ndcg": round(ndcg, 4),
                        "n_relevant": len(relevant),
                        "n_retrieved": len(retrieved),
                    })

            except Exception as e:
                tqdm.write(f"  [ERROR] {ref_repo} {method_name}: {e}")

    # Save raw results
    df = pd.DataFrame(all_rows)
    raw_path = RESULTS_DIR / "stage_a_raw.csv"
    df.to_csv(raw_path, index=False)
    print(f"\nRaw results saved to: {raw_path}")

    # Save summary (mean per method and K)
    summary = (df.groupby(["method", "k"])[["precision", "recall", "f1", "ndcg"]].mean().round(4))
    summary_path = RESULTS_DIR / "stage_a_summary.csv"
    summary.to_csv(summary_path)
    print(f"Summary saved to:      {summary_path}")

    # Print summary table
    print("\n" + "=" * 60)
    print("STAGE A EVALUATION SUMMARY")
    print("=" * 60)
    print(summary.to_string())


if __name__ == "__main__":
    main()
