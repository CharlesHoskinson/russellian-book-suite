# skills/neurosym-forge/tests/test_cljs_integration.py
"""Live integration test: scaffold a project, npm install nbb, run the
BookLogic compiler against fixtures, assert correct outputs.

Requires Node 22+ in PATH. If Node is missing the test SKIPs with a
clear message so the regular pytest run doesn't fail on machines without
the toolchain.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.scaffold_project import scaffold_project


def _node_available() -> bool:
    return shutil.which("node") is not None and shutil.which("npm") is not None


pytestmark = pytest.mark.skipif(
    not _node_available(),
    reason="Node + npm not on PATH; skipping live nbb integration test",
)


SORTS_EDN = """{:forms [(defsort :entity)
                        (defsort :int)]}
"""

PREDICATES_EDN = """{:forms [(defpredicate :parishes-count [:entity] :int)]}
"""

LIFTS_EDN = """{:forms [(deflift L001
                          :from :claim/canonical-text
                          :when "(?i)(?<n>\\\\d+)\\\\s+parishes?"
                          :emit (fact ?claim-id :Bermuda :parishes-count (parse-int ?n))
                          :word-to-int {"nine" 9 "eight" 8 "seven" 7})]}
"""


@pytest.fixture()
def scaffolded_project(tmp_path: Path, skill_root: Path) -> Path:
    out = tmp_path / "demo"
    scaffold_project(
        project_name="Demo", project_slug="demo",
        out_dir=out, skill_root=skill_root,
    )
    (out / "rules" / "booklogic" / "sorts.edn").write_text(SORTS_EDN, encoding="utf-8")
    (out / "rules" / "booklogic" / "predicates.edn").write_text(PREDICATES_EDN, encoding="utf-8")
    (out / "rules" / "booklogic" / "lifts.edn").write_text(LIFTS_EDN, encoding="utf-8")
    return out


def _npm_install(project: Path) -> None:
    result = subprocess.run(
        ["npm", "install", "--no-audit", "--no-fund", "--loglevel=error"],
        cwd=str(project), capture_output=True, text=True, timeout=180,
    )
    if result.returncode != 0:
        pytest.fail(f"npm install failed:\nstdout: {result.stdout}\nstderr: {result.stderr}")


def test_booklogic_compile_emits_predicates_edn(scaffolded_project: Path) -> None:
    """The compiler reads booklogic/*.edn, writes predicates.edn at rules root."""
    _npm_install(scaffolded_project)

    result = subprocess.run(
        ["npm", "run", "booklogic-compile"],
        cwd=str(scaffolded_project), capture_output=True, text=True, timeout=60,
    )
    if result.returncode != 0:
        pytest.fail(f"booklogic-compile failed:\nstdout: {result.stdout}\nstderr: {result.stderr}")

    # predicates.edn must now exist at rules root
    out_path = scaffolded_project / "rules" / "predicates.edn"
    assert out_path.exists(), f"compiler did not write {out_path}"

    text = out_path.read_text(encoding="utf-8")
    assert ":version 1" in text
    assert ":parishes-count" in text
    assert ":value-kind :int" in text


def test_booklogic_nbb_test_fixture_passes(scaffolded_project: Path) -> None:
    """The CLJS test fixture exercises expand and predicates.edn shape from inside nbb."""
    _npm_install(scaffolded_project)

    result = subprocess.run(
        ["npm", "run", "test:booklogic"],
        cwd=str(scaffolded_project), capture_output=True, text=True, timeout=60,
    )
    if result.returncode != 0:
        pytest.fail(f"test:booklogic failed:\nstdout: {result.stdout}\nstderr: {result.stderr}")
    # cljs.test prints assertion counts; we just want exit 0
