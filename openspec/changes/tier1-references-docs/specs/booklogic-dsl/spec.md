# Capability delta: booklogic-dsl — change: tier1-references-docs

## ADD

### REQ-BOOKLOGIC-040 — Ubiquitous

The framework SHALL ship `skills/neurosym-forge/references/atomspace-edn.md`
documenting the wire format of every EDN atom kind (`:expression`,
`:symbol :OPAQUE`, `:symbol :CONTEXT`), including one golden example
per kind, the type of every field, and the cross-language type
asymmetries (Edn::Key vs Edn::Str, Double vs Int discrimination).

**Rationale:** SKILL.md references this file but it does not exist.
**Tested by:** existence-and-headings check in
`skills/neurosym-forge/tests/test_reference_docs.py::test_atomspace_edn_present` (added in D1.1)

### REQ-BOOKLOGIC-041 — Ubiquitous

The framework SHALL ship `references/grounded-atoms.md` documenting
the regex dialect (`(?P<v>)` not `(?<v>)`), subject-naming convention
(`?s` placeholder, `:s` literal), and the `parse-float`/`parse-int`
helper functions in `deflift :emit` forms.

**Rationale:** Currently undocumented; major silent-failure source.
**Tested by:** `test_reference_docs.py::test_grounded_atoms_present` (added in D1.2)

### REQ-BOOKLOGIC-042 — Ubiquitous

The framework SHALL ship `references/phase-boundaries.md` documenting
the three-language pipeline (CLJS → nbb compile → intermediate EDN →
Python codegen → Rust verifier), including per-boundary schema and
test coverage.

**Rationale:** SKILL.md references this file; it does not exist.
**Tested by:** `test_reference_docs.py::test_phase_boundaries_present` (added in D1.3)

### REQ-BOOKLOGIC-043 — Ubiquitous

The framework SHALL ship `references/rewrite-rule-style.md` documenting
`defrule` conventions and CLEARLY MARKING egg as a stub (in line with
the Tier-1 SUPPORT_MATRIX.md).

**Rationale:** Authors writing `defrule` need to know it's stub today.
**Tested by:** `test_reference_docs.py::test_rewrite_rule_style_marks_stub` (added in D1.4)

### REQ-BOOKLOGIC-044 — Ubiquitous

The framework SHALL ship `references/metta-idioms.md` documenting
which MeTTa concepts the framework borrows and which it does not.

**Rationale:** SKILL.md references this file; it does not exist.
**Tested by:** `test_reference_docs.py::test_metta_idioms_present` (added in D1.5)

### REQ-BOOKLOGIC-045 — Ubiquitous

The framework SHALL ship
`references/worked-examples/osmotic-pressure/clojure.md` as a
step-by-step walkthrough of the osmotic_pressure verifier from
`sorts.edn` through `make ci`.

**Rationale:** The single most important onboarding artefact; SKILL.md
references it; it does not exist.
**Tested by:** `test_reference_docs.py::test_worked_example_walks_seven_form_families` (added in D1.6)

### REQ-BOOKLOGIC-046 — Ubiquitous

Every `.edn.tmpl` seed file under
`skills/neurosym-forge/assets/project-template/rules/booklogic/` SHALL
contain at least:
- one comment-line explaining the form's purpose,
- one commented-out worked-example form, and
- a "Common silent failures" comment block listing at least two
  recognised mis-uses.

**Rationale:** New authors discover form syntax by reading the template,
not by grepping a reference verifier.
**Tested by:** `test_seed_template_annotations.py::test_every_seed_has_example_and_failure_notes` (added in D2.8)

### REQ-BOOKLOGIC-047 — Ubiquitous

The framework SHALL ship `docs/booklogic-dsl-reference.md` covering
all seven form families with surface syntax, every keyword arg, the
compilation target, a worked example, and an anti-pattern subsection.

**Rationale:** The canonical author-facing reference; everything else
points to it.
**Tested by:** `test_reference_docs.py::test_dsl_reference_covers_seven_forms` (added in D3.1)

### REQ-BOOKLOGIC-048 — Ubiquitous

`docs/booklogic-dsl-reference.md` SHALL contain a "Debugging" section
documenting:
- `VERIFIER_DEBUG_SMT=1` (dumps Z3 solver state to stderr),
- `make extract` (the new fact-extraction preview),
- `VERIFIER_SOLVER_TIMEOUT_MS` (Z3 timeout override),
- how to interpret a `:unknown` verdict.

**Rationale:** Currently none of these are documented anywhere
user-facing.
**Tested by:** `test_reference_docs.py::test_dsl_reference_has_debugging_section` (added in D3.3)

### REQ-BOOKLOGIC-049 — Ubiquitous

The framework SHALL ship `skills/neurosym-forge/SUPPORT_MATRIX.md`
containing a table that enumerates every DSL form family and its
real wiring status (wired / stub / DROP / external-consumer), so
that authors and the LLM agent reading the skill have unambiguous
ground truth for what each form does at runtime.

**Rationale:** Closes the "SKILL.md says X, codegen does Y" leak
surfaced by the multi-solver audit.
**Tested by:** `test_support_matrix.py::test_matrix_rows_match_codegen_supported_backends` (added in D4.1)

### REQ-BOOKLOGIC-050 — Unwanted behaviour

IF `skills/neurosym-forge/SUPPORT_MATRIX.md` disagrees with the
runtime reality (e.g., the matrix claims `:backend :egg` is wired but
`codegen_axioms.py` still silently drops `:egg` constraints), THEN
the CI lint job SHALL fail with a message naming the disagreement.

**Rationale:** A static doc that drifts from code is a documentation
debt magnet; the lint pins them together.
**Tested by:** `test_support_matrix.py::test_lint_fails_on_codegen_disagreement` (added in D4.3)
