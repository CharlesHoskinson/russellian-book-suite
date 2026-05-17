"""Unit tests for the booklogic Python adapter (consumer side).

All tests use the dev stub via BOOKLOGIC_BIN; no real booklogic CLI required.
"""
import os
import sys
from pathlib import Path

import pytest

from scripts.booklogic_adapter import (
    disputed_questions,
    reconcile_concepts,
    reachable_from_thesis,
    version,
    BooklogicError, BooklogicSchemaViolation, BooklogicTimeout,
    DisputedQuestion, CanonicalConcept, ReachabilityVerdict, BooklogicVersion,
)

STUB = Path(__file__).resolve().parents[1] / "fixtures" / "booklogic_stub.py"

@pytest.fixture(autouse=True)
def _use_stub(monkeypatch):
    monkeypatch.setenv("BOOKLOGIC_BIN", f"{sys.executable} {STUB}")

class _C:
    """Minimal candidate-shaped object for the adapter."""
    def __init__(self, id, extracted_concepts=None, embedding_score=0.0):
        self.id = id
        self.extracted_concepts = extracted_concepts or []
        self.embedding_score = embedding_score

class _Concept:
    def __init__(self, slug, title="", surface_forms=None, sources=None):
        self.slug = slug
        self.title = title
        self.surface_forms = surface_forms or []
        self.sources = sources or []

class _Tree:
    def __init__(self, chapter_id, nodes=None):
        self.chapter_id = chapter_id
        self.nodes = nodes or []

def test_version_returns_dataclass():
    v = version()
    assert isinstance(v, BooklogicVersion)
    assert v.booklogic_version == "0.0.0-stub"
    assert v.api_version == (0, 1)

def test_disputed_questions_empty():
    out = disputed_questions(claims=[])
    assert out == []
    assert isinstance(out, list)

def test_reconcile_concepts_empty():
    out = reconcile_concepts(concepts=[])
    assert out == []

def test_reachable_from_thesis_via_stub():
    cand = _C("arxiv:x", embedding_score=0.8)
    tree = _Tree("ch-01")
    v = reachable_from_thesis(cand, tree)
    assert isinstance(v, ReachabilityVerdict)
    assert v.reachable is True
    assert v.candidate_id == "arxiv:x"
    assert v.rule_trace == []

def test_failure_raises_booklogic_error(monkeypatch):
    # Point BOOKLOGIC_BIN at something that returns non-zero with no output
    if sys.platform == "win32":
        # On Windows, use a command guaranteed to fail
        monkeypatch.setenv("BOOKLOGIC_BIN", "cmd /c exit 99")
    else:
        monkeypatch.setenv("BOOKLOGIC_BIN", "false")
    with pytest.raises(BooklogicError):
        version()
