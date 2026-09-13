# ============================================================
#  OVANDOCODE - FASE 5: shell tools + permisos
#  Guardar como: D:\Trabajo\OvandoCode\_fase5.ps1
# ============================================================
$ErrorActionPreference = 'Stop'
$ProjectRoot = 'D:\Trabajo\OvandoCode'
Set-Location $ProjectRoot
$utf8 = New-Object System.Text.UTF8Encoding $false

Write-Host "=== OVANDOCODE :: Fase 5 - Shell + Permisos ===" -ForegroundColor Cyan

$toolsDir  = "$ProjectRoot\src\ovandocode\tools"
$permDir   = "$ProjectRoot\src\ovandocode\permissions"

# ============================================================
# PARTE A - Sistema de permisos
# ============================================================

# ------------------------------------------------------------
# A.1 permissions/policy.py
# ------------------------------------------------------------
$policy = @'
"""Politica de permisos para ejecucion de comandos y tools."""
from __future__ import annotations

import re
import shlex
from dataclasses import dataclass, field
from enum import Enum
from typing import Literal


class Decision(str, Enum):
    ALLOW = "allow"
    ASK = "ask"
    DENY = "deny"


Mode = Literal["ask", "allowlist", "yolo"]


@dataclass
class PermissionVerdict:
    decision: Decision
    reason: str = ""


# Patrones de comandos considerados "peligrosos" (nunca auto-permitir)
DANGEROUS_PATTERNS = [
    r"\brm\s+-rf\s+/",
    r"\bformat\b",
    r"\bmkfs\b",
    r"\bdd\s+if=",
    r":\(\)\s*\{",            # fork bomb
    r"\bRemove-Item\b.*-Recurse.*-Force",
    r"\brmdir\s+/s",
    r"\bdel\s+/f\s+/s\s+/q",
    r"\bshutdown\b",
    r"\breboot\b",
    r"\bpoweroff\b",
    r"\bdiskpart\b",
    r"\bbcdedit\b",
    r"\breg\s+delete\b",
    r"\bSet-ExecutionPolicy\s+Unrestricted",
    r"\bcurl\b.*\|\s*(bash|sh|powershell|pwsh|iex)",
    r"\biwr\b.*\|\s*iex",
    r"\bInvoke-Expression\b",
    r"\bInvoke-WebRequest\b.*\|\s*Invoke-Expression",
]

# Comandos seguros auto-permitidos (solo lectura/informativos)
DEFAULT_ALLOWLIST = [
    # PowerShell / Windows
    r"^Get-\w+",
    r"^Test-\w+",
    r"^Select-\w+",
    r"^Where-\w+",
    r"^Measure-\w+",
    r"^Resolve-Path\b",
    r"^Get-ChildItem\b",
    r"^Get-Content\b",
    r"^Get-Location\b",
    r"^Get-Date\b",
    r"^Get-Host\b",
    r"^Write-Output\b",
    r"^Write-Host\b",
    r"^echo\b",
    r"^dir\b",
    r"^type\b",
    r"^pwd\b",
    r"^cd\b",
    r"^whoami\b",
    r"^hostname\b",
    # POSIX (bash)
    r"^ls\b",
    r"^cat\b",
    r"^head\b",
    r"^tail\b",
    r"^wc\b",
    r"^grep\b",
    r"^rg\b",
    r"^find\b",
    r"^which\b",
    r"^whereis\b",
    r"^echo\b",
    r"^pwd\b",
    r"^env\b",
    r"^printenv\b",
    r"^uname\b",
    r"^whoami\b",
    # Git read-only
    r"^git\s+status\b",
    r"^git\s+log\b",
    r"^git\s+diff\b",
    r"^git\s+show\b",
    r"^git\s+branch\b(?!\s+-[dD])",
    r"^git\s+remote\b(?!\s+(add|remove|rm))",
    r"^git\s+rev-parse\b",
    # Python read-only
    r"^python\b.*--version",
    r"^python\b.*-V\b",
    r"^pip\s+list\b",
    r"^uv\s+pip\s+list\b",
]


