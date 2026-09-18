---
layout: default
title: OVANDOCODE
---

# OVANDOCODE

> Agente de codificacion autonomo para terminal. TUI moderna, multi-proveedor LLM, MCP, skills y ejecucion segura de shell.

## Instalacion rapida

```powershell
uv tool install git+https://github.com/NocturneLegion/ovandocode.git
ovandocode --version
```

## Documentacion

| Seccion | Descripcion |
|---|---|
| [Instalacion](instalacion.html) | Requisitos, uv, primer arranque |
| [Configuracion](configuracion.html) | .env, config.toml, keyring |
| [Proveedores](proveedores.html) | 10 proveedores LLM soportados |
| [Permisos](permisos.html) | Control de ejecucion de comandos |
| [Herramientas](herramientas.html) | Las 10 tools built-in |
| [Skills](skills.html) | Crear skills personalizadas |
| [MCP](mcp.html) | Servidores MCP externos |
| [Interfaz](interfaz.html) | TUI y CLI |
| [Sesiones](sesiones.html) | Historial y reanudar |
| [Troubleshooting](troubleshooting.html) | Errores comunes |

O ve a la [guia completa](GUIA.html).

## Features

- **10 proveedores LLM**: OpenRouter, OpenAI, Anthropic, Gemini, Groq, DeepSeek, Mistral, xAI, Ollama, LM Studio
- **10 herramientas built-in**: filesystem, shell, web
- **Sistema de skills**: instrucciones especializadas por dominio
- **MCP**: conexion a servidores externos
- **TUI interactiva**: config desde la interfaz, copiar/pegar, redibujar historial
- **Sesiones persistentes**: reanudar conversaciones
- **Configuracion global**: config.toml en AppData

## Repositorio

- **GitHub**: https://github.com/NocturneLegion/ovandocode
- **Releases**: https://github.com/NocturneLegion/ovandocode/releases
- **Issues**: https://github.com/NocturneLegion/ovandocode/issues

## Licencia

MIT
