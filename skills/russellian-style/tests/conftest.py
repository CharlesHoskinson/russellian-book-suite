import os
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


def _is_ci(env: dict | None = None) -> bool:
    env = os.environ if env is None else env
    return env.get("CI", "").lower() in ("1", "true", "yes")


# The spaCy English model (en_core_web_sm) is required to exercise the linter
# suite. Locally it may be absent (developer convenience), in which case the
# model-dependent tests are skipped. In CI the model MUST be present, otherwise
# the entire linter suite would silently drop from collection and the job would
# go green without ever running a linter — a misleading pass. So in a CI context
# (CI=true, as set by GitHub Actions) a missing model is a hard error, not a
# silent skip. Run `python -m spacy download en_core_web_sm` after install.
if not _spacy_model_available():
    if _is_ci():
        raise RuntimeError(
            "spaCy model 'en_core_web_sm' is missing in a CI context. The "
            "russellian-style linter suite cannot run without it and would be "
            "silently skipped. Run `python -m spacy download en_core_web_sm` "
            "before pytest (see CI workflow)."
        )
    collect_ignore_glob = [
        "test_lint_*.py",
        "test_style_pass_*.py",
        "test_bitcoin_samples.py",
        "test_skill_integration.py",
        "unit/test_skill_api.py",
    ]
