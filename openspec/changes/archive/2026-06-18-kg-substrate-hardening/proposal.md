# Change: kg-substrate-hardening

**Sprint:** S8 of the v0.5 KG-for-prose mission
**Branch:** `plan/kg-prose-roadmap` (roadmap); execution branch `feat/kg-substrate-hardening`
**Capability:** `homoiconic-kg` (extend)
**Roadmap:** `docs/specs/2026-06-17-kg-prose-enhancement-roadmap-design.md`
**Depends on:** the landed `homoiconic-kg` capability, and a stable rule surface from S3–S7 (so the fixtures are worth freezing). Measured by S0 (`kg-prose-eval`).

## Why

The brief's substrate verdict is plain: keep Cozo, do **not** migrate, and spend the budget on seam-hardening plus a reference evaluator. Cozo matches the workload — embedded, Datalog, in-engine graph algorithms, time-travel, a Python seam — and nothing on offer beats it on that axis. But its release cadence is slow (latest verified `v0.7.6`, 2023-12-11), so migration risk is real enough to mitigate. The mitigation is not a rewrite; it is a conformance harness that makes a future switch cheap to *contemplate* without paying for it now.

The seam already exists: the `Backend` protocol, `StubBackend`, and the golden compile fixtures (REQ-KG-002, REQ-KG-002b, REQ-KG-007, REQ-KG-008). What is missing is the part that proves the seam is more than a shape — dual-run result-set equality between Cozo and a working reference backend, canonical ordering pinned so that comparison is deterministic, and an explicit, documented list of the conditions under which a swap is reconsidered. This change adds those three pieces and nothing else. It hardens REQ-KG-002/002b/007/008 without breaking them: the production store stays a single Cozo store behind one seam; the reference backend is authoring-time only.

## What

1. A conformance harness behind `cozo_store`: frozen EDN query fixtures, dual-run result-set equality between Cozo and a small reference backend, and canonical-ordering checks.
2. A small reference backend (DataScript-class, or a pure-Python EDN Datalog evaluator) for a **declared** rule subset — authoring-time / test only, never the production store, so REQ-KG-002 stays invariant.
3. A documented, explicit switch-trigger list: Python/platform support breaks; an unpatchable correctness or security issue; the reference backend reproduces the rule surface acceptably; or the embedded / Python-primary / offline constraints are relaxed.

DataScript is cited as the EDN/Datalog reference (in-memory, authoring-time only); Asami is the maintenance-warning north star, not a production store.

## Scope

- This change ships the conformance harness, the reference backend for a declared rule subset, canonical-ordering pinning, and the switch-trigger doc.
- It does **not** ship an actual production migration; the production store stays Cozo (REQ-KG-002 invariant).
- It does **not** cover all queries at once — a declared subset first, widened in later passes.
- The DataScript-vs-pure-Python-evaluator decision is Open Question 3 in the roadmap; this proposal cross-references it and leaves the choice to design time.

## Requirements

See `specs/homoiconic-kg/spec.md` (EARS). Summary:

| REQ id | Pattern | One-line |
|---|---|---|
| REQ-KG-041 | Ubiquitous | A conformance harness runs frozen EDN query fixtures behind the `cozo_store` seam |
| REQ-KG-042 | Event-driven | When a fixture runs against Cozo and the reference backend, their outputs are result-set-equal under canonical ordering |
| REQ-KG-043 | Ubiquitous | A reference backend evaluates a declared rule subset and is authoring-time only, never the production store |
| REQ-KG-044 | Ubiquitous | Query result sets are canonically ordered so dual-run comparison is deterministic |
| REQ-KG-045 | Ubiquitous | A documented switch-trigger list states the explicit conditions under which a backend swap is reconsidered |
| REQ-KG-046 | Unwanted | If the reference backend and Cozo diverge on a fixture, the harness fails loudly and names the fixture and the diverging rows |

## Out of scope

- An actual production migration (this is swap *optionality*, not a swap).
- Covering all queries at once — the harness starts on a declared rule subset.
- The reference-backend implementation choice (DataScript vs pure-Python evaluator), Open Question 3 in the roadmap.
- Learned or richer-semantics evaluation (the S9 stub).
