# Change: tier2-multi-valued-predicates

**Tier:** 2 of 4 (general-purpose framework hardening)
**Branch:** `feat/tier2-multi-valued-predicates`
**Depends on:** none (independent of E.1 and E.2)

## Why

`defpredicate` today restricts the return-sort to a scalar: `:int`,
`:real`, `:bool`, `:string`, or one of the declared entity sorts.
That is sufficient for "the molarity of solution `?s`" or "the
density-g-l of `?s`" — one subject, one numeric value.

The framework's next class of constraint is *cross-chapter
consistency*: "the set of supporting chapters for claim `?c`",
"the list of declared species in ecosystem `?e`", or "the multiset
of edge weights in graph `?g`". Each of these is a multi-valued
observable. Today there is no surface syntax for declaring one;
authors work around it with auxiliary per-element predicates plus a
loop in the verifier — the encoding bloats the constraint count by
2-3× and obscures the original intent.

Motivating example, from the book-suite roadmap:

```edn
;; "Every claim in chapter ?c is supported by at least one chapter from
;;  the set of chapters that ?c declares as upstream."
(defpredicate :upstream-chapters [:chapter] [:set :chapter])
(defconstraint :upstream-non-empty
  :assert (forall ?c (> (count (:upstream-chapters ?c)) 0)))
```

The first form needs `[:set :chapter]` as a return sort; the second
needs the `count` aggregate to take a set.

## What

- Extend `defpredicate`'s return-sort grammar to accept
  `[:vector <sort>]` and `[:set <sort>]` in addition to the existing
  scalar sorts. Mixed-sort containers are not supported in this change.
- Extend the codegen `_emit_expr_typed` to lower a multi-valued
  predicate application to a Z3 Array (for `:vector`) or Z3 Set (for
  `:set`) symbol.
- Add four aggregate operators to the assert-form grammar:
  `(sum vec)`, `(count vec)`, `(in elem set)`, and
  `(forall ?x in vec/set body)`; each lowers to the corresponding
  Z3 form (`Real::add` over an array slice, `Set::contains`, etc.).
- Update `booklogic-schema.edn` (REQ-EDN-052) to encode the new
  return-sort shape in machine-readable form so the Python ingest
  validator (REQ-EDN-053) catches mis-typed bindings.

## Capabilities touched

- `booklogic-dsl` — MODIFY (extends `defpredicate` return-sort grammar
  + new aggregate operators in `defconstraint :assert`)

## Implementation notes

See `docs/plans/2026-05-18-tier234-and-usefulness.md`, Phase E.3.

## Acceptance

- A `defpredicate` with `:return [:set :chapter]` compiles, ingests,
  and is checkable in a `forall`-bounded constraint.
- A `defpredicate` declared multi-valued but bound to a scalar atom
  fails loudly at `smt::check_all` with a message naming the mismatch.
- The DSL reference § 2.2 enumerates the extended return-sort grammar
  and the four new aggregates.
