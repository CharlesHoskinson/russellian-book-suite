# atomspace-edn

REQ-BOOKLOGIC-040. Wire format of every atom kind. The atom IR is the
serialisation contract between the Python ingester, the nbb-compiled
BookLogic intermediates, and the Rust verifier.

## 1. Overview

Atoms are EDN maps. Every atom carries `:id` and `:kind` and one of a small
set of kind-specific field sets. Atoms travel through the pipeline as
ordered vectors inside `{:version 1 :atoms [...]}` containers and are
written/read via `skills/neurosym-forge/scripts/_edn_writer.py` and
`_edn_reader.py`.

The file boundaries that carry atom containers are:

- `work/claims.edn` — the Python ingester's output, consumed by Rust
- `rules/grounded.edn` — author-supplied grounded fixtures (when present)
- `work/verdict.edn` — the Rust verifier's reply

The intermediate `rules/predicates.edn` and friends, emitted by
`nbb -m <slug>.booklogic .`, are NOT atom-shaped — they are pure
defpredicate / defconstraint / etc. data and live alongside the atom
stream rather than inside it.

## 2. Atom kinds

There are three kinds in v1:

- `:expression` — the workhorse. Encodes a grounded predicate
  application `(predicate subject value)` plus claim provenance.
- `:symbol` — a marker atom. Two named symbols are reserved:
  `:OPAQUE` (no lift pattern matched) and `:CONTEXT` (a chapter-level
  design decision, not a fact).
- `:rule` — reserved. Tier 3 will promote rules into the atom stream
  for egg consumption. Not emitted today.

Atom kind is checked by `verifiers/<project>/rust-verifier/src/ir.rs`
and dispatched by `smt.rs`.

## 3. Expression atom — golden example

A grounded fact, e.g. "claim osm-clean-002 says the molarity of solution
S is 0.154":

```edn
{:kind :expression
 :id "osm-clean-002"
 :predicate :molarity
 :subject :S
 :value 0.154
 :sort :formula
 :context false
 :doc "Molarity M = 0.154"
 :source-spans [{:doc-id "vant-hoff-textbook"
                 :locator-text "isotonic saline 0.154 mol/L"}]
 :supports-chapters []
 :confidence 1.0}
```

Field reference:

- `:id` — claim id from the upstream ledger. Used by `assert_and_track`
  as the Z3 tracker so unsat cores name the offending claim.
- `:kind` — `:expression` for this shape.
- `:predicate` — MUST be `Edn::Key` (Keyword) post-Tier 1
  (REQ-EDN-049). The legacy `Edn::Str` form is no longer accepted by
  `smt.rs`.
- `:subject` — MUST also be `Edn::Key`. Conventionally `:S` (or
  `:sol`, `:bermuda`, `:specimen` — anything the deflift `:emit`
  binds; see `references/grounded-atoms.md`).
- `:value` — the grounded value. `Edn::Double` for `:real`-typed
  predicates, `Edn::Int` for `:int`-typed, `Edn::Bool` for `:bool`,
  `Edn::Str` for `:string`. `_emit_float` (REQ-EDN-050) keeps a
  decimal point on every Double so a value like `2.0` does not
  silently round-trip as `Edn::Int` 2 and bind to the wrong Z3 sort.
- `:sort` — `:formula` for atoms produced by the ingester.
- `:context` — `false` for expression atoms (true only for `:CONTEXT`
  symbols).
- `:doc` — the canonical claim text, truncated to 200 chars.
- `:source-spans` — list of `{:doc-id ... :locator-text ...}` maps,
  passed through from the upstream ledger.
- `:supports-chapters` — list of chapter ids the claim supports.
- `:confidence` — Double in `[0.0, 1.0]`, passed through from the
  ledger.

## 4. OPAQUE atom

Emitted when no `deflift` pattern matches the claim's canonical text.
The claim still lands in the atom stream but the verifier ignores it.
Phase A's `make extract` gate fails the build if too many OPAQUE
atoms appear (default threshold: opaque-fraction < 0.5).

```edn
{:kind :symbol
 :id "osm-clean-005"
 :name :OPAQUE
 :sort :formula
 :doc "Some text the lifts did not recognise."
 :source-spans [...]
 :supports-chapters []
 :confidence 0.0}
```

Notes:

- `:confidence 0.0` is conventional, signalling "the ingester did not
  understand this claim".
