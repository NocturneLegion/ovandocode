# MCP (Model Context Protocol)

OVANDOCODE puede conectarse a **servidores MCP** para obtener herramientas adicionales en runtime. Es el estándar abierto de Anthropic para exponer capacidades a agentes LLM.

---

## ¿Qué es MCP?

MCP define un protocolo JSON-RPC entre un **cliente** (OVANDOCODE) y un **servidor** (cualquier programa que exponga tools).

Ventajas:

- **Desacoplamiento**: escribes un servidor MCP una vez y funciona con cualquier cliente compatible.
- **Multi-lenguaje**: hay SDKs en Python, TypeScript, Go, Rust.
- **Composabilidad**: conectas varios servidores a la vez.

---

## Cómo funciona en OVANDOCODE

1. Al arrancar el agente, se lee `mcp.json` en la raíz del proyecto.
2. Se inicia cada servidor en paralelo (subproceso o HTTP).
3. Se listan sus tools y se registran con el prefijo `mcp__<servidor>__<tool>`.
4. El LLM puede invocarlas como cualquier otra tool.
5. Al cerrar el agente, se detienen los servidores.

---

## Archivo `mcp.json`

Ubicación: **raíz del proyecto** (`D:\Trabajo\OvandoCode\mcp.json`).

### Formato

```json
{
  "mcpServers": {
    "nombre-servidor": {
      "transport": "stdio",
      "command": "comando",
      "args": ["arg1", "arg2"],
      "env": { "VAR": "valor" },
      "description": "Texto opcional"
    }
  }
}
```

### Campos

| Campo | Tipo | Aplica a | Descripción |
|---|---|---|---|
| `transport` | `stdio` / `sse` / `http` | siempre | Cómo conectarse al servidor |
| `command` | string | stdio | Ejecutable a lanzar |
| `args` | array | stdio | Argumentos del comando |
| `env` | objeto | stdio | Variables de entorno adicionales |
| `url` | string | sse / http | URL del servidor HTTP |
| `enabled` | bool | siempre | `false` para desactivar sin borrar |
| `description` | string | siempre | Solo informativo |

---

## Servidores incluidos (ejemplo)

OVANDOCODE trae un servidor MCP de ejemplo escrito en Python:

`scripts/mcp_hello_server.py`

Expone 3 tools:

- `sumar(a, b)` — suma dos enteros
- `saludar(nombre)` — devuelve un saludo personalizado
- `hora_actual()` — devuelve la fecha ISO actual

### Configuración por defecto (mcp.json)

```json
{
  "mcpServers": {
    "hello": {
      "transport": "stdio",
      "command": ".venv\\Scripts\\python.exe",
      "args": ["scripts/mcp_hello_server.py"],
      "description": "Servidor MCP de ejemplo"
    }
  }
}
```

---

## Comandos CLI

### Listar servidores configurados

```powershell
ovandocode mcp list
```

Salida:

```
== 1 servidor(es) MCP ==
  * hello           [stdio]
      .venv\Scripts\python.exe scripts/mcp_hello_server.py
      Servidor MCP de ejemplo
```

### Crear `mcp.json` de ejemplo

```powershell
ovandocode mcp init
```

### Probar los servidores

```powershell
ovandocode mcp test
```

Salida:

```
== hello (3 tools) ==
  * sumar: Suma dos numeros enteros y devuelve el resultado.
  * saludar: Devuelve un saludo personalizado.
  * hora_actual: Devuelve la fecha y hora actual en formato ISO 8601.
```

### Ver las tools MCP en el catálogo del agente

```powershell
ovandocode tools list
```

Deben aparecer las 10 built-in + 3 MCP = 13 total:

```
  * mcp__hello__hora_actual
  * mcp__hello__saludar
  * mcp__hello__sumar
  * ... (10 built-in)
```

---

## Uso desde el agente

```powershell
ovandocode run "Usa la herramienta MCP para sumar 17 y 25"
```

El agente verá las tools `mcp__*` en su catálogo y las usará igual que las built-in:

```
>> mcp__hello__sumar {'a': 17, 'b': 25}
<< mcp__hello__sumar [ok]
42
El resultado de sumar 17 y 25 es 42.
```

---

## Servidores MCP populares

### Filesystem (Node.js)

Acceso controlado al sistema de archivos.

```json
{
  "mcpServers": {
    "filesystem": {
      "transport": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "."]
    }
  }
}
```

### GitHub (Node.js)

Gestiona issues, PRs, repos.

```json
{
  "mcpServers": {
    "github": {
      "transport": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_..."
      }
    }
  }
}
```

### SQLite (Python)

```json
{
  "mcpServers": {
    "sqlite": {
      "transport": "stdio",
      "command": "uvx",
      "args": ["mcp-server-sqlite", "--db-path", "./data.db"]
    }
  }
}
```

### SSE (servidor HTTP remoto)

```json
{
  "mcpServers": {
    "mi-api": {
      "transport": "sse",
      "url": "http://localhost:8000/sse"
    }
  }
}
```

---

## Escribir tu propio servidor MCP (Python)

### 1. Instala el SDK

```powershell
uv add mcp
```

### 2. Crea el servidor

`scripts/mi_servidor.py`:

```python
from mcp.server import MCPServer

mcp = MCPServer("mi-servidor")

@mcp.tool()
def mi_tool(param1: str, param2: int) -> str:
    """Descripcion que ve el LLM."""
    return f"Resultado: {param1} {param2}"

if __name__ == "__main__":
    mcp.run()
```

### 3. Regístralo en `mcp.json`

```json
{
  "mcpServers": {
    "mio": {
      "transport": "stdio",
      "command": ".venv\\Scripts\\python.exe",
      "args": ["scripts/mi_servidor.py"]
    }
  }
}
```

### 4. Prueba

```powershell
ovandocode mcp test mio
```

---

## Troubleshooting

### "Connection closed" al arrancar

**Causas comunes**:

1. El ejecutable no existe (revisa `command`).
2. El script del servidor tiene un error de import (pruébalo standalone).
3. Usaste `uv run` en el `command` y hay uv anidado — usa `.venv\Scripts\python.exe` directo.

### El servidor arranca pero no aparecen sus tools

**Causa**: el servidor no está registrando tools con `@mcp.tool()`.

**Solución**: ejecuta el servidor standalone y verifica que no haya errores:

```powershell
.venv\Scripts\python.exe scripts/mi_servidor.py
```

### El agente no usa las tools MCP

**Causa**: el LLM no reconoce que debe usarlas, o el modelo no soporta tool calling.

**Solución**: sé explícito en el prompt: `"Usa la herramienta mcp__hello__sumar para..."`.

### Diferencia entre `mcp list` y `tools list`

- `mcp list` lee `mcp.json` (configuración estática).
- `tools list` arranca los servidores y lista las tools reales (runtime).

---

## Notas técnicas

- SDK usado: `mcp>=1.0.0` (paquete oficial de Anthropic).
- Transport soportados: `stdio`, `sse`, `http`.
- Timeout de arranque: 20 segundos por servidor.
- Si un servidor falla, **los otros siguen funcionando** (fallo aislado).

---

## Siguiente paso

- [Interfaz](interfaz.html) — TUI y CLI
- [Sesiones](sesiones.html) — historial y reanudar
- [Solución de problemas](troubleshooting.html)

---

[← Volver al inicio](index.html)
