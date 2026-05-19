# Design: tier5-edn-metta-bijection

## Bijection rules table

| EDN atom shape            | EDN sample          | MeTTa surface     |
|---------------------------|---------------------|-------------------|
| Keyword                   | `:foo`              | `foo`             |
| Logic variable            | `?x`                | `$x`              |
| Symbol                    | `bar`               | `bar`             |
| List `(...)`              | `(a b c)`           | `(a b c)`         |
| Vector `[...]`            | `[a b c]`           | `(Vector a b c)`  |
| Map `{k v ...}`           | `{:k1 v1 :k2 v2}`   | `(Map (k1 v1) (k2 v2))` (entries sorted by key) |
| Tagged literal `#inst`    | `#inst "2026-..."`  | `(Inst "2026-...")` |
| Integer                   | `42`                | `42`              |
| Real (no scientific form) | `3.14`              | `3.14`            |
| String                    | `"hello"`           | `"hello"`         |
| nil                       | `nil`               | `Nil`             |
| true / false              | `true` / `false`    | `True` / `False`  |

Rationale for each non-obvious choice:

- **Keyword `:foo` → MeTTa symbol `foo` (no prefix).** MeTTa
  has no keyword/symbol distinction at the syntax layer.
  Round-trip relies on the bijection knowing the EDN side
  produced a keyword for this position; we mark each kw-derived
  symbol via a side-channel `_kw_set` carried by `metta_to_edn`.
- **Logic var `?x` → `$x`.** MeTTa's variable sigil is `$`.
- **Vector `[a b c]` → `(Vector a b c)`.** REQ-EDN-051 already
  forbids erasing the list-vs-vector distinction; MeTTa has only
  parenthesised expressions, so we tag vectors with a reserved
  `Vector` head symbol. The `Vector` symbol is reserved; users
  cannot name a function `Vector` in EDN-sourced atoms (a lint
  catches this at scaffold time).
- **Map `{k v}` → `(Map (k v))`.** Similarly tagged. Entries
  sorted lexicographically by key so the surface form is
  deterministic regardless of EDN reader insertion order. This
  is what makes the round-trip byte-stable.
- **`#inst` and other reader tags → `(Inst "...")`.** Only
  the `#inst` tag is supported in v1; other reader tags raise
  `BijectionError`. This keeps the surface narrow.

## Round-trip stability

Byte-stability means: write EDN `x` → MeTTa `m = edn_to_metta(x)`
→ EDN `y = metta_to_edn(m)`; the EDN reader's canonical writer
output for `y` equals the canonical writer output for `x`. This
does NOT require source-string equality (EDN allows comment
whitespace etc.); it requires AST + canonical-write equality.

The `_edn_writer.py` is the single canonical writer (already
shipped by Tier 1). Round-trip tests are at
`skills/neurosym-forge/tests/test_edn_metta_round_trip.py`.

## Atomspace API

```python
class Atomspace:
    """Hash-cons-based atom store with structural deduplication."""

    def add(self, atom) -> Handle:
        """Insert `atom`; return canonical handle. If the
        structural sub-expression is already present, return the
        existing handle (no new allocation)."""

    def lookup(self, handle: Handle): ...

    def iter_atoms(self) -> Iterator[tuple[Handle, atom]]: ...

    def dedup_factor(self) -> float:
        """Ratio of unique handles to inserted atoms.
        Starts at 1.0; strictly decreases each time a duplicate
        sub-expression is inserted."""

    def count(self) -> int:
        """Number of unique handles (= len of internal table)."""
```

## Hash-cons via frozenset-keyed interning

Two implementation candidates:

- **(a) Symbol-table-keyed dict.** Each atom is stringified via
  the canonical EDN writer; the resulting string is the dict key.
  Pro: trivial, O(n log n) insertion via writer. Con: requires
  re-stringifying every sub-expression on every insertion;
  N-deep nested atoms cost O(N²) on insertion.
- **(b) Hash-cons via tuple-keyed dict.** Each atom is converted
  to a recursive tuple `(head, *child_handles)` where children
  are already canonical handles. The tuple is the dict key.
  Pro: O(N) on insertion (each sub-expression hashed exactly
  once); the handle is just the dict's small-int id. Con:
  slightly more code on the insertion path.

**Decision: (b).** The framework's atom files routinely contain
deeply nested expressions; the O(N²) writer-based approach is
visibly slow on the larger golden fixtures. Hash-cons is the
standard technique for atomspace-shaped storage.

```python
# Sketch
class Atomspace:
    def __init__(self):
        self._table: dict[tuple, Handle] = {}
        self._reverse: dict[Handle, atom] = {}
        self._next_id = 0
        self._insertions = 0

    def add(self, atom) -> Handle:
        self._insertions += 1
        key = self._canonical_key(atom)
        if key in self._table:
            return self._table[key]
        h = Handle(self._next_id)
        self._next_id += 1
        self._table[key] = h
        self._reverse[h] = atom
        return h

    def _canonical_key(self, atom):
        # leaf: ("Leaf", repr(atom))
        # list:  ("List", *[self.add(child) for child in atom])
        # vector:("Vector", *[self.add(child) for child in atom])
        # map:   ("Map", *sorted([(self.add(k), self.add(v)) for ...]))
        ...
```

## How dedup composes with embedding sidecar (forward ref)

The `tier5-embedding-sidecar` change consumes
`Atomspace.iter_atoms()` and indexes each handle with a vector.
Because handles are canonical (one per unique sub-expression),
the embedding cost is paid once per structural shape; later
re-insertion of an identical atom does not retrigger embedding.
This composition is asserted as a test in the sidecar change.

## Why not store EDN directly in hyperon's Atomspace?

The hyperon-experimental crate ships its own `space::*` API.
The framework intentionally keeps the Python-side `Atomspace`
separate, because:

- Phase O's MeTTa runtime is per-call (fresh `&self` space per
  constraint); there is no long-lived hyperon space the framework
  could read.
- The Python-side store is the indexing layer the embedding
  sidecar talks to, and it needs to outlive any single MeTTa
  call.
- The hyperon space is alpha; the Python store insulates the
  framework from that surface.

`Atomspace` is therefore a sibling structure, not a wrapper
around `hyperon::space::*`.

## Scaffolding

The new module ships at scaffold time alongside the existing
`_canonical.py`, `_edn_reader.py`, `_edn_writer.py`. The
scaffold's manifest adds the file; the existing
`scaffold_project.py` already iterates the manifest, so no
scaffold-script change is needed beyond manifest expansion.
