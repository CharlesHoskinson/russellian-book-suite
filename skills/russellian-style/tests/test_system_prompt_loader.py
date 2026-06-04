"""system_prompt_loader: returns the text of a mode-keyed system prompt."""
import pytest

pytestmark = pytest.mark.windows_canary

import pytest


def test_load_known_mode_returns_nonempty_text(tmp_path, monkeypatch):
    from scripts.system_prompt_loader import load
    prompts_dir = tmp_path / "system-prompts"
    prompts_dir.mkdir()
    (prompts_dir / "technical-exposition.md").write_text(
        "# Test prompt\n\nBody.\n", encoding="utf-8"
    )
    monkeypatch.setattr("scripts.system_prompt_loader.PROMPTS_DIR", prompts_dir)
    text = load("technical-exposition")
    assert "Test prompt" in text


def test_load_unknown_mode_raises():
    from scripts.system_prompt_loader import load
    with pytest.raises(ValueError):
        load("nonexistent-mode")


def test_load_known_mode_missing_file_raises(tmp_path, monkeypatch):
    from scripts.system_prompt_loader import load
    monkeypatch.setattr("scripts.system_prompt_loader.PROMPTS_DIR", tmp_path)
    with pytest.raises(FileNotFoundError):
        load("technical-exposition")


def test_default_mode_is_technical_exposition():
    from scripts.system_prompt_loader import DEFAULT_MODE
    assert DEFAULT_MODE == "technical-exposition"
