# ============================================================
#  OVANDOCODE - FASE 2: Configuracion y credenciales
#  Guardar como: D:\Trabajo\OvandoCode\_fase2.ps1
# ============================================================
$ErrorActionPreference = 'Stop'
$ProjectRoot = 'D:\Trabajo\OvandoCode'
Set-Location $ProjectRoot
$utf8 = New-Object System.Text.UTF8Encoding $false
$src = "$ProjectRoot\src\ovandocode"

Write-Host "=== OVANDOCODE :: Fase 2 - Config y credenciales ===" -ForegroundColor Cyan

function Write-File($path, $content) {
    $dir = Split-Path $path -Parent
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    [IO.File]::WriteAllText($path, $content, $utf8)
    Write-Host "[OK] $path" -ForegroundColor Green
}

# ------------------------------------------------------------
# 2.1 paths.py
# ------------------------------------------------------------
$paths = @'
"""Rutas estandar de OVANDOCODE (config, datos, logs, sesiones)."""
from __future__ import annotations

import os
from pathlib import Path

from platformdirs import user_config_dir, user_data_dir, user_log_dir

APP_NAME = "OvandoCode"
APP_AUTHOR = "OvandoCode"


def config_dir() -> Path:
    """Directorio de configuracion persistente (%APPDATA%\\OvandoCode en Windows)."""
    p = Path(user_config_dir(APP_NAME, APP_AUTHOR))
    p.mkdir(parents=True, exist_ok=True)
    return p


def data_dir() -> Path:
    """Directorio de datos de usuario."""
    p = Path(user_data_dir(APP_NAME, APP_AUTHOR))
    p.mkdir(parents=True, exist_ok=True)
    return p


def logs_dir() -> Path:
    """Directorio de logs."""
    p = Path(user_log_dir(APP_NAME, APP_AUTHOR))
    p.mkdir(parents=True, exist_ok=True)
    return p


def sessions_dir() -> Path:
    """Directorio de sesiones (dentro del proyecto por defecto)."""
    root = project_root()
    p = root / "sessions"
    p.mkdir(parents=True, exist_ok=True)
    return p


def project_root() -> Path:
    """Raiz del proyecto activo.

    Prioridad:
      1) Variable de entorno OVANDOCODE_PROJECT_ROOT
      2) Directorio de trabajo actual
    """
    env = os.environ.get("OVANDOCODE_PROJECT_ROOT")
    if env:
        p = Path(env).expanduser().resolve()
        if p.is_dir():
            return p
    return Path.cwd().resolve()


def config_file() -> Path:
    return config_dir() / "config.toml"


def env_file() -> Path:
    return project_root() / ".env"
'@
Write-File "$src\config\paths.py" $paths

# ------------------------------------------------------------
# 2.2 settings.py
# ------------------------------------------------------------
$settings = @'
"""Settings globales de OVANDOCODE (Pydantic Settings)."""
from __future__ import annotations

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from ovandocode.config.paths import env_file

