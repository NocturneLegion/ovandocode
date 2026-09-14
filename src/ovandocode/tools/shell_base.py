"""Base comun para herramientas de shell (subprocess async)."""
from __future__ import annotations

import asyncio
import os
import time
from typing import Any

from ovandocode.tools.base import BaseTool, ToolError, ToolResult


class ShellTool(BaseTool):
    """Herramienta generica para ejecutar comandos via subprocess."""

    shell_exe: list[str] = []
    timeout_default: int = 60
    timeout_max: int = 600
    max_output_bytes: int = 128 * 1024  # 128 KB

    async def run(self, **kwargs: Any) -> ToolResult:
        command = kwargs.get("command")
        if not command:
            raise ToolError("Parametro 'command' obligatorio.")

        timeout = int(kwargs.get("timeout", self.timeout_default))
        timeout = max(1, min(timeout, self.timeout_max))
        cwd_arg = kwargs.get("cwd", ".")
        cwd = self._resolve(cwd_arg, must_exist=True) if cwd_arg else self.project_root
        if not cwd.is_dir():
            raise ToolError(f"cwd no es directorio: {cwd_arg}")

        env = os.environ.copy()
        env.setdefault("PYTHONIOENCODING", "utf-8")

        t0 = time.perf_counter()
        try:
            proc = await asyncio.create_subprocess_exec(
                *self.shell_exe, command,
                cwd=str(cwd),
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError as e:
            raise ToolError(f"Ejecutable no encontrado: {self.shell_exe} ({e})") from e

        timed_out = False
        try:
            stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except TimeoutError:
            timed_out = True
            try:
                proc.kill()
            except ProcessLookupError:
                pass
            stdout_b, stderr_b = await proc.communicate()

        elapsed = time.perf_counter() - t0
        returncode = proc.returncode if proc.returncode is not None else -1

        def _decode(b: bytes) -> str:
            if len(b) > self.max_output_bytes:
                b = b[: self.max_output_bytes] + b"\n[...truncado...]"
            return b.decode("utf-8", errors="replace")

        out = _decode(stdout_b)
        err = _decode(stderr_b)
        parts = [f"$ {command}", f"exit={returncode}  time={elapsed:.2f}s"]
        if timed_out:
            parts.append(f"[TIMEOUT despues de {timeout}s]")
        if out:
            parts.append("--- stdout ---")
            parts.append(out.rstrip())
        if err:
            parts.append("--- stderr ---")
            parts.append(err.rstrip())

        return ToolResult(
            ok=(returncode == 0 and not timed_out),
            content="\n".join(parts),
            meta={
                "returncode": returncode,
                "elapsed_s": round(elapsed, 3),
                "timed_out": timed_out,
                "cwd": str(cwd),
            },
        )
