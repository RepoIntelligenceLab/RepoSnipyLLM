#!/usr/bin/env python3
"""
RepoSnipy-LLM — Question-Driven Semantic Search and Explanation
                over Software Repositories.

Usage:
    python -m src.cli --list-tasks
  
    # Respository Understanding
    python -m src.cli --task repository_understanding --list-task-questions
    python -m src.cli --task repository_understanding --question 1 --repo tomerfiliba-org/rpyc --model deepseek:deepseek-chat
    python -m src.cli --task repository_understanding --question 2 --repo tomerfiliba-org/rpyc grpc/grpc --model deepseek:deepseek-chat
    python -m src.cli --task repository_understanding --question 3 --repo tomerfiliba-org/rpyc --topk 10 --model deepseek:deepseek-chat

    # Architecture
    python -m src.cli --task architecture --list-task-questions
    python -m src.cli --task architecture --question 1 --repo tomerfiliba-org/rpyc grpc/grpc --model deepseek:deepseek-chat
    python -m src.cli --task architecture --question 2 --repo tomerfiliba-org/rpyc grpc/grpc --model deepseek:deepseek-chat
    python -m src.cli --task architecture --question 3 --repo tomerfiliba-org/rpyc grpc/grpc --model deepseek:deepseek-chat
    python -m src.cli --task architecture --question 4 --repo tomerfiliba-org/rpyc grpc/grpc --model deepseek:deepseek-chat

    # Execution
    python -m src.cli --task execution --list-task-questions
    python -m src.cli --task execution --question 1 --repo tomerfiliba-org/rpyc grpc/grpc --model deepseek:deepseek-chat
    python -m src.cli --task execution --question 2 --repo tomerfiliba-org/rpyc grpc/grpc --model deepseek:deepseek-chat
    python -m src.cli --task execution --question 3 --repo tomerfiliba-org/rpyc grpc/grpc --model deepseek:deepseek-chat

    # Implementation
    python -m src.cli --task implementation --list-task-questions
    python -m src.cli --task implementation --question 1 --repo tomerfiliba-org/rpyc --model deepseek:deepseek-chat
    python -m src.cli --task implementation --question 2 --repo tomerfiliba-org/rpyc grpc/grpc --model deepseek:deepseek-chat
    python -m src.cli --task implementation --question 3 --repo tomerfiliba-org/rpyc grpc/grpc --model deepseek:deepseek-chat
    python -m src.cli --task implementation --question 4 --repo tomerfiliba-org/rpyc grpc/grpc --model deepseek:deepseek-chat

    # Reuse
    python -m src.cli --task reuse --list-task-questions
    python -m src.cli --task reuse --question 1 --repo tomerfiliba-org/rpyc grpc/grpc --model deepseek:deepseek-chat
    python -m src.cli --task reuse --question 2 --repo tomerfiliba-org/rpyc grpc/grpc --model deepseek:deepseek-chat
    python -m src.cli --task reuse --question 3 --repo tomerfiliba-org/rpyc --topk 10 --model deepseek:deepseek-chat
    python -m src.cli --task reuse --question 4 --repo tomerfiliba-org/rpyc --model deepseek:deepseek-chat
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.questions import TASKS, get_task, get_question
from src.pipeline import run_question
from src.llm import DEFAULT_MODEL
from src.output import print_task_questions, print_answer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="reposnipy-llm",
        description=("RepoSnipy-LLM: Question-driven semantic search and explanation "
                     "over software repositories."),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--list-tasks", action="store_true", help="List all available tasks.")
    parser.add_argument("--list-task-questions",
                        action="store_true",
                        help="List all questions for the specified --task.")
    parser.add_argument("--task", "-t", metavar="TASK_ID", help="Task identifier (e.g. repository_understanding).")
    parser.add_argument("--question", "-q", metavar="N", help="Question number within the task (e.g. 1, 2, 3).")
    parser.add_argument("--repo", "-r", metavar="REPO", nargs="+", help="One or more repository names to analyse.")
    parser.add_argument("--topk",
                        "-k",
                        type=int,
                        default=10,
                        metavar="N",
                        help="Number of candidate repositories to retrieve (default: 10).")
    parser.add_argument("--model",
                        "-m",
                        metavar="MODEL",
                        default=DEFAULT_MODEL,
                        help=f"LLM model to use (default: {DEFAULT_MODEL}).")
    parser.add_argument("--logdir", metavar="DIR", help="Directory to save run logs for reproducibility.")
    parser.add_argument("--format",
                        choices=["text", "json"],
                        default="text",
                        help="Output format: text (default) or json.")
    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    # --list-tasks
    if args.list_tasks:
        for task_id, task in TASKS.items():
            print(f"  {task_id}: {task['name']}")
            print(f"    {task['description']}")
        return 0

    # --list-task-questions
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

    # Validate required args
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

    # Run
    try:
        prompt, answer = run_question(
            question_config=question_config,
            repos=args.repo,
            model=args.model,
            topk=args.topk,
            logdir=args.logdir,
            task_id=args.task,
            question_id=args.question,
        )
    except (ValueError, FileNotFoundError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # Output
    print_answer(
        task_id=args.task,
        question_id=args.question,
        repos=args.repo,
        answer=answer,
        output_format=args.format,
        logfile=args.logdir,
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
