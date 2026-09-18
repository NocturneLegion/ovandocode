# Configuración

OVANDOCODE se configura en **3 niveles**, en orden de prioridad (mayor gana):

1. **Variables de entorno del sistema** (`.env` + variables reales del SO)
2. **Archivo `config.toml`** en `%APPDATA%\OvandoCode\`
3. **Valores por defecto** en `src/ovandocode/config/settings.py`

Las credenciales (API keys) tienen su propia cascada:

1. **Windows Credential Manager** (keyring) — más seguro
2. **`.env`** en la raíz del proyecto
3. **`config.toml`** en `%APPDATA%`
4. **Variables de entorno** del sistema

---

## 1. Archivo `.env`

Es el método más simple. Vive en la raíz del proyecto (`D:\Trabajo\OvandoCode\.env`) y se lee automáticamente al arrancar.

### Crear el archivo

```powershell
cd D:\Trabajo\OvandoCode
notepad .env
```

### Formato

```env
# Comentarios empiezan con # (no ; ni //)

OVANDOCODE_DEFAULT_PROVIDER=groq
OVANDOCODE_DEFAULT_MODEL=openai/gpt-oss-120b
OVANDOCODE_MAX_TOKENS=4096
OVANDOCODE_TEMPERATURE=0.2
OVANDOCODE_PERMISSION_MODE=allowlist
OVANDOCODE_THEME=dark
OVANDOCODE_LOG_LEVEL=INFO

# API keys (una o varias)
GROQ_API_KEY=gsk_...
OPENROUTER_API_KEY=sk-or-v1-...
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

### Reglas de sintaxis

- Cada línea: `CLAVE=valor`
- Sin espacios alrededor del `=`
- Los valores **no** se ponen entre comillas (salvo que tengan espacios)
- Los `#` al inicio de línea son comentarios
- Los `#` al final de línea también son comentarios (ej: `CLAVE=valor  # nota`)

### Comentar / descomentar

Para desactivar una variable sin borrarla:

```env
# OVANDOCODE_MAX_TOKENS=8192
OVANDOCODE_MAX_TOKENS=4096
```

---

## 2. Archivo `config.toml`

Alternativa al `.env`. Vive en la carpeta de usuario y **no** se sube al repo.

### Ubicación

| Sistema | Ruta |
|---|---|
| Windows | `C:\Users\<usuario>\AppData\Local\OvandoCode\OvandoCode\config.toml` |
| Linux | `~/.config/OvandoCode/config.toml` |
| macOS | `~/Library/Application Support/OvandoCode/config.toml` |

Para ver la ruta exacta:

```powershell
ovandocode config show
# Mira la linea 'config_dir'
```

### Formato

```toml
[providers.groq]
api_key = "gsk_..."

[providers.openrouter]
api_key = "sk-or-v1-..."
```

Es el backend menos usado; normalmente se usa keyring o `.env`.

---

## 3. Windows Credential Manager (keyring)

La forma **más segura** de guardar API keys en Windows. Usa la API nativa del sistema operativo (Credentials Manager) — las claves quedan cifradas con tu cuenta de usuario.

### Guardar una key

```powershell
ovandocode config set-key groq
```

Te pedirá la key de forma interactiva (no se muestra mientras escribes).

### Guardar sin prompt (útil para scripts)

```powershell
ovandocode config set-key groq --value "gsk_..."

# O desde variable de entorno
$env:MY_KEY = "gsk_..."
ovandocode config set-key groq --from-env MY_KEY

# O desde stdin
"gsk_..." | ovandocode config set-key groq --stdin
```

### Ver el estado de todas las keys

```powershell
ovandocode config providers
```

Salida:

```
== Proveedores ==
  [OK ] groq         source=keyring
  [OK ] openrouter   source=env
  [-- ] openai       source=none
  ...
```

La columna `source` te dice de dónde salió cada key.

### Eliminar una key

```powershell
ovandocode config del-key groq
```

Solo borra de keyring. Si la key también está en `.env`, se seguirá usando desde ahí.

---

## 4. Variables de entorno del sistema

Si defines variables en tu shell, OVANDOCODE también las respeta.

### Windows (sesión actual)

```powershell
$env:OVANDOCODE_DEFAULT_MODEL = "openai/gpt-oss-120b"
$env:GROQ_API_KEY = "gsk_..."
ovandocode chat
```

### Windows (permanente, solo usuario)

```powershell
[Environment]::SetEnvironmentVariable("OVANDOCODE_DEFAULT_MODEL", "openai/gpt-oss-120b", "User")
```

### Linux / macOS

```bash
export OVANDOCODE_DEFAULT_MODEL="openai/gpt-oss-120b"
ovandocode chat
```

---

## Tabla completa de variables

