"""OVANDOCODE - CLI (Fase 2: version y config)."""
from __future__ import annotations

import os
import sys

import typer

from ovandocode import __version__
from ovandocode.config import (
    config_dir,
    get_credentials,
    get_settings,
    logs_dir,
    project_root,
)

app = typer.Typer(
    name="ovandocode",
    help="OVANDOCODE - Agente de codificacion autonomo.",
    no_args_is_help=False,
    add_completion=False,
)

config_app = typer.Typer(help="Gestion de configuracion y credenciales.")
app.add_typer(config_app, name="config")


@app.command()
def version() -> None:
    """Muestra la version de OVANDOCODE."""
    typer.echo(f"OVANDOCODE v{__version__}")


@config_app.command("show")
def config_show() -> None:
    """Muestra la configuracion activa."""
    s = get_settings()
    typer.echo("== OVANDOCODE config ==")
    typer.echo(f"  project_root     : {project_root()}")
    typer.echo(f"  config_dir       : {config_dir()}")
    typer.echo(f"  logs_dir         : {logs_dir()}")
    typer.echo(f"  default_provider : {s.default_provider}")
    typer.echo(f"  default_model    : {s.default_model}")
    typer.echo(f"  permission_mode  : {s.permission_mode}")
    typer.echo(f"  theme            : {s.theme}")
    typer.echo(f"  log_level        : {s.log_level}")


@config_app.command("providers")
def config_providers() -> None:
    """Lista el estado de cada proveedor (key disponible y donde)."""
    cm = get_credentials()
    typer.echo("== Proveedores ==")
    for st in cm.list_status():
        mark = "OK " if st.available else "-- "
        typer.echo(f"  [{mark}] {st.provider:<12} source={st.source}")


@config_app.command("set-key")
def config_set_key(
    provider: str = typer.Argument(..., help="openrouter, openai, anthropic, ..."),
    value: str | None = typer.Option(
        None, "--value", "-v",
        help="API key directa (util para pegar en terminal).",
    ),
    from_env: str | None = typer.Option(
        None, "--from-env",
        help="Nombre de variable de entorno que contiene la key.",
    ),
    from_stdin: bool = typer.Option(
        False, "--stdin",
        help="Lee la key desde stdin (echo 'KEY' | ovandocode config set-key ...).",
    ),
    backend: str = typer.Option(
        "keyring", "--backend", "-b",
        help="keyring | env | toml",
    ),
    force: bool = typer.Option(
        False, "--force", "-f",
        help="No pregunta confirmacion.",
    ),
) -> None:
    """Guarda la API key de un proveedor.

    Formas de uso:
      1) ovandocode config set-key openrouter --value "sk-or-..."
      2) ovandocode config set-key openrouter --from-env OPENROUTER_API_KEY
      3) echo sk-or-... | ovandocode config set-key openrouter --stdin
      4) ovandocode config set-key openrouter    (prompt interactivo)
    """
    key: str | None = None

    if value:
        key = value.strip()
    elif from_env:
        key = os.environ.get(from_env, "").strip() or None
        if not key:
            typer.secho(f"[ERR] Variable {from_env} vacia o no existe.", fg="red")
            raise typer.Exit(1)
    elif from_stdin:
        key = sys.stdin.read().strip() or None
        if not key:
            typer.secho("[ERR] stdin vacio.", fg="red")
            raise typer.Exit(1)
    else:
        # Fallback interactivo
        typer.echo(f"Ingresa la API key para {provider} y presiona Enter.")
        typer.echo("(El texto no se vera mientras escribes)")
        try:
            key = typer.prompt("API key", hide_input=True)
        except (KeyboardInterrupt, typer.Abort):
            typer.secho("\n[ABORT] Entrada cancelada.", fg="yellow")
            raise typer.Exit(1)
        key = (key or "").strip() or None

    if not key:
        typer.secho("[ERR] Key vacia.", fg="red")
        raise typer.Exit(1)

    # Confirmar si no hay --force
    preview = f"{key[:8]}...{key[-4:]}" if len(key) > 14 else "***"
    if not force:
        typer.echo(f"Provider: {provider}")
        typer.echo(f"Backend : {backend}")
        typer.echo(f"Valor   : {preview}")
        if not typer.confirm("Guardar?", default=True):
            typer.secho("[ABORT] Cancelado.", fg="yellow")
            raise typer.Exit(1)

    cm = get_credentials()
    try:
        cm.set(provider, key, backend=backend)  # type: ignore[arg-type]
    except Exception as e:
        typer.secho(f"[ERR] No se pudo guardar: {e}", fg="red")
        raise typer.Exit(1)

    typer.secho(f"[OK] key guardada en {backend}", fg="green")
    # Mostrar fuente resultante
    typer.echo(f"     source actual: {cm.source_of(provider)}")


