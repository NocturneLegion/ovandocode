"""OVANDOCODE - CLI principal."""
from __future__ import annotations

import asyncio
import json
import os
import sys

import typer
from rich.console import Console

from ovandocode import __version__

app = typer.Typer(
    name="ovandocode",
    help="OVANDOCODE - Agente de codificacion autonomo.",
    no_args_is_help=False,
    add_completion=False,
    rich_markup_mode="rich",
)

console = Console()


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"OVANDOCODE v{__version__}")
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def _root(
    ctx: typer.Context,
    version: bool = typer.Option(
        False, "--version", "-V",
        callback=_version_callback, is_eager=True,
        help="Muestra la version y sale.",
    ),
    debug: bool = typer.Option(
        False, "--debug",
        help="Activa logging DEBUG y muestra tracebacks completos.",
    ),
) -> None:
    """Si no se pasa comando, abre la TUI."""
    if debug:
        os.environ["OVANDOCODE_LOG_LEVEL"] = "DEBUG"
        os.environ["OVANDOCODE_DEBUG"] = "1"

    if ctx.invoked_subcommand is None:
        from ovandocode.tui import run_tui
        run_tui()


# ============================================================
# COMANDOS DE PRIMER NIVEL
# ============================================================

@app.command()
def version() -> None:
    """Muestra la version."""
    console.print(f"OVANDOCODE v{__version__}")


@app.command()
def chat() -> None:
    """Abre la TUI interactiva."""
    from ovandocode.tui import run_tui
    run_tui()


@app.command()
def run(
    prompt: str = typer.Argument(..., help="Tarea para el agente."),
    provider: str | None = typer.Option(None, "--provider", "-p"),
    model: str | None = typer.Option(None, "--model", "-m"),
    max_steps: int = typer.Option(30, "--max-steps"),
    resume: str | None = typer.Option(None, "--resume", "-r"),
    yolo: bool = typer.Option(False, "--yolo", help="Auto-aprobar shells."),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Solo la respuesta final."),
) -> None:
    """Ejecuta el agente una vez (one-shot)."""
    _run_one_shot(prompt, provider, model, max_steps, resume, yolo, quiet)


@app.command()
def headless(
    prompt: str = typer.Argument(..., help="Tarea (modo headless)."),
    provider: str | None = typer.Option(None, "--provider", "-p"),
    model: str | None = typer.Option(None, "--model", "-m"),
    max_steps: int = typer.Option(30, "--max-steps"),
    resume: str | None = typer.Option(None, "--resume", "-r"),
    yolo: bool = typer.Option(True, "--yolo/--no-yolo"),
    json_out: bool = typer.Option(False, "--json", help="Salida JSON."),
) -> None:
    """Ejecuta el agente y devuelve solo el resultado (para pipelines)."""
    result = _run_one_shot(
        prompt, provider, model, max_steps, resume, yolo, quiet=True,
        return_result=True,
    )
    if json_out and result:
        console.print_json(json.dumps({
            "response": result[0],
            "session_id": result[1].id,
            "provider": result[1].provider,
            "model": result[1].model,
            "messages": len(result[1].messages),
        }))
    elif result:
        sys.stdout.write(result[0] + "\n")


def _run_one_shot(
    prompt: str,
    provider: str | None,
    model: str | None,
    max_steps: int,
    resume: str | None,
    yolo: bool,
    quiet: bool,
    return_result: bool = False,
):
    """Logica compartida entre `run` y `headless`."""
    from ovandocode.config import get_settings
    from ovandocode.core import AgentConfig, AgentEvents, run_agent

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
        s.permission_mode = "yolo"  # type: ignore

    def on_text(t: str) -> None:
        if not quiet:
            console.print(t)

    def on_tool_call(name: str, args: dict) -> None:
        if not quiet:
            preview = str(args)[:120]
            console.print(f"[cyan]>> {name}[/] [dim]{preview}[/]")

    def on_tool_result(name: str, ok: bool, content: str) -> None:
        if not quiet:
            color = "green" if ok else "red"
            body = content if len(content) < 500 else content[:500] + "..."
            console.print(f"[{color}]<< {name} [{'ok' if ok else 'fail'}][/]")
            console.print(f"[dim]{body}[/]")

    def on_ask(cmd: str, reason: str) -> bool:
        if quiet:
            return True  # headless: auto-aprobar (por eso el default yolo=True)
        console.print(f"\n[yellow][ASK][/] {cmd}")
        console.print(f"[yellow]      razon: {reason}[/]")
        return typer.confirm("Permitir?", default=False)

    def on_error(msg: str) -> None:
        console.print(f"[bold red]{msg}[/]")

    events = AgentEvents(
        on_assistant_text=on_text,
        on_tool_call=on_tool_call,
        on_tool_result=on_tool_result,
        on_ask_permission=on_ask,
        on_error=on_error,
    )

    async def _go():
        return await run_agent(
            prompt=prompt,
            config=cfg,
            events=events,
            resume_session_id=resume,
        )

    try:
        result = asyncio.run(_go())
    except Exception as e:
        console.print(f"[bold red][FATAL] {type(e).__name__}: {e}[/]")
        if os.environ.get("OVANDOCODE_DEBUG"):
            import traceback
            traceback.print_exc()
        raise typer.Exit(1)

    reply, session = result
    if not quiet:
        console.print("")
        console.print(f"[bright_black][sesion: {session.id}][/]")

    if return_result:
        return reply, session
    return None


