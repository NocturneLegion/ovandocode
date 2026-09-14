# Changelog

Todas las versiones notables de OVANDOCODE.

El formato sigue Keep a Changelog y este proyecto usa Semantic Versioning.

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
