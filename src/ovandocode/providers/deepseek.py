"""Proveedor DeepSeek."""
from __future__ import annotations

from ovandocode.providers.openai_compat import OpenAICompatProvider


class DeepSeekProvider(OpenAICompatProvider):
    name = "deepseek"
    default_base_url = "https://api.deepseek.com/v1"