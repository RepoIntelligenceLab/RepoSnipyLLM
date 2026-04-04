"""
generate_embeddings.py

Reads repository data from repositories_enriched ES index,
generates embeddings using UniXcoder (Henry65/RepoSim4Py pipeline),
and saves results to a pkl file.

Output pkl structure:
{
    "repo_id": {
        "code_embeddings":            np.ndarray (N, 768),
        "mean_code_embedding":        np.ndarray (1, 768),
        "doc_embeddings":             np.ndarray (N, 768),
        "mean_doc_embedding":         np.ndarray (1, 768),
        "requirement_embeddings":     np.ndarray (N, 768),
        "mean_requirement_embedding": np.ndarray (1, 768),
        "readme_embeddings":          np.ndarray (N, 768),
        "mean_readme_embedding":      np.ndarray (1, 768),
        "mean_repo_embedding":        np.ndarray (1, 3072),
    },
    ...
}

Usage:
  python 7_generate_embeddings.py
  python 7_generate_embeddings.py --limit 10
  python 7_generate_embeddings.py --repos 567-labs/instructor django/django
  nohup python -u 7_generate_embeddings.py > logs/embeddings.log 2>&1 &
"""

from __future__ import annotations

import argparse
import os
import pickle
from pathlib import Path

import numpy as np
import torch
from dotenv import load_dotenv
from elasticsearch import Elasticsearch
from tqdm import tqdm
from transformers import pipeline

load_dotenv()

ES_URL = os.getenv("ES_URL", "http://localhost:9200")
API_KEY = os.getenv("ES_API_KEY")
INDEX = "repositories_enriched_new"
MODEL_NAME = "Henry65/RepoSim4Py"
OUTPUT_PKL = Path("../data/repo_embeddings/repo_info_embeddings.pkl")
MAX_LENGTH = 512
DEVICE = 0 if torch.cuda.is_available() else -1

# ── ES client ─────────────────────────────────────────────────────────────────


def get_es_client() -> Elasticsearch:
    return Elasticsearch(ES_URL, api_key=API_KEY)


def get_all_repo_ids(es: Elasticsearch) -> list[str]:
    repo_ids = []
    resp = es.search(index=INDEX, body={"query": {"match_all": {}}, "_source": False, "size": 1000}, scroll="2m")
    scroll_id = resp["_scroll_id"]
    hits = resp["hits"]["hits"]
    while hits:
        repo_ids.extend(hit["_id"] for hit in hits)
        resp = es.scroll(scroll_id=scroll_id, scroll="2m")
        scroll_id = resp["_scroll_id"]
        hits = resp["hits"]["hits"]
    es.clear_scroll(scroll_id=scroll_id)
    return repo_ids


# ── Data extraction from ES doc ───────────────────────────────────────────────


def extract_codes(doc: dict) -> set[str]:
    codes = set()
    for file_entry in (doc.get("files") or []):
        for fn in (file_entry.get("functions") or []):
            src = fn.get("source_code")
            if src:
                codes.add(src)
            for nested_fn in (fn.get("functions") or []):
                src = nested_fn.get("source_code")
                if src:
                    codes.add(src)
        for cls in (file_entry.get("classes") or []):
            for method in (cls.get("methods") or []):
                src = method.get("source_code")
                if src:
                    codes.add(src)
    return codes


def extract_docs(doc: dict) -> set[str]:
    docs = set()
    for file_entry in (doc.get("files") or []):
        for fn in (file_entry.get("functions") or []):
            d = fn.get("doc") or {}
            for field in ("short_description", "long_description"):
                val = d.get(field)
                if val:
                    docs.add(val)
            for nested_fn in (fn.get("functions") or []):
                d = nested_fn.get("doc") or {}
                for field in ("short_description", "long_description"):
                    val = d.get(field)
                    if val:
                        docs.add(val)
        for cls in (file_entry.get("classes") or []):
            d = cls.get("doc") or {}
            for field in ("short_description", "long_description"):
                val = d.get(field)
                if val:
                    docs.add(val)
            for method in (cls.get("methods") or []):
                d = method.get("doc") or {}
                for field in ("short_description", "long_description"):
                    val = d.get(field)
                    if val:
                        docs.add(val)
    return docs


def extract_requirements(doc: dict) -> set[str]:
    reqs = set()
    requirements = doc.get("requirements") or {}
    for k in requirements:
        if not k.startswith("#"):
            reqs.add(k)
    return reqs


def extract_readmes(doc: dict) -> set[str]:
    readmes = set()
    for r in (doc.get("readme_files") or []):
        content = r.get("content") or ""
        for line in content.split("\n"):
            line = line.strip()
            if line:
                readmes.add(line)
    return readmes


# ── Embedding generation ──────────────────────────────────────────────────────


def encode(model_pipeline, text: str, max_length: int) -> torch.Tensor:
    """Encode a single text using UniXcoder via the pipeline's encode method."""
    return model_pipeline.encode(text, max_length)


