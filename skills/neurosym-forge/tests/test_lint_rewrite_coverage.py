# skills/neurosym-forge/tests/test_lint_rewrite_coverage.py
from __future__ import annotations

import pytest

pytestmark = pytest.mark.windows_canary

from pathlib import Path


from scripts._edn_reader import Keyword
from scripts._io import write_edn_file, file_checksum
from scripts.lint_rewrite_coverage import lint_rewrite_coverage

RULES_KEY = Keyword("rules")
CHECKSUMS_KEY = Keyword("checksums")
ID_KEY = Keyword("id")
KIND_KEY = Keyword("kind")
SORT_KEY = Keyword("sort")
NAME_KEY = Keyword("name")
LHS_KEY = Keyword("lhs")
RHS_KEY = Keyword("rhs")


def _make_rule(rid: str) -> dict:
    return {
        ID_KEY: rid,
        LHS_KEY: {KIND_KEY: Keyword("variable"), NAME_KEY: "?x", SORT_KEY: Keyword("int")},
        RHS_KEY: {KIND_KEY: Keyword("variable"), NAME_KEY: "?x", SORT_KEY: Keyword("int")},
    }


def _make_scaffold(root: Path, rules: dict, tests: list[str]) -> None:
    (root / "rules").mkdir(parents=True)
    (root / "tests" / "rules").mkdir(parents=True)
    checksums: dict = {}
    for fname, rule_list in rules.items():
        p = root / "rules" / fname
        write_edn_file(p, {RULES_KEY: rule_list})
        checksums[fname] = file_checksum(p)
    write_edn_file(root / "rules" / ".checksums.edn", {CHECKSUMS_KEY: checksums})
    for t in tests:
        (root / "tests" / "rules" / t).write_text("(deftest ...)\n", encoding="utf-8")


def test_clean_coverage(tmp_path: Path) -> None:
    _make_scaffold(
        tmp_path,
        rules={"seed.edn": [_make_rule("R001")]},
        tests=["test_R001.cljs"],
    )
    report = lint_rewrite_coverage(tmp_path)
    assert report.ok


def test_missing_fixture_flagged(tmp_path: Path) -> None:
    _make_scaffold(
        tmp_path,
        rules={"seed.edn": [_make_rule("R001")]},
        tests=[],
    )
    report = lint_rewrite_coverage(tmp_path)
    assert not report.ok
    assert any("R001" in e and "fixture" in e for e in report.errors)


def test_checksum_mismatch_flagged(tmp_path: Path) -> None:
    _make_scaffold(
        tmp_path,
        rules={"seed.edn": [_make_rule("R001")]},
        tests=["test_R001.cljs"],
    )
    (tmp_path / "rules" / "seed.edn").write_text("tampered\n", encoding="utf-8")
    report = lint_rewrite_coverage(tmp_path)
    assert not report.ok
    assert any("checksum" in e for e in report.errors)
