"""End-to-end smoke for the osmotic-pressure verifier.

REQ-OSMOTIC-040, REQ-OSMOTIC-041: sat + unsat verdicts from real fixtures.

Pipeline per fixture:
  1. ingest_ledger      fixtures/claims_*.jsonl -> work/claims.edn
                        (uses rules/predicates.edn regen'd by the BookLogic
                         compiler in Phase 4)
  2. verify             node cljs-orchestrator/dist/main.js verify
                        work/claims.edn work/verdict.edn
  3. read verdict       parse work/verdict.edn (EDN) and assert :verdict / :core

The tests skip when the verifier dist is not built (local Windows-only
case). CI builds the verifier before invoking pytest.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from scripts._edn_reader import Keyword
from scripts._io import read_edn_file
from scripts.ingest_ledger import ingest


_KW_VERDICT = Keyword("verdict")
_KW_STATUS = Keyword("status")
_KW_CORE = Keyword("core")


def _verifier_main_js(project_root: Path) -> Path:
    return project_root / "cljs-orchestrator" / "dist" / "main.js"


def _have_verifier(project_root: Path) -> bool:
    return _verifier_main_js(project_root).exists()


def _have_node() -> bool:
    return shutil.which("node") is not None or shutil.which("node.exe") is not None


pytestmark = pytest.mark.skipif(
    not _have_node(),
    reason="node not on PATH; CI sets up Node 22",
)


def _run_verifier(project_root: Path, claims_edn: Path, verdict_edn: Path) -> None:
    subprocess.run(
        ["node", str(_verifier_main_js(project_root)),
         "verify", str(claims_edn), str(verdict_edn)],
        check=True, cwd=str(project_root),
    )


def _verdict_status(verdict_edn: Path) -> str:
    """Return ':sat' / ':unsat' / ':unknown' from a verdict.edn file."""
    payload = read_edn_file(verdict_edn)
    # Accept either :verdict (PR-4 schema) or :status (legacy emit_verdict
    # which currently writes :status). PR-5 unifies these; until then accept both.
    for key in (_KW_VERDICT, _KW_STATUS):
        v = payload.get(key)
        if v is None:
            continue
        return str(v) if isinstance(v, Keyword) else v
    raise AssertionError(f"verdict.edn missing :verdict / :status: {payload!r}")


def _verdict_core(verdict_edn: Path) -> list[str]:
    payload = read_edn_file(verdict_edn)
    core = payload.get(_KW_CORE, [])
    return list(core)


def test_clean_fixture_is_sat(project_root: Path, tmp_work: Path) -> None:
    """REQ-OSMOTIC-040: clean fixture (i=2) yields :sat verdict."""
    if not _have_verifier(project_root):
        pytest.skip(f"verifier not built ({_verifier_main_js(project_root)})")

    claims_edn = tmp_work / "claims.edn"
    verdict_edn = tmp_work / "verdict.edn"
    ingest(
        project_root / "fixtures" / "claims_clean.jsonl",
        project_root / "rules" / "predicates.edn",
        claims_edn,
    )
    _run_verifier(project_root, claims_edn, verdict_edn)

    status = _verdict_status(verdict_edn)
    assert status in (":sat", "sat"), (
        f"expected :sat for clean fixture, got {status!r}"
    )


def test_doctored_fixture_is_unsat_with_i1_in_core(
    project_root: Path, tmp_work: Path,
) -> None:
    """REQ-OSMOTIC-041: doctored fixture (i=1) yields :unsat with osm-doc-001 in core."""
    if not _have_verifier(project_root):
        pytest.skip(f"verifier not built ({_verifier_main_js(project_root)})")

    claims_edn = tmp_work / "claims.edn"
    verdict_edn = tmp_work / "verdict.edn"
    ingest(
        project_root / "fixtures" / "claims_doctored.jsonl",
        project_root / "rules" / "predicates.edn",
        claims_edn,
    )
    _run_verifier(project_root, claims_edn, verdict_edn)

    status = _verdict_status(verdict_edn)
    assert status in (":unsat", "unsat"), (
        f"expected :unsat for doctored fixture, got {status!r}"
    )
    core = _verdict_core(verdict_edn)
    assert "osm-doc-001" in core, (
        f"expected i=1 claim 'osm-doc-001' in unsat core, got {core!r}"
    )
