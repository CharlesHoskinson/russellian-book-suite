# KG-for-prose enhancement roadmap (v0.5) — Design

**Date:** 2026-06-17
**Author:** Charles
**Status:** Draft, pending user approval
**Builds on:** `openspec/changes/archive/2026-06-17-homoiconic-kg-edn-front-cozo-back/` (the EDN-front/Cozo-back foundation, landed today). This roadmap is the "P2–P5 follow-on specs" that change deferred, plus new capabilities.
**Informed by:** `docs/research/2026-06-16-homoiconic-edn-kg-prose-brief.md` (the research brief; the source PDF lives outside the repo).

## Problem

The suite now has one homoiconic knowledge graph (EDN front, Cozo back, code ↔ claim ↔ thesis joinable). The ledger stores claims, source-spans, confidence, status, and the argument edges (`supports`, `conflicts-with`, `counter-claim`, `load-bearing`, `derived-from`). `propagate_belief.py` already runs a Bayesian erosion pass. `consistency_cozo` already runs symbolic contradiction checks.

What the graph does **not** yet do is *reach the prose*. The writer (`book-compose`) receives flat claim lists, not claim-first structured bundles. Generated sentences are ephemeral — nothing binds a sentence to the claim and span it asserts, and nothing checks that the sentence is faithful to its cited span. The argument edges are stored but never evaluated for acceptability, so the writer is never warned that a load-bearing claim rests on a defeated argument. Contradiction detection is lexical (antonym pairs), with no unit/quantity/temporal normalization. Mathematically and scientifically delicate claims rely on prose-level confidence, not on discharged proof obligations, even though Z3 already ships in the suite.

The research brief surveys the state of the art (GraphRAG, ALCE/FActScore/RARR/LongCite/CiteEval, Dung/ASPIC+, provenance semirings, temporal/unit-aware verification, Lean/Z3, CODEXGRAPH) and proposes seven enhancements plus a substrate verdict. A gap analysis against the codebase (see §"Current state") shows the enhancements range from ~95% done (belief erosion) to greenfield (argumentation, proof obligations).

## Goal

Define the **v0.5 "claim-first prose" mission** as ten OpenSpec changes (S0–S9), sequenced by evidence strength and dependency, that turn the existing graph into a writer-facing reasoning surface. This roadmap doc fixes the sprint sequence, capability decomposition, REQ-slug allocation, and the cross-cutting evaluation strategy. Each sprint then ships its own `proposal.md` + EARS spec delta; `design.md` and `tasks.md` are authored at each sprint's kickoff (when codebase state is known), not up front.

## Non-goals

- No implementation in this pass. This roadmap produces requirements (proposals + EARS spec deltas), not code.
- No rewrite of the landed `homoiconic-kg` change or `propagate_belief.py`. S5 *completes* the erosion work; it does not replace it.
- No substrate migration. The brief's verdict — keep Cozo, harden the seam — is adopted (S8). Asami/DataScript appear only as a reference evaluator, never as the production store.
- No collision with the neurosym-forge `tierN-*` verifier roadmap. That track is about *induced BookLogic theories* and *verifier verdicts*; this track is about the *claim ledger* and the *prose writer*. Shared vocabulary ("confidence", "provenance", "revision") is deliberately cross-referenced in §"Relationship to existing roadmaps" to prevent concept drift.

## Current state (gap analysis summary)

| Brief move | Already in repo | Genuine gap | State |
|---|---|---|---|
| #1 Claim-first chapter planner | chapter-contracts, `thesis-node`, `community`, `chapter_evidence_coverage.edn`, `query_chapter_evidence.py` | the `chapter-retrieval-bundle` projector | ~40% |
| #2 Writer-assertion + sentence citation | claim↔span binding, confidence, status machine | `writer-assertion` entity, sentence→span NLI check, atomic-fact decomposition, RARR loop | ~50% |
| #3 Grounded argumentation | raw `conflicts-with`/`counter-claim`/`load-bearing` edges, `rebuttal-presence.edn` | Dung rules: `attacked`/`defended`/`undefeated-attacker`/`grounded-accepted` + warnings | ~5% |
| #4 Belief-erosion propagation | `propagate_belief.py` (full Bayesian engine), p-prior/p-posterior | `effective-confidence` relation, `erosion-reason` justification sets, why-provenance, freshness decay | ~95% |
| #5 Contradiction workbench | `detect_conflicts.py`, `consistency_cozo`, `contradiction_scan.edn`, `stale_after_source_refresh.edn` | quantity/unit/time-interval normalization, NLI residue seam | ~70% |
| #6 Proof obligations | `neurosym-forge`, `halmos`, Z3, `export_symbolic_trace.py` (all standalone) | `proof-obligation` entity, checker dispatch, gating math/science prose | ~0% |
| #7 Code↔claim autolink | `code-claim-link` entity exists (schema), graphify P4 fusion | deterministic file-path + exact-symbol linker, `link-evidence` relation | ~30% |
| Substrate | `Backend` protocol, `StubBackend`, golden compile fixtures, contract tests | dual-run Cozo-vs-reference equality harness, canonical ordering | ~80% |

