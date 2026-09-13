# ============================================================
#  OVANDOCODE - FASE 6b: el loop del agente
#  Guardar como: D:\Trabajo\OvandoCode\_fase6b.ps1
# ============================================================
$ErrorActionPreference = 'Stop'
$ProjectRoot = 'D:\Trabajo\OvandoCode'
Set-Location $ProjectRoot
$utf8 = New-Object System.Text.UTF8Encoding $false

Write-Host "=== OVANDOCODE :: Fase 6b - Loop del agente ===" -ForegroundColor Cyan

$coreDir = "$ProjectRoot\src\ovandocode\core"

# ------------------------------------------------------------
# 6b.1 core/prompts.py (system prompt por defecto)
# ------------------------------------------------------------
$prompts = @'
"""Prompts del sistema para OVANDOCODE."""
from __future__ import annotations

from pathlib import Path

BASE_SYSTEM_PROMPT = """\
Eres OVANDOCODE, un agente de codificacion autonomo que trabaja en la terminal.

## Entorno
- Sistema operativo: {os_name}
- Directorio del proyecto: {project_root}
- Fecha: {date}

## Capacidades
Tienes acceso a herramientas para leer/escribir/editar archivos, buscar con glob y grep,
y ejecutar comandos en PowerShell, bash y Python. Usalas proactivamente.

## Reglas de trabajo
1. **Explora antes de actuar**: usa `list_dir`, `glob_files` o `grep` para entender la estructura
   antes de modificar archivos.
2. **Lee antes de editar**: nunca edites un archivo sin leerlo primero en la sesion.
3. **Prefiere `edit_file` sobre `write_file`**: cambios quirurgicos son mas seguros.
4. **Ejecuta pruebas**: cuando modifiques codigo, ejecuta los tests con `run_powershell` o `run_python`.
5. **Sé conciso**: no repitas al usuario lo que acabas de hacer con cada tool. Avanza.
6. **Pide confirmacion solo cuando sea necesario**: para acciones destructivas o ambiguas.
7. **No inventes rutas**: verifica que existan antes de referenciarlas.

## Formato de respuesta
- Texto plano (no markdown) para conversacion normal.
- Bloques de codigo con triple backtick cuando muestres codigo.
- Si vas a usar una herramienta, hazlo directamente (no describas "voy a usar X").
- Al terminar una tarea, resume en 1-3 lineas que hiciste.
"""


def build_system_prompt(project_root: Path) -> str:
    import platform
    from datetime import datetime

    return BASE_SYSTEM_PROMPT.format(
        os_name=platform.platform(),
        project_root=str(project_root),
        date=datetime.now().strftime("%Y-%m-%d %H:%M"),
    )
'@
[IO.File]::WriteAllText("$coreDir\prompts.py", $prompts, $utf8)
Write-Host "[OK] core/prompts.py" -ForegroundColor Green

# ------------------------------------------------------------
# 6b.2 core/agent.py (loop principal)
# ------------------------------------------------------------
$agent = @'
"""Loop principal del agente OVANDOCODE."""
from __future__ import annotations

import asyncio
import json
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ovandocode.config import get_settings
from ovandocode.core.context import ContextManager
from ovandocode.core.messages import (
    assistant,
    system,
    tool_result,
    user,
)
from ovandocode.core.prompts import build_system_prompt
from ovandocode.core.session import Session, SessionStore
from ovandocode.permissions import Decision, PermissionPolicy
from ovandocode.providers import create_provider
from ovandocode.providers.base import BaseProvider
from ovandocode.providers.types import (
    ChatRequest,
    Message,
    ProviderError,
)
from ovandocode.tools import ToolRegistry


# ---------------- eventos para callbacks ----------------
@dataclass
class AgentEvents:
    """Callbacks opcionales que la UI puede conectar para mostrar progreso."""
    on_assistant_text: Callable[[str], None] | None = None
    on_tool_call: Callable[[str, dict], None] | None = None
    on_tool_result: Callable[[str, bool, str], None] | None = None
    on_ask_permission: Callable[[str, str], bool] | None = None
    on_info: Callable[[str], None] | None = None
    on_error: Callable[[str], None] | None = None
    on_compact: Callable[[int, int], None] | None = None  # (antes, despues)


