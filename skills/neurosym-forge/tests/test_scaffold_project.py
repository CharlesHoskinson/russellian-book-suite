from __future__ import annotations

import pytest

pytestmark = pytest.mark.windows_canary

import json
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
    # CLJS namespace is dashed (osmotic-pressure.core) even though the file
    # path uses underscores (osmotic_pressure/core.cljs) — standard
    # ClojureScript convention for `_`<->`-` inversion.
    assert "(ns osmotic-pressure.core" in core
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


def test_scaffolded_axioms_rs_is_present(tmp_project_root: Path, skill_root: Path) -> None:
    """REQ-VERIFIER-BUILD-010: scaffolded project has axioms.rs (placeholder or generated)."""
    scaffold_project(project_name="X", project_slug="x",
                     out_dir=tmp_project_root, skill_root=skill_root)
    axioms = tmp_project_root / "rust-verifier" / "src" / "axioms.rs"
    assert axioms.exists()
    text = axioms.read_text(encoding="utf-8")
    # No constraints declared in a fresh scaffold → file is the placeholder.
    assert "PLACEHOLDER" in text or "No-op default" in text


def test_scaffolded_axioms_rs_regenerated_when_constraints_declared(
    tmp_project_root: Path, skill_root: Path,
) -> None:
    """REQ-DSL-021: codegen overwrites axioms.rs when constraints.edn is present."""
    scaffold_project(project_name="X", project_slug="x",
                     out_dir=tmp_project_root, skill_root=skill_root)
    # Manually write an intermediate constraints.edn (simulating nbb output).
    rules = tmp_project_root / "rules"
    rules.mkdir(exist_ok=True)
    (rules / "constraints.edn").write_text(
        '{:version 1 :constraints [{:id "C001" :backend :z3 '
        ':assert "(= (:parishes-count :Bermuda) 9)" :tolerance nil '
        ':track :claim/id :on-unsat {:defect :D13 :severity :critical '
        ':message "wrong"}}]}',
        encoding="utf-8",
    )
    from scripts.codegen_axioms import run as run_axioms
    run_axioms(tmp_project_root)
    axioms = (tmp_project_root / "rust-verifier" / "src" / "axioms.rs").read_text(encoding="utf-8")
    assert "GENERATED BY neurosym-forge codegen_axioms" in axioms
    assert "C001" in axioms
    tracker = (tmp_project_root / "rules" / "axioms-tracker-map.edn").read_text(encoding="utf-8")
    assert "C001" in tracker
    assert ":D13" in tracker


def test_scaffolded_booklogic_active_form_seeds(tmp_project_root: Path, skill_root: Path) -> None:
    scaffold_project(project_name="X", project_slug="x",
                     out_dir=tmp_project_root, skill_root=skill_root)
    booklogic = tmp_project_root / "rules" / "booklogic"
    for fname in ("rules.edn", "constraints.edn", "queries.edn", "remedies.edn"):
        p = booklogic / fname
        assert p.exists(), f"missing scaffold seed: {p}"
        # REQ-BOOKLOGIC-046: each seed ships with comments + example + silent-failure
        # notes; the empty `{:forms []}` literal remains at the bottom.
        assert p.read_text(encoding="utf-8").rstrip().endswith("{:forms []}"), \
            f"{fname} seed must end with the {{:forms []}} literal"


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


def test_scaffolded_package_json_has_nbb(tmp_project_root: Path, skill_root: Path) -> None:
    scaffold_project(project_name="X", project_slug="x",
                     out_dir=tmp_project_root, skill_root=skill_root)
    pkg = json.loads((tmp_project_root / "package.json").read_text(encoding="utf-8"))
    assert "nbb" in pkg.get("devDependencies", {})
    assert "booklogic-compile" in pkg.get("scripts", {})
    assert "test:booklogic" in pkg.get("scripts", {})


def test_scaffolded_booklogic_rules_directory(tmp_project_root: Path, skill_root: Path) -> None:
    scaffold_project(project_name="X", project_slug="x",
                     out_dir=tmp_project_root, skill_root=skill_root)
    booklogic = tmp_project_root / "rules" / "booklogic"
    assert (booklogic / "sorts.edn").exists()
    assert (booklogic / "predicates.edn").exists()
    assert (booklogic / "lifts.edn").exists()
    contents = (booklogic / "sorts.edn").read_text(encoding="utf-8")
    assert "{:forms []}" in contents
