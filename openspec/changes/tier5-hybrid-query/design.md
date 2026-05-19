# Design: tier5-hybrid-query

## The composition pattern

The analysis described the right neuro-symbolic query pattern as
"embedding-veto + symbolic-veto":

```
                +---------------------------+
   $hint  --->  | (neighbors $hint $k)      |  ----> top-k atoms
                |  fast filter (cheap, ~ms) |        (high recall, some noise)
                +---------------------------+
                              |
                              v
                +---------------------------+
   $template -> | (match $space $template)  |  ----> bindings
                |  slow filter (precise)    |        (intersected with top-k)
                +---------------------------+
                              |
                              v
                       result set
```

The order is load-bearing. Running symbolic-match across the whole atomspace
first defeats the purpose: the embedding stage exists to cap the candidate
set before the expensive match runs. The framework enforces the order by
making `hybrid-match` a single grounded atom — the author cannot accidentally
swap the stages.

## Grounded atom surface

```
(hybrid-match $space $template $hint $k)
  -> seq of bindings (same shape as native MeTTa match)

(neighbors-only $space $hint $k)
  -> seq of (atom, similarity) pairs, ordered by similarity descending
```

`$space` is a MeTTa Atomspace handle (Phase O / Phase P). `$template` is a
MeTTa pattern with variables. `$hint` is the seed atom whose embedding
seeds the neighbours query. `$k` is the neighbour-set cap.

Result shape for `hybrid-match`: the intersection of the neighbour set and
the symbolic-match result. Ordering: by descending similarity (the
embedding-stage ranking is preserved through the intersection). An empty
result is a valid answer — distinct from an error.

`neighbors-only` exposes the intermediate (pre-symbolic-filter) result for
authors who want to debug the embedding stage or use top-k directly.

## Fallback when the sidecar is unavailable

Phase Q defines an `EmbeddingUnavailableError` raised when the sidecar
process is not reachable. `hybrid-match` catches that error and degrades:

1. Run `match($space, $template)` over the whole space.
2. Emit a one-line warning to stderr naming the unavailable sidecar:
   `[hybrid-match] WARN: embedding sidecar 'minilm-l6' unavailable; falling back to pure symbolic match`.
3. Return the symbolic-match result.

The warning is structured (prefixed `[hybrid-match] WARN:`) so log
collectors can grep it. The fallback is non-fatal because the symbolic
stage alone produces a correct (if larger) answer; the embedding stage
was an optimisation, not a soundness gate.

## When to use hybrid-match vs pure match

| Query shape | Use |
| --- | --- |
| Known-id lookup ("fetch atom :alice-age") | pure `(match ...)` — no `$hint` needed |
| "Find atoms similar to X and satisfying P" | `(hybrid-match ...)` |
| "What are the 10 nearest atoms to X?" | `(neighbors-only ...)` |
| "Top-k similar AND graph-reachable" | `(hybrid-match ...)` with a reachability template |

The framework does not auto-route: the author picks the grounded atom.
Auto-routing would obscure cost; the analysis specifically called out
that the two stages have different cost profiles and authors should see
that.

## Test fixture

The acceptance test uses a 10-atom "ages" fixture: nine red-herring
atoms about unrelated people plus one atom matching the template
`($Person $age)` where the embedding hint is a sentence about "how old
is Alice". The test asserts the Alice-age atom is in the top-1 result.
The fixture is small enough to run in <100 ms and large enough that
pure-symbolic match would do 10x the work of hybrid-match.

## Why a new capability

`booklogic-dsl` covers the EDN-level form families (`defconstraint`,
`defquery`, etc.). `hybrid-query` introduces grounded MeTTa atoms that
live inside the Phase O runtime — different surface, different consumer
(MeTTa interpreter, not the CLJS codegen). Splitting capabilities keeps
the booklogic-dsl spec from accumulating runtime-grounded-atom REQs
alongside its EDN-form REQs.
