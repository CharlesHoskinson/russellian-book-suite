# Tasks: tier6-agm-revision

See `docs/plans/2026-05-19-tier6-theory-induction.md` Phase Z
for full TDD steps. Task numbers correspond 1:1.

## Phase Z.1 — Module skeleton

- [ ] Z1.1: New
  `skills/neurosym-forge/scripts/_agm_revision.py` declaring
  `@dataclass RevisionReport` with fields
  `rules_affected`, `rules_active`, `rules_tentative`,
  `rules_quarantined`, `diff_summary`,
  `full_quarantine_warning`. (REQ-REVISE-045)
- [ ] Z1.2: Function signature
  `revise_theory(induced_path, prov_path, retracted_docs,
  contradicting_atoms) -> RevisionReport` declared with
  type hints. (REQ-REVISE-040)

## Phase Z.2 — Affected-rule detection

- [ ] Z2.1: For every rule in the sidecar, compute the
  set-intersection of its
  `:prov/source-documents` ∩ `retracted_docs` and its
  `:prov/derived-from-atoms` ∩ `contradicting_atoms`.
  (REQ-REVISE-041)
- [ ] Z2.2: Skip rules with empty intersections (unaffected
  rules retain their entrenchment / status). (REQ-REVISE-041)
- [ ] Z2.3: Per-corpus scoping: when a rule carries
  `:prov/induced-from-corpus`, apply `retracted_docs` only
  if the doc belongs to that corpus. (REQ-REVISE-041)

## Phase Z.3 — Support contraction

- [ ] Z3.1: Remove affected atoms from
  `:prov/derived-from-atoms`; remove affected docs from
  `:prov/source-documents`. (REQ-REVISE-041)
- [ ] Z3.2: Re-run Phase X's 5-fold document-held-out
  validation on the diminished support; capture the new
  `held_out_sat_rate`. (REQ-REVISE-041)

## Phase Z.4 — Entrenchment + status

- [ ] Z4.1: Implement the entrenchment formula
  `held_out_sat_rate × min(support_doc_count / 10.0, 1.0)`
  bounded in `[0.0, 1.0]`. (REQ-REVISE-041)
- [ ] Z4.2: Status threshold lookup: `>= 0.7` → `:active`;
  `[0.4, 0.7)` → `:tentative`; `< 0.4` → `:quarantined`.
  (REQ-REVISE-042)
- [ ] Z4.3: Quarantined rules are NOT deleted; status is
  recorded and the rule persists in both the theory file and
  the sidecar. (REQ-REVISE-042)
- [ ] Z4.4: Promote-up is explicitly deferred — Tier 6
  implements contract-down only; assert no rule's status
  ever moves from `:tentative` → `:active` or
  `:quarantined` → `:active` in this tier. (REQ-REVISE-043)

## Phase Z.5 — Full-quarantine warning

- [ ] Z5.1: After processing every rule, count
  `:quarantined` rules; if equal to total rule count, set
  `RevisionReport.full_quarantine_warning = True` and log a
  structured warning naming the revision input.
  (REQ-REVISE-044)

## Phase Z.6 — RevisionReport assembly

- [ ] Z6.1: Build `diff_summary` as a `; `-separated string
  of `<rule-id>: <old-status> -> <new-status>` entries,
  ordered by rule id. (REQ-REVISE-045)
- [ ] Z6.2: Populate post-revision status counts
  (`rules_active`, `rules_tentative`,
  `rules_quarantined`). (REQ-REVISE-045)
- [ ] Z6.3: `rules_affected` counts rules whose status
  transitioned (NOT rules whose entrenchment merely
  changed). (REQ-REVISE-045)

## Phase Z.7 — Test harness

- [ ] Z7.1: `tests/test_agm_revision.py::test_single_paper_one_rule_contracts`.
  Fixture: 3-rule theory; one rule supported by the
  retracted paper. Assert: the affected rule's entrenchment
  drops; the other two are unchanged. (REQ-REVISE-046)
- [ ] Z7.2: `tests/test_agm_revision.py::test_single_paper_five_rules_contract`.
  Fixture: 8-rule theory; 5 rules supported by the
  retracted paper. Assert: all 5 rules contract; the other 3
  are unchanged. (REQ-REVISE-046)
- [ ] Z7.3: `tests/test_agm_revision.py::test_contradicting_atom_downgrades_active_to_tentative`.
  Fixture: 1 rule at `:active` with entrenchment 0.72;
  contradicting atom drops support enough to land in
  `[0.4, 0.7)`. (REQ-REVISE-046)
- [ ] Z7.4: `tests/test_agm_revision.py::test_full_quarantine_warning_fires`.
  Fixture: 3-rule theory where every rule's support shrinks
  below 0.4 after revision. Assert: warning fires; structured
  log entry present. (REQ-REVISE-044)

## Phase Z.8 — Commit

- [ ] Z8.1: Commit `_agm_revision.py` + tests once Z1-Z7 are
  green.
