"""Skip-gate spaCy model tests when the model is absent (mirrors russellian-style)."""
import pytest


def _model_present() -> bool:
    try:
        import spacy
        spacy.load("en_core_web_sm")
        return True
    except Exception:
        return False


def pytest_collection_modifyitems(config, items):
    if _model_present():
        return
    skip = pytest.mark.skip(reason="en_core_web_sm not installed")
    for item in items:
        if "needs_model" in item.keywords:
            item.add_marker(skip)
