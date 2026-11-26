import json
import pytest

from openprospect import ai


def test_provider_settings_are_saved_outside_repository(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENPROSPECT_HOME", str(tmp_path))
    saved = ai.save_provider_settings("claude-code")
    assert saved["provider"] == "claude-code"
    stored = json.loads((tmp_path / "ai-settings.json").read_text(encoding="utf-8"))
    assert stored["provider"] == "claude-code"
    assert ai.provider_name() == "claude-code"


def test_provider_selection_rejects_unknown_provider(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENPROSPECT_HOME", str(tmp_path))
    with pytest.raises(ValueError):
        ai.save_provider_settings("paid-magic")


def test_cli_provider_is_honestly_not_connected_without_binary(monkeypatch):
    monkeypatch.setattr(ai.shutil, "which", lambda name: None)
    monkeypatch.setenv("OPENPROSPECT_AI_PROVIDER", "claude-code")
    assert ai.provider_status()["status"] == "Not connected"
    with pytest.raises(RuntimeError, match="not installed"):
        ai._ask_cli("claude-code", "hello", "system")
