"""Tests de core.messages."""

from ovandocode.core.messages import (
    assistant,
    estimate_tokens,
    from_dict,
    summarize_for_compact,
    system,
    to_dict,
    tool_result,
    user,
)
from ovandocode.providers.types import ToolCall


def test_user_crea_mensaje_con_rol():
    m = user("hola")
    assert m.role == "user"
    assert m.content == "hola"


def test_system_crea_mensaje_con_rol():
    m = system("eres un agente")
    assert m.role == "system"


def test_assistant_con_tool_calls():
    tc = ToolCall(id="1", name="read_file", arguments={"path": "x.py"})
    m = assistant("voy a leer", tool_calls=[tc])
    assert m.role == "assistant"
    assert len(m.tool_calls) == 1
    assert m.tool_calls[0].name == "read_file"


def test_tool_result_con_id_y_nombre():
    m = tool_result("call_1", "read_file", "contenido")
    assert m.role == "tool"
    assert m.tool_call_id == "call_1"
    assert m.name == "read_file"


def test_to_dict_from_dict_roundtrip():
    tc = ToolCall(id="1", name="foo", arguments={"a": 1})
    original = assistant("hola", tool_calls=[tc])
    d = to_dict(original)
    recovered = from_dict(d)
    assert recovered.role == original.role
    assert recovered.content == original.content
    assert len(recovered.tool_calls) == 1
    assert recovered.tool_calls[0].arguments == {"a": 1}


def test_estimate_tokens_aproximado():
    msgs = [user("a" * 400)]  # ~100 tokens
    n = estimate_tokens(msgs)
    assert 90 <= n <= 120


def test_estimate_tokens_vacio():
    assert estimate_tokens([]) == 1  # minimo 1


def test_summarize_con_pocos_mensajes_devuelve_vacio():
    msgs = [user(f"m{i}") for i in range(3)]
    assert summarize_for_compact(msgs, keep_last=6) == ""


def test_summarize_trunca_contenido_largo():
    msgs = [user("x" * 500), assistant("y" * 500)] + [user("reciente")] * 6
    resumen = summarize_for_compact(msgs, keep_last=6)
    assert "..." in resumen
    assert "reciente" not in resumen
