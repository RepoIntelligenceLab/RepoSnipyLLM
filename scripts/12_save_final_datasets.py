import pickle

with open("../data/reports/successful_repos.txt") as f:
    es_repos = set(line.strip() for line in f if line.strip())

with open("../data/AWESOME-PYTHON-REPOS.pkl", "rb") as f:
    repos_dict = pickle.load(f)

print(f"Original pkl: {len(repos_dict)} repos")
print(f"Successful repos: {len(es_repos)}")

final_dict = {repo_id: cats for repo_id, cats in repos_dict.items() if repo_id in es_repos}

print(f"Final pkl: {len(final_dict)} repos")
print(f"Removed: {len(repos_dict) - len(final_dict)} repos")

with open("../data/AWESOME-PYTHON-REPOS_FINAL.pkl", "wb") as f:
    pickle.dump(final_dict, f)

print("Saved to AWESOME-PYTHON-REPOS_FINAL.pkl")
