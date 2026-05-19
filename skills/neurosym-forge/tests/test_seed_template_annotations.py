"""REQ-BOOKLOGIC-046: every .edn.tmpl seed under
assets/project-template/rules/booklogic/ has at least one comment, one
commented-out example form, and a 'common silent failures' block."""
from __future__ import annotations

from pathlib import Path

import pytest

SEED_DIR = (Path(__file__).resolve().parents[1]
            / "assets" / "project-template" / "rules" / "booklogic")

SEEDS = sorted(SEED_DIR.glob("*.edn.tmpl"))


def _has_example_form(text: str) -> bool:
    """A commented-out example starts with `;;` and contains a form head
    like (def... or (approx= ..."""
    for line in text.splitlines():
        stripped = line.lstrip()
        if not stripped.startswith(";"):
            continue
        if "(def" in stripped or "(approx=" in stripped or "(=" in stripped:
            return True
    return False


@pytest.mark.parametrize("seed", SEEDS, ids=lambda p: p.name)
def test_seed_has_comments(seed: Path):
    text = seed.read_text(encoding="utf-8")
    assert any(line.strip().startswith(";") for line in text.splitlines()), \
        f"{seed.name} has no comments — author has no guidance"


@pytest.mark.parametrize("seed", SEEDS, ids=lambda p: p.name)
def test_seed_has_example_form(seed: Path):
    text = seed.read_text(encoding="utf-8")
    assert _has_example_form(text), \
        f"{seed.name} has no commented-out example form"


@pytest.mark.parametrize("seed", SEEDS, ids=lambda p: p.name)
def test_seed_has_silent_failure_notes(seed: Path):
    text = seed.read_text(encoding="utf-8").lower()
    assert "silent" in text or "common" in text, \
        f"{seed.name} has no 'common silent failures' notes"


def test_all_seeds_present():
    expected = {"sorts.edn.tmpl", "predicates.edn.tmpl", "lifts.edn.tmpl",
                "rules.edn.tmpl", "constraints.edn.tmpl",
                "queries.edn.tmpl", "remedies.edn.tmpl",
                "induced-theory.prov.edn.tmpl"}
    actual = {p.name for p in SEEDS}
    assert actual == expected, f"missing seeds: {expected - actual}; extra: {actual - expected}"
