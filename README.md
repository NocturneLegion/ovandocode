# OVANDOCODE

> Agente de codificacion autonomo para terminal. TUI moderna, multi-proveedor LLM, MCP, skills y ejecucion segura de shell.

## Que es OVANDOCODE

Un agente que vive en tu terminal y puede:

- **Leer, escribir y editar** archivos de tu proyecto.
- **Ejecutar comandos** en PowerShell, bash y Python (con politica de permisos).
- **Buscar** con glob y grep, respetando .gitignore.
- **Cargar skills** especializadas (testing, code review, commits, las que quieras).
- **Conectar a servidores MCP** para herramientas externas.
- **Usar cualquier LLM** (OpenRouter, OpenAI, Anthropic, Gemini, Groq, DeepSeek, Mistral, xAI, Ollama, LM Studio).

## Instalacion

### Requisitos

- Python 3.11+
- Windows 10/11, Linux o macOS
- PowerShell 7+ (recomendado en Windows)

### Opcion A - Instalar como tool global

```powershell
uv tool install --editable .
```

Esto instala `ovandocode` como comando global en `%USERPROFILE%\.local\bin`.

### Opcion B - Solo para probar (sin instalar)

```powershell
uv sync --extra dev
uv run ovandocode
```

## Uso

```powershell
# TUI interactiva
ovandocode

# Tarea one-shot
ovandocode run "refactoriza src/foo.py"

# Headless (para pipelines)
ovandocode headless "explica este repo" --json

# Historial de sesiones
ovandocode history

# Reanudar una sesion en la TUI
ovandocode sessions resume <ID>
```

## Configuracion

### API keys

```powershell
# Guardar en Windows Credential Manager (recomendado)
ovandocode config set-key openrouter

# Ver estado de todos los proveedores
ovandocode config providers
```

O edita `.env` en la raiz del proyecto:

```env
OPENROUTER_API_KEY=sk-or-v1-...
OVANDOCODE_DEFAULT_PROVIDER=openrouter
OVANDOCODE_DEFAULT_MODEL=openrouter/free
OVANDOCODE_MAX_TOKENS=4096
```

### Proveedores soportados

| Proveedor | Variable | URL |
|---|---|---|
| OpenRouter | `OPENROUTER_API_KEY` | https://openrouter.ai/keys |
| OpenAI | `OPENAI_API_KEY` | https://platform.openai.com/api-keys |
| Anthropic | `ANTHROPIC_API_KEY` | https://console.anthropic.com/ |
| Gemini | `GEMINI_API_KEY` | https://aistudio.google.com/apikey |
| Groq | `GROQ_API_KEY` | https://console.groq.com/keys |
| DeepSeek | `DEEPSEEK_API_KEY` | https://platform.deepseek.com/ |
| Mistral | `MISTRAL_API_KEY` | https://console.mistral.ai/ |
| xAI (Grok) | `XAI_API_KEY` | https://console.x.ai/ |
| Ollama | (local) | http://localhost:11434 |
| LM Studio | (local) | http://localhost:1234/v1 |

## Skills

Las skills son archivos `SKILL.md` con frontmatter YAML:

```markdown
---
name: mi-skill
description: Que hace esta skill
when_to_use: Cuando el usuario pida X
tags: [python, testing]
version: 1.0.0
---

# Instrucciones detalladas
...
```

Se descubren automaticamente desde:
1. `src/ovandocode/skills/builtin/` (incluidas)
2. `~/.ovandocode/skills/` (usuario)
3. `<proyecto>/skills/` (proyecto, prioridad mas alta)

```powershell
ovandocode skills list
ovandocode skills show python-testing
ovandocode skills init mi-skill-nueva
```

## MCP

Edita `mcp.json` en la raiz del proyecto:

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

```powershell
ovandocode mcp list
ovandocode mcp test
```

## Permisos

Modos configurables con `OVANDOCODE_PERMISSION_MODE`:

- `ask` - pregunta siempre antes de ejecutar shells
- `allowlist` - auto-aprueba comandos seguros, pregunta el resto (**default**)
- `yolo` - auto-aprueba todo excepto patrones peligrosos

```powershell
ovandocode perm check "Get-ChildItem ."
ovandocode perm check "rm -rf /"
```

## Desarrollo

```powershell
uv sync --extra dev

# Tests
uv run pytest -v
uv run pytest --cov=src/ovandocode --cov-report=term-missing

# Lint
uv run ruff check src tests
uv run ruff check src tests --fix
```

## Estructura

```
src/ovandocode/
  cli.py              # entrypoint Typer
  config/             # settings, rutas, credenciales
  providers/          # LLM providers (OpenAI-compat + nativos)
  core/               # agente, mensajes, sesiones, contexto, prompts
  tools/              # read/write/edit/list/glob/grep/shell/mcp/load_skill
  skills/             # loader SKILL.md + builtin
  mcp/                # cliente MCP
  permissions/        # politica de aprobacion
  tui/                # Textual App
```

## Licencia

MIT - ver [LICENSE](LICENSE).
