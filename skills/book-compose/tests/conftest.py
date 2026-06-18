import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))


def _spacy_model_available() -> bool:
    try:
        import spacy

        spacy.load("en_core_web_sm")
        return True
    except Exception:
        return False


# Computed once at conftest import: loading the model per test would be wasteful.
_SPACY_MODEL_AVAILABLE = _spacy_model_available()


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "needs_spacy_model: test transitively loads the russellian-style / "
        "feynman-style NLP linters and requires the en_core_web_sm spaCy model; "
        "skipped when the model is not installed.",
    )


def pytest_collection_modifyitems(config, items):
    """Skip marked tests when the spaCy model is absent.

    Replaces the former hand-maintained filename list (which drifted: it missed
    test_halmos_gate.py and test_feynman_final_stage.py). The former
    ~/.claude sibling gate is gone — sibling resolution is repo-first, so those
    tests run from the in-repo siblings.
    """
    if _SPACY_MODEL_AVAILABLE:
        return
    skip = pytest.mark.skip(reason="en_core_web_sm spaCy model not installed")
    for item in items:
        if "needs_spacy_model" in item.keywords:
            item.add_marker(skip)
