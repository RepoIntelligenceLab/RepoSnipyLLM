"""
fill_sub_embeddings.py

Reads mean_code_embedding, mean_doc_embedding, mean_requirement_embedding,
and mean_readme_embedding from embeddings.pkl and fills them into
repositories_enriched_new ES index as separate dense_vector fields (768 dims).

Usage:
  python 11_fill_sub_embeddings.py
  python 11_fill_sub_embeddings.py --pkl path/to/embeddings.pkl
"""

from __future__ import annotations

import argparse
import os
import pickle
import time
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from elasticsearch import Elasticsearch
from tqdm import tqdm

load_dotenv()

ES_URL = os.getenv("ES_URL", "http://localhost:9200")
API_KEY = os.getenv("ES_API_KEY")
INDEX = "repositories_enriched_new"

# Sub-embedding fields to fill: (pkl_key, es_field_name)
SUB_EMBEDDINGS = [
    ("mean_code_embedding", "embedding_code"),
    ("mean_doc_embedding", "embedding_doc"),
    ("mean_requirement_embedding", "embedding_requirement"),
    ("mean_readme_embedding", "embedding_readme"),
]


def get_es_client() -> Elasticsearch:
    return Elasticsearch(ES_URL, api_key=API_KEY)


def update_mapping(es: Elasticsearch):
    """Add 4 new dense_vector fields (768 dims) to the index mapping."""
    properties = {
        field: {
            "type": "dense_vector",
            "dims": 768,
            "index": True,
            "similarity": "cosine"
        }
        for _, field in SUB_EMBEDDINGS
    }
    es.indices.put_mapping(index=INDEX, body={"properties": properties})
    print(f"Mapping updated: {[f for _, f in SUB_EMBEDDINGS]}\n")


def main(pkl_path: str = "../data/repo_embeddings/repo_info_embeddings.pkl"):
    pkl_file = Path(pkl_path)
    if not pkl_file.exists():
        print(f"[ERROR] pkl file not found: {pkl_file}")
        return

    print(f"Loading embeddings from {pkl_file}...")
    with open(pkl_file, "rb") as f:
        embeddings = pickle.load(f)
    print(f"Loaded {len(embeddings)} repos\n")

    es = get_es_client()
    print(f"ES: {es.info()['version']['number']}")

    update_mapping(es)

    success = 0
    skipped = 0
    failed = 0
    failed_repos = []

    for repo_id, data in tqdm(embeddings.items(), desc="Filling sub-embeddings"):

        # Build doc update — only include fields that are valid
        doc = {}

        for pkl_key, es_field in SUB_EMBEDDINGS:
            vec = data.get(pkl_key)
            if vec is None:
                tqdm.write(f"  [WARN] {repo_id} — missing {pkl_key}, skipping this field")
                continue

            vec_flat = vec.flatten().tolist()

            if len(vec_flat) != 768:
                tqdm.write(f"  [WARN] {repo_id} — wrong shape for {pkl_key}: {len(vec_flat)}, skipping this field")
                continue

            if np.allclose(vec.flatten(), 0):
                tqdm.write(f"  [WARN] {repo_id} — zero vector for {pkl_key}, skipping this field")
                continue

            doc[es_field] = vec_flat

        if not doc:
            tqdm.write(f"  [SKIP] {repo_id} — no valid embeddings")
            skipped += 1
            continue

        try:
            es.update(index=INDEX, id=repo_id, doc=doc, request_timeout=60, refresh="wait_for")
            tqdm.write(f"  [OK] {repo_id}")
            success += 1
            time.sleep(0.05)
        except Exception as e:
            tqdm.write(f"  [ERROR] {repo_id}: {e}")
            failed += 1
            failed_repos.append(repo_id)

    print()
    print("=" * 60)
    print(f"Done.")
    print(f"  Success : {success}")
    print(f"  Skipped : {skipped}")
    print(f"  Failed  : {failed}")
    if failed_repos:
        print(f"\nFailed repos:")
        for r in failed_repos:
            print(f"  {r}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pkl", default="../data/repo_embeddings/repo_info_embeddings.pkl")
    args = parser.parse_args()
    main(pkl_path=args.pkl)
