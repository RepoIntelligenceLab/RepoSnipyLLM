"""
Extracted on: 2026-04-02

Description:
    Performs static analysis using inspect4py. Optimized for remote/background 
    execution via nohup.

Usage:
    nohup python -u 2_inspect4py_analyse_awesome-python.py > analysis.log 2>&1 &
"""

import pickle
import subprocess
import os
import shutil
from pathlib import Path
from tqdm import tqdm

# --- PATH CONFIGURATION ---
PKL_PATH = Path("../data/AWESOME-PYTHON-REPOS.pkl")
WORKDIR = Path("../data/repos")
OUTDIR = Path("../data/output")
REQ_DIR = Path("../data/requirements")

# Ensure environment is ready
for d in [WORKDIR, OUTDIR, REQ_DIR]:
    d.mkdir(parents=True, exist_ok=True)


def process_single_repo(repo):
    """
    Core logic for a single repository: Clone -> Analyze -> Standardized Move.
    Returns a status string for logging.
    """
    try:
        repo_dir = WORKDIR / repo
        repo_out = OUTDIR / repo
        repo_url = f"https://github.com/{repo}.git"

        # 1. Resume Logic
        # Skip if the directory_info.json (sentinel file) exists
        if (repo_out / "directory_info.json").exists():
            return f"[SKIPPED] {repo}"

        # 2. Shallow Clone
        if not repo_dir.exists():
            repo_dir.parent.mkdir(parents=True, exist_ok=True)
            # capture_output prevents git progress text from cluttering logs
            subprocess.run(["git", "clone", "--depth", "1", repo_url, str(repo_dir)], check=False, capture_output=True)

        # 3. Static Analysis (inspect4py)
        repo_out.mkdir(parents=True, exist_ok=True)
        inspect_cmd = [
            "inspect4py", "-i",
            str(repo_dir), "-o",
            str(repo_out), "-r", "-html", "-cl", "-cf", "-dt", "-si", "-ast", "-sc", "-ld", "-rm", "-md"
        ]

        # Execute analysis synchronously
        subprocess.run(inspect_cmd, check=False, capture_output=True)

        # 4. Post-Analysis: Move requirements files
        cwd = Path.cwd()
        pure_repo_name = repo.split('/')[-1]
        repo_slug = repo.replace('/', '_')

        for req_file in cwd.glob(f"requirements_{pure_repo_name}*.txt"):
            # Target format: owner_repo_requirements.txt
            new_filename = f"{repo_slug}_requirements.txt"
            target_path = REQ_DIR / new_filename
            shutil.move(str(req_file), str(target_path))

        return f"[SUCCESS] {repo}"

    except Exception as e:
        return f"[FAILED]  {repo} | Error: {str(e)}"


def main():
    if not PKL_PATH.exists():
        print(f"Error: Master list {PKL_PATH} not found.")
        return

    with open(PKL_PATH, "rb") as f:
        repos_dict = pickle.load(f)

    # Sort repositories case-insensitively for a predictable log
    repo_list = sorted(list(repos_dict.keys()), key=str.lower)

    print(f"Total Repositories: {len(repo_list)}")

    # Serial processing loop
    with tqdm(total=len(repo_list), desc="Analyzing", unit="repo") as pbar:
        for repo in repo_list:
            # Directly process one by one
            result = process_single_repo(repo)

            # Print to log (nohup.out)
            tqdm.write(result)

            # Update progress bar
            pbar.update(1)

    print("\n--- Pipeline Finished: Data is Clean and Standardized ---")


if __name__ == "__main__":
    main()