@dataclass
class PermissionPolicy:
    """Decide si un comando puede ejecutarse.

    Modos:
      - ask:       siempre preguntar
      - allowlist: auto-permitir los que estan en allowlist, resto preguntar
      - yolo:      auto-permitir todo EXCEPTO patrones peligrosos (que igual preguntan)
    """
    mode: Mode = "allowlist"
    allowlist: list[str] = field(default_factory=lambda: list(DEFAULT_ALLOWLIST))
    denylist: list[str] = field(default_factory=lambda: list(DANGEROUS_PATTERNS))
    _allow_rx: list[re.Pattern] = field(default_factory=list, init=False)
    _deny_rx: list[re.Pattern] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        self._allow_rx = [re.compile(p, re.IGNORECASE) for p in self.allowlist]
        self._deny_rx = [re.compile(p, re.IGNORECASE) for p in self.denylist]

    def decide(self, command: str) -> PermissionVerdict:
        cmd = command.strip()
        if not cmd:
            return PermissionVerdict(Decision.DENY, "comando vacio")

        # 1) Denylist siempre gana -> preguntar (no denegar del todo para no ser molesto)
        for rx in self._deny_rx:
            if rx.search(cmd):
                return PermissionVerdict(Decision.ASK, f"patron peligroso: {rx.pattern}")

        # 2) Modo yolo -> permitir todo lo que no sea peligroso
        if self.mode == "yolo":
            return PermissionVerdict(Decision.ALLOW, "modo yolo")

        # 3) Modo ask -> siempre preguntar
        if self.mode == "ask":
            return PermissionVerdict(Decision.ASK, "modo ask")

        # 4) Modo allowlist
        for rx in self._allow_rx:
            if rx.search(cmd):
                return PermissionVerdict(Decision.ALLOW, f"allowlist: {rx.pattern}")

        return PermissionVerdict(Decision.ASK, "no esta en allowlist")

    def is_safe(self, command: str) -> bool:
        return self.decide(command).decision == Decision.ALLOW


def parse_command_tokens(command: str) -> list[str]:
    """Divide un comando en tokens (soporta comillas simples y dobles)."""
    try:
        return shlex.split(command, posix=False)
    except ValueError:
        return command.split()
'@
[IO.File]::WriteAllText("$permDir\policy.py", $policy, $utf8)
Write-Host "[OK] permissions/policy.py" -ForegroundColor Green

# ------------------------------------------------------------
# A.2 permissions/__init__.py
# ------------------------------------------------------------
$permInit = @'
"""Sistema de permisos de OVANDOCODE."""
from ovandocode.permissions.policy import (
    DEFAULT_ALLOWLIST,
    DANGEROUS_PATTERNS,
    Decision,
    PermissionPolicy,
    PermissionVerdict,
    parse_command_tokens,
)

__all__ = [
    "DEFAULT_ALLOWLIST",
    "DANGEROUS_PATTERNS",
    "Decision",
    "PermissionPolicy",
    "PermissionVerdict",
    "parse_command_tokens",
]
'@
[IO.File]::WriteAllText("$permDir\__init__.py", $permInit, $utf8)
Write-Host "[OK] permissions/__init__.py" -ForegroundColor Green

# ============================================================
# PARTE B - Shell tools
# ============================================================

# ------------------------------------------------------------
# B.1 tools/shell_base.py
# ------------------------------------------------------------
$shellBase = @'
"""Base comun para herramientas de shell (subprocess async)."""
from __future__ import annotations

import asyncio
import os
import time
from pathlib import Path
from typing import Any

from ovandocode.tools.base import BaseTool, ToolError, ToolResult


