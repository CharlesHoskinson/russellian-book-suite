# Tasks: kg-belief-erosion-completion

- [x] Add `effective-confidence` to `kg-schema.edn` and schema contract tests. (REQ-KG-028)
- [x] Add deterministic source freshness decay with explicit `as_of` input and unchanged default trust loading. (REQ-KG-032, REQ-KG-033)
- [x] Build the effective-confidence materializer over `propagate_belief.propagate`. (REQ-KG-028, REQ-KG-033)
- [x] Derive minimal support-erosion reasons from non-dismissed counter-claims and weakest weakened parent. (REQ-KG-029)
- [x] Route fresh trusted `conflicts_with` edges into the existing counter-claim damping path and name refreshed-source conflict reasons. (REQ-KG-030)
- [x] Add on-demand bounded why-provenance for flagged load-bearing claims only. (REQ-KG-031)
- [x] Mark oversized why-provenance witness sets truncated instead of expanding unboundedly. (REQ-KG-034)
- [x] Add S5 tests for every requirement and canonical correctness case. (REQ-KG-028, REQ-KG-029, REQ-KG-030, REQ-KG-031, REQ-KG-032, REQ-KG-033, REQ-KG-034)
