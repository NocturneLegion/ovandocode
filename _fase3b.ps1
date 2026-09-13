# ============================================================
#  OVANDOCODE - FASE 3b: proveedores concretos
#  Guardar como: D:\Trabajo\OvandoCode\_fase3b.ps1
# ============================================================
$ErrorActionPreference = 'Stop'
$ProjectRoot = 'D:\Trabajo\OvandoCode'
Set-Location $ProjectRoot
$utf8 = New-Object System.Text.UTF8Encoding $false

Write-Host "=== OVANDOCODE :: Fase 3b - Proveedores concretos ===" -ForegroundColor Cyan

$prov = "$ProjectRoot\src\ovandocode\providers"

# ------------------------------------------------------------
# 3b.1 OpenRouter
# ------------------------------------------------------------
$openrouter = @'
"""Proveedor OpenRouter (agregador de modelos)."""
from __future__ import annotations

from typing import Any

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
'@
[IO.File]::WriteAllText("$prov\openrouter.py", $openrouter, $utf8)
Write-Host "[OK] providers/openrouter.py" -ForegroundColor Green

# ------------------------------------------------------------
# 3b.2 OpenAI
# ------------------------------------------------------------
$openai = @'
"""Proveedor OpenAI oficial."""
from __future__ import annotations

from ovandocode.providers.openai_compat import OpenAICompatProvider


class OpenAIProvider(OpenAICompatProvider):
    name = "openai"
    default_base_url = "https://api.openai.com/v1"
'@
[IO.File]::WriteAllText("$prov\openai.py", $openai, $utf8)
Write-Host "[OK] providers/openai.py" -ForegroundColor Green

# ------------------------------------------------------------
# 3b.3 DeepSeek
# ------------------------------------------------------------
$deepseek = @'
"""Proveedor DeepSeek."""
from __future__ import annotations

from ovandocode.providers.openai_compat import OpenAICompatProvider


class DeepSeekProvider(OpenAICompatProvider):
    name = "deepseek"
    default_base_url = "https://api.deepseek.com/v1"
'@
[IO.File]::WriteAllText("$prov\deepseek.py", $deepseek, $utf8)
Write-Host "[OK] providers/deepseek.py" -ForegroundColor Green

# ------------------------------------------------------------
# 3b.4 Groq
# ------------------------------------------------------------
$groq = @'
"""Proveedor Groq (inferencia ultra rapida)."""
from __future__ import annotations

from ovandocode.providers.openai_compat import OpenAICompatProvider


class GroqProvider(OpenAICompatProvider):
    name = "groq"
    default_base_url = "https://api.groq.com/openai/v1"
'@
[IO.File]::WriteAllText("$prov\groq.py", $groq, $utf8)
Write-Host "[OK] providers/groq.py" -ForegroundColor Green

# ------------------------------------------------------------
# 3b.5 Mistral
# ------------------------------------------------------------
$mistral = @'
"""Proveedor Mistral AI."""
from __future__ import annotations

from ovandocode.providers.openai_compat import OpenAICompatProvider


class MistralProvider(OpenAICompatProvider):
    name = "mistral"
    default_base_url = "https://api.mistral.ai/v1"
'@
[IO.File]::WriteAllText("$prov\mistral.py", $mistral, $utf8)
Write-Host "[OK] providers/mistral.py" -ForegroundColor Green

# ------------------------------------------------------------
# 3b.6 xAI (Grok)
# ------------------------------------------------------------
$xai = @'
"""Proveedor xAI (modelos Grok)."""
from __future__ import annotations

from ovandocode.providers.openai_compat import OpenAICompatProvider


class XAIProvider(OpenAICompatProvider):
    name = "xai"
    default_base_url = "https://api.x.ai/v1"
'@
[IO.File]::WriteAllText("$prov\xai.py", $xai, $utf8)
Write-Host "[OK] providers/xai.py" -ForegroundColor Green

# ------------------------------------------------------------
# 3b.7 Ollama (local)
# ------------------------------------------------------------
$ollama = @'
"""Proveedor Ollama (modelos locales via endpoint OpenAI-compatible)."""
from __future__ import annotations

from ovandocode.providers.openai_compat import OpenAICompatProvider


class OllamaProvider(OpenAICompatProvider):
    name = "ollama"
    requires_api_key = False
    default_base_url = "http://localhost:11434/v1"
'@
[IO.File]::WriteAllText("$prov\ollama.py", $ollama, $utf8)
Write-Host "[OK] providers/ollama.py" -ForegroundColor Green

# ------------------------------------------------------------
# 3b.8 LM Studio (local)
# ------------------------------------------------------------
$lmstudio = @'
"""Proveedor LM Studio (servidor local OpenAI-compatible)."""
from __future__ import annotations

from ovandocode.providers.openai_compat import OpenAICompatProvider


