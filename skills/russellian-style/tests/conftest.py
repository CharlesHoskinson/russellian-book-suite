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


# Skip linter tests when the spaCy English model is missing. Run
# `python -m spacy download en_core_web_sm` once after install to enable them.
if not _spacy_model_available():
    collect_ignore_glob = [
        "test_lint_*.py",
        "test_style_pass_*.py",
        "test_bitcoin_samples.py",
        "test_skill_integration.py",
    ]
