"""Registro global de herramientas disponibles."""
from __future__ import annotations

from pathlib import Path

from ovandocode.permissions import PermissionPolicy
from ovandocode.tools.base import BaseTool, ToolError, ToolResult
from ovandocode.tools.bash_tool import BashTool
from ovandocode.tools.edit_file import EditFileTool
from ovandocode.tools.glob_tool import GlobTool
from ovandocode.tools.grep import GrepTool
from ovandocode.tools.list_dir import ListDirTool
from ovandocode.tools.load_skill import LoadSkillTool
from ovandocode.tools.mcp_tool import MCPTool
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
    LoadSkillTool,
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
        self.mcp_manager = None  # se asigna en async_setup_mcp
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



    async def async_setup_mcp(self) -> None:
        """Descubre servidores MCP y registra sus tools."""
        from ovandocode.mcp.config import default_config_path, load_mcp_config
        from ovandocode.mcp.manager import MCPManager

        cfg_path = default_config_path(self.project_root)
        try:
            configs = load_mcp_config(cfg_path)
        except Exception as e:
            print(f"[warn] mcp.json invalido: {e}")
            return
        if not configs:
            return

        self.mcp_manager = MCPManager(configs)
        await self.mcp_manager.start_all()

        for server_name, tool_def in self.mcp_manager.all_tools():
            schema = getattr(tool_def, "inputSchema", None) or {
                "type": "object",
                "properties": {},
            }
            self.register(
                MCPTool(
                    manager=self.mcp_manager,
                    server_name=server_name,
                    mcp_tool_name=getattr(tool_def, "name", "?"),
                    description=getattr(tool_def, "description", ""),
                    schema=schema,
                )
            )

    async def async_teardown_mcp(self) -> None:
        if self.mcp_manager is not None:
            await self.mcp_manager.stop_all()
            self.mcp_manager = None

__all__ = ["BUILTIN_TOOLS", "BaseTool", "ToolError", "ToolRegistry", "ToolResult"]
