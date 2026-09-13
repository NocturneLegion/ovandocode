"""Helpers para manipular historial de mensajes."""
from __future__ import annotations

import json
from typing import Any

from ovandocode.providers.types import Message, ToolCall


def user(content: str) -> Message:
    return Message(role="user", content=content)


def system(content: str) -> Message:
    return Message(role="system", content=content)


def assistant(content: str = "", tool_calls: list[ToolCall] | None = None) -> Message:
    return Message(role="assistant", content=content, tool_calls=tool_calls or [])


def tool_result(tool_call_id: str, name: str, content: str) -> Message:
    return Message(role="tool", content=content, tool_call_id=tool_call_id, name=name)


def to_dict(msg: Message) -> dict[str, Any]:
    """Serializa un Message a dict plano (para JSONL)."""
    d: dict[str, Any] = {"role": msg.role, "content": msg.content}
    if msg.tool_calls:
        d["tool_calls"] = [
            {"id": tc.id, "name": tc.name, "arguments": tc.arguments}
            for tc in msg.tool_calls
        ]
    if msg.tool_call_id:
        d["tool_call_id"] = msg.tool_call_id
    if msg.name:
        d["name"] = msg.name
    return d


def from_dict(d: dict[str, Any]) -> Message:
    """Reconstruye un Message desde dict."""
    tcs = [
        ToolCall(id=t["id"], name=t["name"], arguments=t.get("arguments") or {})
        for t in d.get("tool_calls", [])
    ]
    return Message(
        role=d["role"],
        content=d.get("content") or "",
        tool_calls=tcs,
        tool_call_id=d.get("tool_call_id"),
        name=d.get("name"),
    )


def estimate_tokens(messages: list[Message]) -> int:
    """Estimacion grosera de tokens (4 chars ~ 1 token).

    Sirve como heuristica para auto-compactar; no reemplaza al tokenizer real.
    """
    total_chars = 0
    for m in messages:
        total_chars += len(m.content or "")
        for tc in m.tool_calls:
            total_chars += len(json.dumps(tc.arguments, ensure_ascii=False))
            total_chars += len(tc.name)
    return max(1, total_chars // 4)


def summarize_for_compact(messages: list[Message], keep_last: int = 6) -> str:
    """Genera un resumen textual de los mensajes viejos (sin LLM).

    Se usa cuando falla la compactacion via LLM o como fallback rapido.
    """
    if len(messages) <= keep_last:
        return ""
    old = messages[:-keep_last]
    lines: list[str] = []
    for m in old:
        content = (m.content or "").strip().replace("\n", " ")
        if len(content) > 200:
            content = content[:200] + "..."
        if m.tool_calls:
            names = ", ".join(tc.name for tc in m.tool_calls)
            lines.append(f"[{m.role}] {content} (tools: {names})")
        else:
            lines.append(f"[{m.role}] {content}")
    return "\n".join(lines)