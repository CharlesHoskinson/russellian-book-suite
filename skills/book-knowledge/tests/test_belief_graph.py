import pytest

pytestmark = pytest.mark.windows_canary

from pathlib import Path
import json
import pytest

from scripts.belief_graph import load_belief_graph, prior_for_status
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


def test_prior_for_status_defaults():
    assert prior_for_status("verified")   == 0.7
    assert prior_for_status("proposed")   == 0.5
    assert prior_for_status("disputed")   == 0.2
    assert prior_for_status("refuted")    == 0.05
    assert prior_for_status("superseded") == 0.5


def test_prior_for_status_unknown_raises():
    with pytest.raises(ValueError):
        prior_for_status("anything-else")


def test_source_trust_defaults_to_one(tmp_path):
    root = _seed(tmp_path)
    from scripts.belief_graph import load_source_trust
    trust = load_source_trust(root)
    assert trust.get("src1", 1.0) == 1.0
    assert trust.get("missing-doc", 1.0) == 1.0


def test_source_trust_reads_manifest_field(tmp_path):
    root = _seed(tmp_path)
    manifest_dir = root / "raw" / "manifests"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    (manifest_dir / "src1.json").write_text(
        '{"doc_id": "src1", "trust": 0.6}', encoding="utf-8"
    )
    from scripts.belief_graph import load_source_trust
    trust = load_source_trust(root)
    assert trust["src1"] == 0.6
