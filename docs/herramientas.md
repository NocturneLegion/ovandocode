# Herramientas

OVANDOCODE expone **10 herramientas built-in** al LLM más las que agregues via MCP. El modelo decide cuál usar según la tarea.

---

## Resumen

| Nombre | Categoría | Qué hace |
|---|---|---|
| `read_file` | Filesystem | Lee un archivo de texto |
| `write_file` | Filesystem | Crea o sobrescribe un archivo |
| `edit_file` | Filesystem | Reemplaza texto exacto en un archivo |
| `list_dir` | Filesystem | Lista contenido de un directorio |
| `glob_files` | Búsqueda | Encuentra archivos por patrón glob |
| `grep` | Búsqueda | Busca regex en el contenido de archivos |
| `run_powershell` | Shell | Ejecuta comandos PowerShell |
| `run_bash` | Shell | Ejecuta comandos bash |
| `run_python` | Shell | Ejecuta código Python |
| `load_skill` | Meta | Carga una skill del catálogo |

Todas las herramientas:

- Trabajan con rutas **relativas** al directorio del proyecto.
- Están **sandboxed**: no pueden acceder fuera del `project_root`.
- Tienen un timeout configurable (por defecto 60s para shells).

---

## Filesystem

### `read_file`

Lee un archivo de texto y devuelve su contenido con números de línea.

**Parámetros**:

| Nombre | Tipo | Default | Descripción |
|---|---|---|---|
| `path` | string | (requerido) | Ruta relativa al proyecto |
| `offset` | int | `0` | Línea inicial (0-indexed) |
| `limit` | int | `2000` | Máximo de líneas a devolver |

**Ejemplo de uso** (el LLM lo invoca así):

```json
{
  "path": "src/ovandocode/core/agent.py",
  "offset": 0,
  "limit": 50
}
```

**Output**:

```
# src/ovandocode/core/agent.py (450 lineas totales, mostrando 50 desde 0)
     1  """Loop principal del agente."""
     2  from __future__ import annotations
     3
     4  import asyncio
     ...
```

**Límites**: máximo 512 KB por archivo. Falla si no es UTF-8.

### `write_file`

Crea o sobrescribe un archivo. Crea directorios intermedios si no existen.

**Parámetros**:

| Nombre | Tipo | Descripción |
|---|---|---|
| `path` | string | Ruta relativa |
| `content` | string | Contenido completo |

**Advertencia**: sobrescribe sin confirmar. El agente normalmente lee primero para evitar pérdida de datos.

### `edit_file`

Reemplaza un fragmento exacto de texto. Más seguro que `write_file` para cambios quirúrgicos.

**Parámetros**:

| Nombre | Tipo | Default | Descripción |
|---|---|---|---|
| `path` | string | (requerido) | Ruta del archivo |
| `old_string` | string | (requerido) | Texto original exacto |
| `new_string` | string | (requerido) | Texto de reemplazo |
| `replace_all` | bool | `false` | Si es true, reemplaza todas las ocurrencias |

**Reglas de seguridad**:

1. `old_string` debe aparecer **al menos una vez**. Si no, error.
2. Si aparece **más de una vez** y `replace_all=false`, error (para evitar reemplazos ambiguos).
3. Si `old_string == new_string`, error.

### `list_dir`

Lista el contenido de un directorio (no recursivo).

**Parámetros**:

| Nombre | Tipo | Default | Descripción |
|---|---|---|---|
| `path` | string | `.` | Directorio a listar |
| `show_hidden` | bool | `false` | Mostrar archivos ocultos |

**Ignora automáticamente**: `.git`, `.venv`, `__pycache__`, `node_modules`, `dist`, `build`, etc.

---

## Búsqueda

### `glob_files`

Encuentra archivos por patrón glob. Resultados ordenados por fecha de modificación (más recientes primero).

**Parámetros**:

| Nombre | Tipo | Default | Descripción |
|---|---|---|---|
| `pattern` | string | (requerido) | Patrón glob, ej `**/*.py` |
| `path` | string | `.` | Directorio base |
| `max_results` | int | `200` | Máximo de resultados |

**Ejemplos de patrones**:

- `**/*.py` — todos los `.py` recursivamente
- `src/**/*.ts` — TypeScript en `src/`
- `*.md` — markdown en el directorio actual
- `tests/test_*.py` — tests

### `grep`

Busca un patrón regex en el contenido de archivos. Respeta un `.gitignore` básico.

**Parámetros**:

| Nombre | Tipo | Default | Descripción |
|---|---|---|---|
| `pattern` | string | (requerido) | Regex (Python `re`) |
| `path` | string | `.` | Directorio o archivo |
| `glob` | string | `**/*` | Filtro glob |
| `ignore_case` | bool | `false` | Case-insensitive |
| `max_matches` | int | `100` | Máximo de líneas a devolver |

