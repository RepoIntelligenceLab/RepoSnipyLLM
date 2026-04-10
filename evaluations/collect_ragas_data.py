"""
collect_ragas_data.py

Collects (question, context, answer) triples for RAGAS evaluation
by running RepoSnipy-LLM on all single and search handler questions
across all 41 reference repositories.

Single handler: 41 repos x 3 questions  = 123 triples
Search handler: 41 pairs x 13 questions = 533 triples
Total:                                     656 triples

Output:
  evaluations/results/ragas_dataset.json

Supports resume: already collected triples are skipped.

Usage:
  cd evaluations/
  mkdir -p logs
  nohup python -u collect_ragas_data.py --model deepseek:deepseek-chat > logs/collect_ragas.log 2>&1 &
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

from tqdm import tqdm

# Change working directory to project root so prompt paths resolve correctly
os.chdir(Path(__file__).parent.parent)

# Add project root to path so we can import src.*
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.pipeline import run_question
from src.questions import get_question

from config import REFERENCE_REPOS, SEARCH_PAIRS

# Results dir is always relative to this script, not cwd
RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)
OUTPUT_PATH = RESULTS_DIR / "ragas_dataset.json"

MODEL = "deepseek:deepseek-chat"

# ── Question registry ─────────────────────────────────────────────────────────

SINGLE_QUESTIONS = [
    ("repository_understanding", "1"),
    ("implementation", "1"),
    ("reuse", "4"),
]

SEARCH_QUESTIONS = [
    ("repository_understanding", "2"),
    ("architecture", "1"),
    ("architecture", "2"),
    ("architecture", "3"),
    ("architecture", "4"),
    ("execution", "1"),
    ("execution", "2"),
    ("execution", "3"),
    ("implementation", "2"),
    ("implementation", "3"),
    ("implementation", "4"),
    ("reuse", "1"),
    ("reuse", "2"),
]

# ── Helpers ───────────────────────────────────────────────────────────────────


def make_key(task_id: str, question_id: str, ref_repo: str) -> str:
    """Unique key for resume support."""
    return f"{task_id}__{question_id}__{ref_repo}"


def load_existing(path: Path) -> dict:
    if path.exists():
        with open(path) as f:
            data = json.load(f)
        print(f"Resuming: {len(data)} triples already collected")
        return data
    return {}


def save(data: dict, path: Path):
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ── Collection ────────────────────────────────────────────────────────────────


def collect_single(
    task_id: str,
    question_id: str,
    ref_repo: str,
    model: str,
) -> dict | None:
    """Run a single-handler question and return a triple."""
    try:
        question_config = get_question(task_id, question_id)

        prompt, answer, context = run_question(
            question_config=question_config,
            repos=[ref_repo],
            model=model,
            topk=10,
            logdir=None,
            task_id=task_id,
            question_id=question_id,
        )

        question_text = f"{question_config['name']} (repo: {ref_repo})"

        return {
            "task": task_id,
            "question_id": question_id,
            "handler": "single",
            "repo": ref_repo,
            "question": question_text,
            "context": context,
            "answer": answer,
        }

    except Exception as e:
        tqdm.write(f"    [ERROR] {task_id} Q{question_id} {ref_repo}: {e}")
        return None


def collect_search(
    task_id: str,
    question_id: str,
    ref_repo: str,
    partner_repo: str,
    model: str,
) -> dict | None:
    """Run a search-handler question on a pair of repos and return a triple."""
    try:
        question_config = get_question(task_id, question_id)

        prompt, answer, context = run_question(
            question_config=question_config,
            repos=[ref_repo, partner_repo],
            model=model,
            topk=10,
            logdir=None,
            task_id=task_id,
            question_id=question_id,
        )

        question_text = f"{question_config['name']} (repos: {ref_repo}, {partner_repo})"

        return {
            "task": task_id,
            "question_id": question_id,
            "handler": "search",
            "repo": ref_repo,
            "partner": partner_repo,
            "question": question_text,
            "context": context,
            "answer": answer,
        }

    except Exception as e:
        tqdm.write(f"    [ERROR] {task_id} Q{question_id} {ref_repo}+{partner_repo}: {e}")
        return None


# ── Main ──────────────────────────────────────────────────────────────────────


def main(model: str = MODEL):
    print(f"Model:            {model}")
    print(f"Single questions: {len(SINGLE_QUESTIONS)}")
    print(f"Search questions: {len(SEARCH_QUESTIONS)}")
    print(f"Reference repos:  {len(REFERENCE_REPOS)}")

    total_single = len(SINGLE_QUESTIONS) * len(REFERENCE_REPOS)
    total_search = len(SEARCH_QUESTIONS) * len(REFERENCE_REPOS)
    total = total_single + total_search
    print(f"Total triples:    {total} ({total_single} single + {total_search} search)\n")

    data = load_existing(OUTPUT_PATH)

    success = 0
    skipped = 0
    failed = 0

    with tqdm(total=total, desc="Collecting triples") as pbar:

        # ── Single questions ──────────────────────────────────────────────────
        for task_id, question_id in SINGLE_QUESTIONS:
            for ref_repo in REFERENCE_REPOS:
                key = make_key(task_id, question_id, ref_repo)

                if key in data:
                    skipped += 1
                    pbar.update(1)
                    continue

                tqdm.write(f"  [SINGLE] {task_id} Q{question_id} | {ref_repo}")
                triple = collect_single(task_id, question_id, ref_repo, model)

                if triple:
                    data[key] = triple
                    save(data, OUTPUT_PATH)
                    success += 1
                else:
                    failed += 1

                pbar.update(1)
                time.sleep(0.5)

        # ── Search questions ──────────────────────────────────────────────────
        for task_id, question_id in SEARCH_QUESTIONS:
            for ref_repo in REFERENCE_REPOS:
                partner_repo = SEARCH_PAIRS.get(ref_repo)
                if not partner_repo:
                    tqdm.write(f"  [SKIP] {ref_repo} — no partner repo")
                    skipped += 1
                    pbar.update(1)
                    continue

                key = make_key(task_id, question_id, ref_repo)

                if key in data:
                    skipped += 1
                    pbar.update(1)
                    continue

                tqdm.write(f"  [SEARCH] {task_id} Q{question_id} | {ref_repo} + {partner_repo}")
                triple = collect_search(task_id, question_id, ref_repo, partner_repo, model)

                if triple:
                    data[key] = triple
                    save(data, OUTPUT_PATH)
                    success += 1
                else:
                    failed += 1

                pbar.update(1)
                time.sleep(0.5)

    print()
    print("=" * 60)
    print(f"Done.")
    print(f"  Success : {success}")
    print(f"  Skipped : {skipped}")
    print(f"  Failed  : {failed}")
    print(f"  Saved   : {len(data)} triples -> {OUTPUT_PATH}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=MODEL, help=f"LLM model (default: {MODEL})")
    args = parser.parse_args()
    main(model=args.model)
