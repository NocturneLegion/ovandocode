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
