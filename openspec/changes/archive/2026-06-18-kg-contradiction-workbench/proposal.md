# Change: kg-contradiction-workbench

**Sprint:** S4 of the v0.5 KG-for-prose mission
**Branch:** `plan/kg-prose-roadmap` (roadmap); execution branch `feat/kg-contradiction-workbench`
**Capability:** `homoiconic-kg` (extend)
**Roadmap:** `docs/specs/2026-06-17-kg-prose-enhancement-roadmap-design.md`
**Depends on:** S2 (`kg-writer-assertion-contract`). Measured by S0 (`kg-prose-eval`).

## Why

Contradiction detection in the suite is lexical: `detect_conflicts.py` matches
antonym pairs, and the symbolic `consistency_cozo` D9–D11 rules catch orphans,
transitive contradictions, and invariant violations. Neither normalizes
quantities, units, or time intervals, so "30 km" versus "18 mi", "before 1920"
versus "after 1925", or "0.5" versus "50%" pass as non-conflicting. There is also
no seam for paraphrastic residue — two claims that contradict only after a
meaning-preserving rephrase escape every symbolic rule.

The brief's move #5 pushes the *exact* symbolic checks into EDN/Datalog —
quantity, unit, and interval normalization plus stale supersession detection —
and reserves NLI strictly for the residue that survives all symbolic checks. This
keeps determinism where it matters (symbolic checks are golden-able, result-set
equal) and isolates the non-deterministic model behind a stubbable, offline-
freezable seam.

## What

1. Normalized helper relations declared in `kg-schema.edn` and emitted by the
   projector: `claim-quantity`, `claim-unit`, `claim-time-interval`, and
   `claim-normal-form`.
2. Datalog rules over those relations for:
   - exact contradictions (same subject/predicate, incompatible objects),
   - time-interval inconsistencies (disjoint where overlap is required, or vice
     versa),
   - quantity clashes after unit conversion to a canonical unit,
   - stale or invalid supersession chains.
3. An external NLI residue seam: only candidate pairs that fail *every* symbolic
   check route to an NLI/domain verifier. The seam is stubbable and offline-
   freezable; the symbolic checks stay deterministic regardless of seam state.

The helper relations and rules live in `book-knowledge` (ledger ownership) and run
through `cozo_store` (REQ-KG-002/002b stays invariant). The pass composes with the
existing `consistency_cozo` D9–D11 pass rather than replacing it.

## Scope

- This change ships the four helper relations (added to `kg-schema.edn`), the
  symbolic contradiction rules, and the NLI residue seam.
- It does **not** choose the NLI model — that is an S2/S4 design-time decision
  (see the roadmap open questions); the seam ships stubbable and offline-freezable.
- It does **not** replace the existing lexical antonym detector
  (`detect_conflicts.py`) — that stays as a complementary pass.
- The symbolic checks compose with the existing `consistency_cozo` D9–D11 pass;
  they add normalized-quantity/interval/supersession defects alongside it, they do
  not subsume it.

## Requirements

See `specs/homoiconic-kg/spec.md` (EARS). These append to the existing
`homoiconic-kg` REQ-KG numbering (the landed change reached REQ-KG-011); this
change uses REQ-KG-021..027. Summary:

| REQ id | Pattern | One-line |
|---|---|---|
| REQ-KG-021 | Ubiquitous | The schema declares `claim-quantity`, `claim-unit`, `claim-time-interval`, `claim-normal-form` |
| REQ-KG-022 | Event-driven | When two in-scope claims assert incompatible quantities after unit normalization, the system marks a hard contradiction |
| REQ-KG-023 | Event-driven | When two claims' time intervals are inconsistent, the system flags an interval inconsistency |
| REQ-KG-024 | Event-driven | When a supersession chain is stale or invalid, the system flags it |
| REQ-KG-025 | Ubiquitous | The symbolic contradiction checks are deterministic (result-set-equal, golden-able) |
| REQ-KG-026 | Optional | Where a candidate pair fails all symbolic checks but stays a candidate, it routes to the NLI seam as paraphrastic residue |
| REQ-KG-027 | Unwanted | If the NLI seam is unavailable, the symbolic checks still run and the residue is marked unresolved, not dropped |

## Out of scope

- The NLI/domain verifier model choice (design-time).
- Replacing the lexical antonym detector (`detect_conflicts.py`) — it stays.
- Belief erosion over the new contradiction defects (S5 consumes them).
- Replacing the `consistency_cozo` D9–D11 pass — this change composes with it.