class ShellTool(BaseTool):
    """Herramienta generica para ejecutar comandos via subprocess."""

    shell_exe: list[str] = []
    timeout_default: int = 60
    timeout_max: int = 600
    max_output_bytes: int = 128 * 1024  # 128 KB

    async def run(self, **kwargs: Any) -> ToolResult:
        command = kwargs.get("command")
        if not command:
            raise ToolError("Parametro 'command' obligatorio.")

        timeout = int(kwargs.get("timeout", self.timeout_default))
        timeout = max(1, min(timeout, self.timeout_max))
        cwd_arg = kwargs.get("cwd", ".")
        cwd = self._resolve(cwd_arg, must_exist=True) if cwd_arg else self.project_root
        if not cwd.is_dir():
            raise ToolError(f"cwd no es directorio: {cwd_arg}")

        env = os.environ.copy()
        env.setdefault("PYTHONIOENCODING", "utf-8")

        t0 = time.perf_counter()
        try:
            proc = await asyncio.create_subprocess_exec(
                *self.shell_exe, command,
                cwd=str(cwd),
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError as e:
            raise ToolError(f"Ejecutable no encontrado: {self.shell_exe} ({e})") from e

        timed_out = False
        try:
            stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            timed_out = True
            try:
                proc.kill()
            except ProcessLookupError:
                pass
            stdout_b, stderr_b = await proc.communicate()

        elapsed = time.perf_counter() - t0
        returncode = proc.returncode if proc.returncode is not None else -1

        def _decode(b: bytes) -> str:
            if len(b) > self.max_output_bytes:
                b = b[: self.max_output_bytes] + b"\n[...truncado...]"
            return b.decode("utf-8", errors="replace")

        out = _decode(stdout_b)
        err = _decode(stderr_b)
        parts = [f"$ {command}", f"exit={returncode}  time={elapsed:.2f}s"]
        if timed_out:
            parts.append(f"[TIMEOUT despues de {timeout}s]")
        if out:
            parts.append("--- stdout ---")
            parts.append(out.rstrip())
        if err:
            parts.append("--- stderr ---")
            parts.append(err.rstrip())

        return ToolResult(
            ok=(returncode == 0 and not timed_out),
            content="\n".join(parts),
            meta={
                "returncode": returncode,
                "elapsed_s": round(elapsed, 3),
                "timed_out": timed_out,
                "cwd": str(cwd),
            },
        )
'@
[IO.File]::WriteAllText("$toolsDir\shell_base.py", $shellBase, $utf8)
Write-Host "[OK] tools/shell_base.py" -ForegroundColor Green

# ------------------------------------------------------------
# B.2 tools/powershell_tool.py
# ------------------------------------------------------------
$psTool = @'
"""Tool: run_powershell."""
from __future__ import annotations

import os
import shutil
from typing import Any

from ovandocode.tools.shell_base import ShellTool


def _find_pwsh() -> list[str]:
    """Prefiere pwsh (PowerShell 7) sobre powershell.exe (5.1)."""
    for exe in ("pwsh", "pwsh.exe"):
        if shutil.which(exe):
            return [exe, "-NoLogo", "-NoProfile", "-NonInteractive", "-Command"]
    for exe in ("powershell", "powershell.exe"):
        if shutil.which(exe):
            return [exe, "-NoLogo", "-NoProfile", "-NonInteractive", "-Command"]
    # Fallback en Windows siempre existe
    if os.name == "nt":
        return ["powershell.exe", "-NoLogo", "-NoProfile", "-NonInteractive", "-Command"]
    raise RuntimeError("No se encontro PowerShell en el sistema.")


class PowerShellTool(ShellTool):
    name = "run_powershell"
    description = (
        "Ejecuta un comando en PowerShell y devuelve stdout, stderr y codigo de salida. "
        "Usa esto para tareas de Windows (procesos, servicios, archivos). "
        "El cwd por defecto es la raiz del proyecto."
    )
    parameters = {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "Comando PowerShell a ejecutar."},
            "cwd": {"type": "string", "default": ".", "description": "Directorio de trabajo."},
            "timeout": {"type": "integer", "default": 60, "description": "Timeout en segundos."},
        },
        "required": ["command"],
    }
    shell_exe = _find_pwsh()