def generate_embeddings_for_set(model_pipeline,
                                text_set: set[str],
                                max_length: int,
                                batch_size: int = 64) -> np.ndarray:
    if not text_set:
        return torch.zeros((1, 768)).cpu().numpy()

    texts = list(text_set)
    all_embeddings = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        with torch.no_grad():
            batch_embeddings = torch.cat([model_pipeline.encode(text, max_length) for text in batch], dim=0)
            all_embeddings.append(batch_embeddings.cpu().numpy())
            del batch_embeddings
            torch.cuda.empty_cache()

    return np.concatenate(all_embeddings, axis=0)


def generate_repo_embeddings(model_pipeline, doc: dict) -> dict:
    """Generate all embeddings for a single repository document."""
    codes = extract_codes(doc)
    docs = extract_docs(doc)
    requirements = extract_requirements(doc)
    readmes = extract_readmes(doc)

    code_embeddings = generate_embeddings_for_set(model_pipeline, codes, MAX_LENGTH)
    doc_embeddings = generate_embeddings_for_set(model_pipeline, docs, MAX_LENGTH)
    req_embeddings = generate_embeddings_for_set(model_pipeline, requirements, MAX_LENGTH)
    readme_embeddings = generate_embeddings_for_set(model_pipeline, readmes, MAX_LENGTH)

    mean_code = code_embeddings.mean(axis=0, keepdims=True)
    mean_doc = doc_embeddings.mean(axis=0, keepdims=True)
    mean_req = req_embeddings.mean(axis=0, keepdims=True)
    mean_readme = readme_embeddings.mean(axis=0, keepdims=True)

    mean_repo = np.concatenate([mean_code, mean_doc, mean_req, mean_readme], axis=1)

    return {
        "code_embeddings": code_embeddings,
        "mean_code_embedding": mean_code,
        "doc_embeddings": doc_embeddings,
        "mean_doc_embedding": mean_doc,
        "requirement_embeddings": req_embeddings,
        "mean_requirement_embedding": mean_req,
        "readme_embeddings": readme_embeddings,
        "mean_readme_embedding": mean_readme,
        "mean_repo_embedding": mean_repo,
    }


# ── Main ──────────────────────────────────────────────────────────────────────


def main(limit: int | None = None, repos: list[str] | None = None):
    print(f"Device: {'GPU' if DEVICE == 0 else 'CPU'}")
    print(f"Loading model: {MODEL_NAME}")
    model_pipeline = pipeline(model=MODEL_NAME, trust_remote_code=True, device=DEVICE)
    print("Model loaded.\n")

    es = get_es_client()
    print(f"ES: {es.info()['version']['number']}")

    if repos:
        repo_ids = repos
    else:
        repo_ids = get_all_repo_ids(es)

    if limit:
        repo_ids = repo_ids[:limit]

    print(f"Total repos to process: {len(repo_ids)}\n")

    # Load existing pkl if it exists (for resume support)
    if OUTPUT_PKL.exists():
        with open(OUTPUT_PKL, "rb") as f:
            results = pickle.load(f)
        print(f"Resuming from existing pkl ({len(results)} already done)\n")
    else:
        results = {}

    success = 0
    skipped = 0
    failed = 0
    failed_repos = []

    for repo_id in tqdm(repo_ids, desc="Generating embeddings"):
        if repo_id in results:
            tqdm.write(f"  [SKIP] {repo_id} — already done")
            skipped += 1
            continue

        try:
            doc = es.get(index=INDEX, id=repo_id)["_source"]
        except Exception as e:
            tqdm.write(f"  [ERROR] {repo_id} — ES fetch failed: {e}")
            failed += 1
            failed_repos.append(repo_id)
            continue

        try:
            embeddings = generate_repo_embeddings(model_pipeline, doc)
            results[repo_id] = embeddings
            tqdm.write(f"  [OK] {repo_id} — mean_repo_embedding shape: {embeddings['mean_repo_embedding'].shape}")
            success += 1

            # Save after each repo for safety
            with open(OUTPUT_PKL, "wb") as f:
                pickle.dump(results, f)

        except Exception as e:
            tqdm.write(f"  [ERROR] {repo_id} — embedding failed: {e}")
            failed += 1
            failed_repos.append(repo_id)

    print()
    print("=" * 60)
    print(f"Done.")
    print(f"  Success : {success}")
    print(f"  Skipped : {skipped}")
    print(f"  Failed  : {failed}")
    if failed_repos:
        print(f"\nFailed repos:")
        for r in failed_repos:
            print(f"  {r}")
    print(f"\nSaved to: {OUTPUT_PKL}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", "-n", type=int, default=None)
    parser.add_argument("--repos", "-r", nargs="+", default=None)
    args = parser.parse_args()
    main(limit=args.limit, repos=args.repos)
