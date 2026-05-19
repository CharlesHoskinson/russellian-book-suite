# Capability delta: candidate-generation — change: tier6-candidate-generation

This change introduces a new capability
`candidate-generation`, the inducer's generation stage. It
emits BookLogic candidate forms from THREE sources (Horn-
body mining, Popper-style typed search, LLM proposer)
behind a single uniform protocol; dedupes alpha-equivalent
candidates; ranks survivors by semantic coherence; persists
the queue for post-mortem. Validation is downstream
(Phase X for numeric fitting; later phases for full solver
validation).

## ADD

### REQ-INDUCE-050 — Ubiquitous

The framework SHALL ship
`skills/neurosym-forge/scripts/induce_theory.cljs` as the
main orchestrator for theory induction; nbb SHALL invoke
it as `nbb -m induce-theory <project-root>`.

**Rationale:** The inducer lives in ClojureScript via nbb
per the user-chosen architecture; nbb natively reads and
writes EDN and sits next to the existing `booklogic.cljs`
compiler. A single entry point per project keeps the
top-level CLI surface (Phase AA) trivially thin.
**Tested by:** `tests/test_induce_theory.py::test_orchestrator_entrypoint_runs_on_fixture_project` (added in W1.1).

### REQ-INDUCE-051 — Ubiquitous

The candidate generator SHALL produce candidates from THREE
sources in this order:
(a) Horn-body mining via Cozo Datalog queries enumerating
    frequent predicate-pair patterns;
(b) Popper-style typed search bounded to ≤4 literals per
    rule using mode declarations derived from
    `booklogic-schema.edn`;
(c) LLM proposer (Phase V) invoked once per Phase Q
    `SemanticIndex` cluster.
Each source SHALL emit at most N candidates (default N=20,
overridable via `NEUROSYM_INDUCTION_CANDIDATES_PER_SOURCE`).

**Rationale:** Each source has different blind spots; the
union covers the candidate space. Both deep-research reports
explicitly recommend all three. Per-source caps prevent any
one source from saturating the queue.
**Tested by:** `tests/test_induce_theory.py::test_each_source_emits_candidates_within_cap` (added in W2.1, W3.2, W4.2).

### REQ-INDUCE-052 — Ubiquitous

Candidates SHALL be deduplicated by canonical S-expression
form (via an extension to `_canonical.py`) BEFORE
validation. Alpha-equivalent rules SHALL collapse to one
candidate; the surviving candidate's `:origin` field SHALL
carry the set union of contributing source tags.

**Rationale:** Three sources producing the same candidate is
not redundancy to delete — it is corroboration to preserve.
The canonical-form key collapses syntactic noise; the
origin-set union records which sources agreed.
**Tested by:** `tests/test_induce_theory.py::test_alpha_equivalent_candidates_collapse_with_merged_origin` (added in W7.2).

### REQ-INDUCE-053 — Optional feature

WHERE Phase Q's `SemanticIndex` is available, candidates
SHALL be RANKED by semantic-coherence score (mean pairwise
cosine similarity over the cited atoms) DESCENDING, before
validation. When `SemanticIndex` is absent, the queue SHALL
remain in stable insertion order.

**Rationale:** Higher-coherence candidates are more likely
to validate; ranking puts them first so the validation
budget hits winners earliest. Graceful degradation when the
index is unavailable keeps the inducer runnable on bare
projects.
**Tested by:** `tests/test_induce_theory.py::test_semantic_ranking_orders_by_coherence_descending` and `::test_ranking_falls_back_to_stable_order_without_index` (added in W7.3).

### REQ-INDUCE-054 — Unwanted behaviour

IF the Cozo atomspace is empty or contains fewer than 10
atoms, the candidate generator SHALL skip the Horn-body
source AND emit a structured warning naming the corpus size,
THEN SHALL proceed with the Popper and LLM sources.

**Rationale:** Frequent-pair statistics are meaningless on
<10 atoms; running the Horn-body source on a tiny corpus
produces noise candidates that waste validation budget. The
threshold is conservative; Popper and LLM remain available
because both work on per-cluster slices that survive a small
overall corpus.
**Tested by:** `tests/test_induce_theory.py::test_horn_body_skipped_with_warning_on_small_corpus` (added in W2.3).

### REQ-INDUCE-055 — Ubiquitous

The candidate queue SHALL be persisted at
`work/induction/candidates.edn` for debugging and
post-mortem analysis; rejected candidates SHALL be retained
in the queue with their `:status` field set to `:rejected`
and a `:rejection-reason` field carrying a tag such as
`:grammar-fail/unknown-predicate`, `:duplicate`,
`:type-fail`, or `:budget-exceeded`.

**Rationale:** A rejected candidate's canonical form and
rejection reason are the framework's debugging surface — why
did the inducer drop this idea? Without persistence, the
generation stage is a black box.
**Tested by:** `tests/test_induce_theory.py::test_queue_persists_rejected_candidates_with_reason_tags` (added in W6.1).

### REQ-INDUCE-056 — Optional feature

WHERE `NEUROSYM_INDUCTION_BUDGET_USD` is set, the generator
SHALL track LLM cost using the cached cost-per-call from
Phase P's SQLite cache; when accumulated spend exceeds the
budget, the LLM source SHALL halt; Horn-body and Popper
sources SHALL continue unaffected. The final spend SHALL be
logged to `work/induction/budget.json`.

**Rationale:** Cost discipline at the source level. Halting
only the LLM source preserves the non-LLM sources' full
output even on a tight budget; the budget log is the audit
trail.
**Tested by:** `tests/test_induce_theory.py::test_budget_halts_llm_but_other_sources_complete` (added in W7.4).

### REQ-INDUCE-057 — Ubiquitous

A test suite SHALL exercise EACH source independently
(Horn-body fixture atomspace; Popper-typed search over
fixture schema; LLM source against the Stub provider) plus
the deduplication step and the semantic-ranking
integration.

**Rationale:** Three-source isolation tests catch source-
specific regressions; the dedup and ranking tests catch
cross-source interaction bugs. Without per-source isolation,
a failure in Popper masks as a queue-shape failure
downstream.
**Tested by:** `tests/test_induce_theory.py::{test_horn_body_source_in_isolation,test_popper_source_in_isolation,test_llm_source_against_stub,test_dedup_merges_origins,test_ranking_orders_by_coherence}` (added in W7.1, W7.2, W7.3).
