"""REQ-EDN-051: EDN list (paren) vs vector (bracket) round-trip faithfully."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts._edn_reader import read_edn, EdnList, EdnVector
from scripts._edn_writer import write_edn


def test_paren_round_trip_preserves_list():
    src = "(approx= 1 2 :tolerance 0.03)"
    parsed = read_edn(src)
    assert isinstance(parsed, EdnList), f"expected EdnList, got {type(parsed).__name__}"
    emitted = write_edn(parsed)
    assert emitted.startswith("(") and emitted.endswith(")"), (
        f"emitted {emitted!r} should be a paren list"
    )
    re_parsed = read_edn(emitted)
    assert isinstance(re_parsed, EdnList)


def test_bracket_round_trip_preserves_vector():
    src = "[1 2 3]"
    parsed = read_edn(src)
    assert isinstance(parsed, EdnVector), f"expected EdnVector, got {type(parsed).__name__}"
    emitted = write_edn(parsed)
    assert emitted.startswith("[") and emitted.endswith("]"), (
        f"emitted {emitted!r} should be a bracket vector"
    )
    re_parsed = read_edn(emitted)
    assert isinstance(re_parsed, EdnVector)
