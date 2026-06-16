"""H-06 (Sprint 4): run_bermuda_counter_claim_gen is idempotent — a second run
does not append a duplicate set of counter-claims."""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
sys.path.insert(0, str(REPO / "skills" / "book-knowledge"))

import run_bermuda_counter_claim_gen as tool  # noqa: E402
from scripts.workspace import init_workspace, WorkspaceLayout  # noqa: E402
from scripts.ledger import append_claim  # noqa: E402


def _seed(ws: Path):
    init_workspace(ws)
    layout = WorkspaceLayout(ws)
    for cid in tool.RIVALS:
        append_claim(layout, {
            "claim_id": cid,
            "canonical_text": f"Load-bearing claim {cid} about Bermuda's structure.",
            "status": "verified", "claim_type": "fact", "confidence": 0.9,
            "source_spans": [{"doc_id": "bermuda", "locator_text": "loc-text"}],
            "created_at": "2026-05-11T00:00:00Z", "load_bearing": True,
        })


def _count_counter_claims(ws: Path) -> int:
    path = ws / "claims" / "counter-claims.jsonl"
    if not path.exists():
        return 0
    return len([l for l in path.read_text(encoding="utf-8").splitlines() if l.strip()])


def test_second_run_is_idempotent(tmp_path):
    ws = tmp_path / "book"
    _seed(ws)
    first = tool.generate(ws)
    n_after_first = _count_counter_claims(ws)
    assert n_after_first > 0
    assert sum(len(v) for v in first.values()) == n_after_first

    second = tool.generate(ws)
    n_after_second = _count_counter_claims(ws)
    assert n_after_second == n_after_first, "second run appended duplicate counter-claims"
    assert all(v == [] for v in second.values()), "second run should skip all cids"
