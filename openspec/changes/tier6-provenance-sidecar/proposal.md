# Change: tier6-provenance-sidecar

**Tier:** 6 of 7 (theory-induction tier)
**Branch:** `plan/tier6-theory-induction`
**Depends on:** Tier 1-5 landed; composes with Phase Q
(semantic retrieval), Phase V (induction grammar), Phase W
(candidate generation), Phase X (SMT numeric fitting)

## Why

An induced BookLogic constraint that nobody can audit is a
liability. After Phase W proposes and Phase X validates a
candidate, the framework knows exactly which atoms supported
the rule, which source documents those atoms came from, which
contradicting atoms it tolerated as advisory, which solver
runs validated it, and what the per-rule LLM cost was. Today
that knowledge dies in stdout. A future reviewer auditing
`rules/booklogic/induced-theory.edn` cannot answer "where did
this constraint come from?".

Both deep-research reports converged on the same answer:
PROV-O, the W3C provenance vocabulary. Every induced rule
carries a sidecar entry citing its evidence so paper
retractions, contradicting atoms, and entrenchment recomputes
all become mechanical operations on a typed object.

## What

- A new Python module `_provenance.py` exposing
  `ProvenanceSidecar` with `add_rule_provenance`, `lookup`,
  `iter_rules`, `remove_rule`, `save`, `load`.
- A canonical sidecar shape at
  `rules/booklogic/induced-theory.prov.edn` with PROV-O
  fields: `:prov/derived-from-atoms`, `:prov/source-documents`,
  `:prov/contradiction-atoms`, `:prov/proposed-by`,
  `:prov/validated-by`, `:prov/entrenchment`, `:prov/status`,
  `:prov/llm-repair-calls`, `:prov/cost-usd`.
- Optional `:prov/semantic-neighbours` and
  `:prov/induced-from-corpus` extensions.
- Byte-stable EDN round-trip discipline.
- Graceful-degrade error path on missing / malformed sidecar.

## Capabilities touched

- `provenance-sidecar` — ADD (new capability; companion
  artifact to `induced-theory.edn`)

## Implementation notes

See `docs/plans/2026-05-19-tier6-theory-induction.md`,
Phase Y.

## Acceptance

- 8 REQ-PROV IDs (040-047) ship in
  `specs/provenance-sidecar/spec.md`.
- A 10-rule sidecar round-trips byte-identical through
  `load(save(load(path)))`.
- A missing or malformed sidecar surfaces a structured error
  via `_cli_errors` and `forge theory` continues with empty
  provenance.
- `scaffold_project.py` vendors a starter sidecar into newly
  scaffolded projects.
