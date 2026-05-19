# Capability delta: theory-revision — change: tier6-agm-revision

This change introduces a new capability `theory-revision`,
an AGM-compliant operation that mutates an induced theory's
provenance sidecar when new evidence (a retracted paper, a
contradicting atom) reaches a previously-induced rule. The
operation contracts the affected rule's support, recomputes
entrenchment, and demotes or quarantines the rule's status;
it never silently overwrites a rule, and quarantined rules
persist in the sidecar.

## ADD

### REQ-REVISE-040 — Ubiquitous

The framework SHALL ship
`skills/neurosym-forge/scripts/_agm_revision.py` exposing
`revise_theory(induced_path: Path, prov_path: Path,
retracted_docs: list[str] | None, contradicting_atoms:
list[str] | None) -> RevisionReport`. The function SHALL
load the induced theory and the provenance sidecar from the
supplied paths, mutate the sidecar in place per the algorithm
in REQ-REVISE-041, write the sidecar back to `prov_path`, and
return the `RevisionReport` per REQ-REVISE-045. The induced
theory file at `induced_path` SHALL NOT be rewritten — only
the sidecar's `:prov/*` fields change.

**Rationale:** A single entry point keeps the revision
discipline (contract → re-validate → recompute → record) in
one place; surfacing only the sidecar as the mutation target
preserves the rule-text-vs-rule-status separation the Phase Y
two-file layout already established.
**Tested by:**
`tests/test_agm_revision.py::test_revise_theory_signature_and_in_place_sidecar_mutation`
(added in Z1.2)

### REQ-REVISE-041 — Ubiquitous

For every rule in the sidecar, `revise_theory` SHALL:
(a) compute the set
`:prov/source-documents` ∩ `retracted_docs` and the set
`:prov/derived-from-atoms` ∩ `contradicting_atoms`;
(b) skip rules where both sets are empty (rules unaffected
by this revision retain their entrenchment and status);
(c) remove the affected atoms from
`:prov/derived-from-atoms` and the affected docs from
`:prov/source-documents` on each affected rule;
(d) re-run the 5-fold document-held-out validation pass
from Phase X on the diminished support to produce a new
`held_out_sat_rate`;
(e) recompute the rule's `:prov/entrenchment` as
`held_out_sat_rate × min(support_doc_count / 10.0, 1.0)`
clamped to `[0.0, 1.0]`. When a rule carries
`:prov/induced-from-corpus`, `retracted_docs` SHALL be
applied only if the document belongs to the rule's source
corpus.

**Rationale:** The contract-then-re-validate sequence
implements the AGM contraction step under the Levi identity
`K * φ = (K - ¬φ) + φ`. The 10-document saturation in the
entrenchment formula matches the "≥10 papers" rule-of-thumb
authors apply when curating hand-written constraints and
prevents a single highly-supported rule from dominating the
threshold cliff. Per-corpus scoping prevents a retraction in
one corpus from spuriously demoting rules induced from
another corpus.
**Tested by:**
`tests/test_agm_revision.py::test_single_paper_one_rule_contracts`,
`tests/test_agm_revision.py::test_single_paper_five_rules_contract`,
`tests/test_agm_revision.py::test_entrenchment_formula_clamps_to_unit_interval`
(added in Z7.1-Z7.2)

### REQ-REVISE-042 — Ubiquitous

Status transitions SHALL be deterministic functions of
entrenchment: `:prov/entrenchment >= 0.7` SHALL set
`:prov/status` to `:active`;
`0.4 <= :prov/entrenchment < 0.7` SHALL set `:prov/status`
to `:tentative`; `:prov/entrenchment < 0.4` SHALL set
`:prov/status` to `:quarantined`. Quarantined rules SHALL
persist in both `induced-theory.edn` and the provenance
sidecar with the lower status; `revise_theory` SHALL NOT
delete a rule.

**Rationale:** Deterministic thresholds let a reviewer
reproduce the framework's status assignment from the
entrenchment column alone, removing one source of "why did
this rule change?" friction. Preserving quarantined rules
maintains the AGM recovery postulate: enough of the prior
belief set remains to support re-expansion when new evidence
arrives.
**Tested by:**
`tests/test_agm_revision.py::test_status_thresholds_deterministic`,
`tests/test_agm_revision.py::test_quarantined_rule_persists_in_sidecar`
(added in Z4.2-Z4.3)

