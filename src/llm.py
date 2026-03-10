"""
LLM client for RepoSnipy-LLM.
"""

from langchain_ollama import OllamaLLM

DEFAULT_MODEL = "qwen3:8b"


def generate(prompt: str, model: str = DEFAULT_MODEL) -> str:
    llm = OllamaLLM(model=model)
    return llm.invoke(prompt)
