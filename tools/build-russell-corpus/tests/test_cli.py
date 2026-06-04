"""CLI dispatch tests — the extract/cross-check subcommands must run a real LLM
caller, not the abort-on-call _stub_llm default (finding cli-llm-unwired-stub)."""
import sys
from pathlib import Path

import pytest

import scripts.cli as cli


def test_extract_subcommand_uses_live_caller_not_stub(monkeypatch, tmp_path):
    """`main()` dispatching the extract subcommand must invoke a real caller, so the
    stage runs instead of aborting with SystemExit('No LLM caller wired')."""
    captured = {}

    def fake_extract_stage(**kwargs):
        captured["llm_call"] = kwargs["llm_call"]

    monkeypatch.setattr(
        "scripts.extract_candidates.extract_candidates", fake_extract_stage
    )
    argv = [
        "build-russell-corpus", "extract",
        "--source", str(tmp_path / "s.html"),
        "--source-id", "problems",
        "--source-url", "u",
        "--vocabulary", str(tmp_path / "v.json"),
        "--prompt", str(tmp_path / "p.md"),
        "--out", str(tmp_path / "c.jsonl"),
    ]
    monkeypatch.setattr(sys, "argv", argv)
    cli.main()
    # The wired caller must be the real live caller, not an abort stub / None.
    from scripts.live_llm import extract_llm
    assert captured["llm_call"] is extract_llm


def test_cross_check_subcommand_uses_live_caller_not_stub(monkeypatch, tmp_path):
    captured = {}

    def fake_cross_check_stage(**kwargs):
        captured["llm_call"] = kwargs["llm_call"]

    monkeypatch.setattr(
        "scripts.cross_check.run_cross_check_batch", fake_cross_check_stage
    )
    argv = [
        "build-russell-corpus", "cross-check",
        "--passed-sentinel", str(tmp_path / "ps.jsonl"),
        "--rejected", str(tmp_path / "r.jsonl"),
        "--verified", str(tmp_path / "v.jsonl"),
        "--vocabulary", str(tmp_path / "voc.json"),
    ]
    monkeypatch.setattr(sys, "argv", argv)
    cli.main()
    from scripts.live_llm import cross_check_llm
    assert captured["llm_call"] is cross_check_llm


def test_backfill_locators_subcommand_dispatches(monkeypatch, tmp_path):
    """The backfill-locators subcommand routes to backfill_content_locators with the
    index/source-cache paths (finding sentinel-seed-entries-have-no-locator)."""
    captured = {}

    def fake_backfill(**kwargs):
        captured.update(kwargs)
        return 0

    monkeypatch.setattr(
        "scripts.backfill_locators.backfill_content_locators", fake_backfill
    )
    argv = [
        "build-russell-corpus", "backfill-locators",
        "--index", str(tmp_path / "index.json"),
        "--source-cache", str(tmp_path / "cache"),
    ]
    monkeypatch.setattr(sys, "argv", argv)
    cli.main()
    assert captured["index_path"] == tmp_path / "index.json"
    assert captured["source_cache_dir"] == tmp_path / "cache"
