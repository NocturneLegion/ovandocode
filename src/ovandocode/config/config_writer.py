"""Gestor del archivo config.toml global de OVANDOCODE."""
from __future__ import annotations

import tomllib
from dataclasses import asdict
from pathlib import Path
from typing import Any

import tomli_w

from ovandocode.config.paths import config_file

# Campos que se pueden persistir y su tipo
PERSISTABLE_FIELDS: dict[str, type] = {
    "default_provider": str,
    "default_model": str,
    "temperature": float,
    "max_tokens": int,
    "request_timeout": float,
    "permission_mode": str,
    "auto_compact": bool,
    "compact_threshold": float,
    "theme": str,
    "show_token_usage": bool,
    "log_level": str,
    "log_to_file": bool,
    "ollama_base_url": str,
    "lmstudio_base_url": str,
}


class GlobalConfigError(Exception):
    """Error al leer o escribir config.toml."""


class GlobalConfig:
    """Lee y escribe los defaults persistentes en config.toml.

    Estructura:
        [defaults]
        default_provider = "groq"
        default_model = "openai/gpt-oss-120b"
        ...
    """

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or config_file()

    # ---------------- IO ----------------
    def _load_raw(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        try:
            with self.path.open("rb") as f:
                return tomllib.load(f)
        except (tomllib.TOMLDecodeError, OSError) as e:
            raise GlobalConfigError(f"Error leyendo {self.path}: {e}") from None

    def _save_raw(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with self.path.open("wb") as f:
                tomli_w.dump(data, f)
        except OSError as e:
            raise GlobalConfigError(f"Error escribiendo {self.path}: {e}") from None

    # ---------------- API ----------------
    def all(self) -> dict[str, Any]:
        """Devuelve todos los defaults persistidos."""
        data = self._load_raw()
        return dict(data.get("defaults", {}))

    def get(self, key: str) -> Any:
        """Devuelve un valor o None si no esta seteado."""
        return self.all().get(key)

    def set(self, key: str, value: Any) -> None:
        """Persiste una clave. Valida el tipo si es conocida."""
        if key not in PERSISTABLE_FIELDS:
            raise GlobalConfigError(
                f"Campo desconocido: '{key}'. "
                f"Validos: {sorted(PERSISTABLE_FIELDS)}"
            )
        expected = PERSISTABLE_FIELDS[key]
        value = self._coerce(key, value, expected)

        data = self._load_raw()
        defaults = data.setdefault("defaults", {})
        defaults[key] = value
        self._save_raw(data)

    def unset(self, key: str) -> bool:
        """Borra una clave. Devuelve True si existia."""
        data = self._load_raw()
        defaults = data.get("defaults", {})
        if key not in defaults:
            return False
        del defaults[key]
        data["defaults"] = defaults
        self._save_raw(data)
        return True

    def reset(self) -> None:
        """Borra TODO el archivo."""
        if self.path.exists():
            self.path.unlink()

    def exists(self) -> bool:
        return self.path.exists()

    def path_str(self) -> str:
        return str(self.path)

    # ---------------- helpers ----------------
    @staticmethod
    def _coerce(key: str, value: Any, expected: type) -> Any:
        try:
            if expected is bool:
                if isinstance(value, bool):
                    return value
                s = str(value).strip().lower()
                if s in ("true", "1", "yes", "y", "on"):
                    return True
                if s in ("false", "0", "no", "n", "off"):
                    return False
                raise ValueError(f"no es booleano: {value!r}")
            if expected is int:
                return int(value)
            if expected is float:
                return float(value)
            return str(value)
        except (ValueError, TypeError) as e:
            raise GlobalConfigError(
                f"Valor invalido para '{key}' ({expected.__name__}): {value!r} ({e})"
            ) from None


# Campos persistidos por defecto (para reset y validacion)
DEFAULT_PERSISTED_FIELDS = tuple(PERSISTABLE_FIELDS.keys())


__all__ = [
    "DEFAULT_PERSISTED_FIELDS",
    "GlobalConfig",
    "GlobalConfigError",
    "PERSISTABLE_FIELDS",
]
