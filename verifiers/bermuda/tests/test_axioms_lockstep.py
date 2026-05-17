"""Check that the checked-in rust-verifier/src/axioms.rs is byte-identical to
the BookLogic compiler's regenerated output. If a contributor edits
constraints.edn but forgets to rerun the compiler, this test catches it.

REQ-VERIFIER-BUILD-030, REQ-VERIFIER-BUILD-031"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

try:
    import yaml
    _YAML_OK = True
except ImportError:
    _YAML_OK = False

BERMUDA_ROOT = Path(__file__).resolve().parents[1]
AXIOMS_RS = BERMUDA_ROOT / "rust-verifier" / "src" / "axioms.rs"


@pytest.fixture()
def regenerated_axioms(tmp_path: Path) -> str:
    """Run `npm run booklogic-compile` + codegen_axioms in a copy of the
    project and return the regenerated axioms.rs content. Skips if nbb
    or npx is unavailable."""
    if shutil.which("npx") is None:
        pytest.skip("npx not available; cannot regenerate axioms.rs")
    work = tmp_path / "bermuda"
    shutil.copytree(BERMUDA_ROOT, work, ignore=shutil.ignore_patterns(
        "node_modules", "target", "dist", ".venv", "__pycache__", "work"
    ))
    # Reuse the repo's node_modules if present to skip a 60-second npm install.
    src_nm = BERMUDA_ROOT / "node_modules"
    if src_nm.exists():
        try:
            (work / "node_modules").symlink_to(src_nm, target_is_directory=True)
        except OSError:
            # Windows may lack the symlink privilege; fall back to npm install.
            subprocess.run(["npm", "install"], cwd=str(work), check=True,
                           shell=sys.platform == "win32", capture_output=True)
    else:
        subprocess.run(["npm", "install"], cwd=str(work), check=True,
                       shell=sys.platform == "win32", capture_output=True)
    # Step 1: nbb booklogic-compile → intermediate constraints.edn
    _shell = sys.platform == "win32"
    result = subprocess.run(
        ["npx", "nbb", "-m", "bermuda.booklogic", "."],
        cwd=str(work), check=True, capture_output=True, text=True,
        shell=_shell,
    )
    # Step 2: Python codegen_axioms → axioms.rs
    neurosym_scripts = BERMUDA_ROOT.parents[1] / "skills" / "neurosym-forge" / "scripts"
    sys.path.insert(0, str(neurosym_scripts.parent))
    from scripts.codegen_axioms import run as codegen_run
    codegen_run(work)
    regenerated = work / "rust-verifier" / "src" / "axioms.rs"
    assert regenerated.exists(), (
        f"codegen did not write axioms.rs (nbb stdout: {result.stdout})"
    )
    return regenerated.read_text(encoding="utf-8")


def test_axioms_rs_committed_is_in_sync(regenerated_axioms: str) -> None:
    """The checked-in axioms.rs must be byte-identical to the compiler's output."""
    on_disk = AXIOMS_RS.read_text(encoding="utf-8")
    assert on_disk == regenerated_axioms, (
        "axioms.rs is out of sync with constraints.edn. "
        "Run `npm run booklogic-compile` + codegen_axioms in verifiers/bermuda/ "
        "and commit the result."
    )


def test_axioms_rs_asserts_canonical_parishes() -> None:
    text = AXIOMS_RS.read_text(encoding="utf-8")
    assert "parishes-count_Bermuda" in text or "parishes_count_Bermuda" in text
    assert "9" in text


def test_axioms_rs_uses_assert_and_track() -> None:
    text = AXIOMS_RS.read_text(encoding="utf-8")
    # Every constraint must be tracked so the unsat core points back.
    assert text.count("assert_and_track") >= 9, \
        "expected ≥9 tracked assertions (5 canonical + 4 quantitative)"


def test_canonical_rs_is_gone() -> None:
    p = BERMUDA_ROOT / "rust-verifier" / "src" / "canonical.rs"
    assert not p.exists(), "canonical.rs must be deleted; axioms.rs supersedes it"


def test_lib_rs_declares_axioms_mod_not_canonical() -> None:
    text = (BERMUDA_ROOT / "rust-verifier" / "src" / "lib.rs").read_text(encoding="utf-8")
    assert "mod axioms" in text, "lib.rs must declare `mod axioms;`"
    assert "mod canonical" not in text, "lib.rs must not declare `mod canonical;`"


@pytest.mark.skipif(not _YAML_OK, reason="pyyaml not installed")
def test_ci_yaml_has_bermuda_z3_jobs() -> None:
    ci = yaml.safe_load(
        (BERMUDA_ROOT.parents[1] / ".github" / "workflows" / "ci.yml").read_text(
            encoding="utf-8"
        )
    )
    jobs = ci.get("jobs", {})
    assert "bermuda-z3-build" in jobs, "bermuda-z3-build job missing from ci.yml"
    assert "bermuda-z3-verify" in jobs, "bermuda-z3-verify job missing from ci.yml"
    assert jobs["bermuda-z3-build"].get("runs-on") == "ubuntu-latest"
    assert jobs["bermuda-z3-verify"].get("runs-on") == "ubuntu-latest"
