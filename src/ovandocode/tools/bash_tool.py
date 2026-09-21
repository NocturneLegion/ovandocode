"""Tool: run_bash."""
from __future__ import annotations

import os
import shutil
from typing import Any

from ovandocode.tools.base import ToolError
from ovandocode.tools.shell_base import ShellTool


def _find_bash() -> list[str]:
    # 1) Buscar en PATH
    for exe in ("bash", "bash.exe"):
        path = shutil.which(exe)
        if path:
            return [path, "-lc"]
    # 2) Rutas tipicas de Git for Windows (bash.exe no suele estar en PATH)
    if os.name == "nt":
        candidates = [
            r"C:\Program Files\Git\bin\bash.exe",
            r"C:\Program Files\Git\usr\bin\bash.exe",
            r"C:\Program Files (x86)\Git\bin\bash.exe",
            r"C:\Program Files (x86)\Git\usr\bin\bash.exe",
        ]
        for c in candidates:
            if os.path.isfile(c):
                return [c, "-lc"]
    raise ToolError(
        "No se encontro 'bash' en el sistema. "
        "En Windows instala Git Bash o WSL para usar run_bash, "
        "o usa 'run_powershell' en su lugar."
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
