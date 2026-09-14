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
