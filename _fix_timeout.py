"""Parche: timeout + feedback en el loop del agente."""
import pathlib

path = pathlib.Path(r"D:\Trabajo\OvandoCode\src\ovandocode\core\agent.py")
txt = path.read_text(encoding="utf-8")

# 1. Import asyncio ya está. Agregar wait_for con timeout al chat()
old = """            try:
                assert self._provider is not None
                resp = await self._provider.chat(req)
            except ProviderError as e:
                msg = f"[PROVIDER ERROR] {type(e).__name__}: {e}"
                self._emit("on_error", msg)
                return msg"""

new = """            assert self._provider is not None
            try:
                resp = await asyncio.wait_for(
                    self._provider.chat(req),
                    timeout=self.config.provider_timeout,
                )
            except asyncio.TimeoutError:
                msg = (
                    f"[TIMEOUT] el proveedor no respondio en "
                    f"{self.config.provider_timeout}s. Intenta de nuevo o cambia de modelo."
                )
                self._emit("on_error", msg)
                return msg
            except ProviderError as e:
                msg = f"[PROVIDER ERROR] {type(e).__name__}: {e}"
                self._emit("on_error", msg)
                return msg"""

if old in txt:
    txt = txt.replace(old, new)
    print("[OK] loop con timeout aplicado")
else:
    print("[skip] el bloque ya estaba modificado o no se encontro")

# 2. Agregar provider_timeout a AgentConfig
old_cfg = """    auto_compact: bool = True
    system_prompt_override: str | None = None"""

new_cfg = """    auto_compact: bool = True
    system_prompt_override: str | None = None
    provider_timeout: float = 180.0"""

if old_cfg in txt and "provider_timeout" not in txt:
    txt = txt.replace(old_cfg, new_cfg)
    print("[OK] provider_timeout agregado a AgentConfig")

path.write_text(txt, encoding="utf-8", newline="\n")
print("Listo.")