### Comportamiento del agente

| Variable | Tipo | Default | Descripción |
|---|---|---|---|
| `OVANDOCODE_DEFAULT_PROVIDER` | string | `openrouter` | Proveedor LLM por defecto |
| `OVANDOCODE_DEFAULT_MODEL` | string | `anthropic/claude-sonnet-4` | Modelo por defecto |
| `OVANDOCODE_TEMPERATURE` | float (0.0-2.0) | `0.2` | Creatividad del modelo. Menor = más determinista |
| `OVANDOCODE_MAX_TOKENS` | int | `8192` | Máximo de tokens a generar. Bajarlo si tienes poco crédito |
| `OVANDOCODE_REQUEST_TIMEOUT` | float | `120.0` | Timeout HTTP por request en segundos |
| `OVANDOCODE_PERMISSION_MODE` | `ask` / `allowlist` / `yolo` | `allowlist` | Política de ejecución de shells |
| `OVANDOCODE_AUTO_COMPACT` | bool | `true` | Auto-compactar contexto cuando se llena |
| `OVANDOCODE_COMPACT_THRESHOLD` | float (0.0-1.0) | `0.8` | Umbral de uso para compactar (0.8 = 80%) |

### Interfaz

| Variable | Tipo | Default | Descripción |
|---|---|---|---|
| `OVANDOCODE_THEME` | `dark` / `light` | `dark` | Tema de la TUI |
| `OVANDOCODE_SHOW_TOKEN_USAGE` | bool | `true` | Mostrar conteo de tokens |
| `OVANDOCODE_LOG_LEVEL` | `DEBUG` / `INFO` / `WARNING` / `ERROR` | `INFO` | Nivel de logging |
| `OVANDOCODE_LOG_TO_FILE` | bool | `true` | Escribir logs a archivo |

### Endpoints locales

| Variable | Default | Descripción |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | URL del servidor Ollama |
| `LMSTUDIO_BASE_URL` | `http://localhost:1234/v1` | URL de LM Studio |

### API keys

| Variable | Proveedor |
|---|---|
| `OPENROUTER_API_KEY` | OpenRouter |
| `OPENAI_API_KEY` | OpenAI |
| `ANTHROPIC_API_KEY` | Anthropic |
| `GEMINI_API_KEY` | Google Gemini |
| `DEEPSEEK_API_KEY` | DeepSeek |
| `GROQ_API_KEY` | Groq |
| `MISTRAL_API_KEY` | Mistral |
| `XAI_API_KEY` | xAI (Grok) |

---

## 5. Comandos del CLI para configuración

```powershell
# Ver configuracion actual
ovandocode config show

# Ver estado de cada proveedor
ovandocode config providers

# Guardar key (interactivo)
ovandocode config set-key groq

# Guardar key directa
ovandocode config set-key groq --value "gsk_..."

# Guardar en .env en vez de keyring
ovandocode config set-key groq --value "gsk_..." --backend env

# Eliminar key (solo keyring)
ovandocode config del-key groq
```

---

## 6. Ejemplo completo de `.env` recomendado

```env
# ============================================================
# OVANDOCODE - configuracion personal
# ============================================================

# --- Proveedor principal ---
OVANDOCODE_DEFAULT_PROVIDER=groq
OVANDOCODE_DEFAULT_MODEL=openai/gpt-oss-120b
OVANDOCODE_MAX_TOKENS=4096
OVANDOCODE_TEMPERATURE=0.2

# --- API keys (al menos una) ---
GROQ_API_KEY=gsk_...
OPENROUTER_API_KEY=sk-or-v1-...

# --- Permisos ---
# ask = pregunta todo | allowlist = auto-aprueba seguros | yolo = todo automatico
OVANDOCODE_PERMISSION_MODE=allowlist

# --- UI ---
OVANDOCODE_THEME=dark
OVANDOCODE_LOG_LEVEL=INFO
```

---

## 7. Prioridad y troubleshooting

Si una variable no parece aplicarse, revisa en este orden:

1. `ovandocode config show` — ¿aparece el valor esperado?
2. El `.env` está en `D:\Trabajo\OvandoCode\.env` (junto a `pyproject.toml`)
3. No hay espacios raros ni caracteres invisibles alrededor del `=`
4. No hay dos líneas con la misma clave (la última gana)
5. Reinicia la terminal si cambiaste variables del sistema con `SetEnvironmentVariable`

Para forzar la recarga de `.env` después de editarlo: simplemente cierra y reabre `ovandocode`.

---

## Siguiente paso

- [Proveedores](proveedores.html) — configurar cada LLM
- [Permisos](permisos.html) — modos de ejecución de comandos
- [Solución de problemas](troubleshooting.html)

---

[← Volver al inicio](index.html)
