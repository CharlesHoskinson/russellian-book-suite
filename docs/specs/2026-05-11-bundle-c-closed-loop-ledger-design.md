# Bundle C — Closed-Loop Ledger and Abductive QA

Design doc. 2026-05-11. Target: russellian-book-suite v5.x.

## Problem

The claim ledger is write-only. Sources are ingested, claims are extracted, SHACL validates the projected graph, and downstream skills read claims as ground truth. Nothing writes back. A claim that book-qa later discovers is unsupported stays `verified` in the ledger forever; the next chapter draft happily re-cites it. The contract-acceptance tests are threshold linters, not logical assertions over the graph, so a chapter that omits a load-bearing topic can pass coverage and still be wrong.

Bundle C closes three loops:
1. Each load-bearing claim is forced to carry its abductive rivals into the chapter contract, so prose either addresses them or fails coverage.
2. Claim confidence propagates through the PROV-O graph instead of being a static field set at extraction time.
3. book-qa findings write back to the ledger state machine, so the next build excludes refuted claims by default.

## Scope

In:
- `book-knowledge`: counter-claim generator, Bayesian posterior over PROV-O, defeasible SPARQL coverage rules, new ledger state `refuted`.
- `book-qa`: writeback adapter from defect tickets to ledger state transitions.
- `book-compose`: contract loader reads counter-claims as must-address entries; ledger slice excludes `refuted` and `disputed` by default with explicit pin opt-in.

Out:
- ASPIC+ argument graph (Bundle A).
- RST discourse-tree parser (Bundle B).
- Autoformalization to FOL with SMT checking (Bundle B).
- Any change to `russellian-style` linters, persona personas, or render pipeline.

## Architecture

```
                            ┌──────────────────────────────┐
sources ───► ingest ───►    │ claim-ledger.jsonl           │
                            │   status: proposed|verified| │
contract ──► counter-       │           disputed|superseded│
            abduction ────► │           refuted (new)      │
                            │   p_posterior: float (new)   │
                            │   counter_claim_ids: [...]   │
                            └──────────────────────────────┘
                                       │
            ┌──────────────────────────┼──────────────────────────┐
            │                          │                          │
            ▼                          ▼                          ▼
   propagate_belief.py        run_competency_queries     book-compose loads
   (PROV-O Bayes pass)        (SPARQL with severity      contract + counter-
                              and exception metadata)    claims as
                                                         must-address
            │                          │                          │
            ▼                          ▼                          ▼
   p_posterior updated         coverage report             chapter draft
   on every claim              (pass / soft-fail /         (every counter-
                               hard-fail)                  claim addressed
                                                          or chapter blocked)
                                                                   │
                                                                   ▼
                                                          book-qa runs
                                                                   │
                                                                   ▼
                                                          writeback_adapter.py
                                                                   │
                                                                   ▼
                                                          ledger transitions:
                                                          C-XXXX verified → disputed
                                                          C-YYYY disputed → refuted
                                                          (new event in
                                                          claims/events.jsonl)
```

Data flow remains acyclic per build, but the ledger now mutates between builds. `claims/events.jsonl` is the append-only audit log of every state transition with provenance (which defect ticket or which propagation pass caused it).

## Components

### 1. Abductive counter-claim generator

New script: `book-knowledge/scripts/generate_counter_claims.py`.

Input:
- `claims/ledger.jsonl` filtered to claims tagged `load_bearing: true` (a new optional field on claims; defaults `false`).
- Chapter contract YAML for the chapter the claim is bound to.

Process (per load-bearing claim):
1. LLM prompt: "Given claim C, generate the 2–3 strongest rival hypotheses that, if true, would falsify or weaken C. Each rival must be a single declarative sentence and must cite at least one disagreement vector (mechanism, measurement, scope, time period, or population)."
2. Emit each rival as a counter-claim record in `claims/counter-claims.jsonl` with fields `id`, `target_claim_id`, `text`, `disagreement_vector`, `status: open|addressed|dismissed`, `provenance` (model + prompt hash).
3. Update the target claim's `counter_claim_ids` field with the new IDs.
4. Counter-claims are *never* projected into the main RDF graph as PROV-O assertions. They live in a parallel namespace `cc:` so the main graph stays a positive-claim graph.

Counter-claim status transitions are driven by the chapter contract. A counter-claim becomes `addressed` via a two-stage check run by book-compose after the draft is written: (a) fast path — exact-string match on the counter-claim's canonical form if it is a verbatim quote; (b) default path — a deterministic LLM verifier that answers "does this chapter explicitly acknowledge and engage with the following rival hypothesis: <text>?" with a single yes/no plus the supporting paragraph span. The verifier output is cached under `claims/address-checks/<chapter>-<cc_id>.json` keyed on chapter content hash plus counter-claim text, so re-runs are free. A counter-claim becomes `dismissed` only on explicit operator action recorded in `claims/events.jsonl`.

