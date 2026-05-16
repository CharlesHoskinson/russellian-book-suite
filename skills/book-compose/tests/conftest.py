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


# Skip tests that invoke russellian-style linters when the spaCy English
# model is missing. Run `python -m spacy download en_core_web_sm` once
# after install to enable them.
if not _spacy_model_available():
    collect_ignore_glob = [
        "test_chapter_contract_check.py",
        "test_persona_metrics.py",
        "test_skill_integration.py",
    ]
