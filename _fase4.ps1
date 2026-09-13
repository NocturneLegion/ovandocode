# ============================================================
#  OVANDOCODE - FASE 4: herramientas de filesystem
#  Guardar como: D:\Trabajo\OvandoCode\_fase4.ps1
# ============================================================
$ErrorActionPreference = 'Stop'
$ProjectRoot = 'D:\Trabajo\OvandoCode'
Set-Location $ProjectRoot
$utf8 = New-Object System.Text.UTF8Encoding $false

Write-Host "=== OVANDOCODE :: Fase 4 - Tools filesystem ===" -ForegroundColor Cyan

$toolsDir = "$ProjectRoot\src\ovandocode\tools"
if (-not (Test-Path $toolsDir)) { New-Item -ItemType Directory -Path $toolsDir -Force | Out-Null }

# ------------------------------------------------------------
# 4.1 tools/base.py (clase Tool abstracta)
# ------------------------------------------------------------
$base = @'
"""Clase base e infraestructura comun para todas las herramientas."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ToolError(Exception):
    """Error controlado dentro de una herramienta (se reporta al LLM)."""


@dataclass
class ToolResult:
    """Resultado de ejecutar una herramienta."""
    ok: bool
    content: str
    meta: dict[str, Any] | None = None

    def to_text(self) -> str:
        return self.content


class BaseTool(ABC):
    """Interfaz de una herramienta invocable por el LLM.

    Cada subclase declara:
      - name: identificador unico (snake_case)
      - description: texto que ve el LLM
      - parameters: JSON Schema de los argumentos
      - run(**kwargs) -> ToolResult
    """

    name: str = ""
    description: str = ""
    parameters: dict[str, Any] = {"type": "object", "properties": {}}

    def __init__(self, project_root: Path | None = None) -> None:
        self.project_root = (project_root or Path.cwd()).resolve()

    # ---------------- contrato ----------------
    @abstractmethod
    async def run(self, **kwargs: Any) -> ToolResult:
        ...

    # ---------------- helpers ----------------
    def schema(self) -> dict[str, Any]:
        """Devuelve el schema en formato OpenAI tools."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def _resolve(self, path: str, must_exist: bool = False) -> Path:
        """Resuelve una ruta relativa contra project_root con sandbox.

        Bloquea escapes fuera del project_root (ej: ../../Windows).
        """
        p = Path(path)
        if not p.is_absolute():
            p = self.project_root / p
        try:
            p = p.resolve()
        except OSError as e:
            raise ToolError(f"Ruta invalida: {path} ({e})") from e

        # Sandbox
        try:
            p.relative_to(self.project_root)
        except ValueError:
            raise ToolError(
                f"Ruta fuera del proyecto permitido: {path} "
                f"(project_root={self.project_root})"
            ) from None

        if must_exist and not p.exists():
            raise ToolError(f"Archivo o directorio no existe: {path}")
        return p
'@
[IO.File]::WriteAllText("$toolsDir\base.py", $base, $utf8)
Write-Host "[OK] tools/base.py" -ForegroundColor Green

# ------------------------------------------------------------
# 4.2 tools/read_file.py
# ------------------------------------------------------------
$read_file = @'
"""Tool: read_file."""
from __future__ import annotations

from typing import Any

from ovandocode.tools.base import BaseTool, ToolError, ToolResult

MAX_BYTES = 512 * 1024  # 512 KB


