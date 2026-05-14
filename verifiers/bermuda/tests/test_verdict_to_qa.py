from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts._edn_reader import Keyword
from scripts._io import write_edn_file
from scripts.verdict_to_qa import translate

_KW_VERSION = Keyword("version")
_KW_VERDICT = Keyword("verdict")
_KW_CORE = Keyword("core")
_KW_REASON = Keyword("reason")


def test_sat_emits_empty_defects(fixtures_dir: Path, tmp_path: Path) -> None:
    out = tmp_path / "verification-defects.json"
    translate(fixtures_dir / "verdict_sat.edn", out)
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["verdict"] == "sat"
    assert payload["core"] == []


def test_unsat_passes_core_through(fixtures_dir: Path, tmp_path: Path) -> None:
    out = tmp_path / "verification-defects.json"
    translate(fixtures_dir / "verdict_unsat.edn", out)
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["verdict"] == "unsat"
    assert "clm-2026-000008" in payload["core"]
    assert payload["explanation"]


def test_missing_input_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        translate(tmp_path / "nonexistent.edn", tmp_path / "out.json")


def test_unknown_verdict_is_logged_not_gated(tmp_path: Path) -> None:
    inp = tmp_path / "unknown.edn"
    write_edn_file(inp, {
        _KW_VERSION: 1,
        _KW_VERDICT: Keyword("unknown"),
        _KW_CORE: [],
        _KW_REASON: "smt timeout",
    })
    out = tmp_path / "verification-defects.json"
    translate(inp, out)
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["verdict"] == "unknown"
    assert payload["core"] == []