### 2. Bayesian belief propagation

New script: `book-knowledge/scripts/propagate_belief.py`.

Process:
1. Read `graph/dataset.trig`.
2. Build a directed graph of `prov:wasDerivedFrom` and `prov:wasInformedBy` edges, plus `cc:rebuts` edges from counter-claims.
3. Each claim node carries a prior `p_prior`. The prior is set at extraction and is *reset on every state transition* via `apply_writeback.py`: 0.7 for `verified`, 0.5 for `proposed`, 0.2 for `disputed`, 0.05 for `refuted`, 0.5 for `superseded`. Reset means: any time a claim's status changes, the next propagation pass starts from this state-determined prior, not from the previous posterior.
4. One pass of loopy belief propagation:
   - Corroboration: if claim C is derived from two independent sources S1 and S2, posterior is `1 - (1 - p(C|S1)) * (1 - p(C|S2))`.
   - Rebuttal: each `addressed` counter-claim reduces target by a configurable factor (default 0.85). Each `open` counter-claim reduces by a smaller factor (default 0.95) — open rivals weigh less because the chapter hasn't acknowledged them.
   - Source trust: each source carries `trust: float` in its manifest; trust multiplies into the derivation product. Default `1.0`.
5. Convergence: fixed-point iteration capped at 20 passes, convergence epsilon 1e-4.
6. Value clamping: every posterior is clamped to `[0.05, 0.95]` before being written, so a claim never reaches 0 or 1 (preserves the ability to update under new evidence).
7. Write `p_posterior` back to each claim record (in-place update of `ledger.jsonl`; full prior copy preserved in `claims/snapshots/<utc-iso>.jsonl`).
8. Emit `graph/reports/belief-propagation-<run>.md` listing the top-20 largest absolute deltas plus a histogram of posterior values.

This is *not* a probabilistic logic engine. It is a deliberately simple closed-form pass: each claim is a node, each derivation is an independent evidence channel, and counter-claims are damping factors. Anything more sophisticated belongs to Bundle A.

### 3. Defeasible coverage queries

Modify `book-knowledge/scripts/run_competency_queries.py`.

Current behaviour: runs every `.sparql` query in `assets/queries/` and emits pass / fail per query against threshold linters in chapter contracts.

New behaviour:
- Three query classes, signalled by directory: `assets/queries/{coverage,consistency,defeasible}/`.
- `coverage/` queries are strict SPARQL ASK / SELECT. Failure = hard-gate.
- `consistency/` queries find contradictions among `verified` claims. Failure = hard-gate.
- `defeasible/` queries express soft constraints with explicit fallbacks: each query carries front-matter declaring `severity`, `default_satisfied`, and `exceptions: [<query_id>]`. A defeasible rule fails the build only if it fires *and* no exception query also fires.
- Replace existing chapter-contract `acceptance_tests: thresholds: ...` with `acceptance_tests: sparql: [coverage/topic-NN.sparql, defeasible/rebuttal-presence.sparql]`. Old threshold form stays supported for one release for backward compatibility.

Concretely, the three shipping defeasible rules (`book-knowledge/assets/queries/defeasible/`):

1. `rebuttal-presence.sparql` — every `load_bearing: true` claim cited in chapter N has at least one `cc:` counter-claim whose status is `addressed` in the same chapter. Exception: claims tagged `axiom: true`.
2. `contested-rebuttal-window.sparql` — every `status: disputed` claim cited in chapter N has a rebuttal-or-acknowledgement within 300 words of its citation in the rendered chapter. Exception: chapter front-matter declares `accepts_unrebutted: true`.
3. `posterior-floor.sparql` — every cited claim has `p_posterior >= 0.4`. Exception: contract pins claim with `pin_low_confidence: true`.

### 4. Closed-loop writeback adapter

Two scripts, one per skill:

- `book-qa/scripts/propose_writeback.py` — reads QA tickets, emits proposed transitions. Lives in book-qa because it consumes QA outputs.
- `book-knowledge/scripts/apply_writeback.py` — reads proposed transitions and mutates the ledger. Lives in book-knowledge because that skill is the canonical owner of `claims/`. This preserves the rule that only book-knowledge writes to `claims/`.

Input to `propose_writeback.py`: `qa/swarm-findings.json` from the C1–C15 swarm and `qa/lint-findings.json` from D1–D8 (D11 entailment failures in particular).

Process:
- For each ticket of class `unsupported_claim` (D11 failed-entailment and the corresponding swarm verdict from book-thesis): look up the cited claim ID. If the source span no longer supports the claim text, propose transition `verified → disputed`.
- For each ticket of class `refuted_by_new_source` (new ticket class to surface this): propose transition `disputed → refuted`.
- For each ticket of class `addressed_rival`: mark the matching counter-claim `open → addressed`.
- Write proposed transitions to `claims/proposed-transitions.jsonl` and a human-readable summary `qa/ledger-writeback-<version>.md`.

