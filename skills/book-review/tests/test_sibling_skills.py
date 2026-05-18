import pytest
from scripts.sibling_skills import (
    book_knowledge_root, russellian_style_root, book_compose_root,
    SiblingNotFoundError, load_book_knowledge_module, load_russellian_style_module,
)


def test_locates_all_three_siblings():
    for root_fn in (book_knowledge_root, russellian_style_root, book_compose_root):
        root = root_fn()
        assert root.is_dir()
        assert (root / "SKILL.md").is_file()


def test_load_book_knowledge_module_returns_workspace_module():
    mod = load_book_knowledge_module("workspace")
    assert hasattr(mod, "WorkspaceLayout")
    assert hasattr(mod, "init_workspace")


def test_load_russellian_style_module_returns_lint_common():
    mod = load_russellian_style_module("lint_common")
    assert hasattr(mod, "iter_sentences")
    assert hasattr(mod, "load_markdown")


def test_unknown_sibling_raises():
    from scripts.sibling_skills import _resolve
    with pytest.raises(SiblingNotFoundError):
        _resolve("nonexistent-skill")