# ---------------- excepciones ----------------
class AgentMaxStepsError(Exception):
    """Se alcanzo el maximo numero de pasos del agente."""


# ---------------- configuracion ----------------
@dataclass
class AgentConfig:
    provider: str = "openrouter"
    model: str = "anthropic/claude-sonnet-4"
    max_steps: int = 30
    temperature: float = 0.2
    max_tokens: int = 8192
    auto_compact: bool = True
    system_prompt_override: str | None = None


class Agent:
    """Orquesta proveedor + tools + permisos + sesion + contexto."""

    def __init__(
        self,
        config: AgentConfig,
        session: Session,
        events: AgentEvents | None = None,
        store: SessionStore | None = None,
    ) -> None:
        self.config = config
        self.session = session
        self.events = events or AgentEvents()
        self.store = store

        self.settings = get_settings()
        self.policy = PermissionPolicy(mode=self.settings.permission_mode)
        self.tools = ToolRegistry(policy=self.policy)
        self.context = ContextManager(
            threshold=self.settings.compact_threshold,
        )
        self._provider: BaseProvider | None = None

    # ---------------- ciclo de vida ----------------
    async def __aenter__(self) -> "Agent":
        self._provider = create_provider(self.config.provider)
        return self

    async def __aexit__(self, *exc: object) -> None:
        if self._provider:
            await self._provider.close()

    # ---------------- helpers ----------------
    def _emit(self, event: str, *args: Any) -> None:
        cb = getattr(self.events, event, None)
        if cb:
            try:
                cb(*args)
            except Exception:
                pass  # la UI no debe romper al agente

    def _ensure_system_prompt(self) -> None:
        if self.session.messages and self.session.messages[0].role == "system":
            return
        prompt = self.config.system_prompt_override or build_system_prompt(
            self.tools.project_root
        )
        self.session.messages.insert(0, system(prompt))
        self.session._persist_full()

    def _maybe_compact(self) -> None:
        if not self.config.auto_compact:
            return
        if not self.context.should_compact(self.session.messages):
            return

        before = len(self.session.messages)
        new_msgs, _ = self.context.compact(self.session.messages)
        self.session.replace_history(new_msgs)
        self._emit("on_compact", before, len(new_msgs))

    async def _ask_permission(self, command: str, reason: str) -> bool:
        """Consulta al usuario si puede ejecutar un comando peligroso/no listado."""
        # Si no hay callback, denegar por seguridad
        if self.events.on_ask_permission is None:
            print(f"\n[ASK] {command}\n  razon: {reason}", file=sys.stderr)
            print("[ASK] sin callback; denegado por seguridad.", file=sys.stderr)
            return False
        return bool(self.events.on_ask_permission(command, reason))

    async def _run_tool(self, name: str, arguments: dict) -> tuple[bool, str]:
        """Ejecuta una tool respetando la politica de permisos."""
        # Solo consultamos la politica para shells
        if name in ("run_powershell", "run_bash", "run_python"):
            cmd = arguments.get("command") or arguments.get("code") or ""
            verdict = self.policy.decide(cmd)
            if verdict.decision == Decision.DENY:
                return False, f"[PERMISSION DENIED] {verdict.reason}"
            if verdict.decision == Decision.ASK:
                allowed = await self._ask_permission(cmd, verdict.reason)
                if not allowed:
                    return False, "[PERMISSION DENIED by user]"

        result = await self.tools.run(name, arguments)
        return result.ok, result.content

    # ---------------- paso del agente ----------------
    async def step(self, user_input: str) -> str:
        """Ejecuta un turno completo (user input -> respuesta final).

        Maneja el ciclo:
          user -> LLM -> [tool calls -> tool results -> LLM]* -> respuesta
        """
        self._ensure_system_prompt()
        self.session.append(user(user_input))

        final_text = ""
        for step_num in range(1, self.config.max_steps + 1):
            self._maybe_compact()

            req = ChatRequest(
                messages=self.session.messages,
                model=self.config.model,
                tools=self.tools.schemas(),
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )

            try:
                assert self._provider is not None
                resp = await self._provider.chat(req)
            except ProviderError as e:
                msg = f"[PROVIDER ERROR] {type(e).__name__}: {e}"
                self._emit("on_error", msg)
                return msg

            # Registra respuesta del assistant
            assistant_msg = assistant(resp.content, tool_calls=resp.tool_calls)
            self.session.append(assistant_msg)

            if resp.content:
                self._emit("on_assistant_text", resp.content)
                final_text = resp.content

            # Si no hay tool calls, terminamos
            if not resp.tool_calls:
                return final_text

            # Ejecuta cada tool call
            for tc in resp.tool_calls:
                self._emit("on_tool_call", tc.name, tc.arguments)
                ok, content = await self._run_tool(tc.name, tc.arguments)
                self._emit("on_tool_result", tc.name, ok, content)
                self.session.append(tool_result(tc.id, tc.name, content))

        raise AgentMaxStepsError(
            f"Se alcanzaron {self.config.max_steps} pasos sin respuesta final."
        )

    # ---------------- one-shot ----------------
    async def run_once(self, prompt: str) -> str:
        """Ejecuta una tarea de un solo turno (sin interaccion posterior)."""
        return await self.step(prompt)


