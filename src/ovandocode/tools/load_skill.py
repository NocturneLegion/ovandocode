"""Tool: load_skill."""
from __future__ import annotations

from typing import Any

from ovandocode.skills.loader import SkillLoader
from ovandocode.tools.base import BaseTool, ToolError, ToolResult


class LoadSkillTool(BaseTool):
    name = "load_skill"
    description = (
        "Carga el contenido completo de una skill del proyecto. "
        "Usa esto cuando la tarea actual coincida con la descripcion/when_to_use "
        "de alguna skill del catalogo del system prompt. "
        "Devuelve las instrucciones detalladas que debes seguir."
    )
    parameters = {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Nombre de la skill a cargar."},
        },
        "required": ["name"],
    }

    def __init__(self, **kw: Any) -> None:
        super().__init__(**kw)
        self._loader = SkillLoader(project_root=self.project_root)

    async def run(self, **kwargs: Any) -> ToolResult:
        name = kwargs.get("name")
        if not name:
            raise ToolError("Parametro 'name' obligatorio.")
        try:
            skill = self._loader.get(name)
        except Exception as e:
            raise ToolError(f"No se pudo cargar la skill '{name}': {e}") from None
        return ToolResult(
            ok=True,
            content=skill.to_full(),
            meta={"skill": skill.name, "path": str(skill.path), "builtin": skill.builtin},
        )
