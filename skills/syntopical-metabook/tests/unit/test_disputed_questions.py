import os
import sys
from pathlib import Path
from types import SimpleNamespace
from scripts.synthesize.disputed_questions import build_disputed_questions

STUB = Path(__file__).resolve().parents[1] / "fixtures" / "booklogic_stub.py"

def test_writes_one_file_per_topic(tmp_path, monkeypatch):
    # Patch the booklogic adapter to return a fake DisputedQuestion grouped by topic
    from scripts.booklogic_adapter import DisputedQuestion, Position
    fake_results = [
        DisputedQuestion(topic="finality", question="(asserts is-irreversible)",
                         positions=[
                             Position(claim_id="cl1", source_id="s1", stance="(asserts yes)",
                                      rewrite_witness="rule-1"),
                             Position(claim_id="cl2", source_id="s2", stance="(asserts no)",
                                      rewrite_witness="rule-2"),
                         ]),
    ]
    import scripts.synthesize.disputed_questions as dq
    monkeypatch.setattr(dq, "_booklogic_disputed_questions", lambda claims: fake_results)
    fake_bk = SimpleNamespace(query_claims=lambda f, root: [
        SimpleNamespace(id="cl1", state="verified", tags=["finality"], source_id="s1",
                        body="...", locator="p.1"),
        SimpleNamespace(id="cl2", state="verified", tags=["finality"], source_id="s2",
                        body="...", locator="p.2"),
    ])
    monkeypatch.setattr(dq, "_load_book_knowledge", lambda: fake_bk)
    build_disputed_questions(tmp_path)
    body = (tmp_path / "syntopical" / "disputed-questions" / "finality.md").read_text(encoding="utf-8")
    assert "| Question | Position | Source | Claim-ID | Rewrite-witness | Evidence locator |" in body
    assert "rule-1" in body
    assert "rule-2" in body

def test_empty_response_clears_existing(tmp_path, monkeypatch):
    # Pre-existing file that should be cleared on empty response
    d = tmp_path / "syntopical" / "disputed-questions"
    d.mkdir(parents=True)
    stale = d / "finality.md"
    stale.write_text("stale", encoding="utf-8")
    import scripts.synthesize.disputed_questions as dq
    monkeypatch.setattr(dq, "_booklogic_disputed_questions", lambda claims: [])
    fake_bk = SimpleNamespace(query_claims=lambda f, root: [])
    monkeypatch.setattr(dq, "_load_book_knowledge", lambda: fake_bk)
    build_disputed_questions(tmp_path)
    assert not stale.exists()
