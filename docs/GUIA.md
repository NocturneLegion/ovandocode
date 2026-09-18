# Guía completa de OVANDOCODE

Bienvenido a la documentación de OVANDOCODE. Esta guía cubre todo lo que necesitas para instalar, configurar y usar el agente.

---

## Índice

### Primeros pasos

1. **[Instalación](instalacion.html)** — requisitos, `uv`, instalación global, primer arranque.
2. **[Configuración](configuracion.html)** — `.env`, `config.toml`, keyring, todas las variables.
3. **[Proveedores LLM](proveedores.html)** — los 10 proveedores soportados (Groq, OpenRouter, OpenAI, Anthropic, Gemini, DeepSeek, Mistral, xAI, Ollama, LM Studio).

### Uso

4. **[Interfaz](interfaz.html)** — TUI interactiva + CLI (modo one-shot y headless).
5. **[Herramientas](herramientas.html)** — las 10 tools built-in del agente.
6. **[Sesiones](sesiones.html)** — historial persistente, reanudar, auto-compactación.

### Extender el agente

7. **[Skills](skills.html)** — crear skills personalizadas con `SKILL.md`.
8. **[MCP](mcp.html)** — conectar servidores MCP externos.

### Control y seguridad

9. **[Permisos](permisos.html)** — modos de ejecución de comandos (allowlist, yolo, ask).
10. **[Solución de problemas](troubleshooting.html)** — errores comunes y cómo resolverlos.

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
| Instalarlo | [Instalación](instalacion.html) |
| Configurar una API key | [Configuración](configuracion.html) |
| Saber qué modelo elegir | [Proveedores](proveedores.html) |
| Aprender a usarlo | [Interfaz](interfaz.html) |
| Crear una skill | [Skills](skills.html) |
| Conectar MCP | [MCP](mcp.html) |
| Controlar qué ejecuta | [Permisos](permisos.html) |
| Algo falla | [Troubleshooting](troubleshooting.html) |

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

---

[← Volver al inicio](index.html)
