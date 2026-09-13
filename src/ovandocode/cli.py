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


def main() -> None:
    """Entrypoint principal (TUI en Fase 9)."""
    if len(sys.argv) == 1:
        typer.echo("OVANDOCODE - Fase 2 OK (TUI llega en Fase 9)")
        typer.echo("Prueba: uv run ovandocode config show")
        return
    app()


if __name__ == "__main__":
    main()