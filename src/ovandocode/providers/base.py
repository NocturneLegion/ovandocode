"""Clase base abstracta para todos los proveedores LLM."""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

import httpx

from ovandocode.providers.types import ChatRequest, ChatResponse


class BaseProvider(ABC):
    """Interfaz comun que todo proveedor debe implementar.

    Ciclo de vida:
        async with SomeProvider(api_key=...) as p:
            resp = await p.chat(req)
            async for chunk in p.stream_chat(req):
                ...
    """

    name: str = "base"
    requires_api_key: bool = True
    default_base_url: str = ""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 120.0,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url or self.default_base_url
        self.timeout = timeout

    # ---------------- API requerida ----------------
    @abstractmethod
    async def chat(self, req: ChatRequest) -> ChatResponse:
        """Envia una solicitud de completado y devuelve la respuesta completa."""

    @abstractmethod
    def stream_chat(self, req: ChatRequest) -> AsyncIterator[str]:
        """Envia una solicitud y emite deltas de texto a medida que llegan."""

    # ---------------- Ciclo de vida ----------------
    async def close(self) -> None:
        """Libera recursos (conexiones HTTP). Sobrescribir si aplica."""

    async def __aenter__(self) -> "BaseProvider":
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()

    # ---------------- Utilidades ----------------
    def _require_key(self) -> str:
        from ovandocode.providers.types import ProviderAuthError
        if self.requires_api_key and not self.api_key:
            raise ProviderAuthError(
                f"Proveedor '{self.name}' requiere API key y no se encontro ninguna."
            )
        return self.api_key or ""

    def _client(self, extra_headers: dict[str, str] | None = None) -> httpx.AsyncClient:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        if extra_headers:
            headers.update(extra_headers)
        return httpx.AsyncClient(
            base_url=self.base_url.rstrip("/"),
            timeout=self.timeout,
            headers=headers,
        )