'@
[IO.File]::WriteAllText("$toolsDir\powershell_tool.py", $psTool, $utf8)
Write-Host "[OK] tools/powershell_tool.py" -ForegroundColor Green

# ------------------------------------------------------------
# B.3 tools/bash_tool.py
# ------------------------------------------------------------
$bashTool = @'
"""Tool: run_bash."""
from __future__ import annotations

import shutil
from typing import Any

from ovandocode.tools.base import ToolError
from ovandocode.tools.shell_base import ShellTool


def _find_bash() -> list[str]:
    for exe in ("bash", "bash.exe"):
        path = shutil.which(exe)
        if path:
            return [path, "-lc"]
    raise ToolError(
        "No se encontro 'bash' en el sistema. "
        "En Windows instala Git Bash o WSL para usar run_bash."
    )


class BashTool(ShellTool):
    name = "run_bash"
    description = (
        "Ejecuta un comando en bash (Git Bash en Windows, o bash nativo). "
        "Ideal para scripts POSIX, grep, awk, sed, etc."
    )
    parameters = {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "Comando bash a ejecutar."},
            "cwd": {"type": "string", "default": "."},
            "timeout": {"type": "integer", "default": 60},
        },
        "required": ["command"],
    }

    def __init__(self, **kw: Any) -> None:
        super().__init__(**kw)
        try:
            self.shell_exe = _find_bash()
        except ToolError:
            self.shell_exe = []  # se valida al ejecutar
'@
[IO.File]::WriteAllText("$toolsDir\bash_tool.py", $bashTool, $utf8)
Write-Host "[OK] tools/bash_tool.py" -ForegroundColor Green

# ------------------------------------------------------------
# B.4 tools/python_tool.py
# ------------------------------------------------------------
$pyTool = @'
"""Tool: run_python (usa el interprete del venv actual)."""
from __future__ import annotations

import sys
from typing import Any

from ovandocode.tools.shell_base import ShellTool


class PythonTool(ShellTool):
    name = "run_python"
    description = (
        "Ejecuta codigo Python con el interprete del entorno actual (uv/venv). "
        "El codigo se pasa por stdin (-c) para evitar problemas de escape. "
        "Usa esto para calculos, scripts cortos, o testear snippets."
    )
    parameters = {
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "Codigo Python a ejecutar."},
            "cwd": {"type": "string", "default": "."},
            "timeout": {"type": "integer", "default": 60},
        },
        "required": ["code"],
    }

    def __init__(self, **kw: Any) -> None:
        super().__init__(**kw)
        self.shell_exe = [sys.executable, "-c"]

    async def run(self, **kwargs: Any):
        # Renombrar 'code' a 'command' que es lo que espera ShellTool
        if "code" in kwargs and "command" not in kwargs:
            kwargs["command"] = kwargs.pop("code")
        return await super().run(**kwargs)
'@
[IO.File]::WriteAllText("$toolsDir\python_tool.py", $pyTool, $utf8)
Write-Host "[OK] tools/python_tool.py" -ForegroundColor Green

# ------------------------------------------------------------
# B.5 Actualizar registry con los nuevos tools + ignores
# ------------------------------------------------------------
$registry = @'
"""Registro global de herramientas disponibles."""
from __future__ import annotations

from pathlib import Path

from ovandocode.permissions import PermissionPolicy
from ovandocode.tools.bash_tool import BashTool
from ovandocode.tools.base import BaseTool, ToolError, ToolResult
from ovandocode.tools.edit_file import EditFileTool
from ovandocode.tools.glob_tool import GlobTool
from ovandocode.tools.grep import GrepTool
from ovandocode.tools.list_dir import ListDirTool
from ovandocode.tools.powershell_tool import PowerShellTool
from ovandocode.tools.python_tool import PythonTool
from ovandocode.tools.read_file import ReadFileTool
from ovandocode.tools.write_file import WriteFileTool

