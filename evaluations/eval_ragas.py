"""
eval_ragas.py

RAGAS evaluation on the collected (question, context, answer) triples.

Metrics:
  - Faithfulness                         : Is the answer grounded in the retrieved context?
  - Answer Relevance                     : Does the answer actually address the question?
  - Context Precision (without reference): Is the retrieved context relevant to the question?

LLM judge  : DeepSeek (deepseek-chat) via OpenAI-compatible API
Embeddings : Local sentence-transformers (all-mpnet-base-v2, 768 dims, no API key needed)

Input:
  results/ragas_dataset.json

Output:
  results/ragas_raw.csv     : per-triple scores
  results/ragas_summary.csv : mean scores grouped by handler and task

Usage:
  cd evaluations/
  python eval_ragas.py
  python eval_ragas.py --dataset results/ragas_dataset.json
  nohup python -u eval_ragas.py > logs/eval_ragas.log 2>&1 &

Dependencies:
  pip install ragas langchain-openai langchain-community sentence-transformers datasets
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
from datasets import Dataset
from dotenv import load_dotenv
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI
from ragas import evaluate
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.llms import LangchainLLMWrapper
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    LLMContextPrecisionWithoutReference,
)

load_dotenv()

RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)

DATASET_PATH = RESULTS_DIR / "ragas_dataset.json"
RAW_OUTPUT = RESULTS_DIR / "ragas_raw.csv"
SUMMARY_OUTPUT = RESULTS_DIR / "ragas_summary.csv"

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"

EMBEDDING_MODEL = "sentence-transformers/all-mpnet-base-v2"

# ── Models ────────────────────────────────────────────────────────────────────


def get_llm() -> LangchainLLMWrapper:
    """DeepSeek as RAGAS judge LLM."""
    if not DEEPSEEK_API_KEY:
        raise ValueError("DEEPSEEK_API_KEY not set in .env")
    langchain_llm = ChatOpenAI(
        model=DEEPSEEK_MODEL,
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
        temperature=0,
    )
    return LangchainLLMWrapper(langchain_llm)


def get_embeddings() -> LangchainEmbeddingsWrapper:
    """Local sentence-transformers for answer_relevancy metric (no API key needed)."""
    hf_embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL, )
    return LangchainEmbeddingsWrapper(hf_embeddings)


# ── Data loading ──────────────────────────────────────────────────────────────


def load_triples(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}\nRun collect_ragas_data.py first.")
    with open(path) as f:
        data = json.load(f)
    triples = list(data.values())
    print(f"Loaded {len(triples)} triples from {path}")
    return triples


def build_ragas_dataset(triples: list[dict]) -> Dataset:
    """
    RAGAS expects columns: question, contexts (list), answer
    """
    return Dataset.from_list([{
        "question": t["question"],
        "contexts": [t["context"]],
        "answer": t["answer"],
    } for t in triples])


# ── Evaluation ────────────────────────────────────────────────────────────────


def run_ragas(dataset: Dataset, llm, embeddings) -> pd.DataFrame:
    result = evaluate(
        dataset=dataset,
        metrics=[
            faithfulness,
            answer_relevancy,
            LLMContextPrecisionWithoutReference(),
        ],
        llm=llm,
        embeddings=embeddings,
    )
    return result.to_pandas()


# ── Main ──────────────────────────────────────────────────────────────────────


def main(dataset_path: Path = DATASET_PATH):
    triples = load_triples(dataset_path)
    ragas_dataset = build_ragas_dataset(triples)

    print(f"\nLLM judge  : DeepSeek ({DEEPSEEK_MODEL})")
    print(f"Embeddings : Local sentence-transformers ({EMBEDDING_MODEL})")
    print(f"Metrics    : faithfulness, answer_relevancy, context_precision_without_reference\n")

    llm = get_llm()
    embeddings = get_embeddings()

    df = run_ragas(ragas_dataset, llm, embeddings)

    # Add metadata columns back
    for col in ["task", "question_id", "handler", "repo"]:
        df[col] = [t.get(col, "") for t in triples]

    # Save raw
    df.to_csv(RAW_OUTPUT, index=False)
    print(f"\nRaw results saved to:  {RAW_OUTPUT}")

    METRIC_COLS = ["faithfulness", "answer_relevancy", "llm_context_precision_without_reference"]

    # Summary by handler
    summary_handler = (df.groupby("handler")[METRIC_COLS].mean().round(4))

    # Summary by task
    summary_task = (df.groupby("task")[METRIC_COLS].mean().round(4))

    # Overall
    summary_overall = (df[METRIC_COLS].mean().round(4))

    # Save summary
    with open(SUMMARY_OUTPUT, "w") as f:
        f.write("=== Overall ===\n")
        summary_overall.to_csv(f)
        f.write("\n=== By Handler ===\n")
        summary_handler.to_csv(f)
        f.write("\n=== By Task ===\n")
        summary_task.to_csv(f)

    print(f"Summary saved to:      {SUMMARY_OUTPUT}")

    print("\n" + "=" * 60)
    print("RAGAS EVALUATION SUMMARY")
    print("=" * 60)

    print("\n--- Overall ---")
    print(summary_overall.to_string())

    print("\n--- By Handler ---")
    print(summary_handler.to_string())

    print("\n--- By Task ---")
    print(summary_task.to_string())


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=str(DATASET_PATH))
    args = parser.parse_args()
    main(dataset_path=Path(args.dataset))
