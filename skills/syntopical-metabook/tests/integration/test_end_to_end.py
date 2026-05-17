"""End-to-end smoke test: empty fixture workspace → Acquire (stubbed) →
Synthesize → Project Lens → Gap Report → book-compose reads the lens.

Uses booklogic dev stub and monkeypatches the three network/ingest seam
helpers in download_and_ingest so the test stays hermetic.
torch/sentence-transformers are also stubbed so rank() works without them."""
import sys
from pathlib import Path
from types import SimpleNamespace
import pytest

ROOT = Path(__file__).resolve().parents[4]  # repo root
STUB = Path(__file__).resolve().parents[1] / "fixtures" / "booklogic_stub.py"


def _seed_workspace(tmp_path):
    ws = tmp_path / "ws"
    (ws / "raw").mkdir(parents=True)
    (ws / "claims").mkdir()
    (ws / "wiki" / "concepts").mkdir(parents=True)
    chap = ws / "chapters" / "ch-01"
    chap.mkdir(parents=True)
    (chap / "contract.yaml").write_text(
        "id: ch-01\ntitle: Finality\nsummary: chapter on finality\ntags: [finality]\n",
        encoding="utf-8")
    (chap / "thesis-tree.yaml").write_text(
        "chapter_id: ch-01\nnodes:\n"
        "  - node_id: n1\n    statement: Finality is irreversible.\n"
        "    tags: [finality]\n    required_evidence_kind: empirical\n"
        "    parent_id: null\n",
        encoding="utf-8")
    return ws


def test_e2e_acquire_synthesize_lens_gap(tmp_path, monkeypatch):
    monkeypatch.setenv("BOOKLOGIC_BIN", f"{sys.executable} {STUB}")
    ws = _seed_workspace(tmp_path)

    # ---- Acquire (stubbed seam) ----
    from scripts.acquire.rank_candidates import Candidate, ScoredCandidate
    from scripts.acquire import rank_candidates as rc_mod
    from scripts.acquire.triage import triage, TriageConfig
    from scripts.acquire.veto import apply_veto
    from scripts.acquire.download_and_ingest import download_and_ingest
    from scripts.acquire import download_and_ingest as dl_mod
    from scripts.acquire.manifest import append_run_record

    # Stub rank() so torch/sentence-transformers are not needed.
    def _stub_rank(query_text, candidates):
        return [ScoredCandidate(id=c.id, score=(0.9 if "finality" in c.abstract.lower() else 0.1))
                for c in candidates]

    monkeypatch.setattr(rc_mod, "rank", _stub_rank)

    candidates = [
        Candidate(id="arxiv:1", title="Finality proof",
                  abstract="proves finality of the longest chain rule"),
        Candidate(id="arxiv:2", title="Cooking", abstract="random unrelated"),
    ]
    scored = rc_mod.rank("Finality is irreversible", candidates)
    tr = triage(scored, TriageConfig(t_high=0.5, t_low=0.3, max_auto_per_run=5),
                workspace_root=ws, run_id="e2e-run")
    assert len(tr.auto_approve) >= 1

    class _Tree:
        chapter_id = "ch-01"
        nodes = []
    lookup = {c.id: {"id": c.id, "extracted_concepts": [],
                     "embedding_score": s.score}
              for s, c in zip(scored, candidates)}
    apply_veto(tr, _Tree(), lookup,
               manifest_path=ws / "syntopical" / "acquisition" / "manifest.jsonl")

    monkeypatch.setattr(dl_mod, "_download_pdf",
                        lambda u, d: SimpleNamespace(path=d, sha256=f"sha-{d.name}",
                                                     bytes=1000,
                                                     content_type="application/pdf"))
    monkeypatch.setattr(dl_mod, "_is_source_ingested", lambda sha, root: False)
    monkeypatch.setattr(dl_mod, "_ingest_pdf",
                        lambda s, r: SimpleNamespace(source_id=f"src-{s.name}",
                                                     sha256=f"sha-{s.name}",
                                                     claims_extracted=0,
                                                     wiki_pages_touched=[],
                                                     status="ingested"))
    outcomes = download_and_ingest(tr.auto_approve, workspace_root=ws)
    assert all(o.status == "ingested" for o in outcomes)
    append_run_record(ws / "syntopical" / "acquisition" / "manifest.jsonl",
                      {"run_id": "e2e-run",
                       "downloaded": [o.candidate_id for o in outcomes]})

    # ---- Synthesize (stubbed book-knowledge/book-thesis) ----
    from scripts.synthesize import topic_map as tm_mod
    from scripts.synthesize import disputed_questions as dq_mod
    from scripts.synthesize import concept_reconcile as cr_mod
    import yaml as _yaml

    def _read_tree(chap_id, root):
        raw = _yaml.safe_load((root / "chapters" / chap_id / "thesis-tree.yaml")
                              .read_text(encoding="utf-8"))
        return SimpleNamespace(chapter_id=raw["chapter_id"],
                               nodes=[SimpleNamespace(**n) for n in raw["nodes"]])

    fake_bk = SimpleNamespace(
        list_concepts=lambda root: [SimpleNamespace(slug="finality",
                                                    title="Finality",
                                                    sources=["s1"],
                                                    surface_forms=["finality"])],
        query_claims=lambda f, root: [
            SimpleNamespace(id="cl1", state="verified", tags=["finality"],
                            source_id="s1", body="proves finality", locator="p.1"),
        ],
    )
    fake_bt = SimpleNamespace(read_thesis_tree=_read_tree)
    for mod in (tm_mod, dq_mod, cr_mod):
        monkeypatch.setattr(mod, "_load_book_knowledge", lambda: fake_bk)
    monkeypatch.setattr(tm_mod, "_load_book_thesis", lambda: fake_bt)
    tm_mod.build_topic_map(ws, chapter_id="ch-01")
    dq_mod.build_disputed_questions(ws)
    cr_mod.build_concept_reconciliation(ws)

    # ---- Project Lens ----
    from scripts.lens.project_lens import project_lens
    lens_path = project_lens(workspace_root=ws, chapter_id="ch-01",
                              source_run_id="e2e-run")
    assert lens_path.exists()

    # ---- Gap Report ----
    from scripts.gap import coverage_report as gr
    monkeypatch.setattr(gr, "_load_book_knowledge", lambda: fake_bk)
    monkeypatch.setattr(gr, "_load_book_thesis", lambda: fake_bt)
    gap_path = gr.build_coverage_report(ws, chapter_id="ch-01", required_per_node=3)
    assert gap_path.exists()

    # ---- book-compose reads the lens (cross-skill integration) ----
    bc_path = str(ROOT / "skills" / "book-compose")
    if bc_path not in sys.path:
        sys.path.insert(0, bc_path)
    # Clear any stale 'scripts' imports (e.g. from syntopical-metabook above).
    # The book-compose skill_api doesn't use 'scripts', only 'skill_api', so
    # this is safe to remove.
    for k in list(sys.modules):
        if k == "skill_api":
            del sys.modules[k]
    import importlib
    skill_api = importlib.import_module("skill_api")
    read_lens = skill_api.read_lens
    Lens = skill_api.Lens

    lens = read_lens("ch-01", ws)
    assert isinstance(lens, Lens)
    assert lens.chapter_id == "ch-01"
    assert lens.source_run_id == "e2e-run"

    # ---- Final artifact sanity: the lens has all four sections ----
    body = lens_path.read_text(encoding="utf-8")
    for section in ("## Topics", "## Disputed Questions",
                    "## Concept Reconciliation", "## Coverage"):
        assert section in body, f"section {section!r} missing from lens"
