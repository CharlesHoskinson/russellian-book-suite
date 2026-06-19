# Change: kg-belief-erosion-completion

**Sprint:** S5 of the v0.5 KG-for-prose mission
**Branch:** `plan/kg-prose-roadmap` (roadmap); execution branch `feat/kg-belief-erosion-completion`
**Capability:** `homoiconic-kg` (extend)
**Roadmap:** `docs/specs/2026-06-17-kg-prose-enhancement-roadmap-design.md`
**Depends on:** S3 (`argumentation` — grounded argument-acceptance labels) and S4 (`homoiconic-kg` — normalized contradictions). Measured by S0 (`kg-prose-eval`).

## Why

`propagate_belief.py` already runs a full deterministic Bayesian erosion pass — evidence-combine, counter-claim damping, derivation attenuation, convergence, and snapshots. The brief's gap analysis (#4) over-estimated this move as a mid-tranche build; it is in fact ~95% done. What is missing is the *materialization*: the erosion pass writes its result back to the ledger only as posterior records. There is no materialized effective-confidence relation the writer can read, no reason a posterior dropped, and no provenance for the drop.

The brief's move #4 adds an auditable signal on top of the existing engine: a materialized `effective-confidence` relation, a `support-erosion-reason` drawn from minimal justification sets, bounded why-provenance computed on demand for load-bearing claims only, and a source-freshness decay so a stale high-trust source is discounted by age. This is a *completion* sprint, not a rewrite — `propagate_belief.py` stays the engine; S5 builds the materialization and provenance around it.

It deliberately avoids a full probabilistic logic engine (MLN/PSL/ProbLog) per the brief: a bounded, deterministic, provenance-aware signal is the better fit for the byte-deterministic offline build. Why-provenance for recursive Datalog can be intractable, so it is throttled — computed only for load-bearing claims the writer/checker flags, with a bounded witness cardinality.

## What

1. Materialize `effective-confidence` as a Cozo relation derived from `p-prior`, `p-posterior`, `supports`, `derived-from`, `conflicts-with`, `source.trust-score`, and source freshness — the engine's result made queryable rather than only appended to the ledger.
2. Emit `support-erosion-reason` from minimal justification sets: which counter-claims or parent-weakening derivations caused a claim's effective-confidence to drop.
3. Bounded why-provenance **on demand**, only for load-bearing claims flagged by the writer/checker — a throttle, because why-provenance for recursive Datalog can be intractable. Return minimal-cardinality witness sets, cached in the ledger.
4. Source-freshness decay: a time-dependent discount so a stale high-trust source is discounted by age, feeding the effective-confidence derivation.

The work lives in `book-knowledge` (ledger ownership) and reuses `skills/book-knowledge/scripts/propagate_belief.py` unchanged as the erosion engine; S5 reads its posterior output and adds the materialized relation, reasons, provenance, and freshness layer around it.

## Scope

- This change ships the `effective-confidence` Cozo relation, the `support-erosion-reason` emitter, on-demand bounded why-provenance for load-bearing claims, and the source-freshness decay — all reusing the existing `propagate_belief` engine with no rewrite.
- The erosion mathematics (evidence-combine, counter-claim damping, derivation attenuation, convergence, snapshots) is unchanged; S5 consumes it, it does not reimplement it.

## Requirements

See `specs/homoiconic-kg/spec.md` (EARS). Summary:

| REQ id | Pattern | One-line |
|---|---|---|
| REQ-KG-028 | Ubiquitous | The system materializes `effective-confidence` as a Cozo relation derived from p-prior/p-posterior/supports/derived-from/conflicts-with/source-trust/freshness |
| REQ-KG-029 | Event-driven | When propagation runs, each claim's effective-confidence carries a `support-erosion-reason` from a minimal justification set |
| REQ-KG-030 | Event-driven | When a refreshed source now conflicts, the affected claim's effective-confidence drops and its reason names the refreshed source + trusted conflict |
| REQ-KG-031 | Optional | Where a load-bearing claim is flagged for explanation, the system computes bounded why-provenance and not for every claim |
| REQ-KG-032 | Ubiquitous | Source trust carries a freshness decay so a stale high-trust source is discounted by age |
| REQ-KG-033 | Ubiquitous | Effective-confidence is deterministic over a snapshot (golden-able) and reuses the `propagate_belief` engine without rewriting it |
| REQ-KG-034 | Unwanted | If a load-bearing claim's why-provenance exceeds the bounded cardinality, the system returns the bounded witness set marked truncated |

## Out of scope

- A full probabilistic logic engine (MLN/PSL/ProbLog). Explicitly avoided per the brief: bounded + deterministic + provenance-aware beats a probabilistic engine for the byte-deterministic offline build.
- The neurosym-forge `tier5-confidence-propagation` track. That propagates confidence through *verifier verdicts* (defects); S5 propagates belief through the *claim ledger*. The shared "confidence"/"provenance" vocabulary is cross-referenced here to prevent concept drift: S5's why-provenance is over *claim derivations*, not over induced BookLogic rules.
- Recomputing the erosion mathematics inside `propagate_belief.py` (evidence-combine, damping, attenuation, convergence, snapshots) — reused as-is.
