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
from scripts.counter_claims import append_counter_claim
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


def test_contradiction_scan_matches_golden() -> None:
    """The EDN port reproduces the bermuda golden exactly (both empty).

    bermuda is a healthy book: no projected claim declares a ``conflicts_with``
    target, so the conflict-edge relation is empty and the scan returns nothing.
    The empty match is therefore vacuous on its own -- the synthetic firing test
    below carries the real proof.
    """
    golden = json.loads((GOLDEN_DIR / "contradiction_scan.json").read_text("utf-8"))
    assert _run("contradiction_scan", BERMUDA) == _canonical_golden(golden)


def test_contradiction_scan_fires_on_conflict(tmp_path: Path) -> None:
    """The MEANINGFUL firing test: a declared conflict edge surfaces the pair.

    Two verified (non-superseded, so they project) claims where clm 1 declares
    ``conflicts_with: [clm 2]``. The projector emits one directional
    ``claim_conflict`` row (claim_id=clm1, other_id=clm2), mirroring
    project_graph's once-per-target ``tbf:conflictsWith`` emission. The scan must
    return exactly the (clm1, clm2) pair -- and ONLY that direction, proving the
    edge projection and the join fire.
    """
    root = init_workspace(tmp_path / "ws")
    layout = WorkspaceLayout(root)

    def _claim(cid: str, conflicts: list[str]) -> dict:
        record = {
            "claim_id": cid,
            "canonical_text": f"claim {cid}",
            "status": "verified",
            "claim_type": "fact",
            "confidence": 0.9,
            "source_spans": [{"doc_id": "doc-1", "locator_text": "locator"}],
            "created_at": "2026-06-16T00:00:00+00:00",
        }
        if conflicts:
            record["conflicts_with"] = conflicts
        return record

    for record in (
        _claim("clm-2026-000001", ["clm-2026-000002"]),
        _claim("clm-2026-000002", []),
    ):
        append_claim(layout, record)

    store = CozoStore.in_memory(schema_path=SCHEMA_PATH)
    project_ledger(layout, store)
    script = compile_query(
        (QUERIES_DIR / "contradiction_scan.edn").read_text("utf-8"), SCHEMA_PATH
    )
    rows = store.query(script)

    assert _canonical(rows) == _canonical(
        [["clm-2026-000001", "clm-2026-000002"]]
    )


def test_orphan_wiki_pages_matches_golden() -> None:
    """The EDN port reproduces the bermuda golden exactly (both empty).

    bermuda has no ``wiki/`` directory, so project_graph emits zero
    ``tbf:WikiPage`` nodes and the projector loads zero ``wiki_page`` rows.
    With no pages there are no orphans, so the golden is ``[]``. The match is
    vacuous on its own -- the synthetic firing test below carries the proof.
    """
    golden = json.loads((GOLDEN_DIR / "orphan_wiki_pages.json").read_text("utf-8"))
    assert _run("orphan_wiki_pages", BERMUDA) == _canonical_golden(golden)


