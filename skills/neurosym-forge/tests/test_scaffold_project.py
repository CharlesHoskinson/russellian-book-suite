from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from scripts._edn_reader import Keyword
from scripts._io import read_edn_file
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
    payload = read_edn_file(tmp_project_root / "rules" / ".forge-version.edn")
    version_key = Keyword("neurosym_forge_version")
    assert version_key in payload
    assert payload[version_key].startswith("0.1")


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


def test_rejects_bad_slug(tmp_path: Path, skill_root: Path) -> None:
    with pytest.raises(ValueError, match="project_slug"):
        scaffold_project(project_name="X", project_slug="My-Project",
                         out_dir=tmp_path / "v", skill_root=skill_root)


def test_rejects_empty_slug(tmp_path: Path, skill_root: Path) -> None:
    with pytest.raises(ValueError, match="project_slug"):
        scaffold_project(project_name="X", project_slug="",
                         out_dir=tmp_path / "v", skill_root=skill_root)


def test_rejects_dotdot_in_out(tmp_path: Path, skill_root: Path, monkeypatch) -> None:
    inside = tmp_path / "cwd"
    inside.mkdir()
    monkeypatch.chdir(inside)
    with pytest.raises(ValueError, match="outside the current working directory"):
        scaffold_project(project_name="X", project_slug="x",
                         out_dir=Path("..") / ".." / ".." / "escape" / "x",
                         skill_root=skill_root)


def test_cli_round_trip(tmp_path: Path, skill_root: Path) -> None:
    out = tmp_path / "v" / "demo"
    result = subprocess.run(
        [sys.executable, "-m", "scripts.scaffold_project",
         "--name", "Demo", "--slug", "demo", "--out", str(out)],
        capture_output=True, text=True, cwd=str(skill_root),
    )
    assert result.returncode == 0, result.stderr
    assert (out / "package.json").exists()


def test_bridge_flag_emits_ingest_ledger(tmp_project_root: Path, skill_root: Path) -> None:
    scaffold_project(
        project_name="Test", project_slug="test_bridge",
        out_dir=tmp_project_root, skill_root=skill_root,
        has_book_knowledge_bridge=True,
    )
    assert (tmp_project_root / "scripts" / "ingest_ledger.py").exists()
    assert (tmp_project_root / "scripts" / "__init__.py").exists()


def test_no_bridge_omits_ingest_ledger(tmp_project_root: Path, skill_root: Path) -> None:
    scaffold_project(
        project_name="Test", project_slug="test_nobridge",
        out_dir=tmp_project_root, skill_root=skill_root,
        has_book_knowledge_bridge=False,
    )
    assert not (tmp_project_root / "scripts" / "ingest_ledger.py").exists()


def test_relative_dotdot_under_cwd_accepted(tmp_path: Path, skill_root: Path,
                                             monkeypatch) -> None:
    """`--out ../verifiers/x` from a sibling cwd resolves to a path under
    the original cwd; this is allowed."""
    # Make tmp_path the cwd so a relative .. resolves under it
    parent = tmp_path
    workdir = parent / "work"
    workdir.mkdir()
    target = parent / "verifiers" / "demo"
    monkeypatch.chdir(workdir)
    scaffold_project(
        project_name="Demo", project_slug="demo",
        out_dir=Path("..") / "verifiers" / "demo",
        skill_root=skill_root,
    )
    assert target.exists()


def test_absolute_outside_cwd_accepted(tmp_path: Path, skill_root: Path,
                                       monkeypatch) -> None:
    """An absolute path outside cwd is allowed (operator opt-in)."""
    inside = tmp_path / "inside"
    inside.mkdir()
    outside = tmp_path / "outside_abs" / "demo"
    monkeypatch.chdir(inside)
    scaffold_project(
        project_name="Demo", project_slug="demo",
        out_dir=outside.resolve(),
        skill_root=skill_root,
    )
    assert outside.exists()


def test_relative_dotdot_escaping_cwd_rejected(tmp_path: Path, skill_root: Path,
                                                monkeypatch) -> None:
    """A relative path with `..` that resolves OUTSIDE cwd is rejected."""
    inside = tmp_path / "deep" / "nested" / "cwd"
    inside.mkdir(parents=True)
    monkeypatch.chdir(inside)
    with pytest.raises(ValueError, match="outside the current working directory"):
        scaffold_project(
            project_name="Demo", project_slug="demo",
            out_dir=Path("..") / ".." / ".." / ".." / "escape",
            skill_root=skill_root,
        )


def test_scaffolded_axioms_rs_exists(tmp_project_root: Path, skill_root: Path) -> None:
    scaffold_project(project_name="X", project_slug="x",
                     out_dir=tmp_project_root, skill_root=skill_root)
    axioms = tmp_project_root / "rust-verifier" / "src" / "axioms.rs"
    assert axioms.exists()
    text = axioms.read_text(encoding="utf-8")
    assert "pub fn assert_axioms" in text


def test_scaffolded_lib_rs_includes_mod_axioms(tmp_project_root: Path, skill_root: Path) -> None:
    scaffold_project(project_name="X", project_slug="x",
                     out_dir=tmp_project_root, skill_root=skill_root)
    lib = (tmp_project_root / "rust-verifier" / "src" / "lib.rs").read_text(encoding="utf-8")
    assert "mod axioms;" in lib


def test_scaffolded_cargo_toml_has_features(tmp_project_root: Path, skill_root: Path) -> None:
    scaffold_project(project_name="X", project_slug="x",
                     out_dir=tmp_project_root, skill_root=skill_root)
    cargo = (tmp_project_root / "rust-verifier" / "Cargo.toml").read_text(encoding="utf-8")
    assert "[features]" in cargo
    assert "pdf" in cargo
