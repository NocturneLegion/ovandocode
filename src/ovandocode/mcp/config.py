"""Configuracion de servidores MCP."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

Transport = Literal["stdio", "sse", "http"]

DEFAULT_CONFIG_NAME = "mcp.json"


@dataclass
class MCPServerConfig:
    """Configuracion de un servidor MCP."""
    name: str
    transport: Transport = "stdio"
    command: str = ""
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    url: str = ""
    enabled: bool = True
    description: str = ""

    @classmethod
    def from_dict(cls, name: str, d: dict) -> MCPServerConfig:
        return cls(
            name=name,
            transport=d.get("transport", "stdio"),
            command=d.get("command", ""),
            args=list(d.get("args", [])),
            env=dict(d.get("env", {})),
            url=d.get("url", ""),
            enabled=bool(d.get("enabled", True)),
            description=d.get("description", ""),
        )

    def validate(self) -> None:
        if self.transport == "stdio" and not self.command:
            raise ValueError(f"{self.name}: falta 'command' para transport stdio")
        if self.transport in ("sse", "http") and not self.url:
            raise ValueError(f"{self.name}: falta 'url' para transport {self.transport}")


def default_config_path(project_root: Path) -> Path:
    return project_root / DEFAULT_CONFIG_NAME


def load_mcp_config(path: Path) -> list[MCPServerConfig]:
    """Carga servidores MCP desde un archivo JSON.

    Formato:
        {
          "mcpServers": {
            "nombre": {
              "transport": "stdio",
              "command": "npx",
              "args": ["-y", "@modelcontextprotocol/server-everything"]
            }
          }
        }
    """
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON invalido en {path}: {e}") from None

    servers = data.get("mcpServers", {})
    if not isinstance(servers, dict):
        return []

    out: list[MCPServerConfig] = []
    for name, cfg in servers.items():
        if not isinstance(cfg, dict):
            continue
        try:
            c = MCPServerConfig.from_dict(name, cfg)
            c.validate()
            if c.enabled:
                out.append(c)
        except ValueError:
            continue
    return out


def save_mcp_config(path: Path, configs: list[MCPServerConfig]) -> None:
    """Guarda una lista de servidores MCP en el archivo JSON."""
    servers: dict = {}
    for c in configs:
        entry: dict = {"transport": c.transport, "enabled": c.enabled}
        if c.description:
            entry["description"] = c.description
        if c.transport == "stdio":
            entry["command"] = c.command
            if c.args:
                entry["args"] = c.args
            if c.env:
                entry["env"] = c.env
        else:
            entry["url"] = c.url
        servers[c.name] = entry
    data = {"mcpServers": servers}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
