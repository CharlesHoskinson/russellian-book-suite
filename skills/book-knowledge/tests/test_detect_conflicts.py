from datetime import datetime, timezone

from scripts.workspace import init_workspace, WorkspaceLayout
from scripts.ledger import append_claim
from scripts.detect_conflicts import detect_conflicts


def _verified(cid: str, text: str) -> dict:
    return {
        "claim_id": cid,
        "canonical_text": text,
        "status": "verified",
        "claim_type": "fact",
        "confidence": 0.9,
        "source_spans": [{"doc_id": "small", "locator_text": "locator"}],
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def test_detects_explicit_conflicts_via_canonical_text(tmp_path):
    layout = WorkspaceLayout(init_workspace(tmp_path / "book"))
    append_claim(layout, _verified("clm-2026-000001", "Conformance is mandatory."))
    append_claim(layout, _verified("clm-2026-000002", "Conformance is optional."))
    conflicts = detect_conflicts(layout)
    assert len(conflicts) >= 1
    pair = conflicts[0]
    assert {"clm-2026-000001", "clm-2026-000002"} == set(pair["claims"])


def test_no_conflicts_when_claims_distinct(tmp_path):
    layout = WorkspaceLayout(init_workspace(tmp_path / "book"))
    append_claim(layout, _verified("clm-2026-000001", "SHACL produces conformance reports."))
    append_claim(layout, _verified("clm-2026-000002", "PROV-O models provenance."))
    assert detect_conflicts(layout) == []


def test_writes_conflicts_jsonl(tmp_path):
    layout = WorkspaceLayout(init_workspace(tmp_path / "book"))
    append_claim(layout, _verified("clm-2026-000001", "Operation X is allowed."))
    append_claim(layout, _verified("clm-2026-000002", "Operation X is forbidden."))
    detect_conflicts(layout)
    assert layout.conflicts.exists()
    content = layout.conflicts.read_text(encoding="utf-8")
    assert "clm-2026-000001" in content


def test_conflicting_claims_transition_to_disputed(tmp_path):
    """After detect_conflicts, both conflicting claims should be status=disputed,
    per the documented five-state machine and the README's state diagram."""
    from scripts.ledger import latest_status

    layout = WorkspaceLayout(init_workspace(tmp_path / "book"))
    append_claim(layout, _verified("clm-2026-000001", "Operation X is allowed."))
    append_claim(layout, _verified("clm-2026-000002", "Operation X is forbidden."))

    conflicts = detect_conflicts(layout)
    assert len(conflicts) >= 1

    assert latest_status(layout, "clm-2026-000001") == "disputed"
    assert latest_status(layout, "clm-2026-000002") == "disputed"


def _latest_record(layout, claim_id):
    from scripts.ledger import read_claims
    rec = None
    for r in read_claims(layout):
        if r["claim_id"] == claim_id:
            rec = r
    return rec


def test_detect_conflicts_populates_conflicts_with(tmp_path):
    """3.5 / H-05 adjacency: each conflicting claim's latest record carries the
    other claim's id in conflicts_with, so the graph projection emits the edge."""
    layout = WorkspaceLayout(init_workspace(tmp_path / "book"))
    append_claim(layout, _verified("clm-2026-000001", "Operation X is allowed."))
    append_claim(layout, _verified("clm-2026-000002", "Operation X is forbidden."))
    detect_conflicts(layout)
    a = _latest_record(layout, "clm-2026-000001")
    b = _latest_record(layout, "clm-2026-000002")
    assert "clm-2026-000002" in a.get("conflicts_with", [])
    assert "clm-2026-000001" in b.get("conflicts_with", [])
