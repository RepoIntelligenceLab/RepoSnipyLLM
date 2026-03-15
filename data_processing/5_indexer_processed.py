"""
indexer_processed.py

Reads from repositories_raw index and writes structured, cleaned documents
into repositories_processed index.

What it does:
  1. Fetches raw documents from repositories_raw
  2. Extracts and transforms fields according to the processed schema
  3. Indexes into repositories_processed

Usage:
  # Test with a few repos first
  python indexer_processed.py --limit 3

  # Index specific repos only
  python indexer_processed.py --repos django/django sympy/sympy

  # Full index
  python indexer_processed.py
"""

from __future__ import annotations

import argparse
import os
from dotenv import load_dotenv
from elasticsearch import Elasticsearch

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────

INDEX_RAW = "repositories_raw"
INDEX_PROCESSED = "repositories_processed"
ES_URL = os.getenv("ES_URL", "http://localhost:9200")
API_KEY = os.getenv("ES_API_KEY")

# ── ES client ─────────────────────────────────────────────────────────────────


def get_client() -> Elasticsearch:
    return Elasticsearch(ES_URL, api_key=API_KEY)


def ensure_index(es: Elasticsearch):
    if es.indices.exists(index=INDEX_PROCESSED):
        return

    mapping = {
        "settings": {
            "index.mapping.total_fields.limit": 10000
        },
        "mappings": {
            "dynamic": False,
            "properties": {
                "repo_id": {
                    "type": "keyword"
                },
                "software_type": {
                    "type": "keyword"
                },
                "license": {
                    "type": "object",
                    "dynamic": False
                },
                "metadata": {
                    "type": "object",
                    "dynamic": False
                },
                "directory_tree": {
                    "type": "object",
                    "dynamic": False
                },
                "requirements": {
                    "type": "object",
                    "dynamic": False
                },
                "tests": {
                    "type": "object",
                    "dynamic": False
                },
                "software_invocation": {
                    "type": "object",
                    "dynamic": False
                },
                "readme_summary": {
                    "type": "text"
                },
                "embedding": {
                    "type": "dense_vector",
                    "dims": 3072,
                    "index": True,
                    "similarity": "cosine"
                },
                "readme_files": {
                    "type": "object",
                    "properties": {
                        "filename": {
                            "type": "keyword"
                        },
                        "content": {
                            "type": "text"
                        },
                        "readme_file_summary": {
                            "type": "text"
                        },
                    }
                },
                "files": {
                    "type": "object",
                    "properties": {
                        "file": {
                            "properties": {
                                "path": {
                                    "type": "keyword"
                                },
                                "fileNameBase": {
                                    "type": "keyword"
                                },
                            }
                        },
                        "is_test": {
                            "type": "boolean"
                        },
                        "body_source_code": {
                            "type": "text"
                        },
                        "file_doc_summary": {
                            "type": "text"
                        },
                        "file_code_summary": {
                            "type": "text"
                        },
                        "dependencies": {
                            "type": "object",
                            "properties": {
                                "from_module": {
                                    "type": "keyword"
                                },
                                "import": {
                                    "type": "keyword"
                                },
                                "type": {
                                    "type": "keyword"
                                },
                            }
                        },
                        "functions": {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "keyword"
                                },
                                "source_code": {
                                    "type": "text"
                                },
                                "function_summary": {
                                    "type": "text"
                                },
                                "doc": {
                                    "properties": {
                                        "short_description": {
                                            "type": "text"
                                        },
                                        "long_description": {
                                            "type": "text"
                                        },
                                    }
                                },
                                "functions": {
                                    "type": "object",
                                    "properties": {
                                        "name": {
                                            "type": "keyword"
                                        },
                                        "source_code": {
                                            "type": "text"
                                        },
                                        "function_summary": {
                                            "type": "text"
                                        },
                                        "doc": {
                                            "properties": {
                                                "short_description": {
                                                    "type": "text"
                                                },
                                                "long_description": {
                                                    "type": "text"
                                                },
                                            }
                                        },
                                    }
                                },
                            }
                        },
                        "classes": {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "keyword"
                                },
                                "extend": {
                                    "type": "keyword"
                                },
                                "class_summary": {
                                    "type": "text"
                                },
                                "doc": {
                                    "properties": {
                                        "short_description": {
                                            "type": "text"
                                        },
                                        "long_description": {
                                            "type": "text"
                                        },
                                    }
                                },
                                "methods": {
                                    "type": "object",
                                    "properties": {
                                        "name": {
                                            "type": "keyword"
                                        },
                                        "source_code": {
                                            "type": "text"
                                        },
                                        "method_summary": {
                                            "type": "text"
                                        },
                                        "doc": {
                                            "properties": {
                                                "short_description": {
                                                    "type": "text"
                                                },
                                                "long_description": {
                                                    "type": "text"
                                                },
                                            }
                                        },
                                    }
                                },
                            }
                        },
                    }
                },
            }
        }
    }

    es.indices.create(index=INDEX_PROCESSED, body=mapping)
    print(f"Created index '{INDEX_PROCESSED}'.")