Provider = Literal[
    "openrouter", "openai", "anthropic", "gemini", "deepseek",
    "groq", "mistral", "xai", "ollama", "lmstudio",
]
PermissionMode = Literal["ask", "allowlist", "yolo"]
Theme = Literal["dark", "light"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="OVANDOCODE_",
        env_file=str(env_file()),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Modelo / proveedor
    default_provider: Provider = "openrouter"
    default_model: str = "anthropic/claude-sonnet-4"

    # Inferencia
    temperature: float = Field(0.2, ge=0.0, le=2.0)
    max_tokens: int = Field(8192, gt=0)
    request_timeout: float = Field(120.0, gt=0)

    # Comportamiento
    permission_mode: PermissionMode = "allowlist"
    auto_compact: bool = True
    compact_threshold: float = Field(0.8, gt=0.0, le=1.0)

    # UI
    theme: Theme = "dark"
    show_token_usage: bool = True

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    log_to_file: bool = True

    # Endpoints locales
    ollama_base_url: str = "http://localhost:11434"
    lmstudio_base_url: str = "http://localhost:1234/v1"


_settings: Settings | None = None


def get_settings() -> Settings:
    """Devuelve la instancia singleton de Settings."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings() -> Settings:
    """Recarga los settings (util tras cambiar .env o config.toml)."""
    global _settings
    _settings = Settings()
    return _settings
'@
Write-File "$src\config\settings.py" $settings

# ------------------------------------------------------------
# 2.3 credentials.py
# ------------------------------------------------------------
$credentials = @'
"""Gestor de credenciales con cascada keyring -> .env -> config.toml."""
from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import keyring
from dotenv import dotenv_values, set_key

from ovandocode.config.paths import config_file, env_file

SERVICE_NAME = "ovandocode"

# Mapeo provider -> nombre de variable de entorno
PROVIDER_ENV_KEYS: dict[str, str] = {
    "openrouter": "OPENROUTER_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "groq": "GROQ_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "xai": "XAI_API_KEY",
}

Backend = Literal["keyring", "env", "toml"]
Source = Literal["keyring", "env", "toml", "os", "none"]


@dataclass
class CredentialStatus:
    provider: str
    available: bool
    source: Source


class CredentialManager:
    """Resuelve API keys con cascada: keyring -> .env -> config.toml -> env vars."""

    def __init__(self, env_path: Path | None = None, toml_path: Path | None = None) -> None:
        self._env_path = env_path or env_file()
        self._toml_path = toml_path or config_file()

    # ---------------- lectura ----------------
    def get(self, provider: str) -> str | None:
        provider = provider.lower()

        # 1) keyring
        try:
            v = keyring.get_password(SERVICE_NAME, provider)
            if v:
                return v
        except Exception:
            pass

        # 2) .env del proyecto
        if self._env_path.exists():
            values = dotenv_values(self._env_path)
            key = PROVIDER_ENV_KEYS.get(provider)
            if key and values.get(key):
                return str(values[key])

        # 3) config.toml
        if self._toml_path.exists():
            try:
                data = tomllib.loads(self._toml_path.read_text(encoding="utf-8"))
                v = data.get("providers", {}).get(provider, {}).get("api_key")
                if v:
                    return str(v)
            except Exception:
                pass

        # 4) variable de entorno del sistema
        key = PROVIDER_ENV_KEYS.get(provider)
        if key and os.environ.get(key):
            return os.environ[key]

        return None

    def source_of(self, provider: str) -> Source:
        provider = provider.lower()
        try:
            if keyring.get_password(SERVICE_NAME, provider):
                return "keyring"
        except Exception:
            pass
        if self._env_path.exists():
            key = PROVIDER_ENV_KEYS.get(provider)
            values = dotenv_values(self._env_path)
            if key and values.get(key):
                return "env"
        if self._toml_path.exists():
            try:
                data = tomllib.loads(self._toml_path.read_text(encoding="utf-8"))
                if data.get("providers", {}).get(provider, {}).get("api_key"):
                    return "toml"
            except Exception:
                pass
        key = PROVIDER_ENV_KEYS.get(provider)
        if key and os.environ.get(key):
            return "os"
        return "none"

    # ---------------- escritura ----------------
    def set(self, provider: str, value: str, backend: Backend = "keyring") -> None:
        provider = provider.lower()
        if backend == "keyring":
            keyring.set_password(SERVICE_NAME, provider, value)
        elif backend == "env":
            self._env_path.parent.mkdir(parents=True, exist_ok=True)
            if not self._env_path.exists():
                self._env_path.write_text("", encoding="utf-8")
            key = PROVIDER_ENV_KEYS.get(provider)
            if not key:
                raise ValueError(f"Proveedor sin variable de entorno mapeada: {provider}")
            set_key(str(self._env_path), key, value)
        elif backend == "toml":
            self._write_toml(provider, value)
        else:
            raise ValueError(f"Backend desconocido: {backend}")

    def delete(self, provider: str, backend: Backend = "keyring") -> None:
        provider = provider.lower()
        if backend == "keyring":
            try:
                keyring.delete_password(SERVICE_NAME, provider)
            except keyring.errors.PasswordDeleteError:
                pass

    # ---------------- info ----------------
    def list_status(self) -> list[CredentialStatus]:
        out: list[CredentialStatus] = []
        for p in PROVIDER_ENV_KEYS:
            src = self.source_of(p)
            out.append(CredentialStatus(provider=p, available=src != "none", source=src))
        return out

    # ---------------- helpers ----------------
    def _write_toml(self, provider: str, value: str) -> None:
        import tomli_w

        data: dict = {}
        if self._toml_path.exists():
            try:
                data = tomllib.loads(self._toml_path.read_text(encoding="utf-8"))
            except Exception:
                data = {}
        data.setdefault("providers", {}).setdefault(provider, {})["api_key"] = value
        self._toml_path.parent.mkdir(parents=True, exist_ok=True)
        with self._toml_path.open("wb") as f:
            tomli_w.dump(data, f)


_manager: CredentialManager | None = None


def get_credentials() -> CredentialManager:
    global _manager
    if _manager is None:
        _manager = CredentialManager()
    return _manager
'@
Write-File "$src\config\credentials.py" $credentials

# ------------------------------------------------------------
# 2.4 config/__init__.py
# ------------------------------------------------------------
$cfginit = @'
"""Configuracion, rutas y credenciales de OVANDOCODE."""
from ovandocode.config.credentials import (
    CredentialManager,
    CredentialStatus,
    get_credentials,
)
from ovandocode.config.paths import (
    config_dir,
    config_file,
    data_dir,
    env_file,
    logs_dir,
    project_root,
    sessions_dir,
)
from ovandocode.config.settings import Settings, get_settings, reload_settings

__all__ = [
    "CredentialManager",
    "CredentialStatus",
    "get_credentials",
    "config_dir",
    "config_file",
    "data_dir",
    "env_file",
    "logs_dir",
    "project_root",
    "sessions_dir",
    "Settings",
    "get_settings",
    "reload_settings",
]
'@
Write-File "$src\config\__init__.py" $cfginit

# ------------------------------------------------------------
# 2.5 cli.py actualizado (con comandos de config)
# ------------------------------------------------------------
$cli = @'
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
'@
Write-File "$src\ovandocode\cli.py" $cli

# ------------------------------------------------------------
# 2.6 Test rapido
# ------------------------------------------------------------
Write-Host "`n-> Probando imports y CLI..." -ForegroundColor Yellow
uv run python -c "from ovandocode.config import get_settings, get_credentials; print('imports OK')"
uv run ovandocode version
uv run ovandocode config show
uv run ovandocode config providers

# ------------------------------------------------------------
# 2.7 Commit
# ------------------------------------------------------------
Write-Host "`n-> commit..." -ForegroundColor Yellow
git add .
git commit -m "Fase 2: configuracion, rutas y gestor de credenciales" | Out-Null

# ------------------------------------------------------------
# 2.8 Verificacion
# ------------------------------------------------------------
Write-Host "`n=== Verificacion Fase 2 ===" -ForegroundColor Cyan
$checks = [ordered]@{
    'config/paths.py'        = (Test-Path 'src\ovandocode\config\paths.py')
    'config/settings.py'     = (Test-Path 'src\ovandocode\config\settings.py')
    'config/credentials.py'  = (Test-Path 'src\ovandocode\config\credentials.py')
    'config/__init__.py'     = (Test-Path 'src\ovandocode\config\__init__.py')
    'cli.py actualizado'     = (Test-Path 'src\ovandocode\cli.py')
    'import ovandocode.config' = [bool](uv run python -c "import ovandocode.config" 2>$null)
    'config show funciona'   = [bool](uv run ovandocode config show 2>$null)
    'commit Fase 2'          = [bool](git log --oneline 2>$null | Select-String 'Fase 2')
}
foreach ($k in $checks.Keys) {
    $ok = $checks[$k]
    $mark  = if ($ok) { '[OK]' } else { '[!!]' }
    $color = if ($ok) { 'Green' } else { 'Red' }
    Write-Host "$mark $k" -ForegroundColor $color
}

Write-Host "`nFase 2 completada." -ForegroundColor Cyan