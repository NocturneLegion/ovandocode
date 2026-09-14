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
