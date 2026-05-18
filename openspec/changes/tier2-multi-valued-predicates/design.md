# Design: tier2-multi-valued-predicates

## REQ-ID range note

The Tier 2 instructions called for REQ-DSL-040..045, but
`booklogic-pr4-active-forms` already declares `REQ-DSL-040 — Event-driven`
in its booklogic-dsl spec delta. To keep REQ-IDs globally unique, this
change folder uses **REQ-DSL-050..055**. The shift is a clerical
collision avoidance; the requirement *contents* match the original
spec.

## Return-sort grammar

Today, `:return` is a single Keyword referencing a sort. Tomorrow:

```
return-sort ::= <sort-keyword>            ; scalar (unchanged)
              | [:vector <sort-keyword>]  ; ordered, index-addressable
              | [:set    <sort-keyword>]  ; unordered, set-membership
```

`<sort-keyword>` must be a base sort or a previously declared sort.
Nested containers (`[:vector [:set :chapter]]`) are **not** supported in
this change; the grammar is one container layer deep.

## Z3 lowering

| BookLogic return-sort | Z3 sort                            | Aggregate ops supported                 |
|-----------------------|------------------------------------|------------------------------------------|
| `[:vector :real]`     | `Array<Int, Real>` + length symbol | `(sum v)`, `(count v)`, `(forall ?x in v ...)` |
| `[:vector :int]`      | `Array<Int, Int>`  + length symbol | `(sum v)`, `(count v)`, `(forall ?x in v ...)` |
| `[:vector :string]`   | `Array<Int, String>` + length      | `(count v)`, `(forall ?x in v ...)`      |
| `[:set <sort>]`       | `Set<<sort>>` (Z3 set theory)      | `(in elem s)`, `(forall ?x in s ...)`    |

Vectors are encoded as Z3 Arrays with a paired `length` symbol so
`(count v)` is constant-time at the SMT level (`Int::new_const("v_len")`).
Sets use Z3's standard set theory (`z3::Set<T>`); `(in elem s)`
lowers to `s.member(&elem)`. The `(forall ?x in coll ...)` form lowers
to `Bool::and` over a bounded unroll for vectors and to a quantified
`forall` over the set sort for sets.

## Why Z3 Array, not Z3 Sequence?

Z3 has both `Array` and `Seq` (sequence) sorts. `Seq` matches the
"ordered collection" intuition more closely but z3-rs 0.20 does not
expose first-class wrappers for `Seq` operations — every call ends up
going through the C API. `Array<Int, T>` plus a paired `length` symbol
covers the same expressive surface with z3-rs's typed Rust API and
unlocks the same aggregate operators with fewer FFI seams.

Z3 Sequence becomes worth revisiting when z3-rs exposes a typed `Seq`
binding; we open an issue against z3-rs and ship Array in the
meantime.

## Why fail-loud on scalar-bound-to-vector?

REQ-EDN-053 already rejects unknown predicates from the ingester
based on the schema. Today, an atom emitting `{:value 42}` for a
predicate declared `[:set :chapter]` would bind a single `Int`
constant to the predicate's variable name; the constraint trying to
use `(count ?coll)` on it would either crash inside z3-rs's typed
wrapper or — worse — silently succeed against an empty set. The
strict binding check raises an error from `smt::check_all`'s value
dispatch (line ~127 in osmotic's `smt.rs`) with a message naming the
declared sort and the actual value shape.

## Schema-file extension

`booklogic-schema.edn` already enumerates `{:arg-sorts ... :return ...}`
per predicate. The schema is extended so `:return` can be the new
vector/set shape:

```edn
{:upstream-chapters {:arg-sorts [:chapter] :return [:set :chapter]}
 :upstream-weights  {:arg-sorts [:chapter] :return [:vector :real]}}
```

Python ingest reads the new shape; CLJS emits it from
`expand-predicates`; Rust reads it for sort validation.

## Why not relax to arbitrary container nesting?

`[:vector [:set :chapter]]` is expressible in Z3 (`Array<Int, Set<Chapter>>`)
but the aggregate operators get ambiguous: does `(count vv)` count
the inner sets or the union? One-container-deep covers the motivating
use cases (set of supporting chapters, list of species, vector of
edge weights) and keeps the surface syntax + lowering rules
specifiable in one design doc.
