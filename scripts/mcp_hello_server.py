"""Servidor MCP de ejemplo para OvandoCode (SDK v2).

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