# ============================================================
# SUB-COMANDO: config
# ============================================================
config_app = typer.Typer(help="Configuracion y credenciales.")
app.add_typer(config_app, name="config")


@config_app.command("show")
def config_show() -> None:
    """Muestra la configuracion efectiva activa."""
    from ovandocode.config import config_dir, get_settings, logs_dir, project_root
    s = get_settings()
    console.print("[bold]== OVANDOCODE config (efectiva) ==[/]")
    console.print(f"  project_root     : {project_root()}")
    console.print(f"  config_dir       : {config_dir()}")
    console.print(f"  logs_dir         : {logs_dir()}")
    console.print(f"  default_provider : {s.default_provider}")
    console.print(f"  default_model    : {s.default_model}")
    console.print(f"  temperature      : {s.temperature}")
    console.print(f"  max_tokens       : {s.max_tokens}")
    console.print(f"  request_timeout  : {s.request_timeout}")
    console.print(f"  permission_mode  : {s.permission_mode}")
    console.print(f"  auto_compact     : {s.auto_compact}")
    console.print(f"  compact_threshold: {s.compact_threshold}")
    console.print(f"  theme            : {s.theme}")
    console.print(f"  log_level        : {s.log_level}")


@config_app.command("get")
def config_get(key: str = typer.Argument(..., help="Nombre del campo.")) -> None:
    """Lee un valor persistido en config.toml (o vacio si no esta)."""
    from ovandocode.config import GlobalConfig, GlobalConfigError
    gc = GlobalConfig()
    try:
        value = gc.get(key)
    except GlobalConfigError as e:
        console.print(f"[red][ERR] {e}[/]")
        raise typer.Exit(1)
    if value is None:
        console.print(f"[dim](no seteado: {key})[/]")
    else:
        console.print(f"{key} = {value!r}")


@config_app.command("set")
def config_set(
    key: str = typer.Argument(..., help="Campo a persistir."),
    value: str = typer.Argument(..., help="Valor (string; se coercionara)."),
) -> None:
    """Persiste un valor en config.toml (afecta a futuros proyectos)."""
    from ovandocode.config import GlobalConfig, GlobalConfigError
    gc = GlobalConfig()
    try:
        gc.set(key, value)
    except GlobalConfigError as e:
        console.print(f"[red][ERR] {e}[/]")
        raise typer.Exit(1)
    console.print(f"[green][OK] {key} = {gc.get(key)!r}[/]")
    console.print(f"[dim]guardado en: {gc.path_str()}[/]")


@config_app.command("unset")
def config_unset(key: str = typer.Argument(...)) -> None:
    """Borra un valor persistido de config.toml."""
    from ovandocode.config import GlobalConfig
    gc = GlobalConfig()
    if gc.unset(key):
        console.print(f"[green][OK] {key} eliminado[/]")
    else:
        console.print(f"[yellow]({key} no estaba seteado)[/]")


@config_app.command("all")
def config_all() -> None:
    """Muestra todos los valores persistidos en config.toml."""
    from ovandocode.config import GlobalConfig
    gc = GlobalConfig()
    data = gc.all()
    if not data:
        console.print(f"[dim](config.toml vacio: {gc.path_str()})[/]")
        return
    console.print(f"[bold]== config.toml ({gc.path_str()}) ==[/]")
    for k, v in sorted(data.items()):
        console.print(f"  {k} = {v!r}")


