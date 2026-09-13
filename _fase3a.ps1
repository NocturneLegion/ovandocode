# ============================================================
#  OVANDOCODE - FASE 3a: tipos base, BaseProvider, OpenAI-compat
#  Guardar como: D:\Trabajo\OvandoCode\_fase3a.ps1
# ============================================================
$ErrorActionPreference = 'Stop'
$ProjectRoot = 'D:\Trabajo\OvandoCode'
Set-Location $ProjectRoot
$utf8 = New-Object System.Text.UTF8Encoding $false

Write-Host "=== OVANDOCODE :: Fase 3a - Capa de proveedores ===" -ForegroundColor Cyan

$prov = "$ProjectRoot\src\ovandocode\providers"
if (-not (Test-Path $prov)) { New-Item -ItemType Directory -Path $prov -Force | Out-Null }

# ------------------------------------------------------------
# 3a.1 providers/types.py
# ------------------------------------------------------------
$types = @'
"""Tipos compartidos entre todos los proveedores LLM."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Role = Literal["system", "user", "assistant", "tool"]


@dataclass
class ToolCall:
    """Llamada a una herramienta solicitada por el modelo."""
    id: str
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)

    def to_openai(self) -> dict[str, Any]:
        import json
        return {
            "id": self.id,
            "type": "function",
            "function": {
                "name": self.name,
                "arguments": json.dumps(self.arguments, ensure_ascii=False),
            },
        }


@dataclass
class Message:
    """Mensaje en el historial de conversacion."""
    role: Role
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_call_id: str | None = None
    name: str | None = None

    def to_openai(self) -> dict[str, Any]:
        d: dict[str, Any] = {"role": self.role, "content": self.content}
        if self.tool_calls:
            d["tool_calls"] = [tc.to_openai() for tc in self.tool_calls]
        if self.tool_call_id:
            d["tool_call_id"] = self.tool_call_id
        if self.name:
            d["name"] = self.name
        return d


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass
class ChatRequest:
    """Solicitud de completado a un proveedor."""
    messages: list[Message]
    model: str
    tools: list[dict[str, Any]] = field(default_factory=list)
    temperature: float = 0.2
    max_tokens: int | None = None


@dataclass
class ChatResponse:
    """Respuesta normalizada de cualquier proveedor."""
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    usage: Usage = field(default_factory=Usage)
    model: str = ""
    finish_reason: str | None = None
    raw: dict[str, Any] | None = None


# ---------------- Excepciones ----------------
class ProviderError(Exception):
    """Error generico de proveedor."""


class ProviderAuthError(ProviderError):
    """Autenticacion invalida (401/403)."""


class ProviderRateLimitError(ProviderError):
    """Rate limit (429)."""


class ProviderConnectionError(ProviderError):
    """Fallo de red o timeout."""


class ProviderResponseError(ProviderError):
    """Respuesta inesperada del proveedor."""
'@
[IO.File]::WriteAllText("$prov\types.py", $types, $utf8)
Write-Host "[OK] providers/types.py" -ForegroundColor Green

# ------------------------------------------------------------
# 3a.2 providers/base.py
# ------------------------------------------------------------
$base = @'
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
'@
[IO.File]::WriteAllText("$prov\base.py", $base, $utf8)
Write-Host "[OK] providers/base.py" -ForegroundColor Green

# ------------------------------------------------------------
# 3a.3 providers/openai_compat.py
# ------------------------------------------------------------
$compat = @'
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
    Message,
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

    async def close(self) -> None:
        await self._http.aclose()
'@
[IO.File]::WriteAllText("$prov\openai_compat.py", $compat, $utf8)
Write-Host "[OK] providers/openai_compat.py" -ForegroundColor Green

# ------------------------------------------------------------
# 3a.4 Verificacion rapida
# ------------------------------------------------------------
Write-Host "`n-> probando imports..." -ForegroundColor Yellow
uv run python -c "from ovandocode.providers.types import Message, ChatRequest, ChatResponse; from ovandocode.providers.base import BaseProvider; from ovandocode.providers.openai_compat import OpenAICompatProvider; print('imports OK')"

# ------------------------------------------------------------
# 3a.5 Commit
# ------------------------------------------------------------
Write-Host "`n-> commit..." -ForegroundColor Yellow
git add .
git commit -m "Fase 3a: tipos base y proveedor OpenAI-compatible" | Out-Null

Write-Host "`n=== Verificacion Fase 3a ===" -ForegroundColor Cyan
$checks = [ordered]@{
    'providers/types.py'          = (Test-Path 'src\ovandocode\providers\types.py')
    'providers/base.py'           = (Test-Path 'src\ovandocode\providers\base.py')
    'providers/openai_compat.py'  = (Test-Path 'src\ovandocode\providers\openai_compat.py')
    'imports base funcionan'      = [bool](uv run python -c "from ovandocode.providers.openai_compat import OpenAICompatProvider" 2>$null)
    'commit Fase 3a'              = [bool](git log --oneline 2>$null | Select-String 'Fase 3a')
}
foreach ($k in $checks.Keys) {
    $ok = $checks[$k]
    $mark  = if ($ok) { '[OK]' } else { '[!!]' }
    $color = if ($ok) { 'Green' } else { 'Red' }
    Write-Host "$mark $k" -ForegroundColor $color
}

Write-Host "`nFase 3a completada." -ForegroundColor Cyan