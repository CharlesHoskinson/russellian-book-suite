"""sibling_skills loads book-review modules under an alias namespace to avoid
the scripts/ package collision when three skills share the same package name.
"""
import pytest


def test_loads_persona_loader_from_book_review():
    from scripts.sibling_skills import load_book_review_module
    pl = load_book_review_module("persona_loader")
    assert hasattr(pl, "load_persona")
    assert hasattr(pl, "Persona")


def test_loads_dispatch_review_from_book_review():
    from scripts.sibling_skills import load_book_review_module
    dr = load_book_review_module("dispatch_review")
    assert hasattr(dr, "render_prompt")
    assert hasattr(dr, "parse_review_report")


def test_unknown_module_raises():
    from scripts.sibling_skills import load_book_review_module, SiblingNotFoundError
    with pytest.raises(SiblingNotFoundError):
        load_book_review_module("does_not_exist")
