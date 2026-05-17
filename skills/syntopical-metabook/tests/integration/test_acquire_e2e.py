"""End-to-end Acquire smoke test against a fixture workspace.

Uses the booklogic stub (BOOKLOGIC_BIN) and monkeypatches the network-touching
pieces so the test stays hermetic."""
import os
import sys
import json
from pathlib import Path
from types import SimpleNamespace
import pytest

STUB = Path(__file__).resolve().parents[1] / "fixtures" / "booklogic_stub.py"

def _workspace(tmp_path):
    """Build a minimal fixture workspace with one chapter contract and thesis tree."""
    ws = tmp_path / "ws"
    (ws / "raw").mkdir(parents=True)
    (ws / "claims").mkdir()
    (ws / "wiki" / "concepts").mkdir(parents=True)
    (ws / "graph").mkdir()
    chap = ws / "chapters" / "ch-01"
    chap.mkdir(parents=True)
    (chap / "contract.yaml").write_text(
        "id: ch-01\ntitle: Finality\nsummary: A chapter on finality.\n"
        "tags: [finality, longest-chain]\n", encoding="utf-8")
    (chap / "thesis-tree.yaml").write_text(
        "chapter_id: ch-01\n"
        "nodes:\n"
        "  - node_id: n1\n"
        "    statement: Finality is irreversible.\n"
        "    tags: [finality]\n"
        "    required_evidence_kind: empirical\n"
        "    parent_id: null\n",
        encoding="utf-8")
    return ws

@pytest.fixture
def use_stub(monkeypatch):
    monkeypatch.setenv("BOOKLOGIC_BIN", f"{sys.executable} {STUB}")

def test_e2e_acquire_with_stubbed_network(tmp_path, monkeypatch, use_stub):
    from scripts.acquire.rank_candidates import rank, Candidate
    from scripts.acquire.triage import triage, TriageConfig
    from scripts.acquire.veto import apply_veto
    from scripts.acquire.download_and_ingest import download_and_ingest
    from scripts.acquire.manifest import append_run_record, halt_check
    from scripts.acquire import download_and_ingest as dl_mod

    ws = _workspace(tmp_path)

    # Build candidates directly (no network expansion)
    candidates = [
        Candidate(id="arxiv:2310.04673", title="Finality proof",
                  abstract="proves finality of the longest chain rule"),
        Candidate(id="arxiv:9999.99999", title="Cooking recipes",
                  abstract="random unrelated content"),
    ]
    scored = rank("Finality is irreversible", candidates)
    cfg = TriageConfig(t_high=0.5, t_low=0.3, max_auto_per_run=5)
    tr = triage(scored, cfg, workspace_root=ws, run_id="run-e2e")
    assert len(tr.auto_approve) >= 1  # at least one relevant candidate above 0.5

    # Apply veto using the stub
    class _Tree:
        chapter_id = "ch-01"
        nodes = []
    lookup = {c.id: {"id": c.id, "extracted_concepts": [], "embedding_score": s.score}
              for s, c in zip(scored, candidates)}
    apply_veto(tr, _Tree(), lookup, manifest_path=ws / "syntopical" / "acquisition" / "manifest.jsonl")

    # Stub download_and_ingest end-to-end
    monkeypatch.setattr(dl_mod, "_download_pdf",
                        lambda url, dest: SimpleNamespace(
                            path=dest, sha256=f"sha-{dest.name}", bytes=1000,
                            content_type="application/pdf"))
    monkeypatch.setattr(dl_mod, "_is_source_ingested", lambda sha, root: False)
    monkeypatch.setattr(dl_mod, "_ingest_pdf",
                        lambda src, root: SimpleNamespace(
                            source_id=f"src-{src.name}", sha256=f"sha-{src.name}",
                            claims_extracted=0, wiki_pages_touched=[], status="ingested"))

    outcomes = download_and_ingest(tr.auto_approve, workspace_root=ws)
    assert all(o.status == "ingested" for o in outcomes)

    # Write a run record to manifest
    append_run_record(ws / "syntopical" / "acquisition" / "manifest.jsonl", {
        "run_id": "run-e2e", "auto_approved": [c.id for c in tr.auto_approve],
        "manual_review": [c.id for c in tr.manual_review],
        "rejected_n": len(tr.reject),
        "downloaded": [{"id": o.candidate_id, "sha256": o.sha256} for o in outcomes],
    })
    manifest_lines = (ws / "syntopical" / "acquisition" / "manifest.jsonl"
                      ).read_text(encoding="utf-8").strip().splitlines()
    assert len(manifest_lines) >= 1
    record = json.loads(manifest_lines[-1])
    assert record["run_id"] == "run-e2e"
    assert len(record["downloaded"]) == len(tr.auto_approve)
