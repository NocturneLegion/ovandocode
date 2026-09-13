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