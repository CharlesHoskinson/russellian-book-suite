# Graph audit playbook

The graph layer projects the claim ledger and source manifests into RDF, validates them with SHACL, and answers competency queries with SPARQL. The release gate uses this layer to decide whether a chapter ships.

## TriG dataset structure

`graph/dataset.trig` is a single file containing the full RDF dataset. Named graphs partition triples by function:

- `<base>/graphs/claims/<claim_id>` — one graph per claim. Holds the claim record and its source spans as RDF.
- `<base>/graphs/chapters/<chapter_id>` — one graph per chapter contract. Holds chapter metadata and citations.
- `<base>/graphs/wiki/<page_slug>` — one graph per wiki concept or entity page. Holds backlink and tag metadata.
- `<base>/graphs/runs/<run_id>` — one graph per ingest or audit run. Holds PROV-O activity records.
- `<base>/graphs/reports/<report_id>` — one graph per generated report (SHACL run, competency batch).

The default (unnamed) graph mirrors the union of all named graphs. Mirroring exists for legacy SPARQL clients that issue queries without `FROM NAMED` and would otherwise see an empty store. Modern queries should target named graphs explicitly.

## Naming convention

`<base>/graphs/<scope>/<id>` where scope ∈ `{claims, chapters, wiki, runs, reports}`. The base IRI is fixed per workspace; ids are the same identifiers used elsewhere (claim_id, chapter_id, page slug, etc.). The convention is enforced by `scripts/project_graph.py`; do not invent new scopes without extending the schema.

## PROV-O usage

Every claim is a `prov:Entity`. Every source span is a `prov:Entity`. The connection between them — and between derived claims and their predecessors — is `prov:wasDerivedFrom`.

```
?claim a prov:Entity ;
       a tbf:Claim ;
       schema:text "..." ;
       tbf:status "verified" ;
       tbf:confidence 0.92 ;
       tbf:hasSourceSpan ?span ;
       prov:wasDerivedFrom ?span .

?span a prov:Entity ;
      a tbf:SourceSpan ;
      tbf:fromDoc ?doc ;
      tbf:locatorText "..." .
```

For derived claims (claims with a `derived_from` field), an additional `prov:wasDerivedFrom` edge connects the new claim to each predecessor claim. Ingest, validation, and release runs are `prov:Activity` records and connect to the entities they touch via `prov:used` and `prov:generated`.

## SHACL shapes

Two shapes ship in `assets/shapes.ttl` and are copied into `graph/shapes.ttl` at workspace init.

### `tbf:ClaimShape`

Targets every `tbf:Claim`. Constraints:

- `schema:text` — exactly one, datatype `xsd:string`.
- `tbf:status` — exactly one, value from `{proposed, verified, disputed, superseded}`.
- `tbf:confidence` — exactly one, datatype `xsd:decimal`, in [0, 1].
- `tbf:hasSourceSpan` — at least one.
- An `sh:sparql` constraint additionally requires that every `verified` claim have at least one `prov:wasDerivedFrom` edge. Verified claims with no provenance are non-conforming.

### `tbf:ChapterSectionShape`

Targets every `tbf:ChapterSection`. An `sh:sparql` constraint requires that every `tbf:cites` edge from a chapter section point at a claim whose `tbf:status` is `verified`. Sections that cite proposed, disputed, or superseded claims are non-conforming.

## SPARQL competency queries

Five queries ship in `assets/queries/`. Each answers one operational question.

### `unsupported_claims.rq`

Finds verified claims with no `prov:wasDerivedFrom` edge. Should return zero rows after a clean projection. Non-zero rows indicate either a projection bug or a claim whose source spans failed to materialize as RDF.

### `contradiction_scan.rq`

Finds pairs of claims connected by an explicit `tbf:conflictsWith` edge. The query returns both directions of every conflict. Used by the release gate to block chapters that cite either side of a live contradiction.

### `stale_after_source_refresh.rq`

Finds verified claims whose `last_verified_at` is older than the most recent `dcterms:modified` of any source they cite. Stale claims need re-verification.

### `orphan_wiki_pages.rq`

Finds `tbf:WikiPage` resources not referenced by any claim's source span and not cited by any chapter section. Orphans are candidates for deletion or absorption into another page.

### `chapter_evidence_coverage.rq`

For each chapter, returns the count of verified claims it cites. Compared against `tbf:minimumVerifiedClaims` from the chapter contract during the release gate.

## Release-gate semantics

A chapter passes the release gate iff all four conditions hold:

1. SHACL conforms — `shacl_report.conforms == true` for the latest validation run.
2. `unsupported_claims` returns 0 rows.
3. `contradiction_scan` returns 0 rows for any chapter under release. Conflicts elsewhere in the graph do not block this chapter; conflicts on this chapter's claims do.
4. Each chapter contract under release has `count(verified citations) ≥ tbf:minimumVerifiedClaims`.

Failure produces a remediation queue at `graph/reports/release-gate-<run>.md` listing every failing condition with concrete focus nodes and queries to re-run. The gate never auto-fixes; it diagnoses.

## Reading SHACL violation reports

The textual report at `graph/reports/shacl-latest.txt` lists each violation as a block with three load-bearing fields:

- **Focus node** — the RDF node being validated. Usually a claim IRI like `<.../graphs/claims/clm-2026-000017>`.
- **Result path** — the property at fault. `tbf:confidence`, `tbf:hasSourceSpan`, etc.
- **Result message** — the human-readable explanation. "Confidence 1.2 not in [0,1]" or "Verified claim missing prov:wasDerivedFrom".

Iterate the report top to bottom. Each violation is independent; fixing one does not invalidate the others. Re-run `validate_shacl.py` after a batch of fixes; do not trust the prior report once the ledger has changed.

## Fix-don't-suppress

When a validation fails, repair the data. Do not weaken the shape. The SHACL shapes encode the project's epistemic discipline; loosening them to make a draft pass corrupts the gate's meaning. If a shape really is wrong (the requirement was over-specified, the schema needs evolution), update the shape in `assets/shapes.ttl`, regenerate `graph/shapes.ttl` from the asset, and document the change in `wiki/log.md`.
