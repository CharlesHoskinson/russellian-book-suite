# skills/neurosym-forge/tests/test_cljs_integration.py
"""Live integration test: scaffold a project, npm install nbb, run the
BookLogic compiler against fixtures, assert correct outputs.

Requires Node 22+ in PATH. If Node is missing the test SKIPs with a
clear message so the regular pytest run doesn't fail on machines without
the toolchain.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from scripts.scaffold_project import scaffold_project


def _node_available() -> bool:
    return shutil.which("node") is not None and shutil.which("npm") is not None


pytestmark = pytest.mark.skipif(
    not _node_available(),
    reason="Node + npm not on PATH; skipping live nbb integration test",
)


# Resolve npm to its full path. On Windows, `npm` is a `.cmd` batch wrapper;
# subprocess on Windows uses CreateProcess which doesn't auto-resolve `.cmd`
# unless given an absolute path. shutil.which() finds the .cmd correctly.
NPM = shutil.which("npm") or "npm"


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


@pytest.fixture(scope="module")
def scaffolded_project(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Module-scoped: scaffold + npm install once, reuse across both tests.

    Cold `npm install` of nbb is ~50MB and 1-3 minutes; doing it per test
    triples the wall time of this suite for no test-isolation benefit.
    """
    skill_root = Path(__file__).resolve().parent.parent
    out = tmp_path_factory.mktemp("cljs_integration") / "demo"
    scaffold_project(
        project_name="Demo", project_slug="demo",
        out_dir=out, skill_root=skill_root,
    )
    (out / "rules" / "booklogic" / "sorts.edn").write_text(SORTS_EDN, encoding="utf-8")
    (out / "rules" / "booklogic" / "predicates.edn").write_text(PREDICATES_EDN, encoding="utf-8")
    (out / "rules" / "booklogic" / "lifts.edn").write_text(LIFTS_EDN, encoding="utf-8")
    _npm_install(out)
    return out


def _npm_install(project: Path) -> None:
    result = subprocess.run(
        [NPM, "install", "--no-audit", "--no-fund", "--loglevel=error"],
        cwd=str(project), capture_output=True, text=True, timeout=600,
    )
    if result.returncode != 0:
        pytest.fail(f"npm install failed:\nstdout: {result.stdout}\nstderr: {result.stderr}")


def test_booklogic_compile_emits_predicates_edn(scaffolded_project: Path) -> None:
    """The compiler reads booklogic/*.edn, writes predicates.edn at rules root."""
    result = subprocess.run(
        [NPM, "run", "booklogic-compile"],
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
    result = subprocess.run(
        [NPM, "run", "test:booklogic"],
        cwd=str(scaffolded_project), capture_output=True, text=True, timeout=60,
    )
    if result.returncode != 0:
        pytest.fail(f"test:booklogic failed:\nstdout: {result.stdout}\nstderr: {result.stderr}")
    # cljs.test prints assertion counts; we just want exit 0
