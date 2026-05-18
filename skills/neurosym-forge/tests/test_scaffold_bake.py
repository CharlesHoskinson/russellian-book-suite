"""REQ-SCAFFOLD-BAKE-001: a freshly scaffolded project passes `make ci`
end-to-end.

Catches sprint-5 bugs #1 (stale napi build), #2 (CLJS namespace
mismatch), #3 (CI module name drift), #5 (shadow-cljs .node path) at
once. Runs inside the nix shell (so the test inherits the same toolchain
as CI).
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SKILL_ROOT = REPO_ROOT / "skills" / "neurosym-forge"
TEMPLATE_ROOT = SKILL_ROOT / "assets" / "project-template"

# Skip on non-Linux: cargo can't produce .so anywhere else.
# Also skip when nbb isn't on PATH — that means we're not in the nix develop
# shell (the canonical gate is the new ci.yml from PR-2, which runs every
# job through `nix develop -c`).
pytestmark = pytest.mark.skipif(
    shutil.which("cargo") is None
    or shutil.which("nbb") is None
    or sys.platform != "linux",
    reason="scaffold-bake requires the nix develop shell (cargo + nbb + jdk)",
)


def _copy_smoke_rules(project_dir: Path) -> None:
    """Drop a minimal known-good ruleset into the baked project so its
    booklogic compiler has something to compile.
    """
    src = SKILL_ROOT / "tests" / "fixtures" / "bake-smoke-rules"
    dst = project_dir / "rules" / "booklogic"
    dst.mkdir(parents=True, exist_ok=True)
    for f in src.iterdir():
        shutil.copy(f, dst / f.name)


def _scaffold(tmp_path: Path, slug: str) -> Path:
    """Invoke the scaffolder to produce a baked project."""
    import sys
    sys.path.insert(0, str(SKILL_ROOT))
    from scripts.scaffold_project import scaffold_project  # type: ignore
    out_dir = tmp_path / slug
    scaffold_project(
        project_name="Bake Test",
        project_slug=slug,
        out_dir=out_dir,
        skill_root=SKILL_ROOT,
    )
    _copy_smoke_rules(out_dir)
    return out_dir


def test_scaffold_with_underscore_slug_passes_ci(tmp_path: Path) -> None:
    """The slug 'bake_test' (with underscore) is the tricky case — CLJS
    namespaces should render dashed ('bake-test.core'), file paths
    should stay underscored ('bake_test/core.cljs'). Sprint-5 burned
    here.
    """
    project = _scaffold(tmp_path, "bake_test")
    result = subprocess.run(
        ["make", "ci"], cwd=project, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, (
        f"baked project failed `make ci`:\n"
        f"--- stdout ---\n{result.stdout}\n"
        f"--- stderr ---\n{result.stderr}"
    )


def test_scaffold_with_simple_slug_passes_ci(tmp_path: Path) -> None:
    """Sanity: a single-word slug ('baketest') also passes."""
    project = _scaffold(tmp_path, "baketest")
    result = subprocess.run(
        ["make", "ci"], cwd=project, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, (
        f"baked project failed `make ci`:\n"
        f"--- stdout ---\n{result.stdout}\n"
        f"--- stderr ---\n{result.stderr}"
    )
