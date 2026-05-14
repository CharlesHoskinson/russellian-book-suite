# skills/neurosym-forge/tests/test_lint_rewrite_coverage.py
from __future__ import annotations

from pathlib import Path

import pytest

from scripts._io import write_json_as_edn, file_checksum
from scripts.lint_rewrite_coverage import lint_rewrite_coverage


def _make_scaffold(root: Path, rules: dict[str, list[dict]], tests: list[str]) -> None:
    (root / "rules").mkdir(parents=True)
    (root / "tests" / "rules").mkdir(parents=True)
    checksums: dict[str, str] = {}
    for fname, rule_list in rules.items():
        p = root / "rules" / fname
        write_json_as_edn(p, {"rules": rule_list})
        checksums[fname] = file_checksum(p)
    write_json_as_edn(root / "rules" / ".checksums.edn", {"checksums": checksums})
    for t in tests:
        (root / "tests" / "rules" / t).write_text("(deftest ...)\n", encoding="utf-8")


def test_clean_coverage(tmp_path: Path) -> None:
    _make_scaffold(
        tmp_path,
        rules={"seed.edn": [
            {"id": "R001",
             "lhs": {"kind": "variable", "name": "?x", "sort": ":int"},
             "rhs": {"kind": "variable", "name": "?x", "sort": ":int"}}
        ]},
        tests=["test_R001.cljs"],
    )
    report = lint_rewrite_coverage(tmp_path)
    assert report.ok


def test_missing_fixture_flagged(tmp_path: Path) -> None:
    _make_scaffold(
        tmp_path,
        rules={"seed.edn": [
            {"id": "R001",
             "lhs": {"kind": "variable", "name": "?x", "sort": ":int"},
             "rhs": {"kind": "variable", "name": "?x", "sort": ":int"}}
        ]},
        tests=[],
    )
    report = lint_rewrite_coverage(tmp_path)
    assert not report.ok
    assert any("R001" in e and "fixture" in e for e in report.errors)


def test_checksum_mismatch_flagged(tmp_path: Path) -> None:
    _make_scaffold(
        tmp_path,
        rules={"seed.edn": [
            {"id": "R001",
             "lhs": {"kind": "variable", "name": "?x", "sort": ":int"},
             "rhs": {"kind": "variable", "name": "?x", "sort": ":int"}}
        ]},
        tests=["test_R001.cljs"],
    )
    (tmp_path / "rules" / "seed.edn").write_text("tampered\n", encoding="utf-8")
    report = lint_rewrite_coverage(tmp_path)
    assert not report.ok
    assert any("checksum" in e for e in report.errors)
