# Proveedores LLM

OVANDOCODE soporta **10 proveedores** de modelos de lenguaje. Puedes cambiar entre ellos en cualquier momento con `--provider` o editando `OVANDOCODE_DEFAULT_PROVIDER`.

---

## Tabla comparativa

| Proveedor | Costo | Tool calling | Velocidad | Ideal para |
|---|---|---|---|---|
| **Groq** | Gratis (tier generoso) | Excelente | Muy rápido | Uso diario, agentes |
| **OpenRouter** | Gratis / pago | Bueno | Medio | Explorar muchos modelos |
| **OpenAI** | Pago | Excelente | Rápido | Máxima calidad |
| **Anthropic** | Pago | Excelente | Rápido | Razonamiento complejo |
| **Gemini** | Gratis (tier) / pago | Bueno | Rápido | Tareas largas (1M ctx) |
| **DeepSeek** | Muy barato | Bueno | Medio | Costo bajo, buen coding |
| **Mistral** | Pago | Bueno | Rápido | Modelos europeos |
| **xAI (Grok)** | Pago | Bueno | Rápido | Alternativa a GPT |
| **Ollama** | Gratis (local) | Variable | Según GPU | Privacidad total |
| **LM Studio** | Gratis (local) | Variable | Según GPU | GUI + API local |

---

## 1. Groq (recomendado para empezar)

**Gratis y extremadamente rápido**. Ideal para uso diario con un agente.

### Registro

1. Ve a https://console.groq.com/keys
2. Regístrate con Google o email
3. Crea una API key (empieza por `gsk_`)

### Configuración

```env
GROQ_API_KEY=gsk_tu_key
OVANDOCODE_DEFAULT_PROVIDER=groq
OVANDOCODE_DEFAULT_MODEL=openai/gpt-oss-120b
```

### Modelos recomendados

| Modelo | Contexto | Notas |
|---|---|---|
| `openai/gpt-oss-120b` | 128K | **Recomendado para agentes.** Tool calling excelente |
| `openai/gpt-oss-20b` | 128K | Más liviano, rápido |
| `qwen/qwen3.6-27b` | 128K | Buen coding |

### Probar

```powershell
ovandocode providers ping groq
```

---

## 2. OpenRouter (agregador)

Acceso a **cientos de modelos** (Claude, GPT, Gemini, Llama, etc.) con una sola API key.

### Registro

1. Ve a https://openrouter.ai/keys
2. Regístrate (gratis)
3. Crea una key (empieza por `sk-or-v1-`)

### Configuración

```env
OPENROUTER_API_KEY=sk-or-v1-tu_key
OVANDOCODE_DEFAULT_PROVIDER=openrouter
OVANDOCODE_DEFAULT_MODEL=openrouter/free
```

### Modelos recomendados

| Modelo | Precio | Notas |
|---|---|---|
| `openrouter/free` | Gratis | **Auto-router** al mejor modelo gratuito disponible |
| `anthropic/claude-sonnet-4` | Pago | Mejor agente coding |
| `openai/gpt-4o` | Pago | Buen tool calling |
| `google/gemini-2.5-flash` | Pago barato | Rápido y barato |
| `deepseek/deepseek-chat` | Muy barato | Buena relación calidad/precio |

### Nota sobre créditos

OpenRouter reserva el `max_tokens` completo contra tu saldo antes de ejecutar. Si tienes saldo bajo, baja `OVANDOCODE_MAX_TOKENS` a 2048-4096 para evitar error 402.

---

## 3. OpenAI

Máxima calidad y tool calling con los modelos GPT.

### Registro

1. Ve a https://platform.openai.com/api-keys
2. Crea una key (empieza por `sk-`)

### Configuración

```env
OPENAI_API_KEY=sk-tu_key
OVANDOCODE_DEFAULT_PROVIDER=openai
OVANDOCODE_DEFAULT_MODEL=gpt-4o-mini
```

### Modelos recomendados

