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