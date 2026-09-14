"""Generador Fase 8 (MCP) de OvandoCode."""
import pathlib

ROOT = pathlib.Path(r"D:\Trabajo\OvandoCode")
SRC = ROOT / "src" / "ovandocode"
MCP = SRC / "mcp"
SCRIPTS = ROOT / "scripts"


def write(path: pathlib.Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")
    print(f"[OK] {path}")


# ============================================================
# 1. mcp/config.py
# ============================================================
write(MCP / "config.py", '''"""Configuracion de servidores MCP."""
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
    def from_dict(cls, name: str, d: dict) -> "MCPServerConfig":
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
''')


# ============================================================
# 2. mcp/client.py
# ============================================================
write(MCP / "client.py", '''"""Cliente MCP: una conexion a un servidor."""
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
        return "\\n".join(parts) if parts else "(sin contenido)"

    async def stop(self) -> None:
        if self._stack is not None:
            try:
                await self._stack.aclose()
            except Exception:
                pass
        self._stack = None
        self._session = None
        self._tools = []
''')


# ============================================================
# 3. mcp/manager.py
# ============================================================
write(MCP / "manager.py", '''"""Gestor de multiples servidores MCP."""
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
        except (asyncio.TimeoutError, MCPClientError, Exception) as e:
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
''')


# ============================================================
# 4. mcp/__init__.py
# ============================================================
write(MCP / "__init__.py", '''"""Soporte MCP (Model Context Protocol) de OVANDOCODE."""
from ovandocode.mcp.client import MCPClient, MCPClientError
from ovandocode.mcp.config import (
    MCPServerConfig,
    default_config_path,
    load_mcp_config,
    save_mcp_config,
)
from ovandocode.mcp.manager import MCPManager

__all__ = [
    "MCPClient",
    "MCPClientError",
    "MCPManager",
    "MCPServerConfig",
    "default_config_path",
    "load_mcp_config",
    "save_mcp_config",
]
''')


# ============================================================
# 5. tools/mcp_tool.py
# ============================================================
write(SRC / "tools" / "mcp_tool.py", '''"""Wrapper que expone una tool MCP como tool del agente."""
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
''')


# ============================================================
# 6. Parchear tools/registry.py
# ============================================================
reg_path = SRC / "tools" / "registry.py"
txt = reg_path.read_text(encoding="utf-8")

if "async_setup_mcp" not in txt:
    # Añadir import de MCPTool y MCPManager + atributo mcp_manager + metodo
    txt = txt.replace(
        "from ovandocode.tools.list_dir import ListDirTool",
        "from ovandocode.tools.list_dir import ListDirTool\n"
        "from ovandocode.tools.mcp_tool import MCPTool",
    )
    # Añadir atributo en __init__
    txt = txt.replace(
        "        self.policy = policy or PermissionPolicy()",
        "        self.policy = policy or PermissionPolicy()\n"
        "        self.mcp_manager = None  # se asigna en async_setup_mcp",
    )
    # Añadir metodo async_setup_mcp antes del __all__
    method = '''

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
'''
    txt = txt.replace(
        '\n__all__ = ["BaseTool", "ToolError", "ToolRegistry", "ToolResult", "BUILTIN_TOOLS"]',
        method + '\n__all__ = ["BaseTool", "ToolError", "ToolRegistry", "ToolResult", "BUILTIN_TOOLS"]',
    )
    reg_path.write_text(txt, encoding="utf-8", newline="\n")
    print(f"[OK] {reg_path} (modificado)")
else:
    print(f"[skip] {reg_path} ya tiene async_setup_mcp")


# ============================================================
# 7. Parchear core/agent.py
# ============================================================
agent_path = SRC / "core" / "agent.py"
txt = agent_path.read_text(encoding="utf-8")

if "async_setup_mcp" not in txt:
    # __aenter__: iniciar MCP
    txt = txt.replace(
        '''    async def __aenter__(self) -> "Agent":
        self._provider = create_provider(self.config.provider)
        return self''',
        '''    async def __aenter__(self) -> "Agent":
        self._provider = create_provider(self.config.provider)
        await self.tools.async_setup_mcp()
        return self''',
    )
    # __aexit__: apagar MCP
    txt = txt.replace(
        '''    async def __aexit__(self, *exc: object) -> None:
        if self._provider:
            await self._provider.close()''',
        '''    async def __aexit__(self, *exc: object) -> None:
        await self.tools.async_teardown_mcp()
        if self._provider:
            await self._provider.close()''',
    )
    agent_path.write_text(txt, encoding="utf-8", newline="\n")
    print(f"[OK] {agent_path} (modificado)")
else:
    print(f"[skip] {agent_path} ya tiene async_setup_mcp")


# ============================================================
# 8. scripts/mcp_hello_server.py (servidor MCP de ejemplo)
# ============================================================
write(SCRIPTS / "mcp_hello_server.py", '''"""Servidor MCP de ejemplo para OvandoCode.

Expone 3 tools triviales para probar el cliente MCP:
  - sumar(a, b): suma dos enteros
  - saludar(nombre): devuelve un saludo
  - hora_actual(): devuelve la fecha/hora ISO actual
"""
from datetime import datetime

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("hello")


@mcp.tool()
def sumar(a: int, b: int) -> int:
    """Suma dos numeros enteros y devuelve el resultado."""
    return a + b


@mcp.tool()
def saludar(nombre: str) -> str:
    """Devuelve un saludo personalizado."""
    return f"Hola, {nombre}! Bienvenido a OvandoCode MCP."


@mcp.tool()
def hora_actual() -> str:
    """Devuelve la fecha y hora actual en formato ISO 8601."""
    return datetime.now().isoformat(timespec="seconds")


if __name__ == "__main__":
    mcp.run()
''')


# ============================================================
# 9. mcp.json (config con el servidor de ejemplo)
# ============================================================
mcp_json = ROOT / "mcp.json"
if not mcp_json.exists():
    write(mcp_json, '''{
  "mcpServers": {
    "hello": {
      "transport": "stdio",
      "command": "uv",
      "args": ["run", "python", "scripts/mcp_hello_server.py"],
      "description": "Servidor MCP de ejemplo con sumar, saludar, hora_actual"
    }
  }
}
''')
else:
    print(f"[skip] {mcp_json} ya existe")


# ============================================================
# 10. Parchear cli.py (sub-app mcp)
# ============================================================
cli_path = SRC / "cli.py"
txt = cli_path.read_text(encoding="utf-8")

if "mcp_app" not in txt:
    block = '''

mcp_app = typer.Typer(help="Servidores MCP.")
app.add_typer(mcp_app, name="mcp")


@mcp_app.command("list")
def mcp_list() -> None:
    """Lista servidores MCP configurados."""
    from ovandocode.config import project_root
    from ovandocode.mcp.config import default_config_path, load_mcp_config

    path = default_config_path(project_root())
    if not path.exists():
        typer.echo(f"(no existe {path})")
        typer.echo("Crea uno con: ovandocode mcp init")
        return
    try:
        configs = load_mcp_config(path)
    except Exception as e:
        typer.secho(f"[ERR] {e}", fg="red")
        raise typer.Exit(1)
    if not configs:
        typer.echo("(sin servidores MCP habilitados)")
        return
    typer.echo(f"== {len(configs)} servidor(es) MCP ==")
    for c in configs:
        typer.echo(f"  * {c.name:<15} [{c.transport}]")
        if c.transport == "stdio":
            typer.echo(f"      {c.command} {' '.join(c.args)}")
        else:
            typer.echo(f"      {c.url}")
        if c.description:
            typer.echo(f"      {c.description}")


@mcp_app.command("init")
def mcp_init() -> None:
    """Crea un mcp.json vacio con un servidor de ejemplo."""
    from ovandocode.config import project_root
    from ovandocode.mcp.config import default_config_path

    path = default_config_path(project_root())
    if path.exists():
        typer.secho(f"[ERR] ya existe: {path}", fg="red")
        raise typer.Exit(1)
    content = (
        "{\\n"
        '  "mcpServers": {\\n'
        '    "hello": {\\n'
        '      "transport": "stdio",\\n'
        '      "command": "uv",\\n'
        '      "args": ["run", "python", "scripts/mcp_hello_server.py"],\\n'
        '      "description": "Servidor MCP de ejemplo"\\n'
        "    }\\n"
        "  }\\n"
        "}\\n"
    )
    path.write_text(content, encoding="utf-8")
    typer.secho(f"[OK] creado: {path}", fg="green")


@mcp_app.command("test")
def mcp_test(
    name: str = typer.Argument(None, help="Nombre del servidor (opcional, prueba todos)."),
) -> None:
    """Inicia los servidores MCP y lista sus tools."""
    import asyncio
    from ovandocode.config import project_root
    from ovandocode.mcp.config import default_config_path, load_mcp_config
    from ovandocode.mcp.manager import MCPManager

    path = default_config_path(project_root())
    configs = load_mcp_config(path)
    if name:
        configs = [c for c in configs if c.name == name]
    if not configs:
        typer.secho("[ERR] sin servidores MCP que probar", fg="red")
        raise typer.Exit(1)

    async def _go() -> None:
        mgr = MCPManager(configs)
        await mgr.start_all()
        try:
            if mgr.errors:
                for srv, err in mgr.errors.items():
                    typer.secho(f"[ERR] {srv}: {err}", fg="red")
            for srv, client in mgr.clients.items():
                typer.secho(f"== {srv} ({len(client.tools)} tools) ==", fg="cyan")
                for t in client.tools:
                    typer.echo(f"  * {t.name}: {getattr(t, 'description', '')[:70]}")
        finally:
            await mgr.stop_all()

    asyncio.run(_go())


def main() -> None:
'''
    txt = txt.replace("\n\ndef main() -> None:", block)
    cli_path.write_text(txt, encoding="utf-8", newline="\n")
    print(f"[OK] {cli_path} (modificado)")
else:
    print(f"[skip] {cli_path} ya tiene mcp_app")


print("")
print("=== Fase 8 generada ===")