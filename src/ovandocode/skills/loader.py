"""Cargador de skills desde directorios SKILL.md."""
from __future__ import annotations

import re
from pathlib import Path

import yaml

from ovandocode.skills.types import Skill, SkillError

FRONTMATTER_RX = re.compile(r"^---\s*\r?\n(.*?)\r?\n---\s*\r?\n(.*)$", re.DOTALL)


def parse_skill_file(path: Path, builtin: bool = False) -> Skill:
    """Parsea un SKILL.md (frontmatter YAML + body markdown)."""
    if not path.exists():
        raise SkillError(f"SKILL.md no encontrado: {path}")

    raw = path.read_text(encoding="utf-8")
    m = FRONTMATTER_RX.match(raw)
    if not m:
        raise SkillError(f"Falta frontmatter YAML (---) al inicio: {path}")

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

    Prioridad (mayor gana):
      1) proyecto: <project_root>/skills/
      2) usuario:  ~/.ovandocode/skills/
      3) builtin:  <pkg>/skills/builtin/
    """

    def __init__(self, project_root: Path, user_skills_dir: Path | None = None) -> None:
        self.project_root = project_root
        self.project_skills_dir = project_root / "skills"
        self.user_skills_dir = user_skills_dir or Path.home() / ".ovandocode" / "skills"
        self.builtin_dir = Path(__file__).parent / "builtin"
        self._skills: dict[str, Skill] = {}
        self._load_errors: list[str] = []

    def discover(self, force: bool = False) -> dict[str, Skill]:
        if self._skills and not force:
            return self._skills
        self._skills.clear()
        self._load_errors.clear()

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
                f"Skill no encontrada: '{name}'. Disponibles: {sorted(self._skills.keys())}"
            )
        return self._skills[name]

    def all(self) -> list[Skill]:
        self.discover()
        return sorted(self._skills.values(), key=lambda s: s.name)

    def errors(self) -> list[str]:
        return list(self._load_errors)

    def count(self) -> int:
        return len(self._skills)

    def catalog_text(self) -> str:
        """Listado compacto para el system prompt."""
        skills = self.all()
        if not skills:
            return ""
        lines = [
            "## Skills disponibles",
            "",
            "Tienes skills especializadas. Usa la tool `load_skill` para cargar "
            "el contenido completo cuando la tarea encaje con `when_to_use`.",
            "",
        ]
        for s in skills:
            lines.append(s.to_summary())
        return "\n".join(lines)

    def find_by_keywords(self, text: str) -> list[Skill]:
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