| Modelo | Contexto | Notas |
|---|---|---|
| `gpt-4o` | 128K | Máxima calidad |
| `gpt-4o-mini` | 128K | **Recomendado.** Barato y muy capaz |
| `o1-mini` | 128K | Razonamiento (sin tool calling) |

---

## 4. Anthropic (Claude)

Excelente para razonamiento complejo y tareas de agente prolongadas. Usa la **API Messages nativa** (no OpenAI-compat).

### Registro

1. Ve a https://console.anthropic.com/
2. Crea una key (empieza por `sk-ant-`)

### Configuración

```env
ANTHROPIC_API_KEY=sk-ant-tu_key
OVANDOCODE_DEFAULT_PROVIDER=anthropic
OVANDOCODE_DEFAULT_MODEL=claude-sonnet-4-20250514
```

### Modelos recomendados

| Modelo | Contexto | Notas |
|---|---|---|
| `claude-sonnet-4-20250514` | 200K | **Recomendado para agentes.** Tool calling sobresaliente |
| `claude-opus-4-20250514` | 200K | Máxima calidad (caro) |
| `claude-haiku-4-20250514` | 200K | Rápido y barato |

---

## 5. Google Gemini

Modelos Gemini con **hasta 2M tokens de contexto**. Usa la API `generativelanguage` nativa.

### Registro

1. Ve a https://aistudio.google.com/apikey
2. Crea una key gratis

### Configuración

```env
GEMINI_API_KEY=tu_key
OVANDOCODE_DEFAULT_PROVIDER=gemini
OVANDOCODE_DEFAULT_MODEL=gemini-2.5-flash
```

### Modelos recomendados

| Modelo | Contexto | Notas |
|---|---|---|
| `gemini-2.5-flash` | 1M | **Recomendado.** Rápido, gratis en tier básico |
| `gemini-2.5-pro` | 2M | Máxima calidad, más caro |
| `gemini-2.0-flash` | 1M | Versión anterior estable |

---

## 6. DeepSeek

Modelos de coding muy baratos y de calidad.

### Registro

1. Ve a https://platform.deepseek.com/
2. Crea una key

### Configuración

```env
DEEPSEEK_API_KEY=tu_key
OVANDOCODE_DEFAULT_PROVIDER=deepseek
OVANDOCODE_DEFAULT_MODEL=deepseek-chat
```

### Modelos

| Modelo | Notas |
|---|---|
| `deepseek-chat` | Modelo general, muy barato |
| `deepseek-reasoner` | Razonamiento (tipo o1) |

---

## 7. Mistral

Modelos europeos, buenos para código y multilingüe.

### Registro

1. Ve a https://console.mistral.ai/
2. Crea una key

### Configuración

```env
MISTRAL_API_KEY=tu_key
OVANDOCODE_DEFAULT_PROVIDER=mistral
OVANDOCODE_DEFAULT_MODEL=mistral-large-latest
```

---

## 8. xAI (Grok)

Modelos Grok de xAI.

### Registro

1. Ve a https://console.x.ai/
2. Crea una key

### Configuración

```env
XAI_API_KEY=tu_key
OVANDOCODE_DEFAULT_PROVIDER=xai
OVANDOCODE_DEFAULT_MODEL=grok-3
```

---

## 9. Ollama (modelos locales)

**Privacidad total**: los modelos corren en tu máquina, nada sale a internet.

### Instalación

1. Descarga de https://ollama.com/download
2. Instala un modelo:

```powershell
ollama pull qwen2.5-coder:7b
ollama pull llama3.3:70b
```

### Configuración

```env
OVANDOCODE_DEFAULT_PROVIDER=ollama
OVANDOCODE_DEFAULT_MODEL=qwen2.5-coder:7b
OLLAMA_BASE_URL=http://localhost:11434
```

### Notas

- No requiere API key
- Requiere GPU decente para modelos grandes (70B+)
- Con modelos pequeños (7B-13B) el tool calling puede ser irregular
- **Recomendado**: `qwen2.5-coder:32b` o superior para agentes

