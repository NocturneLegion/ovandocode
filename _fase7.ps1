# ============================================================
#  OVANDOCODE - FASE 7: Skills
#  Guardar como: D:\Trabajo\OvandoCode\_fase7.ps1
# ============================================================
$ErrorActionPreference = 'Stop'
$ProjectRoot = 'D:\Trabajo\OvandoCode'
Set-Location $ProjectRoot
$utf8 = New-Object System.Text.UTF8Encoding $false

Write-Host "=== OVANDOCODE :: Fase 7 - Skills ===" -ForegroundColor Cyan

$skillsDir = "$ProjectRoot\src\ovandocode\skills"
$builtinDir = "$skillsDir\builtin"
$userSkillsDir = "$ProjectRoot\skills"

foreach ($d in @($skillsDir, $builtinDir, $userSkillsDir)) {
    if (-not (Test-Path $d)) { New-Item -ItemType Directory -Path $d -Force | Out-Null }
}

# ------------------------------------------------------------
# 7.1 skills/types.py
# ------------------------------------------------------------
$types = @'
"""Tipos del sistema de skills."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Skill:
    """Una skill cargada desde SKILL.md."""
    name: str
    description: str
    body: str
    path: Path
    when_to_use: str = ""
    tags: list[str] = field(default_factory=list)
    version: str = "0.0.0"
    author: str = ""
    builtin: bool = False

    def to_summary(self) -> str:
        """Resumen de una linea para el system prompt."""
        tag_str = f" tags=[{','.join(self.tags)}]" if self.tags else ""
        return f"- {self.name}: {self.description}{tag_str}"

    def to_full(self) -> str:
        """Representacion completa (frontmatter + body)."""
        lines = [
            f"# Skill: {self.name}",
            f"description: {self.description}",
        ]
        if self.when_to_use:
            lines.append(f"when_to_use: {self.when_to_use}")
        if self.tags:
            lines.append(f"tags: {', '.join(self.tags)}")
        lines.append("")
        lines.append(self.body.strip())
        return "\n".join(lines)


class SkillError(Exception):
    """Error al cargar o parsear una skill."""
'@
[IO.File]::WriteAllText("$skillsDir\types.py", $types, $utf8)
Write-Host "[OK] skills/types.py" -ForegroundColor Green

# ------------------------------------------------------------
# 7.2 skills/loader.py
# ------------------------------------------------------------
$loader = @'
"""Cargador de skills desde directorios SKILL.md."""
from __future__ import annotations

import re
from pathlib import Path

import yaml

from ovandocode.skills.types import Skill, SkillError

FRONTMATTER_RX = re.compile(r"^---\s*\r?\n(.*?)\r?\n---\s*\r?\n(.*)$", re.DOTALL)


def parse_skill_file(path: Path, builtin: bool = False) -> Skill:
    """Parsea un archivo SKILL.md (frontmatter YAML + body markdown).

    Formato esperado:
        ---
        name: mi-skill
        description: Que hace
        when_to_use: Cuando el usuario pide X
        tags: [python, testing]
        version: 0.1.0
        ---
        # Cuerpo markdown con instrucciones
    """
    if not path.exists():
        raise SkillError(f"SKILL.md no encontrado: {path}")

    raw = path.read_text(encoding="utf-8")
    m = FRONTMATTER_RX.match(raw)
    if not m:
        raise SkillError(
            f"Falta frontmatter YAML (---) al inicio: {path}"
        )

    fm_text, body = m.group(1), m.group(2)
    try:
        fm = yaml.safe_load(fm_text) or {}
    except yaml.YAMLError as e:
        raise SkillError(f"YAML invalido en {path}: {e}") from None

    if not isinstance(fm, dict):
        raise SkillError(f"Frontmatter debe ser un dict: {path}")

    name = str(fm.get("name") or path.parent.name).strip()
    description = str(fm.get("description") or "").strip()
    if not description:
        raise SkillError(f"Falta 'description' en {path}")

    tags_raw = fm.get("tags") or []
    if isinstance(tags_raw, str):
        tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
    else:
        tags = [str(t) for t in tags_raw]

    return Skill(
        name=name,
        description=description,
        body=body,
        path=path,
        when_to_use=str(fm.get("when_to_use") or "").strip(),
        tags=tags,
        version=str(fm.get("version") or "0.0.0"),
        author=str(fm.get("author") or ""),
        builtin=builtin,
    )


class SkillLoader:
    """Descubre y carga skills desde multiples directorios.

    Prioridad (mayor gana en colisiones de nombre):
      1) proyecto: <project_root>/skills/
      2) usuario:  ~/.ovandocode/skills/ (si existe)
      3) builtin:  <pkg>/skills/builtin/
    """

    def __init__(
        self,
        project_root: Path,
        user_skills_dir: Path | None = None,
    ) -> None:
        self.project_root = project_root
        self.project_skills_dir = project_root / "skills"
        self.user_skills_dir = (
            user_skills_dir or Path.home() / ".ovandocode" / "skills"
        )
        self.builtin_dir = Path(__file__).parent / "builtin"
        self._skills: dict[str, Skill] = {}
        self._load_errors: list[str] = []

    # ---------------- descubrimiento ----------------
    def discover(self, force: bool = False) -> dict[str, Skill]:
        if self._skills and not force:
            return self._skills

        self._skills.clear()
        self._load_errors.clear()

        # Orden: builtin -> usuario -> proyecto (proyecto gana)
        for base, is_builtin in [
            (self.builtin_dir, True),
            (self.user_skills_dir, False),
            (self.project_skills_dir, False),
        ]:
            if not base or not base.is_dir():
                continue
            for skill_md in sorted(base.glob("*/SKILL.md")):
                try:
                    sk = parse_skill_file(skill_md, builtin=is_builtin)
                    self._skills[sk.name] = sk
                except SkillError as e:
                    self._load_errors.append(str(e))

        return self._skills

    def get(self, name: str) -> Skill:
        self.discover()
        if name not in self._skills:
            raise SkillError(
                f"Skill no encontrada: '{name}'. Disponibles: "
                f"{sorted(self._skills.keys())}"
            )
        return self._skills[name]

    def all(self) -> list[Skill]:
        self.discover()
        return sorted(self._skills.values(), key=lambda s: s.name)

    def errors(self) -> list[str]:
        return list(self._load_errors)

    def count(self) -> int:
        return len(self._skills)

    # ---------------- integracion con el agente ----------------
    def catalog_text(self) -> str:
        """Listado compacto para el system prompt (nombre + descripcion)."""
        skills = self.all()
        if not skills:
            return ""
        lines = ["## Skills disponibles", ""]
        lines.append(
            "Tienes skills especializadas. Usa la tool `load_skill` para cargar "
            "el contenido completo cuando la tarea encaje con `when_to_use`."
        )
        lines.append("")
        for s in skills:
            lines.append(s.to_summary())
        return "\n".join(lines)

    def find_by_keywords(self, text: str) -> list[Skill]:
        """Skills cuyas tags o when_to_use aparecen mencionados en el texto."""
        lowered = text.lower()
        hits: list[Skill] = []
        for s in self.all():
            if s.name.lower() in lowered:
                hits.append(s)
                continue
            for tag in s.tags:
                if tag.lower() in lowered:
                    hits.append(s)
                    break
        return hits
'@
[IO.File]::WriteAllText("$skillsDir\loader.py", $loader, $utf8)
Write-Host "[OK] skills/loader.py" -ForegroundColor Green

# ------------------------------------------------------------
# 7.3 tools/load_skill.py
# ------------------------------------------------------------
$loadSkill = @'
"""Tool: load_skill (inyecta el cuerpo de una skill en el contexto)."""
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
'@
[IO.File]::WriteAllText("$ProjectRoot\src\ovandocode\tools\load_skill.py", $loadSkill, $utf8)
Write-Host "[OK] tools/load_skill.py" -ForegroundColor Green

# ------------------------------------------------------------
# 7.4 skills/__init__.py
# ------------------------------------------------------------
$skillsInit = @'
"""Sistema de skills de OVANDOCODE."""
from ovandocode.skills.loader import SkillLoader, parse_skill_file
from ovandocode.skills.types import Skill, SkillError

__all__ = ["Skill", "SkillError", "SkillLoader", "parse_skill_file"]
'@
[IO.File]::WriteAllText("$skillsDir\__init__.py", $skillsInit, $utf8)
Write-Host "[OK] skills/__init__.py" -ForegroundColor Green

# ------------------------------------------------------------
# 7.5 Skills built-in de ejemplo (3 utiles)
# ------------------------------------------------------------

# 7.5.1 python-testing
$skillDir = "$builtinDir\python-testing"
New-Item -ItemType Directory -Path $skillDir -Force | Out-Null
$skillMd = @'
---
name: python-testing
description: Escribir y ejecutar tests de Python con pytest siguiendo buenas practicas
when_to_use: Cuando el usuario pida escribir tests, corregir tests fallidos, o cuando modifiques codigo que tenga tests asociados
tags: [python, testing, pytest, tdd]
version: 1.0.0
author: OvandoCode
---

# Escribir tests de Python con pytest

## Estructura
- Los tests van en `tests/` paralelo a `src/`.
- Un archivo `test_<modulo>.py` por modulo testeado.
- Nombra cada test `test_<comportamiento>_<condicion>`.

## Reglas
1. **Un assert por test** cuando sea posible.
2. **Usa fixtures** en vez de setup/teardown manuales.
3. **Parametriza** casos similares con `@pytest.mark.parametrize`.
4. **Async tests** requieren `pytest-asyncio` y `asyncio_mode = auto`.
5. **Cubre**: happy path, edge cases, errores esperados, y al menos un caso limite.

## Plantilla basica

```python
import pytest
from mi_modulo import mi_funcion


@pytest.mark.parametrize("entrada,esperado", [
    (1, 2),
    (2, 4),
    (0, 0),
    (-1, -2),
])
def test_mi_funcion_duplica(entrada, esperado):
    assert mi_funcion(entrada) == esperado


def test_mi_funcion_falla_con_string():
    with pytest.raises(TypeError):
        mi_funcion("no soy numero")