# ── Transformers ──────────────────────────────────────────────────────────────


def extract_doc(doc_val) -> dict | None:
    """
    Extract doc field from inspect4py format.
    Handles:
      - None / missing
      - {"short_description": "...", "long_description": "..."}
      - {"short_description": "...", "full": "..."}   <- full is fallback for long_description
      - plain string (fallback: treat as short_description)
    """
    if not doc_val:
        return None
    if isinstance(doc_val, str):
        return {"short_description": doc_val, "long_description": None}
    if isinstance(doc_val, dict):
        short = doc_val.get("short_description") or None
        long_ = doc_val.get("long_description") or doc_val.get("full") or None
        if short or long_:
            return {"short_description": short, "long_description": long_}
    return None


def extract_functions(fns) -> list[dict]:
    """Extract functions from dict format into list."""
    if not isinstance(fns, dict):
        return []
    result = []
    for name, val in fns.items():
        if not isinstance(val, dict):
            continue
        entry = {
            "name": name,
            "doc": extract_doc(val.get("doc")),
            "source_code": val.get("source_code") or None,
            "function_summary": None,
            "functions": extract_functions(val.get("functions", {})),
        }
        result.append(entry)
    return result


def extract_classes(cls) -> list[dict]:
    """Extract classes from dict format into list."""
    if not isinstance(cls, dict):
        return []
    result = []
    for name, val in cls.items():
        if not isinstance(val, dict):
            continue
        methods = []
        for m_name, m_val in (val.get("methods") or {}).items():
            if not isinstance(m_val, dict):
                continue
            methods.append({
                "name": m_name,
                "doc": extract_doc(m_val.get("doc")),
                "source_code": m_val.get("source_code") or None,
                "method_summary": None,
            })
        entry = {
            "name": name,
            "doc": extract_doc(val.get("doc")),
            "extend": val.get("extend") or [],
            "class_summary": None,
            "methods": methods,
        }
        result.append(entry)
    return result


def extract_files(raw: dict, repo_id: str) -> list[dict]:
    """Extract all file entries from path keys."""
    files = []
    for key, value in raw.items():
        # path keys look like org/repo/... and contain lists of file entries
        if not isinstance(value, list):
            continue
        if not key.startswith(repo_id):
            continue
        for entry in value:
            if not isinstance(entry, dict) or "file" not in entry:
                continue
            file_entry = {
                "file": {
                    "path": entry["file"].get("path"),
                    "fileNameBase": entry["file"].get("fileNameBase"),
                },
                "is_test":
                entry.get("is_test", False),
                "body_source_code":
                entry.get("body", {}).get("source_code") if isinstance(entry.get("body"), dict) else None,
                "dependencies": [{
                    "from_module": dep.get("from_module"),
                    "import": dep.get("import"),
                    "type": dep.get("type"),
                } for dep in entry.get("dependencies", []) if isinstance(dep, dict)],
                "functions":
                extract_functions(entry.get("functions", {})),
                "classes":
                extract_classes(entry.get("classes", {})),
                "file_doc_summary":
                None,
                "file_code_summary":
                None,
            }
            files.append(file_entry)
    return files


def extract_readme_files(raw: dict) -> list[dict]:
    """Extract readme_files into list format."""
    readme_raw = raw.get("readme_files", {})
    if not isinstance(readme_raw, dict):
        return []
    result = []
    for filename, content in readme_raw.items():
        result.append({
            "filename": filename,
            "content": content if isinstance(content, str) else str(content),
            "readme_file_summary": None,
        })
    return result


