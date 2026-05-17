import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))


def _spacy_model_available() -> bool:
    try:
        import spacy
        spacy.load("en_core_web_sm")
        return True
    except Exception:
        return False


def _sibling_skills_installed() -> bool:
    import os
    home = Path(os.environ.get("USERPROFILE") or os.path.expanduser("~"))
    return (home / ".claude" / "skills" / "book-knowledge").is_dir()


# Skip tests when their prerequisites aren't installed in this environment.
# Run `python -m spacy download en_core_web_sm` for the linter tests, and
# ensure ~/.claude/skills/{book-knowledge,russellian-style} exist for the
# sibling-skill tests.
_skip = []
if not _spacy_model_available():
    _skip += [
        "test_chapter_contract_check.py",
        "test_persona_metrics.py",
        "test_skill_integration.py",
    ]
if not _sibling_skills_installed():
    _skip += [
        "test_preflight.py",
        "test_query_chapter_evidence.py",
        "test_sibling_skills.py",
    ]
collect_ignore_glob = _skip
