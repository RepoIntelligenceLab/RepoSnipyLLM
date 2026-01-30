import pickle
import subprocess
from pathlib import Path

# Path to the pickle file that stores repository information (dict)
PKL_PATH = "../data/AWESOME-PYTHON-REPOS.pkl"

# Directory to clone repositories into
WORKDIR = Path("../data/repos")

# Directory to store inspect4py outputs
OUTDIR = Path("../data/output")

# Create required directories if they do not exist
WORKDIR.mkdir(parents=True, exist_ok=True)
OUTDIR.mkdir(parents=True, exist_ok=True)

# Load repository dictionary from pickle file
with open(PKL_PATH, "rb") as f:
    repos = pickle.load(f)

# repos is a dict: keys are repo names like "owner/repo"
repo_list = list(repos.keys())

print(f"Loaded repos: {len(repo_list)}")


def run(cmd):
    """Run a shell command and print it to stdout."""
    print(">>", " ".join(cmd))
    subprocess.run(cmd, check=False)


for repo in repo_list:
    # Repo name format: "owner/repository"

    repo_dir = WORKDIR / repo
    repo_url = f"https://github.com/{repo}.git"

    # Clone the repository if it does not exist
    if not repo_dir.exists():
        # run(["git", "clone", "--depth", "1", repo_url, str(repo_dir)]) # shallow clone
        run(["git", "clone", repo_url, str(repo_dir)])
    else:
        print(f"Skip clone (already exists): {repo_dir}")

    # Create output directory for this repository
    repo_out = OUTDIR / repo
    repo_out.mkdir(parents=True, exist_ok=True)

    # inspect4py run (full analysis)
    """
    -r find the requirements of the repository.
    -html generates an html file of the DirJson in the output directory.
    -cl generates the call list in a separate html file.
    -cf generates the call graph for each file in a different directory.
    -dt captures the file directory tree from the root path of the target repository.
    -si generates which are the software invocation commands to run and test the target repository.
    -ast generates abstract syntax tree in json format.
    -sc generates source code of each ast node.
    -ld detects the license of the target repository.
    -rm extract all readme files in the target repository.
    -md extract metadata of the target repository using Github API.
    -df extract data flow graph for every function
    """
    run([
        "inspect4py", "-i",
        str(repo_dir), "-o",
        str(repo_out), "-r", "-html", "-cl", "-cf", "-dt", "-si", "-ast", "-sc", "-ld", "-rm", "-md"
    ])
