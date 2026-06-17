import sys
import types

import pytest

from scripts.sibling_skills import (
    russellian_style_root, book_knowledge_root, feynman_style_root,
    book_review_root, review_conductor_root, sibling_python,
    load_russellian_style_module,
)
import scripts.sibling_skills as ss


@pytest.mark.parametrize("resolver,skill_name", [
    (russellian_style_root, "russellian-style"),
    (book_knowledge_root, "book-knowledge"),
    (feynman_style_root, "feynman-style"),
    (book_review_root, "book-review"),
    (review_conductor_root, "review-conductor"),
])
def test_sibling_roots_resolve_repo_first_when_uninstalled(resolver, skill_name, monkeypatch, tmp_path):
    """Every sibling root must resolve the in-repo sibling when the installed
    ~/.claude/skills copy is absent (the P5.1 repo-first convention). Otherwise
    book-compose breaks on any box where the sibling isn't globally installed —
    which is exactly what broke the halmos gate (russellian_style_root was the
    last installed-only resolver)."""
    monkeypatch.setenv("USERPROFILE", str(tmp_path))  # empty ~/.claude/skills
    root = resolver()
    assert root.is_dir() and (root / "SKILL.md").is_file()
    assert root.name == skill_name
    assert (root.parent / "book-compose").is_dir()  # the repo sibling, next to us


@pytest.mark.parametrize("alias,ensure", [
    ("_russellian_style_scripts", "_ensure_rs_package"),
    ("_feynman_style_scripts", "_ensure_fs_package"),
    ("_book_review_scripts", "_ensure_br_package"),
    ("_review_conductor_scripts", "_ensure_rc_package"),
])
def test_ensure_package_rejects_mismatched_alias(alias, ensure, request):
    """The alias is process-global; if already registered for a DIFFERENT root,
    _ensure_* must fail loud rather than serve the wrong copy (the split-brain
    guard _ensure_bk_package has must hold for every loader)."""
    bogus = types.ModuleType(alias)
    bogus.__path__ = ["/nonexistent/elsewhere/scripts"]
    sys.modules[alias] = bogus
    request.addfinalizer(lambda: sys.modules.pop(alias, None))
    with pytest.raises(ss.SiblingNotFoundError, match="different"):
        getattr(ss, ensure)()


def test_russellian_style_root_exists():
    root = russellian_style_root()
    assert root.is_dir()
    assert (root / "SKILL.md").is_file()
    assert (root / "scripts" / "lint_hedges.py").is_file()


def test_book_knowledge_root_exists():
    root = book_knowledge_root()
    assert root.is_dir()
    assert (root / "SKILL.md").is_file()
    assert (root / "scripts" / "validate_shacl.py").is_file()


def test_sibling_python_uses_skill_venv():
    py = sibling_python(book_knowledge_root())
    assert py.exists()
    assert ".venv" in str(py)


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
    monkeypatch.setattr("scripts.sibling_skills.russellian_style_root", lambda: skill)
    monkeypatch.delitem(sys.modules, "_russellian_style_scripts", raising=False)
    request.addfinalizer(lambda: sys.modules.pop("_russellian_style_scripts", None))
    request.addfinalizer(lambda: sys.modules.pop("_russellian_style_scripts.boom", None))

    with pytest.raises(RuntimeError, match="boom"):
        load_russellian_style_module("boom")
    assert "_russellian_style_scripts.boom" not in sys.modules

    with pytest.raises(RuntimeError, match="boom"):
        load_russellian_style_module("boom")
