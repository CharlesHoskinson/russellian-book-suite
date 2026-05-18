# skills/neurosym-forge/tests/test_lint_atomspace.py
from __future__ import annotations

from pathlib import Path


from scripts._edn_reader import Keyword
from scripts._io import read_edn_file, write_edn_file
from scripts.lint_atomspace import lint_atomspace

SORTS_KEY = Keyword("sorts")
ATOMS_KEY = Keyword("atoms")
RULES_KEY = Keyword("rules")
KIND_KEY = Keyword("kind")
SORT_KEY = Keyword("sort")
NAME_KEY = Keyword("name")


def test_clean_atomspace_passes(fixtures_dir: Path) -> None:
    payload = read_edn_file(fixtures_dir / "seed_atomspace.edn")
    report = lint_atomspace(payload)
    assert report.ok
    assert report.errors == []


def test_missing_sort_flagged(tmp_path: Path) -> None:
    payload = {
        Keyword("version"): 1,
        SORTS_KEY: [Keyword("int")],
        RULES_KEY: [],
        ATOMS_KEY: [{KIND_KEY: Keyword("symbol"), NAME_KEY: Keyword("foo")}],
    }
    report = lint_atomspace(payload)
    assert not report.ok
    assert any("missing 'sort'" in e for e in report.errors)


def test_unknown_sort_reference_flagged() -> None:
    payload = {
        Keyword("version"): 1,
        SORTS_KEY: [Keyword("int")],
        RULES_KEY: [],
        ATOMS_KEY: [{KIND_KEY: Keyword("symbol"), NAME_KEY: Keyword("foo"),
                     SORT_KEY: Keyword("unknown")}],
    }
    report = lint_atomspace(payload)
    assert not report.ok
    assert any("unknown sort" in e for e in report.errors)


def test_rule_with_invalid_balance_flagged() -> None:
    payload = {
        Keyword("version"): 1,
        SORTS_KEY: [Keyword("real")],
        ATOMS_KEY: [],
        RULES_KEY: [{
            Keyword("id"): "R002",
            Keyword("lhs"): {KIND_KEY: Keyword("expression"), SORT_KEY: Keyword("real"),
                             Keyword("head"): {KIND_KEY: Keyword("symbol"), NAME_KEY: Keyword("f"),
                                               SORT_KEY: {Keyword("kind"): Keyword("fn"),
                                                          Keyword("args"): [Keyword("real")],
                                                          Keyword("ret"): Keyword("real")}},
                             Keyword("args"): [{KIND_KEY: Keyword("variable"),
                                               NAME_KEY: "?x", SORT_KEY: Keyword("real")}]},
            Keyword("rhs"): {KIND_KEY: Keyword("variable"), NAME_KEY: "?y",
                             SORT_KEY: Keyword("real")},
        }],
    }
    report = lint_atomspace(payload)
    assert not report.ok
    assert any("R002" in e and "unbound" in e for e in report.errors)


def test_null_sorts_flagged() -> None:
    payload = {SORTS_KEY: None, RULES_KEY: [], ATOMS_KEY: []}
    report = lint_atomspace(payload)
    assert not report.ok
    assert any("must be a list" in e for e in report.errors)


def test_cli_returns_nonzero_on_errors(tmp_path: Path) -> None:
    import subprocess
    import sys
    bad = tmp_path / "bad.edn"
    write_edn_file(bad, {
        Keyword("version"): 1,
        SORTS_KEY: [Keyword("int")],
        RULES_KEY: [],
        ATOMS_KEY: [{KIND_KEY: Keyword("symbol"), NAME_KEY: Keyword("foo")}],
    })
    result = subprocess.run(
        [sys.executable, "-m", "scripts.lint_atomspace", str(bad)],
        capture_output=True, text=True, cwd=str(Path(__file__).resolve().parent.parent),
    )
    assert result.returncode == 1
    assert "missing 'sort'" in result.stdout or "missing 'sort'" in result.stderr
