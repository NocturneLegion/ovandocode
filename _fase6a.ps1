# ============================================================
#  OVANDOCODE - FASE 6a: messages, session, context
#  Guardar como: D:\Trabajo\OvandoCode\_fase6a.ps1
# ============================================================
$ErrorActionPreference = 'Stop'
$ProjectRoot = 'D:\Trabajo\OvandoCode'
Set-Location $ProjectRoot
$utf8 = New-Object System.Text.UTF8Encoding $false

Write-Host "=== OVANDOCODE :: Fase 6a - Core (messages/session/context) ===" -ForegroundColor Cyan

$coreDir = "$ProjectRoot\src\ovandocode\core"
if (-not (Test-Path $coreDir)) { New-Item -ItemType Directory -Path $coreDir -Force | Out-Null }

# ------------------------------------------------------------
# 6a.1 core/messages.py (helpers de historial)
# ------------------------------------------------------------
$messages = @'
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
'@
[IO.File]::WriteAllText("$coreDir\messages.py", $messages, $utf8)
Write-Host "[OK] core/messages.py" -ForegroundColor Green

# ------------------------------------------------------------
# 6a.2 core/session.py (persistencia JSONL)
# ------------------------------------------------------------
$session = @'
"""Sesiones persistentes en formato JSONL (una linea por mensaje)."""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from ovandocode.core.messages import from_dict, to_dict
from ovandocode.providers.types import Message


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _new_id() -> str:
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"{ts}-{uuid.uuid4().hex[:6]}"


@dataclass
class Session:
    """Sesion de conversacion persistida en disco."""
    id: str = field(default_factory=_new_id)
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)
    model: str = ""
    provider: str = ""
    messages: list[Message] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    path: Path | None = None

    # ---------------- historial ----------------
    def append(self, msg: Message) -> None:
        self.messages.append(msg)
        self.updated_at = _now_iso()
        self._persist_append(msg)

    def extend(self, msgs: list[Message]) -> None:
        for m in msgs:
            self.append(m)

    def replace_history(self, msgs: list[Message]) -> None:
        """Reemplaza el historial completo (usado por compactacion)."""
        self.messages = list(msgs)
        self.updated_at = _now_iso()
        self._persist_full()

    def last_user_text(self) -> str:
        for m in reversed(self.messages):
            if m.role == "user":
                return m.content
        return ""

    def clear(self) -> None:
        self.messages.clear()
        self.updated_at = _now_iso()
        self._persist_full()

    # ---------------- persistencia ----------------
    def _persist_append(self, msg: Message) -> None:
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(to_dict(msg), ensure_ascii=False) + "\n")
        self._write_meta()

    def _persist_full(self) -> None:
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as f:
            for m in self.messages:
                f.write(json.dumps(to_dict(m), ensure_ascii=False) + "\n")
        self._write_meta()

    def _write_meta(self) -> None:
        if self.path is None:
            return
        meta_path = self.path.with_suffix(".meta.json")
        meta = {
            "id": self.id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "provider": self.provider,
            "model": self.model,
            "message_count": len(self.messages),
            "metadata": self.metadata,
        }
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------------- IO publico ----------------