**Correction to the brief's own roadmap:** the brief sequences belief-erosion as a mid-tranche build, but `propagate_belief.py` already implements it. S5 is therefore a *completion* sprint (materialize the relation, add justification + provenance), not a build-from-scratch.

## Approach

### Sprint sequence

```
S0  kg-prose-eval-harness        NEW  kg-prose-eval        foundational (characterization-first)
S1  kg-chapter-retrieval-bundles NEW  chapter-retrieval    brief #1   evidence A
S2  kg-writer-assertion-contract NEW  attributed-generation brief #2  evidence A
S3  kg-argumentation-layer       NEW  argumentation        brief #3   evidence B   (dep: S2)
S4  kg-contradiction-workbench   EXT  homoiconic-kg        brief #5   evidence A/B (dep: S2)
S5  kg-belief-erosion-completion EXT  homoiconic-kg        brief #4   evidence B   (dep: S3,S4)
S6  kg-code-claim-autolink       EXT  homoiconic-kg        brief #7   evidence B
S7  kg-proof-obligations         NEW  proof-obligations    brief #6   evidence B   (dep: S4)
S8  kg-substrate-hardening       EXT  homoiconic-kg        substrate  evidence B
S9  kg-advanced-semantics        —    (stub)               speculative evidence C/B (dep: S3,S6,S7)
```

Rationale for the order: S0 first because "characterization first, goldens second" is the repo's stated discipline (REQ-KG-005) and nothing downstream is measurable without the frozen benchmark. S1+S2 are the brief's tranche-1 evidence-A wins and are pure projector/prompt-contract work with no substrate change. S3+S4 are the warning-surface tranche and both attach to the S2 writer-assertion. S5 completes erosion once contradictions (S4) and argument warnings (S3) feed it. S6 runs in parallel (depends only on graphify ingestion). S7 needs S4's normalized claims. S8 hardens the seam once the rule surface from S3–S7 is stable. S9 is the speculative stub.

### Capability decomposition

Five new capabilities plus extensions to the landed `homoiconic-kg`:

| Capability | Slug | Owner skill(s) | Sprints |
|---|---|---|---|
| `kg-prose-eval` (new) | `EVAL` | book-knowledge + book-qa | S0 (+ every sprint contributes goldens) |
| `chapter-retrieval` (new) | `CHAP` | book-knowledge → book-compose | S1 |
| `attributed-generation` (new) | `ATTR` | book-compose + book-qa + book-knowledge | S2 |
| `argumentation` (new) | `ARG` | book-knowledge | S3 |
| `proof-obligations` (new) | `PROOF` | book-knowledge + neurosym-forge + halmos | S7 |
| `homoiconic-kg` (extend) | `KG` | book-knowledge | S4, S5, S6, S8 (REQ-KG-021+) |

