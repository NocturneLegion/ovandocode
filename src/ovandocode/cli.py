"""OVANDOCODE - CLI (Fase 2: version y config)."""
from __future__ import annotations

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
    backend: str = typer.Option("keyring", help="keyring | env | toml"),
) -> None:
    """Guarda la API key de un proveedor (pide el valor de forma segura)."""
    value = typer.prompt(f"API key para {provider}", hide_input=True)
    cm = get_credentials()
    cm.set(provider, value, backend=backend)  # type: ignore[arg-type]
    typer.echo(f"[OK] key guardada en {backend}")


@config_app.command("del-key")
def config_del_key(provider: str = typer.Argument(...)) -> None:
    """Elimina la API key (solo backend keyring)."""
    cm = get_credentials()
    cm.delete(provider, backend="keyring")
    typer.echo(f"[OK] key eliminada de keyring: {provider}")


def main() -> None:
    """Entrypoint principal (TUI en Fase 9)."""
    if len(__import__("sys").argv) == 1:
        typer.echo("OVANDOCODE - Fase 2 OK (TUI llega en Fase 9)")
        typer.echo("Prueba: uv run ovandocode config show")
        return
    app()


if __name__ == "__main__":
    main()