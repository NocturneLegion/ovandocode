"""TUI principal de OVANDOCODE (Textual)."""
from __future__ import annotations

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import Footer, Header, Input, RichLog, Static

from ovandocode import __version__
from ovandocode.config import get_settings, sessions_dir
from ovandocode.core import (
    Agent,
    AgentConfig,
    AgentEvents,
    SessionStore,
)
from ovandocode.providers import REGISTRY, list_providers
from ovandocode.skills import SkillLoader
from ovandocode.tui.widgets.permission import PermissionScreen

HELP_TEXT = """[bold]Comandos disponibles[/]
  /help              Muestra esta ayuda
  /quit              Salir
  /clear             Nueva sesion (limpia el chat)
  /session           Info de la sesion actual
  /model [nombre]    Ver o cambiar el modelo
  /provider [nombre] Ver o cambiar el proveedor
  /skills            Lista skills disponibles
  /mcp               Estado de los servidores MCP
  /tools             Lista herramientas activas
"""


class OvandoCodeApp(App):
    """Aplicacion principal."""

    CSS_PATH = "theme.tcss"
    TITLE = "OVANDOCODE"
    SUB_TITLE = f"v{__version__}"
    BINDINGS = [
        Binding("ctrl+c", "quit", "Salir", priority=True),
        Binding("ctrl+l", "clear_chat", "Limpiar"),
        Binding("ctrl+n", "new_session", "Nueva sesion"),
    ]

    def __init__(self, agent_config: AgentConfig) -> None:
        super().__init__()
        self.agent_config = agent_config
        self.agent: Agent | None = None
        self.session = None
        self.store = SessionStore(sessions_dir())

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical():
            yield RichLog(id="chat", highlight=True, markup=True, wrap=True)
            yield Input(placeholder="Escribe tu mensaje... (o /help)", id="input")
            yield Static("", id="status")
        yield Footer()

    # ---------------- ciclo de vida ----------------
    async def on_mount(self) -> None:
        log = self.query_one("#chat", RichLog)
        log.write(f"[bold cyan]OVANDOCODE[/] v{__version__}")
        log.write(f"Proveedor: [yellow]{self.agent_config.provider}[/]")
        log.write(f"Modelo:    [yellow]{self.agent_config.model}[/]")
        log.write("")
        log.write("[dim]Escribe /help para ver comandos.[/]")
        log.write("")

        self.session = self.store.new(
            provider=self.agent_config.provider,
            model=self.agent_config.model,
        )

        events = AgentEvents(
            on_assistant_text=self._ev_assistant_text,
            on_tool_call=self._ev_tool_call,
            on_tool_result=self._ev_tool_result,
            on_error=self._ev_error,
            on_ask_permission=self._ev_ask_permission,
            on_compact=self._ev_compact,
        )
        self.agent = Agent(
            config=self.agent_config,
            session=self.session,
            events=events,
            store=self.store,
        )
        await self.agent.__aenter__()
        self._update_status()
        self.query_one("#input", Input).focus()

    async def on_unmount(self) -> None:
        if self.agent is not None:
            await self.agent.__aexit__(None, None, None)

    # ---------------- eventos del agente (callbacks) ----------------
    def _log(self) -> RichLog:
        return self.query_one("#chat", RichLog)

    def _ev_assistant_text(self, text: str) -> None:
        log = self._log()
        log.write(f"[bold cyan]Agent:[/] {text}")
        log.write("")

    def _ev_tool_call(self, name: str, args: dict) -> None:
        preview = str(args)
        if len(preview) > 120:
            preview = preview[:120] + "..."
        self._log().write(f"[dim]  >> {name} {preview}[/]")

    def _ev_tool_result(self, name: str, ok: bool, content: str) -> None:
        color = "green" if ok else "red"
        preview = content.replace("\n", " ")
        if len(preview) > 240:
            preview = preview[:240] + "..."
        self._log().write(f"[dim {color}]  << {name}: {preview}[/]")

    def _ev_error(self, msg: str) -> None:
        self._log().write(f"[bold red]{msg}[/]")

    def _ev_compact(self, before: int, after: int) -> None:
        self._log().write(
            f"[dim yellow]  [compact] {before} -> {after} mensajes[/]"
        )

    async def _ev_ask_permission(self, command: str, reason: str) -> bool:
        return bool(await self.push_screen_wait(PermissionScreen(command, reason)))

    # ---------------- input ----------------
    async def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        self.query_one("#input", Input).value = ""
        if not text:
            return

        if text.startswith("/"):
            await self._handle_slash(text)
            return

        self._log().write(f"[bold green]Tu:[/] {text}")
        self._log().write("")
        self._run_agent(text)

    @work(exclusive=True)
    async def _run_agent(self, text: str) -> None:
        self.query_one("#status", Static).update("[yellow]Pensando...[/]")
        try:
            assert self.agent is not None
            await self.agent.step(text)
        except Exception as e:
            self._log().write(f"[bold red]Error fatal: {type(e).__name__}: {e}[/]")
        finally:
            self._update_status()

    # ---------------- slash commands ----------------
    async def _handle_slash(self, text: str) -> None:
        parts = text[1:].split(maxsplit=1)
        cmd = parts[0].lower() if parts else ""
        arg = parts[1] if len(parts) > 1 else ""

        if cmd in ("q", "quit", "exit"):
            self.exit()
        elif cmd == "help":
            self._log().write(HELP_TEXT)
        elif cmd == "clear":
            self.action_new_session()
        elif cmd == "session":
            if self.session:
                self._log().write(
                    f"[bold]Sesion actual[/]\n"
                    f"  id:       {self.session.id}\n"
                    f"  provider: {self.session.provider}\n"
                    f"  model:    {self.session.model}\n"
                    f"  mensajes: {len(self.session.messages)}"
                )
        elif cmd == "model":
            if not arg:
                self._log().write(f"Modelo actual: [yellow]{self.agent_config.model}[/]")
            else:
                self.agent_config.model = arg
                if self.session:
                    self.session.model = arg
                self._log().write(f"[green]Modelo cambiado a:[/] {arg}")
                self._update_status()
        elif cmd == "provider":
            if not arg:
                self._log().write(
                    f"Proveedor actual: [yellow]{self.agent_config.provider}[/]\n"
                    f"Disponibles: {', '.join(list_providers())}"
                )
            else:
                if arg not in REGISTRY:
                    self._log().write(f"[red]Proveedor desconocido: {arg}[/]")
                else:
                    self.agent_config.provider = arg
                    if self.session:
                        self.session.provider = arg
                    self._log().write(f"[green]Proveedor cambiado a:[/] {arg}")
                    self._log().write("[dim](reinicia el agente para aplicar)[/]")
                    self._update_status()
        elif cmd == "skills":
            loader = SkillLoader(project_root=self.agent.tools.project_root if self.agent else None)
            skills = loader.all()
            if not skills:
                self._log().write("(sin skills)")
            else:
                self._log().write(f"[bold]{len(skills)} skill(s):[/]")
                for s in skills:
                    origen = "builtin" if s.builtin else "proyecto"
                    self._log().write(f"  [{origen}] {s.name} - {s.description[:60]}")
        elif cmd == "mcp":
            if self.agent and self.agent.tools.mcp_manager:
                mgr = self.agent.tools.mcp_manager
                self._log().write(f"[bold]MCP activos:[/] {mgr.running_count}")
                for srv, client in mgr.clients.items():
                    self._log().write(f"  {srv}: {len(client.tools)} tools")
                for srv, err in mgr.errors.items():
                    self._log().write(f"  [red]{srv}: {err}[/]")
            else:
                self._log().write("(sin servidores MCP activos)")
        elif cmd == "tools":
            if self.agent:
                names = self.agent.tools.names()
                self._log().write(f"[bold]{len(names)} herramientas activas:[/]")
                for n in names:
                    self._log().write(f"  * {n}")
        else:
            self._log().write(f"[red]Comando desconocido:[/] /{cmd}. Usa /help.")

    # ---------------- acciones ----------------
    def action_clear_chat(self) -> None:
        self.query_one("#chat", RichLog).clear()

    def action_new_session(self) -> None:
        log = self._log()
        log.write("")
        log.write("[dim]--- nueva sesion ---[/]")
        log.write("")
        # Cerrar agente anterior y crear uno nuevo
        async def _reset():
            if self.agent is not None:
                await self.agent.__aexit__(None, None, None)
            self.session = self.store.new(
                provider=self.agent_config.provider,
                model=self.agent_config.model,
            )
            events = AgentEvents(
                on_assistant_text=self._ev_assistant_text,
                on_tool_call=self._ev_tool_call,
                on_tool_result=self._ev_tool_result,
                on_error=self._ev_error,
                on_ask_permission=self._ev_ask_permission,
                on_compact=self._ev_compact,
            )
            self.agent = Agent(
                config=self.agent_config,
                session=self.session,
                events=events,
                store=self.store,
            )
            await self.agent.__aenter__()
        self.run_worker(_reset(), exclusive=True)
        self._update_status()

    def _update_status(self) -> None:
        if self.session is None:
            return
        s = (
            f" {self.agent_config.provider}/{self.agent_config.model}"
            f" | sesion: {self.session.id[:20]}"
            f" | msgs: {len(self.session.messages)}"
        )
        self.query_one("#status", Static).update(s)


def run_tui(agent_config: AgentConfig | None = None) -> None:
    """Arranca la TUI con la configuracion dada (o la de settings)."""
    if agent_config is None:
        s = get_settings()
        agent_config = AgentConfig(
            provider=s.default_provider,
            model=s.default_model,
            temperature=s.temperature,
            max_tokens=s.max_tokens,
            auto_compact=s.auto_compact,
        )
    app = OvandoCodeApp(agent_config)
    app.run()
