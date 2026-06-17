# RDF↔Cozo query-divergence decisions (P5.2, REQ-KG-017)

The P0/P1 query ports (`docs/audits/2026-06-16-homoiconic-kg-p0p1-audit.md`)
documented three places where the EDN/Cozo competency queries diverge from the
legacy rdflib/SPARQL ones, deferred to P5. This records the canonical decision for
each. The legacy RDF path (`project_graph` + the `.rq` files) is retired in P5.4;
the query-port goldens (`tests/golden/kg/`) were captured from the RDF path and run
ONLY against the Cozo path (`test_query_ports._run`), and **every bermuda golden is
unchanged by these decisions** (verified below), so no golden was rewritten.

## 1. `stale_after_source_refresh` — ADOPT the Cozo doc_id join (canonical)

The `.rq` join is structurally DEAD over the RDF projection: `prov:wasDerivedFrom`
points at the source-SPAN URI (`…/sources/<doc>#<locator>`) while
`schema:dateCreated` lands on the BARE manifest URI (`…/sources/<doc>`), so
`?src schema:dateCreated ?src_date` never binds — the SPARQL always returns empty.
The Cozo port implements the INTENDED join (claim → source-span → source on
`doc_id`).

**Decision:** the corrected doc_id join is canonical. No `project_graph` URI-minting
fix (it's retired in P5.4). **Real-data impact:** none — bermuda claims were each
created at the instant their source was ingested (equal, not strictly later), so
both return empty; the synthetic fire test (`test_query_ports.py`) proves the Cozo
port fires on a genuinely refreshed source.

## 2. `unsupported_claims` — source-span is the canonical provenance signal

The `.rq` negates `prov:wasDerivedFrom`, which `project_graph` emitted for BOTH
source spans AND `derived_from` claim refs. The Cozo port negates only the
source-span back-ref, so a verified claim whose only "provenance" is a
`derived_from` link to another claim is flagged unsupported by Cozo, not by SPARQL.

**Decision:** source-span is the intended provenance signal. A claim that derives
from another claim but has NO source of its own IS unsupported — the Cozo
(source-span-only) negation is canonical; `derived_from` is deliberately not
projected into it. **Real-data impact:** none — bermuda has zero `derived_from`
claims, so the golden coincides.

## 3a. wiki-page URI — DROP the doubled `wiki/wiki/` prefix (canonical)

`project_graph` minted `{BASE}wiki/{rel-to-ROOT}` where the root-relative path
already started with `wiki/`, giving a doubled `…/wiki/wiki/…`; the Cozo projector
mirrored the quirk byte-for-byte.

**Decision:** key the page URI on the path RELATIVE TO THE WIKI DIR → a single
`…/wiki/<path>` prefix (`project_ledger_cozo._wiki_page_uri`). **Real-data impact:**
none — bermuda has no `wiki/` directory (the `orphan_wiki_pages` golden is empty).
Only the synthetic `test_orphan_wiki_pages_fires_on_orphan` asserted the doubled
prefix; updated to the single prefix.

## 3b. counter-claim status — DEDUPE to latest-per-id (canonical)

`project_graph` emitted one `tbf:ccStatus` triple per counter-claim RECORD; as an
RDF set this kept every distinct `(cc, status)` tuple, so a cc that went
`open → addressed` carried BOTH facts. The Cozo projector mirrored that history set
(keyed by the synthetic `(cc-id . cc-status)` pair).

**Decision (user-confirmed 2026-06-17):** project ONE row per counter-claim carrying
its LATEST status (`latest_per` over the append-only ledger), keyed by the bare cc
id. The QA gate (`rebuttal-presence`) acts on the CURRENT status: an
`addressed → open` reopened rebuttal is treated as unaddressed (exposed). This
reverses the earlier history-preserving design.

**Real-data impact:** none on bermuda's current results — all 9 bermuda
counter-claims went `open → addressed` (latest = `addressed`), so the `addressed`
fact still exists post-dedupe and `rebuttal-presence` / `contested-rebuttal-window`
stay empty (`[]`). The behaviour only differs for an `addressed → open` reopen,
which bermuda has none of; the new `test_rebuttal_presence_uses_latest_counter_claim_status`
fire test pins exactly that discriminating case.

## Verification
book-knowledge **320 passed** (incl. all 8 query-port goldens unchanged + the new
cc-dedupe fire test + the updated wiki fire test); book-thesis **65**, book-compose
`query_chapter_evidence` **4** (cross-skill consumers of the shared schema /
projector unaffected).
