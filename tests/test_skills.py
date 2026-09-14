"""Tests del sistema de skills."""
import pytest

from ovandocode.skills import SkillError, SkillLoader, parse_skill_file


def _write_skill(base, name, body="Contenido"):
    d = base / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(
        f"---\n"
        f"name: {name}\n"
        f"description: descripcion de {name}\n"
        f"when_to_use: cuando pidan {name}\n"
        f"tags: [tag1, tag2]\n"
        f"version: 1.2.3\n"
        f"---\n\n"
        f"# {name}\n\n{body}\n",
        encoding="utf-8",
    )
    return d / "SKILL.md"


def test_parse_skill_file_ok(tmp_path):
    p = _write_skill(tmp_path, "mi-skill")
    s = parse_skill_file(p)
    assert s.name == "mi-skill"
    assert s.description == "descripcion de mi-skill"
    assert s.tags == ["tag1", "tag2"]
    assert s.version == "1.2.3"


def test_parse_skill_falta_frontmatter(tmp_path):
    p = tmp_path / "SKILL.md"
    p.write_text("# Sin frontmatter", encoding="utf-8")
    with pytest.raises(SkillError):
        parse_skill_file(p)


def test_parse_skill_falta_description(tmp_path):
    d = tmp_path / "x"
    d.mkdir()
    (d / "SKILL.md").write_text("---\nname: x\n---\nbody", encoding="utf-8")
    with pytest.raises(SkillError):
        parse_skill_file(d / "SKILL.md")


def test_loader_descubre_proyecto(tmp_path):
    _write_skill(tmp_path / "skills", "s1")
    _write_skill(tmp_path / "skills", "s2")
    loader = SkillLoader(project_root=tmp_path)
    names = {s.name for s in loader.all()}
    assert {"s1", "s2"}.issubset(names)


def test_loader_prioriza_proyecto_sobre_builtin(tmp_path):
    # El loader tiene builtin con python-testing; creamos uno con el mismo nombre
    _write_skill(tmp_path / "skills", "python-testing", body="VERSION PROYECTO")
    loader = SkillLoader(project_root=tmp_path)
    s = loader.get("python-testing")
    assert "VERSION PROYECTO" in s.body


def test_loader_catalogo_texto(tmp_path):
    _write_skill(tmp_path / "skills", "foo")
    loader = SkillLoader(project_root=tmp_path)
    text = loader.catalog_text()
    assert "Skills disponibles" in text
    assert "foo" in text


def test_loader_find_by_keywords(tmp_path):
    _write_skill(tmp_path / "skills", "test-helper")
    loader = SkillLoader(project_root=tmp_path)
    hits = loader.find_by_keywords("necesito ayuda con test-helper")
    assert any(h.name == "test-helper" for h in hits)
