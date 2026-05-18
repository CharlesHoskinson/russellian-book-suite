"""End-to-end D13 smoke. Runs the full verifier against a fixture chapter
containing the canonical parish-count drift. Asserts:

    1. The Rust verifier exits with :unsat.
    2. The unsat core contains the offending prose atom id.
    3. verdict_to_qa emits a verification-defects.json with verdict=unsat.
    4. book-qa.lint_d13_verification_unsat returns ≥1 D13 critical defect.

Skipped when the Rust verifier hasn't been built (PR-5 Phase 4 / CI Phase 5
covers the build); the test is the canonical gate in CI but skips cleanly
on local machines without Z3.

REQ-QA-PIPE-020..024, REQ-CLJS-ORCH-020"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

BERMUDA_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BERMUDA_ROOT.parents[1]
FIXTURE = BERMUDA_ROOT / "tests" / "fixtures" / "chapter_ch02_eight_parishes.md"


def _verifier_built() -> bool:
    """The CLJS bundle and Rust addon must both be present."""
    main_js = BERMUDA_ROOT / "cljs-orchestrator" / "dist" / "main.js"
    return main_js.exists()


@pytest.mark.skipif(not _verifier_built(),
                    reason="Rust+CLJS verifier not built locally; CI is the gate")
def test_d13_fires_on_ch02_parish_count_drift(tmp_path: Path) -> None:
    """Drive the real verifier end-to-end. Workspace is a clean copy of the
    bermuda-manual example with ch-02 prose replaced by the fixture."""
    # 1. Stage workspace.
    workspace = tmp_path / "bermuda-manual"
    shutil.copytree(REPO_ROOT / "examples" / "bermuda-manual", workspace)
    # Replace ch-02 prose with the fixture (preserves manifest.yaml etc.).
    ch02 = workspace / "book" / "releases" / "6.0.0" / "chapter-bundles" / "ch-02-v6" / "draft.md"
    ch02.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")

    # 2. Run the full verifier (real Z3, no stub).
    import sys
    sys.path.insert(0, str(BERMUDA_ROOT))
    from scripts.run_verification import run

    rc = run(
        workspace=workspace,
        release_version="6.0.0",
        project_root=BERMUDA_ROOT,
        stub_verifier=False,
    )
    # rc is 0 on a successful verifier invocation regardless of verdict; we
    # introspect verdict.edn for the actual outcome.
    assert rc == 0, f"verifier exited rc={rc}"

    # 3. Assert verdict.edn says unsat.
    from scripts._io import read_edn_file
    from scripts._edn_reader import Keyword
    verdict_path = BERMUDA_ROOT / "work" / "verdict.edn"
    verdict = read_edn_file(verdict_path)
    assert verdict.get(Keyword("verdict")) in {Keyword("unsat"), "unsat"}, (
        f"expected :unsat verdict, got {verdict.get(Keyword('verdict'))}; "
        f"full verdict={verdict}"
    )

    # 4. Assert at least one prose-extracted claim id appears in the core.
    core = verdict.get(Keyword("core"), [])
    prose_in_core = [c for c in core if str(c).startswith("prose-ch-02")]
    assert prose_in_core or any(c == "clm-2026-000008" for c in core), (
        f"expected ch-02 prose atom or clm-2026-000008 in unsat core; got core={core}"
    )

    # 5. Translate verdict.edn → verification-defects.json.
    from scripts.verdict_to_qa import translate
    qa_dir = workspace / "qa"
    qa_dir.mkdir(parents=True, exist_ok=True)
    translate(verdict_path, qa_dir / "verification-defects.json")

    # 6. Run book-qa lint_d13.
    sys.path.insert(0, str(REPO_ROOT / "skills" / "book-qa"))
    from scripts.lint_artifact import lint_d13_verification_unsat
    defects = lint_d13_verification_unsat(workspace)
    d13 = [d for d in defects if d.class_ == "D13"]
    assert len(d13) >= 1, f"expected ≥1 D13 defect; got {defects}"
    assert all(d.severity == "critical" for d in d13), \
        f"D13 must be critical severity; got {[d.severity for d in d13]}"
