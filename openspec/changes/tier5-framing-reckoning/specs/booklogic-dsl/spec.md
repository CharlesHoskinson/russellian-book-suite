# Capability delta: booklogic-dsl — change: tier5-framing-reckoning

## ADD

### REQ-BOOKLOGIC-060 — Ubiquitous

The framework SHALL ship `docs/concepts/metta-runtime-grounded-vs-shaped.md`
(~150 lines) explicitly distinguishing what's MeTTa-runtime-grounded
(after Tier 5: `defconstraint :backend :metta`, the Phase O embedded
interpreter, the `(neighbors ...)` / `(hybrid-match ...)` /
`(neighbors-only ...)` grounded atoms) from what's MeTTa-shaped (EDN
atom encoding, `defrule` on egg, `:backend :z3` / `:cozo`). The doc
SHALL include a retraction section naming any earlier sentence that
implied "the framework runs MeTTa" without the qualifier.

**Rationale:** Tier 5 lands real MeTTa runtime work alongside the
existing MeTTa-shaped surface. Readers need a single wayfinder
naming which feature lives on which layer or the promotional drift
the external analysis flagged will re-accumulate.
**Tested by:** `skills/neurosym-forge/tests/test_reference_docs.py::test_metta_runtime_grounded_vs_shaped_present` (added in S1.1).

### REQ-BOOKLOGIC-061 — Ubiquitous

`skills/neurosym-forge/SKILL.md` SHALL (a) name the embedded
hyperon-experimental crate version + its alpha status, (b) link to
`docs/concepts/metta-runtime-grounded-vs-shaped.md` near the top of
the file, and (c) retire any pre-Tier-5 sentence that implied the
framework "runs MeTTa" without the qualifier — those sentences SHALL
be replaced with the qualified copy described in design.md.

**Rationale:** SKILL.md is the first file a fresh agent reads. If it
overstates the integration, the rest of the framework reads as a
disappointment. The qualified copy makes the runtime story honest at
the entry point.
**Tested by:** `tests/test_skill_md.py::test_skill_md_qualifies_metta_runtime_claim` and `::test_skill_md_names_hyperon_experimental_version` (added in S2.1 / S2.2).

### REQ-BOOKLOGIC-062 — Ubiquitous

`skills/neurosym-forge/SUPPORT_MATRIX.md` SHALL gain a row
`defconstraint :backend :metta | wired (alpha) | hyperon-experimental`
mirroring Phase O's REQ-METTA-045, and SHALL add a `wired (alpha)`
status-legend entry naming the alpha caveat (API may change
incompatibly; pinned crate version; deprecation runbook covers
migration).

**Rationale:** The support matrix is the live ground-truth surface
for which backend / form combos work. A new `:metta` backend without
a matrix row is exactly the documentation-debt shape Tier 1's
SUPPORT_MATRIX.md was built to retire.
**Tested by:** `tests/test_support_matrix.py::test_metta_row_present_with_alpha_qualifier` (added in S3.1).

### REQ-BOOKLOGIC-063 — Ubiquitous

`skills/neurosym-forge/references/metta-idioms.md` SHALL be rewritten
to: (a) keep the existing "what we borrow from MeTTa" / "what we
don't borrow" structure, (b) lift the §1 subsections to acknowledge
they describe the EDN encoding rather than a runtime, (c) add a third
section "What we now embed at runtime" listing the Phase O / P / Q / R
capabilities, and (d) replace any pre-Tier-5 claim that the framework
"runs a MeTTa interpreter" with the qualified post-Tier-5 statement.

**Rationale:** The metta-idioms reference is the canonical
"is this idiom available?" lookup; Tier 5 changes the answer for
several idioms (atomspace, grounded atoms) from "shaped" to
"runtime-grounded". Updating the doc keeps that lookup honest.
**Tested by:** `tests/test_reference_docs.py::test_metta_idioms_has_runtime_section` (added in S4.2).

### REQ-BOOKLOGIC-064 — Unwanted behaviour

IF a future doc PR introduces promotional language that overstates
the MeTTa integration (e.g., describes `:backend :metta` as
"production-ready" or "stable" while hyperon-experimental remains
alpha), THEN the drift lint at
`skills/neurosym-forge/tests/test_support_matrix.py` SHALL fail with
a message naming the offending word and the file it appeared in. The
lint SHALL check SUPPORT_MATRIX.md, SKILL.md, and
references/metta-idioms.md `:metta`-adjacent sections.

**Rationale:** Static docs drift; the lint is the only mechanism that
pins the framing-honesty contract over time. The forbidden-word set
(production, production-ready, stable, GA) is narrow enough to avoid
false positives and broad enough to catch the drift shapes the
external analysis identified.
**Tested by:** `tests/test_support_matrix.py::test_metta_row_not_described_as_production_or_stable` and `::test_skill_md_and_metta_idioms_no_production_claim` (added in S5.1 / S5.2).

### REQ-BOOKLOGIC-065 — Optional feature

WHERE the framework's authors choose to deprecate `:backend :metta`
(e.g., hyperon-experimental's API changes incompatibly, a security
advisory lands, or a performance regression exceeds acceptable
bounds), the framework SHALL provide a deprecation runbook at
`docs/operations/deprecate-metta-backend.md` covering: trigger
conditions, migration paths per constraint shape (arithmetic →
`:backend :z3`; reachability → `:backend :cozo` or Z3 axioms), the
test-file impact, the SUPPORT_MATRIX.md update step, and a
changelog / external-README communication template.

**Rationale:** hyperon-experimental is alpha; the framework should
not be paralysed if it moves. The runbook makes deprecation a
documented, low-stakes operation rather than an unbounded refactor.
**Tested by:** `tests/test_reference_docs.py::test_deprecate_metta_runbook_present` (added in S6.1).

### REQ-BOOKLOGIC-066 — Ubiquitous

`docs/booklogic-dsl-reference.md` §2.5 (the `defconstraint` operator
table) SHALL gain a `:metta` backend row that explicitly carries the
`(alpha)` qualifier, names the hyperon-experimental crate as the
runtime, and links to Phase O's REQ-METTA-045.

**Rationale:** §2.5 is the canonical author-facing reference for
backend choice. A new backend without a row there is invisible to
authors who read the reference top-down; the `(alpha)` qualifier
inline is the wayfinder readers use to know which surface is
hardened and which is on the runtime-grounded edge.
**Tested by:** `tests/test_reference_docs.py::test_dsl_reference_section_two_five_lists_metta_alpha_row` (added in S6.2).
