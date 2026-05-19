"""REQ-INGEST-046, REQ-INGEST-047: scaffold-bake structural assertions that
don't require the nix shell (so they run on Windows / dev laptops too)."""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SKILL_ROOT = REPO_ROOT / "skills" / "neurosym-forge"


def _scaffold(tmp_path: Path, slug: str) -> Path:
    sys.path.insert(0, str(SKILL_ROOT))
    from scripts.scaffold_project import scaffold_project  # type: ignore
    out_dir = tmp_path / slug
    scaffold_project(
        project_name="Bake Test",
        project_slug=slug,
        out_dir=out_dir,
        skill_root=SKILL_ROOT,
    )
    return out_dir


def test_baked_makefile_has_extract_target(tmp_path: Path) -> None:
    """REQ-INGEST-046: baked Makefile has `extract` target."""
    project = _scaffold(tmp_path, "extract_bake")
    makefile_text = (project / "Makefile").read_text(encoding="utf-8")
    assert "\nextract:" in makefile_text, (
        f"baked Makefile lacks `extract` target:\n{makefile_text}"
    )


def test_baked_ci_depends_on_extract(tmp_path: Path) -> None:
    """REQ-INGEST-046: baked `ci:` target depends on `extract`."""
    project = _scaffold(tmp_path, "extract_bake_ci")
    text = (project / "Makefile").read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.startswith("ci:"):
            deps = line.split(":", 1)[1].split()
            assert "extract" in deps, f"`ci:` deps={deps!r}"
            return
    raise AssertionError("no `ci:` line in baked Makefile")


def test_baked_project_has_extract_preview_shim(tmp_path: Path) -> None:
    """REQ-INGEST-047: baked project includes the extract_preview.py shim
    AND the vendored canonical lib."""
    project = _scaffold(tmp_path, "extract_bake_shim")
    assert (project / "scripts" / "extract_preview.py").exists(), \
        "baked project missing scripts/extract_preview.py"
    assert (project / "scripts" / "_extract_preview_lib.py").exists(), \
        "baked project missing scripts/_extract_preview_lib.py (vendored)"


def test_baked_project_vendors_provenance(tmp_path: Path) -> None:
    """REQ-PROV-047: baked project ships scripts/_provenance.py (vendored)
    so `forge induce` can use ProvenanceSidecar without PYTHONPATH tricks.
    """
    project = _scaffold(tmp_path, "provenance_bake")
    assert (project / "scripts" / "_provenance.py").exists(), \
        "baked project missing scripts/_provenance.py (vendored)"


def test_baked_project_ships_starter_sidecar(tmp_path: Path) -> None:
    """REQ-PROV-047: baked project ships an empty starter
    rules/booklogic/induced-theory.prov.edn so the inducer has a
    well-formed target on its first invocation.
    """
    project = _scaffold(tmp_path, "provenance_bake_starter")
    sidecar = project / "rules" / "booklogic" / "induced-theory.prov.edn"
    assert sidecar.exists(), f"baked project missing {sidecar}"
    text = sidecar.read_text(encoding="utf-8")
    assert ":version 1" in text
    assert ":rules {}" in text


def test_baked_starter_sidecar_loads_via_provenance_sidecar(tmp_path: Path) -> None:
    """REQ-PROV-047 + REQ-PROV-040: the starter sidecar must be a valid
    EDN file that `ProvenanceSidecar.load` can parse without error.
    """
    project = _scaffold(tmp_path, "provenance_bake_load")
    sidecar_path = project / "rules" / "booklogic" / "induced-theory.prov.edn"
    sys.path.insert(0, str(SKILL_ROOT))
    from scripts._provenance import ProvenanceSidecar  # type: ignore
    sidecar = ProvenanceSidecar.load(sidecar_path)
    assert list(sidecar.iter_rules()) == []