**Output**: `ruta:línea:texto`.

**Ejemplos de patrones**:

- `def \w+` — definiciones de función
- `import pandas` — imports específicos
- `TODO|FIXME` — marcas de pendientes
- `class \w+\(.*\):` — definiciones de clase

---

## Shell

⚠️ Todas las herramientas de shell pasan por la **política de permisos** (ver [permisos.md](permisos.md)).

### `run_powershell`

Ejecuta un comando PowerShell. Prefiere `pwsh` (PowerShell 7) sobre `powershell.exe` (5.1).

**Parámetros**:

| Nombre | Tipo | Default | Descripción |
|---|---|---|---|
| `command` | string | (requerido) | Comando a ejecutar |
| `cwd` | string | `.` | Directorio de trabajo |
| `timeout` | int | `60` | Timeout en segundos (máx 600) |

**Output**:

```
$ Get-Date; Get-Location
exit=0  time=0.58s
--- stdout ---
domingo, 13 de septiembre de 2026 19:44:15
Path: D:\Trabajo\OvandoCode
```

### `run_bash`

Ejecuta un comando bash. En Windows usa Git Bash si está disponible.

**Requisito**: `bash` en el PATH. Si no está, la tool no se registra.

**Parámetros**: mismos que `run_powershell`.

### `run_python`

Ejecuta código Python con el intérprete del venv actual.

**Parámetros**:

| Nombre | Tipo | Default | Descripción |
|---|---|---|---|
| `code` | string | (requerido) | Código Python a ejecutar |
| `cwd` | string | `.` | Directorio de trabajo |
| `timeout` | int | `60` | Timeout en segundos |

**Ejemplo**:

```
>> run_python {'code': 'import sys; print(sys.version)'}
3.11.16 (main, Sep  1 2026, 14:15:24) [MSC v.1944 64 bit (AMD64)]
```

---

## Meta

### `load_skill`

Carga el contenido completo de una skill del catálogo. El agente la invoca cuando la tarea actual encaja con `when_to_use`.

**Parámetros**:

| Nombre | Tipo | Descripción |
|---|---|---|
| `name` | string | Nombre de la skill |

**Output**: frontmatter + cuerpo markdown de la skill.

Ver [skills.md](skills.md) para más detalle.

---

## Comandos CLI para herramientas

### Listar todas

```powershell
ovandocode tools list
```

### Invocar una directamente

```powershell
# Leer un archivo
ovandocode tools call read_file -j "{\"path\": \"README.md\"}"

# Listar un directorio
ovandocode tools call list_dir -j "{\"path\": \"src\"}"

# Glob
ovandocode tools call glob_files -j "{\"pattern\": \"**/*.py\"}"

# Grep
ovandocode tools call grep -j "{\"pattern\": \"def main\"}"

# Ejecutar codigo Python
ovandocode tools call run_python -j "{\"code\": \"print(2+2)\"}"
```

### Pruebas rápidas

```powershell
ovandocode tools test list_dir --path .
ovandocode tools test read_file --path README.md
ovandocode tools test glob_files --path "**/*.py"
ovandocode tools test grep --path "import"
```

---

## Sandbox de rutas

Todas las tools de filesystem validan que la ruta esté dentro del `project_root`. Ejemplos:

```
read_file("src/foo.py")         -> OK
read_file("../../etc/passwd")   -> ERROR: ruta fuera del proyecto
read_file("C:\\Windows\\...")  -> ERROR: ruta fuera del proyecto
```

El proyecto se determina por:

1. Variable `OVANDOCODE_PROJECT_ROOT` (si está definida).
2. Directorio de trabajo actual (`cwd`) al arrancar.

---

## Timeouts y límites

| Tool | Timeout default | Límite de output |
|---|---|---|
| `read_file` | — | 512 KB por archivo |
| `write_file` | — | sin límite |
| `edit_file` | — | sin límite |
| `list_dir` | — | sin límite |
| `glob_files` | — | 500 resultados máximo |
| `grep` | — | 300 matches, archivos < 2 MB |
| `run_powershell` | 60s | 128 KB stdout + stderr |
| `run_bash` | 60s | 128 KB stdout + stderr |
| `run_python` | 60s | 128 KB stdout + stderr |

---

## Herramientas MCP

Además de las built-in, OVANDOCODE puede cargar herramientas desde servidores MCP externos. Se registran con el prefijo `mcp__<servidor>__<tool>`.

Ejemplo: si tienes un servidor MCP llamado `github`, sus tools aparecen como:

- `mcp__github__list_repos`
- `mcp__github__create_issue`

Ver [mcp.md](mcp.md) para más detalle.

---

## Siguiente paso

- [Skills](skills.md) — crear skills personalizadas
- [MCP](mcp.md) — servidores MCP externos
- [Interfaz](interfaz.md) — uso de TUI y CLI
