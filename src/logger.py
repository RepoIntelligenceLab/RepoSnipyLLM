"""
Logger for RepoSnipy-LLM.
Saves each run as a JSON file for reproducibility.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def save(
    logdir: str,
    task_id: str,
    question_id: str,
    repos: list[str],
    prompt: str,
    answer: str,
    model: str,
) -> Path:
    """Save a run log to logdir/<timestamp>_<task>_<question>.json"""
    logpath = Path(logdir)
    logpath.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    fname = logpath / f"{ts}_{task_id}_Q{question_id}.json"

    payload = {
        "timestamp": ts,
        "task": task_id,
        "question": question_id,
        "repos": repos,
        "model": model,
        "prompt": prompt,
        "answer": answer,
    }

    with open(fname, "w") as f:
        json.dump(payload, f, indent=2)

    return fname
