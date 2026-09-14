"""Proveedor Anthropic (API Messages nativa)."""
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

ANTHROPIC_VERSION = "2023-06-01"


class AnthropicProvider(BaseProvider):
    name = "anthropic"
    default_base_url = "https://api.anthropic.com/v1"

    def __init__(self, **kw: Any) -> None:
        super().__init__(**kw)
        # Anthropic usa x-api-key en vez de Authorization: Bearer
        self._http = httpx.AsyncClient(
            base_url=self.base_url.rstrip("/"),
            timeout=self.timeout,
            headers={
                "Content-Type": "application/json",
                "x-api-key": self.api_key or "",
                "anthropic-version": ANTHROPIC_VERSION,
            },
        )

    # ---------------- conversion ----------------
    @staticmethod
    def _to_anthropic_messages(
        req: ChatRequest,
    ) -> tuple[str | None, list[dict[str, Any]]]:
        system_parts: list[str] = []
        out: list[dict[str, Any]] = []
        for m in req.messages:
            if m.role == "system":
                system_parts.append(m.content)
            elif m.role == "tool":
                out.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": m.tool_call_id or "",
                        "content": m.content,
                    }],
                })
            elif m.role == "assistant":
                blocks: list[dict[str, Any]] = []
                if m.content:
                    blocks.append({"type": "text", "text": m.content})
                for tc in m.tool_calls:
                    blocks.append({
                        "type": "tool_use",
                        "id": tc.id,
                        "name": tc.name,
                        "input": tc.arguments,
                    })
                out.append({"role": "assistant", "content": blocks or [{"type": "text", "text": ""}]})
            else:  # user
                out.append({"role": "user", "content": [{"type": "text", "text": m.content}]})
        return ("\n\n".join(system_parts) if system_parts else None), out

    @staticmethod
    def _convert_tools(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Convierte tools formato OpenAI -> Anthropic."""
        out: list[dict[str, Any]] = []
        for t in tools:
            fn = t.get("function", t)
            out.append({
                "name": fn.get("name", ""),
                "description": fn.get("description", ""),
                "input_schema": fn.get("parameters", {"type": "object", "properties": {}}),
            })
        return out

    # ---------------- payload ----------------
    def _payload(self, req: ChatRequest, stream: bool = False) -> dict[str, Any]:
        system, msgs = self._to_anthropic_messages(req)
        payload: dict[str, Any] = {
            "model": req.model,
            "messages": msgs,
            "max_tokens": req.max_tokens or 4096,
            "temperature": req.temperature,
        }
        if system:
            payload["system"] = system
        if req.tools:
            payload["tools"] = self._convert_tools(req.tools)
        if stream:
            payload["stream"] = True
        return payload

    # ---------------- parsing ----------------
    @staticmethod
    def _parse(data: dict[str, Any], fallback_model: str) -> ChatResponse:
        content_parts: list[str] = []
        tool_calls: list[ToolCall] = []
        for block in data.get("content", []):
            if block.get("type") == "text":
                content_parts.append(block.get("text", ""))
            elif block.get("type") == "tool_use":
                tool_calls.append(ToolCall(
                    id=block.get("id", ""),
                    name=block.get("name", ""),
                    arguments=block.get("input", {}) or {},
                ))
        u = data.get("usage") or {}
        return ChatResponse(
            content="".join(content_parts),
            tool_calls=tool_calls,
            usage=Usage(
                input_tokens=int(u.get("input_tokens") or 0),
                output_tokens=int(u.get("output_tokens") or 0),
            ),
            model=data.get("model", fallback_model),
            finish_reason=data.get("stop_reason"),
            raw=data,
        )

    # ---------------- errores ----------------
    def _raise_http(self, r: httpx.Response) -> None:
        if r.status_code in (401, 403):
            raise ProviderAuthError(f"anthropic: {r.status_code} - {r.text[:300]}")
        if r.status_code == 429:
            raise ProviderRateLimitError(f"anthropic: rate limit - {r.text[:300]}")
        if r.status_code >= 400:
            raise ProviderResponseError(f"anthropic: {r.status_code} - {r.text[:300]}")

    # ---------------- API ----------------
    async def chat(self, req: ChatRequest) -> ChatResponse:
        self._require_key()
        try:
            r = await self._http.post("/messages", json=self._payload(req))
        except httpx.RequestError as e:
            raise ProviderConnectionError(f"anthropic: {e}") from e
        self._raise_http(r)
        return self._parse(r.json(), req.model)

    async def stream_chat(self, req: ChatRequest) -> AsyncIterator[str]:
        self._require_key()
        try:
            async with self._http.stream("POST", "/messages", json=self._payload(req, True)) as r:
                self._raise_http(r)
                async for line in r.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    try:
                        evt = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    if evt.get("type") == "content_block_delta":
                        delta = evt.get("delta", {}).get("text")
                        if delta:
                            yield delta
        except httpx.RequestError as e:
            raise ProviderConnectionError(f"anthropic: {e}") from e

    async def list_models(self) -> list[str]:
        """Lista modelos via GET /v1/models (Anthropic)."""
        self._require_key()
        try:
            r = await self._http.get("/models", params={"limit": 1000})
        except httpx.RequestError as e:
            raise ProviderConnectionError(f"anthropic: {e}") from e
        self._raise_http(r)
        try:
            data = r.json()
        except Exception as e:
            raise ProviderResponseError(f"anthropic: respuesta no JSON: {e}") from None
        items = data.get("data") or []
        out = [str(m.get("id")) for m in items if m.get("id")]
        return sorted(out)

    async def close(self) -> None:
        await self._http.aclose()
