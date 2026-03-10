"""
Run RepoSnipyLLM Question 1 with LangChain + Ollama.

Prereqs:
  - Ollama running locally (default: http://localhost:11434)
  - pip install langchain langchain-ollama

Input:
  - q1_retrieved.json produced by build_q1_json.py

Output:
  - Prints the LLM answer to stdout
"""

from __future__ import annotations

import json
import argparse
from pathlib import Path
from typing import Any, Dict, List

from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate

PROMPT_1 = """You are given documentation and structural information extracted from a software repository.

Using ONLY the information provided below, answer the following:

1. What is the main purpose or goal of this repository?
2. What type of software is it (e.g. library, application, script-based project), based on the available evidence?
3. How is the software installed, if installation instructions are provided?
4. How is the software intended to be used or executed?

If any of these points cannot be determined from the provided information, explicitly state that the information is not available.

Do NOT make assumptions.
Do NOT introduce information that is not supported by the retrieved documents.

Retrieved information:
{retrieved_documents}
"""


def format_retrieved_documents(docs: List[Dict[str, Any]]) -> str:
    """
    Convert retrieved docs into a readable, provenance-preserving text block.
    """
    blocks: List[str] = []
    for i, d in enumerate(docs, start=1):
        doc_type = d.get("doc_type", "unknown")
        path = d.get("path")
        content = d.get("content")

        header = f"[{i}] doc_type={doc_type}"
        if path:
            header += f" | path={path}"
        blocks.append(header)

        # Keep it simple; dump JSON for structured items.
        if isinstance(content, (dict, list)):
            blocks.append(json.dumps(content, ensure_ascii=False, indent=2))
        else:
            blocks.append(str(content))

        blocks.append("")
    return "\n".join(blocks).strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="inp", default="q1_retrieved.json", help="Input JSON path")
    parser.add_argument("--model", dest="model", default="llama3.1", help="Ollama model name, e.g. qwen2.5:7b")
    parser.add_argument("--base-url", dest="base_url", default="http://localhost:11434", help="Ollama base URL")
    parser.add_argument("--temperature", dest="temperature", type=float, default=0.0, help="Sampling temperature")
    args = parser.parse_args()

    payload = json.loads(Path(args.inp).read_text(encoding="utf-8"))
    docs = payload.get("retrieved_documents", [])
    retrieved_text = format_retrieved_documents(docs)

    llm = ChatOllama(
        model=args.model,
        base_url=args.base_url,
        temperature=args.temperature,
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a careful assistant that must follow the instructions strictly."),
        ("human", PROMPT_1),
    ])

    chain = prompt | llm
    resp = chain.invoke({"retrieved_documents": retrieved_text})

    print("\n" + "=" * 80)
    print(f"Repo: {payload.get('repo_name', 'unknown')}")
    print("=" * 80 + "\n")
    print(resp.content.strip())
    print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    main()
