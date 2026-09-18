# Interfaz

OVANDOCODE tiene **dos formas de uso**:

1. **TUI** (Terminal User Interface) — modo interactivo con chat en vivo.
2. **CLI** (Command Line Interface) — modo one-shot o headless para scripts.

---

## TUI (modo interactivo)

### Abrir

```powershell
ovandocode
```

O explícitamente:

```powershell
ovandocode chat
```

### Layout

```
┌─ OVANDOCODE ─────────────── v0.1.0 ────────────── [reloj] ─┐
│                                                              │
│  OVANDOCODE v0.1.0                                           │
│  Proveedor: groq                                             │
│  Modelo:    openai/gpt-oss-120b                              │
│                                                              │
│  Escribe /help para ver comandos.                            │
│                                                              │
│  Tu: crea un archivo test.py con hola mundo                  │
│                                                              │
│  Agent:                                                     │
│    >> write_file {path: 'test.py', content: 'print(...)'}    │
│    << write_file: [OK] creado: test.py (23 caracteres)       │
│                                                              │
│  Archivo test.py creado con exito.                           │
│                                                              │
│ ┌──────────────────────────────────────────────────────┐    │
│ │ Escribe tu mensaje... (o /help)                      │    │
│ └──────────────────────────────────────────────────────┘    │
│  groq/openai/gpt-oss-120b | sesion: 20260913-... | msgs: 3  │
│  ^C Salir  ^L Limpiar  ^N Nueva sesion                       │
└──────────────────────────────────────────────────────────────┘
```

### Atajos de teclado

| Atajo | Acción |
|---|---|
| `Ctrl+C` | Salir |
| `Ctrl+L` | Limpiar el chat |
| `Ctrl+N` | Nueva sesión |
| `Enter` | Enviar mensaje |

### Slash commands

Los comandos que empiezan con `/` se ejecutan dentro de la TUI:

| Comando | Descripción |
|---|---|
| `/help` | Muestra la lista de comandos |
| `/quit` | Salir |
| `/clear` | Nueva sesión (limpia el chat) |
| `/session` | Info de la sesión actual (ID, provider, modelo, mensajes) |
| `/model [nombre]` | Ver o cambiar el modelo |
| `/provider [nombre]` | Ver o cambiar el proveedor |
| `/skills` | Lista las skills disponibles |
| `/mcp` | Estado de los servidores MCP activos |
| `/tools` | Lista de herramientas activas |

### Ejemplos de uso

**Pregunta simple:**

```
¿Qué archivos .py hay en src/?
```

**Crear un archivo:**

```
Crea un README.md con instrucciones basicas de instalacion
```

**Refactorizar:**

```
Refactoriza src/utils.py para extraer la logica de parseo a su propia funcion
```

**Buscar y editar:**

```
Encuentra todos los TODO en el codigo y crea un archivo TODO.md con la lista
```

**Ejecutar tests:**

```
Corre los tests y arregla el que falle
```

**Cambiar de proveedor en runtime:**

```
/provider anthropic
/model claude-sonnet-4-20250514
```

---

## CLI (modo no interactivo)

### `run` — one-shot con output

Ejecuta el agente una vez con un prompt y muestra todo el progreso.

```powershell
ovandocode run "refactoriza src/foo.py"
```

**Opciones**:

| Flag | Descripción |
|---|---|
| `--provider`, `-p` | Proveedor a usar |
| `--model`, `-m` | Modelo a usar |
| `--max-steps` | Máximo de iteraciones del agente (default: 30) |
| `--resume`, `-r` | Reanudar una sesión existente por ID |
| `--yolo` | Auto-aprobar todas las shells |
| `--quiet`, `-q` | Mostrar solo la respuesta final |

**Ejemplo completo**:

```powershell
ovandocode run "explica el modulo core/agent.py" --provider groq --model openai/gpt-oss-120b
```

### `headless` — solo la respuesta

Diseñado para **pipelines y scripts**. No muestra progreso, no pregunta permisos.

```powershell
ovandocode headless "Dime cuantos archivos .py hay en src/"
```

Output: solo el texto de respuesta. Ideal para capturar en variables:

```powershell
$respuesta = ovandocode headless "Explica que hace src/utils.py"
Write-Host "El agente dijo: $respuesta"
```

### `headless --json` — output estructurado

```powershell
ovandocode headless "Dime cuanto es 123 + 456" --json
```

Salida:

```json
{
  "response": "579",
  "session_id": "20260913-215249-3f5fd4",
  "provider": "groq",
  "model": "openai/gpt-oss-120b",
  "messages": 3
}
```

Útil para parsear con `ConvertFrom-Json` o `jq`:

```powershell
$json = ovandocode headless "Analiza este repo" --json | ConvertFrom-Json
Write-Host "Respuesta: $($json.response)"
Write-Host "Sesion: $($json.session_id)"
```

### `history` — últimas sesiones

```powershell
ovandocode history
ovandocode history --limit 20
```

### `--version` / `-V`

```powershell
ovandocode --version
# OVANDOCODE v0.1.0
```

### `--debug`

Activa tracebacks completos y logging DEBUG:

```powershell
ovandocode --debug run "tarea que falla"
```

---

## Estructura de comandos

```
ovandocode [--version] [--debug] [COMANDO] [ARGS]

Comandos:
  (sin comando)   Abre la TUI
  chat            Abre la TUI
  run             One-shot con progreso
  headless        Solo la respuesta (para pipelines)
  history         Últimas sesiones
  version         Muestra la versión

  config          show | providers | set-key | del-key
  providers       list | ping
  tools           list | call | test
  skills          list | show | init
  sessions        list | show | delete | stats | resume
  mcp             list | init | test
  perm            check
```

---

## Combinaciones útiles

### Analizar un proyecto nuevo

```powershell
cd C:\ruta\al\proyecto
ovandocode
# dentro de la TUI:
# /skills
# Explica la estructura de este proyecto y dime por donde empezar
```

### Automatizar un refactor

```powershell
ovandocode run "Extrae la funcion parse_config de main.py a un modulo aparte"
```

### Usar en un script CI

```powershell
# En tu pipeline de CI
$review = ovandocode headless "Revisa este diff y dime si hay problemas: $(git diff)" --json
if ($review -match "error") { exit 1 }
```

### Encadenar tareas

```powershell
ovandocode run "crea tests para utils.py" 
ovandocode run "corre los tests"
ovandocode run "haz commit si todo pasa"
```

---

## Comparativa de modos

| Aspecto | TUI | run | headless |
|---|---|---|---|
| Interactivo | ✅ | ❌ | ❌ |
| Muestra tool calls | ✅ | ✅ | ❌ |
| Pregunta permisos | ✅ | ✅ | ❌ (auto) |
| Slash commands | ✅ | ❌ | ❌ |
| Output capturable | ❌ | ❌ | ✅ |
| Cambiar modelo runtime | ✅ | ❌ | ❌ |
| Ideal para | Uso diario | Tareas puntuales | Pipelines |

---

## Siguiente paso

- [Sesiones](sesiones.html) — historial y reanudar
- [Solución de problemas](troubleshooting.html)

---

[← Volver al inicio](index.html)
