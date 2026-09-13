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