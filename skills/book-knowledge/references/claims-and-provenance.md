# Claims and provenance

Claims are the typed, verifiable units of knowledge in the workspace. Every fact the book asserts traces back, through one or more claim records, to source spans in raw documents.

## The four states

Every claim is in exactly one of four states:

- `proposed` — entered the ledger; not yet checked against sources.
- `verified` — locator text confirmed against the cited source.
- `disputed` — another verified claim explicitly contradicts it.
- `superseded` — a newer claim has replaced it.

## Allowed transitions

State transitions form a directed graph:

```
proposed   → verified | disputed | superseded
verified   → disputed | superseded
disputed   → verified | superseded
superseded → (terminal)
```

`scripts.claim_validator.assert_transition_allowed` enforces this. Any attempt to invent another transition (e.g., `verified → proposed`) raises `ClaimValidationError`. The state machine is intentionally narrow: you re-verify by superseding, not by demoting.

## Claim record schema

Validated against `assets/claim-record.schema.json`. Required fields:

- `claim_id` — pattern `clm-YYYY-NNNNNN`. Year is UTC; sequence is per-year and monotonic.
- `canonical_text` — the claim itself, ≥ 4 chars. Should read as a standalone declarative sentence.
- `status` — one of `proposed`, `verified`, `disputed`, `superseded`.
- `claim_type` — one of `fact`, `definition`, `design_decision`, `method`, `result`, `open_question`.
- `confidence` — float in [0, 1].
- `source_spans` — array, ≥ 1 entry. Each span has at minimum `doc_id` and `locator_text`.
- `created_at` — ISO 8601 UTC.

Optional fields:

- `semantic_class` — short tag for clustering (free-form, kept stable per project).
- `derived_from` — array of `claim_id`s this claim builds on.
- `supports_chapters` — array of chapter ids that cite this claim.
- `conflicts_with` — array of `claim_id`s explicitly contradicted.
- `supersedes` — single `claim_id` this record replaces.
- `last_verified_at` — ISO 8601 UTC.
- `generated_by_run` — caller-supplied run identifier.
- `review_notes` — short prose; populated by `transition_status`.

`additionalProperties: false` — unknown fields are rejected.

## Source span schema

Each entry in `source_spans` is a minimal pointer back into `raw/`:

- `doc_id` — required. Must match an ingested manifest.
- `locator_text` — required, ≥ 4 chars. A verbatim substring of the source content used for cross-checking.
- `node_id` — optional. Structural node identifier from the source manifest tree (chapter id, heading slug).
- `page_index` — optional, ≥ 1. PDF page number.

`locator_text` is the load-bearing field. It is what `verify_claim.py` searches for. Choose a unique enough substring that grep will not produce false positives; choose a short enough substring that minor whitespace differences do not break the match.

## Verification protocol

`scripts/verify_claim.py`:

1. Loads the claim record.
2. For each `source_span`, opens the cited `wiki/sources/<doc_id>.md`.
3. Searches for `locator_text` exactly (after whitespace normalization).
4. If every locator matches: calls `transition_status(claim_id, "verified", note="locator-text confirmed")`.
5. If any locator misses: claim stays `proposed`. The reason is recorded in a per-claim verification report under `claims/verification/<claim_id>.md` listing which spans failed.

Verification is purely textual. It does not interpret meaning. A locator that says "X causes Y" is verified if and only if those words appear in the source — regardless of whether the source actually argues that X causes Y. Semantic verification happens via human review and `detect_conflicts.py`.

## Supersession discipline

NEVER mutate an existing claim record in place. The ledger is append-only. To replace a claim:

1. Author the replacement as a NEW record.
2. Set `supersedes: <old_claim_id>` on the new record.
3. Append the new record via `append_claim`.
4. Call `transition_status(old_claim_id, "superseded", note="superseded by clm-YYYY-NNNNNN")`.

The two records both live in `claims/ledger.jsonl`. The history is preserved. Downstream tools (graph projection, competency queries, release gate) reason about "current" claims by collapsing supersession chains to their tip.

## Confidence calibration

Calibrate by source-strength heuristic, not by gut:

- **0.95 – 1.00** — direct quotation from an authoritative source. The locator text is a verbatim phrase from the source, and the source is primary (paper of record, official spec, definitive textbook).
- **0.85 – 0.94** — paraphrase of explicit source content. The source says it; you have rephrased it. No interpretation introduced.
- **0.70 – 0.84** — synthesis spanning multiple verified sources. Each source contributes a fragment; the claim is the conjunction.
- **Below 0.70** — keep the claim `proposed` until a stronger source is found. Do not promote weak claims into the verified set; they pollute downstream reasoning and pass through SHACL conformance checks unnoticed.

The release gate does not currently filter by confidence, but downstream curators do. A book that ships with a high proportion of verified-but-low-confidence claims is fragile against future source revisions.

## Anti-patterns

- **In-place edits to ledger.jsonl.** Always append. Editors that "tidy up" prior records destroy the audit trail.
- **Synthetic locator_text.** The locator must be a substring of the actual source. If you cannot find a real substring, the claim is not yet supportable; keep it `proposed` and find a better source.
- **Wide-net `conflicts_with`.** Use this field only for genuine logical contradictions, not for "these two claims sit in tension." Tension goes in the wiki; only contradictions go in the field.
