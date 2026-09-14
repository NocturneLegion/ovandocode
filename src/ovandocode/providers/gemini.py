"""Proveedor Google Gemini (API generativelanguage nativa)."""
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

GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"


class GeminiProvider(BaseProvider):
    name = "gemini"
    default_base_url = GEMINI_BASE

    def __init__(self, **kw: Any) -> None:
        super().__init__(**kw)
        self._http = httpx.AsyncClient(
            base_url=self.base_url.rstrip("/"),
            timeout=self.timeout,
            headers={"Content-Type": "application/json"},
        )

    # ---------------- conversion ----------------
    @staticmethod
    def _to_gemini_contents(req: ChatRequest) -> tuple[str | None, list[dict[str, Any]]]:
        sys_parts: list[str] = []
        out: list[dict[str, Any]] = []
        for m in req.messages:
            if m.role == "system":
                sys_parts.append(m.content)
            elif m.role == "user":
                out.append({"role": "user", "parts": [{"text": m.content}]})
            elif m.role == "assistant":
                parts: list[dict[str, Any]] = []
                if m.content:
                    parts.append({"text": m.content})
                for tc in m.tool_calls:
                    parts.append({"functionCall": {"name": tc.name, "args": tc.arguments}})
                out.append({"role": "model", "parts": parts or [{"text": ""}]})
            elif m.role == "tool":
                out.append({
                    "role": "user",
                    "parts": [{
                        "functionResponse": {
                            "name": m.name or "tool",
                            "response": {"result": m.content},
                        },
                    }],
                })
        return ("\n\n".join(sys_parts) if sys_parts else None), out

    @staticmethod
    def _convert_tools(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        decls: list[dict[str, Any]] = []
        for t in tools:
            fn = t.get("function", t)
            decls.append({
                "name": fn.get("name", ""),
                "description": fn.get("description", ""),
                "parameters": fn.get("parameters", {"type": "object", "properties": {}}),
            })
        return [{"functionDeclarations": decls}]

    def _payload(self, req: ChatRequest) -> dict[str, Any]:
        system, contents = self._to_gemini_contents(req)
        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": req.temperature,
            },
        }
        if req.max_tokens:
            payload["generationConfig"]["maxOutputTokens"] = req.max_tokens
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}
        if req.tools:
            payload["tools"] = self._convert_tools(req.tools)
        return payload

    # ---------------- parsing ----------------
    @staticmethod
    def _parse(data: dict[str, Any], fallback_model: str) -> ChatResponse:
        candidates = data.get("candidates") or []
        if not candidates:
            raise ProviderResponseError(f"gemini: respuesta sin candidates: {data}")
        parts = candidates[0].get("content", {}).get("parts", [])
        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []
        for p in parts:
            if "text" in p:
                text_parts.append(p["text"])
            elif "functionCall" in p:
                fc = p["functionCall"]
                tool_calls.append(ToolCall(
                    id=f"call_{fc.get('name','')}_{len(tool_calls)}",
                    name=fc.get("name", ""),
                    arguments=fc.get("args", {}) or {},
                ))
        um = data.get("usageMetadata") or {}
        return ChatResponse(
            content="".join(text_parts),
            tool_calls=tool_calls,
            usage=Usage(
                input_tokens=int(um.get("promptTokenCount") or 0),
                output_tokens=int(um.get("candidatesTokenCount") or 0),
            ),
            model=data.get("modelVersion", fallback_model),
            finish_reason=candidates[0].get("finishReason"),
            raw=data,
        )

    def _raise_http(self, r: httpx.Response) -> None:
        if r.status_code in (401, 403):
            raise ProviderAuthError(f"gemini: {r.status_code} - {r.text[:300]}")
        if r.status_code == 429:
            raise ProviderRateLimitError(f"gemini: rate limit - {r.text[:300]}")
        if r.status_code >= 400:
            raise ProviderResponseError(f"gemini: {r.status_code} - {r.text[:300]}")

    # ---------------- API ----------------
    async def chat(self, req: ChatRequest) -> ChatResponse:
        self._require_key()
        url = f"/models/{req.model}:generateContent?key={self.api_key}"
        try:
            r = await self._http.post(url, json=self._payload(req))
        except httpx.RequestError as e:
            raise ProviderConnectionError(f"gemini: {e}") from e
        self._raise_http(r)
        return self._parse(r.json(), req.model)

    async def stream_chat(self, req: ChatRequest) -> AsyncIterator[str]:
        self._require_key()
        url = f"/models/{req.model}:streamGenerateContent?alt=sse&key={self.api_key}"
        try:
            async with self._http.stream("POST", url, json=self._payload(req)) as r:
                self._raise_http(r)
                async for line in r.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    try:
                        evt = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    for cand in evt.get("candidates", []):
                        for p in cand.get("content", {}).get("parts", []):
                            if "text" in p:
                                yield p["text"]
        except httpx.RequestError as e:
            raise ProviderConnectionError(f"gemini: {e}") from e

    async def close(self) -> None:
        await self._http.aclose()
