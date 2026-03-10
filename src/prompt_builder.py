"""
Prompt Builder for RepoSnipy-LLM.

Loads a prompt template from the prompts/ directory and fills in
the retrieved repository data.
"""

from __future__ import annotations

import json
from pathlib import Path


def _format_repo_block(repo_data: dict) -> str:
    """Format a single repo's extracted fields into readable text."""
    lines = []

    if "software_type" in repo_data:
        lines.append(f"Software type: {repo_data['software_type']}")

    if "invocation" in repo_data and repo_data["invocation"]:
        for inv in repo_data["invocation"]:
            if inv.get("installation"):
                lines.append(f"Installation: {inv['installation']}")
            if inv.get("run"):
                lines.append(f"Run: {', '.join(inv['run']) if isinstance(inv['run'], list) else inv['run']}")

    if "requirements" in repo_data and repo_data["requirements"]:
        reqs = repo_data["requirements"]
        # Filter out non-package keys
        packages = {k: v for k, v in reqs.items() if not k.startswith("#")}
        if packages:
            req_str = ", ".join(f"{k} {v}".strip() for k, v in packages.items())
            lines.append(f"Requirements: {req_str}")

    if "directory_tree" in repo_data and repo_data["directory_tree"]:
        tree_str = json.dumps(repo_data["directory_tree"], indent=2)
        lines.append(f"Directory structure:\n{tree_str}")

    if "readme" in repo_data and repo_data["readme"]:
        lines.append(f"README:\n{repo_data['readme']}")

    return "\n\n".join(lines)


def build_prompt(template_path: str, question_config: dict, repo_data_list: list[dict]) -> str:
    """
    Load a prompt template and fill in the retrieved data.

    Parameters
    ----------
    template_path   : path to the .txt prompt template
    question_config : the question entry from questions.py
    repo_data_list  : list of repo data dicts (one for Q1/Q3, many for Q2)
    """
    path = Path(template_path)
    if not path.exists():
        raise FileNotFoundError(f"Prompt template not found: {template_path}")

    template = path.read_text()

    if question_config["input"] == "single_repo":
        repo_block = _format_repo_block(repo_data_list[0])
        return template.replace("{{RETRIEVED_DOCUMENTS}}", repo_block)

    if question_config["input"] == "multi_repo":
        blocks = []
        for repo_data in repo_data_list:
            block = f"### Repository: {repo_data['repo_name']}\n\n{_format_repo_block(repo_data)}"
            blocks.append(block)
        combined = "\n\n---\n\n".join(blocks)
        return template.replace("{{RETRIEVED_DOCUMENTS_BY_REPOSITORY}}", combined)

    raise ValueError(f"Unknown input type: {question_config['input']}")
