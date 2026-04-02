"""
Description:
    Analyzes the analysis status of repositories and exports categorized lists 
    into individual text files. All outputs are SORTED alphabetically for 
    easier debugging and comparison.

Usage:
    python 2_check_and_export_progress.py
"""

import pickle
import os
from pathlib import Path

# --- CONFIGURATION ---
PKL_PATH = Path("../data/AWESOME-PYTHON-REPOS.pkl")
WORKDIR = Path("../data/repos")
OUTDIR = Path("../data/output")
REPORT_DIR = Path("../data/reports")

# Ensure the reports directory exists
REPORT_DIR.mkdir(parents=True, exist_ok=True)


def export_sorted_list_to_file(repo_list, filename):
    """Sorts the list alphabetically and saves to a file."""
    filepath = REPORT_DIR / filename

    # Sort the list in place (alphabetical order)
    sorted_list = sorted(repo_list, key=str.lower)

    with open(filepath, "w", encoding="utf-8") as f:
        for repo in sorted_list:
            f.write(f"{repo}\n")
    return filepath


def run_diagnostics():
    # 1. Load the ground truth from Stage 1
    if not PKL_PATH.exists():
        print(f"Error: Master list {PKL_PATH} not found.")
        return

    with open(PKL_PATH, "rb") as f:
        master_repos = pickle.load(f)

    all_repos = list(master_repos.keys())

    # 2. Categorize repositories into tracking buckets
    categories = {
        "missing_clones.txt": [],  # Not found in repos/ folder
        "missing_outputs.txt": [],  # Cloned but no folder in output/
        "incomplete_analyses.txt": [],  # Output folder exists but directory_info.json is missing
        "successful_repos.txt": []  # Full analysis confirmed
    }

    print(f"Analyzing {len(all_repos)} repositories for status check...")

    for repo in all_repos:
        repo_path = WORKDIR / repo
        output_path = OUTDIR / repo
        target_file = output_path / "directory_info.json"

        if not repo_path.exists():
            categories["missing_clones.txt"].append(repo)
        elif not output_path.exists():
            categories["missing_outputs.txt"].append(repo)
        elif not target_file.exists():
            categories["incomplete_analyses.txt"].append(repo)
        else:
            categories["successful_repos.txt"].append(repo)

    # 3. Sort and Export
    print("\nGeneration Reports in: ", REPORT_DIR.resolve())
    for filename, repo_list in categories.items():
        # The function now handles the sorting before writing
        path = export_sorted_list_to_file(repo_list, filename)
        print(f" - [Sorted] Saved {len(repo_list):<4} items to {filename}")

    print("\n--- Diagnostic & Sorting Complete ---")


if __name__ == "__main__":
    run_diagnostics()
