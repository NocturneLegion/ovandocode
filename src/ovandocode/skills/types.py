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
