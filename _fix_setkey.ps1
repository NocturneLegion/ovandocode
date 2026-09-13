# ============================================================
#  OVANDOCODE - FIX set-key: metodos alternativos de entrada
#  Guardar como: D:\Trabajo\OvandoCode\_fix_setkey.ps1
# ============================================================
$ErrorActionPreference = 'Stop'
$ProjectRoot = 'D:\Trabajo\OvandoCode'
Set-Location $ProjectRoot
$utf8 = New-Object System.Text.UTF8Encoding $false

Write-Host "=== FIX set-key ===" -ForegroundColor Cyan

$cliPath = "$ProjectRoot\src\ovandocode\cli.py"

$cli = @'
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


def main() -> None:
    """Entrypoint principal (TUI en Fase 9)."""
    if len(sys.argv) == 1:
        typer.echo("OVANDOCODE - Fase 2 OK (TUI llega en Fase 9)")
        typer.echo("Prueba: uv run ovandocode config show")
        return
    app()


if __name__ == "__main__":
    main()
'@

[IO.File]::WriteAllText($cliPath, $cli, $utf8)
Write-Host "[OK] cli.py actualizado" -ForegroundColor Green

# Prueba de ayuda
Write-Host "`n-> probando ayuda del comando..." -ForegroundColor Yellow
uv run ovandocode config set-key --help

# Commit
Write-Host "`n-> commit..." -ForegroundColor Yellow
git add .
git commit -m "Fix Fase 2: set-key acepta --value, --from-env, --stdin" | Out-Null

Write-Host "`nFix set-key completado." -ForegroundColor Cyan