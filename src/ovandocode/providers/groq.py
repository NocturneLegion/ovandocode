"""Proveedor Groq (inferencia ultra rapida)."""
from __future__ import annotations

from ovandocode.providers.openai_compat import OpenAICompatProvider


class GroqProvider(OpenAICompatProvider):
    name = "groq"
    default_base_url = "https://api.groq.com/openai/v1"
