import pytest
from ovandocode.core.messages import summarize_for_compact, user, assistant
from ovandocode.providers.types import ToolCall


def test_summarize_returns_empty_when_within_keep_last():
    """Si hay <= keep_last mensajes, el resumen esta vacio."""
    messages = [user(f"msg{i}") for i in range(6)]
    assert summarize_for_compact(messages) == ""


def test_summarize_with_default_keep_last():
    """Con 7 mensajes, resume el primero (se descartan los ultimos 6)."""
    messages = [user(f"msg{i}") for i in range(7)]
    result = summarize_for_compact(messages)
    assert result == "[user] msg0"


def test_summarize_custom_keep_last():
    """keep_last personalizado controla cuantos mensajes se conservan."""
    messages = [user(f"msg{i}") for i in range(4)]
    result = summarize_for_compact(messages, keep_last=2)
    assert result == "[user] msg0\n[user] msg1"


def test_summarize_truncates_long_content():
    """El contenido de cada mensaje se trunca a 200 caracteres."""
    long_content = "a" * 201
    messages = [user(long_content)] + [user(f"msg{i}") for i in range(6)]
    result = summarize_for_compact(messages)
    assert result == "[user] " + ("a" * 200) + "..."


def test_summarize_includes_tool_call_names():
    """Cuando un mensaje tiene tool_calls, se incluyen los nombres."""
    tc = ToolCall(id="tc1", name="get_weather", arguments={"city": "Madrid"})
    messages = [assistant("consultando clima", tool_calls=[tc])] + [user(f"msg{i}") for i in range(6)]
    result = summarize_for_compact(messages)
    assert "tools: get_weather" in result


def test_summarize_strips_newlines():
    """Los saltos de linea en el contenido se reemplazan por espacios."""
    messages = [user("line1\nline2\nline3")] + [user(f"msg{i}") for i in range(6)]
    result = summarize_for_compact(messages)
    assert "\n" not in result
    assert "line1 line2 line3" in result


def test_summarize_handles_empty_content():
    """Mensajes con contenido vacio no causan errores."""
    messages = [user("")] + [user(f"msg{i}") for i in range(6)]
    result = summarize_for_compact(messages)
    assert result == "[user] "


def test_summarize_empty_messages_list():
    """Con lista vacia, el resumen esta vacio."""
    assert summarize_for_compact([]) == ""