`apply_writeback.py` commits proposed transitions. Default mode is propose-only; `--auto-apply` applies transitions whose ticket severity is `critical` and whose source-span re-check is deterministic (D11). Editorial-only tickets always require operator review.

Every applied transition appends to `claims/events.jsonl` with `{timestamp, claim_id, from, to, cause_ticket_id, cause_class, operator}`.

A claim in state `refuted` is excluded from `book-compose`'s default ledger slice. To force inclusion, the chapter contract sets `force_include_refuted: [<claim_id>, ...]` — useful when a chapter argues *against* the refuted claim.

## Data model changes

### `claims/ledger.jsonl`

Existing fields are preserved. New fields:
- `load_bearing: bool` — default `false`. Set by contract author or by an LLM tagging pass.
- `p_prior: float` — default depends on status as above.
- `p_posterior: float` — written by `propagate_belief.py`.
- `counter_claim_ids: [string]` — IDs of records in `counter-claims.jsonl`.
- Status enum gains `refuted`. The full state machine becomes:

  ```
  proposed → verified → disputed → ┬── refuted    (terminal)
                                   └── superseded (terminal)
  ```

  `disputed` is the only state from which `refuted` is reachable. `verified → superseded` remains supported (a claim replaced by a better-cited equivalent). A claim cannot transition from `refuted` back to `verified`; if a refuted claim turns out to be true after all, the operator creates a new claim and links it via `prov:supersedes` to the refuted one.

### `claims/counter-claims.jsonl` (new file)

One record per counter-claim:
```json
{
  "id": "cc-0001-abcdef",
  "target_claim_id": "clm-0142-7e21a3",
  "text": "Bermuda's ferry network has consolidated rather than expanded since 2020.",
  "disagreement_vector": "scope",
  "status": "open",
  "provenance": { "generator": "abduction-v1", "prompt_sha256": "..." },
  "created_at": "2026-05-11T19:00:00Z",
  "addressed_in_chapter": null
}
```

### `claims/events.jsonl` (new file)

Append-only state-transition log:
```json
{
  "timestamp": "2026-05-11T19:30:00Z",
  "claim_id": "clm-0142-7e21a3",
  "from": "verified",
  "to": "disputed",
  "cause_ticket_id": "ch07-D11-04",
  "cause_class": "unsupported_claim",
  "operator": "charles@host"
}
```

### `claims/snapshots/<utc-iso>.jsonl` (new directory)

Full ledger snapshot written before each `propagate_belief.py` run, so posteriors can be diffed and rolled back.

## Integration points

| Skill | Owns | Reads | Writes |
|---|---|---|---|
| book-knowledge | `claims/`, `graph/`, `wiki/` | `raw/`, contract YAML | counter-claims, posteriors, snapshots, events |
| book-qa | defect tickets, `propose_writeback.py` | ledger (read-only at QA time) | `qa/ledger-writeback-*.md`, `claims/proposed-transitions.jsonl` |
| book-compose | `chapters/` | ledger slice (excludes `refuted`), counter-claims as contract input | unchanged |
| russellian-style | — | unchanged | unchanged |
| book-review | — | unchanged | unchanged |
| book-thesis | thesis graph | claim ledger | unchanged (already writes D9–D12 defects) |

`apply_writeback.py` is the only operation that mutates `ledger.jsonl` outside of book-knowledge's own ingest path; it lives inside book-knowledge so the ownership invariant holds. It consumes `claims/proposed-transitions.jsonl`, which book-qa writes — proposing is not the same as mutating.

## Acceptance criteria

Evaluated after Phase 4 ships. Items 1–5 must hold from Phase 3 onward; items 6–8 are evaluated only after Phase 4 promotes defeasible queries to hard-gate.

A bermuda-manual re-build with Bundle C enabled must:

1. Produce `claims/counter-claims.jsonl` with at least one record per claim tagged `load_bearing` in any contract.
2. Produce `claims/snapshots/<utc-iso>.jsonl` and `graph/reports/belief-propagation-<run>.md` on every `propagate_belief` invocation.
3. Fail the build if any chapter cites a claim with `p_posterior < 0.4` and the contract has not pinned it.
4. Re-running book-qa on a known-bad chapter (one with a fabricated citation) must produce a proposed transition `verified → disputed` for the affected claim and a `qa/ledger-writeback-*.md` listing it.
5. Applying the writeback and re-building must exclude the disputed claim from the next chapter draft, observable in the chapter contract's "claims slice" log.
6. The defeasible coverage check `rebuttal-presence.sparql` must fire and block release when a load-bearing claim has open counter-claims unaddressed.
7. Existing threshold-form chapter contracts continue to work without modification (backward compatibility).
8. Test suite: ≥40 new pytest tests across book-knowledge (counter-claim generator, propagate, defeasible queries) and book-qa (writeback adapter). Total ledger-related tests stay above current count.

