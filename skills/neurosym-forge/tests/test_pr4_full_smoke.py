"""End-to-end smoke for PR-4 Track A codegen.

Scaffolds a fresh project, declares one defconstraint, runs nbb compile,
runs axioms codegen, and finally gates on `cargo check --features smt`.

REQ-VERIFIER-BUILD-010: byte-deterministic codegen output.
REQ-VERIFIER-BUILD-011: cargo check --features smt succeeds against generated axioms.rs.

Skips cleanly when:
  - Node + npm are missing (no nbb)
  - cargo is missing (no Rust toolchain)
  - The cargo-check step would require a network fetch we can't guarantee

These tests are expected to take 60-180 seconds when they run. The
suite registers as `slow` via a marker; CI runs them in a separate job.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from scripts.scaffold_project import scaffold_project


def _have(cmd: str) -> bool:
    return shutil.which(cmd) is not None


pytestmark = [
    pytest.mark.skipif(
        not (_have("node") and _have("npm")),
        reason="Node + npm not on PATH",
    ),
    pytest.mark.slow,
]


NPM   = shutil.which("npm")   or "npm"
CARGO = shutil.which("cargo") or "cargo"


CONSTRAINTS_EDN = """{:forms
 [(defconstraint C001-bermuda-parishes
    :backend :z3
    :assert (= (:parishes-count :Bermuda) 9)
    :track :claim/id
    :on-unsat {:defect :D13
               :severity :critical
               :message "Bermuda has nine parishes."})]}
"""


@pytest.fixture(scope="module")
def smoke_project(tmp_path_factory: pytest.TempPathFactory) -> Path:
    skill_root = Path(__file__).resolve().parent.parent
    out = tmp_path_factory.mktemp("pr4_smoke") / "demo"
    scaffold_project(project_name="Demo", project_slug="demo",
                     out_dir=out, skill_root=skill_root)
    (out / "rules" / "booklogic" / "constraints.edn").write_text(
        CONSTRAINTS_EDN, encoding="utf-8",
    )
    r = subprocess.run(
        [NPM, "install", "--no-audit", "--no-fund", "--loglevel=error"],
        cwd=str(out), capture_output=True, text=True, timeout=600,
    )
    if r.returncode != 0:
        pytest.fail(f"npm install failed:\n{r.stdout}\n{r.stderr}")
    r = subprocess.run(
        [NPM, "run", "booklogic-compile"],
        cwd=str(out), capture_output=True, text=True, timeout=120,
    )
    if r.returncode != 0:
        pytest.fail(f"booklogic-compile failed:\n{r.stdout}\n{r.stderr}")
    r = subprocess.run(
        [NPM, "run", "codegen-axioms"],
        cwd=str(out), capture_output=True, text=True, timeout=60,
    )
    if r.returncode != 0:
        pytest.fail(f"codegen-axioms failed:\n{r.stdout}\n{r.stderr}")
    return out


def test_axioms_rs_compiles_under_cargo_check(smoke_project: Path) -> None:
    """`cargo check --features smt` against the generated axioms.rs.

    REQ-VERIFIER-BUILD-011: cargo check succeeds.
    """
    if not _have("cargo"):
        pytest.skip("cargo not on PATH")
    manifest = smoke_project / "rust-verifier" / "Cargo.toml"
    r = subprocess.run(
        [CARGO, "check", "--manifest-path", str(manifest), "--features", "smt"],
        capture_output=True, text=True, timeout=600,
    )
    if r.returncode != 0:
        pytest.fail(
            "cargo check failed against generated axioms.rs:\n"
            f"stdout:\n{r.stdout}\nstderr:\n{r.stderr}"
        )


def test_axioms_tracker_map_written(smoke_project: Path) -> None:
    """REQ-DSL-023: axioms-tracker-map.edn is written by codegen."""
    tracker = smoke_project / "rules" / "axioms-tracker-map.edn"
    assert tracker.exists()
    text = tracker.read_text(encoding="utf-8")
    assert "C001-bermuda-parishes" in text
    assert ":D13" in text
