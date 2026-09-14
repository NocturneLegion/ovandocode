"""Tool: run_powershell."""
from __future__ import annotations

import os
import shutil

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
