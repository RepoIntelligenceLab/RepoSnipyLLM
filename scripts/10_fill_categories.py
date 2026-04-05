import json
import os
from dotenv import load_dotenv
from elasticsearch import Elasticsearch
import pickle

load_dotenv()

ES_URL = os.getenv("ES_URL", "http://localhost:9200")
API_KEY = os.getenv("ES_API_KEY")
INDEX = "repositories_enriched_new"

es = Elasticsearch(ES_URL, api_key=API_KEY)

# update mapping
es.indices.put_mapping(index=INDEX, body={"properties": {"category": {"type": "keyword"}}})
print("Mapping updated")

# read Pickle file
pickle_path = "../data/AWESOME-PYTHON-REPOS.pkl"
with open(pickle_path, 'rb') as f:
    repos_dict = pickle.load(f)

success = 0
skipped = 0

for repo_id, category in repos_dict.items():
    # check if repo exists in ES
    if not es.exists(index=INDEX, id=repo_id):
        print(f"  [SKIP] {repo_id} — not in ES")
        skipped += 1
        continue

    es.update(index=INDEX, id=repo_id, doc={"category": category})
    print(f"  [OK] {repo_id} -> {category}")
    success += 1

print(f"\nDone. success={success}, skipped={skipped}")
