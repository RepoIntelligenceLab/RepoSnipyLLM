"""
export_test.py

Export a single repo from repositories_raw index to a JSON file for inspection.

Usage:
  python export_test.py --repo 0rpc/zerorpc-python
"""

import argparse
import json
from elasticsearch import Elasticsearch

ES_URL = "http://localhost:9200"
API_KEY = "bm1SNEtKd0JRRU9zZjhvNHlNV1c6dWFwV1RSV0U4cER6emNyZlRFVXJMZw=="


def export_repo(repo_id: str):
    es = Elasticsearch(ES_URL, api_key=API_KEY)

    try:
        result = es.get(index="repositories_raw", id=repo_id)
    except Exception as e:
        print(f"[ERROR] Failed to fetch {repo_id}: {e}")
        return

    doc = result["_source"]

    filename = repo_id.replace("/", "_") + ".json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)

    print(f"Exported {repo_id} → {filename}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", "-r", required=True, help="e.g. 0rpc/zerorpc-python")
    args = parser.parse_args()
    export_repo(args.repo)