Per OpenSpec workflow, new capabilities have no steady-state `openspec/specs/<capability>/spec.md` until their first change archives; this roadmap writes only the change-local deltas under `changes/<change>/specs/<capability>/spec.md`. `homoiconic-kg` extensions continue its existing REQ-KG numbering from REQ-KG-021 (the homoiconic-kg cutover's P0–P5 phases reached REQ-KG-020).

### REQ-slug allocation

Added to the table in `openspec/README.md`:

| Slug | Capability |
|---|---|
| `EVAL` | kg-prose-eval |
| `CHAP` | chapter-retrieval |
| `ATTR` | attributed-generation |
| `ARG` | argumentation |
| `PROOF` | proof-obligations |

`homoiconic-kg` keeps slug `KG`; S4/S5/S6/S8 append REQ-KG-021… in sprint order without renumbering existing IDs (S4=021–027, S5=028–034, S6=035–040, S8=041–046).

### EARS conventions

Unchanged from `openspec/README.md`: five patterns (Ubiquitous, Event-driven `When`, State-driven `While`, Optional `Where`, Unwanted `If`), each REQ heading carries its pattern label, each requirement leads with subject + SHALL, and every requirement pins at least one `#### Scenario:` with `WHEN/THEN/AND` bullets naming the test that proves it.

## Per-sprint briefs

**S0 — `kg-prose-eval-harness` (`kg-prose-eval`, EVAL).** A frozen benchmark of chapter-writing tasks whose inputs are ledger snapshots and whose outputs are graph-structured side products (selected claims, cited spans, contradiction alerts, proof traces), not only text. Metrics: sentence-level citation precision/recall vs. human-verified spans, partial-support rate, internal FActScore (atomic facts backed by verified / disputed / no claim), argument-acceptability warning precision/recall, contradiction catch-rate (symbolic) + recall (residual) + false-positive rate, proof-obligation discharge rate and gated-sentence-escape rate, code-link precision/recall. Result-set equality wherever determinism allows. *Evidence A.* REQ-EVAL-001…00n.

**S1 — `kg-chapter-retrieval-bundles` (`chapter-retrieval`, CHAP).** A projector materializing a `chapter-retrieval-bundle` per chapter from `chapter`/`claim-chapter`/`thesis-node`/`community`/`code-claim-link`/`claim`: dominant communities, top load-bearing claims, unresolved rebuttals, and the minimal source-span anchor set. Delivered to the writer as EDN/JSON, never a flat passage pile, with a prompt scaffold ("state thesis, present supports in order, caveat the disputed counter-claim"). *Evidence A (GraphRAG local/global).* REQ-CHAP-001…00n.

**S2 — `kg-writer-assertion-contract` (`attributed-generation`, ATTR).** A first-class `writer-assertion` entity (`sentence-text`, `asserts-claim`, `cites-span`, `citation-check-status`, `revision-origin`); every generated sentence binds to ≥1 `claim.id` + ≥1 `source-span.id`. A post-generation sentence→span faithfulness check (small NLI / citation model behind a seam) with a deterministic policy: on failure, revise from the cited span (RARR) or downgrade to a hedged, non-canonical form. Plus atomic-fact decomposition (FActScore) producing `draft-atomic-fact` mapped to an existing claim or a `novel-draft-claim` that blocks publication until ingested or removed. *Evidence A ("Attribute First, then Generate"; FActScore).* REQ-ATTR-001…00n.

**S3 — `kg-argumentation-layer` (`argumentation`, ARG).** EDN/Datalog rules deriving `attacked`, `defended`, `undefeated-attacker`, `grounded-accepted`, `grounded-rejected` over `supports`/`conflicts-with`/`counter-claim`/`sub-argument`/`load-bearing`, plus warnings (e.g. `contested-load-bearing-with-undefended-attack`). Grounded semantics only at first (deterministic, explainable); preferred/stable deferred to S9. *Evidence B (Dung; ASPIC+/ASP).* REQ-ARG-001…00n.

**S4 — `kg-contradiction-workbench` (extends `homoiconic-kg`, KG).** Normalized helper relations `claim-quantity`, `claim-unit`, `claim-time-interval`, `claim-normal-form`; symbolic rules for exact contradictions, interval inconsistencies, quantity clashes after unit conversion, and stale supersession chains. Only paraphrastic residue routes to an external NLI seam. *Evidence A symbolic / B residue.* REQ-KG-021…027.

**S5 — `kg-belief-erosion-completion` (extends `homoiconic-kg`, KG).** Materialize `effective-confidence` as a Cozo relation derived from `p-prior`/`p-posterior`/`supports`/`derived-from`/`conflicts-with`/source trust/freshness; emit `support-erosion-reason` from minimal justification sets; add bounded why-provenance on-demand for `load-bearing` claims only; add source-freshness decay. Completes `propagate_belief.py`. *Evidence B (provenance semirings).* REQ-KG-028…034.

**S6 — `kg-code-claim-autolink` (extends `homoiconic-kg`, KG).** Replace the wholly-explicit `code-claim-link` with a derived relation whose evidence is stored in a new `link-evidence` relation (`kind`, `score`, `witness`, `provenance`). Stage one is deterministic only: `source.file` matches a module path, a mention resolves to a `code-node` symbol, or a cited symbol has a CONTAINS/USES edge. Learned ranking is S9. *Evidence B (CODEXGRAPH; De-Hallucinator).* REQ-KG-035…040.

**S7 — `kg-proof-obligations` (`proof-obligations`, PROOF).** A `proof-obligation` entity (`statement`, `linked-claim`, `checker-kind` ∈ {z3, cvc5, lean, units, stats-report}, `status`, `assumptions`, `artifact-path`, `countermodel-path`, `checked-at`, `normal-form`) plus a `verification-artifact` record and `requires-proof` relation. The halmos / math-science writer passes consume only claims whose obligations are discharged or explicitly waived. A `scientific-claim-check` seam validates units, uncertainty qualifiers, and statistical-reporting norms. *Evidence B (Lean kernel; Z3 proof objects; EQUATOR/PRISMA).* REQ-PROOF-001…00n.

**S8 — `kg-substrate-hardening` (extends `homoiconic-kg`, KG).** A conformance harness behind `cozo_store`: frozen EDN query fixtures, dual-run result-set equality between Cozo and a small reference backend (DataScript-class, authoring-time only), canonical ordering checks, and a documented switch-trigger list. Buys swap optionality without a migration. *Evidence B.* REQ-KG-041…046.

**S9 — `kg-advanced-semantics` (speculative stub).** Learned code↔claim ranking (TransE/RotatE/GNN link-prediction as a *candidate ranker*, never an unreviewed fact ingester); richer ASPIC+/preferred/stable argumentation semantics in an ASP solver for offline audits; autoformalization loops for complex math prose, scoped tightly with explicit uncertainty. Proposal-only stub; each item graduates to its own sprint when the deterministic layer beneath it is proven. *Evidence C/B.*

## Dependency graph

```
S0 ──► (enables measurement of all)
S1 ──────────────► S9
S2 ──► S3 ──► S5
   └──► S4 ──► S5
        └────► S7 ──► S9
S6 ──────────────► S9
S3,S4,S5,S6,S7 ──► S8 (harden once rule surface stable)
```

S1, S2, and S6 have no upstream sprint dependency (only the current claim/source-span/code-graph state). S5 is the join point for the warning sprints. S8 follows the rule-producing sprints. S9 follows the deterministic layers it ranks/extends.

## Evaluation strategy (cross-cutting)

S0 stands up the harness; every later sprint contributes goldens to it rather than inventing its own measurement. The philosophy mirrors the existing `homoiconic-kg` discipline: characterization fixtures before a behavior lands, result-set equality where determinism allows, and graph-structured side products measured alongside prose. The decisive experiment named in the brief — *claim-first graph bundles vs. flat passage bundles on the suite's own chapter-writing tasks* — is the S1 acceptance benchmark, not an abstract "GraphRAG vs RAG" claim.

## Relationship to existing roadmaps

- **neurosym-forge `tierN-*` (verifier track).** Distinct subject. `tier5-confidence-propagation` propagates confidence through *verifier verdicts* (defects); S5 here propagates belief through the *claim ledger*. `tier6-agm-revision` revises *induced BookLogic theories*; this roadmap never induces rules. `tier6-provenance-sidecar` is PROV-O over *induced rules*; S5's why-provenance is over *claim derivations*. Where a future reader might conflate them, the sprint proposals cross-link explicitly.
- **`homoiconic-kg` (landed today).** This roadmap is its follow-on. S4/S5/S6/S8 extend its capability spec; S1/S2/S3/S7 add new capabilities that join through the same Cozo seam and EDN compiler. No sprint reaches the backend except through `cozo_store` (REQ-KG-002/002b stays invariant).

## Versioning and milestones

The track ships as the **v0.5** mission. Each sprint maps to one GitHub Milestone and one squash-merged PR, mirroring the v0.4 cadence in `docs/specs/2026-05-17-ears-openspec-roadmap-design.md`. A `v0.5.0` Release publishes after S8 (S9 is post-1.0 exploratory).

## Open questions

1. **NLI/citation model choice (S2, S4 residue).** Which small, offline, freezable model backs the sentence→span and paraphrastic-contradiction checks? Must satisfy byte-deterministic offline build. Candidate selection is an S2 design-time decision.
2. **Argumentation semantics ceiling (S3 vs S9).** Is grounded acceptability sufficient for the writer-warning surface, or do load-bearing chains need preferred/stable often enough to justify the ASP solver sooner than S9?
3. **Reference backend for S8.** DataScript (JS/CLJS, in-memory) vs. a pure-Python EDN Datalog evaluator. The brief favors DataScript as the EDN-congenial north star; a Python evaluator avoids a JVM/JS runtime in CI.
4. **Proof-obligation gating strictness (S7).** Hard-block undischarged math/science claims, or allow an explicit `conjectural` prose mode? Interacts with `BLOCKING_DEFEASIBLE`.
5. **Eval gold provenance (S0).** Human-verified spans require an annotation pass; how large a gold set is enough to make precision/recall meaningful without overfitting the benchmark?

## Risks (from the brief)

- **Graph-structure payoff is not guaranteed.** Recent GraphRAG evaluations are sober. Mitigation: the S0 benchmark measures claim-first vs. flat bundles on real tasks before committing to S1's bundle shape.
- **Sentence→span entailment is brittle under aggressive paraphrase.** Mitigation: narrow, local citation contracts and an explicit `partial-support` state (S2), not binary pass/fail.
- **Provenance cost explosion.** Why-provenance for recursive Datalog can be intractable. Mitigation: S5 computes it on-demand only for `load-bearing` claims.
- **Wrong backend switch.** Mitigation: S8 ships a shadow reference backend for a rule subset, not a production migration; switch triggers are explicit.
- **Premature autoformalization.** Mitigation: S7 starts with bounded SMT obligations + a small hand-curated Lean subset; autoformalization stays in the S9 stub.
