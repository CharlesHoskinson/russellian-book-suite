# Capability delta: edn-boundary — change: booklogic-cleanup

## ADD

### REQ-EDN-010 — Ubiquitous

The `verifiers/bermuda/rules/seed.edn` file shall be valid EDN: keyword keys
are written as `:foo` (not `":foo"`), and the file round-trips through
`skills/neurosym-forge/scripts/_io.read_edn_file` to a structure where every
key is a `Keyword` instance.

**Rationale:** PR-1's boundary fix migrated the Python/Rust code paths but
missed the static data files. CLJS readers parse `":int"` as a string, not
a keyword, silently breaking downstream meander matches.
**Tested by:** `verifiers/bermuda/tests/test_rules_seed_edn_roundtrip.py::test_seed_edn_real_edn` (added in cleanup T2.1)

### REQ-EDN-011 — Ubiquitous

The `verifiers/bermuda/rules/grounded.edn` file shall be valid EDN with
keyword keys, round-tripping through `_io.read_edn_file` to a structure where
every key is a `Keyword`.

**Rationale:** Same as REQ-EDN-010, applied to the grounded-atoms file.
**Tested by:** `verifiers/bermuda/tests/test_rules_seed_edn_roundtrip.py::test_grounded_edn_real_edn` (added in cleanup T2.1)

## MODIFY

(none)

## REMOVE

(none)
