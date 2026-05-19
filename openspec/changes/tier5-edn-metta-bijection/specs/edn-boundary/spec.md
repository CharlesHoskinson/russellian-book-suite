# Capability delta: edn-boundary — change: tier5-edn-metta-bijection

This change EXTENDS the existing `edn-boundary` capability
(REQ-EDN-040..053 shipped by Tier 1) with REQ-EDN-060..067
defining the canonical bijection between BookLogic EDN atoms
and MeTTa surface s-expressions, plus a hash-cons-based
in-memory Atomspace that deduplicates structurally identical
sub-expressions.

## ADD

### REQ-EDN-060 — Ubiquitous

The framework SHALL define a bijection
`edn_to_metta(form) -> str` and
`metta_to_edn(text) -> form` in a new module
`skills/neurosym-forge/scripts/_edn_metta.py`, such that
`metta_to_edn(edn_to_metta(x)) == x` for every atom shape
present in `skills/neurosym-forge/tests/golden/*.edn`. Equality
SHALL be defined as: the canonical EDN-writer output for the
round-tripped value equals the canonical EDN-writer output for
the original.

**Rationale:** Without a defined bijection, every Phase O code
path that wants to talk to the embedded MeTTa runtime reinvents
the translation. One canonical translator is the single source
of truth.
**Tested by:** `tests/test_edn_metta_round_trip.py::test_seven_golden_atoms_round_trip` (added in P1.3)

### REQ-EDN-061 — Ubiquitous

The bijection SHALL implement the following per-atom-kind rules:

- EDN keyword `:foo` SHALL translate to MeTTa symbol `foo` (no
  prefix); on the reverse direction, the keyword/symbol
  distinction is recovered via a side-channel kw-set produced
  by `edn_to_metta`.
- EDN logic variable `?x` SHALL translate to MeTTa variable
  `$x` and back.
- EDN list `(a b c)` SHALL translate to MeTTa expression
  `(a b c)` and back.
- EDN vector `[a b c]` SHALL translate to MeTTa expression
  `(Vector a b c)` and back. The `Vector` head symbol is
  reserved at scaffold time.

**Rationale:** Preserves the EdnList-vs-EdnVector distinction
from REQ-EDN-051 — meander dispatch on `(list? form)` keeps
working after a MeTTa round-trip.
**Tested by:** `tests/test_edn_metta_round_trip.py::test_keyword_var_list_vector_round_trip` (added in P1.2)

### REQ-EDN-062 — Ubiquitous

EDN map `{:k1 v1 :k2 v2}` SHALL translate to MeTTa
`(Map (k1 v1) (k2 v2))` with entries ordered by lexicographic
sort of the canonical written form of each key. The reverse
direction SHALL strip the `Map` head and reconstruct an EDN map.
Byte-stability of the round-trip depends on this deterministic
ordering.

**Rationale:** EDN maps have no stable insertion order; without
a sort step, two semantically identical maps produce different
MeTTa strings, and the byte-stability invariant fails.
**Tested by:** `tests/test_edn_metta_round_trip.py::test_map_round_trip_is_byte_stable_regardless_of_insertion_order` (added in P1.2)

### REQ-EDN-063 — Optional feature

WHERE a tagged literal `#inst "..."` appears in EDN, the
framework SHALL translate to MeTTa `(Inst "...")` and back.
IF any other reader-tag form (`#uuid`, `#js/object`, etc.)
appears, THEN `edn_to_metta` SHALL raise `BijectionError` with
a remediation message naming the unsupported tag.

**Rationale:** EDN reader tags are open-ended; the framework
supports `#inst` because timestamps appear in claim provenance,
and rejects others loudly so the bijection's coverage is never
silently truncated.
**Tested by:** `tests/test_edn_metta_round_trip.py::test_inst_round_trip_and_other_tags_raise` (added in P2.3)

### REQ-EDN-064 — Ubiquitous

A new module `skills/neurosym-forge/scripts/_atomspace.py`
SHALL implement `class Atomspace` providing:

- `add(atom) -> Handle` — insert the atom; return a canonical
  handle. Structurally identical sub-expressions SHALL share a
  single handle (hash-cons).
- `lookup(handle) -> atom`.
- `iter_atoms() -> Iterator[tuple[Handle, atom]]`.
- `dedup_factor() -> float` — ratio of unique handles to total
  insertions. Starts at 1.0; strictly decreases each time a
  duplicate sub-expression is inserted.
- `count() -> int` — number of unique handles.

The implementation SHALL use hash-cons via tuple-keyed dict
(per `design.md` choice (b)), so insertion of an N-deep atom is
O(N), not O(N²).

**Rationale:** The Atomspace's most valuable property is
automatic deduplication of sub-expressions; the framework's
current `atom.py` does not deliver this and the indexing /
embedding layers (REQ-EMBED-040..046) need it.
**Tested by:** `tests/test_atomspace.py::test_atomspace_handles_deeply_nested_atoms` and `::test_dedup_factor_starts_at_one` (added in P3.2)

### REQ-EDN-065 — Unwanted behaviour

IF a structurally identical sub-expression is added to the
Atomspace twice, THEN `Atomspace.add` SHALL return the same
handle both times, and `dedup_factor` SHALL strictly decrease
on the second insertion. The reverse `lookup` SHALL produce
the single canonical atom regardless of which insertion order
produced the handle. Identity SHALL be structural, not nominal:
EDN `(P (Q a) b)` inserted twice SHALL share one `(Q a)` child
handle.

**Rationale:** This is the load-bearing dedup invariant — the
test exists to catch a regression where two equal atoms produce
different handles (which would silently double the embedding
sidecar's work and break the wiki's "one fact, one node"
property).
**Tested by:** `tests/test_atomspace.py::test_duplicate_insertion_returns_same_handle` and `::test_shared_subexpression_shares_handle` (added in P3.3)

### REQ-EDN-066 — Ubiquitous

The 7 golden atom files at `skills/neurosym-forge/tests/golden/`
(`canonical_var_name.edn`, `constraint_entry.edn`,
`context_atom.edn`, `expression_atom.edn`, `opaque_atom.edn`,
`predicate_entry.edn`, `verdict.edn`) SHALL each have a
round-trip test through MeTTa surface syntax. Byte-stability is
the invariant: writer-output equality before and after the
EDN → MeTTa → EDN round-trip.

**Rationale:** The golden files are the framework's
canonical-shape oracle; the bijection has not landed until they
all round-trip through it.
**Tested by:** `tests/test_edn_metta_round_trip.py::test_all_seven_golden_files_round_trip_byte_stable` (added in P1.3)

### REQ-EDN-067 — Ubiquitous

`_edn_metta.py` and `_atomspace.py` SHALL be vendored at
scaffold time alongside `_canonical.py`, `_edn_reader.py`, and
`_edn_writer.py`. A project scaffolded by `scaffold_project.py`
SHALL contain both modules at the expected paths.

**Rationale:** Downstream verifier projects need the bijection
and storage modules in the same place they expect the rest of
the EDN tooling. Scaffold parity matters.
**Tested by:** `tests/test_scaffold_manifest.py::test_scaffold_includes_edn_metta_and_atomspace_modules` (added in P4.2)
