# Chapter Contract Specification

A chapter contract is a YAML file under `chapters/contracts/<chapter_id>.yaml`. It binds a chapter to a thesis, an audience, an evidence floor, and a battery of acceptance tests. The contract precedes drafting. Every drafted artifact is judged against it.

## Schema

The canonical schema lives at `assets/chapter-contract.schema.json` and is enforced by `scripts/chapter_contract.py:validate_contract`. Required fields: `chapter_id`, `title`, `purpose`, `audience`, `chapter_type`, `evidence_requirements`, `acceptance_tests`, `output_formats`. Optional fields: `must_include`, `must_not_do`, `style`. Unknown fields are rejected (`additionalProperties: false`).

### Field reference

- `chapter_id` (string, required, pattern `^ch-[0-9]{2,3}$`). Stable identifier. Used to address drafts (`chapters/drafts/<chapter_id>/`), releases (`chapters/releases/<chapter_id>-<version>/`), and SPARQL queries against the workspace graph.
- `title` (string, required, min length 1). Reader-facing title.
- `purpose` (string, required, min length 10). One sentence. The axiomatic spine of the chapter; every section must derive from it.
- `audience` (enum, required). One of `senior-engineer`, `researcher`, `manager`, `developer`. Sets the prior-knowledge floor.
- `chapter_type` (enum, required). One of `tutorial`, `reference`, `synthesis`, `argument`. Governs section structure and citation density.
- `must_include` (array of strings, optional). Topics the chapter is required to cover. Each entry should map to one or more outline sections.
- `must_not_do` (array of strings, optional). Negative constraints. Common entries: `speculate beyond verified claims`, `cite a paper not in the workspace`, `use code without explaining why`.
- `evidence_requirements` (object, required). Fields:
  - `minimum_verified_claims` (int, required). Floor on cited verified claims.
  - `max_unresolved_conflicts` (int, required). Ceiling on contradictions touching cited claims.
  - `required_sources` (array of strings, optional). `doc_id` values that must appear in the cited slice.
  - `evidence_density_target` (number, optional). Verified claims per 1000 words. See rationale below.
- `acceptance_tests` (array of strings, required). Boolean expressions evaluated by `chapter_contract_check.py` and `preflight.py`. See test integration below.
- `style` (object, optional). Fields: `inherit` (string, e.g. `russellian-style`), `overrides` (object). The drafting playbook reads `inherit` to choose the style skill invoked per section.
- `output_formats` (array, required, min items 1). Subset of `markdown`, `pdf`, `epub`, `latex`. Drives `build_release_bundle.py`.

## Three example contracts

### Tutorial contract

```yaml
chapter_id: ch-04
title: Building a Verified Ledger Step Loop
purpose: Walk a senior engineer through implementing the verifier loop end to end.
audience: senior-engineer
chapter_type: tutorial
must_include:
  - prerequisites and dependency layout
  - the verifier inner-loop signature
  - failure-mode triage with worked traces
must_not_do:
  - introduce code without first stating the invariant it preserves
evidence_requirements:
  minimum_verified_claims: 12
  max_unresolved_conflicts: 0
  required_sources: [chapman-2024-ledger]
  evidence_density_target: 6
acceptance_tests:
  - shacl_conforms == true
  - unsupported_claim_count == 0
  - hedge_count == 0
  - passive_voice_ratio < 0.05
output_formats: [markdown, pdf]
```

### Reference contract

```yaml
chapter_id: ch-09
title: Effect Kinds and Their Witness Encoding
purpose: Catalogue every effect kind with its ABI, witness layout, and verification predicate.
audience: developer
chapter_type: reference
must_include:
  - one subsection per EffectKind variant
  - the WitLedgerEffect ABI table
must_not_do:
  - editorialise; the entries are pure reference
evidence_requirements:
  minimum_verified_claims: 25
  max_unresolved_conflicts: 0
  evidence_density_target: 9
acceptance_tests:
  - shacl_conforms == true
  - unsupported_claim_count == 0
  - hedge_count == 0
  - passive_voice_ratio < 0.05
output_formats: [markdown, pdf, latex]
```

### Synthesis contract

```yaml
chapter_id: ch-12
title: Why Coroutines Beat Continuations for User-Defined Tokens
purpose: Argue that coroutine-shaped state machines minimise circuit width for UDT workflows.
audience: researcher
chapter_type: synthesis
must_include:
  - the coroutine-vs-continuation comparison table
  - the circuit-width measurements from the bench corpus
must_not_do:
  - claim a result that is not in the verified-claims slice
evidence_requirements:
  minimum_verified_claims: 18
  max_unresolved_conflicts: 0
  evidence_density_target: 7
acceptance_tests:
  - shacl_conforms == true
  - unsupported_claim_count == 0
  - hedge_count == 0
  - passive_voice_ratio < 0.05
  - modifier_budget_violations == 0
output_formats: [markdown, pdf, epub]
```

## Rationale: `evidence_density_target`

The target is verified claims per 1000 words. Five is the floor for narrative chapters. Seven is healthy for synthesis. Nine is appropriate for reference catalogues. Below five, the prose is opinion. Above twelve, the prose is a bibliography. The drafting playbook surfaces the live density during Stage 4 and warns when a section drops below `0.7 * evidence_density_target`.

## Acceptance-test integration

`acceptance_tests` are simple infix expressions: `<metric> <op> <value>`. The check splits responsibility across two scripts.

`preflight.py` evaluates workspace-level metrics produced by book-knowledge: `shacl_conforms` (bool), `unsupported_claim_count` (int from the unsupported-claims competency query), and `contradiction_count` (int from the contradiction-scan query). Failure here blocks the pipeline before any drafting occurs.

`chapter_contract_check.py` evaluates style-level metrics produced by russellian-style's linters: `hedge_count`, `passive_voice_ratio`, `modifier_budget_violations`, `parallel_structure_violations`, `sentence_count`. The script imports each linter via `load_russellian_style_module` and runs them against the assembled `draft.md`. Tests not matching either set of metrics are silently skipped, so contracts may carry forward-looking expressions without breaking.

## Required-versus-optional behaviour

Missing required fields raise `ContractValidationError` from `validate_contract`. The drafting pipeline halts immediately. Missing optional fields default as follows: `must_include` and `must_not_do` default to empty lists, `style` defaults to `{}`, `evidence_density_target` defaults to unset (no warning emitted), and `required_sources` defaults to empty (no source check). The `must_include` list is consulted by the outline-discipline checker; the `must_not_do` list is rendered into the drafting prompt as negative constraints. Neither list is verified mechanically beyond what the russellian-style linters already enforce.
