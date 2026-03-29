"""
Prompt Builder for RepoSnipy-LLM.

Utils layer: pure prompt construction functions.
No business logic, no LLM calls, no data loading.
"""

from __future__ import annotations

import json
from pathlib import Path

# ── Formatting helpers ────────────────────────────────────────────────────────


def _format_repo_block(repo_data: dict, retrieval: list[str]) -> str:
    """Format a single repo's extracted fields based on retrieval config."""
    lines = []

    if "readme_summary" in retrieval and repo_data.get("readme_summary"):
        lines.append(f"Summary:\n{repo_data['readme_summary']}")

    if "readme" in retrieval and repo_data.get("readme"):
        lines.append(f"README:\n{repo_data['readme']}")

    if "software_type" in retrieval and repo_data.get("software_type"):
        lines.append(f"Software type: {repo_data['software_type']}")

    if "invocation" in retrieval and repo_data.get("invocation"):
        for inv in repo_data["invocation"]:
            if inv.get("installation"):
                lines.append(f"Installation: {inv['installation']}")
            if inv.get("run"):
                lines.append(f"Run: {', '.join(inv['run']) if isinstance(inv['run'], list) else inv['run']}")

    if "requirements" in retrieval and repo_data.get("requirements"):
        reqs = repo_data["requirements"]
        packages = {k: v for k, v in reqs.items() if not k.startswith("#")}
        if packages:
            req_str = ", ".join(f"{k} {v}".strip() for k, v in packages.items())
            lines.append(f"Requirements: {req_str}")

    if "directory_tree" in retrieval and repo_data.get("directory_tree"):
        tree_str = json.dumps(repo_data["directory_tree"], indent=2)
        lines.append(f"Directory structure:\n{tree_str}")

    if not lines:
        return "No structured information available for this repository."

    return "\n\n".join(lines)


def _load_template(template_path: str) -> str:
    path = Path(template_path)
    if not path.exists():
        raise FileNotFoundError(f"Prompt template not found: {path}")
    return path.read_text()


def _format_repos_block(repo_data_list: list[dict], retrieval: list[str]) -> str:
    blocks = [f"### {r['repo_name']}\n\n{_format_repo_block(r, retrieval)}" for r in repo_data_list]
    return "\n\n---\n\n".join(blocks)


# ── Prompt builders ───────────────────────────────────────────────────────────


def build_single_repo_prompt(question_config: dict, repo_data: dict) -> str:
    template = _load_template(question_config["prompt"])
    repo_block = _format_repo_block(repo_data, question_config["retrieval"])
    return template.replace("{{RETRIEVED_DOCUMENTS}}", repo_block)


def build_batch_summarise_prompt(question_config: dict, repo_data_list: list[dict]) -> str:
    template_dir = str(Path(question_config["prompt"]).parent)
    template = _load_template(f"{template_dir}/batch_summarise.txt")
    repos_block = _format_repos_block(repo_data_list, question_config["retrieval"])
    return template.replace("{{REPOSITORIES}}", repos_block)


def build_final_compare_prompt(question_config: dict, group_summaries: list[str]) -> str:
    template = _load_template(question_config["prompt"])
    summaries_block = "\n\n---\n\n".join(group_summaries)
    return template.replace("{{REPOSITORY_SUMMARIES}}", summaries_block)


def build_final_similar_prompt(
    question_config: dict,
    reference_block: str,
    group_summaries: list[str],
) -> str:
    template = _load_template(question_config["prompt"])
    summaries_block = "\n\n---\n\n".join(group_summaries)
    return (template.replace("{{REFERENCE_REPO}}", reference_block).replace("{{REPOSITORY_SUMMARIES}}",
                                                                            summaries_block))
