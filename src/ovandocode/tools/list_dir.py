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
