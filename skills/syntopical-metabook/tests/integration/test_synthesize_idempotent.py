import sys
from pathlib import Path
from types import SimpleNamespace

STUB = Path(__file__).resolve().parents[1] / "fixtures" / "booklogic_stub.py"

def _hash_dir(d: Path) -> dict:
    """Return a {relpath: sha256} map for stable comparison."""
    import hashlib
    out: dict = {}
    if not d.exists():
        return out
    for p in sorted(d.rglob("*")):
        if p.is_file():
            out[str(p.relative_to(d))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out

def test_synthesize_double_run_zero_diff(tmp_path, monkeypatch):
    """REQ-SYN-4: re-running synthesize with no upstream changes produces zero diffs."""
    monkeypatch.setenv("BOOKLOGIC_BIN", f"{sys.executable} {STUB}")
    # Build a fixture workspace
    ws = tmp_path / "ws"
    (ws / "claims").mkdir(parents=True)
    (ws / "wiki" / "concepts").mkdir(parents=True)
    chap = ws / "chapters" / "ch-01"
    chap.mkdir(parents=True)
    (chap / "thesis-tree.yaml").write_text(
        "chapter_id: ch-01\nnodes:\n"
        "  - node_id: n1\n    statement: x\n    tags: [finality]\n"
        "    required_evidence_kind: empirical\n    parent_id: null\n",
        encoding="utf-8")
    # Stub the three book-knowledge calls to return fixed data
    from scripts.synthesize import topic_map as tm_mod
    from scripts.synthesize import disputed_questions as dq_mod
    from scripts.synthesize import concept_reconcile as cr_mod
    fake_bk = SimpleNamespace(
        list_concepts=lambda root: [],
        query_claims=lambda f, root: [],
    )
    monkeypatch.setattr(tm_mod, "_load_book_knowledge", lambda: fake_bk)
    monkeypatch.setattr(dq_mod, "_load_book_knowledge", lambda: fake_bk)
    monkeypatch.setattr(cr_mod, "_load_book_knowledge", lambda: fake_bk)
    fake_bt = SimpleNamespace(read_thesis_tree=lambda chap, root: SimpleNamespace(
        chapter_id="ch-01", nodes=[]))
    monkeypatch.setattr(tm_mod, "_load_book_thesis", lambda: fake_bt)

    # Run synthesize twice
    tm_mod.build_topic_map(ws, chapter_id="ch-01")
    dq_mod.build_disputed_questions(ws)
    cr_mod.build_concept_reconciliation(ws)
    snap1 = _hash_dir(ws / "syntopical")
    tm_mod.build_topic_map(ws, chapter_id="ch-01")
    dq_mod.build_disputed_questions(ws)
    cr_mod.build_concept_reconciliation(ws)
    snap2 = _hash_dir(ws / "syntopical")
    assert snap1 == snap2, f"Idempotence violated. Diff: {set(snap1.items()) ^ set(snap2.items())}"