@config_app.command("del-key")
def config_del_key(provider: str = typer.Argument(...)) -> None:
    """Elimina la API key (solo backend keyring)."""
    cm = get_credentials()
    cm.delete(provider, backend="keyring")
    typer.echo(f"[OK] key eliminada de keyring: {provider}")


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


tools_app = typer.Typer(help="Herramientas del agente.")
app.add_typer(tools_app, name="tools")


@tools_app.command("list")
def tools_list() -> None:
    """Lista herramientas built-in."""
    from ovandocode.tools import ToolRegistry
    reg = ToolRegistry()
    typer.echo("== Herramientas disponibles ==")
    for n in reg.names():
        t = reg.get(n)
        typer.echo(f"  * {n:<15} {t.description.splitlines()[0][:60]}")


@tools_app.command("test")
def tools_test(
    tool: str = typer.Argument(...),
    path: str = typer.Option(".", "--path", "-p"),
) -> None:
    """Prueba rapida de una herramienta (read_file, list_dir, glob_files)."""
    import asyncio

    from ovandocode.tools import ToolRegistry
    reg = ToolRegistry()

    async def _go() -> None:
        if tool == "read_file":
            res = await reg.run("read_file", {"path": path, "limit": 10})
        elif tool == "list_dir":
            res = await reg.run("list_dir", {"path": path})
        elif tool == "glob_files":
            res = await reg.run("glob_files", {"pattern": path or "**/*.py", "max_results": 20})
        elif tool == "grep":
            res = await reg.run("grep", {"pattern": path or "import", "max_matches": 20})
        else:
            typer.secho(f"[ERR] Uso: tools test <read_file|list_dir|glob_files|grep>", fg="red")
            raise typer.Exit(1)
        typer.echo(res.content)

    asyncio.run(_go())


perm_app = typer.Typer(help="Politica de permisos.")
app.add_typer(perm_app, name="perm")


@perm_app.command("check")
def perm_check(
    command: str = typer.Argument(..., help="Comando a evaluar (entre comillas)."),
    mode: str = typer.Option("allowlist", "--mode", "-m", help="ask | allowlist | yolo"),
) -> None:
    """Evalua como la politica trataria un comando."""
    from ovandocode.permissions import PermissionPolicy
    pol = PermissionPolicy(mode=mode)  # type: ignore[arg-type]
    v = pol.decide(command)
    color = {"allow": "green", "ask": "yellow", "deny": "red"}[v.decision.value]
    typer.secho(f"[{v.decision.value.upper()}] {v.reason}", fg=color)


shell_app = typer.Typer(help="Pruebas de shell tools.")
app.add_typer(shell_app, name="shell")


@shell_app.command("ps")
def shell_ps(
    command: str = typer.Argument(..., help="Comando PowerShell."),
) -> None:
    """Ejecuta un comando PowerShell usando la tool interna."""
    import asyncio
    from ovandocode.tools import ToolRegistry

    async def _go() -> None:
        reg = ToolRegistry()
        res = await reg.run("run_powershell", {"command": command, "timeout": 30})
        typer.echo(res.content)

    asyncio.run(_go())


@shell_app.command("py")
def shell_py(
    code: str = typer.Argument(..., help="Codigo Python (entre comillas)."),
) -> None:
    """Ejecuta un snippet Python usando la tool interna."""
    import asyncio
    from ovandocode.tools import ToolRegistry

    async def _go() -> None:
        reg = ToolRegistry()
        res = await reg.run("run_python", {"code": code, "timeout": 30})
        typer.echo(res.content)

    asyncio.run(_go())


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
        typer.echo("(sin skills)")
        return
    typer.echo(f"== {len(skills)} skill(s) ==")
    for s in skills:
        origen = "builtin" if s.builtin else "proyecto"
        typer.echo(f"  [{origen:<8}] {s.name:<20} v{s.version:<8} {s.description[:60]}")
    errs = loader.errors()
    if errs:
        typer.secho(f"\n[!] {len(errs)} error(es):", fg="yellow")
        for e in errs:
            typer.secho(f"    {e}", fg="yellow")


@skills_app.command("show")
def skills_show(name: str = typer.Argument(...)) -> None:
    """Muestra una skill completa."""
    from ovandocode.config import project_root
    from ovandocode.skills import SkillError, SkillLoader
    loader = SkillLoader(project_root=project_root())
    try:
        s = loader.get(name)
    except SkillError as e:
        typer.secho(f"[ERR] {e}", fg="red")
        raise typer.Exit(1)
    typer.echo(s.to_full())
    typer.echo("")
    typer.secho(f"[path: {s.path}]", fg="bright_black")


