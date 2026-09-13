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