@config_app.command("reset")
def config_reset(
    yes: bool = typer.Option(False, "--yes", "-y", help="No preguntar."),
) -> None:
    """Borra TODA la configuracion persistida en config.toml."""
    from ovandocode.config import GlobalConfig
    gc = GlobalConfig()
    if not gc.exists():
        console.print("[dim](no hay config.toml)[/]")
        return
    if not yes:
        if not typer.confirm(f"Borrar {gc.path_str()}?"):
            raise typer.Exit(0)
    gc.reset()
    console.print("[green][OK] config.toml eliminado[/]")


@config_app.command("file")
def config_file_path() -> None:
    """Muestra la ruta del archivo config.toml."""
    from ovandocode.config import GlobalConfig
    gc = GlobalConfig()
    exists = "[green]existe[/]" if gc.exists() else "[dim]no existe[/]"
    console.print(f"{gc.path_str()}  ({exists})")



@config_app.command("providers")
def config_providers() -> None:
    """Lista el estado de cada proveedor."""
    from ovandocode.config import get_credentials
    cm = get_credentials()
    console.print("[bold]== Proveedores ==[/]")
    for st in cm.list_status():
        mark = "[green]OK[/]" if st.available else "[red]--[/]"
        console.print(f"  [{mark}] {st.provider:<12} source={st.source}")


@config_app.command("set-key")
def config_set_key(
    provider: str = typer.Argument(...),
    value: str | None = typer.Option(None, "--value", "-v"),
    from_env: str | None = typer.Option(None, "--from-env"),
    from_stdin: bool = typer.Option(False, "--stdin"),
    backend: str = typer.Option("keyring", "--backend", "-b"),
    force: bool = typer.Option(False, "--force", "-f"),
) -> None:
    """Guarda la API key de un proveedor."""
    from ovandocode.config import get_credentials
    key = None
    if value:
        key = value.strip()
    elif from_env:
        key = (os.environ.get(from_env) or "").strip() or None
    elif from_stdin:
        key = sys.stdin.read().strip() or None
    else:
        try:
            key = typer.prompt("API key", hide_input=True).strip() or None
        except (KeyboardInterrupt, typer.Abort):
            raise typer.Exit(1)
    if not key:
        console.print("[red][ERR] key vacia[/]")
        raise typer.Exit(1)
    if not force:
        preview = f"{key[:8]}...{key[-4:]}" if len(key) > 14 else "***"
        console.print(f"Provider: {provider}\nBackend : {backend}\nValor   : {preview}")
        if not typer.confirm("Guardar?", default=True):
            raise typer.Exit(1)
    get_credentials().set(provider, key, backend=backend)  # type: ignore
    console.print(f"[green][OK] key guardada en {backend}[/]")


@config_app.command("del-key")
def config_del_key(provider: str = typer.Argument(...)) -> None:
    """Elimina la API key (keyring)."""
    from ovandocode.config import get_credentials
    get_credentials().delete(provider, backend="keyring")
    console.print(f"[green][OK] eliminada de keyring: {provider}[/]")


# ============================================================
# SUB-COMANDO: providers
# ============================================================
providers_app = typer.Typer(help="Proveedores LLM.")
app.add_typer(providers_app, name="providers")


@providers_app.command("list")
def providers_list() -> None:
    """Lista proveedores registrados."""
    from ovandocode.config import get_credentials
    from ovandocode.providers import REGISTRY, list_providers
    cm = get_credentials()
    console.print("[bold]== Proveedores LLM ==[/]")
    for name in list_providers():
        cls = REGISTRY[name]
        status = cm.source_of(name) if cls.requires_api_key else "local"
        ok = "OK" if (status != "none" or not cls.requires_api_key) else "--"
        key_req = "requiere key" if cls.requires_api_key else "sin key"
        color = "green" if ok == "OK" else "red"
        console.print(f"  [{color}]{ok}[/] {name:<12} {key_req:<13} source={status}")


