"""Settings globales de OVANDOCODE (Pydantic Settings)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import Field
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

from ovandocode.config.paths import config_file, env_file

Provider = Literal[
    "openrouter", "openai", "anthropic", "gemini", "deepseek",
    "groq", "mistral", "xai", "ollama", "lmstudio",
]
PermissionMode = Literal["ask", "allowlist", "yolo"]
Theme = Literal["dark", "light"]


class TomlDefaultsSource(PydanticBaseSettingsSource):
    """Lee la seccion [defaults] de config.toml (fuente de menor prioridad)."""

    def __init__(self, settings_cls, toml_path):  # type: ignore[no-untyped-def]
        super().__init__(settings_cls)
        self._toml_path = toml_path

    def get_field_value(self, field, field_name):  # type: ignore[no-untyped-def]
        return None, field_name, False

    def __call__(self) -> dict[str, Any]:
        import tomllib
        from pathlib import Path

        p = Path(self._toml_path)
        if not p.exists():
            return {}
        try:
            with p.open("rb") as f:
                data = tomllib.load(f)
        except Exception:
            return {}
        defaults = data.get("defaults", {})
        return {k: v for k, v in defaults.items() if v is not None}


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

    @classmethod
    def settings_customise_sources(  # type: ignore[override]
        cls,
        settings_cls,
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        """Orden de prioridad (mayor gana):
            1. init_settings (argumentos directos del CLI)
            2. toml_defaults (config.toml global: fuente de verdad del usuario)
            3. env_settings (variables OVANDOCODE_* del SO)
            4. dotenv_settings (.env del proyecto, solo secretos de desarrollo)
            5. defaults del codigo

        El config.toml global GANA sobre .env y variables de entorno para que la
        configuracion elegida por el usuario en la TUI se respete siempre,
        sin importar el proyecto o carpeta desde donde se ejecute.
        """
        toml_source = TomlDefaultsSource(settings_cls, config_file())
        return (
            init_settings,
            toml_source,
            env_settings,
            dotenv_settings,
            file_secret_settings,
        )


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
