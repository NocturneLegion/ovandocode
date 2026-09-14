# Guía completa de OVANDOCODE

Bienvenido a la documentación de OVANDOCODE. Esta guía cubre todo lo que necesitas para instalar, configurar y usar el agente.

---

## Índice

### Primeros pasos

1. **[Instalación](instalacion.md)** — requisitos, `uv`, instalación global, primer arranque.
2. **[Configuración](configuracion.md)** — `.env`, `config.toml`, keyring, todas las variables.
3. **[Proveedores LLM](proveedores.md)** — los 10 proveedores soportados (Groq, OpenRouter, OpenAI, Anthropic, Gemini, DeepSeek, Mistral, xAI, Ollama, LM Studio).

### Uso

4. **[Interfaz](interfaz.md)** — TUI interactiva + CLI (modo one-shot y headless).
5. **[Herramientas](herramientas.md)** — las 10 tools built-in del agente.
6. **[Sesiones](sesiones.md)** — historial persistente, reanudar, auto-compactación.

### Extender el agente

7. **[Skills](skills.md)** — crear skills personalizadas con `SKILL.md`.
8. **[MCP](mcp.md)** — conectar servidores MCP externos.

### Control y seguridad

9. **[Permisos](permisos.md)** — modos de ejecución de comandos (allowlist, yolo, ask).
10. **[Solución de problemas](troubleshooting.md)** — errores comunes y cómo resolverlos.

---

## Recorrido rápido (5 minutos)

### 1. Instalar

```powershell
uv tool install --editable .
ovandocode --version
```

### 2. Configurar un proveedor

Consigue una API key gratis de [Groq](https://console.groq.com/keys) y:

```powershell
notepad .env
```

Pega:

```env
GROQ_API_KEY=gsk_tu_key
OVANDOCODE_DEFAULT_PROVIDER=groq
OVANDOCODE_DEFAULT_MODEL=openai/gpt-oss-120b
OVANDOCODE_MAX_TOKENS=4096
```

### 3. Usar

```powershell
# TUI interactiva
ovandocode

# O una tarea puntual
ovandocode run "explica la estructura de este proyecto"
```

---

## Casos de uso comunes

### Analizar un proyecto nuevo

```powershell
cd C:\ruta\al\proyecto
ovandocode run "Explica la estructura de este proyecto y dime por donde empezar"
```

### Refactorizar código

```powershell
ovandocode run "Refactoriza src/utils.py extrayendo la logica de parseo a su propia funcion"
```

### Escribir tests

```powershell
ovandocode run "Escribe tests para todas las funciones publicas de src/core/agent.py"
```

El agente cargará automáticamente la skill `python-testing`.

### Hacer un commit

```powershell
ovandocode run "Revisa los cambios y hazme un commit siguiendo Conventional Commits"
```

El agente cargará la skill `commit-message`.

### Code review

```powershell
ovandocode run "Revisa src/ovandocode/tools/shell_base.py y dime que mejoras haria"
```

El agente cargará la skill `code-review`.

### Integrar en CI/CD

```powershell
$review = ovandocode headless "Revisa este diff y senala problemas: $(git diff HEAD~1)" --json
$data = $review | ConvertFrom-Json
if ($data.response -match "critico|error") { exit 1 }
```

---

## ¿Por dónde empiezo?

| Si quieres... | Ve a... |
|---|---|
| Instalarlo | [Instalación](instalacion.md) |
| Configurar una API key | [Configuración](configuracion.md) |
| Saber qué modelo elegir | [Proveedores](proveedores.md) |
| Aprender a usarlo | [Interfaz](interfaz.md) |
| Crear una skill | [Skills](skills.md) |
| Conectar MCP | [MCP](mcp.md) |
| Controlar qué ejecuta | [Permisos](permisos.md) |
| Algo falla | [Troubleshooting](troubleshooting.md) |

---

## Enlaces externos

- **Repo**: https://github.com/TU-USUARIO/ovandocode
- **Issues**: https://github.com/TU-USUARIO/ovandocode/issues
- **uv** (gestor): https://docs.astral.sh/uv/
- **Textual** (TUI): https://textual.textualize.io/
- **MCP** (protocolo): https://modelcontextprotocol.io/

---

## Licencia

MIT — ver [LICENSE](../LICENSE).
