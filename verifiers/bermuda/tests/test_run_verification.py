from __future__ import annotations

import inspect
import json
from pathlib import Path


from scripts.run_verification import run


def test_run_signature_defaults_to_real_verifier() -> None:
    """`stub_verifier` must default to False so CI exercises the real
    pipeline; the stub stays available behind explicit opt-in.

    REQ-CLJS-ORCH-020"""
    sig = inspect.signature(run)
    p = sig.parameters["stub_verifier"]
    assert p.default is False, (
        f"stub_verifier default must be False (got {p.default!r}); "
        "explicit opt-in only for local fast iteration"
    )


def _seed_workspace(root: Path) -> None:
    (root / "examples" / "test-workspace" / "claims").mkdir(parents=True)
    (root / "examples" / "test-workspace" / "claims" / "ledger.jsonl").write_text(
        '{"claim_id": "clm-2026-000001", "claim_type": "fact",'
        ' "canonical_text": "Bermuda has nine traditional parishes including St. George\'s.",'
        ' "status": "verified", "confidence": 0.9}\n',
        encoding="utf-8",
    )
    (root / "examples" / "test-workspace" / "book" / "releases" / "1.0.0"
     / "chapter-bundles" / "ch-01").mkdir(parents=True)
    (root / "examples" / "test-workspace" / "book" / "releases" / "1.0.0"
     / "chapter-bundles" / "ch-01" / "draft.md").write_text(
        "Bermuda has 8 traditional parishes.", encoding="utf-8",
    )
    (root / "examples" / "test-workspace" / "qa").mkdir()


def test_run_with_explicit_stub(tmp_path: Path, project_root: Path) -> None:
    """The stub remains usable for fast local iteration via explicit opt-in."""
    _seed_workspace(tmp_path)
    workspace = tmp_path / "examples" / "test-workspace"
    rc = run(
        workspace=workspace,
        release_version="1.0.0",
        project_root=project_root,
        stub_verifier=True,
        stub_verdict="unsat",
        stub_core=["clm-2026-000001", "prose-ch-01-001"],
    )
    assert rc == 0
    out = workspace / "qa" / "verification-defects.json"
    assert out.exists()
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["verdict"] == "unsat"
    assert "clm-2026-000001" in payload["core"]


def test_run_with_sat_stub(tmp_path: Path, project_root: Path) -> None:
    _seed_workspace(tmp_path)
    workspace = tmp_path / "examples" / "test-workspace"
    rc = run(workspace=workspace, release_version="1.0.0",
             project_root=project_root, stub_verifier=True,
             stub_verdict="sat", stub_core=[])
    assert rc == 0
    payload = json.loads((workspace / "qa" / "verification-defects.json").read_text())
    assert payload["verdict"] == "sat"
