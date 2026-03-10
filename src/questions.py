"""
Question and Task registry for RepoSnipy-LLM.

To add a new question: add an entry to the TASKS dict below.
To add a new task: add a new key to TASKS with its own questions dict.
"""

TASKS = {
    "repository_understanding": {
        "name": "Repository Understanding",
        "description": "Questions that help users understand one or more repositories.",
        "questions": {
            "1": {
                "name":
                "What does a repository do?",
                "description": ("Explains the main purpose, software type, "
                                "installation and usage of a single repository."),
                "input":
                "single_repo",
                "retrieval": [
                    "readme",
                    "software_type",
                    "invocation",
                    "requirements",
                    "directory_tree",
                ],
                "prompt":
                "prompts/q1_what_does_repo_do.txt",
            },
            "2": {
                "name":
                "What are the similarities and differences between repositories?",
                "description": ("Compares two or more repositories based on "
                                "structure, software type, dependencies and usage patterns."),
                "input":
                "multi_repo",
                "retrieval": [
                    "readme",
                    "software_type",
                    "invocation",
                    "requirements",
                    "directory_tree",
                ],
                "prompt":
                "prompts/q2_compare_repositories.txt",
            },
            "3": {
                "name":
                "Find repositories similar to a given one.",
                "description": ("Retrieves and explains repositories most similar "
                                "to a reference repository in terms of structure and functionality."),
                "input":
                "single_repo",
                "retrieval": [
                    "readme",
                    "software_type",
                ],
                "prompt":
                "prompts/q3_find_similar_repositories.txt",
                "requires_embeddings":
                True,
            },
        },
    },
}


def get_task(task_id: str) -> dict:
    if task_id not in TASKS:
        available = ", ".join(TASKS.keys())
        raise ValueError(f"Unknown task '{task_id}'. Available tasks: {available}")
    return TASKS[task_id]


def get_question(task_id: str, question_id: str) -> dict:
    task = get_task(task_id)
    questions = task["questions"]
    if question_id not in questions:
        available = ", ".join(questions.keys())
        raise ValueError(f"Unknown question '{question_id}' for task '{task_id}'. "
                         f"Available questions: {available}")
    return questions[question_id]