@providers_app.command("ping")
def providers_ping(
    provider: str = typer.Argument(...),
    model: str | None = typer.Option(None, "--model", "-m"),
) -> None:
    """Envia un prompt trivial para verificar conectividad."""
    from ovandocode.config import get_settings
    from ovandocode.providers import Message, create_provider
    from ovandocode.providers.types import ChatRequest

    async def _go() -> None:
        p = create_provider(provider)
        chosen = model or get_settings().default_model
        console.print(f"-> {provider} :: {chosen}")
        async with p:
            resp = await p.chat(ChatRequest(
                messages=[Message(role="user", content="Responde solo: PONG")],
                model=chosen, max_tokens=16,
            ))
        console.print(f"[green]respuesta: {resp.content.strip()!r}[/]")
        console.print(f"tokens: in={resp.usage.input_tokens} out={resp.usage.output_tokens}")

    try:
        asyncio.run(_go())
    except Exception as e:
        console.print(f"[red][ERR] {type(e).__name__}: {e}[/]")
        raise typer.Exit(1)


@providers_app.command("models")
def providers_models(
    provider: str = typer.Argument(..., help="Nombre del proveedor."),
    refresh: bool = typer.Option(False, "--refresh", "-r", help="Ignora el cache y refetchea."),
    limit: int = typer.Option(0, "--limit", "-n", help="0 = sin limite."),
    filter_str: str | None = typer.Option(None, "--filter", "-f", help="Filtro substring."),
) -> None:
    """Lista los modelos disponibles del proveedor (cache 24h)."""
    from ovandocode.providers import REGISTRY, ModelsCache, create_provider

    if provider not in REGISTRY:
        console.print(f"[red][ERR] proveedor desconocido: {provider}[/]")
        raise typer.Exit(1)

    cache = ModelsCache()
    models: list[str] | None = None

    if not refresh:
        models = cache.get(provider)

    if models is None:
        console.print(f"[dim]Fetching modelos de {provider}...[/]")

        async def _fetch() -> list[str]:
            p = create_provider(provider)
            try:
                async with p:
                    return await p.list_models()
            except Exception as e:
                console.print(f"[red][ERR] {type(e).__name__}: {e}[/]")
                return []

        models = asyncio.run(_fetch())
        if models:
            cache.set(provider, models)

    if not models:
        console.print(f"[yellow](sin modelos para {provider})[/]")
        return

    if filter_str:
        q = filter_str.lower()
        models = [m for m in models if q in m.lower()]

    if limit > 0:
        models = models[:limit]

    console.print(f"[bold]{len(models)} modelo(s) de {provider}:[/]")
    for m in models:
        console.print(f"  {m}")


@providers_app.command("models-cache")
def providers_models_cache(
    provider: str | None = typer.Argument(None, help="Proveedor a limpiar (o todos)."),
) -> None:
    """Muestra o limpia el cache de modelos."""
    from ovandocode.providers import ModelsCache

    cache = ModelsCache()

    if provider is None:
        info = cache.info()
        if not info:
            console.print("(cache vacio)")
            return
        console.print("[bold]Cache de modelos:[/]")
        for entry in info:
            console.print(
                f"  {entry['provider']:<12} {entry['count']:>5} modelos   "
                f"fetched: {entry['fetched_at']}"
            )
    else:
        cache.clear(provider)
        console.print(f"[green][OK] cache limpiado: {provider}[/]")


@providers_app.command("models-clear-all")
def providers_models_clear_all() -> None:
    """Limpia TODA la cache de modelos."""
    from ovandocode.providers import ModelsCache

    cache = ModelsCache()
    cache.clear()
    console.print("[green][OK] cache de modelos limpiada completamente[/]")


# ============================================================
# SUB-COMANDO: tools
# ============================================================
tools_app = typer.Typer(help="Herramientas del agente.")
app.add_typer(tools_app, name="tools")


@tools_app.command("list")
def tools_list() -> None:
    """Lista herramientas disponibles."""
    from ovandocode.tools import ToolRegistry
    reg = ToolRegistry()
    console.print(f"[bold]== {len(reg.names())} herramientas ==[/]")
    for n in reg.names():
        t = reg.get(n)
        console.print(f"  * [cyan]{n:<18}[/] {t.description.splitlines()[0][:70]}")


