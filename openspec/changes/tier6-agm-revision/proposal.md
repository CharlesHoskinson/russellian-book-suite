# Change: tier6-agm-revision

**Tier:** 6 of 7 (theory-induction tier)
**Branch:** `plan/tier6-theory-induction`
**Depends on:** Tier 6 phase Y (provenance-sidecar) landed

## Why

Once an induced theory exists, new evidence will eventually
contradict it. A paper gets retracted; a re-ingest of the
corpus surfaces atoms that fail an existing rule; a sister
corpus is added with a different empirical regime. The
naive answer is "re-induce from scratch." That throws away
the audit trail and silently overwrites rules a human
reviewer already approved.

Both deep-research reports converged on the AGM postulates
(Alchourrón, Gärdenfors, Makinson) as the correct discipline:
a revision is a contraction followed by an expansion;
entrenchment ranks rules so the framework knows what to give
up first; quarantined rules persist with lower status rather
than being deleted. The Levi-revision via Harper-identity
pattern guides the mathematics.

## What

- A new Python module `_agm_revision.py` exposing
  `revise_theory(induced_path, prov_path, retracted_docs,
  contradicting_atoms) -> RevisionReport`.
- A deterministic entrenchment formula
  `(held-out-sat-rate × support-doc-count)` normalised to
  `[0.0, 1.0]`.
- Deterministic status thresholds: `>= 0.7` → `:active`;
  `[0.4, 0.7)` → `:tentative`; `< 0.4` → `:quarantined`.
- Quarantine-down only this tier; promote-up deferred to
  Tier 7.
- A structured warning when a single revision quarantines
  the entire theory.
- A `RevisionReport` dict surfaced through `forge revise`.

## Capabilities touched

- `theory-revision` — ADD (new capability; mutates the
  provenance sidecar from Phase Y in AGM-compliant steps)

## Implementation notes

See `docs/plans/2026-05-19-tier6-theory-induction.md`,
Phase Z.

## Acceptance

- 7 REQ-REVISE IDs (040-046) ship in
  `specs/theory-revision/spec.md`.
- A test harness exercises: retracted paper supports 1 rule
  (rule contracts), retracted paper supports 5 rules (5
  rules contract), contradicting atom downgrades a rule
  from `:active` to `:tentative`, full-quarantine warning
  fires when all rules cross the threshold.
- The revision never silently deletes a rule; quarantined
  rules persist in the sidecar with lower status.
- The `RevisionReport` shape is stable and consumable by
  Phase AA's `forge revise` subcommand.
