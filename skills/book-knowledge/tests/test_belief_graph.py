from pathlib import Path
import json

from scripts.belief_graph import BeliefGraph, load_belief_graph
from scripts.workspace import init_workspace, WorkspaceLayout


def _seed(tmp_path: Path) -> Path:
    layout_root = init_workspace(tmp_path)
    layout = WorkspaceLayout(layout_root)
    claims = [
        {"claim_id": "clm-2026-000001", "canonical_text": "Claim A core.",
         "status": "verified", "claim_type": "fact", "confidence": 0.7,
         "source_spans": [{"doc_id": "src1", "locator_text": "A evidence"}],
         "created_at": "2026-05-11T00:00:00Z"},
        {"claim_id": "clm-2026-000002", "canonical_text": "Claim B derived.",
         "status": "verified", "claim_type": "fact", "confidence": 0.6,
         "source_spans": [{"doc_id": "src2", "locator_text": "B evidence"}],
         "derived_from": ["clm-2026-000001"],
         "created_at": "2026-05-11T00:00:00Z"},
    ]
    with layout.ledger.open("w", encoding="utf-8") as fh:
        for c in claims:
            fh.write(json.dumps(c) + "\n")
    return layout_root


def test_load_belief_graph_picks_up_derivation_edges(tmp_path):
    root = _seed(tmp_path)
    bg = load_belief_graph(root)
    assert "clm-2026-000001" in bg.nodes
    assert "clm-2026-000002" in bg.nodes
    assert ("clm-2026-000001", "clm-2026-000002") in bg.derivation_edges


def test_node_carries_status_and_sources(tmp_path):
    root = _seed(tmp_path)
    bg = load_belief_graph(root)
    n = bg.nodes["clm-2026-000001"]
    assert n.status == "verified"
    assert n.sources == ["src1"]
