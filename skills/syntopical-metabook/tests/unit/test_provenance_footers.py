"""NFR-8: every syntopical artifact must carry a provenance footer.

Runs the synthesize pipeline on a stub workspace and asserts that every
.md file written under syntopical/ contains the marker
'generated_by: syntopical-metabook'."""
from __future__ import annotations
from pathlib import Path
from types import SimpleNamespace


def _make_workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "ws"
    (ws / "claims").mkdir(parents=True)
    (ws / "wiki" / "concepts").mkdir(parents=True)
    chap = ws / "chapters" / "ch-01"
    chap.mkdir(parents=True)
    (chap / "contract.yaml").write_text(
        "id: ch-01\ntitle: Finality\nsummary: ...\ntags: [finality]\n",
        encoding="utf-8")
    (chap / "thesis-tree.yaml").write_text(
        "chapter_id: ch-01\nnodes:\n"
        "  - node_id: n1\n    statement: x\n    tags: [finality]\n"
        "    required_evidence_kind: empirical\n    parent_id: null\n",
        encoding="utf-8")
    return ws


def test_provenance_footer_present_in_all_syntopical_artifacts(tmp_path, monkeypatch):
    ws = _make_workspace(tmp_path)

    from scripts.synthesize import topic_map as tm_mod
    from scripts.synthesize import disputed_questions as dq_mod
    from scripts.synthesize import concept_reconcile as cr_mod
    from scripts.lens.project_lens import project_lens
    from scripts.gap import coverage_report as gr_mod
    import scripts.booklogic_adapter as bla_mod

    import yaml as _yaml

    def _read_tree(chap_id, root):
        raw = _yaml.safe_load(
            (root / "chapters" / chap_id / "thesis-tree.yaml").read_text(encoding="utf-8")
        )
        return SimpleNamespace(
            chapter_id=raw["chapter_id"],
            nodes=[SimpleNamespace(**n) for n in raw["nodes"]],
        )

    fake_bk = SimpleNamespace(
        list_concepts=lambda root: [
            SimpleNamespace(slug="finality", title="Finality",
                            sources=["s1"], surface_forms=["finality"])
        ],
        query_claims=lambda f, root: [
            SimpleNamespace(id="cl1", state="verified", tags=["finality"],
                            source_id="s1", body="proves finality", locator="p.1"),
        ],
    )
    fake_bt = SimpleNamespace(read_thesis_tree=_read_tree)

    for mod in (tm_mod, dq_mod, cr_mod):
        monkeypatch.setattr(mod, "_load_book_knowledge", lambda: fake_bk)
    monkeypatch.setattr(tm_mod, "_load_book_thesis", lambda: fake_bt)
    monkeypatch.setattr(gr_mod, "_load_book_knowledge", lambda: fake_bk)
    monkeypatch.setattr(gr_mod, "_load_book_thesis", lambda: fake_bt)
    # Stub the booklogic adapter so no subprocess is spawned.
    # These functions are imported by name into the module's namespace, so we
    # patch both the canonical location and the already-bound module attributes.
    monkeypatch.setattr(bla_mod, "disputed_questions", lambda claims: [])
    monkeypatch.setattr(bla_mod, "reconcile_concepts", lambda concepts: [])
    monkeypatch.setattr(dq_mod, "_booklogic_disputed_questions", lambda claims: [])
    monkeypatch.setattr(cr_mod, "_booklogic_reconcile_concepts", lambda concepts: [])

    # Run the full synthesis + lens + gap pipeline.
    tm_mod.build_topic_map(ws, chapter_id="ch-01")
    dq_mod.build_disputed_questions(ws)
    cr_mod.build_concept_reconciliation(ws)
    project_lens(workspace_root=ws, chapter_id="ch-01", source_run_id="prov-test")
    gr_mod.build_coverage_report(ws, chapter_id="ch-01", required_per_node=3)

    # Collect all .md files under syntopical/.
    syn_dir = ws / "syntopical"
    md_files = list(syn_dir.rglob("*.md"))
    assert md_files, "no markdown artifacts found under syntopical/"

    _MARKER = "generated_by: syntopical-metabook"
    missing: list[str] = []
    for f in md_files:
        body = f.read_text(encoding="utf-8")
        if _MARKER not in body:
            missing.append(str(f.relative_to(ws)))

    assert not missing, (
        f"Provenance footer missing from the following artifacts: {missing}"
    )
