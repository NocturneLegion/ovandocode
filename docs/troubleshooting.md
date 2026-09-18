# Solución de problemas

Problemas comunes y sus soluciones.

---

## Instalación

### `ovandocode : no se reconoce como comando`

**Causa**: el binario no está en el PATH o no se instaló.

**Solución**:

```powershell
# Verificar que esta instalado
uv tool list

# Reinstalar
uv tool install --editable .

# Actualizar PATH
uv tool update-shell

# Cerrar y reabrir la terminal
```

Si nada funciona, usa `uv run ovandocode` en lugar de `ovandocode`.

### Error de `ExecutionPolicy` al ejecutar `.ps1`

**Causa**: PowerShell bloquea scripts por defecto.

**Solución**:

```powershell
Set-ExecutionPolicy -Scope Process Bypass -Force
```

Es temporal para esa sesión. No cambia la política permanente.

---

## Proveedores LLM

### Error 401 / 403 — Auth

**Causa**: API key inválida o no se está leyendo.

**Verificar**:

```powershell
ovandocode config providers
```

Debe mostrar `source=keyring`, `source=env` o `source=toml`. Si dice `source=none`, la key no está configurada.

**Solución**:

```powershell
# Opcion 1: en .env
notepad .env
# Añade: GROQ_API_KEY=gsk_...

# Opcion 2: keyring
ovandocode config set-key groq
```

### Error 402 — Payment required (OpenRouter)

**Causa**: OpenRouter reserva `max_tokens` completo contra tu saldo.

**Solución**: baja `max_tokens` a 4096 o menos:

```env
OVANDOCODE_MAX_TOKENS=4096
```

O carga crédito en https://openrouter.ai/settings/credits.

### Error 404 — Model not found

**Causa**: el modelo no existe o fue deprecado (frecuente con `:free` en OpenRouter).

**Solución**:

- Verifica el nombre en la web del proveedor.
- Usa `openrouter/free` para que OpenRouter elija automáticamente.
- Para Groq: `openai/gpt-oss-120b` o `openai/gpt-oss-20b`.

### Error 429 — Rate limit

**Causa**: superaste el límite por minuto.

**Solución**:

- Espera 60 segundos.
- Cambia de proveedor:

```powershell
ovandocode run "..." --provider groq
```

### Timeout

**Causa**: el modelo tarda más de lo permitido.

**Solución**:

```env
OVANDOCODE_REQUEST_TIMEOUT=300.0
```

### El modelo responde pero no usa tools

**Causa**: ese modelo no soporta tool calling nativo (o lo hace mal).

**Solución**: cambia a un modelo con tool calling bueno:

| Buen tool calling | Mal tool calling |
|---|---|
| `openai/gpt-oss-120b` (Groq) | Modelos muy pequeños (<7B) |
| `claude-sonnet-4-20250514` | Modelos sin soporte de functions |
| `gpt-4o-mini` | Llama 2 |
| `gemini-2.5-flash` | |
| `deepseek-chat` | |

---

## Configuración

### `.env` no se lee

**Verificar**:

1. El archivo está en la **raíz del proyecto** (junto a `pyproject.toml`).
2. No tiene BOM ni caracteres invisibles al inicio.
3. Las claves no tienen espacios alrededor del `=`.
4. No hay dos líneas con la misma clave (la última gana).

**Debug**:

```powershell
ovandocode config show
```

Si los valores no aparecen, revisa el archivo con:

```powershell
uv run python -c "print(open('.env').read())"
```

### Los acentos se ven mal en PowerShell

**Causa**: Windows PowerShell 5.1 lee con codepage cp1252, no UTF-8.

**Solución**:

- Usa **PowerShell 7+** (`pwsh`), que lee UTF-8 por defecto.
- O usa `-Encoding UTF8` en `Get-Content`.

El problema es solo visual. Los archivos en disco están bien.

---

## Agente

### El agente se queda colgado

**Causa**: proveedor lento (especialmente `openrouter/free` con contextos grandes).

**Solución**:

1. Espera 1-2 minutos.
2. Si sigue colgado, `Ctrl+C`.
3. Cambia a un proveedor más rápido (Groq).

### `[PROVIDER ERROR]` en el chat

El agente muestra el error exacto del proveedor. Lee el código HTTP:

| Código | Significado |
|---|---|
| 401/403 | API key inválida |
| 404 | Modelo no existe |
| 429 | Rate limit |
| 402 | Sin saldo |
| 5xx | Error del proveedor (espera y reintenta) |

### `AgentMaxStepsError`

