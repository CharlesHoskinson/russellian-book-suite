# Capability delta: hybrid-query — change: tier5-hybrid-query

## ADD

### REQ-QUERY-040 — Ubiquitous

The framework SHALL expose a grounded atom
`(hybrid-match $space $template $hint $k)` that returns atoms in
`$space` that (a) are among the top-`$k` nearest neighbours of `$hint`
per Phase Q's embedding sidecar AND (b) unify with `$template` per the
MeTTa Atomspace's native match. Result ordering SHALL preserve the
embedding-stage similarity ranking.

**Rationale:** The framework's promise of neuro-symbolic query only
materialises when the embedding sidecar and the MeTTa Atomspace
compose. Exposing the composition as a single grounded atom prevents
authors from accidentally reversing the stages.
**Tested by:** `skills/neurosym-forge/tests/test_hybrid_match.py::test_hybrid_match_returns_intersection` (added in R1.1).

### REQ-QUERY-041 — Ubiquitous

`(hybrid-match $space $template $hint $k)` SHALL run the embedding
neighbours-query FIRST and the symbolic match SECOND. The order is
load-bearing — vector top-k is the fast filter (high recall, cheap),
symbolic match is the slow filter (precise, expensive). The framework
SHALL NOT expose an option to reverse the order.

**Rationale:** Running symbolic match across the whole atomspace
defeats the purpose of the embedding stage; pinning the order in the
grounded atom enforces the "fast filter then slow filter" discipline
the analysis identified as the right pattern.
**Tested by:** `tests/test_hybrid_match.py::test_pipeline_order_neighbours_before_match` (added in R2.1).

### REQ-QUERY-042 — Optional feature

WHERE the embedding sidecar is unavailable (Phase Q's
`EmbeddingUnavailableError`), the framework SHALL fall back to a
pure-symbolic match across all of `$space` AND surface a stderr
warning prefixed `[hybrid-match] WARN:` naming the unavailable
sidecar.

**Rationale:** The embedding stage is an optimisation, not a soundness
gate; the symbolic stage alone produces a correct answer over a larger
candidate set. The structured warning lets log collectors detect
fallback events without making the call fatal.
**Tested by:** `tests/test_hybrid_match.py::test_sidecar_unavailable_falls_back_and_warns` (added in R2.2).

### REQ-QUERY-043 — Unwanted behaviour

IF no atoms among the embedding neighbours unify with `$template`, the
framework SHALL return an empty result, NOT raise an error. Empty is a
valid answer — the symbolic stage genuinely matched zero candidates.

**Rationale:** Distinguishing "no match" from "error" is the
difference between a meaningful empty answer and a spurious failure
mode that masks valid queries.
**Tested by:** `tests/test_hybrid_match.py::test_empty_intersection_returns_empty_not_error` (added in R2.3).

### REQ-QUERY-044 — Ubiquitous

A test suite SHALL exercise `(hybrid-match ...)` on a known-good
fixture of 10 atoms about "ages" with one atom matching the template
`($Person $age)` whose embedding-neighbour rank for the hint sentence
"how old is Alice" is top-1. The test SHALL assert the matching atom
appears in the top-1 result.

**Rationale:** A small, deterministic fixture pins the expected
end-to-end behaviour; running pure-symbolic match over the same
fixture would do 10x the work, making the fixture also a regression
test for the optimisation goal.
**Tested by:** `tests/test_hybrid_match.py::test_ages_fixture_top1_matches_alice` (added in R3.1).

### REQ-QUERY-045 — Optional feature

WHERE a query author wants to inspect the embedding-veto step's
intermediate result, the framework SHALL provide a grounded atom
`(neighbors-only $space $hint $k)` that returns the neighbour set
(as `(atom, similarity)` pairs, ordered by descending similarity)
without the symbolic-match stage.

**Rationale:** Debugging a hybrid query requires seeing what the
embedding stage produced before the symbolic stage culled it. A
separate grounded atom exposes the intermediate without complicating
the `(hybrid-match ...)` surface.
**Tested by:** `tests/test_hybrid_match.py::test_neighbors_only_returns_ordered_pairs` (added in R1.2).

### REQ-QUERY-046 — Ubiquitous

`docs/booklogic-dsl-reference.md` SHALL grow a "§7 Hybrid queries"
section covering both grounded atoms: `(hybrid-match ...)` and
`(neighbors-only ...)`, with one worked example each and a
when-to-use table distinguishing hybrid-match from pure match for
known-id lookups.

**Rationale:** Without doc coverage the grounded atoms are
discoverable only by reading source — the same documentation-debt
shape Tier 1 retired for the EDN forms.
**Tested by:** `tests/test_reference_docs.py::test_dsl_reference_has_section_seven_hybrid_queries` (added in R3.2).
