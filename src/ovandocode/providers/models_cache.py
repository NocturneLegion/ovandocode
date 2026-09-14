"""Cache persistente de listas de modelos por proveedor."""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from ovandocode.config.paths import data_dir

CACHE_TTL_HOURS = 24
CACHE_FILENAME = "models_cache.json"


def cache_file() -> Path:
    return data_dir() / CACHE_FILENAME


class ModelsCache:
    """Cache en disco con TTL configurable."""

    def __init__(self, path: Path | None = None, ttl_hours: int = CACHE_TTL_HOURS) -> None:
        self.path = path or cache_file()
        self.ttl_hours = ttl_hours
        self._data: dict[str, dict] = self._load()

    # ---------------- IO ----------------
    def _load(self) -> dict:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    # ---------------- API ----------------
    def get(self, provider: str) -> list[str] | None:
        """Devuelve modelos cacheados o None si no hay o estan viejos."""
        entry = self._data.get(provider)
        if not entry:
            return None
        try:
            when = datetime.fromisoformat(entry.get("fetched_at", ""))
        except ValueError:
            return None
        if datetime.now() - when >= timedelta(hours=self.ttl_hours):
            return None
        models = entry.get("models") or []
        return list(models) if models else None

    def set(self, provider: str, models: list[str]) -> None:
        self._data[provider] = {
            "fetched_at": datetime.now().isoformat(timespec="seconds"),
            "models": list(models),
            "count": len(models),
        }
        self._save()

    def clear(self, provider: str | None = None) -> None:
        if provider:
            self._data.pop(provider, None)
        else:
            self._data.clear()
        self._save()

    def info(self) -> list[dict]:
        """Info de cada proveedor cacheado."""
        out = []
        for prov, entry in sorted(self._data.items()):
            out.append({
                "provider": prov,
                "count": entry.get("count", len(entry.get("models", []))),
                "fetched_at": entry.get("fetched_at", ""),
            })
        return out
