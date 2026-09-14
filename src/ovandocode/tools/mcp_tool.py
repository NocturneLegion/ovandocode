"""Wrapper que expone una tool MCP como tool del agente."""
from __future__ import annotations

from typing import Any

from ovandocode.mcp.manager import MCPManager
from ovandocode.tools.base import BaseTool, ToolResult


def _mcp_tool_name(server: str, tool: str) -> str:
    """Nombre seguro para el LLM (evita colisiones)."""
    return f"mcp__{server}__{tool}"


class MCPTool(BaseTool):
    """Envuelve una tool MCP descubierta en runtime."""

    def __init__(
        self,
        manager: MCPManager,
        server_name: str,
        mcp_tool_name: str,
        description: str,
        schema: dict[str, Any],
    ) -> None:
        super().__init__()
        self._manager = manager
        self._server = server_name
        self._mcp_tool = mcp_tool_name
        self.name = _mcp_tool_name(server_name, mcp_tool_name)
        self.description = f"[MCP:{server_name}] {description or 'Sin descripcion.'}"
        self.parameters = schema or {"type": "object", "properties": {}}

    async def run(self, **kwargs: Any) -> ToolResult:
        try:
            content = await self._manager.call(self._server, self._mcp_tool, kwargs)
        except Exception as e:
            return ToolResult(
                ok=False,
                content=f"[MCP ERROR] {type(e).__name__}: {e}",
            )
        return ToolResult(
            ok=True,
            content=content,
            meta={"server": self._server, "tool": self._mcp_tool},
        )
