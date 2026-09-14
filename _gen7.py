"""Generador de archivos Fase 7 (skills) de OvandoCode."""
import pathlib
import re

ROOT = pathlib.Path(r"D:\Trabajo\OvandoCode")
SRC = ROOT / "src" / "ovandocode"
SKILLS = SRC / "skills"
BUILTIN = SKILLS / "builtin"


def write(path: pathlib.Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")
    print(f"[OK] {path}")


# ============================================================
# 1. skills/types.py
# ============================================================
write(SKILLS / "types.py", '''"""Tipos del sistema de skills."""
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
        return "\\n".join(lines)


class SkillError(Exception):
    """Error al cargar o parsear una skill."""
''')


# ============================================================
# 2. skills/loader.py
# ============================================================
write(SKILLS / "loader.py", '''"""Cargador de skills desde directorios SKILL.md."""
from __future__ import annotations

import re
from pathlib import Path

import yaml

from ovandocode.skills.types import Skill, SkillError

FRONTMATTER_RX = re.compile(r"^---\\s*\\r?\\n(.*?)\\r?\\n---\\s*\\r?\\n(.*)$", re.DOTALL)


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
        return "\\n".join(lines)

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
''')


# ============================================================
# 3. skills/__init__.py
# ============================================================
write(SKILLS / "__init__.py", '''"""Sistema de skills de OVANDOCODE."""
from ovandocode.skills.loader import SkillLoader, parse_skill_file
from ovandocode.skills.types import Skill, SkillError

__all__ = ["Skill", "SkillError", "SkillLoader", "parse_skill_file"]
''')


# ============================================================
# 4. tools/load_skill.py
# ============================================================
write(SRC / "tools" / "load_skill.py", '''"""Tool: load_skill."""
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
''')


# ============================================================
# 5. SKILL.md builtin: python-testing
# ============================================================
write(BUILTIN / "python-testing" / "SKILL.md", '''---
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
1. Un assert por test cuando sea posible.
2. Usa fixtures en vez de setup/teardown manuales.
3. Parametriza casos similares con pytest.mark.parametrize.
4. Async tests requieren pytest-asyncio y asyncio_mode = auto.
5. Cubre: happy path, edge cases, errores esperados, y al menos un caso limite.

## Plantilla basica

    import pytest
    from mi_modulo import mi_funcion

    @pytest.mark.parametrize("entrada,esperado", [(1,2),(2,4),(0,0),(-1,-2)])
    def test_mi_funcion_duplica(entrada, esperado):
        assert mi_funcion(entrada) == esperado

    def test_mi_funcion_falla_con_string():
        with pytest.raises(TypeError):
            mi_funcion("no soy numero")

## Comandos utiles
- Correr todo: uv run pytest
- Un archivo: uv run pytest tests/test_foo.py -v
- Con cobertura: uv run pytest --cov=src/ovandocode --cov-report=term-missing
- Detener en el primer fallo: uv run pytest -x

## Flujo
1. grep para encontrar tests existentes del modulo.
2. read_file del modulo y sus tests actuales.
3. Escribe/edita el test con edit_file (o write_file si es nuevo).
4. Corre uv run pytest <ruta> con run_powershell.
5. Si falla, itera. No declares "listo" sin ver exit=0.
''')


# ============================================================
# 6. SKILL.md builtin: code-review
# ============================================================
write(BUILTIN / "code-review" / "SKILL.md", '''---
name: code-review
description: Revisar codigo en busca de bugs, code smells y mejoras de calidad
when_to_use: Cuando el usuario pida revisar, auditar, o mejorar codigo existente
tags: [review, quality, refactor, bugs]
version: 1.0.0
author: OvandoCode
---

# Revision de codigo

## Checklist
1. Correccion: hay bugs evidentes, off-by-one, condiciones invertidas?
2. Manejo de errores: se capturan excepciones correctamente? se validan inputs?
3. Recursos: se cierran archivos, conexiones, subprocess?
4. Tipos: hay anotaciones? son correctas?
5. Duplicacion: se puede extraer funcion/clase?
6. Nombres: son descriptivos? verbos para funciones, sustantivos para clases?
7. Complejidad: funciones de mas de 50 lineas? anidamiento > 3 niveles?
8. Seguridad: inyeccion, path traversal, secrets hardcodeados?
9. Tests: el cambio tiene tests? cubren edge cases?
10. Performance: algoritmos O(n^2) evitables? queries N+1?

## Formato de salida
Agrupa por severidad:

### Criticos (rompen funcionalidad o seguridad)
- archivo:linea - descripcion + fix sugerido

### Importantes (deuda tecnica)
- ...

### Menores (estilo, preferencias)
- ...

## Reglas
- No cambies el codigo sin permiso; solo reporta.
- Si el usuario dice "aplica los fixes", hazlo uno por uno con edit_file.
- Cita archivo:linea exactos.
''')


# ============================================================
# 7. SKILL.md builtin: commit-message
# ============================================================
write(BUILTIN / "commit-message" / "SKILL.md", '''---
name: commit-message
description: Redactar mensajes de commit en formato Conventional Commits
when_to_use: Cuando el usuario pida hacer commit, redactar mensajes de commit, o revisar cambios pendientes
tags: [git, commit, conventional-commits]
version: 1.0.0
author: OvandoCode
---

# Mensajes de commit (Conventional Commits)

## Formato

    <tipo>(<scope>): <descripcion corta>

    <cuerpo opcional explicando el que y el por que>

    <footer opcional: BREAKING CHANGE, Closes #123>

## Tipos permitidos
- feat: nueva funcionalidad
- fix: correccion de bug
- docs: solo documentacion
- style: formato, espacios (sin cambio de comportamiento)
- refactor: reestructuracion sin cambio funcional
- perf: mejora de performance
- test: agregar o corregir tests
- build: build system, dependencias
- ci: CI/CD
- chore: mantenimiento (no src, no tests)
- revert: revertir commit previo

## Reglas
1. Primera linea <= 72 caracteres.
2. Imperativo presente: "add" no "added" ni "adds".
3. Sin punto final en la primera linea.
4. Scope entre parentesis cuando aplique: feat(agent): ...
5. BREAKING CHANGE en el footer si rompe compatibilidad.

## Flujo
1. git status para ver cambios.
2. git diff --stat para resumen.
3. git diff (o --staged) para detalle.
4. git log --oneline -10 para ver estilo del repo.
5. Propone un mensaje.
6. Si el usuario aprueba, ejecuta: git add -A; git commit -m "<mensaje>".

## Ejemplos
- feat(tools): add grep tool with regex and glob filters
- fix(agent): handle provider timeout without crashing
- refactor(providers): extract openai_compat base class
- docs(readme): add installation instructions for Windows
''')


# ============================================================
# 8. Modificar tools/registry.py (agregar LoadSkillTool)
# ============================================================
registry_path = SRC / "tools" / "registry.py"
txt = registry_path.read_text(encoding="utf-8")
if "LoadSkillTool" not in txt:
    txt = txt.replace(
        "from ovandocode.tools.list_dir import ListDirTool",
        "from ovandocode.tools.list_dir import ListDirTool\n"
        "from ovandocode.tools.load_skill import LoadSkillTool",
    )
    txt = txt.replace(
        "    PythonTool,\n]",
        "    PythonTool,\n    LoadSkillTool,\n]",
    )
    registry_path.write_text(txt, encoding="utf-8", newline="\n")
    print(f"[OK] {registry_path} (modificado)")
else:
    print(f"[skip] {registry_path} ya tiene LoadSkillTool")


# ============================================================
# 9. Modificar core/prompts.py (agregar skills_catalog)
# ============================================================
prompts_path = SRC / "core" / "prompts.py"
txt = prompts_path.read_text(encoding="utf-8")
if "skills_catalog" not in txt:
    # Reemplaza la firma de build_system_prompt
    txt = txt.replace(
        "def build_system_prompt(project_root: Path) -> str:",
        "def build_system_prompt(project_root: Path, skills_catalog: str = \"\") -> str:",
    )
    # Agrega {skills_catalog} al final del template (si no está)
    if "{skills_catalog}" not in txt:
        # Insertar antes de las triples comillas finales del template
        txt = txt.replace(
            'Al terminar una tarea, resume en 1-3 lineas que hiciste.\n"""',
            'Al terminar una tarea, resume en 1-3 lineas que hiciste.\n\n{skills_catalog}\n"""',
        )
    # Añadir al .format()
    txt = txt.replace(
        'date=datetime.now().strftime("%Y-%m-%d %H:%M"),\n    )',
        'date=datetime.now().strftime("%Y-%m-%d %H:%M"),\n        skills_catalog=skills_catalog or "",\n    )',
    )
    prompts_path.write_text(txt, encoding="utf-8", newline="\n")
    print(f"[OK] {prompts_path} (modificado)")
else:
    print(f"[skip] {prompts_path} ya tiene skills_catalog")


# ============================================================
# 10. Modificar core/agent.py (inyectar catálogo)
# ============================================================
agent_path = SRC / "core" / "agent.py"
txt = agent_path.read_text(encoding="utf-8")
if "SkillLoader" not in txt:
    # Import
    txt = txt.replace(
        "from ovandocode.providers.base import BaseProvider",
        "from ovandocode.providers.base import BaseProvider\n"
        "from ovandocode.skills import SkillLoader",
    )
    # _ensure_system_prompt
    old = """        prompt = self.config.system_prompt_override or build_system_prompt(
            self.tools.project_root
        )"""
    new = """        if self.config.system_prompt_override:
            prompt = self.config.system_prompt_override
        else:
            loader = SkillLoader(project_root=self.tools.project_root)
            catalog = loader.catalog_text()
            prompt = build_system_prompt(
                self.tools.project_root,
                skills_catalog=catalog,
            )"""
    txt = txt.replace(old, new)
    agent_path.write_text(txt, encoding="utf-8", newline="\n")
    print(f"[OK] {agent_path} (modificado)")
else:
    print(f"[skip] {agent_path} ya tiene SkillLoader")


# ============================================================
# 11. Modificar cli.py (agregar sub-app skills)
# ============================================================
cli_path = SRC / "cli.py"
txt = cli_path.read_text(encoding="utf-8")
if "skills_app" not in txt:
    block = '''

skills_app = typer.Typer(help="Gestion de skills.")
app.add_typer(skills_app, name="skills")


@skills_app.command("list")
def skills_list() -> None:
    """Lista skills disponibles."""
    from ovandocode.config import project_root
    from ovandocode.skills import SkillLoader
    loader = SkillLoader(project_root=project_root())
    skills = loader.all()
    if not skills:
        typer.echo("(sin skills)")
        return
    typer.echo(f"== {len(skills)} skill(s) ==")
    for s in skills:
        origen = "builtin" if s.builtin else "proyecto"
        typer.echo(f"  [{origen:<8}] {s.name:<20} v{s.version:<8} {s.description[:60]}")
    errs = loader.errors()
    if errs:
        typer.secho(f"\\n[!] {len(errs)} error(es):", fg="yellow")
        for e in errs:
            typer.secho(f"    {e}", fg="yellow")


@skills_app.command("show")
def skills_show(name: str = typer.Argument(...)) -> None:
    """Muestra una skill completa."""
    from ovandocode.config import project_root
    from ovandocode.skills import SkillError, SkillLoader
    loader = SkillLoader(project_root=project_root())
    try:
        s = loader.get(name)
    except SkillError as e:
        typer.secho(f"[ERR] {e}", fg="red")
        raise typer.Exit(1)
    typer.echo(s.to_full())
    typer.echo("")
    typer.secho(f"[path: {s.path}]", fg="bright_black")


@skills_app.command("init")
def skills_init(name: str = typer.Argument(...)) -> None:
    """Crea una skill nueva en skills/<name>/SKILL.md."""
    from ovandocode.config import project_root
    root = project_root() / "skills" / name
    path = root / "SKILL.md"
    if path.exists():
        typer.secho(f"[ERR] ya existe: {path}", fg="red")
        raise typer.Exit(1)
    root.mkdir(parents=True, exist_ok=True)
    content = (
        "---\\n"
        f"name: {name}\\n"
        "description: Describe brevemente que hace esta skill\\n"
        "when_to_use: Cuando el usuario pida...\\n"
        "tags: [ejemplo]\\n"
        "version: 0.1.0\\n"
        "---\\n"
        "\\n"
        "# " + name.replace("-", " ").title() + "\\n"
        "\\n"
        "## Instrucciones\\n"
        "\\n"
        "Aqui van las instrucciones detalladas que el agente debe seguir.\\n"
    )
    path.write_text(content, encoding="utf-8")
    typer.secho(f"[OK] creada: {path}", fg="green")
    typer.echo(f"Editala con: notepad \\"{path}\\"")
'''
    txt = txt.replace("\n\ndef main() -> None:", block + "\n\ndef main() -> None:")
    cli_path.write_text(txt, encoding="utf-8", newline="\n")
    print(f"[OK] {cli_path} (modificado)")
else:
    print(f"[skip] {cli_path} ya tiene skills_app")


print("\\n=== Fase 7 generada ===")