"""
Prompt Builder for RepoSnipy-LLM.

Utils layer: pure prompt construction functions.
No business logic, no LLM calls, no data loading.
"""

from __future__ import annotations

import json
from pathlib import Path

MAX_PROMPT_CHARS = 250000

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

    if "tests" in retrieval:
        if repo_data.get("tests"):
            lines.append(f"Tests: {json.dumps(repo_data['tests'], indent=2)}")
        elif "has_tests" in repo_data:
            lines.append(f"Tests: {'present' if repo_data['has_tests'] else 'not found'}")

    return "\n\n".join(lines)


def _load_template(template_path: str) -> str:
    path = Path(template_path)
    if not path.exists():
        raise FileNotFoundError(f"Prompt template not found: {path}")
    return path.read_text()


def _format_repos_block(repo_data_list: list[dict], retrieval: list[str]) -> str:
    blocks = [f"### {r['repo_name']}\n\n{_format_repo_block(r, retrieval)}" for r in repo_data_list]
    return "\n\n---\n\n".join(blocks)


def _truncate(prompt: str, context: str) -> tuple[str, str]:
    """
    Truncate prompt to MAX_PROMPT_CHARS.
    Returns (truncated_prompt, actual_context) where actual_context
    reflects what was actually included in the prompt.
    """
    if len(prompt) <= MAX_PROMPT_CHARS:
        return prompt, context

    truncated_prompt = prompt[:MAX_PROMPT_CHARS]
    # Infer how much of the context was actually included
    overhead = len(prompt) - len(context)
    actual_context_len = max(0, MAX_PROMPT_CHARS - overhead)
    actual_context = context[:actual_context_len]
    return truncated_prompt, actual_context


# ── Prompt builders ───────────────────────────────────────────────────────────


def build_single_repo_prompt(question_config: dict, repo_data: dict) -> tuple[str, str]:
    template = _load_template(question_config["prompt"])
    context = _format_repo_block(repo_data, question_config["retrieval"])
    prompt = template.replace("{{RETRIEVED_DOCUMENTS}}", context)
    return _truncate(prompt, context)


def build_batch_summarise_prompt(question_config: dict, repo_data_list: list[dict]) -> tuple[str, str]:
    template_dir = str(Path(question_config["prompt"]).parent)
    template = _load_template(f"{template_dir}/batch_summarise.txt")
    context = _format_repos_block(repo_data_list, question_config["retrieval"])
    prompt = template.replace("{{REPOSITORIES}}", context)
    return _truncate(prompt, context)


def build_final_compare_prompt(question_config: dict, group_summaries: list[str]) -> tuple[str, str]:
    template = _load_template(question_config["prompt"])
    context = "\n\n---\n\n".join(group_summaries)
    prompt = template.replace("{{REPOSITORY_SUMMARIES}}", context)
    return _truncate(prompt, context)


def build_final_similar_prompt(
    question_config: dict,
    reference_block: str,
    group_summaries: list[str],
) -> tuple[str, str]:
    template = _load_template(question_config["prompt"])
    summaries_block = "\n\n---\n\n".join(group_summaries)
    context = f"{reference_block}\n\n---\n\n{summaries_block}"
    prompt = (template.replace("{{REFERENCE_REPO}}", reference_block).replace("{{REPOSITORY_SUMMARIES}}",
                                                                              summaries_block))
    return _truncate(prompt, context)
