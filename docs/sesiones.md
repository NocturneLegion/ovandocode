# Sesiones

OVANDOCODE persiste cada conversación en disco para que puedas:

- **Revisar** qué hizo el agente en el pasado.
- **Reanudar** una conversación interrumpida.
- **Auditar** decisiones y tool calls.

---

## Formato de almacenamiento

Cada sesión es **un par de archivos** en la carpeta `sessions/` del proyecto:

```
sessions/
├── 20260913-215249-3f5fd4.jsonl
└── 20260913-215249-3f5fd4.meta.json
```

### `.jsonl` — historial completo

Formato **JSON Lines**: una línea por mensaje. Append-only (se añade, no se reescribe).

Cada línea es un objeto con `role`, `content`, y opcionalmente `tool_calls` o `tool_call_id`:

```json
{"role": "system", "content": "Eres OVANDOCODE..."}
{"role": "user", "content": "Lista los .py del proyecto"}
{"role": "assistant", "content": "", "tool_calls": [{"id": "...", "name": "glob_files", "arguments": {"pattern": "**/*.py"}}]}
{"role": "tool", "content": "# 47 coincidencias...", "tool_call_id": "...", "name": "glob_files"}
{"role": "assistant", "content": "Hay 47 archivos .py..."}
```

### `.meta.json` — metadata

Metadatos para que `sessions list` sea rápido (no lee el JSONL completo):

```json
{
  "id": "20260913-215249-3f5fd4",
  "created_at": "2026-09-13T21:52:49",
  "updated_at": "2026-09-13T21:53:12",
  "provider": "groq",
  "model": "openai/gpt-oss-120b",
  "message_count": 5,
  "metadata": {}
}
```

### Nombre de archivo

Formato: `YYYYMMDD-HHMMSS-xxxxxx` donde `xxxxxx` es un hash aleatorio.

Ejemplo: `20260913-215249-3f5fd4`

---

## Comandos CLI

### `sessions list` — listar todas

```powershell
ovandocode sessions list
```

Salida:

```
== 5 sesion(es) ==
  20260913-215249-3f5fd4       msgs=   5  2026-09-13T21:53:12  groq/openai/gpt-oss-120b
  20260913-210501-a1b2c3       msgs=  12  2026-09-13T21:10:22  groq/openai/gpt-oss-120b
  20260913-195855-4e064b       msgs=   3  2026-09-13T19:59:12  openrouter/free
  ...
```

### `sessions show <id>` — ver una sesión

```powershell
ovandocode sessions show 20260913-215249-3f5fd4
```

Salida (resumida):

```
== sesion 20260913-215249-3f5fd4 ==
  provider: groq
  model:    openai/gpt-oss-120b
  created:  2026-09-13T21:52:49
  updated:  2026-09-13T21:53:12
  msgs:     5

  [  1] system    Eres OVANDOCODE, un agente de codificacion...
  [  2] user      Lista los .py del proyecto
  [  3] assistant  (tools: glob_files)
  [  4] tool      # 47 coincidencia(s) para '**/*.py'...
  [  5] assistant Hay 47 archivos .py repartidos en...
```

### `sessions stats <id>` — estadísticas de contexto

```powershell
ovandocode sessions stats 20260913-215249-3f5fd4
```

Salida:

```
== stats sesion 20260913-215249-3f5fd4 ==
  mensajes:           5
  tokens (estimados): 1,247
  limite contexto:    128,000
  uso:                0.97%
  necesita compactar: False
```

### `sessions delete <id>` — eliminar

```powershell
ovandocode sessions delete 20260913-215249-3f5fd4
```

### `sessions resume <id>` — reanudar en la TUI

```powershell
ovandocode sessions resume 20260913-215249-3f5fd4
```

Abre la TUI con el historial cargado. El agente tiene contexto de todo lo anterior.

---

## Reanudar en modo one-shot

```powershell
ovandocode run "ahora hazme tests para esos archivos" --resume 20260913-215249-3f5fd4
```

---

## Ubicación de las sesiones

Por defecto van a `<proyecto>/sessions/`. Para cambiarlo:

```powershell
$env:OVANDOCODE_PROJECT_ROOT = "D:\otra\ruta"
ovandocode
# Las sesiones van a D:\otra\ruta\sessions\
```

---

## Contexto y auto-compactación

Cuando una sesión crece mucho, el agente **compacta automáticamente**:

1. Detecta que el historial supera el 80% del límite del contexto.
2. Resume los mensajes viejos en un párrafo.
3. Mantiene los últimos 8 mensajes intactos.
4. Reemplaza el historial con `[system] + [resumen] + [últimos 8]`.

Esto evita el error **context length exceeded** sin perder información crítica.

### Configurar el umbral

```env
OVANDOCODE_AUTO_COMPACT=true
OVANDOCODE_COMPACT_THRESHOLD=0.8
```

### Desactivar auto-compactación

```env
OVANDOCODE_AUTO_COMPACT=false
```

⚠️ Si la desactivas, las sesiones largas fallarán con error de contexto.

---

## Buenas prácticas

1. **Una sesión = una tarea**. No mezcles refactors con preguntas de otro módulo.
2. **Cierra la TUI con `Ctrl+C`** al terminar. La sesión se guarda automáticamente.
3. **Borra sesiones viejas** con `sessions delete` si te molestan.
4. **Usa `--resume`** para continuar tareas largas sin repetir contexto.
5. **Backup**: las sesiones son solo archivos, cópialas a donde quieras.

---

## Añadir `sessions/` a `.gitignore`

Por defecto, `.gitignore` ya ignora las sesiones:

```
sessions/*
!sessions/.gitkeep
```

Así no contaminan tu repo. Si quieres versionar alguna sesión específica:

```powershell
git add -f sessions/20260913-215249-3f5fd4.jsonl
```

---

## Troubleshooting

### `sessions list` no muestra nada

**Causa**: no hay sesiones en el proyecto actual.

**Solución**: crea una corriendo `ovandocode` y enviando un mensaje.

### No puedo reanudar una sesión

**Causas**:

1. El ID no existe (revisa `sessions list`).
2. El archivo `.jsonl` está corrupto (edítalo o bórralo).
3. La sesión es de otro proyecto.

### La sesión crece mucho

**Solución**: la auto-compactación debería manejarlo. Si no, borra la sesión y empieza una nueva.

---

## Siguiente paso

- [Solución de problemas](troubleshooting.html)

---

[← Volver al inicio](index.html)
