"""Tests de mcp.config (sin arrancar servidores)."""
import json

import pytest

from ovandocode.mcp.config import (
    MCPServerConfig,
    load_mcp_config,
    save_mcp_config,
)


def test_load_config_vacio(tmp_path):
    p = tmp_path / "mcp.json"
    assert load_mcp_config(p) == []


def test_load_config_valido(tmp_path):
    p = tmp_path / "mcp.json"
    p.write_text(json.dumps({
        "mcpServers": {
            "srv1": {"transport": "stdio", "command": "python", "args": ["x.py"]},
            "srv2": {"transport": "sse", "url": "http://localhost:1234"},
        }
    }), encoding="utf-8")
    configs = load_mcp_config(p)
    assert len(configs) == 2
    names = {c.name for c in configs}
    assert names == {"srv1", "srv2"}


def test_load_config_invalido_no_rompe(tmp_path):
    p = tmp_path / "mcp.json"
    p.write_text("{ no json", encoding="utf-8")
    with pytest.raises(ValueError):
        load_mcp_config(p)


def test_validate_stdio_requiere_command():
    c = MCPServerConfig(name="x", transport="stdio")
    with pytest.raises(ValueError):
        c.validate()


def test_validate_sse_requiere_url():
    c = MCPServerConfig(name="x", transport="sse")
    with pytest.raises(ValueError):
        c.validate()


def test_save_roundtrip(tmp_path):
    p = tmp_path / "mcp.json"
    configs = [
        MCPServerConfig(name="a", transport="stdio", command="py", args=["x"]),
        MCPServerConfig(name="b", transport="sse", url="http://x"),
    ]
    save_mcp_config(p, configs)
    loaded = load_mcp_config(p)
    assert {c.name for c in loaded} == {"a", "b"}
