"""Equivalence tests for the EDN->Cozo competency-query ports (REQ-KG-006).

Each ported booklogic ``defquery`` (under ``assets/kg-queries/``) must reproduce
its characterization golden (P0.1) exactly when compiled (P0.5) and run (P0.3)
over the projected ledger (P0.6). This module is the per-query match gate that
``test_characterization`` defers to.

The golden on bermuda is empty for ``unsupported_claims`` (a healthy book — every
verified claim carries a source span), so the golden match alone would pass even
for a broken negation. The synthetic firing test is therefore the load-bearing
one: it builds a workspace with one sourced and one sourceless verified claim and
asserts the query returns ONLY the sourceless id.
"""
from __future__ import annotations

import json
from pathlib import Path

from scripts.booklogic_kg import compile_query
from scripts.cozo_store import CozoStore
from scripts.ledger import append_claim
from scripts.project_ledger_cozo import project_ledger
from scripts.workspace import WorkspaceLayout, init_workspace

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = SKILL_ROOT / "assets" / "kg-schema.edn"
QUERIES_DIR = SKILL_ROOT / "assets" / "kg-queries"
GOLDEN_DIR = Path(__file__).parent / "golden" / "kg"
REPO_ROOT = SKILL_ROOT.parents[1]
BERMUDA = REPO_ROOT / "examples" / "bermuda-manual"


def _canonical(rows: list[list]) -> list[str]:
    """Canonical (order-independent) form of a result set.

    Result-set equality is an unordered multiset compared after a canonical
    sort (spec Definitions; mirrors ``test_determinism._canonical``). Cells are
    coerced to str so a Cozo row compares equal to the golden's str bindings.
    """
    return sorted(json.dumps([str(c) for c in r], sort_keys=True) for r in rows)


def _canonical_golden(golden: list[dict]) -> list[str]:
    """Canonicalize golden binding-dicts into the same comparable form.

    Each golden row is a dict of SPARQL bindings (e.g. ``{"claim": "..."}``);
    the dict's values, in key-sorted order, are the row's cells.
    """
    rows = [[d[k] for k in sorted(d)] for d in golden]
    return _canonical(rows)


def _run(name: str, workspace: Path) -> list[str]:
    """Project ``workspace``, compile+run ``<name>.edn``, return canonical rows."""
    store = CozoStore.in_memory(schema_path=SCHEMA_PATH)
    project_ledger(WorkspaceLayout(workspace), store)
    edn = (QUERIES_DIR / f"{name}.edn").read_text(encoding="utf-8")
    script = compile_query(edn, SCHEMA_PATH)
    return _canonical(store.query(script))


def test_unsupported_claims_matches_golden() -> None:
    """The EDN port reproduces the bermuda golden exactly (both empty)."""
    golden = json.loads((GOLDEN_DIR / "unsupported_claims.json").read_text("utf-8"))
    assert _run("unsupported_claims", BERMUDA) == _canonical_golden(golden)


def test_unsupported_claims_fires_on_sourceless_claim(tmp_path: Path) -> None:
    """The MEANINGFUL test: the negation actually isolates the sourceless claim.

    Two verified claims — one WITH a source span, one WITHOUT. The query must
    return exactly the sourceless one, proving the negation fires (guards the
    empty-oracle trap).

    A verified claim that lacks source spans cannot be written through
    ``append_claim`` (the ledger schema requires ``source_spans`` to be
    non-empty — by design, a verified claim should carry provenance). The
    sourceless record is therefore appended as raw JSONL to model exactly the
    data-quality gap ``unsupported_claims`` audits: a verified claim whose
    ledger record carries no provenance. The projector reads the ledger
    unvalidated, so this drives the real projection path.
    """
    root = init_workspace(tmp_path / "ws")
    layout = WorkspaceLayout(root)
    append_claim(
        layout,
        {
            "claim_id": "clm-2026-000001",
            "canonical_text": "a verified claim that has a source span attached",
            "status": "verified",
            "claim_type": "fact",
            "confidence": 0.9,
            "source_spans": [
                {"doc_id": "doc-1", "locator_text": "the source locator text"}
            ],
            "created_at": "2026-06-16T00:00:00+00:00",
        },
    )
    sourceless = {
        "claim_id": "clm-2026-000002",
        "canonical_text": "a verified claim with no source span whatsoever",
        "status": "verified",
        "claim_type": "fact",
        "confidence": 0.9,
        "source_spans": [],
        "created_at": "2026-06-16T00:00:00+00:00",
    }
    with layout.ledger.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(sourceless, sort_keys=True) + "\n")

    store = CozoStore.in_memory(schema_path=SCHEMA_PATH)
    project_ledger(layout, store)
    script = compile_query(
        (QUERIES_DIR / "unsupported_claims.edn").read_text("utf-8"), SCHEMA_PATH
    )
    rows = store.query(script)

    assert _canonical(rows) == _canonical([["clm-2026-000002"]])


def test_chapter_evidence_coverage_matches_golden() -> None:
    """The EDN port reproduces the non-empty bermuda golden exactly.

    This is the meaningful end-to-end proof: bermuda's golden has 10 rows (one
    per chapter, each with one verified supporting claim). The COUNT-aggregating
    SPARQL must reproduce identically through the EDN->Cozo path.
    """
    golden = json.loads(
        (GOLDEN_DIR / "chapter_evidence_coverage.json").read_text("utf-8")
    )
    assert _run("chapter_evidence_coverage", BERMUDA) == _canonical_golden(golden)