class SessionStore:
    """Gestiona el directorio de sesiones."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def new(self, provider: str = "", model: str = "") -> Session:
        s = Session(provider=provider, model=model)
        s.path = self.root / f"{s.id}.jsonl"
        s._write_meta()
        return s

    def load(self, session_id: str) -> Session:
        path = self.root / f"{session_id}.jsonl"
        if not path.exists():
            raise FileNotFoundError(f"Sesion no encontrada: {session_id}")

        meta_path = path.with_suffix(".meta.json")
        meta: dict = {}
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                meta = {}

        msgs: list[Message] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                msgs.append(from_dict(json.loads(line)))
            except (json.JSONDecodeError, KeyError):
                continue

        s = Session(
            id=meta.get("id", session_id),
            created_at=meta.get("created_at", ""),
            updated_at=meta.get("updated_at", ""),
            provider=meta.get("provider", ""),
            model=meta.get("model", ""),
            messages=msgs,
            metadata=meta.get("metadata", {}),
            path=path,
        )
        return s

    def list_sessions(self) -> list[dict]:
        """Lista metadatos de todas las sesiones (mas reciente primero)."""
        out: list[dict] = []
        for meta_path in self.root.glob("*.meta.json"):
            try:
                data = json.loads(meta_path.read_text(encoding="utf-8"))
                out.append(data)
            except (json.JSONDecodeError, OSError):
                continue
        out.sort(key=lambda d: d.get("updated_at", ""), reverse=True)
        return out

    def delete(self, session_id: str) -> bool:
        p = self.root / f"{session_id}.jsonl"
        m = self.root / f"{session_id}.meta.json"
        deleted = False
        if p.exists():
            p.unlink()
            deleted = True
        if m.exists():
            m.unlink()
        return deleted
'@
[IO.File]::WriteAllText("$coreDir\session.py", $session, $utf8)
Write-Host "[OK] core/session.py" -ForegroundColor Green

# ------------------------------------------------------------
# 6a.3 core/context.py (gestion y auto-compactacion)
# ------------------------------------------------------------
$context = @'
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
'@
[IO.File]::WriteAllText("$coreDir\context.py", $context, $utf8)
Write-Host "[OK] core/context.py" -ForegroundColor Green

# ------------------------------------------------------------
# 6a.4 core/__init__.py
# ------------------------------------------------------------
$coreInit = @'
"""Nucleo del agente: mensajes, sesiones, contexto."""
from ovandocode.core.context import ContextManager, ContextStats
from ovandocode.core.messages import (
    assistant,
    estimate_tokens,
    from_dict,
    system,
    to_dict,
    tool_result,
    user,
)
from ovandocode.core.session import Session, SessionStore

__all__ = [
    "ContextManager",
    "ContextStats",
    "Session",
    "SessionStore",
    "assistant",
    "estimate_tokens",
    "from_dict",
    "system",
    "to_dict",
    "tool_result",
    "user",
]
'@
[IO.File]::WriteAllText("$coreDir\__init__.py", $coreInit, $utf8)
Write-Host "[OK] core/__init__.py" -ForegroundColor Green

# ------------------------------------------------------------
# 6a.5 CLI: comando sessions (list/show/delete)
# ------------------------------------------------------------
$cliPath = "$ProjectRoot\src\ovandocode\cli.py"
$cliContent = [IO.File]::ReadAllText($cliPath)

$sessionsCmd = @'
sessions_app = typer.Typer(help="Gestion de sesiones de conversacion.")
app.add_typer(sessions_app, name="sessions")


@sessions_app.command("list")
def sessions_list() -> None:
    """Lista sesiones guardadas."""
    from ovandocode.config import sessions_dir
    from ovandocode.core import SessionStore

    store = SessionStore(sessions_dir())
    rows = store.list_sessions()
    if not rows:
        typer.echo("(sin sesiones)")
        return
    typer.echo(f"== {len(rows)} sesion(es) ==")
    for r in rows:
        typer.echo(
            f"  {r.get('id','?'):<28} "
            f"msgs={r.get('message_count',0):>4}  "
            f"{r.get('updated_at','')}  "
            f"{r.get('provider','')}/{r.get('model','')}"
        )


@sessions_app.command("show")
def sessions_show(session_id: str = typer.Argument(...)) -> None:
    """Muestra el historial completo de una sesion."""
    from ovandocode.config import sessions_dir
    from ovandocode.core import SessionStore

    store = SessionStore(sessions_dir())
    try:
        s = store.load(session_id)
    except FileNotFoundError as e:
        typer.secho(f"[ERR] {e}", fg="red")
        raise typer.Exit(1)

    typer.echo(f"== sesion {s.id} ==")
    typer.echo(f"  provider: {s.provider}")
    typer.echo(f"  model:    {s.model}")
    typer.echo(f"  created:  {s.created_at}")
    typer.echo(f"  updated:  {s.updated_at}")
    typer.echo(f"  msgs:     {len(s.messages)}")
    typer.echo("")
    for i, m in enumerate(s.messages, 1):
        content = (m.content or "").replace("\n", " ")
        if len(content) > 100:
            content = content[:100] + "..."
        tools = ""
        if m.tool_calls:
            tools = " (tools: " + ", ".join(tc.name for tc in m.tool_calls) + ")"
        typer.echo(f"  [{i:>3}] {m.role:<9} {content}{tools}")


@sessions_app.command("delete")
def sessions_delete(session_id: str = typer.Argument(...)) -> None:
    """Elimina una sesion."""
    from ovandocode.config import sessions_dir
    from ovandocode.core import SessionStore

    store = SessionStore(sessions_dir())
    if store.delete(session_id):
        typer.secho(f"[OK] eliminada: {session_id}", fg="green")
    else:
        typer.secho(f"[ERR] no existe: {session_id}", fg="red")


@sessions_app.command("stats")
def sessions_stats(session_id: str = typer.Argument(...)) -> None:
    """Muestra estadisticas de contexto de una sesion."""
    from ovandocode.config import sessions_dir, get_settings
    from ovandocode.core import ContextManager, SessionStore

    store = SessionStore(sessions_dir())
    try:
        s = store.load(session_id)
    except FileNotFoundError as e:
        typer.secho(f"[ERR] {e}", fg="red")
        raise typer.Exit(1)

    st = get_settings()
    cm = ContextManager(threshold=st.compact_threshold)
    stats = cm.stats(s.messages)
    typer.echo(f"== stats sesion {s.id} ==")
    typer.echo(f"  mensajes:           {stats.messages}")
    typer.echo(f"  tokens (estimados): {stats.estimated_tokens}")
    typer.echo(f"  limite contexto:    {stats.context_limit}")
    typer.echo(f"  uso:                {stats.usage_pct * 100:.2f}%")
    typer.echo(f"  necesita compactar: {stats.needs_compact}")


def main() -> None:
'@
$cliContent = $cliContent -replace '(?ms)^def main\(\) -> None:', $sessionsCmd
[IO.File]::WriteAllText($cliPath, $cliContent, $utf8)
Write-Host "[OK] cli.py actualizado (sessions)" -ForegroundColor Green

# ------------------------------------------------------------
# 6a.6 Verificacion funcional
# ------------------------------------------------------------
Write-Host "`n-> probando core..." -ForegroundColor Yellow
uv run python -c "
from ovandocode.core import SessionStore, ContextManager, user, assistant
from ovandocode.config import sessions_dir
store = SessionStore(sessions_dir())
s = store.new(provider='openrouter', model='test')
s.append(user('hola mundo'))
s.append(assistant('hola'))
s2 = store.load(s.id)
print('OK session:', s2.id, '| msgs:', len(s2.messages))
cm = ContextManager(context_limit=100, threshold=0.5)
print('OK ctx should_compact:', cm.should_compact(s2.messages))
store.delete(s.id)
print('OK cleanup')
"
uv run ovandocode sessions list

# ------------------------------------------------------------
# 6a.7 Commit
# ------------------------------------------------------------
Write-Host "`n-> commit..." -ForegroundColor Yellow
git add .
git commit -m "Fase 6a: messages, sessions (JSONL) y context manager" | Out-Null

Write-Host "`n=== Verificacion Fase 6a ===" -ForegroundColor Cyan
$checks = [ordered]@{
    'core/messages.py'  = (Test-Path 'src\ovandocode\core\messages.py')
    'core/session.py'   = (Test-Path 'src\ovandocode\core\session.py')
    'core/context.py'   = (Test-Path 'src\ovandocode\core\context.py')
    'core/__init__.py'  = (Test-Path 'src\ovandocode\core\__init__.py')
    'commit Fase 6a'    = [bool](git log --oneline 2>$null | Select-String 'Fase 6a')
}
foreach ($k in $checks.Keys) {
    $ok = $checks[$k]
    $mark  = if ($ok) { '[OK]' } else { '[!!]' }
    $color = if ($ok) { 'Green' } else { 'Red' }
    Write-Host "$mark $k" -ForegroundColor $color
}

Write-Host "`nFase 6a completada." -ForegroundColor Cyan