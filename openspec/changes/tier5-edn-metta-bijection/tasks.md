# Tasks: tier5-edn-metta-bijection

See `docs/plans/2026-05-19-tier5-metta-runtime.md` Phase P for
full TDD steps. Task numbers correspond 1:1.

## Phase P.1 — Bijection module

- [ ] P1.1: Create `skills/neurosym-forge/scripts/_edn_metta.py` exposing `edn_to_metta(form) -> str` and `metta_to_edn(text) -> form`; both side-aware (carry kw-vs-symbol info through the round-trip). (REQ-EDN-060)
- [ ] P1.2: Implement the per-atom-kind translation rules (keyword, var, list, vector, map, tagged literal) per the bijection rules table in `design.md`. (REQ-EDN-061, REQ-EDN-062, REQ-EDN-063)
- [ ] P1.3: Failing test `tests/test_edn_metta_round_trip.py::test_seven_golden_atoms_round_trip` asserts byte-stability for every golden file. Commit. (REQ-EDN-066)

## Phase P.2 — Reader tag handling

- [ ] P2.1: `metta_to_edn` recognises `(Inst "...")` heads and emits `#inst "..."` on the EDN side. (REQ-EDN-063)
- [ ] P2.2: Other reader-tag forms (`#uuid`, `#js`, etc.) raise `BijectionError` with a remediation message. (REQ-EDN-063)
- [ ] P2.3: Failing test `tests/test_edn_metta_round_trip.py::test_unsupported_reader_tag_raises` covers the error path. Commit.

## Phase P.3 — Atomspace storage

- [ ] P3.1: Create `skills/neurosym-forge/scripts/_atomspace.py` with `class Atomspace` plus `class Handle` (newtype around int). Hash-cons via tuple-keyed dict per `design.md` choice (b). (REQ-EDN-064)
- [ ] P3.2: Implement `add`, `lookup`, `iter_atoms`, `dedup_factor`, `count`. (REQ-EDN-064)
- [ ] P3.3: Failing test `tests/test_atomspace.py::test_duplicate_insertion_returns_same_handle` asserts the dedup invariant and that `dedup_factor` strictly decreases on duplicate insertion. Commit. (REQ-EDN-065)

## Phase P.4 — Scaffold integration

- [ ] P4.1: Add `_edn_metta.py` and `_atomspace.py` to the scaffold manifest in `skills/neurosym-forge/scripts/scaffold_project.py`. (REQ-EDN-067)
- [ ] P4.2: A new project scaffolded by `scaffold_project.py --slug demo` contains both modules at `demo/scripts/`. Commit. (REQ-EDN-067)

## Phase P.5 — Test fixtures + bench

- [ ] P5.1: Add `tests/test_atomspace.py::test_atomspace_handles_deeply_nested_atoms` — assert insertion of a 64-deep nested expression takes < 100 ms (hash-cons keeps it O(N), the naive writer-based approach would not). (REQ-EDN-064)
- [ ] P5.2: Push branch `plan/tier5-metta-runtime`; open PR; merge on green CI.
