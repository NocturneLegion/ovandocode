"""Fix: migrar servidor MCP de FastMCP (v1) a MCPServer (v2)."""
import pathlib

path = pathlib.Path(r"D:\Trabajo\OvandoCode\scripts\mcp_hello_server.py")
path.write_text('''"""Servidor MCP de ejemplo para OvandoCode (SDK v2).

Expone 3 tools triviales para probar el cliente MCP:
  - sumar(a, b): suma dos enteros
  - saludar(nombre): devuelve un saludo
  - hora_actual(): devuelve la fecha/hora ISO actual
"""
from datetime import datetime

from mcp.server import MCPServer

mcp = MCPServer("hello")


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
''', encoding="utf-8", newline="\n")
print("[OK] mcp_hello_server.py migrado a SDK v2")

# Tambien corregir mcp.json (usar .venv directo para evitar uv anidado)
mcp_json = pathlib.Path(r"D:\Trabajo\OvandoCode\mcp.json")
mcp_json.write_text('''{
  "mcpServers": {
    "hello": {
      "transport": "stdio",
      "command": ".venv\\\\Scripts\\\\python.exe",
      "args": ["scripts/mcp_hello_server.py"],
      "description": "Servidor MCP de ejemplo con sumar, saludar, hora_actual"
    }
  }
}
''', encoding="utf-8", newline="\n")
print("[OK] mcp.json actualizado (.venv directo)")