@tools_app.command("call")
def tools_call(
    name: str = typer.Argument(..., help="Nombre de la tool."),
    json_args: str = typer.Option(
        "{}", "--json", "-j",
        help='Argumentos como JSON, ej: {"path": "README.md"}',
    ),
    pretty: bool = typer.Option(True, "--pretty/--raw"),
) -> None:
    """Invoca una tool directamente (util para debugging)."""
    from ovandocode.tools import ToolRegistry

    try:
        args = json.loads(json_args)
    except json.JSONDecodeError as e:
        console.print(f"[red][ERR] JSON invalido: {e}[/]")
        raise typer.Exit(1)

    async def _go():
        reg = ToolRegistry()
        return await reg.run(name, args)

    result = asyncio.run(_go())
    if pretty:
        console.print(result.content)
    else:
        sys.stdout.write(result.content + "\n")


@tools_app.command("test")
def tools_test(
    tool: str = typer.Argument(...),
    path: str = typer.Option(".", "--path", "-p"),
) -> None:
    """Prueba rapida de tools built-in."""
    from ovandocode.tools import ToolRegistry
    reg = ToolRegistry()

    async def _go():
        if tool == "read_file":
            return await reg.run("read_file", {"path": path, "limit": 10})
        if tool == "list_dir":
            return await reg.run("list_dir", {"path": path})
        if tool == "glob_files":
            return await reg.run("glob_files", {"pattern": path or "**/*.py", "max_results": 20})
        if tool == "grep":
            return await reg.run("grep", {"pattern": path or "import", "max_matches": 20})
        console.print("[red]Uso: tools test <read_file|list_dir|glob_files|grep>[/]")
        raise typer.Exit(1)

    result = asyncio.run(_go())
    console.print(result.content)


# ============================================================
# SUB-COMANDO: skills
# ============================================================
skills_app = typer.Typer(help="Gestion de skills.")
app.add_typer(skills_app, name="skills")


@skills_app.command("list")
def skills_list() -> None:
    """Lista skills disponibles."""
    from ovandocode.config import project_root
    from ovandocode.skills import SkillLoader
    loader = SkillLoader(project_root=project_root())
    skills = loader.all()
    if not skills:
        console.print("(sin skills)")
        return
    console.print(f"[bold]== {len(skills)} skill(s) ==[/]")
    for s in skills:
        origen = "builtin" if s.builtin else "proyecto"
        console.print(f"  [{origen:<8}] {s.name:<20} v{s.version:<8} {s.description[:60]}")
    errs = loader.errors()
    if errs:
        console.print(f"[yellow]\n[!] {len(errs)} error(es):[/]")
        for e in errs:
            console.print(f"[yellow]    {e}[/]")


@skills_app.command("show")
def skills_show(name: str = typer.Argument(...)) -> None:
    """Muestra una skill completa."""
    from ovandocode.config import project_root
    from ovandocode.skills import SkillError, SkillLoader
    loader = SkillLoader(project_root=project_root())
    try:
        s = loader.get(name)
    except SkillError as e:
        console.print(f"[red][ERR] {e}[/]")
        raise typer.Exit(1)
    console.print(s.to_full())
    console.print(f"\n[bright_black][path: {s.path}][/]")


@skills_app.command("init")
def skills_init(name: str = typer.Argument(...)) -> None:
    """Crea una skill nueva."""
    from ovandocode.config import project_root
    root = project_root() / "skills" / name
    path = root / "SKILL.md"
    if path.exists():
        console.print(f"[red][ERR] ya existe: {path}[/]")
        raise typer.Exit(1)
    root.mkdir(parents=True, exist_ok=True)
    content = (
        "---\n"
        f"name: {name}\n"
        "description: Describe brevemente que hace esta skill\n"
        "when_to_use: Cuando el usuario pida...\n"
        "tags: [ejemplo]\n"
        "version: 0.1.0\n"
        "---\n\n"
        f"# {name.replace('-', ' ').title()}\n\n"
        "## Instrucciones\n\n"
        "Aqui van las instrucciones detalladas que el agente debe seguir.\n"
    )
    path.write_text(content, encoding="utf-8")
    console.print(f"[green][OK] creada: {path}[/]")


# ============================================================
# SUB-COMANDO: sessions
# ============================================================
sessions_app = typer.Typer(help="Gestion de sesiones.")
app.add_typer(sessions_app, name="sessions")