class LMStudioProvider(OpenAICompatProvider):
    name = "lmstudio"
    requires_api_key = False
    default_base_url = "http://localhost:1234/v1"
'@
[IO.File]::WriteAllText("$prov\lmstudio.py", $lmstudio, $utf8)
Write-Host "[OK] providers/lmstudio.py" -ForegroundColor Green

# ------------------------------------------------------------
# 3b.9 Anthropic (implementacion nativa, no OpenAI-compat)
# ------------------------------------------------------------
$anthropic = @'
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

    async def close(self) -> None:
        await self._http.aclose()
'@
[IO.File]::WriteAllText("$prov\anthropic.py", $anthropic, $utf8)
Write-Host "[OK] providers/anthropic.py" -ForegroundColor Green

# ------------------------------------------------------------
# 3b.10 Google Gemini (implementacion nativa)
# ------------------------------------------------------------
$gemini = @'
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
'@
[IO.File]::WriteAllText("$prov\gemini.py", $gemini, $utf8)
Write-Host "[OK] providers/gemini.py" -ForegroundColor Green

# ------------------------------------------------------------
# 3b.11 providers/__init__.py con factory
# ------------------------------------------------------------
$provinit = @'
"""Proveedores LLM de OVANDOCODE.

Uso:
    from ovandocode.providers import create_provider
    p = create_provider("openrouter", api_key="sk-...")
    resp = await p.chat(req)
"""
from __future__ import annotations

from typing import Any

from ovandocode.config import get_credentials, get_settings
from ovandocode.providers.anthropic import AnthropicProvider
from ovandocode.providers.base import BaseProvider
from ovandocode.providers.deepseek import DeepSeekProvider
from ovandocode.providers.gemini import GeminiProvider
from ovandocode.providers.groq import GroqProvider
from ovandocode.providers.lmstudio import LMStudioProvider
from ovandocode.providers.mistral import MistralProvider
from ovandocode.providers.ollama import OllamaProvider
from ovandocode.providers.openai import OpenAIProvider
from ovandocode.providers.openai_compat import OpenAICompatProvider
from ovandocode.providers.openrouter import OpenRouterProvider
from ovandocode.providers.types import (
    ChatRequest,
    ChatResponse,
    Message,
    ProviderAuthError,
    ProviderConnectionError,
    ProviderError,
    ProviderRateLimitError,
    ProviderResponseError,
    ToolCall,
    Usage,
)
from ovandocode.providers.xai import XAIProvider

REGISTRY: dict[str, type[BaseProvider]] = {
    "openrouter": OpenRouterProvider,
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "gemini": GeminiProvider,
    "deepseek": DeepSeekProvider,
    "groq": GroqProvider,
    "mistral": MistralProvider,
    "xai": XAIProvider,
    "ollama": OllamaProvider,
    "lmstudio": LMStudioProvider,
}


def list_providers() -> list[str]:
    """Devuelve los nombres de todos los proveedores registrados."""
    return sorted(REGISTRY.keys())


def create_provider(
    name: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    **kwargs: Any,
) -> BaseProvider:
    """Crea una instancia del proveedor indicado.

    Si no se pasa `name`, usa el default de Settings.
    Si no se pasa `api_key`, la resuelve via CredentialManager.
    """
    settings = get_settings()
    name = (name or settings.default_provider).lower()

    if name not in REGISTRY:
        raise ValueError(
            f"Proveedor desconocido: '{name}'. Disponibles: {list_providers()}"
        )

    cls = REGISTRY[name]

    # Resolver API key si no se paso
    if api_key is None and cls.requires_api_key:
        api_key = get_credentials().get(name)

    # Resolver base_url para locales via settings
    if base_url is None:
        if name == "ollama":
            base_url = settings.ollama_base_url.rstrip("/") + "/v1"
        elif name == "lmstudio":
            base_url = settings.lmstudio_base_url

    return cls(
        api_key=api_key,
        base_url=base_url,
        timeout=settings.request_timeout,
        **kwargs,
    )


__all__ = [
    "AnthropicProvider",
    "BaseProvider",
    "ChatRequest",
    "ChatResponse",
    "DeepSeekProvider",
    "GeminiProvider",
    "GroqProvider",
    "LMStudioProvider",
    "Message",
    "MistralProvider",
    "OllamaProvider",
    "OpenAICompatProvider",
    "OpenAIProvider",
    "OpenRouterProvider",
    "ProviderAuthError",
    "ProviderConnectionError",
    "ProviderError",
    "ProviderRateLimitError",
    "ProviderResponseError",
    "REGISTRY",
    "ToolCall",
    "Usage",
    "XAIProvider",
    "create_provider",
    "list_providers",
]
'@
[IO.File]::WriteAllText("$prov\__init__.py", $provinit, $utf8)
Write-Host "[OK] providers/__init__.py" -ForegroundColor Green

