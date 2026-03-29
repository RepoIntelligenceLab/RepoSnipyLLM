"""
Data Loader for RepoSnipy-LLM.

Reads repository data from Elasticsearch (repositories_enriched index).
The public API (load_repo / load_repos) is unchanged so nothing above
this layer needs to change.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from elasticsearch import Elasticsearch

load_dotenv()

INDEX = "repositories_enriched"
ES_URL = os.getenv("ES_URL", "http://localhost:9200")
API_KEY = os.getenv("ES_API_KEY")


class RepoNotFoundError(Exception):
    pass


def _get_client() -> Elasticsearch:
    return Elasticsearch(ES_URL, api_key=API_KEY)


def _fetch_doc(repo_name: str) -> dict:
    """
    Fetch a single document from ES by repo_id.
    Raises RepoNotFoundError if not found.
    """
    es = _get_client()
    try:
        result = es.get(index=INDEX, id=repo_name)
        return result["_source"]
    except Exception:
        raise RepoNotFoundError(f"Repository '{repo_name}' not found in Elasticsearch index '{INDEX}'.\n"
                                f"Make sure the repo has been indexed and use the full path <org>/<repo>.")


def _extract_fields(doc: dict, fields: list[str]) -> dict:
    """
    Extract only the requested fields from a processed ES document.
    Field names match the retrieval keys defined in questions.py.
    """
    extracted = {}

    if "readme_summary" in fields:
        extracted["readme_summary"] = doc.get("readme_summary") or ""

    if "readme" in fields:
        readme_files = doc.get("readme_files") or []
        texts = [r["content"] for r in readme_files if r.get("content")]
        extracted["readme"] = "\n\n".join(texts).strip()

    if "software_type" in fields:
        extracted["software_type"] = doc.get("software_type") or "unknown"

    if "invocation" in fields:
        extracted["invocation"] = doc.get("software_invocation") or []

    if "requirements" in fields:
        extracted["requirements"] = doc.get("requirements") or {}

    if "directory_tree" in fields:
        extracted["directory_tree"] = doc.get("directory_tree") or {}

    if "tests" in fields:
        tests = doc.get("tests")
        extracted["tests"] = tests or None
        extracted["has_tests"] = bool(tests)

    if "license" in fields:
        extracted["license"] = doc.get("license") or []

    return extracted


def load_repo(repo_name: str, fields: list[str]) -> dict:
    """
    Load a single repository's data from Elasticsearch.

    Returns a dict with:
      - repo_name
      - the requested fields
    """
    doc = _fetch_doc(repo_name)
    data = _extract_fields(doc, fields)
    data["repo_name"] = repo_name
    return data


def load_repos(repo_names: list[str], fields: list[str]) -> list[dict]:
    """
    Load multiple repositories from Elasticsearch.
    """
    return [load_repo(name, fields) for name in repo_names]
