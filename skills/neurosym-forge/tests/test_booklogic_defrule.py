"""Python-side gate: a defrule form lands in rules/rules.edn after
nbb compilation. Reuses the scaffolded-project fixture from
test_cljs_integration.

REQ-DSL-010: defrule expander.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.windows_canary

import shutil
import subprocess
from pathlib import Path

import pytest

from scripts.scaffold_project import scaffold_project
from scripts._io import read_edn_file
from scripts._edn_reader import Keyword


def _node_available() -> bool:
    return shutil.which("node") is not None and shutil.which("npm") is not None


pytestmark = pytest.mark.skipif(
    not _node_available(),
    reason="Node + npm not on PATH; skipping live nbb integration test",
)


NPM = shutil.which("npm") or "npm"


RULES_EDN = """{:forms [(defrule R001-normalize-st-davids
                          (= (entity "St. David's Island")
                             :St_Davids_Island)
                          :tags [:normalization :entity])
                        (defrule R002-celsius-to-kelvin
                          (= (apply :temperature :subject)
                             (apply :temperature-celsius :subject))
                          :tags [:algebraic :unit-conversion])]}
"""


@pytest.fixture(scope="module")
def project_with_rules(tmp_path_factory: pytest.TempPathFactory) -> Path:
    skill_root = Path(__file__).resolve().parent.parent
    out = tmp_path_factory.mktemp("defrule") / "demo"
    scaffold_project(
        project_name="Demo", project_slug="demo",
        out_dir=out, skill_root=skill_root,
    )
    (out / "rules" / "booklogic" / "rules.edn").write_text(RULES_EDN, encoding="utf-8")
    # Install once.
    r = subprocess.run(
        [NPM, "install", "--no-audit", "--no-fund", "--loglevel=error"],
        cwd=str(out), capture_output=True, text=True, timeout=600,
    )
    if r.returncode != 0:
        pytest.fail(f"npm install failed:\nstdout: {r.stdout}\nstderr: {r.stderr}")
    return out


def test_defrule_compile_emits_rules_edn(project_with_rules: Path) -> None:
    """REQ-DSL-010: defrule forms appear in rules/rules.edn after compilation."""
    r = subprocess.run(
        [NPM, "run", "booklogic-compile"],
        cwd=str(project_with_rules), capture_output=True, text=True, timeout=60,
    )
    if r.returncode != 0:
        pytest.fail(f"booklogic-compile failed:\nstdout: {r.stdout}\nstderr: {r.stderr}")
    rules_path = project_with_rules / "rules" / "rules.edn"
    assert rules_path.exists()
    payload = read_edn_file(rules_path)
    assert payload[Keyword("version")] == 1
    rules = payload[Keyword("rules")]
    assert len(rules) == 2
    names = {entry[Keyword("id")] for entry in rules}
    assert "R001-normalize-st-davids" in names
    assert "R002-celsius-to-kelvin"  in names


def test_defrule_compile_preserves_tags(project_with_rules: Path) -> None:
    """REQ-DSL-010: defrule :tags are preserved in rules.edn."""
    r = subprocess.run(
        [NPM, "run", "booklogic-compile"],
        cwd=str(project_with_rules), capture_output=True, text=True, timeout=60,
    )
    assert r.returncode == 0
    payload = read_edn_file(project_with_rules / "rules" / "rules.edn")
    rules = payload[Keyword("rules")]
    by_name = {e[Keyword("id")]: e for e in rules}
    assert Keyword("normalization") in by_name["R001-normalize-st-davids"][Keyword("tags")]
    assert Keyword("algebraic")     in by_name["R002-celsius-to-kelvin"][Keyword("tags")]
