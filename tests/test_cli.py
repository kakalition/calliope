from __future__ import annotations

from typer.testing import CliRunner

from calliope.cli import app
from calliope.config import get_settings


def _prepare(tmp_path, monkeypatch) -> CliRunner:
    monkeypatch.setenv("AGENT_HOME", str(tmp_path / "home"))
    get_settings.cache_clear()
    return CliRunner()


def test_entry_list_stats(tmp_path, monkeypatch):
    runner = _prepare(tmp_path, monkeypatch)

    result = runner.invoke(app, ["entry", "Today I practised English writing.", "--mood", "4"])
    assert result.exit_code == 0, result.output
    assert "saved entry" in result.output
    assert "streak: 1 days" in result.output

    listed = runner.invoke(app, ["list"])
    assert listed.exit_code == 0
    assert "Today I practised English writing." in listed.output

    stats = runner.invoke(app, ["stats"])
    assert stats.exit_code == 0
    assert "entries: 1" in stats.output
    assert "current streak: 1 days" in stats.output

    get_settings.cache_clear()


def test_soul_command(tmp_path, monkeypatch):
    runner = _prepare(tmp_path, monkeypatch)
    result = runner.invoke(app, ["soul"])
    assert result.exit_code == 0
    assert "Calliope" in result.output
    get_settings.cache_clear()


def test_up_with_nothing_enabled(tmp_path, monkeypatch):
    runner = _prepare(tmp_path, monkeypatch)
    monkeypatch.setenv("WEBUI_ENABLED", "false")
    get_settings.cache_clear()
    result = runner.invoke(app, ["up", "--no-a2a", "--no-mcp"])
    assert result.exit_code == 0
    assert "nothing to run" in result.output
    get_settings.cache_clear()