# ---------------- helper de alto nivel ----------------
async def run_agent(
    prompt: str,
    config: AgentConfig | None = None,
    events: AgentEvents | None = None,
    resume_session_id: str | None = None,
    store: SessionStore | None = None,
) -> tuple[str, Session]:
    """Crea un agente, ejecuta un prompt y devuelve (respuesta, sesion).

    Si se pasa `resume_session_id`, reanuda una sesion existente.
    Si se pasa `store`, la sesion se persiste automaticamente.
    """
    from ovandocode.config import sessions_dir

    if store is None:
        store = SessionStore(sessions_dir())

    if config is None:
        s = get_settings()
        config = AgentConfig(provider=s.default_provider, model=s.default_model)

    if resume_session_id:
        session = store.load(resume_session_id)
        # actualiza provider/model si difieren
        session.provider = config.provider
        session.model = config.model
    else:
        session = store.new(provider=config.provider, model=config.model)

    async with Agent(config=config, session=session, events=events, store=store) as agent:
        result = await agent.run_once(prompt)

    return result, session
'@
[IO.File]::WriteAllText("$coreDir\agent.py", $agent, $utf8)
Write-Host "[OK] core/agent.py" -ForegroundColor Green

# ------------------------------------------------------------
# 6b.3 Actualizar core/__init__.py
# ------------------------------------------------------------
$coreInit = @'
"""Nucleo del agente: mensajes, sesiones, contexto, agente."""
from ovandocode.core.agent import (
    Agent,
    AgentConfig,
    AgentEvents,
    AgentMaxStepsError,
    run_agent,
)
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
from ovandocode.core.prompts import build_system_prompt
from ovandocode.core.session import Session, SessionStore

__all__ = [
    "Agent",
    "AgentConfig",
    "AgentEvents",
    "AgentMaxStepsError",
    "ContextManager",
    "ContextStats",
    "Session",
    "SessionStore",
    "assistant",
    "build_system_prompt",
    "estimate_tokens",
    "from_dict",
    "run_agent",
    "system",
    "to_dict",
    "tool_result",
    "user",
]
'@
[IO.File]::WriteAllText("$coreDir\__init__.py", $coreInit, $utf8)
Write-Host "[OK] core/__init__.py actualizado" -ForegroundColor Green

# ------------------------------------------------------------
# 6b.4 CLI: comando `ask` (one-shot)
# ------------------------------------------------------------
$cliPath = "$ProjectRoot\src\ovandocode\cli.py"
$cliContent = [IO.File]::ReadAllText($cliPath)

$askCmd = @'
ask_app = typer.Typer(help="Ejecutar el agente en modo one-shot.")