## Non-goals

- Replacing the antonym-pair `detect_conflicts.py`. Bundle C runs alongside it; abductive counter-claims are a strictly broader detector.
- Defeasible logic semantics beyond the explicit-exception query form. No grounded/preferred semantics, no argument graphs, no semirings.
- LLM as a logic engine. The LLM only generates counter-claim text. All state transitions, propagation, and coverage checks are deterministic.
- UI for reviewing proposed transitions. CLI-only for v1; review is reading the markdown report.
- Confidence calibration. `p_prior` defaults are heuristic, not learned. Calibration belongs to a later bundle.

## Risks and open questions

1. **Counter-claim quality**. The whole bundle rests on the LLM generating *relevant* rivals, not strawmen. Mitigation: keep the prompt narrow ("strongest rival, single sentence, name a disagreement vector"); cache prompts in `provenance.prompt_sha256` so we can A/B prompt revisions. If quality is bad, the contract author edits the file by hand — counter-claims are not a black box.
2. **Belief propagation oversmooths**. With 20 iterations and corroboration multiplied per source, well-cited claims could approach 1.0 and undercited claims could approach 0.0, losing signal. Mitigation: cap posterior at `[0.05, 0.95]`; emit a histogram in the propagation report; tune the rebuttal damping factors after first full bermuda re-run.
3. **Writeback false positives**. An LLM swarm ticket that wrongly flags an unsupported claim could transition a true claim to `disputed`. Mitigation: `apply_writeback.py` requires deterministic re-check for `--auto-apply`; editorial tickets are always propose-only.
4. **`load_bearing` tagging burden**. Asking the operator to tag every load-bearing claim by hand is friction. Mitigation: ship a one-pass LLM tagger that proposes tags; operator confirms in a single review session per book.
5. **Counter-claim staleness**. A counter-claim generated against an early draft of a claim may not match the claim after it has been revised. Mitigation: each counter-claim's `target_claim_id` includes the claim version hash; a claim revision invalidates its counter-claims and triggers regeneration.
6. **Backward compat for old contracts**. Existing bermuda contracts use threshold acceptance tests. Bundle C must run them as today. Drop only after one major-version cycle.

## Implementation phases

Total engineering: ~2.5 weeks of focused work, sequential.

Phase 1 (~3 days): `propagate_belief.py` + snapshot + report + `p_posterior` field on ledger. No counter-claims yet, no writeback. Ships as a no-op on existing books because nothing yet reads `p_posterior`.

Phase 2 (~4 days): `generate_counter_claims.py` + `counter-claims.jsonl` + `load_bearing` field + two-stage `addressed` detection in book-compose + `claims/address-checks/` cache. Add `rebuttal-presence.sparql` and the other two defeasible queries as non-blocking warnings at first.

Phase 3 (~4 days): `propose_writeback.py` (book-qa) + `apply_writeback.py` (book-knowledge) + `events.jsonl` + `refuted` state + book-compose exclusion of refuted by default + `force_include_refuted` opt-in.

Phase 4 (~2 days): one full bermuda re-build with Bundle C enabled; tune damping factors using the propagation histogram; promote defeasible queries from warning to hard-gate; lock acceptance criteria.

## Test plan

- Unit: each new script has tests for its determinism (given the same input ledger and snapshot, output is bit-identical) and edge cases (empty counter-claims file, single-claim ledger, cyclic provenance graph rejection).
- Integration: synthetic 3-chapter tiny-example-book gets a closed-loop run — generate counters, draft, QA, writeback, rebuild — and asserts that a planted bad claim is `disputed` after one round and `refuted` after two.
- Regression: bermuda manuscript re-builds to byte-identical PDF when Bundle C is disabled (env flag `BUNDLE_C=0`). Re-builds with Bundle C produce a diffable change to the ledger and a non-empty `belief-propagation-*.md`.
- No new live-LLM tests in CI; counter-claim generator gets cassette-recorded fixtures.

## Out-of-scope but worth flagging

- Bundle B (RST discourse-tree D9-equivalent at paragraph grain) would complement this well — counter-claims need to be *addressed* in prose, and discourse-tree parsing is how we'd verify that automatically rather than by LLM check. Until Bundle B exists, address-detection is an LLM call in book-compose.
- Bundle A (ASPIC+ semantics) would replace `propagate_belief.py` with a real argumentation engine. Bundle C's posterior pass is the placeholder until that exists; the data model (counter-claims, events log) is forward-compatible.
