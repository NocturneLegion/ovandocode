"""Proveedor xAI (modelos Grok)."""
from __future__ import annotations

from ovandocode.providers.openai_compat import OpenAICompatProvider


class XAIProvider(OpenAICompatProvider):
    name = "xai"
    default_base_url = "https://api.x.ai/v1"