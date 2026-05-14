# skills/neurosym-forge/tests/test_lint_atomspace.py
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts._io import read_edn_as_json, write_json_as_edn
from scripts.lint_atomspace import lint_atomspace, LintReport


def test_clean_atomspace_passes(fixtures_dir: Path) -> None:
    payload = read_edn_as_json(fixtures_dir / "seed_atomspace.edn")
    report = lint_atomspace(payload)
    assert report.ok
    assert report.errors == []


def test_missing_sort_flagged(tmp_path: Path) -> None:
    payload = {"version": 1, "sorts": [":int"], "rules": [],
               "atoms": [{"kind": "symbol", "name": ":foo"}]}
    report = lint_atomspace(payload)
    assert not report.ok
    assert any("missing 'sort'" in e for e in report.errors)


def test_unknown_sort_reference_flagged() -> None:
    payload = {"version": 1, "sorts": [":int"], "rules": [],
               "atoms": [{"kind": "symbol", "name": ":foo", "sort": ":unknown"}]}
    report = lint_atomspace(payload)
    assert not report.ok
    assert any("unknown sort" in e for e in report.errors)


def test_rule_with_invalid_balance_flagged() -> None:
    payload = {"version": 1, "sorts": [":real"], "atoms": [],
               "rules": [{
                   "id": "R002",
                   "lhs": {"kind": "expression", "sort": ":real",
                           "head": {"kind": "symbol", "name": ":f",
                                    "sort": {"kind": "fn", "args": [":real"], "ret": ":real"}},
                           "args": [{"kind": "variable", "name": "?x", "sort": ":real"}]},
                   "rhs": {"kind": "variable", "name": "?y", "sort": ":real"}
               }]}
    report = lint_atomspace(payload)
    assert not report.ok
    assert any("R002" in e and "unbound" in e for e in report.errors)


def test_cli_returns_nonzero_on_errors(tmp_path: Path) -> None:
    import subprocess
    import sys
    bad = tmp_path / "bad.edn"
    write_json_as_edn(bad, {"version": 1, "sorts": [":int"], "rules": [],
                            "atoms": [{"kind": "symbol", "name": ":foo"}]})
    result = subprocess.run(
        [sys.executable, "-m", "scripts.lint_atomspace", str(bad)],
        capture_output=True, text=True, cwd=str(Path(__file__).resolve().parent.parent),
    )
    assert result.returncode == 1
    assert "missing 'sort'" in result.stdout or "missing 'sort'" in result.stderr
