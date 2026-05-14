from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from scripts._io import read_edn_as_json
from scripts.scaffold_project import scaffold_project


def test_emits_expected_files(tmp_project_root: Path, skill_root: Path) -> None:
    scaffold_project(
        project_name="Osmotic Pressure Verifier",
        project_slug="osmotic_pressure",
        out_dir=tmp_project_root,
        skill_root=skill_root,
    )
    for rel in [
        "shadow-cljs.edn",
        "package.json",
        "deps.edn",
        ".gitignore",
        "README.md",
        "SKILL.md",
        "rules/seed.edn",
        "rules/grounded.edn",
        "rules/predicates.edn",
        "rules/.forge-version.edn",
        "cljs-orchestrator/src/main/osmotic_pressure/core.cljs",
        "cljs-orchestrator/src/main/osmotic_pressure/phases.cljs",
        "cljs-orchestrator/src/main/osmotic_pressure/ir.cljs",
        "cljs-orchestrator/src/main/osmotic_pressure/nl_to_fol.cljs",
        "cljs-orchestrator/src/main/osmotic_pressure/unify.cljs",
        "cljs-orchestrator/src/main/osmotic_pressure/bridge.cljs",
        "rust-verifier/Cargo.toml",
        "rust-verifier/build.rs",
        "rust-verifier/src/lib.rs",
        "rust-verifier/src/ir.rs",
        "rust-verifier/src/smt.rs",
        "rust-verifier/src/eqsat.rs",
        "rust-verifier/src/kg.rs",
        "rust-verifier/src/typeset.rs",
        "templates/report.tex.tera",
        "templates/claim_table.tex.tera",
    ]:
        assert (tmp_project_root / rel).exists(), f"missing {rel}"


def test_slug_substitution(tmp_project_root: Path, skill_root: Path) -> None:
    scaffold_project(
        project_name="X",
        project_slug="osmotic_pressure",
        out_dir=tmp_project_root,
        skill_root=skill_root,
    )
    core = (tmp_project_root / "cljs-orchestrator/src/main/osmotic_pressure/core.cljs").read_text()
    assert "(ns osmotic_pressure.core" in core
    cargo = (tmp_project_root / "rust-verifier/Cargo.toml").read_text()
    assert 'name    = "osmotic_pressure-verifier"' in cargo


def test_forge_version_recorded(tmp_project_root: Path, skill_root: Path) -> None:
    scaffold_project(
        project_name="X",
        project_slug="x",
        out_dir=tmp_project_root,
        skill_root=skill_root,
    )
    payload = read_edn_as_json(tmp_project_root / "rules" / ".forge-version.edn")
    assert "neurosym_forge_version" in payload
    assert payload["neurosym_forge_version"].startswith("0.1")


def test_refuses_to_overwrite(tmp_project_root: Path, skill_root: Path) -> None:
    scaffold_project(
        project_name="X", project_slug="x",
        out_dir=tmp_project_root, skill_root=skill_root,
    )
    with pytest.raises(FileExistsError):
        scaffold_project(
            project_name="X", project_slug="x",
            out_dir=tmp_project_root, skill_root=skill_root,
        )


def test_cli_round_trip(tmp_path: Path, skill_root: Path) -> None:
    out = tmp_path / "v" / "demo"
    result = subprocess.run(
        [sys.executable, "-m", "scripts.scaffold_project",
         "--name", "Demo", "--slug", "demo", "--out", str(out)],
        capture_output=True, text=True, cwd=str(skill_root),
    )
    assert result.returncode == 0, result.stderr
    assert (out / "package.json").exists()
