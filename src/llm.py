"""
LLM client for RepoSnipy-LLM.

Supports:
  - Ollama local models  (model="qwen3:8b" etc.)
  - DeepSeek API         (model="deepseek")
  - ZhipuAI API          (model="zhipu")
"""

import os

from dotenv import load_dotenv
from langchain_ollama import OllamaLLM
from openai import OpenAI
from zai import ZhipuAiClient

load_dotenv()

DEFAULT_MODEL = "deepseek"

_deepseek_client = None
_zhipu_client = None


def _get_deepseek_client() -> OpenAI:
    global _deepseek_client
    if _deepseek_client is None:
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY not set in .env")
        _deepseek_client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    return _deepseek_client


def _get_zhipu_client() -> ZhipuAiClient:
    global _zhipu_client
    if _zhipu_client is None:
        api_key = os.getenv("ZHIPU_API_KEY")
        if not api_key:
            raise ValueError("ZHIPU_API_KEY not set in .env")
        _zhipu_client = ZhipuAiClient(api_key=api_key)
    return _zhipu_client


def generate(prompt: str, model: str = DEFAULT_MODEL) -> str:
    """
    Generate a response from the specified model.

    model="deepseek"      → DeepSeek API (deepseek-chat)
    model="zhipu"         → ZhipuAI API (glm-4.7-flash)
    model="qwen3:8b" etc. → Ollama local model
    """
    if model == "deepseek":
        client = _get_deepseek_client()
        response = client.chat.completions.create(model="deepseek-chat", messages=[{"role": "user", "content": prompt}])
        return response.choices[0].message.content

    if model == "zhipu":
        client = _get_zhipu_client()
        response = client.chat.completions.create(model="glm-4.7-flash", messages=[{"role": "user", "content": prompt}])
        return response.choices[0].message.content

    # Ollama fallback
    llm = OllamaLLM(model=model)
    return llm.invoke(prompt)
