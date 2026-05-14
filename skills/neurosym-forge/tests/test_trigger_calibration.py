# skills/neurosym-forge/tests/test_trigger_calibration.py
"""Smoke-test that SKILL.md trigger phrases roughly match expected prompts.

This is a heuristic check — the actual trigger is Claude's judgement at
SKILL.md load time. We assert that every positive case has at least one
substring overlap with the SKILL.md description, and no negative case does.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

SKILL_ROOT = Path(__file__).resolve().parent.parent
SKILL_MD = SKILL_ROOT / "SKILL.md"
TRIGGER_PATH = SKILL_ROOT / "tests" / "trigger_tests.yaml"


def _description() -> str:
    text = SKILL_MD.read_text(encoding="utf-8")
    m = re.search(r"^description:\s*(.+?)(?:\nlicense:|\nmetadata:)", text, re.DOTALL | re.MULTILINE)
    assert m
    return m.group(1).lower()


def _tokens(s: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9-+]+", s.lower()) if len(w) >= 2}


def _matches(prompt: str, description: str) -> bool:
    prompt_tokens = _tokens(prompt)
    desc_tokens = _tokens(description)
    return bool(prompt_tokens & desc_tokens & {
        "scaffold", "verifier", "rule", "z3",
        "ground", "grounded", "atomspace", "cljs",
        "fol", "smt", "egraph", "e-graph", "datalog",
        "metta", "metta-style",
        "neurosymbolic", "neurosym",
    })


@pytest.fixture(scope="module")
def cases() -> dict:
    return yaml.safe_load(TRIGGER_PATH.read_text(encoding="utf-8"))


def test_positive_cases_overlap_description(cases: dict) -> None:
    desc = _description()
    misses = [p for p in cases["positive"] if not _matches(p, desc)]
    assert not misses, f"positive prompts missing trigger overlap: {misses}"


def test_negative_cases_dont_overlap(cases: dict) -> None:
    desc = _description()
    hits = [p for p in cases["negative"] if _matches(p, desc)]
    assert not hits, f"negative prompts unexpectedly match triggers: {hits}"
