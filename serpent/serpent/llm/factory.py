"""Factory for creating LLM clients and loading registry."""

from pathlib import Path
from typing import Optional

import yaml

from serpent.config import SerpentConfig
from serpent.llm.anthropic import AnthropicClient
from serpent.llm.base import LLMClient
from serpent.llm.gemini import GeminiClient
from serpent.llm.openai import OpenAIClient


class ModelInfo:
    """Information about a model."""
    def __init__(self, data: dict) -> None:
        self.name = data.get("name", "Unknown")
        self.context_window = data.get("context_window", 128000)
        self.max_output_tokens = data.get("max_output_tokens", 4096)
        self.supports_thinking = data.get("supports_thinking", False)
        self.supports_tool_use = data.get("supports_tool_use", True)


class ProviderInfo:
    """Information about a provider."""
    def __init__(self, name: str, data: dict) -> None:
        self.name = data.get("name", name)
        self.base_url = data.get("base_url", "")
        self.models = {
            k: ModelInfo(v) for k, v in data.get("models", {}).items()
        }


class Registry:
    """Loaded provider registry."""
    def __init__(self, data: dict) -> None:
        self.providers = {
            k: ProviderInfo(k, v) for k, v in data.get("providers", {}).items()
        }


def load_registry() -> Registry:
    """Load the providers registry from YAML."""
    paths = [
        Path("providers.yaml"),
        Path(__file__).parent.parent.parent / "providers.yaml",
    ]
    
    for path in paths:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            return Registry(data)
    
    return Registry({"providers": {}})


def create_client(config: SerpentConfig) -> LLMClient:
    """Create an LLM client based on configuration."""
    registry = load_registry()
    provider_info = registry.providers.get(config.provider)
    
    if not provider_info:
        raise ValueError(f"Unknown provider: {config.provider}")
    
    api_key = config.api_key
    if not api_key:
        provider_config = config.providers.get(config.provider)
        if provider_config:
            api_key = provider_config.api_key
    
    if not api_key:
        import os
        env_var = f"{config.provider.upper()}_API_KEY"
        api_key = os.environ.get(env_var) or os.environ.get("OPENAI_API_KEY", "")
    
    if not api_key:
        raise ValueError(f"No API key found for provider {config.provider}. Set {env_var} or add to config.")
    
    base_url = None
    if config.providers and config.provider in config.providers:
        base_url = config.providers[config.provider].base_url
    if not base_url and provider_info:
        base_url = provider_info.base_url
    
    if config.provider == "anthropic":
        return AnthropicClient(api_key, config.model, base_url)
    elif config.provider in ("openai", "deepseek", "moonshot"):
        return OpenAIClient(api_key, config.model, base_url)
    elif config.provider == "google":
        return GeminiClient(api_key, config.model, base_url)
    else:
        raise ValueError(f"Unsupported provider: {config.provider}")