**Causa**: el agente llegó a `max_steps` (30 por defecto) sin terminar.

**Solución**:

```powershell
ovandocode run "tarea larga" --max-steps 60
```

O simplifica la tarea en subtareas más pequeñas.

### El agente comete errores recurrentes

**Causas**:

1. Modelo débil.
2. System prompt inadecuado.
3. Sin skills para la tarea.

**Solución**:

- Cambia a un modelo mejor (`claude-sonnet-4`, `gpt-4o`).
- Escribe una skill con instrucciones paso a paso.

---

## Permisos

### El agente pide permiso constantemente

**Causa**: muchas shells no están en la allowlist.

**Solución**:

```env
OVANDOCODE_PERMISSION_MODE=yolo
```

⚠️ Solo en proyectos seguros o con git activo.

### El agente no puede ejecutar nada

**Causa**: modo `ask` + respuestas negativas.

**Solución**: revisa el comando antes de aprobar. Si es seguro, pulsa `y`.

---

## TUI (Textual)

### La TUI no abre o se ve mal

**Causas**:

1. Terminal sin soporte de TUI (usa `cmd.exe` clásico).
2. Terminal demasiado pequeña.
3. Encoding incorrecto.

**Solución**:

- Usa **Windows Terminal** (no `cmd.exe`).
- Agranda la ventana (mínimo 80x24).
- Windows Terminal lee UTF-8 por defecto.

### La TUI se ve "rota" con caracteres raros

**Causa**: fuente sin soporte de caracteres Unicode de caja (box-drawing).

**Solución**: usa una fuente como **Cascadia Code**, **JetBrains Mono** o **Fira Code**.

---

## Herramientas

### `Archivo o directorio no existe`

**Causa**: la ruta pasada a la tool no existe.

**Solución**: usa `list_dir` primero para ver qué hay.

### `Ruta fuera del proyecto permitido`

**Causa**: intentaste acceder a algo fuera del `project_root`.

**Solución**: la tool está sandboxed. Trabaja con rutas relativas al proyecto.

### `Ejecutable no encontrado` (run_bash)

**Causa**: no tienes bash en Windows.

**Solución**: instala Git Bash o WSL.

```powershell
# Con winget:
winget install Git.Git
```

O usa `run_powershell` en su lugar.

---

## Skills

### Una skill no aparece en `skills list`

**Verificar**:

1. El archivo se llama **exactamente** `SKILL.md` (case-sensitive).
2. El frontmatter empieza con `---` en la línea 1.
3. Tiene el campo `description`.
4. El YAML es válido.

Corre `ovandocode skills list` y busca la sección de errores.

### El agente no usa mi skill

**Causas**:

1. `when_to_use` poco claro.
2. Modelo con tool calling débil.
3. El prompt del usuario no menciona nada que dispare la skill.

**Solución**: sé explícito (`"Usa la skill X para..."`).

---

## MCP

### `Connection closed` al arrancar un servidor MCP

**Causas**:

1. Comando incorrecto en `mcp.json`.
2. `uv` anidado (`uv run` dentro de `uv run`).
3. Script del servidor con error de import.

**Solución**:

- Verifica el comando:

```powershell
.venv\Scripts\python.exe scripts/mi_servidor.py
```

- En `mcp.json`, usa la ruta directa al python del venv:

```json
{
  "command": ".venv\\\\Scripts\\\\python.exe",
  "args": ["scripts/mi_servidor.py"]
}
```

### El servidor arranca pero no expone tools

**Causa**: no estás registrando tools con `@mcp.tool()`.

**Solución**: revisa el script del servidor. Cada tool necesita el decorador.

---

## Obtener más información

### Activar modo debug

```powershell
ovandocode --debug run "tarea que falla"
```

Muestra tracebacks completos y logging DEBUG.

### Ver logs

Windows:

```powershell
ls "$env:LOCALAPPDATA\OvandoCode\OvandoCode\Logs"
```

Linux / macOS:

```bash
ls ~/.local/state/OvandoCode/logs/
```

### Inspeccionar una sesión

```powershell
ovandocode sessions show <id>
ovandocode sessions stats <id>
```

### Preguntar a la comunidad

- Abre un issue: https://github.com/TU-USUARIO/ovandocode/issues
- Incluye: `ovandocode --version`, el error completo, y qué estabas haciendo.

---

## Siguiente paso

- Volver a la [Guía completa](GUIA.html)
- [Instalación](instalacion.html)
- [Configuración](configuracion.html)

---

[← Volver al inicio](index.html)
