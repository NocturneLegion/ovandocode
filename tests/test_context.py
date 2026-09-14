"""Tests de core.context."""
import pytest

from ovandocode.core.context import ContextManager
from ovandocode.core.messages import system, user


def test_stats_uso_bajo():
    cm = ContextManager(context_limit=1000, threshold=0.8)
    msgs = [user("hola")]
    stats = cm.stats(msgs)
    assert stats.messages == 1
    assert stats.needs_compact is False


def test_should_compact_por_umbral():
    cm = ContextManager(context_limit=100, threshold=0.5)
    # ~250 chars => ~62 tokens => 62% > 50% umbral
    msgs = [user("x" * 250)]
    assert cm.should_compact(msgs) is True


def test_compact_preserva_system_y_ultimos():
    cm = ContextManager(context_limit=1000, threshold=0.8, keep_last=3)
    msgs = [system("eres agente")] + [user(f"m{i}") for i in range(10)]
    new, summary = cm.compact(msgs)
    # system primero
    assert new[0].role == "system"
    # resumen tras el system
    assert "Contexto previo resumido" in new[1].content
    # ultimos 3 preservados
    assert new[-1].content == "m9"
    assert new[-3].content == "m7"


def test_compact_no_hace_nada_si_pocos():
    cm = ContextManager(keep_last=5)
    msgs = [user(f"m{i}") for i in range(3)]
    new, summary = cm.compact(msgs)
    assert new == msgs
    assert summary == ""


def test_threshold_invalido():
    with pytest.raises(ValueError):
        ContextManager(threshold=0)
    with pytest.raises(ValueError):
        ContextManager(threshold=1.5)


def test_keep_last_invalido():
    with pytest.raises(ValueError):
        ContextManager(keep_last=1)
