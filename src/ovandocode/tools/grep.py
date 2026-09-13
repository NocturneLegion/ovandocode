"""Tool: grep (busqueda regex en archivos)."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ovandocode.tools.base import BaseTool, ToolError, ToolResult

IGNORE_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache", "node_modules",
               ".ruff_cache", ".mypy_cache", ".idea", ".vscode", "dist", "build"}
BINARY_EXT = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".zip", ".tar",
              ".gz", ".7z", ".exe", ".dll", ".so", ".pyc", ".woff", ".woff2"}
MAX_MATCHES = 300
MAX_FILE_BYTES = 2 * 1024 * 1024


class GrepTool(BaseTool):
    name = "grep"
    description = (
        "Busca un patron regex dentro del contenido de archivos. "
        "Respeta .gitignore basico (ignora .git, .venv, __pycache__, node_modules, etc). "
        "Devuelve lineas en formato 'ruta:linea:texto'."
    )
    parameters = {
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "Expresion regular (Python re)."},
            "path": {"type": "string", "default": ".", "description": "Directorio o archivo."},
            "glob": {"type": "string", "default": "**/*", "description": "Filtro glob."},
            "ignore_case": {"type": "boolean", "default": False},
            "max_matches": {"type": "integer", "default": 100},
        },
        "required": ["pattern"],
    }

    async def run(self, **kwargs: Any) -> ToolResult:
        pattern = kwargs.get("pattern")
        base = kwargs.get("path", ".")
        glob_pat = kwargs.get("glob", "**/*")
        ignore_case = bool(kwargs.get("ignore_case", False))
        max_matches = min(int(kwargs.get("max_matches", 100)), MAX_MATCHES)
        if not pattern:
            raise ToolError("Parametro 'pattern' obligatorio.")

        try:
            flags = re.IGNORECASE if ignore_case else 0
            rx = re.compile(pattern, flags)
        except re.error as e:
            raise ToolError(f"Regex invalida: {e}") from None

        base_path = self._resolve(base, must_exist=True)
        files: list[Path] = [base_path] if base_path.is_file() else [
            f for f in base_path.glob(glob_pat)
            if f.is_file()
            and f.suffix.lower() not in BINARY_EXT
            and not any(part in IGNORE_DIRS for part in f.parts)
        ]

        results: list[str] = []
        hits = 0
        truncated = False

        for f in files:
            if truncated:
                break
            try:
                if f.stat().st_size > MAX_FILE_BYTES:
                    continue
                text = f.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue

            rel = f.relative_to(self.project_root)
            for i, line in enumerate(text.splitlines(), 1):
                if rx.search(line):
                    results.append(f"{rel}:{i}:{line}")
                    hits += 1
                    if hits >= max_matches:
                        truncated = True
                        break

        if not results:
            return ToolResult(ok=True, content=f"(sin coincidencias para '{pattern}')")

        header = f"# {hits} coincidencia(s)"
        if truncated:
            header += f" (truncado a {max_matches})"
        return ToolResult(
            ok=True,
            content=header + "\n" + "\n".join(results),
            meta={"matches": hits, "truncated": truncated},
        )