def test_chapter_evidence_coverage_counts_distinct_verified(tmp_path: Path) -> None:
    """The MEANINGFUL firing test: count is DISTINCT-verified, grouped by chapter.

    Two chapters with a known mix:
      - ch-aaa: two verified claims (counts 2) plus one proposed claim (excluded).
      - ch-bbb: one verified claim (counts 1).
    A verified claim supporting BOTH chapters must contribute to each group.
    """
    root = init_workspace(tmp_path / "ws")
    layout = WorkspaceLayout(root)

    def _claim(cid: str, status: str, chapters: list[str]) -> dict:
        return {
            "claim_id": cid,
            "canonical_text": f"claim {cid}",
            "status": status,
            "claim_type": "fact",
            "confidence": 0.9,
            "source_spans": [
                {"doc_id": "doc-1", "locator_text": "locator text"}
            ],
            "supports_chapters": chapters,
            "created_at": "2026-06-16T00:00:00+00:00",
        }

    base = "https://example.org/book-knowledge/chapters/"
    # ch-aaa: clm 1 (verified), clm 2 (verified, also supports ch-bbb),
    #         clm 3 (proposed -> excluded). ch-bbb: clm 2 only.
    for record in (
        _claim("clm-2026-000001", "verified", ["ch-aaa"]),
        _claim("clm-2026-000002", "verified", ["ch-aaa", "ch-bbb"]),
        _claim("clm-2026-000003", "proposed", ["ch-aaa"]),
    ):
        append_claim(layout, record)

    store = CozoStore.in_memory(schema_path=SCHEMA_PATH)
    project_ledger(layout, store)
    script = compile_query(
        (QUERIES_DIR / "chapter_evidence_coverage.edn").read_text("utf-8"),
        SCHEMA_PATH,
    )
    rows = store.query(script)

    assert _canonical(rows) == _canonical(
        [[f"{base}ch-aaa", 2], [f"{base}ch-bbb", 1]]
    )


def test_posterior_floor_matches_golden() -> None:
    """The EDN port reproduces the bermuda golden exactly (both empty).

    bermuda's golden is ``[]``: the lowest *projected* posterior is 0.4299, above
    the 0.4 floor (the sub-floor 0.3685 claims are superseded, so the projector
    drops them). The empty match alone is therefore vacuous -- the synthetic
    firing test below carries the real proof. To keep this gate non-vacuous we
    also assert bermuda actually projects claims that carry posteriors (so the
    query ran over real data, it just found none below the floor).
    """
    golden = json.loads((GOLDEN_DIR / "posterior-floor.json").read_text("utf-8"))
    assert _run("posterior-floor", BERMUDA) == _canonical_golden(golden)

    # Non-vacuity: bermuda DOES project claims carrying a (non-null) posterior --
    # the query found none below the floor, not none at all. (An ordered compare
    # against a null cell errors in Cozo, so guard with !is_null, mirroring the
    # compiler's lowering.)
    store = CozoStore.in_memory(schema_path=SCHEMA_PATH)
    project_ledger(WorkspaceLayout(BERMUDA), store)
    with_posterior = store.query(
        "?[claim, p] := *claim{id: claim, p_posterior: p}, !is_null(p), p >= 0.0"
    )
    assert with_posterior, "bermuda should project claims carrying p_posterior"


def test_posterior_floor_fires_below_threshold(tmp_path: Path) -> None:
    """The MEANINGFUL firing test: ONLY the sub-floor, non-pinned claim returns.

    Three verified claims, each supporting a chapter so the supportsChapter join
    is satisfied:
      - clm 1: posterior 0.3 (below floor), not pinned -> MUST return.
      - clm 2: posterior 0.9 (above floor)             -> excluded by ``< 0.4``.
      - clm 3: posterior 0.3 (below floor) but pinned  -> excluded by the
               pin-low-confidence negation.
    All three are non-superseded so they project. The query must return exactly
    clm 1, proving both the ordered comparison and the pin negation fire.
    """
    root = init_workspace(tmp_path / "ws")
    layout = WorkspaceLayout(root)

    def _claim(cid: str, posterior: float, pinned: bool) -> dict:
        return {
            "claim_id": cid,
            "canonical_text": f"claim {cid}",
            "status": "verified",
            "claim_type": "fact",
            "confidence": 0.9,
            "p_posterior": posterior,
            "pin_low_confidence": pinned,
            "source_spans": [{"doc_id": "doc-1", "locator_text": "locator"}],
            "supports_chapters": ["ch-aaa"],
            "created_at": "2026-06-16T00:00:00+00:00",
        }

    for record in (
        _claim("clm-2026-000001", 0.3, False),
        _claim("clm-2026-000002", 0.9, False),
        _claim("clm-2026-000003", 0.3, True),
    ):
        append_claim(layout, record)

    store = CozoStore.in_memory(schema_path=SCHEMA_PATH)
    project_ledger(layout, store)
    script = compile_query(
        (QUERIES_DIR / "posterior-floor.edn").read_text("utf-8"), SCHEMA_PATH
    )
    rows = store.query(script)

    assert _canonical(rows) == _canonical([["clm-2026-000001", 0.3]])
