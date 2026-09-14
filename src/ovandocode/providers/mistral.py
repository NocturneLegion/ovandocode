"""Proveedor Mistral AI."""
from __future__ import annotations

from ovandocode.providers.openai_compat import OpenAICompatProvider


class MistralProvider(OpenAICompatProvider):
    name = "mistral"
    default_base_url = "https://api.mistral.ai/v1"
