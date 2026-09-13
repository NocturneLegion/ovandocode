"""Clase base e infraestructura comun para todas las herramientas."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ToolError(Exception):
    """Error controlado dentro de una herramienta (se reporta al LLM)."""


@dataclass
class ToolResult:
    """Resultado de ejecutar una herramienta."""
    ok: bool
    content: str
    meta: dict[str, Any] | None = None

    def to_text(self) -> str:
        return self.content


class BaseTool(ABC):
    """Interfaz de una herramienta invocable por el LLM.

    Cada subclase declara:
      - name: identificador unico (snake_case)
      - description: texto que ve el LLM
      - parameters: JSON Schema de los argumentos
      - run(**kwargs) -> ToolResult
    """

    name: str = ""
    description: str = ""
    parameters: dict[str, Any] = {"type": "object", "properties": {}}

    def __init__(self, project_root: Path | None = None) -> None:
        self.project_root = (project_root or Path.cwd()).resolve()

    # ---------------- contrato ----------------
    @abstractmethod
    async def run(self, **kwargs: Any) -> ToolResult:
        ...

    # ---------------- helpers ----------------
    def schema(self) -> dict[str, Any]:
        """Devuelve el schema en formato OpenAI tools."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def _resolve(self, path: str, must_exist: bool = False) -> Path:
        """Resuelve una ruta relativa contra project_root con sandbox.

        Bloquea escapes fuera del project_root (ej: ../../Windows).
        """
        p = Path(path)
        if not p.is_absolute():
            p = self.project_root / p
        try:
            p = p.resolve()
        except OSError as e:
            raise ToolError(f"Ruta invalida: {path} ({e})") from e

        # Sandbox
        try:
            p.relative_to(self.project_root)
        except ValueError:
            raise ToolError(
                f"Ruta fuera del proyecto permitido: {path} "
                f"(project_root={self.project_root})"
            ) from None

        if must_exist and not p.exists():
            raise ToolError(f"Archivo o directorio no existe: {path}")
        return p