class ReadFileTool(BaseTool):
    name = "read_file"
    description = (
        "Lee el contenido de un archivo de texto. "
        "Opcionalmente especifica offset (linea inicial, 0-indexed) y limit (numero de lineas). "
        "Devuelve las lineas numeradas para facilitar ediciones posteriores."
    )
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Ruta relativa al proyecto."},
            "offset": {"type": "integer", "description": "Linea inicial (0-indexed).", "default": 0},
            "limit": {"type": "integer", "description": "Maximo de lineas a devolver.", "default": 2000},
        },
        "required": ["path"],
    }

    async def run(self, **kwargs: Any) -> ToolResult:
        path = kwargs.get("path")
        offset = int(kwargs.get("offset", 0))
        limit = int(kwargs.get("limit", 2000))
        if not path:
            raise ToolError("Parametro 'path' obligatorio.")

        p = self._resolve(path, must_exist=True)
        if not p.is_file():
            raise ToolError(f"No es un archivo regular: {path}")
        if p.stat().st_size > MAX_BYTES:
            raise ToolError(f"Archivo demasiado grande (> {MAX_BYTES} bytes): {path}")

        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            raise ToolError(f"El archivo no es texto UTF-8: {path}") from None

        lines = text.splitlines()
        total = len(lines)
        chunk = lines[offset : offset + limit]
        numbered = [f"{i + offset + 1:>6}\t{ln}" for i, ln in enumerate(chunk)]
        header = f"# {path} ({total} lineas totales, mostrando {len(chunk)} desde {offset})\n"
        return ToolResult(
            ok=True,
            content=header + "\n".join(numbered),
            meta={"path": str(p), "total_lines": total, "offset": offset, "limit": limit},
        )
'@
[IO.File]::WriteAllText("$toolsDir\read_file.py", $read_file, $utf8)
Write-Host "[OK] tools/read_file.py" -ForegroundColor Green

# ------------------------------------------------------------
# 4.3 tools/write_file.py
# ------------------------------------------------------------
$write_file = @'
"""Tool: write_file."""
from __future__ import annotations

from typing import Any

from ovandocode.tools.base import BaseTool, ToolError, ToolResult


class WriteFileTool(BaseTool):
    name = "write_file"
    description = (
        "Crea o sobrescribe un archivo con el contenido dado. "
        "Crea los directorios intermedios si no existen."
    )
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Ruta relativa al proyecto."},
            "content": {"type": "string", "description": "Contenido completo del archivo."},
        },
        "required": ["path", "content"],
    }

    async def run(self, **kwargs: Any) -> ToolResult:
        path = kwargs.get("path")
        content = kwargs.get("content", "")
        if not path:
            raise ToolError("Parametro 'path' obligatorio.")

        p = self._resolve(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        existed = p.exists()
        p.write_text(content, encoding="utf-8")
        action = "sobrescrito" if existed else "creado"
        return ToolResult(
            ok=True,
            content=f"[OK] {action}: {path} ({len(content)} caracteres)",
            meta={"path": str(p), "created": not existed, "bytes": len(content.encode('utf-8'))},
        )
'@
[IO.File]::WriteAllText("$toolsDir\write_file.py", $write_file, $utf8)
Write-Host "[OK] tools/write_file.py" -ForegroundColor Green

# ------------------------------------------------------------
# 4.4 tools/edit_file.py (find & replace exacto)
# ------------------------------------------------------------
$edit_file = @'
"""Tool: edit_file (sustitucion exacta de un fragmento unico)."""
from __future__ import annotations

from typing import Any

from ovandocode.tools.base import BaseTool, ToolError, ToolResult


class EditFileTool(BaseTool):
    name = "edit_file"
    description = (
        "Reemplaza un fragmento exacto de texto dentro de un archivo. "
        "old_string debe ser unico en el archivo; si no lo es, incluye mas contexto. "
        "Si replace_all=true, reemplaza todas las ocurrencias."
    )
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "old_string": {"type": "string", "description": "Texto original exacto."},
            "new_string": {"type": "string", "description": "Texto de reemplazo."},
            "replace_all": {"type": "boolean", "default": False},
        },
        "required": ["path", "old_string", "new_string"],
    }

    async def run(self, **kwargs: Any) -> ToolResult:
        path = kwargs.get("path")
        old = kwargs.get("old_string")
        new = kwargs.get("new_string")
        replace_all = bool(kwargs.get("replace_all", False))

        if not path or old is None or new is None:
            raise ToolError("Parametros 'path', 'old_string', 'new_string' obligatorios.")
        if old == new:
            raise ToolError("old_string y new_string son identicos.")

        p = self._resolve(path, must_exist=True)
        if not p.is_file():
            raise ToolError(f"No es archivo regular: {path}")

        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            raise ToolError(f"Archivo no UTF-8: {path}") from None

        count = text.count(old)
        if count == 0:
            raise ToolError("old_string no encontrado en el archivo.")
        if count > 1 and not replace_all:
            raise ToolError(
                f"old_string aparece {count} veces; incluye mas contexto o usa replace_all=true."
            )

        new_text = text.replace(old, new) if replace_all else text.replace(old, new, 1)
        p.write_text(new_text, encoding="utf-8")

        return ToolResult(
            ok=True,
            content=f"[OK] editado: {path} ({count if replace_all else 1} reemplazo(s))",
            meta={"path": str(p), "replacements": count if replace_all else 1},
        )
