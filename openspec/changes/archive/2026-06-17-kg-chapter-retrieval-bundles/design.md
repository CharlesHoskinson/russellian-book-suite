# Design: kg-chapter-retrieval-bundles

## Goal

Materialize one deterministic chapter-retrieval bundle per chapter from the
existing EDN-front/Cozo-back graph, then hand that structured bundle to
book-compose as JSON/EDN plus a prompt scaffold. The change is a projector and
serializer only: it does not change the claim ledger, writer output contract, or
backend substrate.

## Relation Shape

`assets/kg-schema.edn` declares a new `:chapter-retrieval-bundle` relation:

- `:id` — deterministic bundle id, `bundle:<chapter-id>`.
- `:chapter-id` — caller-facing chapter id.
- `:chapter-uri` — the full chapter URI used by `claim-chapter`.
- `:payload-json` — canonical JSON payload, sorted keys.
- `:payload-edn` — EDN serialization of the same payload.
- `:prompt-scaffold` — deterministic writer prompt scaffold derived from the payload.

The payload structure is declared in
`assets/chapter-retrieval-bundle.schema.json`. The relation stores serialized
payloads so the graph has exactly one row per chapter while callers can validate
and address sections by key.

## Projector Algorithm

`scripts/project_chapter_bundle.py` owns projection. It creates an in-memory
`CozoStore` from `kg-schema.edn`, calls `project_ledger_cozo.project_ledger`, and
then reuses the same chapter URI and verified-claim selection semantics as
`book-compose/scripts/query_chapter_evidence.py`: `claim-chapter` joined to
`claim.status == "verified"`.

For the selected claim ids:

1. Load claim rows from the store and keep load-bearing claims first, then by
   descending confidence, then claim id.
2. Rank dominant communities from `code-claim-link` joined to `code-node` /
   `community`. Ranking is by number of selected claims represented, then
   community id.
3. Surface unresolved rebuttals from latest-per-id `counter-claim` rows whose
   `cc-status` is `open` and whose target is selected. Addressed and dismissed
   rows are excluded because the ledger projection already collapses the
   counter-claim log to latest-per-id.
4. Build the minimal span anchor set over selected load-bearing claims. Spans
   are considered in `(claim-id, span-id)` order and one span is selected for
   each still-uncovered claim. With current schema each `source-span` belongs to
   one claim, so this is both deterministic and minimal.
5. Include `code-links` only when at least one selected claim has a
   `code-claim-link` row.
6. Flag every selected load-bearing claim with no source span under
   `flags.unanchored-load-bearing`.

The projector loads the resulting row into the same store and returns the row as
a Python dict. It never opens the ledger for writing.

## Serializer and Prompt Scaffold

`book-compose/scripts/chapter_bundle.py` is the consumer-facing serializer. It
uses `sibling_skills.load_book_knowledge_module("project_chapter_bundle")` to
call the projector, validates the returned payload against book-knowledge's JSON
schema, and returns:

- `chapter_id`
- `json`
- `edn`
- `payload`
- `prompt_scaffold`

The prompt scaffold is deterministic and derived from the structured payload:
state the chapter thesis, present support claims in bundle order, anchor each
claim to the supplied spans, and caveat unresolved rebuttals.

## Determinism

All ordering is explicit. JSON serialization uses `indent=2`, `sort_keys=True`,
and a trailing newline. Tests compare the projector payload to a frozen golden
and run the projector twice on one snapshot to prove canonical equality.

## Boundaries

- No projector writes to `claims/`, `raw/`, or `wiki/`.
- No module imports `pycozo` outside `cozo_store`.
- No writer assertion, sentence citation checking, argument acceptability, or
  community recomputation is included in this sprint.
