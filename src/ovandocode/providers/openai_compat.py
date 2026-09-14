"""Proveedor generico para APIs compatibles con OpenAI /chat/completions.

Sirve como base para: OpenRouter, OpenAI, DeepSeek, Groq, Mistral, xAI,
LM Studio, Together, Fireworks y cualquier endpoint OpenAI-compatible.
"""
from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from ovandocode.providers.base import BaseProvider
from ovandocode.providers.types import (
    ChatRequest,
    ChatResponse,
    ProviderAuthError,
    ProviderConnectionError,
    ProviderRateLimitError,
    ProviderResponseError,
    ToolCall,
    Usage,
)


class OpenAICompatProvider(BaseProvider):
    """Cliente para cualquier endpoint compatible con OpenAI."""

    name = "openai_compat"
    default_base_url = "https://api.openai.com/v1"

    def __init__(self, **kw: Any) -> None:
        super().__init__(**kw)
        self._http = self._client(extra_headers=self._extra_headers())

    def _extra_headers(self) -> dict[str, str]:
        """Hook para subclases (OpenRouter agrega HTTP-Referer y X-Title)."""
        return {}

    # ---------------- payload ----------------
    def _payload(self, req: ChatRequest, stream: bool = False) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": req.model,
            "messages": [m.to_openai() for m in req.messages],
            "temperature": req.temperature,
        }
        if req.max_tokens:
            payload["max_tokens"] = req.max_tokens
        if req.tools:
            payload["tools"] = req.tools
        if stream:
            payload["stream"] = True
        return payload

    # ---------------- parsing ----------------
    @staticmethod
    def _parse_tool_calls(raw_calls: list[dict[str, Any]]) -> list[ToolCall]:
        out: list[ToolCall] = []
        for tc in raw_calls:
            fn = tc.get("function", {})
            raw_args = fn.get("arguments") or "{}"
            try:
                args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
            except json.JSONDecodeError:
                args = {"_raw": raw_args}
            out.append(ToolCall(id=tc.get("id", ""), name=fn.get("name", ""), arguments=args))
        return out

    def _parse(self, data: dict[str, Any], fallback_model: str) -> ChatResponse:
        try:
            choice = data["choices"][0]
        except (KeyError, IndexError) as e:
            raise ProviderResponseError(f"Respuesta sin 'choices': {data}") from e

        msg = choice.get("message", {})
        content = msg.get("content") or ""
        tool_calls = self._parse_tool_calls(msg.get("tool_calls") or [])
        u = data.get("usage") or {}
        return ChatResponse(
            content=content,
            tool_calls=tool_calls,
            usage=Usage(
                input_tokens=int(u.get("prompt_tokens") or 0),
                output_tokens=int(u.get("completion_tokens") or 0),
            ),
            model=data.get("model", fallback_model),
            finish_reason=choice.get("finish_reason"),
            raw=data,
        )

    # ---------------- errores ----------------
    def _raise_http(self, r: httpx.Response) -> None:
        if r.status_code in (401, 403):
            raise ProviderAuthError(f"{self.name}: {r.status_code} - {r.text[:300]}")
        if r.status_code == 429:
            raise ProviderRateLimitError(f"{self.name}: rate limit - {r.text[:300]}")
        if r.status_code >= 400:
            raise ProviderResponseError(f"{self.name}: {r.status_code} - {r.text[:300]}")

    # ---------------- API ----------------
    async def chat(self, req: ChatRequest) -> ChatResponse:
        self._require_key()
        try:
            r = await self._http.post("/chat/completions", json=self._payload(req))
        except httpx.RequestError as e:
            raise ProviderConnectionError(f"{self.name}: {e}") from e
        self._raise_http(r)
        return self._parse(r.json(), req.model)

    async def stream_chat(self, req: ChatRequest) -> AsyncIterator[str]:
        self._require_key()
        payload = self._payload(req, stream=True)
        try:
            async with self._http.stream("POST", "/chat/completions", json=payload) as r:
                self._raise_http(r)
                async for line in r.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    try:
                        delta = chunk["choices"][0].get("delta", {}).get("content")
                    except (KeyError, IndexError):
                        delta = None
                    if delta:
                        yield delta
        except httpx.RequestError as e:
            raise ProviderConnectionError(f"{self.name}: {e}") from e

    async def list_models(self) -> list[str]:
        """Lista modelos via GET /models (endpoint OpenAI-compatible)."""
        self._require_key()
        try:
            r = await self._http.get("/models")
        except httpx.RequestError as e:
            raise ProviderConnectionError(f"{self.name}: {e}") from e
        self._raise_http(r)
        try:
            data = r.json()
        except Exception as e:
            raise ProviderResponseError(f"{self.name}: respuesta no JSON: {e}") from None
        items = data.get("data") or []
        out: list[str] = []
        for m in items:
            mid = m.get("id") or m.get("name")
            if mid:
                out.append(str(mid))
        return sorted(out)

    async def close(self) -> None:
        await self._http.aclose()