@ask_app.command("run")
def ask_run(
    prompt: str = typer.Argument(..., help="Prompt o tarea para el agente."),
    provider: str = typer.Option(None, "--provider", "-p"),
    model: str = typer.Option(None, "--model", "-m"),
    max_steps: int = typer.Option(30, "--max-steps"),
    resume: str = typer.Option(None, "--resume", "-r", help="ID de sesion a reanudar."),
    yolo: bool = typer.Option(False, "--yolo", help="Auto-aprobar todas las tools (peligroso)."),
) -> None:
    """Ejecuta el agente una vez con el prompt dado."""
    import asyncio

    from ovandocode.core.agent import AgentConfig, AgentEvents, run_agent
    from ovandocode.config import get_settings

    s = get_settings()
    cfg = AgentConfig(
        provider=provider or s.default_provider,
        model=model or s.default_model,
        max_steps=max_steps,
        temperature=s.temperature,
        max_tokens=s.max_tokens,
        auto_compact=s.auto_compact,
    )
    if yolo:
        s.permission_mode = "yolo"  # type: ignore[assignment]

    def on_text(t: str) -> None:
        typer.echo(t)

    def on_tool_call(name: str, args: dict) -> None:
        preview = str(args)[:120]
        typer.secho(f"\n>> {name} {preview}", fg="cyan")

    def on_tool_result(name: str, ok: bool, content: str) -> None:
        color = "green" if ok else "red"
        body = content if len(content) < 500 else content[:500] + "..."
        typer.secho(f"<< {name} [{'ok' if ok else 'fail'}]", fg=color)
        typer.echo(body)

    def on_ask(cmd: str, reason: str) -> bool:
        typer.secho(f"\n[ASK] {cmd}", fg="yellow")
        typer.secho(f"      razon: {reason}", fg="yellow")
        return typer.confirm("Permitir?", default=False)

    def on_error(msg: str) -> None:
        typer.secho(msg, fg="red")

    events = AgentEvents(
        on_assistant_text=on_text,
        on_tool_call=on_tool_call,
        on_tool_result=on_tool_result,
        on_ask_permission=on_ask,
        on_error=on_error,
    )

    async def _go() -> None:
        try:
            reply, session = await run_agent(
                prompt=prompt,
                config=cfg,
                events=events,
                resume_session_id=resume,
            )
        except Exception as e:
            typer.secho(f"[FATAL] {type(e).__name__}: {e}", fg="red")
            raise typer.Exit(1)
        typer.echo("")
        typer.secho(f"[sesion: {session.id}]", fg="bright_black")

    asyncio.run(_go())


app.add_typer(ask_app, name="ask")


def main() -> None:
'@
$cliContent = $cliContent -replace '(?ms)^def main\(\) -> None:', $askCmd
[IO.File]::WriteAllText($cliPath, $cliContent, $utf8)
Write-Host "[OK] cli.py actualizado (ask run)" -ForegroundColor Green

# ------------------------------------------------------------
# 6b.5 Verificacion
# ------------------------------------------------------------
Write-Host "`n-> probando imports..." -ForegroundColor Yellow
uv run python -c "from ovandocode.core import Agent, AgentConfig, run_agent; print('OK agent')"
uv run ovandocode ask --help

# ------------------------------------------------------------
# 6b.6 Commit
# ------------------------------------------------------------
Write-Host "`n-> commit..." -ForegroundColor Yellow
git add .
git commit -m "Fase 6b: loop del agente + CLI ask run" | Out-Null

Write-Host "`n=== Verificacion Fase 6b ===" -ForegroundColor Cyan
$checks = [ordered]@{
    'core/prompts.py' = (Test-Path 'src\ovandocode\core\prompts.py')
    'core/agent.py'   = (Test-Path 'src\ovandocode\core\agent.py')
    'commit Fase 6b'  = [bool](git log --oneline 2>$null | Select-String 'Fase 6b')
}
foreach ($k in $checks.Keys) {
    $ok = $checks[$k]
    $mark  = if ($ok) { '[OK]' } else { '[!!]' }
    $color = if ($ok) { 'Green' } else { 'Red' }
    Write-Host "$mark $k" -ForegroundColor $color
}

Write-Host "`nFase 6b completada." -ForegroundColor Cyan