import sys

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


def test_failed_exec_does_not_cache_partial_module(tmp_path, monkeypatch, request):
    # A module whose body raises must not stay in sys.modules: the second
    # load would otherwise return the half-executed module and surface as a
    # misleading "cannot import name ..." instead of the original error.
    skill = tmp_path / ".claude" / "skills" / "russellian-style"
    (skill / "scripts").mkdir(parents=True)
    (skill / "SKILL.md").write_text("stub", encoding="utf-8")
    (skill / "scripts" / "boom.py").write_text(
        "before = 1\nraise RuntimeError('boom')\n", encoding="utf-8"
    )
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.delitem(sys.modules, "_russellian_style_scripts", raising=False)
    request.addfinalizer(lambda: sys.modules.pop("_russellian_style_scripts", None))
    request.addfinalizer(lambda: sys.modules.pop("_russellian_style_scripts.boom", None))

    with pytest.raises(RuntimeError, match="boom"):
        load_russellian_style_module("boom")
    assert "_russellian_style_scripts.boom" not in sys.modules

    with pytest.raises(RuntimeError, match="boom"):
        load_russellian_style_module("boom")
