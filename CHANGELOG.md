# Changelog

Todas las versiones notables de OVANDOCODE.

El formato sigue Keep a Changelog y este proyecto usa Semantic Versioning.

## [0.2.1] - 2026-09-18

Version de mantenimiento. Corrige el bug critico de reanudado de sesiones.

### Corregido

- **`sessions resume` no funciona**: `on_mount` pisaba la sesion precargada
  creando siempre una nueva. Ahora respeta la sesion cargada por el CLI
  y sincroniza el provider/model del agent_config con los de la sesion.
- **Historial no se redibujaba al reanudar**: `_redraw_history` no se
  invocaba porque la sesion quedaba vacia tras pisarla. Ahora se ve todo
  el historial al abrir la TUI.

### Anadido

- **Comando `/history`**: redibuja el historial en el chat bajo demanda.
- **Redibujado automatico**: al reanudar una sesion, el historial previo
  se muestra al arrancar la TUI.

## [0.2.0] - 2026-09-14

Segunda version. Foco en la experiencia de usuario en la TUI, gestion de credenciales
desde la interfaz, y mejoras de seleccion de modelos.

### Anadido

- **Gestion de API keys desde la TUI**: `/provider` unifica la eleccion de proveedor
  con el estado de cada API key (verde/rojo/gris) y permite configurarlas sin salir.
- **Validacion real de API keys**: antes de guardar, se hace ping al proveedor para
  verificar que la key funciona (evita keys invalidas silenciosas).
- **Persistencia global** (`config.toml`): los cambios de proveedor/modelo se pueden
  guardar para futuros proyectos con confirmacion interactiva.
- **Selector de modelos con scroll completo**: navegacion por teclado (flechas,
  PageUp/PageDown, Home/End), contador de posicion, filtro en vivo.
- **Copy/paste en la TUI**: `Ctrl+Shift+C` copia el chat completo al portapapeles
  (texto plano sin codigos de color) y `Ctrl+Shift+V` pega en el input.
- **Ruta del proyecto visible** en el banner, la barra de estado y el titulo
  de la ventana (para saber donde esta trabajando el agente).
- **Listado de modelos por proveedor**: `ovandocode providers models <provider>`
  con cache en disco de 24h.

### Cambiado

- **`/credentials` y `/credentials config` eliminados** en favor de un `/provider`
  unificado que hace ambas cosas.
- **`/model` y `/provider`** ahora abren pickers interactivos (no solo texto).
- El provider picker muestra el estado de las credenciales de cada proveedor
  con colores (verde = configurado, rojo = falta, gris = local sin key).

### Corregido

- `CredentialsScreen` usaba `value=""` en el `Select` (rompia con `allow_blank=False`).
- `on_click` en `CredentialsListScreen` usaba `event.static` (inexistente) en vez
  de `event.widget`.
- `_write_log` se llamaba a si mismo recursivamente (RecursionError en `/help`).
- `push_screen_wait` sin `@work` causaba `NoActiveWorker` en los slash commands.
- `Optional[X]` en firmas de comandos Typer rompia el CLI en runtime.

### Eliminado

- Comando `/credentials` (reemplazado por `/provider`).
- Comando `/credentials config` (reemplazado por `/provider` -> click -> editor).

## [0.1.0] - 2026-09-13

Primera version funcional. Agente de codificacion autonomo para terminal.

### Anadido

- Core del agente: loop autonomo con tool calling, max_steps, compactacion automatica de contexto.
- Multi-proveedor LLM: OpenRouter, OpenAI, Anthropic (API nativa), Gemini (API nativa), DeepSeek, Groq, Mistral, xAI, Ollama, LM Studio.
- Herramientas built-in: read_file, write_file, edit_file, list_dir, glob_files, grep, run_powershell, run_bash, run_python, load_skill.
- Sistema de skills: carga SKILL.md (frontmatter YAML) desde builtin, usuario y proyecto. 3 skills de ejemplo incluidas.
- Soporte MCP: cliente stdio/SSE, manager multi-servidor, wrapper de tools MCP.
- Politica de permisos: modos ask / allowlist / yolo con patrones peligrosos bloqueados.
- Sesiones persistentes: JSONL append-only + metadatos .meta.json.
- TUI con Textual: chat en vivo, slash commands, modal de confirmacion de permisos, tema dark.
- CLI Typer: run, headless, chat, history, sessions, config, providers, tools, skills, mcp, perm.
- Config en cascada: keyring -> .env -> config.toml -> env vars.
- Tests: 73 tests con pytest, cobertura configurable.
- CI: GitHub Actions (Ubuntu + Windows, Python 3.11/3.12, ruff + pytest).

### Notas

- Requiere Python 3.11+.
- Proveedor por defecto: openrouter con modelo openrouter/free.
- Alternativa recomendada: groq con openai/gpt-oss-120b (gratis y muy rapido).

[0.2.0]: https://github.com/NocturneLegion/ovandocode/releases/tag/v0.2.0

[0.2.1]: https://github.com/NocturneLegion/ovandocode/releases/tag/v0.2.1
