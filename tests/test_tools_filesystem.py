"""Tests de tools de filesystem."""
import pytest

from ovandocode.tools import ToolRegistry


@pytest.mark.asyncio
async def test_read_file_existente(project_dir):
    reg = ToolRegistry(project_root=project_dir)
    res = await reg.run("read_file", {"path": "archivo.txt"})
    assert res.ok
    assert "linea1" in res.content
    assert "linea3" in res.content


@pytest.mark.asyncio
async def test_read_file_inexistente(project_dir):
    reg = ToolRegistry(project_root=project_dir)
    res = await reg.run("read_file", {"path": "no_existe.txt"})
    assert not res.ok
    assert "ERROR" in res.content


@pytest.mark.asyncio
async def test_write_file_crea_archivo(project_dir):
    reg = ToolRegistry(project_root=project_dir)
    res = await reg.run("write_file", {"path": "nuevo.txt", "content": "abc"})
    assert res.ok
    assert (project_dir / "nuevo.txt").read_text(encoding="utf-8") == "abc"


@pytest.mark.asyncio
async def test_write_file_crea_directorios(project_dir):
    reg = ToolRegistry(project_root=project_dir)
    res = await reg.run("write_file", {"path": "a/b/c.txt", "content": "x"})
    assert res.ok
    assert (project_dir / "a" / "b" / "c.txt").exists()


@pytest.mark.asyncio
async def test_edit_file_reemplazo_unico(project_dir):
    reg = ToolRegistry(project_root=project_dir)
    res = await reg.run("edit_file", {
        "path": "archivo.txt",
        "old_string": "linea2",
        "new_string": "LINEA2",
    })
    assert res.ok
    assert "LINEA2" in (project_dir / "archivo.txt").read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_edit_file_ambiguo_falla(project_dir):
    (project_dir / "dup.txt").write_text("aaa\naaa\n", encoding="utf-8")
    reg = ToolRegistry(project_root=project_dir)
    res = await reg.run("edit_file", {
        "path": "dup.txt",
        "old_string": "aaa",
        "new_string": "bbb",
    })
    assert not res.ok
    assert "replace_all" in res.content or "veces" in res.content


@pytest.mark.asyncio
async def test_list_dir_no_recursivo(project_dir):
    reg = ToolRegistry(project_root=project_dir)
    res = await reg.run("list_dir", {"path": "."})
    assert res.ok
    assert "archivo.txt" in res.content
    assert "subdir" in res.content


@pytest.mark.asyncio
async def test_glob_files(project_dir):
    reg = ToolRegistry(project_root=project_dir)
    res = await reg.run("glob_files", {"pattern": "**/*.py"})
    assert res.ok
    assert "modulo.py" in res.content


@pytest.mark.asyncio
async def test_grep_encuentra_patron(project_dir):
    reg = ToolRegistry(project_root=project_dir)
    res = await reg.run("grep", {"pattern": "def hola"})
    assert res.ok
    assert "modulo.py" in res.content


@pytest.mark.asyncio
async def test_sandbox_bloquea_path_traversal(project_dir):
    reg = ToolRegistry(project_root=project_dir)
    res = await reg.run("read_file", {"path": "../../etc/passwd"})
    assert not res.ok
    assert "fuera del proyecto" in res.content.lower() or "ERROR" in res.content
