# Capability delta: bermuda-rules — change: booklogic-cleanup

## ADD

### REQ-BERMUDA-RULES-001 — State-driven

While the verifier reads `verifiers/bermuda/rules/seed.edn`, the file shall
contain the same semantic content as before the cleanup (sorts, rules, atoms
collections) expressed with `Keyword`-shaped keys.

**Rationale:** Cleanup is a syntax conversion, not a semantic edit.
**Tested by:** `verifiers/bermuda/tests/test_rules_seed_edn_roundtrip.py::test_seed_preserves_semantics` (added in cleanup T2.2)

### REQ-BERMUDA-RULES-002 — State-driven

While the verifier reads `verifiers/bermuda/rules/grounded.edn`, the file
shall contain the same semantic content as before the cleanup expressed with
`Keyword`-shaped keys.

**Rationale:** Same as REQ-BERMUDA-RULES-001 for grounded atoms.
**Tested by:** `verifiers/bermuda/tests/test_rules_seed_edn_roundtrip.py::test_grounded_preserves_semantics` (added in cleanup T2.3)

## MODIFY

(none)

## REMOVE

(none)
