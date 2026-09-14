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
