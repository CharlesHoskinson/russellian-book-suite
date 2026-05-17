# skills/neurosym-forge/tests/test_bermuda_rules_edn.py
"""Asserts Bermuda's static rule files are real EDN (not JSON-stamped).

After PR-1 the EDN reader returns Keyword instances for keyword tokens. If
seed.edn or grounded.edn still hold JSON-quoted strings like ":int", the
parser produces str values and these assertions fail.

REQ-EDN-010, REQ-EDN-011, REQ-BERMUDA-RULES-001, REQ-BERMUDA-RULES-002
"""
from __future__ import annotations

from pathlib import Path

from scripts._edn_reader import Keyword
from scripts._io import read_edn_file, write_edn_file

# Path to verifiers/bermuda/rules from skills/neurosym-forge/tests
_RULES_DIR = (
    Path(__file__).resolve().parents[3]
    / "verifiers"
    / "bermuda"
    / "rules"
)


def test_seed_edn_has_keyword_keys() -> None:
    """REQ-EDN-010: seed.edn top-level keys are EDN keywords."""
    payload = read_edn_file(_RULES_DIR / "seed.edn")
    assert Keyword("version") in payload
    assert Keyword("sorts") in payload
    assert Keyword("rules") in payload
    assert Keyword("atoms") in payload


def test_seed_edn_sorts_are_keywords() -> None:
    """REQ-EDN-011: seed.edn :sorts vector contains keyword elements."""
    payload = read_edn_file(_RULES_DIR / "seed.edn")
    sorts = payload[Keyword("sorts")]
    assert sorts == [
        Keyword("int"),
        Keyword("real"),
        Keyword("bool"),
        Keyword("entity"),
        Keyword("formula"),
        Keyword("verdict"),
        Keyword("rule"),
        Keyword("atom"),
    ]


def test_seed_edn_round_trips(tmp_path: Path) -> None:
    """REQ-EDN-010: seed.edn round-trips through write_edn_file / read_edn_file."""
    original = read_edn_file(_RULES_DIR / "seed.edn")
    scratch = tmp_path / "seed.edn"
    write_edn_file(scratch, original)
    reparsed = read_edn_file(scratch)
    assert reparsed == original


def test_grounded_edn_has_keyword_keys() -> None:
    """REQ-BERMUDA-RULES-001: grounded.edn top-level keys are EDN keywords."""
    payload = read_edn_file(_RULES_DIR / "grounded.edn")
    assert Keyword("version") in payload
    assert Keyword("grounded") in payload
    entries = payload[Keyword("grounded")]
    assert len(entries) == 3


def test_grounded_edn_entry_shape() -> None:
    """REQ-BERMUDA-RULES-002: grounded.edn first entry has correct keyword structure."""
    payload = read_edn_file(_RULES_DIR / "grounded.edn")
    z3 = payload[Keyword("grounded")][0]
    assert z3[Keyword("kind")] == Keyword("grounded")
    assert z3[Keyword("name")] == Keyword("z3-check-all")
    sort = z3[Keyword("sort")]
    assert sort[Keyword("kind")] == Keyword("fn")
    assert sort[Keyword("args")] == [Keyword("atom")]
    assert sort[Keyword("ret")] == Keyword("verdict")
    grounded_body = z3[Keyword("grounded")]
    assert grounded_body[Keyword("lib")] == "z3"
    assert grounded_body[Keyword("fn")] == "verify_formulas"
    assert grounded_body[Keyword("napi")] is True


def test_grounded_edn_round_trips(tmp_path: Path) -> None:
    """REQ-BERMUDA-RULES-001: grounded.edn round-trips through write/read."""
    original = read_edn_file(_RULES_DIR / "grounded.edn")
    scratch = tmp_path / "grounded.edn"
    write_edn_file(scratch, original)
    reparsed = read_edn_file(scratch)
    assert reparsed == original