### REQ-REVISE-043 — Optional feature

WHERE a quarantined rule later regains support — e.g., a
new corpus adds confirming atoms that push entrenchment
back into the `:tentative` or `:active` band — the
revision MAY auto-promote the rule. Tier 6 SHALL implement
contract-down only; the promote-up direction is explicitly
deferred to Tier 7 because it requires the AST-aware
semantic-distance metric the design spec
(`docs/specs/2026-05-19-tier6-theory-induction-design.md`
§"Open gaps after Tier 6") flagged as open research. In
Tier 6, `revise_theory` SHALL NOT transition any rule's
status from `:tentative` to `:active` or from
`:quarantined` to `:active` or `:tentative`.

**Rationale:** Promote-up reintroduces a rule the framework
had previously down-graded; without an AST-aware
semantic-distance metric, the framework cannot tell whether
the new supporting atoms describe the same underlying
relationship or a coincidentally-similar one. Deferring
promote-up to Tier 7 keeps Tier 6's revision behaviour
deterministic and audit-clean.
**Tested by:**
`tests/test_agm_revision.py::test_no_promote_up_in_tier_six`
(added in Z4.4)

### REQ-REVISE-044 — Unwanted behaviour

IF a single revision moves every rule in the induced theory
to `:quarantined`, THEN `revise_theory` SHALL set
`RevisionReport.full_quarantine_warning = True` AND log a
structured warning entry naming the `retracted_docs` and
`contradicting_atoms` arguments that drove the revision.

**Rationale:** Full theory quarantine on a single revision
input is a strong signal: either the new evidence is itself
in error (a misattributed retraction, a noisy contradicting
atom) or the theory was overfit on the prior corpus. The
framework does not auto-resolve; surfacing the warning is
the discipline so a human reviewer can decide whether to
accept the quarantine, override the input, or re-induce
from scratch.
**Tested by:**
`tests/test_agm_revision.py::test_full_quarantine_warning_fires`
(added in Z7.4)

### REQ-REVISE-045 — Ubiquitous

`revise_theory` SHALL return a `RevisionReport` dataclass
with the fields: `rules_affected` (int — count of rules
whose status transitioned, not the count whose entrenchment
merely changed); `rules_active`, `rules_tentative`,
`rules_quarantined` (int — post-revision counts by
status); `diff_summary` (string — a `; `-separated list of
`<rule-id>: <old-status> -> <new-status>` entries ordered
by rule id); and `full_quarantine_warning` (bool per
REQ-REVISE-044).

**Rationale:** A stable report shape is what lets Phase AA's
`forge revise` print a deterministic summary to the human
reviewer; surfacing `rules_affected` and per-status counts
separately means a CLI can show "3 rules transitioned; 12
remain active" without re-walking the sidecar.
**Tested by:**
`tests/test_agm_revision.py::test_revision_report_shape_and_counts`
(added in Z6.1-Z6.3)

### REQ-REVISE-046 — Ubiquitous

A test suite SHALL exercise at minimum the following four
scenarios: (a) retracting a paper that supports exactly 1
rule causes that rule's entrenchment to drop while leaving
other rules unchanged; (b) retracting a paper that supports
5 rules causes all 5 to contract; (c) a contradicting atom
on an `:active` rule with entrenchment near the 0.7
boundary transitions the rule to `:tentative`; (d) a
synthetic scenario where every rule's support shrinks below
the 0.4 quarantine threshold fires
`full_quarantine_warning`. Each test SHALL operate on a
fixture sidecar and assert the post-revision rule states.

**Rationale:** The four scenarios together cover the
algorithm's branching: single-rule vs multi-rule contraction,
status transitions across the 0.7 boundary, and the
full-quarantine alarm. Coverage of these four cases is the
regression boundary for the revision discipline.
**Tested by:**
`tests/test_agm_revision.py::test_single_paper_one_rule_contracts`,
`tests/test_agm_revision.py::test_single_paper_five_rules_contract`,
`tests/test_agm_revision.py::test_contradicting_atom_downgrades_active_to_tentative`,
`tests/test_agm_revision.py::test_full_quarantine_warning_fires`
(added in Z7.1-Z7.4)
