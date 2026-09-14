"""Cliente MCP: una conexion a un servidor."""
from __future__ import annotations

import os
from contextlib import AsyncExitStack
from typing import Any

from ovandocode.mcp.config import MCPServerConfig


class MCPClientError(Exception):
    """Error al comunicarse con un servidor MCP."""


class MCPClient:
    """Cliente para UN servidor MCP (stdio o SSE)."""

    def __init__(self, config: MCPServerConfig) -> None:
        self.config = config
        self._stack: AsyncExitStack | None = None
        self._session: Any = None
        self._tools: list[Any] = []

    @property
    def name(self) -> str:
        return self.config.name

    @property
    def tools(self) -> list[Any]:
        return list(self._tools)

    @property
    def is_running(self) -> bool:
        return self._session is not None

    async def start(self) -> None:
        """Inicia el subproceso/servidor y abre una sesion MCP."""
        try:
            from mcp import ClientSession, StdioServerParameters
        except ImportError as e:
            raise MCPClientError(f"SDK 'mcp' no disponible: {e}") from None

        self._stack = AsyncExitStack()
        try:
            if self.config.transport == "stdio":
                from mcp.client.stdio import stdio_client

                env = {**os.environ, **self.config.env} if self.config.env else None
                params = StdioServerParameters(
                    command=self.config.command,
                    args=self.config.args,
                    env=env,
                )
                read, write = await self._stack.enter_async_context(stdio_client(params))
            elif self.config.transport in ("sse", "http"):
                from mcp.client.sse import sse_client

                read, write = await self._stack.enter_async_context(
                    sse_client(self.config.url)
                )
            else:
                raise MCPClientError(f"Transport no soportado: {self.config.transport}")

            self._session = await self._stack.enter_async_context(
                ClientSession(read, write)
            )
            await self._session.initialize()
            result = await self._session.list_tools()
            self._tools = list(getattr(result, "tools", []) or [])
        except Exception as e:
            await self.stop()
            raise MCPClientError(f"{self.name}: {e}") from e

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> str:
        """Llama a una tool del servidor y devuelve su salida como texto."""
        if self._session is None:
            raise MCPClientError(f"{self.name}: no esta iniciado")

        try:
            result = await self._session.call_tool(tool_name, arguments)
        except Exception as e:
            raise MCPClientError(f"{self.name}.{tool_name}: {e}") from e

        parts: list[str] = []
        for c in getattr(result, "content", []) or []:
            text = getattr(c, "text", None)
            if text is not None:
                parts.append(str(text))
            else:
                parts.append(f"[{type(c).__name__}]")
        return "\n".join(parts) if parts else "(sin contenido)"

    async def stop(self) -> None:
        if self._stack is not None:
            try:
                await self._stack.aclose()
            except Exception:
                pass
        self._stack = None
        self._session = None
        self._tools = []
