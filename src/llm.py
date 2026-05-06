"""
LLM client for RepoSnipy-LLM.

Supports:
  - Ollama local models  (model="qwen3:8b" etc.)
  - DeepSeek API         (model="deepseek-chat" etc.)
  - ZhipuAI API          (model="glm-4.7-flash" etc.)
"""

import os

from dotenv import load_dotenv
from langchain_ollama import OllamaLLM
from openai import OpenAI
from zai import ZhipuAiClient

load_dotenv()

DEFAULT_MODEL = "zhipu:glm-4.7-flash"
SUPPORTED_PROVIDERS = {"deepseek", "zhipu", "ollama"}
PROVIDER_MODELS = {
    "deepseek": ["deepseek-v4-flash", "deepseek-chat",],
    "zhipu":    ["glm-4.7-flash"],
    "ollama":   ["qwen3:8b"],
}

_deepseek_client = None
_zhipu_client = None
_ollama_client = None


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


def _get_ollama_client(model: str) -> OllamaLLM:
    global _ollama_client
    if _ollama_client is None:
        _ollama_client = OllamaLLM(model=model)
    return _ollama_client


def generate(prompt: str, model: str = DEFAULT_MODEL) -> str:
    """
    Generate a response from the specified model.

    model="deepseek:deepseek-chat"      → DeepSeek API (deepseek-chat)
    model="zhipu:glm-4.7-flash"         → ZhipuAI API (glm-4.7-flash)
    model="ollama:qwen3:8b" etc. → Ollama local model
    """

    def _parse_model(model: str) -> tuple[str, str]:
        """Parse 'provider:model_name' and validate provider.

        Raises ValueError on malformed input or unsupported provider.
        """
        if ":" not in model:
            raise ValueError(f"Invalid model format '{model}'. Expected 'provider:model_name'.")
        provider, _, model_name = model.partition(":")
        provider = provider.strip().lower()
        model_name = model_name.strip()
        if not provider:
            raise ValueError(f"Provider part is empty in model string '{model}'.")
        if not model_name:
            raise ValueError(f"Model name part is empty in model string '{model}'.")
        if provider not in SUPPORTED_PROVIDERS:
            raise ValueError(f"Unknown provider '{provider}'. Supported: {sorted(SUPPORTED_PROVIDERS)}.")
        return provider, model_name

    provider, model_name = _parse_model(model)

    try:
        if provider == "deepseek":
            client = _get_deepseek_client()
            response = client.chat.completions.create(model=model_name, messages=[{"role": "user", "content": prompt}])
            content = response.choices[0].message.content
            if content is None:
                raise RuntimeError(f"DeepSeek returned empty response for '{model_name}'.")
            return content

        elif provider == "zhipu":
            client = _get_zhipu_client()
            response = client.chat.completions.create(model=model_name, messages=[{"role": "user", "content": prompt}])
            content = response.choices[0].message.content
            if content is None:
                raise RuntimeError(f"Zhipu returned empty response for '{model_name}'.")
            return content

        elif provider == "ollama":
            llm = _get_ollama_client(model_name)
            result = llm.invoke(prompt)
            if not result:
                raise RuntimeError(f"Ollama returned empty response for '{model_name}'.")
            return result

    except (ValueError, RuntimeError):
        # Let callers handle parsing/runtime validation errors explicitly
        raise
    except Exception as exc:
        raise RuntimeError(f"LLM call failed for provider='{provider}', model='{model_name}': {exc}") from exc