def test_orphan_wiki_pages_fires_on_orphan(tmp_path: Path) -> None:
    """The MEANINGFUL firing test: ONLY the unreferenced page returns.

    A workspace with a ``wiki/`` dir holding two ``.md`` pages. One page's
    relative path is the ``doc_id`` of a verified claim's source span (so a
    claim's ``hasSourceSpan`` lands on that page -- it is referenced); the other
    page is cited by nothing. The projector mints one ``wiki_page`` row per md
    file (mirroring project_graph's ``tbf:WikiPage`` emission) and back-links a
    source span to its page when the span's ``doc_id`` equals the page path. The
    orphan query must return exactly the unreferenced page, proving both the page
    projection and the two negations fire.
    """
    root = init_workspace(tmp_path / "ws")
    layout = WorkspaceLayout(root)

    referenced_rel = "concepts/referenced.md"
    orphan_rel = "concepts/orphan.md"
    for rel in (referenced_rel, orphan_rel):
        page = layout.wiki / rel
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text(f"# {rel}\n", encoding="utf-8")

    # One verified claim whose source span cites the *referenced* page (its
    # doc_id is that page's relative path), so the page is a claim source.
    append_claim(
        layout,
        {
            "claim_id": "clm-2026-000001",
            "canonical_text": "a verified claim sourced from a wiki page",
            "status": "verified",
            "claim_type": "fact",
            "confidence": 0.9,
            "source_spans": [
                {"doc_id": referenced_rel, "locator_text": "the cited locator text"}
            ],
            "created_at": "2026-06-16T00:00:00+00:00",
        },
    )

    store = CozoStore.in_memory(schema_path=SCHEMA_PATH)
    project_ledger(layout, store)
    script = compile_query(
        (QUERIES_DIR / "orphan_wiki_pages.edn").read_text("utf-8"), SCHEMA_PATH
    )
    returned = {r[0] for r in store.query(script)}

    # P5.2 canonical: page URIs are keyed on the path RELATIVE TO THE WIKI DIR, so a
    # SINGLE ``wiki/`` prefix (project_graph's doubled ``wiki/wiki/`` quirk dropped).
    # (init_workspace also seeds skeleton pages -- index/log/current-status -- which
    # are themselves unreferenced orphans; we assert ONLY on the page pair we control.)
    base = "https://example.org/book-knowledge/wiki/"
    assert f"{base}{orphan_rel}" in returned, "the unreferenced page must be an orphan"
    assert f"{base}{referenced_rel}" not in returned, (
        "the claim-sourced page must NOT be an orphan"
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


# --- counter-claim projection ports (REQ-KG-006) -------------------------------


def _cc(cc_id: str, target: str, status: str) -> dict:
    """A schema-valid counter-claim record targeting ``target`` with ``status``."""
    return {
        "id": cc_id,
        "target_claim_id": target,
        "text": "a counter-claim that rebuts the target claim",
        "disagreement_vector": "mechanism",
        "status": status,
        "provenance": {"generator": "test", "prompt_sha256": "0" * 64},
        "created_at": "2026-06-16T00:00:00+00:00",
    }


def test_rebuttal_presence_matches_golden() -> None:
    """The EDN port reproduces the bermuda golden exactly (both empty).

    bermuda's golden is ``[]``: every load-bearing, non-axiom claim that
    supports a chapter carries an ``addressed`` rebutting counter-claim, so the
    negation excludes them all. The empty match is vacuous on its own -- the
    synthetic firing test below carries the real proof.
    """
    golden = json.loads((GOLDEN_DIR / "rebuttal-presence.json").read_text("utf-8"))
    assert _run("rebuttal-presence", BERMUDA) == _canonical_golden(golden)


def test_rebuttal_presence_fires_on_unaddressed_rebuttal(tmp_path: Path) -> None:
    """The MEANINGFUL firing test: ONLY the exposed load-bearing claim returns.

    Four load-bearing claims, each supporting a chapter (so the supportsChapter
    join holds) and non-superseded (so they project):
      - clm 1: an OPEN rebutting counter-claim     -> exposed, MUST return.
      - clm 2: an ADDRESSED rebutting counter-claim -> excluded by the
               counter-claim negation arm.
      - clm 3: no counter-claim at all              -> exposed, MUST return.
      - clm 4: an axiom with an OPEN rebuttal       -> excluded by the axiom
               negation arm (axioms are exempt).
    Proves both negation arms (addressed-rebuttal AND axiom) fire independently.
    """
    root = init_workspace(tmp_path / "ws")
    layout = WorkspaceLayout(root)

    def _claim(cid: str, axiom: bool = False) -> dict:
        record = {
            "claim_id": cid,
            "canonical_text": f"a load-bearing claim {cid}",
            "status": "verified",
            "claim_type": "fact",
            "confidence": 0.9,
            "load_bearing": True,
            "source_spans": [{"doc_id": "doc-1", "locator_text": "locator text"}],
            "supports_chapters": ["ch-aaa"],
            "created_at": "2026-06-16T00:00:00+00:00",
        }
        if axiom:
            record["axiom"] = True
        return record

    for record in (
        _claim("clm-2026-000001"),
        _claim("clm-2026-000002"),
        _claim("clm-2026-000003"),
        _claim("clm-2026-000004", axiom=True),
    ):
        append_claim(layout, record)

    append_counter_claim(root, _cc("cc-2026-000001", "clm-2026-000001", "open"))
    append_counter_claim(root, _cc("cc-2026-000002", "clm-2026-000002", "addressed"))
    append_counter_claim(root, _cc("cc-2026-000004", "clm-2026-000004", "open"))

    store = CozoStore.in_memory(schema_path=SCHEMA_PATH)
    project_ledger(layout, store)
    script = compile_query(
        (QUERIES_DIR / "rebuttal-presence.edn").read_text("utf-8"), SCHEMA_PATH
    )
    rows = store.query(script)

    assert _canonical(rows) == _canonical(
        [["clm-2026-000001"], ["clm-2026-000003"]]
    )


def test_rebuttal_presence_uses_latest_counter_claim_status(tmp_path: Path) -> None:
    """P5.2 canonical: counter-claims dedupe to LATEST status per cc id.

    Two load-bearing chapter-supporting claims, each with a counter-claim that has
    STATUS HISTORY:
      - clm 1: cc went open -> addressed   -> latest 'addressed' -> EXCLUDED.
      - clm 2: cc reopened addressed -> open -> latest 'open'    -> EXPOSED.
    The reopened case is the discriminator: the OLD distinct-(cc,status) history set
    would still carry clm 2's 'addressed' fact and exclude it; latest-per-id drops
    it, so clm 2 surfaces. Counter-claim history is written directly to the ledger
    (order = recency) to control the transition.
    """
    root = init_workspace(tmp_path / "ws")
    layout = WorkspaceLayout(root)

    def _claim(cid: str) -> dict:
        return {
            "claim_id": cid,
            "canonical_text": f"a load-bearing claim {cid}",
            "status": "verified",
            "claim_type": "fact",
            "confidence": 0.9,
            "load_bearing": True,
            "source_spans": [{"doc_id": "doc-1", "locator_text": "locator text"}],
            "supports_chapters": ["ch-aaa"],
            "created_at": "2026-06-16T00:00:00+00:00",
        }

    append_claim(layout, _claim("clm-2026-000001"))
    append_claim(layout, _claim("clm-2026-000002"))

    # Write counter-claim history directly so file order = recency; latest_per keeps
    # the last record per cc id.
    records = [
        _cc("cc-2026-00000a", "clm-2026-000001", "open"),
        _cc("cc-2026-00000a", "clm-2026-000001", "addressed"),   # latest addressed
        _cc("cc-2026-00000b", "clm-2026-000002", "addressed"),
        _cc("cc-2026-00000b", "clm-2026-000002", "open"),        # reopened -> latest open
    ]
    (root / "claims" / "counter-claims.jsonl").write_text(
        "".join(json.dumps(r, sort_keys=True) + "\n" for r in records),
        encoding="utf-8", newline="\n",
    )

    store = CozoStore.in_memory(schema_path=SCHEMA_PATH)
    project_ledger(layout, store)
    script = compile_query(
        (QUERIES_DIR / "rebuttal-presence.edn").read_text("utf-8"), SCHEMA_PATH
    )
    # Only clm 2 (latest = open) is exposed; clm 1 (latest = addressed) is excluded.
    assert _canonical(store.query(script)) == _canonical([["clm-2026-000002"]])


def test_contested_rebuttal_window_matches_golden() -> None:
    """The EDN port reproduces the bermuda golden exactly (both empty).

    bermuda's golden is ``[]``: it has no ``disputed`` claims, so the positive
    body binds nothing. The empty match is vacuous on its own -- the synthetic
    firing test below carries the real proof.
    """
    golden = json.loads(
        (GOLDEN_DIR / "contested-rebuttal-window.json").read_text("utf-8")
    )
    assert _run("contested-rebuttal-window", BERMUDA) == _canonical_golden(golden)


def test_contested_rebuttal_window_fires_on_disputed_claim(tmp_path: Path) -> None:
    """The MEANINGFUL firing test: ONLY disputed chapter-supporting claims return.

    project_graph emits NO ``tbf:rebuttalWindowOk`` triple, so the SPARQL
    ``FILTER NOT EXISTS { ?claim tbf:rebuttalWindowOk ?chapter }`` never excludes
    anything: the query returns every disputed claim that supports a chapter. The
    relational ``rebuttal-window-ok`` relation is loaded empty (mirroring that
    never-emitted predicate), so the negation arm clears nothing.

      - clm 1: disputed, supports ch-aaa  -> MUST return (one row per chapter).
      - clm 2: disputed, supports ch-aaa AND ch-bbb -> two rows.
      - clm 3: verified, supports ch-aaa  -> excluded by status != disputed.
      - clm 4: disputed, supports no chapter -> excluded (no supportsChapter join).
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
            "source_spans": [{"doc_id": "doc-1", "locator_text": "locator text"}],
            "supports_chapters": chapters,
            "created_at": "2026-06-16T00:00:00+00:00",
        }

    base = "https://example.org/book-knowledge/chapters/"
    for record in (
        _claim("clm-2026-000001", "disputed", ["ch-aaa"]),
        _claim("clm-2026-000002", "disputed", ["ch-aaa", "ch-bbb"]),
        _claim("clm-2026-000003", "verified", ["ch-aaa"]),
        _claim("clm-2026-000004", "disputed", []),
    ):
        append_claim(layout, record)

    store = CozoStore.in_memory(schema_path=SCHEMA_PATH)
    project_ledger(layout, store)
    script = compile_query(
        (QUERIES_DIR / "contested-rebuttal-window.edn").read_text("utf-8"),
        SCHEMA_PATH,
    )
    rows = store.query(script)

    assert _canonical(rows) == _canonical(
        [
            ["clm-2026-000001", f"{base}ch-aaa"],
            ["clm-2026-000002", f"{base}ch-aaa"],
            ["clm-2026-000002", f"{base}ch-bbb"],
        ]
    )


# --- stale-after-source-refresh port (REQ-KG-006) ------------------------------


def test_stale_after_source_refresh_matches_golden() -> None:
    """The EDN port reproduces the bermuda golden exactly (both empty).

    bermuda's golden is ``[]``: its one manifest-backed claim (doc_id "thesis")
    was created at the SAME instant its source was ingested, so the strict
    ``?src_date > ?claim_date`` never fires. The empty match is vacuous on its own
    -- the synthetic firing test below carries the real proof.
    """
    golden = json.loads(
        (GOLDEN_DIR / "stale_after_source_refresh.json").read_text("utf-8")
    )
    assert _run("stale_after_source_refresh", BERMUDA) == _canonical_golden(golden)


def test_stale_after_source_refresh_fires(tmp_path: Path) -> None:
    """The MEANINGFUL firing test: ONLY the claim whose source post-dates it returns.

    Two verified claims, each derived (via a source span's doc_id) from a manifest
    source:
      - clm 1: source ingested 2026-06-10, claim created 2026-06-01 -> source is
               NEWER than the claim -> stale -> MUST return.
      - clm 2: source ingested 2026-06-01, claim created 2026-06-10 -> source
               PREDATES the claim -> not stale -> excluded by the date filter.
    The manifest source rows are written as raw JSON under raw/manifests/, mirroring
    project_graph's manifest pass; the claim->span->source join keys on doc_id and
    the var-vs-var ISO-8601 comparison decides staleness. Proves the source
    projection AND the var-vs-var filter fire.
    """
    root = init_workspace(tmp_path / "ws")
    layout = WorkspaceLayout(root)

    def _claim(cid: str, doc_id: str, created_at: str) -> dict:
        return {
            "claim_id": cid,
            "canonical_text": f"claim {cid}",
            "status": "verified",
            "claim_type": "fact",
            "confidence": 0.9,
            "source_spans": [{"doc_id": doc_id, "locator_text": "locator text"}],
            "created_at": created_at,
        }

    append_claim(layout, _claim("clm-2026-000001", "doc-stale", "2026-06-01T00:00:00+00:00"))
    append_claim(layout, _claim("clm-2026-000002", "doc-fresh", "2026-06-10T00:00:00+00:00"))

    # Source manifests: doc-stale was ingested AFTER its claim (stale); doc-fresh
    # was ingested BEFORE its claim (not stale). Mirrors project_graph's manifest
    # shape (doc_id + ingested_at).
    layout.manifests.mkdir(parents=True, exist_ok=True)
    (layout.manifests / "doc-stale.json").write_text(
        json.dumps({"doc_id": "doc-stale", "ingested_at": "2026-06-10T00:00:00+00:00"}),
        encoding="utf-8",
    )
    (layout.manifests / "doc-fresh.json").write_text(
        json.dumps({"doc_id": "doc-fresh", "ingested_at": "2026-06-01T00:00:00+00:00"}),
        encoding="utf-8",
    )

    store = CozoStore.in_memory(schema_path=SCHEMA_PATH)
    project_ledger(layout, store)
    script = compile_query(
        (QUERIES_DIR / "stale_after_source_refresh.edn").read_text("utf-8"),
        SCHEMA_PATH,
    )
    rows = store.query(script)

    assert _canonical(rows) == _canonical(
        [["clm-2026-000001", "2026-06-01T00:00:00+00:00", "2026-06-10T00:00:00+00:00"]]
    )
