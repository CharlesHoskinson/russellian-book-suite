from scripts.sibling_skills import (
    russellian_style_root, book_knowledge_root, sibling_python,
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
