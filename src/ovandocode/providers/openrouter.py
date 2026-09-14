"""Proveedor OpenRouter (agregador de modelos)."""
from __future__ import annotations

from ovandocode.providers.openai_compat import OpenAICompatProvider


class OpenRouterProvider(OpenAICompatProvider):
    name = "openrouter"
    default_base_url = "https://openrouter.ai/api/v1"

    def _extra_headers(self) -> dict[str, str]:
        # Headers opcionales recomendados por OpenRouter para atribucion
        return {
            "HTTP-Referer": "https://github.com/ovandocode/ovandocode",
            "X-Title": "OVANDOCODE",
        }
