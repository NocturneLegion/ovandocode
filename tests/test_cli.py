"""Tests basicos del CLI (sin invocar la TUI)."""
from typer.testing import CliRunner

from ovandocode import __version__
from ovandocode.cli import app

runner = CliRunner()


def test_version_command():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_version_flag():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_config_show():
    result = runner.invoke(app, ["config", "show"])
    assert result.exit_code == 0
    assert "OVANDOCODE config" in result.stdout


def test_tools_list():
    result = runner.invoke(app, ["tools", "list"])
    assert result.exit_code == 0
    assert "read_file" in result.stdout
    assert "write_file" in result.stdout


def test_skills_list():
    result = runner.invoke(app, ["skills", "list"])
    assert result.exit_code == 0
    # Debe encontrar los 3 builtin (minimo)
    assert "python-testing" in result.stdout


def test_perm_check_allow():
    result = runner.invoke(app, ["perm", "check", "Get-Date"])
    assert result.exit_code == 0
    assert "ALLOW" in result.stdout


def test_perm_check_dangerous():
    result = runner.invoke(app, ["perm", "check", "rm -rf /"])
    assert result.exit_code == 0
    assert "ASK" in result.stdout
