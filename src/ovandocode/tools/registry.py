"""Registro global de herramientas disponibles."""
from __future__ import annotations

from pathlib import Path

from ovandocode.permissions import PermissionPolicy
from ovandocode.tools.bash_tool import BashTool
from ovandocode.tools.base import BaseTool, ToolError, ToolResult
from ovandocode.tools.edit_file import EditFileTool
from ovandocode.tools.glob_tool import GlobTool
from ovandocode.tools.grep import GrepTool
from ovandocode.tools.list_dir import ListDirTool
from ovandocode.tools.powershell_tool import PowerShellTool
from ovandocode.tools.python_tool import PythonTool
from ovandocode.tools.read_file import ReadFileTool
from ovandocode.tools.write_file import WriteFileTool

# Orden importa: los primeros van primero en el prompt del LLM
BUILTIN_TOOLS: list[type[BaseTool]] = [
    ReadFileTool,
    WriteFileTool,
    EditFileTool,
    ListDirTool,
    GlobTool,
    GrepTool,
    PowerShellTool,
    BashTool,
    PythonTool,
]


class ToolRegistry:
    """Contiene las herramientas activas de una sesion del agente."""

    def __init__(
        self,
        project_root: Path | None = None,
        policy: PermissionPolicy | None = None,
    ) -> None:
        self.project_root = (project_root or Path.cwd()).resolve()
        self.policy = policy or PermissionPolicy()
        self._tools: dict[str, BaseTool] = {}
        for cls in BUILTIN_TOOLS:
            try:
                self.register(cls(project_root=self.project_root))
            except Exception as e:
                # bash puede no estar disponible, no es fatal
                print(f"[warn] no se pudo registrar {cls.__name__}: {e}")

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