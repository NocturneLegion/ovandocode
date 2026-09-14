"""Tests de la capa de proveedores (sin red)."""
import json

import pytest

from ovandocode.providers import (
    REGISTRY,
    Message,
    OpenAICompatProvider,
    list_providers,
)
from ovandocode.providers.types import (
    ProviderAuthError,
    ToolCall,
)


def test_registry_tiene_proveedores_esperados():
    names = set(list_providers())
    esperados = {
        "openrouter", "openai", "anthropic", "gemini", "deepseek",
        "groq", "mistral", "xai", "ollama", "lmstudio",
    }
    assert esperados.issubset(names)


def test_openrouter_hereda_openai_compat():
    cls = REGISTRY["openrouter"]
    assert issubclass(cls, OpenAICompatProvider)


def test_provider_requiere_key():
    p = OpenAICompatProvider(api_key=None)
    with pytest.raises(ProviderAuthError):
        p._require_key()


def test_tool_call_to_openai():
    tc = ToolCall(id="x", name="foo", arguments={"a": 1})
    d = tc.to_openai()
    assert d["type"] == "function"
    assert d["function"]["name"] == "foo"
    assert json.loads(d["function"]["arguments"]) == {"a": 1}


def test_message_to_openai_minimo():
    m = Message(role="user", content="hola")
    d = m.to_openai()
    assert d == {"role": "user", "content": "hola"}


def test_parse_respuesta_openai():
    p = OpenAICompatProvider(api_key="dummy")
    data = {
        "choices": [{
            "message": {
                "content": "hola",
                "tool_calls": [{
                    "id": "c1",
                    "function": {"name": "read_file", "arguments": '{"path": "x"}'},
                }],
            },
            "finish_reason": "tool_calls",
        }],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        "model": "test-model",
    }
    resp = p._parse(data, "fallback")
    assert resp.content == "hola"
    assert resp.tool_calls[0].name == "read_file"
    assert resp.tool_calls[0].arguments == {"path": "x"}
    assert resp.usage.input_tokens == 10
    assert resp.usage.output_tokens == 5


def test_parse_tool_call_arguments_invalidos():
    p = OpenAICompatProvider(api_key="dummy")
    data = {
        "choices": [{
            "message": {
                "content": "",
                "tool_calls": [{
                    "id": "x",
                    "function": {"name": "foo", "arguments": "NO ES JSON"},
                }],
            },
        }],
    }
    resp = p._parse(data, "m")
    assert resp.tool_calls[0].arguments == {"_raw": "NO ES JSON"}