'@
[IO.File]::WriteAllText("$toolsDir\edit_file.py", $edit_file, $utf8)
Write-Host "[OK] tools/edit_file.py" -ForegroundColor Green

# ------------------------------------------------------------
# 4.5 tools/list_dir.py
# ------------------------------------------------------------
$list_dir = @'
"""Tool: list_dir."""
from __future__ import annotations

from typing import Any

from ovandocode.tools.base import BaseTool, ToolError, ToolResult

IGNORE_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache", "node_modules",
               ".ruff_cache", ".mypy_cache", ".idea", ".vscode", "dist", "build"}


class ListDirTool(BaseTool):
    name = "list_dir"
    description = (
        "Lista el contenido de un directorio (no recursivo). "
        "Muestra subdirectorios primero, luego archivos, con tamanos."
    )
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "default": "."},
            "show_hidden": {"type": "boolean", "default": False},
        },
        "required": [],
    }

    async def run(self, **kwargs: Any) -> ToolResult:
        path = kwargs.get("path", ".")
        show_hidden = bool(kwargs.get("show_hidden", False))

        p = self._resolve(path, must_exist=True)
        if not p.is_dir():
            raise ToolError(f"No es directorio: {path}")

        dirs: list[str] = []
        files: list[str] = []
        for child in sorted(p.iterdir(), key=lambda x: x.name.lower()):
            if not show_hidden and child.name.startswith("."):
                continue
            if child.is_dir():
                if child.name in IGNORE_DIRS:
                    continue
                dirs.append(f"  [DIR]  {child.name}/")
            else:
                try:
                    size = child.stat().st_size
                except OSError:
                    size = 0
                files.append(f"  [FILE] {child.name}  ({size} bytes)")

        header = f"# {path}/ ({len(dirs)} dirs, {len(files)} archivos)\n"
        body = "\n".join(dirs + files) if (dirs or files) else "  (vacio)"
        return ToolResult(
            ok=True,
            content=header + body,
            meta={"path": str(p), "dirs": len(dirs), "files": len(files)},
        )
'@
[IO.File]::WriteAllText("$toolsDir\list_dir.py", $list_dir, $utf8)
Write-Host "[OK] tools/list_dir.py" -ForegroundColor Green

# ------------------------------------------------------------
# 4.6 tools/glob.py
# ------------------------------------------------------------
$glob = @'
"""Tool: glob_files."""
from __future__ import annotations

from typing import Any

from ovandocode.tools.base import BaseTool, ToolError, ToolResult

IGNORE_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache", "node_modules",
               ".ruff_cache", ".mypy_cache", ".idea", ".vscode", "dist", "build"}
MAX_RESULTS = 500


