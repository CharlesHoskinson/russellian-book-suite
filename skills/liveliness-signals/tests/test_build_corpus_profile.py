# skills/liveliness-signals/tests/test_build_corpus_profile.py
"""Cites REQ-LIVE-001, REQ-LIVE-002 (per-register, deterministic, stats-only)."""
import pytest
pytestmark = pytest.mark.windows_canary
from scripts.build_corpus_profile import build_profile


def _rows(reg, n, text):
    return [{"id": f"{reg}-{i}", "text": text, "register": reg} for i in range(n)]


@pytest.mark.needs_model
def test_build_profile_per_register_and_fallback():
    rows = _rows("polemic", 6, "You must act. The time is now. We will not wait.") \
         + _rows("technical-exposition", 2, "The system maps inputs to outputs deterministically.")
    p = build_profile(rows, min_per_register=5)
    assert set(p["registers"]) == {"technical-exposition", "narrative-editorial", "polemic"}
    assert p["registers"]["polemic"]["fallback"] is False
    # technical has 2 < 5 -> fallback to global
    assert p["registers"]["technical-exposition"]["fallback"] is True
    assert "no source prose" in p["source_policy"].lower()
    assert "cadence" in p["global"] and "diction" in p["global"]


@pytest.mark.needs_model
def test_build_profile_is_deterministic_and_storeless():
    rows = _rows("polemic", 6, "You must act. The time is now. We will not wait.")
    a = build_profile(rows)
    b = build_profile(rows)
    drop = lambda d: {k: v for k, v in d.items() if k != "built_at"}
    assert drop(a) == drop(b)
    blob = str(a)
    assert "You must act" not in blob  # no verbatim prose
