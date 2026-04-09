"""
Extracted on: 2026-04-01

Description:
    This script serves as the primary data ingestion engine. It automates the 
    end-to-end process of acquiring and structuring repository data from 
    vinta/awesome-python.

Main Functionalities:
    1. Remote Fetching: Pulls the latest raw README.md from GitHub.
    2. Hierarchical Parsing: Identifies project categories using Markdown headers.
    3. Path Sanitization: Extracts and cleans 'user/repo' strings via RegEx.
    4. Dual-Indexing: 
        - Forward Index: Saves a Category-to-Repos mapping (JSON) for readability.
        - Reverse Index: Saves a Repo-to-Category lookup table (Pickle) for O(1) 
          search performance in downstream analysis tools.
"""
import requests
import re
import json
import pickle
import os


def run_awesome_python_pipeline(json_path, pickle_path):
    # 1. Fetch the raw README content
    readme_url = "https://raw.githubusercontent.com/vinta/awesome-python/master/README.md"
    try:
        response = requests.get(readme_url)
        response.raise_for_status()
        content = response.text
    except Exception as e:
        print(f"Failed to fetch README: {e}")
        return

    # 2. Prepare data structures
    # Forward mapping: Category -> [repos]
    structured_data = {}
    # Reverse mapping: repo -> Category (for the Pickle file)
    reverse_index = {}

    # Regex patterns
    category_regex = re.compile(r'^###?\s+(.+)')
    # Captures user and repo from github.com links
    repo_link_regex = re.compile(r'github\.com/([\w\-\.]+)/([\w\-\.]+)')

    current_category = None
    lines = content.split('\n')

    # 3. Process lines in a single pass
    for line in lines:
        # Check for category headers
        header_match = category_regex.match(line)
        if header_match:
            header_name = header_match.group(1).strip()
            # Skip TOC or meta sections
            if header_name in ["Contents", "Awesome Python"]:
                current_category = None
            else:
                current_category = header_name
                if current_category not in structured_data:
                    structured_data[current_category] = []
            continue

        # Extract repos if we are under a valid category
        if current_category:
            repos_found = repo_link_regex.findall(line)
            for user, repo in repos_found:
                # Basic cleaning performed immediately
                repo_full_name = f"{user.strip()}/{repo.strip().rstrip('/')}"

                # Exclusion logic
                if repo_full_name != "vinta/awesome-python":
                    # Ensure uniqueness within JSON and populate reverse index
                    if repo_full_name not in structured_data[current_category]:
                        structured_data[current_category].append(repo_full_name)
                        # Build reverse index for Pickle (all categories preserved)
                        if repo_full_name not in reverse_index:
                            reverse_index[repo_full_name] = []
                        if current_category not in reverse_index[repo_full_name]:
                            reverse_index[repo_full_name].append(current_category)

    # 4. Final filtering (remove empty categories)
    final_json_data = {k: v for k, v in structured_data.items() if v}

    # 5. Atomic Saving
    os.makedirs(os.path.dirname(json_path), exist_ok=True)

    # Save JSON
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(final_json_data, f, indent=4, ensure_ascii=False)

    # Save Pickle
    with open(pickle_path, 'wb') as f:
        pickle.dump(reverse_index, f)

    print(f"--- Pipeline Summary (2026-04-01) ---")
    print(f"Categories extracted: {len(final_json_data)}")
    print(f"Total unique repos: {len(reverse_index)}")
    print(f"Files saved: \n - {json_path}\n - {pickle_path}")


if __name__ == "__main__":
    # Define your paths once
    DATA_JSON = "../data/awesome-python_data.json"
    DATA_PICKLE = "../data/AWESOME-PYTHON-REPOS.pkl"

    run_awesome_python_pipeline(DATA_JSON, DATA_PICKLE)
