"""Tests de core.session."""
import pytest

from ovandocode.core.messages import assistant, tool_result, user
from ovandocode.core.session import SessionStore
from ovandocode.providers.types import ToolCall


def test_crear_y_persistir(tmp_path):
    store = SessionStore(tmp_path)
    s = store.new(provider="openrouter", model="test")
    s.append(user("hola"))
    s.append(assistant("respuesta"))
    assert (tmp_path / f"{s.id}.jsonl").exists()
    assert (tmp_path / f"{s.id}.meta.json").exists()


def test_cargar_roundtrip(tmp_path):
    store = SessionStore(tmp_path)
    s = store.new(provider="x", model="y")
    s.append(user("pregunta"))
    tc = ToolCall(id="1", name="foo", arguments={"a": 1})
    s.append(assistant("voy", tool_calls=[tc]))
    s.append(tool_result("1", "foo", "resultado"))

    s2 = store.load(s.id)
    assert len(s2.messages) == 3
    assert s2.messages[1].tool_calls[0].name == "foo"
    assert s2.messages[2].tool_call_id == "1"
    assert s2.provider == "x"


def test_listar_sesiones(tmp_path):
    store = SessionStore(tmp_path)
    s1 = store.new(provider="a", model="m1")
    s1.append(user("1"))
    s2 = store.new(provider="b", model="m2")
    s2.append(user("2"))

    rows = store.list_sessions()
    assert len(rows) == 2
    ids = {r["id"] for r in rows}
    assert {s1.id, s2.id}.issubset(ids)


def test_eliminar(tmp_path):
    store = SessionStore(tmp_path)
    s = store.new()
    s.append(user("x"))
    assert store.delete(s.id) is True
    assert not (tmp_path / f"{s.id}.jsonl").exists()
    assert store.delete("no-existe") is False


def test_cargar_inexistente(tmp_path):
    store = SessionStore(tmp_path)
    with pytest.raises(FileNotFoundError):
        store.load("00000000-000000")
