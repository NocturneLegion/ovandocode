"""Fix: agregar provider_timeout a AgentConfig."""
import pathlib

path = pathlib.Path(r"D:\Trabajo\OvandoCode\src\ovandocode\core\agent.py")
txt = path.read_text(encoding="utf-8")

if "provider_timeout: float" in txt:
    print("[skip] ya existe")
else:
    old = "    system_prompt_override: str | None = None"
    new = (
        "    system_prompt_override: str | None = None\n"
        "    provider_timeout: float = 180.0"
    )
    if old in txt:
        txt = txt.replace(old, new, 1)
        path.write_text(txt, encoding="utf-8", newline="\n")
        print("[OK] provider_timeout agregado a AgentConfig")
    else:
        print("[ERR] no encontre la linea en AgentConfig")