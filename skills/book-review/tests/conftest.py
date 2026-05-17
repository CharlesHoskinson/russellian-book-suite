import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))


def _sibling_skills_installed() -> bool:
    import os
    home = Path(os.environ.get("USERPROFILE") or os.path.expanduser("~"))
    return (home / ".claude" / "skills" / "book-knowledge").is_dir()


# Skip sibling-skill tests when the siblings aren't installed.
if not _sibling_skills_installed():
    collect_ignore_glob = ["test_sibling_skills.py"]