@skills_app.command("init")
def skills_init(name: str = typer.Argument(...)) -> None:
    """Crea una skill nueva en skills/<name>/SKILL.md."""
    from ovandocode.config import project_root
    root = project_root() / "skills" / name
    path = root / "SKILL.md"
    if path.exists():
        typer.secho(f"[ERR] ya existe: {path}", fg="red")
        raise typer.Exit(1)
    root.mkdir(parents=True, exist_ok=True)
    content = (
        "---\n"
        f"name: {name}\n"
        "description: Describe brevemente que hace esta skill\n"
        "when_to_use: Cuando el usuario pida...\n"
        "tags: [ejemplo]\n"
        "version: 0.1.0\n"
        "---\n"
        "\n"
        "# " + name.replace("-", " ").title() + "\n"
        "\n"
        "## Instrucciones\n"
        "\n"
        "Aqui van las instrucciones detalladas que el agente debe seguir.\n"
    )
    path.write_text(content, encoding="utf-8")
    typer.secho(f"[OK] creada: {path}", fg="green")
    typer.echo(f"Editala con: notepad \"{path}\"")


mcp_app = typer.Typer(help="Servidores MCP.")
app.add_typer(mcp_app, name="mcp")


@mcp_app.command("list")
def mcp_list() -> None:
    """Lista servidores MCP configurados."""
    from ovandocode.config import project_root
    from ovandocode.mcp.config import default_config_path, load_mcp_config

    path = default_config_path(project_root())
    if not path.exists():
        typer.echo(f"(no existe {path})")
        typer.echo("Crea uno con: ovandocode mcp init")
        return
    try:
        configs = load_mcp_config(path)
    except Exception as e:
        typer.secho(f"[ERR] {e}", fg="red")
        raise typer.Exit(1)
    if not configs:
        typer.echo("(sin servidores MCP habilitados)")
        return
    typer.echo(f"== {len(configs)} servidor(es) MCP ==")
    for c in configs:
        typer.echo(f"  * {c.name:<15} [{c.transport}]")
        if c.transport == "stdio":
            typer.echo(f"      {c.command} {' '.join(c.args)}")
        else:
            typer.echo(f"      {c.url}")
        if c.description:
            typer.echo(f"      {c.description}")


@mcp_app.command("init")
def mcp_init() -> None:
    """Crea un mcp.json vacio con un servidor de ejemplo."""
    from ovandocode.config import project_root
    from ovandocode.mcp.config import default_config_path

    path = default_config_path(project_root())
    if path.exists():
        typer.secho(f"[ERR] ya existe: {path}", fg="red")
        raise typer.Exit(1)
    content = (
        "{\n"
        '  "mcpServers": {\n'
        '    "hello": {\n'
        '      "transport": "stdio",\n'
        '      "command": "uv",\n'
        '      "args": ["run", "python", "scripts/mcp_hello_server.py"],\n'
        '      "description": "Servidor MCP de ejemplo"\n'
        "    }\n"
        "  }\n"
        "}\n"
    )
    path.write_text(content, encoding="utf-8")
    typer.secho(f"[OK] creado: {path}", fg="green")


@mcp_app.command("test")
def mcp_test(
    name: str = typer.Argument(None, help="Nombre del servidor (opcional, prueba todos)."),
) -> None:
    """Inicia los servidores MCP y lista sus tools."""
    import asyncio
    from ovandocode.config import project_root
    from ovandocode.mcp.config import default_config_path, load_mcp_config
    from ovandocode.mcp.manager import MCPManager

    path = default_config_path(project_root())
    configs = load_mcp_config(path)
    if name:
        configs = [c for c in configs if c.name == name]
    if not configs:
        typer.secho("[ERR] sin servidores MCP que probar", fg="red")
        raise typer.Exit(1)

    async def _go() -> None:
        mgr = MCPManager(configs)
        await mgr.start_all()
        try:
            if mgr.errors:
                for srv, err in mgr.errors.items():
                    typer.secho(f"[ERR] {srv}: {err}", fg="red")
            for srv, client in mgr.clients.items():
                typer.secho(f"== {srv} ({len(client.tools)} tools) ==", fg="cyan")
                for t in client.tools:
                    typer.echo(f"  * {t.name}: {getattr(t, 'description', '')[:70]}")
        finally:
            await mgr.stop_all()

    asyncio.run(_go())


def main() -> None:

    """Entrypoint principal (TUI en Fase 9)."""
    if len(sys.argv) == 1:
        typer.echo("OVANDOCODE - Fase 2 OK (TUI llega en Fase 9)")
        typer.echo("Prueba: uv run ovandocode config show")
        return
    app()


if __name__ == "__main__":
    main()