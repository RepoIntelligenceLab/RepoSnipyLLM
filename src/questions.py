"""
Question and Task registry for RepoSnipy-LLM.

To add a new question: add an entry to the TASKS dict below.
To add a new task: add a new key to TASKS with its own questions dict.

handler types:
  single  - single repo deep analysis
  search  - multi repo retrieval/filtering (user specified)
  similar - embedding-based similarity search (top K)
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
                "handler":
                "single",
                "retrieval": [
                    "readme",
                    "software_type",
                    "invocation",
                    "requirements",
                    "directory_tree",
                ],
                "prompt":
                "prompts/repository_understanding_1_what_does_repo_do.txt",
            },
            "2": {
                "name":
                "What are the similarities and differences between repositories?",
                "description": ("Compares two or more repositories based on "
                                "structure, software type, dependencies and usage patterns."),
                "handler":
                "search",
                "retrieval": [
                    "readme_summary",
                    "software_type",
                    "invocation",
                    "requirements",
                    "directory_tree",
                ],
                "prompt":
                "prompts/repository_understanding_2_compare.txt",
            },
            "3": {
                "name":
                "Find repositories similar to a given one.",
                "description": ("Retrieves and explains repositories most similar "
                                "to a reference repository in terms of structure and functionality."),
                "handler":
                "similar",
                "retrieval": [
                    "readme_summary",
                    "software_type",
                    "invocation",
                    "requirements",
                ],
                "prompt":
                "prompts/repository_understanding_3_similar.txt",
            },
        },
    },
    "architecture": {
        "name": "Architecture Analysis",
        "description": "Questions about the structural and architectural organisation of repositories.",
        "questions": {
            "1": {
                "name": "Which repositories are organised into clearly separated modules or packages?",
                "description": "Identifies repositories with a modular structure.",
                "handler": "search",
                "retrieval": [
                    "readme_summary",
                    "software_type",
                    "directory_tree",
                ],
                "prompt": "prompts/architecture_1_modular_structure.txt",
            },
            "2": {
                "name":
                "Which repositories show a layered structure?",
                "description": ("Identifies repositories with a layered design, "
                                "e.g. separation between core logic and interfaces."),
                "handler":
                "search",
                "retrieval": [
                    "readme_summary",
                    "software_type",
                    "directory_tree",
                ],
                "prompt":
                "prompts/architecture_2_layered_design.txt",
            },
            "3": {
                "name": "Which repositories are designed as reusable libraries rather than standalone applications?",
                "description": "Distinguishes between libraries and standalone applications.",
                "handler": "search",
                "retrieval": [
                    "readme_summary",
                    "software_type",
                    "invocation",
                    "directory_tree",
                ],
                "prompt": "prompts/architecture_3_library_vs_application.txt",
            },
            "4": {
                "name": "Which repositories primarily consist of scripts rather than reusable modules?",
                "description": "Identifies script-based projects.",
                "handler": "search",
                "retrieval": [
                    "readme_summary",
                    "software_type",
                    "invocation",
                    "directory_tree",
                ],
                "prompt": "prompts/architecture_4_script_based.txt",
            },
        },
    },
    "execution": {
        "name": "Execution and Usage",
        "description": "Questions about how repositories are executed and used.",
        "questions": {
            "1": {
                "name":
                "Which repositories provide a clear entry point for execution?",
                "description": ("Identifies repositories with a clear entry point, "
                                "e.g. a main script or command-line interface."),
                "handler":
                "search",
                "retrieval": [
                    "readme_summary",
                    "software_type",
                    "invocation",
                    "directory_tree",
                ],
                "prompt":
                "prompts/execution_1_entry_points.txt",
            },
            "2": {
                "name": "Which repositories are designed to be executed in batch mode rather than interactively?",
                "description": "Distinguishes between batch and interactive execution models.",
                "handler": "search",
                "retrieval": [
                    "readme_summary",
                    "software_type",
                    "invocation",
                    "directory_tree",
                ],
                "prompt": "prompts/execution_2_batch_vs_interactive.txt",
            },
            "3": {
                "name": "Which repositories rely on configuration files or parameters to control execution?",
                "description": "Identifies configuration-driven repositories.",
                "handler": "search",
                "retrieval": [
                    "readme_summary",
                    "software_type",
                    "invocation",
                    "requirements",
                    "directory_tree",
                ],
                "prompt": "prompts/execution_3_configuration_driven.txt",
            },
        },
    },
    "implementation": {
        "name": "Implementation Analysis",
        "description": "Questions about the implementation details of repositories.",
        "questions": {
            "1": {
                "name":
                "How does this repository read input data?",
                "description": ("Explains how a single repository handles data input, "
                                "e.g. files, configuration objects, parameters."),
                "handler":
                "single",
                "retrieval": [
                    "readme_summary",
                    "software_type",
                    "invocation",
                    "requirements",
                    "directory_tree",
                ],
                "prompt":
                "prompts/implementation_1_data_input.txt",
            },
            "2": {
                "name": "Which repositories rely heavily on external libraries or frameworks?",
                "description": "Identifies repositories with heavy external dependencies.",
                "handler": "search",
                "retrieval": [
                    "readme_summary",
                    "software_type",
                    "requirements",
                ],
                "prompt": "prompts/implementation_2_external_dependencies.txt",
            },
            "3": {
                "name": "Which repositories include automated tests or testing infrastructure?",
                "description": "Identifies repositories with testing support.",
                "handler": "search",
                "retrieval": [
                    "readme_summary",
                    "software_type",
                    "tests",
                    "directory_tree",
                ],
                "prompt": "prompts/implementation_3_testing_support.txt",
            },
            "4": {
                "name": "Which repositories provide structured documentation beyond a basic README?",
                "description": "Assesses documentation quality across repositories.",
                "handler": "search",
                "retrieval": [
                    "readme_summary",
                    "software_type",
                    "directory_tree",
                ],
                "prompt": "prompts/implementation_4_documentation_quality.txt",
            },
        },
    },
    "reuse": {
        "name": "Maintenance and Reuse",
        "description": "Questions about the reusability and maintainability of repositories.",
        "questions": {
            "1": {
                "name": "Which repositories appear easy to reuse or extend?",
                "description": ("Assesses ease of reuse based on structure, "
                                "documentation and dependency management."),
                "handler": "single",
                "retrieval": [
                    "readme_summary",
                    "software_type",
                    "invocation",
                    "requirements",
                    "directory_tree",
                    "tests",
                ],
                "prompt": "prompts/reuse_1_ease_of_reuse.txt",
            },
            "2": {
                "name":
                "Which repositories show signs of high structural complexity?",
                "description": ("Identifies repositories with high complexity, "
                                "e.g. deeply nested modules or large functions."),
                "handler":
                "single",
                "retrieval": [
                    "readme_summary",
                    "software_type",
                    "directory_tree",
                ],
                "prompt":
                "prompts/reuse_2_complexity_indicators.txt",
            },
            "3": {
                "name":
                "Which repositories are most similar to a given repository in terms of structure and functionality?",
                "description": "Finds repositories similar to a reference for reuse purposes.",
                "handler": "similar",
                "retrieval": [
                    "readme_summary",
                    "software_type",
                    "invocation",
                    "requirements",
                ],
                "prompt": "prompts/reuse_3_similarity_for_reuse.txt",
            },
            "4": {
                "name":
                "Where in the repository is the core functionality implemented?",
                "description": ("Identifies where core functionality is concentrated, "
                                "e.g. in a few modules or spread across many files."),
                "handler":
                "single",
                "retrieval": [
                    "readme_summary",
                    "software_type",
                    "directory_tree",
                ],
                "prompt":
                "prompts/reuse_4_functionality_location.txt",
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
