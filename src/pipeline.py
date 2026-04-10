"""
Pipeline for RepoSnipy-LLM.

Controller layer: orchestrates data loading, prompt building,
LLM calls, and logging for each question type.
"""

from __future__ import annotations

import math
import os

from dotenv import load_dotenv
from elasticsearch import Elasticsearch

from src.data_loader import load_repo, load_repos
from src.prompt_builder import (
    build_single_repo_prompt,
    build_batch_summarise_prompt,
    build_final_compare_prompt,
    build_final_similar_prompt,
    _format_repo_block,
)
from src.llm import generate
from src.logger import save as save_log

load_dotenv()

GROUP_SIZE = 5

INDEX = "repositories_enriched_new"
ES_URL = os.getenv("ES_URL", "http://localhost:9200")
API_KEY = os.getenv("ES_API_KEY")

# ── ES client ─────────────────────────────────────────────────────────────────


def _get_es_client() -> Elasticsearch:
    return Elasticsearch(ES_URL, api_key=API_KEY)


# ── Embedding retrieval ───────────────────────────────────────────────────────


def _similarity_search(repo_id: str, topk: int) -> list[str]:
    es = _get_es_client()
    doc = es.get(index=INDEX, id=repo_id)["_source"]
    embedding = doc.get("embedding")
    if not embedding:
        raise ValueError(f"Repository '{repo_id}' has no embedding stored.")

    resp = es.search(index=INDEX,
                     body={
                         "query": {
                             "script_score": {
                                 "query": {
                                     "bool": {
                                         "must": {
                                             "exists": {
                                                 "field": "embedding"
                                             }
                                         },
                                         "must_not": {
                                             "term": {
                                                 "_id": repo_id
                                             }
                                         }
                                     }
                                 },
                                 "script": {
                                     "source": "cosineSimilarity(params.query_vector, 'embedding') + 1.0",
                                     "params": {
                                         "query_vector": embedding
                                     }
                                 }
                             }
                         },
                         "size": topk,
                         "_source": False,
                     })

    hits = resp["hits"]["hits"]
    return [hit["_id"] for hit in hits if hit["_id"] != repo_id][:topk]


# ── Summarisation ─────────────────────────────────────────────────────────────


def _get_group_summaries(
    repo_data_list: list[dict],
    question_config: dict,
    model: str,
) -> tuple[list[str], list[str]]:
    """
    Return (group_summaries, group_contexts).

    If len <= GROUP_SIZE: format retrieval info directly (no LLM call).
    If len > GROUP_SIZE: batch summarise in groups via LLM.
    """
    if len(repo_data_list) <= GROUP_SIZE:
        blocks = [
            f"### {r['repo_name']}\n\n{_format_repo_block(r, question_config['retrieval'])}" for r in repo_data_list
        ]
        combined = "\n\n---\n\n".join(blocks)
        return [combined], [combined]

    group_summaries = []
    group_contexts = []
    n_groups = math.ceil(len(repo_data_list) / GROUP_SIZE)

    for i in range(n_groups):
        group = repo_data_list[i * GROUP_SIZE:(i + 1) * GROUP_SIZE]
        prompt, context = build_batch_summarise_prompt(question_config, group)
        summary = generate(prompt, model)
        group_summaries.append(summary)
        group_contexts.append(context)

    return group_summaries, group_contexts


# ── Handlers ──────────────────────────────────────────────────────────────────


def _handle_single(
    question_config: dict,
    repos: list[str],
    model: str,
) -> tuple[str, str, str]:
    if len(repos) != 1:
        raise ValueError(f"This question requires exactly one repository. Got: {repos}")
    repo_data = load_repo(repos[0], question_config["retrieval"])
    prompt, context = build_single_repo_prompt(question_config, repo_data)
    answer = generate(prompt, model)
    return prompt, answer, context


def _handle_search(
    question_config: dict,
    repos: list[str],
    model: str,
) -> tuple[str, str, str]:
    if len(repos) < 2:
        raise ValueError("This question requires at least two repositories.")

    repo_data_list = load_repos(repos, question_config["retrieval"])
    group_summaries, group_contexts = _get_group_summaries(repo_data_list, question_config, model)
    prompt, context = build_final_compare_prompt(question_config, group_summaries)
    answer = generate(prompt, model)
    return prompt, answer, context


def _handle_similar(
    question_config: dict,
    repos: list[str],
    model: str,
    topk: int,
) -> tuple[str, str, str]:
    if len(repos) != 1:
        raise ValueError("This question requires exactly one reference repository.")

    reference_name = repos[0]
    candidate_names = _similarity_search(reference_name, topk)

    reference_data = load_repo(reference_name, question_config["retrieval"])
    candidate_data_list = load_repos(candidate_names, question_config["retrieval"])

    reference_block = (f"### {reference_name}\n\n"
                       f"{_format_repo_block(reference_data, question_config['retrieval'])}")

    group_summaries, group_contexts = _get_group_summaries(candidate_data_list, question_config, model)
    prompt, context = build_final_similar_prompt(question_config, reference_block, group_summaries)
    answer = generate(prompt, model)
    return prompt, answer, context


# ── Public API ────────────────────────────────────────────────────────────────

HANDLERS = {
    "single": _handle_single,
    "search": _handle_search,
    "similar": _handle_similar,
}


def run_question(
    question_config: dict,
    repos: list[str],
    model: str,
    topk: int = 10,
    logdir: str | None = None,
    task_id: str = "",
    question_id: str = "",
) -> tuple[str, str, str]:
    """
    Run a question and return (prompt, answer, context).
    Routes to the appropriate handler based on question_config['handler'].
    """
    handler_name = question_config.get("handler")
    if handler_name not in HANDLERS:
        raise ValueError(f"Unknown handler '{handler_name}'. Available: {list(HANDLERS.keys())}")

    handler = HANDLERS[handler_name]

    if handler_name == "similar":
        prompt, answer, context = handler(question_config, repos, model, topk)
    else:
        prompt, answer, context = handler(question_config, repos, model)

    if logdir:
        save_log(
            logdir=logdir,
            task_id=task_id,
            question_id=question_id,
            repos=repos,
            prompt=prompt,
            answer=answer,
            model=model,
        )

    return prompt, answer, context
