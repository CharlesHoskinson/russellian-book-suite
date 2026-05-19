# Change: tier5-edn-metta-bijection

**Tier:** 5 of 5 (wire format + storage shape)
**Branch:** `plan/tier5-metta-runtime`
**Depends on:** Tier 1 (binding-schema, REQ-EDN-051 list-vs-vector),
Tier 5 (metta-backend)

## Why

Change `tier5-metta-backend` embeds hyperon-experimental as a
4th codegen backend, but every input to that backend currently
passes through ad-hoc per-call string assembly inside
`_emit_metta_block`. The framework's first-class wire format is
EDN; MeTTa's wire format is its surface s-expression syntax;
without a canonical bijection between the two, every code path
that wants to round-trip an atom through MeTTa has to reinvent
the translation.

The external analysis comparing neurosym-forge to MeTTa /
Atomspace also surfaced a second observation: the Atomspace's
most valuable storage property is **automatic deduplication of
sub-expressions**. Inserting `(P (Q a) b)` and `(R (Q a))`
produces one shared `(Q a)` atom; query and indexing operations
benefit from that sharing for free. The framework's current
in-memory atom store (`atom.py`) treats every inserted atom as
fresh, even when the underlying expression has been seen before.

## What

- Define the canonical bijection `edn_to_metta(form) -> str`
  and `metta_to_edn(text) -> form` such that
  `metta_to_edn(edn_to_metta(x)) == x` for every atom shape in
  `skills/neurosym-forge/tests/golden/`.
- Specify the per-atom-kind translation rules: keyword,
  variable, list, vector, map, tagged literal. The list-vs-vector
  distinction from REQ-EDN-051 is preserved through a
  `(Vector ...)` head symbol on the MeTTa side.
- Add a new `skills/neurosym-forge/scripts/_atomspace.py` module
  implementing `class Atomspace` with hash-cons-based
  deduplication: structurally identical sub-expressions reuse a
  single canonical handle. A `dedup_factor()` accessor exposes
  the deduplication property as a measurable invariant.
- Round-trip tests for every golden atom file through MeTTa
  surface syntax assert byte-stability.

## Capabilities touched

- `edn-boundary` — EXTEND (REQ-EDN-060..067 join the existing
  REQ-EDN-040..053 series)

## Implementation notes

See `docs/plans/2026-05-19-tier5-metta-runtime.md`, Phase P.

## Acceptance

- 8 REQ-EDN-060..067 IDs ship in
  `specs/edn-boundary/spec.md`.
- A round-trip test through MeTTa surface syntax passes
  byte-identically for every `tests/golden/*.edn` file.
- `_atomspace.py` is vendored alongside `_canonical.py` /
  `_edn_reader.py` at scaffold time.
- Inserting an identical sub-expression twice returns the same
  handle; `dedup_factor()` strictly decreases.
