# Change: tier1-references-docs

**Tier:** 1 of 4
**Branch:** `feat/tier1-references-docs`
**Depends on:** none (independent docs change)

## Why

The onboarding audit found that `skills/neurosym-forge/SKILL.md` lists
six reference files under `references/` (metta-idioms, atomspace-edn,
grounded-atoms, phase-boundaries, rewrite-rule-style, worked-examples/
osmotic-pressure/clojure.md) but **none of those files actually exist**.
A new author following the README trail hits a dead end. Every existing
`.edn.tmpl` seed file in the project template is `{:forms []}` with
zero comments, zero examples, zero inline schema hints. The author has
to reverse-engineer the DSL by reading the osmotic_pressure source.

The undocumented contracts identified during onboarding:
- Python regex dialect (`(?P<v>)` not `(?<v>)`)
- Subject-naming convention (`?s` placeholder, `:s` literal must match)
- Valid `:backend` names (only `:z3` is actually wired)
- Valid `:value-kind` values (`:real`, `:int`, `:bool`, `:string`)
- `:from :claim/canonical-text` field name on lifts
- The `VERIFIER_DEBUG_SMT=1` env-var debugging affordance

## What

- Fill `skills/neurosym-forge/references/` with the six promised files.
- Annotate every `.edn.tmpl` seed file with a commented-out example
  and a one-line schema hint at the top.
- Add `docs/booklogic-dsl-reference.md` as the canonical author-facing
  DSL reference: form syntax, every keyword arg, every value type,
  every silent-failure path and how to recognise it.
- Add a `SUPPORT_MATRIX.md` at the skill root that explicitly
  enumerates: which DSL backends are wired, which form families have
  end-to-end codegen, which are stub/partial/wired status. (Closes
  the "skill claims X, code does Y" gap surfaced by the multi-solver
  audit.)

## Capabilities touched

- `booklogic-dsl` — MODIFY (adds docs REQs)

## Implementation notes

See `docs/plans/2026-05-18-tier1-general-purpose.md`, Phase D.

## Acceptance

- Every file path mentioned in `skills/neurosym-forge/SKILL.md` exists
  on disk.
- Every `.edn.tmpl` seed has at least one commented-out example form
  and a one-line schema hint.
- `docs/booklogic-dsl-reference.md` covers all 7 form families with
  syntax + valid keyword args + an "anti-pattern / silent failure"
  subsection per form.
- A fresh `scaffold_project` produces a project where the author can
  reach a working `make extract` (REQ-INGEST-040 above) within ~30 min
  of reading the docs alone, without grepping osmotic_pressure source.
