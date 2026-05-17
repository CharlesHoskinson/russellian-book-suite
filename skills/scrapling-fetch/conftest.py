import sys
from pathlib import Path

# Add the russellian-book-suite root to sys.path so sibling_skills is importable
# (the editable install maps the package directory correctly this way)
_repo_root = Path(__file__).resolve().parents[2]  # .../russellian-book-suite
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))
