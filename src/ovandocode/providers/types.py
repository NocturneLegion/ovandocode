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