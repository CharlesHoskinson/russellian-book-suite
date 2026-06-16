import sys
from pathlib import Path

_repo_root = Path(__file__).resolve().parents[2]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

# NFR-5: activate the no-shadow-writes guard for metabook's own test run. The
# autouse fixture in ci/lint_no_shadow_writes.py only fires when registered as a
# plugin; previously it was wired into ci/ only, so it never protected real
# metabook code. The sys.path insert above makes the `ci` package importable
# from this skill's isolated test environment.
pytest_plugins = ["ci.lint_no_shadow_writes"]