# ------------------------------------------------------------
# 3b.12 Actualizar CLI: comando `providers list` y `providers ping`
# ------------------------------------------------------------
$cliPath = "$ProjectRoot\src\ovandocode\cli.py"
$cliContent = [IO.File]::ReadAllText($cliPath)

# Insertar el sub-app providers antes de "def main()"
$providersCmd = @'
providers_app = typer.Typer(help="Proveedores LLM disponibles.")
app.add_typer(providers_app, name="providers")


@providers_app.command("list")
def providers_list() -> None:
    """Lista proveedores registrados y su estado."""
    from ovandocode.providers import REGISTRY, list_providers
    cm = get_credentials()
    typer.echo("== Proveedores LLM ==")
    for name in list_providers():
        cls = REGISTRY[name]
        status = cm.source_of(name) if cls.requires_api_key else "local"
        ok = "OK " if (status != "none" or not cls.requires_api_key) else "-- "
        key_req = "requiere key" if cls.requires_api_key else "sin key"
        typer.echo(f"  [{ok}] {name:<12} {key_req:<13} source={status}")


@providers_app.command("ping")
def providers_ping(
    provider: str = typer.Argument(...),
    model: str = typer.Option(None, "--model", "-m"),
) -> None:
    """Envia un prompt trivial a un proveedor para verificar conectividad."""
    import asyncio

    from ovandocode.providers import Message, create_provider
    from ovandocode.providers.types import ChatRequest

    async def _go() -> None:
        p = create_provider(provider)
        chosen = model or get_settings().default_model
        typer.echo(f"-> {provider} :: {chosen}")
        async with p:
            resp = await p.chat(ChatRequest(
                messages=[Message(role="user", content="Responde solo: PONG")],
                model=chosen,
                max_tokens=16,
            ))
        typer.secho(f"respuesta: {resp.content.strip()!r}", fg="green")
        typer.echo(f"tokens: in={resp.usage.input_tokens} out={resp.usage.output_tokens}")

    try:
        asyncio.run(_go())
    except Exception as e:
        typer.secho(f"[ERR] {type(e).__name__}: {e}", fg="red")
        raise typer.Exit(1)


def main() -> None:
'@

$cliContent = $cliContent -replace '(?ms)^def main\(\) -> None:', $providersCmd
[IO.File]::WriteAllText($cliPath, $cliContent, $utf8)
Write-Host "[OK] cli.py actualizado (providers list/ping)" -ForegroundColor Green

# ------------------------------------------------------------
# 3b.13 Verificacion
# ------------------------------------------------------------
Write-Host "`n-> probando imports y CLI..." -ForegroundColor Yellow
uv run python -c "from ovandocode.providers import list_providers, create_provider; print('OK:', list_providers())"
uv run ovandocode providers list

# ------------------------------------------------------------
# 3b.14 Commit
# ------------------------------------------------------------
Write-Host "`n-> commit..." -ForegroundColor Yellow
git add .
git commit -m "Fase 3b: 10 proveedores LLM + factory + CLI providers" | Out-Null

Write-Host "`n=== Verificacion Fase 3b ===" -ForegroundColor Cyan
$checks = [ordered]@{
    'providers/openrouter.py' = (Test-Path 'src\ovandocode\providers\openrouter.py')
    'providers/openai.py'     = (Test-Path 'src\ovandocode\providers\openai.py')
    'providers/anthropic.py'  = (Test-Path 'src\ovandocode\providers\anthropic.py')
    'providers/gemini.py'     = (Test-Path 'src\ovandocode\providers\gemini.py')
    'providers/deepseek.py'   = (Test-Path 'src\ovandocode\providers\deepseek.py')
    'providers/groq.py'       = (Test-Path 'src\ovandocode\providers\groq.py')
    'providers/mistral.py'    = (Test-Path 'src\ovandocode\providers\mistral.py')
    'providers/xai.py'        = (Test-Path 'src\ovandocode\providers\xai.py')
    'providers/ollama.py'     = (Test-Path 'src\ovandocode\providers\ollama.py')
    'providers/lmstudio.py'   = (Test-Path 'src\ovandocode\providers\lmstudio.py')
    'registry importa'        = [bool](uv run python -c "from ovandocode.providers import list_providers" 2>$null)
    'providers list funciona' = [bool](uv run ovandocode providers list 2>$null)
    'commit Fase 3b'          = [bool](git log --oneline 2>$null | Select-String 'Fase 3b')
}
foreach ($k in $checks.Keys) {
    $ok = $checks[$k]
    $mark  = if ($ok) { '[OK]' } else { '[!!]' }
    $color = if ($ok) { 'Green' } else { 'Red' }
    Write-Host "$mark $k" -ForegroundColor $color
}

Write-Host "`nFase 3b completada." -ForegroundColor Cyan