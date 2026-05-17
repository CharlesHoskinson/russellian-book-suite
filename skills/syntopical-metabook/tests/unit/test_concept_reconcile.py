from pathlib import Path
from types import SimpleNamespace
from scripts.booklogic_adapter import CanonicalConcept, Alternate
from scripts.synthesize.concept_reconcile import build_concept_reconciliation

def test_writes_one_file_per_canonical_concept(tmp_path, monkeypatch):
    fake_results = [
        CanonicalConcept(slug="nakamoto-consensus", alternates=[
            Alternate(slug="longest-chain", surface_form="longest-chain rule",
                      source_id="s1", rewrite_witness="rule-unify-1"),
            Alternate(slug="bitcoin-consensus", surface_form="Bitcoin consensus",
                      source_id="s2", rewrite_witness="rule-unify-2"),
        ]),
    ]
    import scripts.synthesize.concept_reconcile as cr
    monkeypatch.setattr(cr, "_booklogic_reconcile_concepts", lambda concepts: fake_results)
    fake_bk = SimpleNamespace(list_concepts=lambda root: [])
    monkeypatch.setattr(cr, "_load_book_knowledge", lambda: fake_bk)
    build_concept_reconciliation(tmp_path)
    out = tmp_path / "syntopical" / "concepts" / "nakamoto-consensus.md"
    body = out.read_text(encoding="utf-8")
    assert "nakamoto-consensus" in body
    assert "longest-chain" in body
    assert "rule-unify-1" in body
    assert "bitcoin-consensus" in body
