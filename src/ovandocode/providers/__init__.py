"""Proveedores LLM de OVANDOCODE.

Uso:
    from ovandocode.providers import create_provider
    p = create_provider("openrouter", api_key="sk-...")
    resp = await p.chat(req)
"""
from __future__ import annotations

from typing import Any

from ovandocode.config import get_credentials, get_settings
from ovandocode.providers.anthropic import AnthropicProvider
from ovandocode.providers.base import BaseProvider
from ovandocode.providers.deepseek import DeepSeekProvider
from ovandocode.providers.gemini import GeminiProvider
from ovandocode.providers.groq import GroqProvider
from ovandocode.providers.lmstudio import LMStudioProvider
from ovandocode.providers.mistral import MistralProvider
from ovandocode.providers.ollama import OllamaProvider
from ovandocode.providers.openai import OpenAIProvider
from ovandocode.providers.openai_compat import OpenAICompatProvider
from ovandocode.providers.openrouter import OpenRouterProvider
from ovandocode.providers.types import (
    ChatRequest,
    ChatResponse,
    Message,
    ProviderAuthError,
    ProviderConnectionError,
    ProviderError,
    ProviderRateLimitError,
    ProviderResponseError,
    ToolCall,
    Usage,
)
from ovandocode.providers.xai import XAIProvider

REGISTRY: dict[str, type[BaseProvider]] = {
    "openrouter": OpenRouterProvider,
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "gemini": GeminiProvider,
    "deepseek": DeepSeekProvider,
    "groq": GroqProvider,
    "mistral": MistralProvider,
    "xai": XAIProvider,
    "ollama": OllamaProvider,
    "lmstudio": LMStudioProvider,
}


def list_providers() -> list[str]:
    """Devuelve los nombres de todos los proveedores registrados."""
    return sorted(REGISTRY.keys())


def create_provider(
    name: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    **kwargs: Any,
) -> BaseProvider:
    """Crea una instancia del proveedor indicado.

    Si no se pasa `name`, usa el default de Settings.
    Si no se pasa `api_key`, la resuelve via CredentialManager.
    """
    settings = get_settings()
    name = (name or settings.default_provider).lower()

    if name not in REGISTRY:
        raise ValueError(
            f"Proveedor desconocido: '{name}'. Disponibles: {list_providers()}"
        )

    cls = REGISTRY[name]

    # Resolver API key si no se paso
    if api_key is None and cls.requires_api_key:
        api_key = get_credentials().get(name)

    # Resolver base_url para locales via settings
    if base_url is None:
        if name == "ollama":
            base_url = settings.ollama_base_url.rstrip("/") + "/v1"
        elif name == "lmstudio":
            base_url = settings.lmstudio_base_url

    return cls(
        api_key=api_key,
        base_url=base_url,
        timeout=settings.request_timeout,
        **kwargs,
    )


__all__ = [
    "REGISTRY",
    "AnthropicProvider",
    "BaseProvider",
    "ChatRequest",
    "ChatResponse",
    "DeepSeekProvider",
    "GeminiProvider",
    "GroqProvider",
    "LMStudioProvider",
    "Message",
    "MistralProvider",
    "OllamaProvider",
    "OpenAICompatProvider",
    "OpenAIProvider",
    "OpenRouterProvider",
    "ProviderAuthError",
    "ProviderConnectionError",
    "ProviderError",
    "ProviderRateLimitError",
    "ProviderResponseError",
    "ToolCall",
    "Usage",
    "XAIProvider",
    "create_provider",
    "list_providers",
]
