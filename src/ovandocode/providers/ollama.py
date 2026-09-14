"""Proveedor Ollama (modelos locales via endpoint OpenAI-compatible)."""
from __future__ import annotations

from ovandocode.providers.openai_compat import OpenAICompatProvider


class OllamaProvider(OpenAICompatProvider):
    name = "ollama"
    requires_api_key = False
    default_base_url = "http://localhost:11434/v1"
