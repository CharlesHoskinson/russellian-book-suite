# Change: kg-proof-obligations

**Sprint:** S7 of the v0.5 KG-for-prose mission
**Branch:** `plan/kg-prose-roadmap` (roadmap); execution branch `feat/kg-proof-obligations`
**Capability:** `proof-obligations` (new)
**Roadmap:** `docs/specs/2026-06-17-kg-prose-enhancement-roadmap-design.md`
**Depends on:** S4 (`kg-contradiction-workbench`) for normalized claims and claim typing. Measured by S0 (`kg-prose-eval`).

## Why

`neurosym-forge`, `halmos`, and Z3 already exist in the suite, but they stand outside the ledger. A mathematically or scientifically delicate claim therefore rests on prose-level confidence, not on a discharged proof: the verifier may run, but its verdict is not an attributable, replayable graph entity, and nothing forces the writer to wait for it.

The brief's move #6 makes proof obligations first-class KG entities discharged by external verifiers, and gates the math/science writer passes on them: a claim is assertable-as-verified only once its obligation is discharged. This wires the existing standalone verifiers into the ledger and turns their runs into attributable, replayable evidence in the graph, rather than leaving them as side processes whose results never bind a sentence.

## What

1. A `proof-obligation` entity (`statement`, `linked-claim`, `checker-kind` ∈ {z3, cvc5, lean, units, stats-report}, `status`, `assumptions`, `artifact-path`, `countermodel-path`, `checked-at`, `normal-form`), plus a `verification-artifact` record and a `requires-proof` relation.
2. A checker-kind dispatch routing each obligation to z3 / cvc5 / lean / units / stats-report behind a seam — offline, replayable, with artifacts committed.
3. Gating: the halmos / math-science writer passes consume **only** claims whose obligations are discharged or explicitly waived.
4. A `scientific-claim-check` seam validating units, presence of uncertainty qualifiers, evidence type, and statistical-reporting norms, storing each guideline check as a machine-readable obligation.

The entities and relation live in `book-knowledge` (ledger ownership); dispatch invokes `neurosym-forge` + `halmos` + Z3 behind the seam. No sprint reaches the verifiers except through that seam.

## Scope

- This change ships the `proof-obligation` and `verification-artifact` entities, the `requires-proof` relation, the checker-kind dispatch, the writer gating, and the `scientific-claim-check` seam.
- It does **not** ship autoformalization (one-shot NL→formal) — that is S9.
- Deciding which claims auto-route to a checker versus which are manually flagged is a design-time call, not a deliverable of this change.
- The `neurosym-forge` induction track (`tierN-*` verifier/AGM/provenance work) is a separate subject; where a reader might conflate proof obligations over ledger claims with verifier verdicts over induced rules, the two are cross-referenced, not merged.

## Requirements

See `specs/proof-obligations/spec.md` (EARS). Summary:

| REQ id | Pattern | One-line |
|---|---|---|
| REQ-PROOF-001 | Ubiquitous | The schema declares `proof-obligation`, `verification-artifact`, and `requires-proof` |
| REQ-PROOF-002 | Event-driven | When a claim requires proof, an obligation is created with a checker-kind and status `pending` |
| REQ-PROOF-003 | Event-driven | When a checker discharges an obligation, a `verification-artifact` is recorded and status set `discharged` |
| REQ-PROOF-004 | Event-driven | When a checker refutes an obligation, the countermodel path is recorded and status set `refuted` |
| REQ-PROOF-005 | State-driven | While a claim's obligation is undischarged, the writer passes do not assert it as verified |
| REQ-PROOF-006 | Optional | Where an obligation is explicitly waived, the writer may state the claim as conjectural with the waiver noted |
| REQ-PROOF-007 | Event-driven | When a scientific claim lacks required units, uncertainty qualifiers, or statistical reporting, the seam flags it |
| REQ-PROOF-008 | Ubiquitous | Checker runs are offline and replayable, artifacts committed, verifiers invoked behind a seam |
| REQ-PROOF-009 | Unwanted | If an undischarged gated claim reaches final prose, the QA gate fails |

## Out of scope

- Autoformalization (one-shot NL→formal) and complex-math proof synthesis (S9 stub).
- Auto-route-versus-manual-flag routing policy (design-time decision).
- The `neurosym-forge` induction track (`tier5-confidence-propagation`, `tier6-agm-revision`, `tier6-provenance-sidecar`): those operate over induced rules and verifier defects, not over ledger claims.