class GlobTool(BaseTool):
    name = "glob_files"
    description = (
        "Busca archivos por patron glob (ej: '**/*.py', 'src/**/*.ts'). "
        "Devuelve rutas relativas ordenadas por fecha de modificacion (mas recientes primero)."
    )
    parameters = {
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "Patron glob, ej '**/*.py'."},
            "path": {"type": "string", "default": ".", "description": "Directorio base."},
            "max_results": {"type": "integer", "default": 200},
        },
        "required": ["pattern"],
    }

    async def run(self, **kwargs: Any) -> ToolResult:
        pattern = kwargs.get("pattern")
        base = kwargs.get("path", ".")
        max_results = min(int(kwargs.get("max_results", 200)), MAX_RESULTS)
        if not pattern:
            raise ToolError("Parametro 'pattern' obligatorio.")

        base_path = self._resolve(base, must_exist=True)
        if not base_path.is_dir():
            raise ToolError(f"No es directorio: {base}")

        matches: list[tuple[float, str]] = []
        for match in base_path.glob(pattern):
            if any(part in IGNORE_DIRS for part in match.parts):
                continue
            if not match.is_file():
                continue
            try:
                mtime = match.stat().st_mtime
            except OSError:
                mtime = 0
            matches.append((mtime, str(match.relative_to(self.project_root))))

        matches.sort(reverse=True)
        truncated = len(matches) > max_results
        matches = matches[:max_results]

        if not matches:
            return ToolResult(ok=True, content=f"(sin coincidencias para '{pattern}')")

        lines = [f"{m[1]}" for m in matches]
        header = f"# {len(lines)} coincidencia(s) para '{pattern}'"
        if truncated:
            header += f" (truncado a {max_results})"
        return ToolResult(
            ok=True,
            content=header + "\n" + "\n".join(lines),
            meta={"count": len(lines), "truncated": truncated},
        )
'@
[IO.File]::WriteAllText("$toolsDir\glob_tool.py", $glob, $utf8)
Write-Host "[OK] tools/glob_tool.py" -ForegroundColor Green

