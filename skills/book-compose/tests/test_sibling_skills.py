import sys

import pytest

from scripts.sibling_skills import (
    russellian_style_root, book_knowledge_root, sibling_python,
    load_russellian_style_module,
)


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
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.delitem(sys.modules, "_russellian_style_scripts", raising=False)
    request.addfinalizer(lambda: sys.modules.pop("_russellian_style_scripts", None))
    request.addfinalizer(lambda: sys.modules.pop("_russellian_style_scripts.boom", None))

    with pytest.raises(RuntimeError, match="boom"):
        load_russellian_style_module("boom")
    assert "_russellian_style_scripts.boom" not in sys.modules

    with pytest.raises(RuntimeError, match="boom"):
        load_russellian_style_module("boom")
