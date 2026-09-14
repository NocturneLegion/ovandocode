"""Proveedor LM Studio (servidor local OpenAI-compatible)."""
from __future__ import annotations

from ovandocode.providers.openai_compat import OpenAICompatProvider


class LMStudioProvider(OpenAICompatProvider):
    name = "lmstudio"
    requires_api_key = False
    default_base_url = "http://localhost:1234/v1"
