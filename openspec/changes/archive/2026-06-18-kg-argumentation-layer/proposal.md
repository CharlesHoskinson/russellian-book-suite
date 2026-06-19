# Change: kg-argumentation-layer

**Sprint:** S3 of the v0.5 KG-for-prose mission
**Branch:** `plan/kg-prose-roadmap` (roadmap); execution branch `feat/kg-argumentation-layer`
**Capability:** `argumentation` (new)
**Roadmap:** `docs/specs/2026-06-17-kg-prose-enhancement-roadmap-design.md`
**Depends on:** S2 (`attributed-generation`) — warnings attach to the writer-assertion surface — and the existing argument edges in the landed `homoiconic-kg` capability. Measured by S0 (`kg-prose-eval`).

## Why

The ledger already stores the argument edges (`supports`, `conflicts-with`, `counter-claim`, `sub-argument`, `load-bearing`) but never evaluates them for acceptability. A counter-claim can sit unanswered against a load-bearing claim and the writer is never told. The graph holds the structure of the dispute and draws no conclusion from it, so the writer is never warned that a load-bearing claim rests on a defeated argument.

The brief's move #3 adds a computable warning surface via Dung grounded acceptability: deterministic, explainable, and decidable in plain Datalog. Grounded semantics labels each claim accepted, rejected, or undecided from the attack relation alone, and a load-bearing claim that fails to be grounded-accepted is exactly the warning the writer needs. This is a pure EDN/Datalog rule layer over Cozo — no new store, only new derived relations over edges that already exist.

## What

1. EDN/Datalog rules deriving `attacked`, `defended`, `undefeated-attacker`, `grounded-accepted`, and `grounded-rejected` over the existing `supports` / `conflicts-with` / `counter-claim` / `sub-argument` / `load-bearing` edges.
2. Warnings derived from those labels: `contested-load-bearing-with-undefended-attack`, `unsupported-load-bearing`, and `axiom-only-support`.
3. Grounded semantics only at first (deterministic, explainable); the acceptance labels are materialized as a relation. Preferred and stable semantics are deferred to S9.
4. A minimal defeat justification: the defeater set (or the missing support) that explains why a claim is not grounded-accepted, bounded so the explanation stays tractable.

The rule layer lives in `book-knowledge` (ledger ownership) and compiles through the existing EDN→Cozo path; it reads the argument edges and writes only derived relations. The warnings attach to the S2 writer-assertion surface so they reach the writer at the sentence that asserts the contested claim.

## Scope

- This change ships the grounded-acceptability rules, the acceptance-label relation, the three warnings, and the minimal justifications.
- The acceptance labels are consumed downstream by S5 (`kg-belief-erosion-completion`), which reads grounded-acceptance as an input to effective-confidence; this change produces the labels, it does not propagate belief.
- Argument-edge construction is unchanged; S3 consumes the existing edges, it does not infer new ones.

## Requirements

See `specs/argumentation/spec.md` (EARS). Summary:

| REQ id | Pattern | One-line |
|---|---|---|
| REQ-ARG-001 | Ubiquitous | The rule layer derives attacked/defended/undefeated-attacker/grounded-accepted/grounded-rejected over the existing argument edges |
| REQ-ARG-002 | Event-driven | When the argumentation pass runs, each in-scope claim receives exactly one grounded-acceptance label |
| REQ-ARG-003 | Ubiquitous | The system computes grounded semantics only; preferred and stable are out of scope |
| REQ-ARG-004 | Event-driven | When a load-bearing claim has an undefeated attacker, the system emits a contested-load-bearing-with-undefended-attack warning |
| REQ-ARG-005 | Event-driven | When a load-bearing claim's only support is an axiom, the system emits an axiom-only-support warning |
| REQ-ARG-006 | Ubiquitous | Each warning carries a minimal justification (defeater set or missing support) |
| REQ-ARG-007 | Ubiquitous | The acceptance computation is deterministic over a ledger snapshot and compiles through the existing EDN→Cozo path |

## Out of scope

- Preferred, stable, and ASPIC+ richer semantics (S9, likely an ASP solver rather than plain Datalog).
- Numeric belief propagation over the acceptance labels (S5 consumes these labels).
- Construction or revision of the argument edges themselves.