# ------------------------------------------------------------
# 4.7 tools/grep.py (sin dependencias externas)
# ------------------------------------------------------------
$grep = @'
"""Tool: grep (busqueda regex en archivos)."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ovandocode.tools.base import BaseTool, ToolError, ToolResult

IGNORE_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache", "node_modules",
               ".ruff_cache", ".mypy_cache", ".idea", ".vscode", "dist", "build"}
BINARY_EXT = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".zip", ".tar",
              ".gz", ".7z", ".exe", ".dll", ".so", ".pyc", ".woff", ".woff2"}
MAX_MATCHES = 300
MAX_FILE_BYTES = 2 * 1024 * 1024


class GrepTool(BaseTool):
    name = "grep"
    description = (
        "Busca un patron regex dentro del contenido de archivos. "
        "Respeta .gitignore basico (ignora .git, .venv, __pycache__, node_modules, etc). "
        "Devuelve lineas en formato 'ruta:linea:texto'."
    )
    parameters = {
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "Expresion regular (Python re)."},
            "path": {"type": "string", "default": ".", "description": "Directorio o archivo."},
            "glob": {"type": "string", "default": "**/*", "description": "Filtro glob."},
            "ignore_case": {"type": "boolean", "default": False},
            "max_matches": {"type": "integer", "default": 100},
        },
        "required": ["pattern"],
    }

    async def run(self, **kwargs: Any) -> ToolResult:
        pattern = kwargs.get("pattern")
        base = kwargs.get("path", ".")
        glob_pat = kwargs.get("glob", "**/*")
        ignore_case = bool(kwargs.get("ignore_case", False))
        max_matches = min(int(kwargs.get("max_matches", 100)), MAX_MATCHES)
        if not pattern:
            raise ToolError("Parametro 'pattern' obligatorio.")

        try:
            flags = re.IGNORECASE if ignore_case else 0
            rx = re.compile(pattern, flags)
        except re.error as e:
            raise ToolError(f"Regex invalida: {e}") from None

        base_path = self._resolve(base, must_exist=True)
        files: list[Path] = [base_path] if base_path.is_file() else [
            f for f in base_path.glob(glob_pat)
            if f.is_file()
            and f.suffix.lower() not in BINARY_EXT
            and not any(part in IGNORE_DIRS for part in f.parts)
        ]

        results: list[str] = []
        hits = 0
        truncated = False

        for f in files:
            if truncated:
                break
            try:
                if f.stat().st_size > MAX_FILE_BYTES:
                    continue
                text = f.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue

            rel = f.relative_to(self.project_root)
            for i, line in enumerate(text.splitlines(), 1):
                if rx.search(line):
                    results.append(f"{rel}:{i}:{line}")
                    hits += 1
                    if hits >= max_matches:
                        truncated = True
                        break

        if not results:
            return ToolResult(ok=True, content=f"(sin coincidencias para '{pattern}')")

        header = f"# {hits} coincidencia(s)"
        if truncated:
            header += f" (truncado a {max_matches})"
        return ToolResult(
            ok=True,
            content=header + "\n" + "\n".join(results),
            meta={"matches": hits, "truncated": truncated},
        )
'@
[IO.File]::WriteAllText("$toolsDir\grep.py", $grep, $utf8)
Write-Host "[OK] tools/grep.py" -ForegroundColor Green

# ------------------------------------------------------------
# 4.8 tools/registry.py (registro + factory)
# ------------------------------------------------------------
$registry = @'
"""Registro global de herramientas disponibles."""
from __future__ import annotations

from pathlib import Path

from ovandocode.tools.base import BaseTool, ToolError, ToolResult
from ovandocode.tools.edit_file import EditFileTool
from ovandocode.tools.glob_tool import GlobTool
from ovandocode.tools.grep import GrepTool
from ovandocode.tools.list_dir import ListDirTool
from ovandocode.tools.read_file import ReadFileTool
from ovandocode.tools.write_file import WriteFileTool

BUILTIN_TOOLS: list[type[BaseTool]] = [
    ReadFileTool,
    WriteFileTool,
    EditFileTool,
    ListDirTool,
    GlobTool,
    GrepTool,
]


class ToolRegistry:
    """Contiene las herramientas activas de una sesion del agente."""

    def __init__(self, project_root: Path | None = None) -> None:
        self.project_root = (project_root or Path.cwd()).resolve()
        self._tools: dict[str, BaseTool] = {}
        for cls in BUILTIN_TOOLS:
            self.register(cls(project_root=self.project_root))

    def register(self, tool: BaseTool) -> None:
        if not tool.name:
            raise ValueError(f"Tool sin nombre: {type(tool).__name__}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool:
        if name not in self._tools:
            raise ToolError(f"Herramienta desconocida: {name}")
        return self._tools[name]

    def names(self) -> list[str]:
        return sorted(self._tools.keys())

    def schemas(self) -> list[dict]:
        """Devuelve todos los schemas en formato OpenAI tools."""
        return [t.schema() for t in self._tools.values()]

    async def run(self, name: str, arguments: dict) -> ToolResult:
        tool = self.get(name)
        try:
            return await tool.run(**arguments)
        except ToolError as e:
            return ToolResult(ok=False, content=f"[ERROR] {e}")
        except Exception as e:
            return ToolResult(ok=False, content=f"[ERROR inesperado] {type(e).__name__}: {e}")


__all__ = ["BaseTool", "ToolError", "ToolRegistry", "ToolResult", "BUILTIN_TOOLS"]
'@
[IO.File]::WriteAllText("$toolsDir\registry.py", $registry, $utf8)
Write-Host "[OK] tools/registry.py" -ForegroundColor Green

# ------------------------------------------------------------
# 4.9 tools/__init__.py
# ------------------------------------------------------------
$toolsinit = @'
"""Herramientas de OVANDOCODE."""
from ovandocode.tools.base import BaseTool, ToolError, ToolResult
from ovandocode.tools.registry import BUILTIN_TOOLS, ToolRegistry

__all__ = [
    "BaseTool",
    "BUILTIN_TOOLS",
    "ToolError",
    "ToolRegistry",
    "ToolResult",
]
'@
[IO.File]::WriteAllText("$toolsDir\__init__.py", $toolsinit, $utf8)
Write-Host "[OK] tools/__init__.py" -ForegroundColor Green

# ------------------------------------------------------------
# 4.10 CLI: comando `tools list` y `tools test`
# ------------------------------------------------------------
$cliPath = "$ProjectRoot\src\ovandocode\cli.py"
$cliContent = [IO.File]::ReadAllText($cliPath)

$toolsCmd = @'
tools_app = typer.Typer(help="Herramientas del agente.")
app.add_typer(tools_app, name="tools")


@tools_app.command("list")
def tools_list() -> None:
    """Lista herramientas built-in."""
    from ovandocode.tools import ToolRegistry
    reg = ToolRegistry()
    typer.echo("== Herramientas disponibles ==")
    for n in reg.names():
        t = reg.get(n)
        typer.echo(f"  * {n:<15} {t.description.splitlines()[0][:60]}")


@tools_app.command("test")
def tools_test(
    tool: str = typer.Argument(...),
    path: str = typer.Option(".", "--path", "-p"),
) -> None:
    """Prueba rapida de una herramienta (read_file, list_dir, glob_files)."""
    import asyncio

    from ovandocode.tools import ToolRegistry
    reg = ToolRegistry()

    async def _go() -> None:
        if tool == "read_file":
            res = await reg.run("read_file", {"path": path, "limit": 10})
        elif tool == "list_dir":
            res = await reg.run("list_dir", {"path": path})
        elif tool == "glob_files":
            res = await reg.run("glob_files", {"pattern": path or "**/*.py", "max_results": 20})
        elif tool == "grep":
            res = await reg.run("grep", {"pattern": path or "import", "max_matches": 20})
        else:
            typer.secho(f"[ERR] Uso: tools test <read_file|list_dir|glob_files|grep>", fg="red")
            raise typer.Exit(1)
        typer.echo(res.content)

    asyncio.run(_go())


def main() -> None:
'@
$cliContent = $cliContent -replace '(?ms)^def main\(\) -> None:', $toolsCmd
[IO.File]::WriteAllText($cliPath, $cliContent, $utf8)
Write-Host "[OK] cli.py actualizado (tools list/test)" -ForegroundColor Green

# ------------------------------------------------------------
# 4.11 Verificacion funcional
# ------------------------------------------------------------
Write-Host "`n-> probando tools..." -ForegroundColor Yellow
uv run python -c "from ovandocode.tools import ToolRegistry; r = ToolRegistry(); print('OK:', r.names())"
uv run ovandocode tools list
Write-Host ""
uv run ovandocode tools test list_dir --path .
Write-Host ""
uv run ovandocode tools test glob_files --path "**/*.py"

# ------------------------------------------------------------
# 4.12 Commit
# ------------------------------------------------------------
Write-Host "`n-> commit..." -ForegroundColor Yellow
git add .
git commit -m "Fase 4: herramientas de filesystem (read/write/edit/list/glob/grep)" | Out-Null

Write-Host "`n=== Verificacion Fase 4 ===" -ForegroundColor Cyan
$checks = [ordered]@{
    'tools/base.py'       = (Test-Path 'src\ovandocode\tools\base.py')
    'tools/read_file.py'  = (Test-Path 'src\ovandocode\tools\read_file.py')
    'tools/write_file.py' = (Test-Path 'src\ovandocode\tools\write_file.py')
    'tools/edit_file.py'  = (Test-Path 'src\ovandocode\tools\edit_file.py')
    'tools/list_dir.py'   = (Test-Path 'src\ovandocode\tools\list_dir.py')
    'tools/glob_tool.py'  = (Test-Path 'src\ovandocode\tools\glob_tool.py')
    'tools/grep.py'       = (Test-Path 'src\ovandocode\tools\grep.py')
    'tools/registry.py'   = (Test-Path 'src\ovandocode\tools\registry.py')
    'commit Fase 4'       = [bool](git log --oneline 2>$null | Select-String 'Fase 4')
}
foreach ($k in $checks.Keys) {
    $ok = $checks[$k]
    $mark  = if ($ok) { '[OK]' } else { '[!!]' }
    $color = if ($ok) { 'Green' } else { 'Red' }
    Write-Host "$mark $k" -ForegroundColor $color
}

Write-Host "`nFase 4 completada." -ForegroundColor Cyan