- `:context` is absent (compare with `:CONTEXT` which sets it `true`).
- The OPAQUE name is reserved; downstream tools (`extract` gate,
  `lint_atomspace`) match on it as a literal Keyword.

## 5. CONTEXT atom

Emitted when the upstream claim has `claim_type: "design_decision"`. The
verifier treats this as a deliberate marker, not a fact:

```edn
{:kind :symbol
 :id "ch3-decision-007"
 :name :CONTEXT
 :sort :formula
 :context true
 :doc "We model osmosis at constant temperature."
 :source-spans [...]
 :supports-chapters ["ch3"]
 :confidence 1.0}
```

Semantically: "this is a chapter-level decision, not a fact". The
verifier neither asserts nor refutes it. The CONTEXT atom is what lets
`make ci` skip authorial preamble while still keeping it in the
verifiable record for audit.

## 6. Field-type asymmetries (Edn::Key vs Edn::Str)

Two fields are strict Keywords post-Tier 1 (REQ-EDN-049):

- `:predicate` MUST be `Edn::Key`. Pre-Tier 1 the Rust verifier
  accepted strings; that path is gone. Phase C's EdnVector / EdnList
  schema in `booklogic-schema.edn` enforces it.
- `:subject` MUST also be `Edn::Key`. The lift compiler emits a
  Keyword from `:s` (or `:sol`, etc.) in `phases.cljs` and the
  ingester preserves it.

Other fields stay flexible:

- `:id`, `:doc`, `:locator-text` — `Edn::Str`
- `:value` — discriminated by predicate sort (see § 7)

Pretest: if `smt.rs` returns `:sat` on the doctored fixture, the most
common cause is a `:predicate` arriving as `Edn::Str` and silently
failing the dispatch.

## 7. Double vs Int discrimination

Z3 distinguishes `Real` and `Int` sorts strictly. A predicate declared
`[:solution] :real` must bind to `Edn::Double`. A predicate declared
`[:solution] :int` must bind to `Edn::Int`.

`_emit_float` (REQ-EDN-050, in `scripts/_edn_writer.py`) emits every
Python `float` with at least one decimal place:

```python
# REQ-EDN-050: always emit a decimal point so 2.0 stays an Edn::Double
# and never silently collapses to Edn::Int.
def _emit_float(f: float) -> str:
    return repr(f)
```

The sprint-5 regression that motivated this rule: predicate
`:vant-hoff-i` (declared `:real`) received an `Edn::Int` 2 from a
malformed writer, which Z3 silently treated as a free Int constant.
The axiom unified two Real free constants because the value never
bound, and the doctored fixture flipped from `:unsat` to `:sat`.

## 8. The `:version` field

Containers carry `{:version 1 ...}` at the top. Bumping the version is
how we signal a breaking change to the atom shape — for example,
introducing the `:rule` kind, or renaming a reserved Keyword. The
Rust verifier reads `:version` and refuses to proceed on an unknown
value.

Current version: `1`.

## 9. Container shapes by file

The same `:version 1` envelope wraps several distinct container
shapes. Match the file to the right shape:

| File | Container shape |
| --- | --- |
| `work/claims.edn` | `{:version 1 :atoms [...]}` — atom stream |
| `work/verdict.edn` | `{:status :sat\|:unsat\|:unknown :core [...] :explanation "..." :graph-summary {...}}` |
| `rules/predicates.edn` | `{:version 1 :predicates {<name> <spec>}}` — predicate map |
| `rules/constraints.edn` | `{:version 1 :constraints [<defconstraint maps>]}` |
| `rules/booklogic-schema.edn` | Phase C: `{:version 1 :ednvector {...} :ednlist {...}}` |

Only `work/claims.edn` and `rules/grounded.edn` carry the atom-shape
`:atoms` vector. Confusing the two is the most common authoring
mistake; the schema validator (Phase C) catches it cleanly.

## See also

- `references/grounded-atoms.md` — how expression atoms get their
  values (the deflift pass).
- `references/phase-boundaries.md` — where in the pipeline atoms are
  written and read.
- `verifiers/osmotic_pressure/rust-verifier/src/ir.rs` — the Rust-side
  atom decoder.
- `skills/neurosym-forge/scripts/_edn_writer.py` — the canonical
  EDN emitter; `_emit_float` lives here.
