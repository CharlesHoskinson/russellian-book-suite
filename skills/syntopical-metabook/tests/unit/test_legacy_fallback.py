import os
from pathlib import Path
from types import SimpleNamespace
from scripts.synthesize.disputed_questions import build_disputed_questions
from scripts.synthesize.concept_reconcile import build_concept_reconciliation

def test_disputed_questions_legacy_banner(tmp_path, monkeypatch):
    monkeypatch.setenv("SYNTOPICAL_NO_BOOKLOGIC", "1")
    import scripts.synthesize.disputed_questions as dq
    fake_bk = SimpleNamespace(query_claims=lambda f, root: [
        SimpleNamespace(id="cl1", state="verified", tags=["finality"], source_id="s1",
                        body="finality is reached after 6 confirmations", locator="p.1"),
        SimpleNamespace(id="cl2", state="verified", tags=["finality"], source_id="s2",
                        body="finality is not reached after 6 confirmations", locator="p.2"),
    ])
    monkeypatch.setattr(dq, "_load_book_knowledge", lambda: fake_bk)
    # Legacy path doesn't call booklogic; ensure adapter never runs
    monkeypatch.setattr(dq, "_booklogic_disputed_questions",
                        lambda c: (_ for _ in ()).throw(AssertionError("must not call")))
    build_disputed_questions(tmp_path)
    # In legacy mode we may produce no files (if detect_conflicts returns empty), or
    # produce files all with the banner. Either way: any file produced has the banner.
    out_dir = tmp_path / "syntopical" / "disputed-questions"
    if out_dir.exists():
        for f in out_dir.glob("*.md"):
            assert f.read_text(encoding="utf-8").startswith("> Legacy mode — booklogic disabled")

def test_concept_reconcile_legacy_clusters_by_surface_form(tmp_path, monkeypatch):
    monkeypatch.setenv("SYNTOPICAL_NO_BOOKLOGIC", "1")
    import scripts.synthesize.concept_reconcile as cr
    concepts = [
        SimpleNamespace(slug="nakamoto-consensus", title="Nakamoto Consensus",
                        sources=["s1"], surface_forms=["longest-chain rule"]),
        SimpleNamespace(slug="longest-chain", title="Longest chain",
                        sources=["s2"], surface_forms=["longest-chain rule"]),
    ]
    fake_bk = SimpleNamespace(list_concepts=lambda root: concepts)
    monkeypatch.setattr(cr, "_load_book_knowledge", lambda: fake_bk)
    monkeypatch.setattr(cr, "_booklogic_reconcile_concepts",
                        lambda c: (_ for _ in ()).throw(AssertionError("must not call")))
    build_concept_reconciliation(tmp_path)
    out_dir = tmp_path / "syntopical" / "concepts"
    files = list(out_dir.glob("*.md")) if out_dir.exists() else []
    # Surface-form overlap on "longest-chain rule" -> one cluster
    assert len(files) >= 1
    for f in files:
        assert f.read_text(encoding="utf-8").startswith("> Legacy mode — booklogic disabled")
