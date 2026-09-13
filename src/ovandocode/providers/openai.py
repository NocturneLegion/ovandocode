"""Proveedor OpenAI oficial."""
from __future__ import annotations

from ovandocode.providers.openai_compat import OpenAICompatProvider


class OpenAIProvider(OpenAICompatProvider):
    name = "openai"
    default_base_url = "https://api.openai.com/v1"