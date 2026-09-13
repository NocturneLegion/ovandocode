# OVANDOCODE

Agente de codificacion autonomo para terminal.
TUI moderna, multi-proveedor LLM, MCP, skills y ejecucion segura de shell.

## Requisitos

- Python 3.11+
- Windows 10/11 (compatible con Linux/macOS)

## Instalacion (dev)

    uv sync --extra dev
    uv run ovandocode --help

## Uso

    ovandocode                    # TUI interactiva
    ovandocode "refactoriza ..."  # one-shot
    ovandocode --headless "..."   # headless

## Licencia

MIT