---

## 10. LM Studio (modelos locales con GUI)

Similar a Ollama pero con interfaz gráfica para gestionar modelos.

### Instalación

1. Descarga de https://lmstudio.ai/
2. Descarga un modelo desde la app
3. Inicia el servidor local (pestaña "Local Server")

### Configuración

```env
OVANDOCODE_DEFAULT_PROVIDER=lmstudio
OVANDOCODE_DEFAULT_MODEL=tu-modelo-cargado
LMSTUDIO_BASE_URL=http://localhost:1234/v1
```

---

## Comandos de gestión

```powershell
# Ver todos los proveedores y su estado
ovandocode providers list

# Probar conectividad con un proveedor
ovandocode providers ping groq

# Probar con un modelo especifico
ovandocode providers ping openrouter --model "openai/gpt-4o-mini"

# Guardar key en keyring
ovandocode config set-key groq

# Ver donde esta cada key
ovandocode config providers
```

---

## Cambiar proveedor en runtime

### Al arrancar la TUI

```powershell
# Edita .env o usa variable de entorno
$env:OVANDOCODE_DEFAULT_PROVIDER = "anthropic"
$env:OVANDOCODE_DEFAULT_MODEL = "claude-sonnet-4-20250514"
ovandocode
```

### Dentro de la TUI

Usa el comando `/provider` y `/model`:

```
/provider anthropic
/model claude-sonnet-4-20250514
```

### En modo one-shot

```powershell
ovandocode run "explica este codigo" --provider anthropic --model claude-sonnet-4-20250514
```

---

## Cómo elegir un modelo para OVANDOCODE

Un buen modelo para agentes debe tener:

1. **Tool calling nativo**: sin esto, el agente no puede usar herramientas.
2. **Contexto amplio** (≥ 32K): el system prompt + tools + historial ocupan mucho.
3. **Baja latencia**: importante porque el agente hace muchas llamadas.
4. **Precio razonable**: un agente consume 5-20x más que un chat normal.

### Recomendaciones por presupuesto

| Presupuesto | Proveedor | Modelo |
|---|---|---|
| Gratis | Groq | `openai/gpt-oss-120b` |
| Gratis | Gemini | `gemini-2.5-flash` |
| Barato | DeepSeek | `deepseek-chat` |
| Medio | OpenAI | `gpt-4o-mini` |
| Calidad | Anthropic | `claude-sonnet-4-20250514` |
| Privacidad | Ollama | `qwen2.5-coder:32b` |

---

## Troubleshooting

### Error 401 / 403 (Auth)

**Causa**: key inválida, expirada o no se está leyendo.

**Solución**:

```powershell
ovandocode config providers
# Verifica que 'source' no sea 'none'
```

### Error 402 (Payment required)

**Causa**: OpenRouter reserva `max_tokens` completo contra tu saldo.

**Solución**: baja `OVANDOCODE_MAX_TOKENS` a 2048-4096 en `.env`.

### Error 404 (Model not found)

**Causa**: el modelo no existe o fue deprecado.

**Solución**: verifica el nombre exacto en la web del proveedor. Los `:free` de OpenRouter cambian seguido.

### Error 429 (Rate limit)

**Causa**: superaste el límite por minuto.

**Solución**: espera 60 segundos o cambia de proveedor.

### Timeout

**Causa**: el modelo tarda más de `OVANDOCODE_REQUEST_TIMEOUT` segundos.

**Solución**:

```env
OVANDOCODE_REQUEST_TIMEOUT=300.0
```

### El modelo responde pero no usa tools

**Causa**: ese modelo no soporta tool calling o lo hace mal.

**Solución**: cambia a un modelo con tool calling nativo (ver tabla arriba).

---

## Siguiente paso

- [Permisos](permisos.html) — control de ejecución de comandos
- [Herramientas](herramientas.html) — lista de tools disponibles
- [Solución de problemas](troubleshooting.html)

---

[← Volver al inicio](index.html)
