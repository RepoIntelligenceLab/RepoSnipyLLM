"""
fill_readme_file_summary.py

Fills readme_file_summary for all repos in repositories_processed index.
Runs sequentially to avoid rate limiting.

Usage:
  python fill_readme_file_summary.py

Logs are printed to stdout, redirect to file if needed:
  nohup python fill_readme_file_summary.py > logs/readme_file_summary.log 2>&1 &
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

INDEX = 'repositories_processed'
MODEL = 'glm-4.7-flash'
SLEEP_BETWEEN_CALLS = 0.5

# ── Prompt ────────────────────────────────────────────────────────────────────

README_FILE_SUMMARY_PROMPT = """You are a software documentation assistant.
Below is the README content of a software repository.

Write a comprehensive summary of this repository based strictly on the provided content.
Your summary should naturally cover relevant aspects such as:
- The main purpose and goals of the repository
- The type of software (e.g. library, application, tool, framework)
- Key features, capabilities, or use cases
- Installation or usage information, if mentioned
- Target audience or domain, if clear from the content

Guidelines:
- Let the content guide the length and structure of your summary.
- Use ONLY the information provided. Do NOT make assumptions or add external knowledge.
- If the README is too short or uninformative, briefly state what little can be determined.

README content:
{content}
"""


def build_prompt(content: str) -> str:
    return README_FILE_SUMMARY_PROMPT.format(content=content)


def zhipu_generate(prompt: str) -> str:
    response = zhipu.chat.completions.create(model=MODEL, messages=[{'role': 'user', 'content': prompt}])
    return response.choices[0].message.content.strip()


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
            readme_files = doc.get('readme_files') or []

            if not readme_files:
                tqdm.write(f'  [SKIP] {repo_id} — no readme files')
                skipped_repos.append(repo_id)
                continue

            # Skip if all summaries already filled
            if all(r.get('readme_file_summary') for r in readme_files):
                tqdm.write(f'  [SKIP] {repo_id} — already done')
                skipped_repos.append(repo_id)
                continue

            # Generate summary for each readme file one by one
            updated_readmes = []
            file_errors = []

            for r in readme_files:
                if r.get('readme_file_summary'):
                    updated_readmes.append(r)
                    continue

                tqdm.write(f'  [PROC] {repo_id} — {r["filename"]}')
                try:
                    prompt = build_prompt(r['content'])
                    summary = zhipu_generate(prompt)
                    updated_readmes.append({**r, 'readme_file_summary': summary})
                    tqdm.write(f'  [OK]   {repo_id} — {r["filename"]}')
                    time.sleep(SLEEP_BETWEEN_CALLS)
                except Exception as e:
                    tqdm.write(f'  [ERROR] {repo_id} — {r["filename"]}: {e}')
                    updated_readmes.append(r)
                    file_errors.append(r['filename'])

            # Update ES
            es.update(index=INDEX,
                      id=repo_id,
                      body={
                          'script': {
                              'source': 'ctx._source.readme_files = params.readme_files',
                              'params': {
                                  'readme_files': updated_readmes
                              }
                          }
                      })

            if file_errors:
                tqdm.write(f'  [WARN] {repo_id} — completed with errors on: {file_errors}')
                failed_repos.append(repo_id)
            else:
                success_repos.append(repo_id)

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
