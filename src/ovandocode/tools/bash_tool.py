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