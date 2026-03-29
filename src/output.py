"""
Output formatting for RepoSnipy-LLM.
Supports plain text and JSON output modes.
"""

from __future__ import annotations

import json
import sys

_USE_COLOUR = sys.stdout.isatty()


def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _USE_COLOUR else text


BOLD = lambda t: _c("1", t)
CYAN = lambda t: _c("36", t)
DIM = lambda t: _c("2", t)
HEADER = lambda t: _c("1;34", t)
SEP = lambda: DIM("─" * 60)

HANDLER_LABELS = {
    "single": "Single repository analysis",
    "search": "Multi-repository search",
    "similar": "Embedding-based similarity search",
}


def print_task_questions(tasks: dict) -> None:
    """Output for --list-task-questions"""
    for task_id, task in tasks.items():
        print(f"\n{HEADER(f'Task: {task_id}')}")
        print(DIM(f"  {task['description']}\n"))
        for q_id, q in task["questions"].items():
            print(f"  {BOLD(f'[Q{q_id}]')} {q['name']}")
            print(f"        {q['description']}")
            handler_hint = HANDLER_LABELS.get(q.get("handler"), q.get("handler", "unknown"))
            print(DIM(f"        Mode: {handler_hint}"))
            print()


def print_answer(
    task_id: str,
    question_id: str,
    repos: list[str],
    answer: str,
    output_format: str = "text",
    logfile: str | None = None,
) -> None:
    if output_format == "json":
        data = {
            "task": task_id,
            "question": question_id,
            "repos": repos,
            "answer": answer,
        }
        print(json.dumps(data, indent=2))
        return

    print(f"\n{HEADER(f'[RepoSnipy-LLM]')} Task: {task_id}  |  Question: Q{question_id}")
    print(DIM(f"Repositories: {', '.join(repos)}"))
    print(SEP())
    print(f"\n{answer}\n")
    print(SEP())
    if logfile:
        print(DIM(f"\nLogged to: {logfile}"))
    print()
