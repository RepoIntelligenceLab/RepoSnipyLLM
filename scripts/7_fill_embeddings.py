"""
fill_embeddings.py

Reads mean_repo_embedding from embeddings.pkl and fills
the embedding field in repositories_enriched ES index.

Usage:
  python 7_fill_embeddings.py
  python 7_fill_embeddings.py --pkl path/to/embeddings.pkl
"""

from __future__ import annotations

import argparse
import os
import pickle
import time
from pathlib import Path

from dotenv import load_dotenv
from elasticsearch import Elasticsearch
from tqdm import tqdm
import numpy as np

load_dotenv()

ES_URL = os.getenv("ES_URL", "http://localhost:9200")
API_KEY = os.getenv("ES_API_KEY")
INDEX = "repositories_enriched_new"


def get_es_client() -> Elasticsearch:
    return Elasticsearch(ES_URL, api_key=API_KEY)


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
    print(f"ES: {es.info()['version']['number']}\n")

    success = 0
    skipped = 0
    failed = 0
    failed_repos = []

    for repo_id, data in tqdm(embeddings.items(), desc="Filling embeddings"):
        mean_repo = data.get("mean_repo_embedding")
        if mean_repo is None:
            tqdm.write(f"  [SKIP] {repo_id} — no mean_repo_embedding")
            skipped += 1
            continue

        # Flatten to 1D list for ES
        embedding_list = mean_repo.flatten().tolist()

        if len(embedding_list) != 3072:
            tqdm.write(f"  [SKIP] {repo_id} — wrong shape: {len(embedding_list)}")
            skipped += 1
            continue

        if np.allclose(mean_repo.flatten(), 0):
            tqdm.write(f"  [SKIP] {repo_id} — zero vector")
            skipped += 1
            continue

        try:
            es.update(index=INDEX,
                      id=repo_id,
                      doc={"embedding": embedding_list},
                      request_timeout=60,
                      refresh="wait_for")
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
