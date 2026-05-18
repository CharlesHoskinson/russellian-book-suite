"""Scaffolded entry-point for neurosym-forge codegen_axioms.

`scaffold_project.py` copies the canonical library alongside this shim
as `scripts/_codegen_axioms_lib.py` (and its EDN reader/writer deps).
Run as:

    python scripts/codegen_axioms.py
"""
from __future__ import annotations

import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent
_scripts_dir  = Path(__file__).resolve().parent
# Insert both project root and scripts dir so relative imports resolve.
for _p in (str(_project_root), str(_scripts_dir)):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def _import_run():
    # Primary: vendored copy placed by scaffold_project.py.
    # `scripts/` is a package (has __init__.py); project root is on sys.path.
    if (_scripts_dir / "_codegen_axioms_lib.py").exists():
        from scripts._codegen_axioms_lib import run as _run
        return _run

    # Secondary: look for neurosym-forge alongside this project (dev layout).
    candidates = [
        _project_root.parent / "neurosym-forge" / "scripts",
        _project_root.parent.parent / "skills" / "neurosym-forge" / "scripts",
        _project_root.parent.parent.parent / "skills" / "neurosym-forge" / "scripts",
    ]
    for c in candidates:
        if (c / "codegen_axioms.py").exists():
            sys.path.insert(0, str(c.parent))
            from scripts.codegen_axioms import run as _run
            return _run
    raise RuntimeError("cannot locate neurosym-forge.scripts.codegen_axioms")


def main() -> int:
    run = _import_run()
    run(_project_root)
    print(f"[codegen-axioms] {_project_root}/rust-verifier/src/axioms.rs regenerated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
