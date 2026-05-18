"""REQ-EDN-044: golden EDN files round-trip stably through read_edn -> write_edn -> read_edn."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts._edn_reader import read_edn
from scripts._edn_writer import write_edn

GOLDEN_FILES = sorted((ROOT / "tests" / "golden").glob("*.edn"))


@pytest.mark.parametrize("golden", GOLDEN_FILES, ids=lambda p: p.name)
def test_round_trip_stable(golden: Path):
    raw = golden.read_text(encoding="utf-8")
    parsed_once = read_edn(raw)
    emitted_once = write_edn(parsed_once)
    parsed_twice = read_edn(emitted_once)
    emitted_twice = write_edn(parsed_twice)
    assert emitted_once == emitted_twice, (
        f"round-trip not stable for {golden.name}\n"
        f"once:\n{emitted_once}\n"
        f"twice:\n{emitted_twice}"
    )
