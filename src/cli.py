"""
RepoSnipy-LLM — Question-Driven Semantic Search and Explanation
                over Software Repositories.

Usage:
  python -m src.cli --list-tasks
  python -m src.cli --task repository_understanding --list-task-questions
  python -m src.cli --task repository_understanding --question 1 --repo 0rpc/zerorpc-python
  python -m src.cli --task repository_understanding --question 2 --repo 0rpc/zerorpc-python aaugustin/websockets
  python -m src.cli --task repository_understanding --question 3 --repo 0rpc/zerorpc-python --topk 10
  python -m src.cli --task repository_understanding --question 1 --repo 0rpc/zerorpc-python \
                    --model qwen3:8b --logdir ./logs --format json
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.questions import TASKS, get_task, get_question
from src.data_loader import load_repo, load_repos
from src.prompt_builder import build_prompt, build_summarise_prompt, build_compare_prompt
from src.llm import generate, DEFAULT_MODEL, SUPPORTED_PROVIDERS
from src.logger import save as save_log
from src.output import print_task_questions, print_answer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="reposnipy-llm",
        description=("RepoSnipy-LLM: Question-driven semantic search and explanation "
                     "over software repositories."),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--list-tasks",
        action="store_true",
        help="List all available tasks.",
    )
    parser.add_argument(
        "--list-task-questions",
        action="store_true",
        help="List all questions for the specified --task.",
    )
    parser.add_argument(
        "--task",
        "-t",
        metavar="TASK_ID",
        help="Task identifier (e.g. repository_understanding).",
    )
    parser.add_argument(
        "--question",
        "-q",
        metavar="N",
        help="Question number within the task (e.g. 1, 2, 3).",
    )
    parser.add_argument(
        "--repo",
        "-r",
        metavar="REPO",
        nargs="+",
        help="One or more repository names to analyse.",
    )
    parser.add_argument(
        "--topk",
        "-k",
        type=int,
        default=10,
        metavar="N",
        help="Number of candidate repositories to retrieve (default: 10).",
    )
    parser.add_argument(
        "--model",
        "-m",
        metavar="MODEL",
        default=DEFAULT_MODEL,
        help=(
            f"LLM model to use (default: {DEFAULT_MODEL}). "
            "Format: 'provider:model_name' (e.g. deepseek:deepseek-chat, "
            "zhipu:glm-4.7-flash, ollama:qwen3:8b). "
            f"Supported providers: {', '.join(sorted(SUPPORTED_PROVIDERS))}."
        ),
    )
    parser.add_argument(
        "--logdir",
        metavar="DIR",
        help="Directory to save run logs for reproducibility.",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format: text (default) or json.",
    )

    return parser


def handle_single_repo(question_config: dict, repos: list[str], model: str) -> tuple[str, str]:
    if len(repos) != 1:
        raise ValueError(f"This question requires exactly one repository. Got: {repos}")
    repo_data = load_repo(repos[0], question_config["retrieval"])
    prompt = build_prompt(question_config["prompt"], question_config, [repo_data])
    answer = generate(prompt, model)
    return prompt, answer


def handle_multi_repo(question_config: dict, repos: list[str], model: str) -> tuple[str, str]:
    if len(repos) < 2:
        raise ValueError("This question requires at least two repository names.")
    repo_data_list = load_repos(repos, question_config["retrieval"])

    # ── Single-call approach (current) ────────────────────────────────────────
    prompt = build_prompt(question_config["prompt"], question_config, repo_data_list)
    answer = generate(prompt, model)
    return prompt, answer

    # Summarises each repo individually first, then compares the summaries.
    # Uses anonymous aliases (Repository A, B, ...) to prevent the LLM from
    # using prior knowledge about known repositories.
    #
    # template_dir = str(Path(question_config["prompt"]).parent)
    # aliases = [chr(65 + i) for i in range(len(repo_data_list))]  # A, B, C, ...
    # summaries = []
    # for repo_data, alias in zip(repo_data_list, aliases):
    #     summarise_prompt = build_summarise_prompt(template_dir, repo_data, f"Repository {alias}")
    #     summary = generate(summarise_prompt, model)
    #     summaries.append((repo_data["repo_name"], summary))
    # compare_prompt = build_compare_prompt(template_dir, summaries)
    # answer = generate(compare_prompt, model)
    # return compare_prompt, answer


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    # --list-tasks
    if args.list_tasks:
        for task_id, task in TASKS.items():
            print(f"  {task_id}: {task['name']}")
            print(f"    {task['description']}")
        return 0

    # --list-task-questions (requires --task)
    if args.list_task_questions:
        if not args.task:
            parser.error("--list-task-questions requires --task.")
        try:
            task = get_task(args.task)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        print_task_questions({args.task: task})
        return 0

    # Validate required args for a query
    if not args.task:
        parser.error("--task is required. Use --list-tasks to see available tasks.")
    if not args.question:
        parser.error("--question is required. Use --task <id> --list-task-questions to see available questions.")
    if not args.repo:
        parser.error("--repo is required.")

    # Get question config
    try:
        question_config = get_question(args.task, args.question)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # Route to handler based on input type
    try:
        input_type = question_config["input"]
        if input_type == "single_repo":
            prompt, answer = handle_single_repo(question_config, args.repo, args.model)
        elif input_type == "multi_repo":
            prompt, answer = handle_multi_repo(question_config, args.repo, args.model)
        else:
            raise ValueError(f"Unknown input type: {input_type}")
    except (ValueError, FileNotFoundError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # Log if requested
    logfile = None
    if args.logdir:
        log_path = save_log(
            logdir=args.logdir,
            task_id=args.task,
            question_id=args.question,
            repos=args.repo,
            prompt=prompt,
            answer=answer,
            model=args.model,
        )
        logfile = str(log_path)

    # Output
    print_answer(
        task_id=args.task,
        question_id=args.question,
        repos=args.repo,
        answer=answer,
        output_format=args.format,
        logfile=logfile,
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
