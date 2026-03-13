"""
indexer_raw.py

Indexes raw inspect4py output into Elasticsearch index: repositories_raw.

What it does:
  1. Scans data/output/<org>/<repo>/directory_info.json
  2. Strips the '../data/output/' prefix from path keys
  3. Adds repo_id field (org/repo)
  4. Uses org/repo as the ES document _id
  5. Indexes into repositories_raw

Notes:
  - Index is created with dynamic: false, meaning ES will not attempt to
    parse or map nested fields. This avoids issues with special characters
    in field names (e.g. .gitignore, README.rst). repositories_raw is a
    backup index and does not need to be searchable.

Usage:
  # Test with a few repos first
  python indexer_raw.py --limit 3

  # Index specific repos only
  python indexer_raw.py --repos django/django sympy/sympy

  # Full index
  python indexer_raw.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from elasticsearch import Elasticsearch

# ── Config ────────────────────────────────────────────────────────────────────

DATA_ROOT = Path(__file__).parent.parent / "data" / "output"
INDEX_NAME = "repositories_raw"
ES_URL = "http://localhost:9200"
API_KEY = "bm1SNEtKd0JRRU9zZjhvNHlNV1c6dWFwV1RSV0U4cER6emNyZlRFVXJMZw=="

PREFIX_TO_STRIP = "../data/output/"

# ── ES client ─────────────────────────────────────────────────────────────────


def get_client() -> Elasticsearch:
    return Elasticsearch(ES_URL, api_key=API_KEY)


def ensure_index(es: Elasticsearch):
    """
    Create the index with dynamic mapping disabled.
    This prevents ES from trying to parse nested fields with special
    character key names (e.g. .gitignore, README.rst).
    """
    if not es.indices.exists(index=INDEX_NAME):
        es.indices.create(index=INDEX_NAME,
                          body={
                              "settings": {
                                  "index.mapping.total_fields.limit": 10000
                              },
                              "mappings": {
                                  "dynamic": False
                              }
                          })
        print(f"Created index '{INDEX_NAME}' with dynamic mapping disabled.")


# ── Document builder ──────────────────────────────────────────────────────────


def strip_prefix(key: str) -> str:
    """
    Strip '../data/output/' prefix from path keys.

    Example:
      '../data/output/0rpc/zerorpc-python/zerorpc-python'
      → '0rpc/zerorpc-python/zerorpc-python'
    """
    if key.startswith(PREFIX_TO_STRIP):
        return key[len(PREFIX_TO_STRIP):]
    return key


def build_document(raw: dict, repo_id: str) -> dict:
    """
    Build an ES document from raw directory_info.json content.
    - Strip path prefixes from all keys
    - Add repo_id
    """
    doc = {"repo_id": repo_id}
    for key, value in raw.items():
        doc[strip_prefix(key)] = value
    return doc


# ── Indexer ───────────────────────────────────────────────────────────────────


def index_repo(es: Elasticsearch, org: str, repo: str, json_path: Path) -> bool:
    """
    Load a single repo's directory_info.json and index it into ES.
    Returns True on success, False on failure.
    """
    try:
        with open(json_path, encoding="utf-8") as f:
            raw = json.load(f)
    except Exception as e:
        print(f"[ERROR] Failed to read {json_path}: {e}")
        return False

    repo_id = f"{org}/{repo}"
    doc = build_document(raw, repo_id)

    try:
        es.index(index=INDEX_NAME, id=repo_id, document=doc)
        return True
    except Exception as e:
        print(f"[ERROR] Failed to index {repo_id}: {e}")
        return False


def run(limit: int | None = None, repos: list[str] | None = None):
    es = get_client()

    # Verify connection
    try:
        info = es.info()
        print(f"Connected to Elasticsearch {info['version']['number']}")
    except Exception as e:
        print(f"Cannot connect to Elasticsearch: {e}")
        return

    ensure_index(es)

    # Find target json files
    if repos:
        json_files = []
        for repo_id in repos:
            p = DATA_ROOT / repo_id / "directory_info.json"
            if p.exists():
                json_files.append(p)
            else:
                print(f"  [WARN] Not found: {p}")
        print(f"Running in targeted mode: indexing {len(json_files)} repos")
    else:
        json_files = sorted(DATA_ROOT.glob("*/*/directory_info.json"))
        if not json_files:
            print(f"No directory_info.json files found under {DATA_ROOT}")
            return
        if limit:
            json_files = json_files[:limit]
            print(f"Running in test mode: indexing {limit} repos")

    total = len(json_files)
    success = 0
    failed = 0

    print(f"Indexing {total} repos into '{INDEX_NAME}'...\n")

    for json_path in json_files:
        org = json_path.parts[-3]
        repo = json_path.parts[-2]
        repo_id = f"{org}/{repo}"

        print(f"  Indexing {repo_id}...", end=" ", flush=True)
        ok = index_repo(es, org, repo, json_path)
        if ok:
            print("OK")
            success += 1
        else:
            failed += 1

    print(f"\nDone. {success} succeeded, {failed} failed out of {total} total.")


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Index raw inspect4py data into Elasticsearch.")
    parser.add_argument("--limit",
                        "-n",
                        type=int,
                        default=None,
                        help="Only index the first N repos (for testing). Omit to index all.")
    parser.add_argument("--repos",
                        "-r",
                        nargs="+",
                        default=None,
                        help="Only index specific repos, e.g. --repos django/django sympy/sympy")
    args = parser.parse_args()
    run(limit=args.limit, repos=args.repos)