@sessions_app.command("list")
def sessions_list() -> None:
    """Lista sesiones guardadas."""
    from ovandocode.config import sessions_dir
    from ovandocode.core import SessionStore
    store = SessionStore(sessions_dir())
    rows = store.list_sessions()
    if not rows:
        console.print("(sin sesiones)")
        return
    console.print(f"[bold]== {len(rows)} sesion(es) ==[/]")
    for r in rows:
        console.print(
            f"  {r.get('id','?'):<28} "
            f"msgs={r.get('message_count',0):>4}  "
            f"{r.get('updated_at','')}  "
            f"{r.get('provider','')}/{r.get('model','')}"
        )


@sessions_app.command("show")
def sessions_show(session_id: str = typer.Argument(...)) -> None:
    """Muestra el historial de una sesion."""
    from ovandocode.config import sessions_dir
    from ovandocode.core import SessionStore
    store = SessionStore(sessions_dir())
    try:
        s = store.load(session_id)
    except FileNotFoundError as e:
        console.print(f"[red][ERR] {e}[/]")
        raise typer.Exit(1)
    console.print(f"[bold]== sesion {s.id} ==[/]")
    console.print(f"  provider: {s.provider}")
    console.print(f"  model:    {s.model}")
    console.print(f"  created:  {s.created_at}")
    console.print(f"  updated:  {s.updated_at}")
    console.print(f"  msgs:     {len(s.messages)}")
    console.print("")
    for i, m in enumerate(s.messages, 1):
        content = (m.content or "").replace("\n", " ")
        if len(content) > 100:
            content = content[:100] + "..."
        tools = ""
        if m.tool_calls:
            tools = " (tools: " + ", ".join(tc.name for tc in m.tool_calls) + ")"
        console.print(f"  [{i:>3}] {m.role:<9} {content}{tools}")


@sessions_app.command("delete")
def sessions_delete(session_id: str = typer.Argument(...)) -> None:
    """Elimina una sesion."""
    from ovandocode.config import sessions_dir
    from ovandocode.core import SessionStore
    store = SessionStore(sessions_dir())
    if store.delete(session_id):
        console.print(f"[green][OK] eliminada: {session_id}[/]")
    else:
        console.print(f"[red][ERR] no existe: {session_id}[/]")


@sessions_app.command("stats")
def sessions_stats(session_id: str = typer.Argument(...)) -> None:
    """Muestra stats de contexto."""
    from ovandocode.config import get_settings, sessions_dir
    from ovandocode.core import ContextManager, SessionStore
    store = SessionStore(sessions_dir())
    try:
        s = store.load(session_id)
    except FileNotFoundError as e:
        console.print(f"[red][ERR] {e}[/]")
        raise typer.Exit(1)
    st = get_settings()
    cm = ContextManager(threshold=st.compact_threshold)
    stats = cm.stats(s.messages)
    console.print(f"[bold]== stats sesion {s.id} ==[/]")
    console.print(f"  mensajes:           {stats.messages}")
    console.print(f"  tokens (estimados): {stats.estimated_tokens}")
    console.print(f"  limite contexto:    {stats.context_limit}")
    console.print(f"  uso:                {stats.usage_pct * 100:.2f}%")
    console.print(f"  necesita compactar: {stats.needs_compact}")


@sessions_app.command("resume")
def sessions_resume(session_id: str = typer.Argument(...)) -> None:
    """Reanuda una sesion en la TUI."""
    from ovandocode.config import get_settings, sessions_dir
    from ovandocode.core import AgentConfig, SessionStore
    from ovandocode.tui import OvandoCodeApp

    store = SessionStore(sessions_dir())
    try:
        s = store.load(session_id)
    except FileNotFoundError as e:
        console.print(f"[red][ERR] {e}[/]")
        raise typer.Exit(1)
    cfg = AgentConfig(
        provider=s.provider or get_settings().default_provider,
        model=s.model or get_settings().default_model,
    )
    tui = OvandoCodeApp(cfg)
    tui.session = s  # precarga
    tui.run()


# ============================================================
# SUB-COMANDO: history
# ============================================================
@app.command()
def history(
    limit: int = typer.Option(10, "--limit", "-n"),
) -> None:
    """Muestra las ultimas sesiones."""
    from ovandocode.config import sessions_dir
    from ovandocode.core import SessionStore
    store = SessionStore(sessions_dir())
    rows = store.list_sessions()[:limit]
    if not rows:
        console.print("(sin sesiones)")
        return
    console.print(f"[bold]Ultimas {len(rows)} sesiones:[/]")
    for r in rows:
        console.print(
            f"  [cyan]{r.get('id','?')}[/]  "
            f"msgs={r.get('message_count',0):>3}  "
            f"{r.get('updated_at','')}  "
            f"{r.get('provider','')}/{r.get('model','')}"
        )