# Orden importa: los primeros van primero en el prompt del LLM
BUILTIN_TOOLS: list[type[BaseTool]] = [
    ReadFileTool,
    WriteFileTool,
    EditFileTool,
    ListDirTool,
    GlobTool,
    GrepTool,
    PowerShellTool,
    BashTool,
    PythonTool,
]


class ToolRegistry:
    """Contiene las herramientas activas de una sesion del agente."""

    def __init__(
        self,
        project_root: Path | None = None,
        policy: PermissionPolicy | None = None,
    ) -> None:
        self.project_root = (project_root or Path.cwd()).resolve()
        self.policy = policy or PermissionPolicy()
        self._tools: dict[str, BaseTool] = {}
        for cls in BUILTIN_TOOLS:
            try:
                self.register(cls(project_root=self.project_root))
            except Exception as e:
                # bash puede no estar disponible, no es fatal
                print(f"[warn] no se pudo registrar {cls.__name__}: {e}")

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
Write-Host "[OK] tools/registry.py actualizado" -ForegroundColor Green

# ------------------------------------------------------------
# B.6 Actualizar grep/list_dir/glob para ignorar scripts de fase y uv.lock
# ------------------------------------------------------------
$grepPath = "$toolsDir\grep.py"
$grepContent = [IO.File]::ReadAllText($grepPath)
$grepContent = $grepContent -replace
    'IGNORE_DIRS = \{".git", ".venv", "__pycache__", ".pytest_cache", "node_modules",\s*\r?\n\s*".ruff_cache", ".mypy_cache", ".idea", ".vscode", "dist", "build"\}',
    'IGNORE_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache", "node_modules",
               ".ruff_cache", ".mypy_cache", ".idea", ".vscode", "dist", "build"}
IGNORE_FILES = {"uv.lock", "poetry.lock", "package-lock.json", "yarn.lock"}
IGNORE_GLOBS = {"_fase*.ps1", "_fix_*.ps1"}'
[IO.File]::WriteAllText($grepPath, $grepContent, $utf8)

# Agregar el filtro de IGNORE_FILES/IGNORE_GLOBS a la logica de archivos
$grepContent = [IO.File]::ReadAllText($grepPath)
$grepContent = $grepContent -replace
    'files: list\[Path\] = \[base_path\] if base_path\.is_file\(\) else \[\r?\n\s*f for f in base_path\.glob\(glob_pat\)\r?\n\s*if f\.is_file\(\)\r?\n\s*and f\.suffix\.lower\(\) not in BINARY_EXT\r?\n\s*and not any\(part in IGNORE_DIRS for part in f\.parts\)\r?\n\s*\]',
    @'
def _skip(fp: Path) -> bool:
            if any(part in IGNORE_DIRS for part in fp.parts):
                return True
            if fp.name in IGNORE_FILES:
                return True
            from fnmatch import fnmatch
            return any(fnmatch(fp.name, g) for g in IGNORE_GLOBS)

        files: list[Path] = [base_path] if base_path.is_file() else [
            f for f in base_path.glob(glob_pat)
            if f.is_file()
            and f.suffix.lower() not in BINARY_EXT
            and not _skip(f)
        ]
'@
[IO.File]::WriteAllText($grepPath, $grepContent, $utf8)
Write-Host "[OK] tools/grep.py actualizado" -ForegroundColor Green

# ------------------------------------------------------------
# B.7 CLI: comandos permissions y shell test
# ------------------------------------------------------------
$cliPath = "$ProjectRoot\src\ovandocode\cli.py"
$cliContent = [IO.File]::ReadAllText($cliPath)

$permCmd = @'
perm_app = typer.Typer(help="Politica de permisos.")
app.add_typer(perm_app, name="perm")


