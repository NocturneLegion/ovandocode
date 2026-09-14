"""TUI principal de OVANDOCODE (Textual)."""
from __future__ import annotations

import pathlib

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
from ovandocode.tui.widgets import PermissionScreen, PickerScreen

HELP_TEXT = """[bold]Comandos disponibles[/]
  /help              Muestra esta ayuda
  /quit              Salir
  /clear             Nueva sesion (limpia el chat)
  /session           Info de la sesion actual
  /model [nombre]    Abre selector de modelos (o directo si pasas nombre)
  /provider [nombre] Abre selector de proveedores (o directo)
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
        self._project_root: str = str(pathlib.Path.cwd().resolve())

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
        log.write(f"Proyecto:  [bold yellow]{self._project_root}[/]")
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
            self._handle_slash(text)  # @work -> corre en worker
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
    @work(exclusive=False)
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
            if arg:
                # Modo directo: /model gpt-4o
                await self._change_model(arg)
            else:
                # Modo interactivo: abrir picker
                await self._pick_model()
        elif cmd == "provider":
            if arg:
                await self._change_provider(arg)
            else:
                await self._pick_provider()
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

    # ---------------- helpers interactivos ----------------

    async def _pick_model(self) -> None:
        """Abre el selector de modelos del proveedor actual."""
        from ovandocode.providers import ModelsCache, create_provider

        provider = self.agent_config.provider
        current = self.agent_config.model

        self._log().write(f"[dim]Obteniendo modelos de {provider}...[/]")

        cache = ModelsCache()
        models: list[str] | None = cache.get(provider)

        if models is None:
            try:
                p = create_provider(provider)
                async with p:
                    models = await p.list_models()
                if models:
                    cache.set(provider, models)
            except Exception as e:
                self._log().write(f"[red]No se pudieron obtener modelos: {e}[/]")
                self._log().write("[yellow]Puedes escribir el modelo directo con: /model <nombre>[/]")
                return

        if not models:
            self._log().write(f"[yellow](sin modelos para {provider})[/]")
            return

        items = [(m, m) for m in models]
        result = await self.push_screen_wait(
            PickerScreen(
                title=f"Modelos de {provider}",
                subtitle=f"{len(models)} disponibles - escribe para filtrar",
                items=items,
                current=current,
            )
        )
        if result:
            await self._change_model(result)

    async def _change_model(self, model: str) -> None:
        """Aplica un cambio de modelo + persiste si se pide."""
        self.agent_config.model = model
        if self.session:
            self.session.model = model

        # Recargar el agente con el nuevo modelo
        await self._reload_agent()

        self._log().write(f"[green]Modelo cambiado a:[/] {model}")
        self._update_status()
        await self._maybe_persist("default_model", model)

    async def _pick_provider(self) -> None:
        """Abre el selector de proveedores."""
        from ovandocode.providers import list_providers

        providers = list_providers()
        items = [(p, p) for p in providers]
        result = await self.push_screen_wait(
            PickerScreen(
                title="Proveedores disponibles",
                subtitle="Elige uno para cambiar el LLM",
                items=items,
                current=self.agent_config.provider,
                searchable=False,
            )
        )
        if result:
            await self._change_provider(result)

    async def _change_provider(self, provider: str) -> None:
        """Aplica un cambio de proveedor + persiste si se pide."""
        from ovandocode.config import get_credentials
        from ovandocode.providers import REGISTRY

        if provider not in REGISTRY:
            self._log().write(f"[red]Proveedor desconocido: {provider}[/]")
            return

        cls = REGISTRY[provider]
        if cls.requires_api_key:
            key = get_credentials().get(provider)
            if not key:
                self._log().write(
                    f"[yellow]El proveedor {provider} requiere API key.[/]"
                )
                self._log().write(
                    f"[dim]Ejecuta fuera de la TUI: ovandocode config set-key {provider}[/]"
                )
                return

        self.agent_config.provider = provider
        if self.session:
            self.session.provider = provider

        # Reintentar con el modelo por defecto del proveedor
        await self._reload_agent()

        self._log().write(f"[green]Proveedor cambiado a:[/] {provider}")
        self._log().write(f"[dim]Modelo actual: {self.agent_config.model}[/]")
        self._update_status()
        await self._maybe_persist("default_provider", provider)

    async def _reload_agent(self) -> None:
        """Reinstancia el agente con la config actual (provider/model/tools)."""
        if self.agent is not None:
            try:
                await self.agent.__aexit__(None, None, None)
            except Exception:
                pass

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

    async def _maybe_persist(self, key: str, value) -> None:
        """Pregunta si guardar el cambio en config.toml global."""
        from ovandocode.config import GlobalConfig, GlobalConfigError

        try:
            persist = await self.push_screen_wait(
                PermissionScreen(
                    command=f"ovandocode config set {key} {value}",
                    reason="Guardar este cambio para futuros proyectos (config.toml global)",
                )
            )
        except Exception:
            persist = False

        if not persist:
            return

        gc = GlobalConfig()
        try:
            gc.set(key, value)
            self._log().write(f"[green]Guardado en config.toml:[/] {key} = {value!r}")
        except GlobalConfigError as e:
            self._log().write(f"[red]No se pudo guardar: {e}[/]")

    def _update_status(self) -> None:
        if self.session is None:
            return
        # Ruta del proyecto (truncada si es muy larga para el status bar)
        root = self._project_root
        if len(root) > 55:
            root = "..." + root[-52:]
        s = (
            f" {root}"
            f"  |  {self.agent_config.provider}/{self.agent_config.model}"
            f"  |  msgs: {len(self.session.messages)}"
        )
        self.query_one("#status", Static).update(s)

        # Actualizar titulo de la ventana del terminal
        try:
            self.sub_title = f"v{__version__} - {pathlib.Path(self._project_root).name}"
        except Exception:
            pass


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
