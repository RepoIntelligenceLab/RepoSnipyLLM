"""
fill_readme_summary.py

Fills readme_summary for all repos in repositories_enriched index.
Reads all readme files' raw content directly (not from readme_file_summary).
Runs sequentially to avoid rate limiting.

Usage:
  python 8_fill_readme_summary.py

Logs are printed to stdout, redirect to file if needed:
  nohup python -u 8_fill_readme_summary.py > logs/readme_summary.log 2>&1 &
"""

import os
import time
from dotenv import load_dotenv
from elasticsearch import Elasticsearch
from tqdm import tqdm
from zai import ZhipuAiClient

load_dotenv()

ES_URL = os.getenv('ES_URL', 'http://localhost:9200')
API_KEY = os.getenv('ES_API_KEY')
ZHIPU_API_KEY = os.getenv('ZHIPU_API_KEY')

es = Elasticsearch(ES_URL, api_key=API_KEY)
zhipu = ZhipuAiClient(api_key=ZHIPU_API_KEY)

INDEX = 'repositories_enriched_new'
MODEL = 'glm-4.7-flash'
SLEEP_BETWEEN_CALLS = 0.5
MAX_CHARS = 300000

# ── Prompt ────────────────────────────────────────────────────────────────────

README_SUMMARY_PROMPT = """You are a software documentation assistant.
Below are the README files of a software repository (there may be one or more).

Write a comprehensive overall summary of this repository based strictly on the provided content.
Your summary should naturally cover relevant aspects such as:
- The main purpose and goals of the repository
- The type of software (e.g. library, application, tool, framework)
- Key features, capabilities, or use cases
- Installation or usage information, if mentioned
- Target audience or domain, if clear from the content

Guidelines:
- Let the content guide the length and structure of your summary.
- If multiple README files are provided, synthesise them into a single coherent summary.
- Use ONLY the information provided. Do NOT make assumptions or add external knowledge.
- If the README content is too short or uninformative, briefly state what little can be determined.

README content:
{content}
"""


def build_prompt(readme_files: list[dict]) -> str:
    parts = []
    for r in readme_files:
        parts.append(f'--- {r["filename"]} ---\n{r["content"]}')
    combined = '\n\n'.join(parts)
    if len(combined) > MAX_CHARS:
        combined = combined[:MAX_CHARS] + '\n\n[Content truncated due to length]'
    return README_SUMMARY_PROMPT.format(content=combined)


def zhipu_generate(prompt: str, max_retries: int = 3) -> str:
    for attempt in range(max_retries):
        try:
            response = zhipu.chat.completions.create(model=MODEL, messages=[{'role': 'user', 'content': prompt}])
            return response.choices[0].message.content.strip()
        except Exception as e:
            if attempt < max_retries - 1:
                wait = 10 * (attempt + 1)  # 10s, 20s, 30s
                tqdm.write(f'  [RETRY] attempt {attempt + 1}, waiting {wait}s: {e}')
                time.sleep(wait)
            else:
                raise


# ── ES utils ──────────────────────────────────────────────────────────────────


def get_all_repo_ids() -> list[str]:
    repo_ids = []
    resp = es.search(index=INDEX, body={'query': {'match_all': {}}, '_source': False, 'size': 1000}, scroll='2m')
    scroll_id = resp['_scroll_id']
    hits = resp['hits']['hits']
    while hits:
        repo_ids.extend(hit['_id'] for hit in hits)
        resp = es.scroll(scroll_id=scroll_id, scroll='2m')
        scroll_id = resp['_scroll_id']
        hits = resp['hits']['hits']
    es.clear_scroll(scroll_id=scroll_id)
    return repo_ids


# ── Main ──────────────────────────────────────────────────────────────────────


def main():
    print(f'ES: {es.info()["version"]["number"]}')
    print(f'Model: {MODEL}')
    print()

    repo_ids = get_all_repo_ids()
    print(f'Total repos: {len(repo_ids)}\n')

    success_repos = []
    skipped_repos = []
    failed_repos = []

    for repo_id in tqdm(repo_ids, desc='Repos'):
        try:
            doc = es.get(index=INDEX, id=repo_id)['_source']

            # Skip if already filled
            if doc.get('readme_summary'):
                tqdm.write(f'  [SKIP] {repo_id} — already done')
                skipped_repos.append(repo_id)
                continue

            readme_files = doc.get('readme_files') or []

            if not readme_files:
                tqdm.write(f'  [SKIP] {repo_id} — no readme files')
                skipped_repos.append(repo_id)
                continue

            tqdm.write(f'  [PROC] {repo_id} — {len(readme_files)} readme file(s)')

            prompt = build_prompt(readme_files)
            summary = zhipu_generate(prompt)

            # Update ES
            es.update(index=INDEX, id=repo_id, body={'doc': {'readme_summary': summary}})

            tqdm.write(f'  [OK]   {repo_id}')
            success_repos.append(repo_id)
            time.sleep(SLEEP_BETWEEN_CALLS)

        except Exception as e:
            tqdm.write(f'  [ERROR] {repo_id}: {e}')
            failed_repos.append(repo_id)

    # ── Summary ───────────────────────────────────────────────────────────────
    print()
    print('=' * 60)
    print(f'Done.')
    print(f'  Success : {len(success_repos)}')
    print(f'  Skipped : {len(skipped_repos)}')
    print(f'  Failed  : {len(failed_repos)}')

    if success_repos:
        print(f'\nSuccess repos:')
        for r in success_repos:
            print(f'  {r}')

    if skipped_repos:
        print(f'\nSkipped repos:')
        for r in skipped_repos:
            print(f'  {r}')

    if failed_repos:
        print(f'\nFailed repos:')
        for r in failed_repos:
            print(f'  {r}')


if __name__ == '__main__':
    main()
