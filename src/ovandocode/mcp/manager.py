"""Gestor de multiples servidores MCP."""
from __future__ import annotations

import asyncio
from typing import Any

from ovandocode.mcp.client import MCPClient, MCPClientError
from ovandocode.mcp.config import MCPServerConfig


class MCPManager:
    """Administra el ciclo de vida de N servidores MCP."""

    def __init__(self, configs: list[MCPServerConfig], start_timeout: float = 20.0) -> None:
        self.configs = configs
        self.start_timeout = start_timeout
        self._clients: dict[str, MCPClient] = {}
        self._errors: dict[str, str] = {}

    @property
    def clients(self) -> dict[str, MCPClient]:
        return self._clients

    @property
    def errors(self) -> dict[str, str]:
        return self._errors

    @property
    def running_count(self) -> int:
        return len(self._clients)

    async def _start_one(self, cfg: MCPServerConfig) -> None:
        client = MCPClient(cfg)
        try:
            await asyncio.wait_for(client.start(), timeout=self.start_timeout)
            self._clients[cfg.name] = client
        except (TimeoutError, MCPClientError, Exception) as e:
            self._errors[cfg.name] = str(e)
            await client.stop()

    async def start_all(self) -> None:
        """Inicia todos los servidores en paralelo (fallas no bloquean)."""
        if not self.configs:
            return
        await asyncio.gather(
            *(self._start_one(c) for c in self.configs),
            return_exceptions=True,
        )

    async def stop_all(self) -> None:
        await asyncio.gather(
            *(c.stop() for c in list(self._clients.values())),
            return_exceptions=True,
        )
        self._clients.clear()

    def all_tools(self) -> list[tuple[str, Any]]:
        """Devuelve [(server_name, tool_def), ...]."""
        out: list[tuple[str, Any]] = []
        for name, client in self._clients.items():
            for t in client.tools:
                out.append((name, t))
        return out

    def tool_count(self) -> int:
        return sum(len(c.tools) for c in self._clients.values())

    async def call(self, server_name: str, tool_name: str, args: dict[str, Any]) -> str:
        if server_name not in self._clients:
            raise MCPClientError(f"Servidor MCP no activo: {server_name}")
        return await self._clients[server_name].call_tool(tool_name, args)