# ============================================================
# SUB-COMANDO: mcp
# ============================================================
mcp_app = typer.Typer(help="Servidores MCP.")
app.add_typer(mcp_app, name="mcp")


@mcp_app.command("list")
def mcp_list() -> None:
    """Lista servidores MCP configurados."""
    from ovandocode.config import project_root
    from ovandocode.mcp.config import default_config_path, load_mcp_config
    path = default_config_path(project_root())
    if not path.exists():
        console.print(f"(no existe {path})")
        console.print("Crea uno con: ovandocode mcp init")
        return
    try:
        configs = load_mcp_config(path)
    except Exception as e:
        console.print(f"[red][ERR] {e}[/]")
        raise typer.Exit(1)
    if not configs:
        console.print("(sin servidores MCP habilitados)")
        return
    console.print(f"[bold]== {len(configs)} servidor(es) MCP ==[/]")
    for c in configs:
        console.print(f"  * [cyan]{c.name:<15}[/] [{c.transport}]")
        if c.transport == "stdio":
            console.print(f"      {c.command} {' '.join(c.args)}")
        else:
            console.print(f"      {c.url}")
        if c.description:
            console.print(f"      [dim]{c.description}[/]")


@mcp_app.command("init")
def mcp_init() -> None:
    """Crea un mcp.json con un servidor de ejemplo."""
    from ovandocode.config import project_root
    from ovandocode.mcp.config import default_config_path
    path = default_config_path(project_root())
    if path.exists():
        console.print(f"[red][ERR] ya existe: {path}[/]")
        raise typer.Exit(1)
    content = (
        "{\n"
        '  "mcpServers": {\n'
        '    "hello": {\n'
        '      "transport": "stdio",\n'
        '      "command": ".venv\\\\Scripts\\\\python.exe",\n'
        '      "args": ["scripts/mcp_hello_server.py"],\n'
        '      "description": "Servidor MCP de ejemplo"\n'
        "    }\n"
        "  }\n"
        "}\n"
    )
    path.write_text(content, encoding="utf-8")
    console.print(f"[green][OK] creado: {path}[/]")


@mcp_app.command("test")
def mcp_test(
    name: str | None = typer.Argument(None),
) -> None:
    """Prueba los servidores MCP listando sus tools."""
    from ovandocode.config import project_root
    from ovandocode.mcp.config import default_config_path, load_mcp_config
    from ovandocode.mcp.manager import MCPManager

    path = default_config_path(project_root())
    configs = load_mcp_config(path)
    if name:
        configs = [c for c in configs if c.name == name]
    if not configs:
        console.print("[red][ERR] sin servidores MCP que probar[/]")
        raise typer.Exit(1)

    async def _go() -> None:
        mgr = MCPManager(configs)
        await mgr.start_all()
        try:
            if mgr.errors:
                for srv, err in mgr.errors.items():
                    console.print(f"[red][ERR] {srv}: {err}[/]")
            for srv, client in mgr.clients.items():
                console.print(f"[cyan]== {srv} ({len(client.tools)} tools) ==[/]")
                for t in client.tools:
                    console.print(f"  * {t.name}: {getattr(t, 'description', '')[:70]}")
        finally:
            await mgr.stop_all()

    asyncio.run(_go())


# ============================================================
# SUB-COMANDO: perm
# ============================================================
perm_app = typer.Typer(help="Politica de permisos.")
app.add_typer(perm_app, name="perm")


@perm_app.command("check")
def perm_check(
    command: str = typer.Argument(...),
    mode: str = typer.Option("allowlist", "--mode", "-m"),
) -> None:
    """Evalua como la politica trataria un comando."""
    from ovandocode.permissions import PermissionPolicy
    pol = PermissionPolicy(mode=mode)  # type: ignore
    v = pol.decide(command)
    color = {"allow": "green", "ask": "yellow", "deny": "red"}[v.decision.value]
    console.print(f"[{color}][{v.decision.value.upper()}][/] {v.reason}")



def main() -> None:
    """Entrypoint para el script ovandocode."""
    app()


if __name__ == "__main__":
    app()
