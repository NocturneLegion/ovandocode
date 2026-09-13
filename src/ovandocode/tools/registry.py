"""Registro global de herramientas disponibles."""
from __future__ import annotations

from pathlib import Path

from ovandocode.tools.base import BaseTool, ToolError, ToolResult
from ovandocode.tools.edit_file import EditFileTool
from ovandocode.tools.glob_tool import GlobTool
from ovandocode.tools.grep import GrepTool
from ovandocode.tools.list_dir import ListDirTool
from ovandocode.tools.read_file import ReadFileTool
from ovandocode.tools.write_file import WriteFileTool

BUILTIN_TOOLS: list[type[BaseTool]] = [
    ReadFileTool,
    WriteFileTool,
    EditFileTool,
    ListDirTool,
    GlobTool,
    GrepTool,
]


class ToolRegistry:
    """Contiene las herramientas activas de una sesion del agente."""

    def __init__(self, project_root: Path | None = None) -> None:
        self.project_root = (project_root or Path.cwd()).resolve()
        self._tools: dict[str, BaseTool] = {}
        for cls in BUILTIN_TOOLS:
            self.register(cls(project_root=self.project_root))

    def register(self, tool: BaseTool) -> None:
        if not tool.name:
            raise ValueError(f"Tool sin nombre: {type(tool).__name__}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool:
        if name not in self._tools:
            raise ToolError(f"Herramienta desconocida: {name}")
        return self._tools[name]

    def names(self) -> list[str]:
        return sorted(self._tools.keys())

    def schemas(self) -> list[dict]:
        """Devuelve todos los schemas en formato OpenAI tools."""
        return [t.schema() for t in self._tools.values()]

    async def run(self, name: str, arguments: dict) -> ToolResult:
        tool = self.get(name)
        try:
            return await tool.run(**arguments)
        except ToolError as e:
            return ToolResult(ok=False, content=f"[ERROR] {e}")
        except Exception as e:
            return ToolResult(ok=False, content=f"[ERROR inesperado] {type(e).__name__}: {e}")


__all__ = ["BaseTool", "ToolError", "ToolRegistry", "ToolResult", "BUILTIN_TOOLS"]