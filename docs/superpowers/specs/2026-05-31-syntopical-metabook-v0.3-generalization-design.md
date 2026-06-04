# syntopical-metabook v0.3 — Generalization and capability unification

**Status:** Design draft, awaiting user review and a follow-up implementation plan.

## 1. Goal and scope

Turn `syntopical-metabook` into a **general-purpose, domain-agnostic** knowledge-curation skill whose advertised surface matches what it does. Today the skill ships a governance layer (v0.2) but its `description:` advertises four sub-workflows that are implemented, tested, and dormant — wired to no public API and no CLI. The trigger text and the body disagree, and the governance layer's docs, fixtures, and conformance test are bound to one consensus-cryptography paper.

v0.3 resolves both problems at once: wake the four sub-workflows as first-class capabilities, strip every specific-use reference, fix the two governance functional gaps that prevent it running on real data, and produce a standalone QA plan and utility/value plan.

**In scope.** Five unified capabilities (Acquire, Synthesize, Lens, Gap, Govern) exported from `skill_api.py` and reachable from the `forge` CLI; de-specialization of all docs, fixtures, and the conformance test; `defconstraint` support and a staleness guard in governance; a QA plan document; a utility/value plan document.

**Out of scope.** Multi-book aggregation across workspaces (deferred). New synthesis algorithms or new acquisition adapters. Changes to book-knowledge, book-thesis, or scrapling-fetch internals. Any change to the governance stance-derivation math beyond reading a second rule source.

**Non-goal.** The skill does not pick winners among schools of thought, does not rank knowledge by correctness, and does not author prose. It curates, attributes, projects, and reports; humans and downstream skills draw conclusions.

## 2. Current state (audited 2026-05-31)