@perm_app.command("check")
def perm_check(
    command: str = typer.Argument(..., help="Comando a evaluar (entre comillas)."),
    mode: str = typer.Option("allowlist", "--mode", "-m", help="ask | allowlist | yolo"),
) -> None:
    """Evalua como la politica trataria un comando."""
    from ovandocode.permissions import PermissionPolicy
    pol = PermissionPolicy(mode=mode)  # type: ignore[arg-type]
    v = pol.decide(command)
    color = {"allow": "green", "ask": "yellow", "deny": "red"}[v.decision.value]
    typer.secho(f"[{v.decision.value.upper()}] {v.reason}", fg=color)


shell_app = typer.Typer(help="Pruebas de shell tools.")
app.add_typer(shell_app, name="shell")


@shell_app.command("ps")
def shell_ps(
    command: str = typer.Argument(..., help="Comando PowerShell."),
) -> None:
    """Ejecuta un comando PowerShell usando la tool interna."""
    import asyncio
    from ovandocode.tools import ToolRegistry

    async def _go() -> None:
        reg = ToolRegistry()
        res = await reg.run("run_powershell", {"command": command, "timeout": 30})
        typer.echo(res.content)

    asyncio.run(_go())


@shell_app.command("py")
def shell_py(
    code: str = typer.Argument(..., help="Codigo Python (entre comillas)."),
) -> None:
    """Ejecuta un snippet Python usando la tool interna."""
    import asyncio
    from ovandocode.tools import ToolRegistry

    async def _go() -> None:
        reg = ToolRegistry()
        res = await reg.run("run_python", {"code": code, "timeout": 30})
        typer.echo(res.content)

    asyncio.run(_go())


def main() -> None:
'@
$cliContent = $cliContent -replace '(?ms)^def main\(\) -> None:', $permCmd
[IO.File]::WriteAllText($cliPath, $cliContent, $utf8)
Write-Host "[OK] cli.py actualizado (perm/shell)" -ForegroundColor Green

# ------------------------------------------------------------
# B.8 Verificacion
# ------------------------------------------------------------
Write-Host "`n-> probando..." -ForegroundColor Yellow
uv run python -c "from ovandocode.permissions import PermissionPolicy; print('OK perms')"
uv run ovandocode perm check "Get-ChildItem ."
uv run ovandocode perm check "Remove-Item -Recurse -Force C:\"
uv run ovandocode tools list
Write-Host ""
uv run ovandocode shell py "print(2+2)"

# ------------------------------------------------------------
# B.9 Commit
# ------------------------------------------------------------
Write-Host "`n-> commit..." -ForegroundColor Yellow
git add .
git commit -m "Fase 5: shell tools (powershell/bash/python) + politica de permisos" | Out-Null

Write-Host "`n=== Verificacion Fase 5 ===" -ForegroundColor Cyan
$checks = [ordered]@{
    'permissions/policy.py'      = (Test-Path 'src\ovandocode\permissions\policy.py')
    'tools/shell_base.py'        = (Test-Path 'src\ovandocode\tools\shell_base.py')
    'tools/powershell_tool.py'   = (Test-Path 'src\ovandocode\tools\powershell_tool.py')
    'tools/bash_tool.py'         = (Test-Path 'src\ovandocode\tools\bash_tool.py')
    'tools/python_tool.py'       = (Test-Path 'src\ovandocode\tools\python_tool.py')
    'commit Fase 5'              = [bool](git log --oneline 2>$null | Select-String 'Fase 5')
}
foreach ($k in $checks.Keys) {
    $ok = $checks[$k]
    $mark  = if ($ok) { '[OK]' } else { '[!!]' }
    $color = if ($ok) { 'Green' } else { 'Red' }
    Write-Host "$mark $k" -ForegroundColor $color
}

Write-Host "`nFase 5 completada." -ForegroundColor Cyan