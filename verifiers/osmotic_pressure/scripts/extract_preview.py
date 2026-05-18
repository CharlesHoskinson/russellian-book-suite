"""Per-project shim that imports the canonical library."""
from __future__ import annotations

import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent
_scripts_dir = Path(__file__).resolve().parent
for _p in (str(_project_root), str(_scripts_dir)):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def _import_lib():
    if (_scripts_dir / "_extract_preview_lib.py").exists():
        from scripts._extract_preview_lib import main
        return main
    forge = _project_root.parent.parent / "skills" / "neurosym-forge" / "scripts"
    if (forge / "_extract_preview_lib.py").exists():
        sys.path.insert(0, str(forge.parent))
        from scripts._extract_preview_lib import main
        return main
    raise RuntimeError("cannot locate _extract_preview_lib.py")


if __name__ == "__main__":
    raise SystemExit(_import_lib()(sys.argv[1:]))
