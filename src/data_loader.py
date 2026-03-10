"""
Data Loader for RepoSnipy-LLM.

Reads inspect4py directory_info.json files from the local filesystem.
(Later this layer can be swapped out for Elasticsearch without changing
anything above it.)
"""

from __future__ import annotations

import json
from pathlib import Path

# Fixed data root - change this to point at your data/output directory
DATA_ROOT = Path("data/output")


class RepoNotFoundError(Exception):
    pass


def _find_repo_path(repo_name: str) -> Path:
    """
    Find directory_info.json for a given repo_name.
    Expected layout: data/output/<org>/<repo>/directory_info.json

    Accepts:
      - full path:   0rpc/zerorpc-python
      - repo only:   zerorpc-python  (fallback fuzzy match)
    """
    # Try direct path first: data/output/0rpc/zerorpc-python/directory_info.json
    direct = DATA_ROOT / repo_name / "directory_info.json"
    if direct.exists():
        return direct

    # Fallback: match by repo name only (last segment after /)
    name = repo_name.split("/")[-1]
    matches = list(DATA_ROOT.rglob(f"{name}/directory_info.json"))
    if not matches:
        raise RepoNotFoundError(f"Repository '{repo_name}' not found under {DATA_ROOT}.\n"
                                f"Make sure the folder name matches exactly, e.g. 0rpc/zerorpc-python")
    if len(matches) > 1:
        paths = "\n  ".join(str(p) for p in matches)
        raise RepoNotFoundError(f"Multiple matches found for '{repo_name}':\n  {paths}\n"
                                f"Please use the full path <org>/<repo> to disambiguate.")
    return matches[0]


def _extract_fields(raw: dict, fields: list[str]) -> dict:
    """
    Extract only the requested fields from a raw directory_info.json dict.
    """
    extracted = {}

    if "readme" in fields:
        readme_dict = raw.get("readme_files", {})
        # Concatenate all readme texts (usually just one)
        extracted["readme"] = "\n\n".join(readme_dict.values()).strip()

    if "software_type" in fields:
        extracted["software_type"] = raw.get("software_type", "unknown")

    if "invocation" in fields:
        extracted["invocation"] = raw.get("software_invocation", [])

    if "requirements" in fields:
        extracted["requirements"] = raw.get("requirements", {})

    if "directory_tree" in fields:
        extracted["directory_tree"] = raw.get("directory_tree", {})

    if "tests" in fields:
        extracted["has_tests"] = bool(raw.get("tests"))

    if "license" in fields:
        lic = raw.get("license", {})
        extracted["license"] = lic.get("detected_type", [])

    return extracted


def load_repo(repo_name: str, fields: list[str]) -> dict:
    """
    Load a single repository's data.

    Returns a dict with:
      - repo_name
      - the requested fields extracted from directory_info.json
    """
    json_path = _find_repo_path(repo_name)
    with open(json_path) as f:
        raw = json.load(f)

    data = _extract_fields(raw, fields)
    data["repo_name"] = repo_name
    return data


def load_repos(repo_names: list[str], fields: list[str]) -> list[dict]:
    """
    Load multiple repositories. Used by Q2 (comparison).
    """
    return [load_repo(name, fields) for name in repo_names]
