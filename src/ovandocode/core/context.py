"""Gestion de contexto y auto-compactacion del historial."""
from __future__ import annotations

from dataclasses import dataclass

from ovandocode.core.messages import estimate_tokens, summarize_for_compact
from ovandocode.providers.types import Message

# Limites por defecto (tokens aproximados)
DEFAULT_CONTEXT_LIMIT = 128_000
DEFAULT_KEEP_LAST = 8


@dataclass
class ContextStats:
    messages: int
    estimated_tokens: int
    context_limit: int
    usage_pct: float
    needs_compact: bool


class ContextManager:
    """Encapsula la politica de compactacion.

    Metodos:
      - stats(messages): devuelve uso actual vs limite.
      - should_compact(messages): True si supera el umbral.
      - compact(messages, summarize_fn=None): reduce el historial.
    """

    def __init__(
        self,
        context_limit: int = DEFAULT_CONTEXT_LIMIT,
        threshold: float = 0.8,
        keep_last: int = DEFAULT_KEEP_LAST,
    ) -> None:
        if not 0.0 < threshold <= 1.0:
            raise ValueError("threshold debe estar en (0, 1]")
        if keep_last < 2:
            raise ValueError("keep_last debe ser >= 2")
        self.context_limit = context_limit
        self.threshold = threshold
        self.keep_last = keep_last

    # ---------------- stats ----------------
    def stats(self, messages: list[Message]) -> ContextStats:
        tokens = estimate_tokens(messages)
        pct = tokens / self.context_limit if self.context_limit else 0.0
        return ContextStats(
            messages=len(messages),
            estimated_tokens=tokens,
            context_limit=self.context_limit,
            usage_pct=round(pct, 4),
            needs_compact=pct >= self.threshold,
        )

    def should_compact(self, messages: list[Message]) -> bool:
        return self.stats(messages).needs_compact

    # ---------------- compactacion ----------------
    def compact(
        self,
        messages: list[Message],
        summarize_fn=None,
    ) -> tuple[list[Message], str]:
        """Reduce el historial preservando:
          - El system prompt (si esta en el historial).
          - Los ultimos N mensajes (keep_last).
          - Un resumen del medio.

        `summarize_fn` es opcional: recibe los mensajes viejos y devuelve un str.
        Si no se pasa, se usa summarize_for_compact() (sin LLM).
        Devuelve (nuevos_mensajes, resumen).
        """
        if len(messages) <= self.keep_last + 1:
            return messages, ""

        # Separar system prompt del inicio si existe
        head: list[Message] = []
        body = messages
        if messages and messages[0].role == "system":
            head = [messages[0]]
            body = messages[1:]

        if len(body) <= self.keep_last:
            return messages, ""

        old = body[: -self.keep_last]
        tail = body[-self.keep_last :]

        if summarize_fn is not None:
            try:
                summary_text = summarize_fn(old)
            except Exception:
                summary_text = summarize_for_compact(old, keep_last=0)
        else:
            summary_text = summarize_for_compact(old, keep_last=0)

        summary_msg = Message(
            role="user",
            content=(
                "[Contexto previo resumido]\n"
                f"{summary_text}\n\n"
                "[Continua la conversacion desde aqui.]"
            ),
        )
        new_messages = head + [summary_msg] + tail
        return new_messages, summary_text