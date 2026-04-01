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
import os
from pathlib import Path

from dotenv import load_dotenv
from elasticsearch import Elasticsearch

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────

DATA_ROOT = Path(__file__).parent.parent / "data" / "output"
INDEX_NAME = "repositories_raw"
ES_URL = os.getenv("ES_URL", "http://localhost:9200")
API_KEY = os.getenv("ES_API_KEY")

PREFIX_TO_STRIP = "../data/output/"
REPOS_PATH_MARKER = "data/repos/"

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


def strip_key_prefix(key: str) -> str:
    """Strip '../data/output/' prefix from top-level path keys."""
    if key.startswith(PREFIX_TO_STRIP):
        return key[len(PREFIX_TO_STRIP):]
    return key


def detect_repos_prefix(raw: dict) -> str:
    """
    Auto-detect the local repos path prefix from file.path fields.
    Looks for the first string containing 'data/repos/' and extracts
    everything up to and including that marker.

    Example:
      '/home/user/MyProject/data/repos/org/repo/file.py'
      -> '/home/user/MyProject/data/repos/'
    """
    for value in raw.values():
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    path = item.get("file", {}).get("path", "")
                    if REPOS_PATH_MARKER in path:
                        idx = path.index(REPOS_PATH_MARKER) + len(REPOS_PATH_MARKER)
                        return path[:idx]
    return ""


def strip_repos_prefix(s: str, repos_prefix: str) -> str:
    """Strip the local repos path prefix from file path strings.
    Handles both 'path/to/file' and 'python path/to/file' formats.
    """
    if repos_prefix and repos_prefix in s:
        return s.replace(repos_prefix, "")
    return s


def clean_readme_files(readme: dict) -> dict:
    """Strip ../data/output/<org>/<repo>/ prefix from readme_files keys."""
    result = {}
    for k, v in readme.items():
        clean_key = strip_key_prefix(k)
        # strip org/repo/ portion too, leaving just the filename/subpath
        parts = clean_key.split("/", 2)
        clean_key = parts[2] if len(parts) == 3 else clean_key
        result[clean_key] = v
    return result


def clean_value(value, repos_prefix: str):
    """
    Recursively clean file path strings inside values.
    Handles: list of dicts (code file entries), plain strings, dicts.
    """
    if isinstance(value, list):
        return [clean_value(item, repos_prefix) for item in value]
    elif isinstance(value, dict):
        return {k: clean_value(v, repos_prefix) for k, v in value.items()}
    elif isinstance(value, str):
        return strip_repos_prefix(value, repos_prefix)
    return value


def build_document(raw: dict, repo_id: str) -> dict:
    """
    Build an ES document from raw directory_info.json content.
    - Strip ../data/output/ prefix from top-level path keys
    - Auto-detect and strip local repos path from file.path and tests[].run strings
    - Strip prefix from readme_files internal keys
    - Add repo_id
    """
    repos_prefix = detect_repos_prefix(raw)
    doc = {"repo_id": repo_id}
    for key, value in raw.items():
        clean_key = strip_key_prefix(key)
        if clean_key == "readme_files":
            doc[clean_key] = clean_readme_files(value)
        else:
            doc[clean_key] = clean_value(value, repos_prefix)
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
