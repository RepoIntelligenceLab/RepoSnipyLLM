"""
Convert inspect4py extracted JSON (directory_info.json) into a compact JSON
payload for RepoSnipyLLM Question 1 (single-repository description).

Input:
  - directory_info.json (your uploaded file)

Output:
  - q1_retrieved.json (a normalized "retrieved documents" JSON for Prompt 1)
"""

from __future__ import annotations

import json
import argparse
from pathlib import Path
from typing import Any, Dict, List, Optional


def build_q1_payload(data: Dict[str, Any], repo_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Build the normalized retrieved-documents JSON for Q1.
    """
    retrieved_docs: List[Dict[str, Any]] = []

    # README (full or chunked)
    readme_files = data.get("readme_files", {})
    if isinstance(readme_files, dict) and readme_files:
        for path, content in readme_files.items():
            retrieved_docs.append({
                "doc_type": "README",
                "path": str(path),
                "content": str(content),
            })

    # inspect4py software type classification
    if "software_type" in data:
        retrieved_docs.append({
            "doc_type": "inspect4py_software_type",
            "content": data.get("software_type"),
        })

    # Entry point information (main scripts, CLI entry points)
    # inspect4py provides software_invocation; we treat it as "entry_points"
    if "software_invocation" in data:
        retrieved_docs.append({
            "doc_type": "inspect4py_software_invocation",
            "content": data.get("software_invocation"),
        })

    # Optional: dependency summaries (requirements/imports)
    if "requirements" in data:
        retrieved_docs.append({
            "doc_type": "dependencies_requirements",
            "content": data.get("requirements"),
        })

    # Optional: installation files / evidence from directory tree
    # We cannot read setup.py content here, but we can confirm presence.
    if "directory_tree" in data:
        retrieved_docs.append({
            "doc_type": "repository_structure_tree",
            "content": data.get("directory_tree"),
        })

    # Optional: license
    if "license" in data:
        retrieved_docs.append({
            "doc_type": "license",
            "content": data.get("license"),
        })

    payload = {
        "repo_name": repo_name,
        "question_id": "Q1",
        "retrieved_documents": retrieved_docs,
    }
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="inp", default="directory_info.json", help="Input JSON path")
    parser.add_argument("--out", dest="out", default="q1_retrieved.json", help="Output JSON path")
    parser.add_argument("--repo", dest="repo", default=None, help="Override repo name (optional)")
    args = parser.parse_args()

    in_path = Path(args.inp)
    out_path = Path(args.out)

    data = json.loads(in_path.read_text(encoding="utf-8"))
    payload = build_q1_payload(data, repo_name=args.repo)

    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] Wrote: {out_path.resolve()}")


if __name__ == "__main__":
    main()
