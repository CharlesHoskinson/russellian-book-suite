import subprocess
import pytest

from scripts.adapters import AdapterError, ytdlp_runner, scrapling_fetch, make_anthropic_llm_call


def test_ytdlp_runner_passes_timeout(monkeypatch):
    captured = {}
    def fake_run(args, **kwargs):
        captured.update(kwargs)
        return subprocess.CompletedProcess(args, 0, "", "")
    monkeypatch.setattr(subprocess, "run", fake_run)
    ytdlp_runner(["yt-dlp", "--version"], timeout=123.0)
    assert captured["timeout"] == 123.0
    assert captured["encoding"] == "utf-8"


def test_ytdlp_runner_timeout_raises_adapter_error(monkeypatch):
    def fake_run(args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args, timeout=kwargs.get("timeout"))
    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(AdapterError):
        ytdlp_runner(["yt-dlp", "x"], timeout=1.0)


def test_scrapling_fetch_passes_timeout(monkeypatch):
    captured = {}
    def fake_run(args, **kwargs):
        captured.update(kwargs)
        return subprocess.CompletedProcess(args, 0, b"<html>", b"")
    monkeypatch.setattr(subprocess, "run", fake_run)
    out = scrapling_fetch("https://x", timeout=42.0)
    assert captured["timeout"] == 42.0
    assert out == "<html>"


def test_scrapling_fetch_timeout_raises_adapter_error(monkeypatch):
    def fake_run(args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args, timeout=kwargs.get("timeout"))
    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(AdapterError):
        scrapling_fetch("https://x", timeout=1.0)


def test_make_anthropic_llm_call_uses_injected_client():
    class FakeBlock:
        type = "text"
        text = '{"rhetorical_move": "m", "tags": ["a"]}'
    class FakeResp:
        content = [FakeBlock()]
    class FakeMessages:
        def create(self, **kwargs):
            assert kwargs["model"] == "claude-opus-4-8"
            assert kwargs["messages"][0]["content"] == "PROMPT"
            return FakeResp()
    class FakeClient:
        messages = FakeMessages()
    call = make_anthropic_llm_call(client=FakeClient())
    assert call("PROMPT") == '{"rhetorical_move": "m", "tags": ["a"]}'