- Governance v0.2 is merged (PR #117). `scripts/governance/` ships `build_positions`, `render_per_rule`, `render_consensus_map`, `render_adversarial`, `induction_gate`, plus `forge govern {build,report,map,review,quarantine}`. 86 tests pass, 3 skip.
- The four sub-workflows are fully implemented and **domain-neutral already** (no praos/algorand/τ/EpochPoET in their code, tests, or fixtures). They have an end-to-end pipeline test. `book-compose.read_lens()` already consumes the Lens output. They are exported nowhere and have no CLI.
- Consensus-crypto specifics are confined to: the governance `three-schools` fixture (praos/algorand slugs), `governance-playbook.md` (τ≤1 examples), the `/c/epochpoet`-bound conformance test (always skips — no curated schools there), and `SKILL.md`.
- `SKILL.md` declares `version: 0.1.0` while `skill_api.py` declares `API_VERSION = (0, 2)`; the public-surface section documents only two of the five exported governance functions.
- `build_positions` reads only `rules/booklogic/induced-theory.prov.edn`; it ignores `rules/constraints.edn` (code comment: "Phase 4 follow-up; optional"). A workspace with hand-written constraints and zero induced rules produces zero positions — the case the design was motivated by.
- Governance renderers have no staleness guard, though design v0.2 §6 requires one.

## 3. Target capability surface

Five first-class capabilities over any book/knowledge workspace. The orchestrator boundaries are unchanged: no direct network (only via `scrapling-fetch`), no mutation of the canonical workspace (only via `book-knowledge`), all writes confined to `syntopical/`.

| Capability | Public entry points (existing) | Reads | Writes |
|---|---|---|---|
| **Acquire** | `expand_seeds`, `rank`, `triage`, `apply_veto`, `download_and_ingest`, manifest helpers | thesis tree; network via scrapling-fetch | `syntopical/acquisition/` |
| **Synthesize** | `build_topic_map`, `build_disputed_questions`, `build_concept_reconciliation`, citation linters | claim ledger, concepts, thesis (via book-knowledge/book-thesis) | `syntopical/{topic-map.md,concepts/,disputed-questions/}` |
| **Lens** | `project_lens` | prior syntopical artifacts | `syntopical/lenses/<chapter>.md` |
| **Gap** | `build_coverage_report`, `seed_from_gap_report` | claim ledger, thesis | `syntopical/reports/`, `syntopical/acquisition/pending-seeds.txt` |
| **Govern** | `build_positions`, `render_per_rule`, `render_consensus_map`, `render_adversarial`, `governance_filter` | schools, prov sidecar, **constraints.edn (new)**, claim ledger | `syntopical/{positions.edn,rules/,figures/,adversarial-review.md,induction-quarantine.md}` |

The author loop these compose into: **Acquire → Synthesize → Gap → (feed back to Acquire) → Lens → book-compose**, with **Govern** as the quality gate that decides which induced/asserted rules earn a place.

## 4. De-specialization

The four sub-workflows need no code change for neutrality. The work is confined to governance docs/fixtures and SKILL.md.

### 4.1 SKILL.md

- **`description`**: rewrite to describe the five capabilities generically. No "chapter X" phrasing implying a single use; no implication that only acquire/synthesize exist. The "Use when…" triggers cover all five capabilities.
- **`metadata.version`**: set to `0.3.0`, consistent with `API_VERSION`.
- **Body**: replace the "v0.2 ships governance; the four scaffolds are dormant" framing with a description of all five live capabilities and the full `skill_api` surface (all functions, not two).

### 4.2 governance-playbook.md

Replace Praos/Algorand/τ≤1 examples with a domain-neutral illustration. Schools of thought are a general concept; the playbook will use a generic methodological-disagreement example (e.g. two named schools and a `self` school over an unspecified field), with slugs `school-a`, `school-b`, `self` and charter prose that does not encode cryptography. Document `forge govern map`, `review`, and `quarantine` alongside `build`/`report` (currently missing).

### 4.3 Fixtures and conformance

- Re-theme the `three-schools` fixture to neutral slugs and neutral `doc_id`s. Tests assert structural and stance behavior, not domain terms.
- **Replace** the `/c/epochpoet`-bound conformance test with an in-repo **domain-neutral conformance workspace** containing curated schools, a claim ledger, a prov sidecar, AND a `constraints.edn`. This canary runs in CI on every checkout instead of skipping, and exercises both the induced-rule and the new defconstraint path.

## 5. Functional fixes (governance)

### 5.1 defconstraint support

Extend `build_positions` to read `rules/constraints.edn` in addition to the induced-theory prov sidecar. For each `defconstraint` rule:

- Derive the support set from the constraint's cited claims (via the claim ledger / `derive-via` links), per v0.2 design §2.3 step 3.
- Emit positions with `:source :defconstraint` (the `Position` dataclass already carries this field).
- A workspace with constraints and no induced rules now yields positions.

Stance derivation is unchanged — it already operates on a `RuleEvidence` value object; only the evidence-gathering front-end grows a second source.

### 5.2 Staleness guard

Renderers (`render_per_rule`, `render_consensus_map`, `render_adversarial`) refuse to run when `positions.edn` is older than any source ledger it derives from, emitting a clear "`positions.edn` is stale; run `forge govern build` first" message. Implemented as a shared mtime-comparison helper so the three renderers and the CLI commands behave identically. `build_positions` itself is exempt (it is the writer).

### 5.3 Explicit non-change

`:extends` stance keeps its current count-based heuristic (partial support below threshold). The v0.2 design's prose notion of "predicates beyond what the school asserts" is not implemented and is out of scope here; the heuristic is documented as the operational definition.

## 6. Waking the sub-workflows

### 6.1 Public API

`skill_api.py` exports the four sub-workflows' top-level entry points alongside the governance functions. `API_VERSION` bumps to `(0, 3)`. Existing governance exports are unchanged (backward compatible).

### 6.2 CLI surface

`forge_cli.py` (a `click` group that already adds syntopical-metabook to `sys.path`) grows a `forge meta` group mirroring the existing `forge govern` pattern — each subcommand is a thin lazy-import wrapper that surfaces a hand-readable "skill not installed / missing prerequisite" message on import failure:

```
forge meta acquire      # citation-graph acquisition + triage + ingest
forge meta synthesize   # topic map, disputed questions, concept reconciliation
forge meta lens         # project a per-chapter lens
forge meta gap          # coverage report + feed uncovered nodes back to acquire
```

`forge govern …` is kept as-is for backward compatibility (decided: least disruption; not folded under `forge meta`). The two groups together are the skill's full CLI surface.

### 6.3 Sub-workflow argument contracts

Each command takes a workspace root and, where the entry point requires it, a `chapter_id`; optional flags pass through documented parameters (e.g. Acquire `--depth`, Gap `--required-per-node`). The CLI does not invent behavior — it wraps the existing entry points.

## 7. Boundaries (unchanged, now enforced as tests)

- **Reads only:** `raw/`, `wiki/`, `claims/`, `graph/`, `chapters/`, `rules/`, `syntopical/schools/`.
- **Writes only:** under `syntopical/`.
- **Network:** only via `scrapling-fetch`.
- **Symbolic reasoning:** only via `booklogic_adapter`.

v0.3 promotes these from prose to **enforced invariants** in the QA plan: tests assert no write escapes `syntopical/`, and that no module imports an HTTP client directly.

## 8. Dependencies

No new third-party dependencies. Sub-workflows already depend on `sibling_skills.load_skill_api` for book-knowledge / book-thesis / scrapling-fetch, on `booklogic_adapter` for symbolic reasoning (with a `SYNTOPICAL_NO_BOOKLOGIC=1` legacy fallback), and optionally on `torch` + `sentence-transformers` for Acquire ranking (skipped when absent). Governance uses the stdlib only.

## 9. The two planning deliverables

### 9.1 QA plan — `docs/superpowers/plans/2026-05-31-syntopical-metabook-qa-plan.md`

A living test contract, not a one-off checklist:

- **Layered coverage** per capability: unit (pure functions, edge cases), integration (fixture workspace, full pipeline), conformance (the new neutral canary workspace).
- **Invariants as tests:** determinism / byte-idempotence of every writer; boundary enforcement (no write outside `syntopical/`, no direct HTTP import); staleness-guard behavior.
- **CI matrix:** an entry that runs the skill's suite on every checkout, including the conformance canary (no longer skipped) and an install+import smoke leg.
- **Network-path manual smoke checklist:** the one path CI cannot fully exercise (Acquire over scrapling-fetch) gets a documented manual procedure.
- **Coverage gates:** the bar each capability must clear before its CLI command is considered shipped.

### 9.2 Utility / value plan — `docs/superpowers/plans/2026-05-31-syntopical-metabook-utility.md`

- **Who uses it and why:** the author building a book in the suite; the value each capability delivers in one line.
- **The end-to-end loop:** Acquire → Synthesize → Gap → Lens → book-compose, with Govern as the gate, drawn as a flow with the workspace artifacts each stage produces and consumes.
- **Position in the suite:** how syntopical-metabook sits above book-knowledge / neurosym-forge and feeds book-compose; what it owns that no other skill does.
- **"Use when…" scenarios:** concrete trigger scenarios that justify the rewritten `description`, one per capability.

## 10. Testing

Three layers mirroring the existing split, extended to all five capabilities:

- **Unit:** existing sub-workflow unit tests stay; add unit tests for the defconstraint evidence-gathering and the staleness helper.
- **Integration:** the existing end-to-end pipeline test stays; add CLI-level tests for `forge meta {acquire,synthesize,lens,gap}` mirroring the `forge govern` CLI tests, and a governance integration test covering a defconstraint-only workspace.
- **Conformance:** the new in-repo neutral workspace replaces the EpochPoET-bound test and always runs.

All writers remain byte-deterministic; the idempotence tests are part of the boundary-invariant suite.

## 11. PR sequence

Staged so each PR ships a usable, independently mergeable increment.

| PR | Adds | Touches |
|---|---|---|
| PR 1 | defconstraint support in `build_positions` + neutral conformance workspace + staleness guard | `scripts/governance/`, `tests/` |
| PR 2 | De-specialization: SKILL.md (description, version, body), governance-playbook, re-themed fixture | `SKILL.md`, `references/`, `tests/fixtures/` |
| PR 3 | Wake sub-workflows: `skill_api` exports (API 0.3) + `forge meta` CLI group + CLI tests | `skill_api.py`, `neurosym-forge/scripts/forge_cli.py`, `tests/` |
| PR 4 | QA plan + utility/value plan documents | `docs/superpowers/plans/` |

Each PR carries its own tests and leaves `main` green.

## 12. Open questions / explicit non-decisions

- **Multi-book aggregation** across workspaces is deferred to a later version.
- **Acquire ML ranking** stays an optional dependency; the CLI command degrades gracefully (documented) when `torch`/`sentence-transformers` are absent rather than failing hard.
- **Per-school invalidation** (a school's charter change invalidating only its rows) stays deferred; the §5.2 staleness guard is the v0.3 mechanism.
