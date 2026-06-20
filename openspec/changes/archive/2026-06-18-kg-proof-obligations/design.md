# Design: KG proof obligations

## Entity and lifecycle

`proof-obligation` is a book-knowledge-owned append-only record under
`claims/proof-obligations.jsonl`. The latest row per obligation id is projected
into the Cozo `proof-obligation` relation. The relation carries:

- `statement`
- `linked-claim`
- `checker-kind`
- `status`
- `assumptions`
- `artifact-path`
- `countermodel-path`
- `checked-at`
- `normal-form`
- `waiver-reason`

`verification-artifact` is stored under `claims/verification-artifacts.jsonl`
and projected into the graph. `requires-proof` is a derived relation: each
latest obligation produces one row linking the claim to the obligation. This
keeps the claim ledger byte-identical when obligations are created or checked.

The lifecycle is append-only:

- `pending -> discharged`
- `pending -> refuted`
- `pending -> waived`

`discharged` requires an `artifact-path` and `checked-at`. `refuted` requires a
`countermodel-path` and `checked-at`. `waived` requires a recorded waiver reason.
Validation is enforced by a JSON Schema plus a validator module, mirroring the
claim status discipline without changing the claim-record schema.

## Checker dispatch and replay

Checker execution routes through an injected dispatch map keyed by
`checker-kind` (`z3`, `cvc5`, `lean`, `units`, `stats-report`). Tests inject
stub checkers. Production callers can bind those names to the existing verifier
surfaces, but the proof-obligation module does not spawn a verifier directly.

A successful proof writes a committed JSON artifact under
`graph/proof-artifacts/` and appends both a `verification-artifact` record and a
new discharged obligation row. A refutation writes a committed countermodel
under `graph/countermodels/` and appends a refuted obligation row. Re-running a
discharged obligation replays from the artifact path in the latest row and does
not invoke the checker seam, so replay is offline and deterministic.

## Writer gating

The math/science writer consumes obligation status but does not write
book-knowledge records. A discharged claim may be asserted normally. A pending
or refuted obligation is omitted from verified prose or rendered in a
non-canonical form. A waived obligation may be stated as conjectural with the
waiver reason noted, and is never marked verified.

## QA hard gate

Book-qa reads `qa/gated-sentences.jsonl` as a release-gate input. A row asserting
`assertion-kind=verified` for an obligation whose status is neither `discharged`
nor `waived` becomes a critical `gated-sentence-escape` ticket. This class is a
hard failure in the sentinel aggregate, not an advisory warning.

## Scientific claim check

The scientific claim check is deterministic and rule-based. It flags numeric
scientific claims that lack a unit, an uncertainty qualifier, or statistical
reporting. The check emits machine-readable rows with checker kinds `units` or
`stats-report`, which callers may use to open obligations. It does not call an
LLM or external service.

## Ownership

Book-knowledge writes the obligation and artifact JSONL records plus graph
artifact files. Book-qa writes only QA outputs and reads the gated-sentence
input. Halmos/book-compose only consume obligation status and produce chapter
prose; they do not write `claims/`, `graph/`, or `qa/`.
