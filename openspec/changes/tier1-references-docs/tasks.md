# Tasks: tier1-references-docs

See `docs/plans/2026-05-18-tier1-general-purpose.md` Phase D for full
TDD steps. Task numbers correspond 1:1.

## Phase D.1 — Reference files

- [ ] D1.1: Write `skills/neurosym-forge/references/atomspace-edn.md` (200-400 lines, one section per atom kind + golden example + type table). (REQ-BOOKLOGIC-040)
- [ ] D1.2: Write `references/grounded-atoms.md` (regex dialect, subject convention, parse-float/parse-int helpers). (REQ-BOOKLOGIC-041)
- [ ] D1.3: Write `references/phase-boundaries.md` (the 3-language pipeline diagram + per-boundary schema). (REQ-BOOKLOGIC-042)
- [ ] D1.4: Write `references/rewrite-rule-style.md` (defrule conventions; clearly marks egg as stub). (REQ-BOOKLOGIC-043)
- [ ] D1.5: Write `references/metta-idioms.md` (what we borrow from MeTTa; what we don't). (REQ-BOOKLOGIC-044)
- [ ] D1.6: Write `references/worked-examples/osmotic-pressure/clojure.md` (step-by-step walkthrough). (REQ-BOOKLOGIC-045)
- [ ] D1.7: Commit.

## Phase D.2 — Seed template annotations

- [ ] D2.1: Annotate `skills/neurosym-forge/assets/project-template/rules/booklogic/sorts.edn.tmpl` with schema hint + commented example. (REQ-BOOKLOGIC-046)
- [ ] D2.2: Same for predicates.edn.tmpl. (REQ-BOOKLOGIC-046)
- [ ] D2.3: Same for lifts.edn.tmpl. (REQ-BOOKLOGIC-046)
- [ ] D2.4: Same for rules.edn.tmpl. (REQ-BOOKLOGIC-046)
- [ ] D2.5: Same for constraints.edn.tmpl. (REQ-BOOKLOGIC-046)
- [ ] D2.6: Same for queries.edn.tmpl. (REQ-BOOKLOGIC-046)
- [ ] D2.7: Same for remedies.edn.tmpl. (REQ-BOOKLOGIC-046)
- [ ] D2.8: Add a test that asserts every `.edn.tmpl` seed has at least one comment-line and one commented-out example form. (REQ-BOOKLOGIC-046)
- [ ] D2.9: Commit.

## Phase D.3 — Canonical DSL reference

- [ ] D3.1: Write `docs/booklogic-dsl-reference.md` (~800-1200 lines, structure per design.md). (REQ-BOOKLOGIC-047)
- [ ] D3.2: Add link from `skills/neurosym-forge/SKILL.md` "see references" section to the new doc. (REQ-BOOKLOGIC-047)
- [ ] D3.3: Add a "Debugging" section covering `VERIFIER_DEBUG_SMT`, `make extract`, and `:unknown` interpretation. (REQ-BOOKLOGIC-048)
- [ ] D3.4: Commit.

## Phase D.4 — Support matrix

- [ ] D4.1: Write `skills/neurosym-forge/SUPPORT_MATRIX.md` with the form-family / status table per design.md. (REQ-BOOKLOGIC-049)
- [ ] D4.2: Add link from skill SKILL.md → SUPPORT_MATRIX.md. (REQ-BOOKLOGIC-049)
- [ ] D4.3: Add a CI lint that fails if SUPPORT_MATRIX.md disagrees with codegen reality (parsed from `SUPPORTED_BACKENDS` set in codegen_axioms.py). (REQ-BOOKLOGIC-050)
- [ ] D4.4: Commit.

## Phase D.5 — Open PR

- [ ] D5.1: Push branch `feat/tier1-references-docs` and open PR.
- [ ] D5.2: Merge on green CI.