def extract_license(raw: dict) -> list | None:
    """
    Extract license from raw document.

    inspect4py license structure:
      - null
      - {"extracted_text": "..."}                          <- no detected_type
      - {"detected_type": [{"MIT": "91.7%"}, ...], ...}   <- list of {name: probability}

    Returns the full detected_type list, e.g. [{"MIT": "91.7%"}, {"MIT-0": "8.3%"}]
    """
    license_val = raw.get("license")
    if not isinstance(license_val, dict):
        return None

    detected = license_val.get("detected_type")
    if not detected or not isinstance(detected, list):
        return None

    return detected


def build_processed_document(raw: dict, repo_id: str) -> dict:
    """Transform a raw document into the processed schema."""
    license_val = extract_license(raw)

    return {
        "repo_id": repo_id,
        "software_type": raw.get("software_type"),
        "license": license_val,
        "metadata": raw.get("metadata"),
        "directory_tree": raw.get("directory_tree"),
        "requirements": raw.get("requirements"),
        "tests": raw.get("tests"),
        "software_invocation": raw.get("software_invocation"),
        "readme_files": extract_readme_files(raw),
        "readme_summary": None,
        "files": extract_files(raw, repo_id),
    }


# ── Indexer ───────────────────────────────────────────────────────────────────


def process_repo(es: Elasticsearch, repo_id: str, raw: dict) -> bool:
    try:
        doc = build_processed_document(raw, repo_id)
        es.index(index=INDEX_PROCESSED, id=repo_id, document=doc)
        return True
    except Exception as e:
        print(f"[ERROR] Failed to process {repo_id}: {e}")
        return False


def get_all_repo_ids(es: Elasticsearch) -> list[str]:
    """
    Fetch all document IDs from repositories_raw using scroll on _id only.
    This avoids loading source data into memory.
    """
    repo_ids = []
    resp = es.search(index=INDEX_RAW, body={"query": {"match_all": {}}, "_source": False, "size": 1000}, scroll="2m")
    scroll_id = resp["_scroll_id"]
    hits = resp["hits"]["hits"]

    while hits:
        for hit in hits:
            repo_ids.append(hit["_id"])
        resp = es.scroll(scroll_id=scroll_id, scroll="2m")
        scroll_id = resp["_scroll_id"]
        hits = resp["hits"]["hits"]

    es.clear_scroll(scroll_id=scroll_id)
    return repo_ids


def run(limit: int | None = None, repos: list[str] | None = None):
    es = get_client()

    try:
        info = es.info()
        print(f"Connected to Elasticsearch {info['version']['number']}")
    except Exception as e:
        print(f"Cannot connect to Elasticsearch: {e}")
        return

    ensure_index(es)

    # Get list of repo IDs to process
    if repos:
        repo_ids = repos
        print(f"Running in targeted mode: {len(repo_ids)} repos")
    else:
        print("Fetching repo IDs from repositories_raw...")
        repo_ids = get_all_repo_ids(es)
        print(f"Found {len(repo_ids)} repos")

    if limit:
        repo_ids = repo_ids[:limit]
        print(f"Limiting to {limit} repos")

    total = len(repo_ids)
    success = 0
    failed = 0

    print(f"\nProcessing {total} repos...\n")

    for repo_id in repo_ids:
        print(f"  Processing {repo_id}...", end=" ", flush=True)

        # Fetch one doc at a time to avoid memory circuit breaker
        try:
            hit = es.get(index=INDEX_RAW, id=repo_id)
            raw = hit["_source"]
        except Exception as e:
            print(f"[ERROR] Failed to fetch {repo_id}: {e}")
            failed += 1
            continue

        ok = process_repo(es, repo_id, raw)
        if ok:
            print("OK")
            success += 1
        else:
            failed += 1

    print(f"\nDone. {success} succeeded, {failed} failed out of {total} total.")


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build processed index from repositories_raw.")
    parser.add_argument("--limit", "-n", type=int, default=None, help="Only process the first N repos (for testing).")
    parser.add_argument("--repos",
                        "-r",
                        nargs="+",
                        default=None,
                        help="Only process specific repos, e.g. --repos django/django")
    args = parser.parse_args()
    run(limit=args.limit, repos=args.repos)
