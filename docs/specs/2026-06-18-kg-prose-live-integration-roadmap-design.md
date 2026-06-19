# v0.6 — "claim-first prose, live" integration roadmap — Design

**Date:** 2026-06-18
**Author:** Charles
**Status:** Draft, pending user approval
**Builds on:** the completed v0.5 KG-for-prose mission (S0–S8, all merged; `docs/specs/2026-06-17-kg-prose-enhancement-roadmap-design.md`). This roadmap consumes that surface; it adds no new reasoning capability.

## Problem

v0.5 built, audited, and merged the full knowledge-graph reasoning surface — chapter-retrieval bundles (S1), the writer-assertion contract (S2), grounded argumentation warnings (S3), the normalized contradiction workbench (S4), effective-confidence erosion (S5), deterministic code↔claim links (S6), and proof-obligation gating (S7), all measurable by the S0 eval harness. Every piece is correct and tested.

**None of it is wired into the live book build.** `skills/book-compose/scripts/build_book.py` orchestrates the real release (preflight → assemble → render → manifest) and imports none of the v0.5 surfaces. The S1 bundle serializer (`chapter_bundle.py`) and the S2 contract (`writer_assertion.py`) have no live caller anywhere in `book-compose/scripts`; `halmos/proof_gate.py`, `effective_confidence`, `run_argumentation`, and `contradiction_workbench` are imported by zero live modules. The drafting path still selects a flat list of verified claims (`query_chapter_evidence.py`) and never sees a bundle, a warning, a confidence signal, or a proof gate.

The v0.5 machinery is dormant. Until the live drafting loop calls it, none of the reasoning reaches a single sentence of prose, and the S0 benchmark has nothing real to measure.

## Goal

Define the **v0.6 "claim-first prose, live" mission** as six OpenSpec changes (V1–V6) that wire the dormant v0.5 surface into the live `book-compose` drafting loop and measure the result with S0. Each sprint ships its own `proposal.md` + EARS spec delta; `design.md`/`tasks.md` are authored at each sprint's kickoff. The terminal artifact is a book build in which every drafted sentence is bundle-scaffolded, assertion-bound, faithfulness-checked, warning-aware, proof-gated where required, and scored by S0.

## Non-goals

- No new KG reasoning capability — v0.6 *consumes* what v0.5 built; it does not extend the graph's analytic power.
- No S9 graduation. Learned code↔claim ranking, ASPIC+/preferred semantics, and autoformalization all gate on measurements that only V6 can produce (S6 link precision/recall on real chapters, grounded-insufficiency on real chapters, S7 discharge rates). S9 graduates in a later v0.7 once V6's numbers exist.
- No substrate change. Cozo stays the single production store (REQ-KG-002), hardened by S8.
- No rewrite of the v0.5 modules — they are correct; v0.6 calls them from the live path and adds only the thin producer/consumer wiring and the bundle-enrichment sections.

## Current state (integration gap)

| v0.5 surface | Built + tested | Wired into the live book build |
|---|---|---|
| S1 chapter-retrieval bundle | ✅ | ✗ (no live caller of `chapter_bundle.py`) |
| S2 writer-assertion contract | ✅ | ✗ (no live caller of `writer_assertion.py`) |
| S3 grounded argumentation warnings | ✅ | ✗ (`run_argumentation` imported by 0 live modules) |
| S4 contradiction alerts | ✅ | ✗ (`contradiction_workbench` imported by 0 live modules) |
| S5 effective-confidence | ✅ | ✗ (`effective_confidence` imported by 0 live modules) |
| S6 code↔claim links | ✅ | ✗ (not surfaced to the writer) |
| S7 proof-obligation gate | ✅ | ✗ (`halmos/proof_gate.py` has no live caller; nothing emits `qa/gated-sentences.jsonl`) |
| S0 eval harness | ✅ | ✗ (runs on a frozen mini-task, never on a real build) |

## Approach

### Sprint sequence

```
V1  live-chapter-bundle-input      NEW  claim-first-drafting    bundle drives the drafting loop
V2  live-writer-assertion          EXT  attributed-generation   contract on every real sentence   (dep: V1)
V3  live-warning-surface           EXT  claim-first-drafting     S3/S4/S5 warnings in the scaffold  (dep: V1)
V4  live-proof-gate                 EXT  proof-obligations        gated-sentences emitted + gated    (dep: V2)
V5  live-code-grounding             EXT  claim-first-drafting     S6 links surfaced for software     (dep: V1)
V6  live-eval-gate                  EXT  kg-prose-eval            S0 over a real build; advisory→gate (dep: V1–V5)
```

Rationale: V1 is foundational — once the drafting loop consumes the bundle, V2/V3/V5 each attach a surface to it and can proceed in parallel. V4 needs V2 (the assertion contract is what tells the gate which sentence asserts which claim as verified). V6 is the capstone — it measures the fully integrated pipeline and turns S0 from a harness into a quality signal, producing the numbers that later unblock S9.

### Capability decomposition

One new capability plus three extensions:

| Capability | Slug | Owner skill(s) | Sprints |
|---|---|---|---|
| `claim-first-drafting` (new) | `DRAFT` | book-compose (+ book-knowledge bundle reads) | V1, V3, V5 |
| `attributed-generation` (extend) | `ATTR` | book-compose + book-qa | V2 |
| `proof-obligations` (extend) | `PROOF` | book-compose/halmos + book-qa | V4 |
| `kg-prose-eval` (extend) | `EVAL` | book-knowledge + book-qa | V6 |

`claim-first-drafting` is the live drafting loop driven by the KG: it gets its own steady-state spec on V1's archive. The three extensions continue their existing REQ sequences.

### REQ-slug allocation

Add to `openspec/README.md`: `DRAFT` → `claim-first-drafting`. Continuations (no renumbering of existing IDs):

| Sprint | Capability | REQ block |
|---|---|---|
| V1 | claim-first-drafting (new) | REQ-DRAFT-001…006 |
| V3 | claim-first-drafting | REQ-DRAFT-007…012 |
| V5 | claim-first-drafting | REQ-DRAFT-013…018 |
| V2 | attributed-generation | REQ-ATTR-009…014 |
| V4 | proof-obligations | REQ-PROOF-010…015 |
| V6 | kg-prose-eval | REQ-EVAL-008…013 |

### EARS conventions

Unchanged from `openspec/README.md`: five patterns with per-REQ labels, subject-leading SHALL/SHALL NOT, and a `#### Scenario:` per requirement naming the test that proves it. The integration sprints' scenarios assert behavior on the *live drafting path*, not on isolated library calls.

## Per-sprint briefs

**V1 — `live-chapter-bundle-input` (`claim-first-drafting`, DRAFT-001…006).** The chapter-draft step consumes the S1 `chapter-retrieval-bundle` (dominant communities, top load-bearing claims, open rebuttals, minimal span anchors) as the writer scaffold, replacing the flat `query_chapter_evidence` claim list. The drafting prompt is built from the bundle's prompt scaffold. Ownership: book-compose calls the book-knowledge projector via `sibling_skills`; the bundle stays read-only over the ledger. The decisive S0 measurement (claim-first vs. flat) becomes runnable on a real chapter.

**V2 — `live-writer-assertion` (`attributed-generation`, ATTR-009…014).** Every sentence the live drafting loop emits is recorded as a `writer-assertion` bound to its claim + span, run through the sentence→span faithfulness check, and resolved by the revise-or-downgrade policy; atomic-fact decomposition and the novel-draft-claim publication block run on real paragraphs. The faithfulness/decomposer model is the injectable seam S2 already defined (still offline/freezable). Ownership: book-compose records assertions under `chapters/drafts/`; novel-draft-claims route through `qa/proposed-transitions.jsonl`. *Dep: V1.*

**V3 — `live-warning-surface` (`claim-first-drafting`, DRAFT-007…012).** The chapter scaffold gains a warning surface: S3 grounded-acceptability warnings (contested-load-bearing, axiom-only, unsupported-load-bearing), S4 contradiction alerts, and S5 effective-confidence are folded into the bundle as caveats the drafting prompt must respect (e.g. "hedge this claim; its support eroded", "do not assert; load-bearing claim has an undefended attacker"). Deterministic; no new analysis — it consumes the landed S3/S4/S5 relations. *Dep: V1.*

**V4 — `live-proof-gate` (`proof-obligations`, PROOF-010…015).** The math/science writer pass (halmos) emits `qa/gated-sentences.jsonl` recording each rendered sentence, the claim it asserts, and that claim's obligation status; the S7 book-qa `gated-sentence-escape` gate then fires on real builds, hard-failing an undischarged-unwaived verified assertion. Closes the S7 producer gap. Ownership: halmos/book-compose emit only `qa/`; book-qa owns the gate; book-knowledge owns obligations. *Dep: V2.*

**V5 — `live-code-grounding` (`claim-first-drafting`, DRAFT-013…018).** For software chapters, the scaffold surfaces S6 canonical `code-claim-link` rows so the writer grounds software descriptions in the code graph (cutting invented-API risk). Only canonical (deterministic, unambiguous) links are surfaced; ambiguous candidates stay evidence-only and invisible to the writer. *Dep: V1.*

**V6 — `live-eval-gate` (`kg-prose-eval`, EVAL-008…013).** The S0 harness runs over a real chapter build, computing the live metrics — claim-first-vs-flat delta, sentence-level attribution precision/recall, internal FActScore, argument-closure %, contradiction catch-rate, proof-obligation discharge + gated-sentence-escape rate, code-link precision/recall — and emits a build report. Advisory first; a configurable subset becomes a release-gate signal once baselined. Produces the measurements S9 graduation depends on. *Dep: V1–V5.*

## Dependency graph

```
V1 ──► V2 ──► V4
   ├──► V3        ─┐
   └──► V5        ─┤
V2,V3,V5 ─────────►V6  (capstone: measures the integrated pipeline)
```

V1 is the only unblocked start. V2/V3/V5 parallelize off V1. V4 follows V2. V6 is the capstone over all five.

## Relationship to v0.5 and S9

v0.6 adds no analytic power — it makes v0.5's analytic power reach the prose. The S0 harness (v0.5) becomes a live signal (V6). And v0.6 is the precondition for the S9 speculative tranche: each S9 item's graduation criterion is a *measurement on real chapters* that only V6 produces. The roadmap therefore sequences integration before graduation deliberately — building a learned ranker (S9.1) or an ASP audit (S9.2) before the deterministic layer is measured live would be the exact premature-investment the S9 stub warns against.

## Versioning and milestones

The track ships as the **v0.6** mission: one GitHub Milestone + one squash-merged PR per sprint, mirroring v0.5. A `v0.6.0` Release publishes after V6, when a real book build is end-to-end claim-first and S0-scored.

## Open questions

1. **Drafting-loop seam (V1).** Where exactly does the bundle replace `query_chapter_evidence` — at the chapter-contract build, the per-chapter draft prompt, or both? A V1 design-time decision against the current `book-compose` draft flow.
2. **Warning → prose policy (V3).** How forcefully does a warning bind the writer — a hard "omit", a required hedge, or a prompt caveat? Interacts with the S2 revise/downgrade policy and the `BLOCKING_DEFEASIBLE` default.
3. **Middle-chapter quality dip.** The known 4–8/10 quality dip (one-fresh-agent-per-chapter, ≤500-word prompts) constrains how much bundle/warning context a single drafting prompt can carry. V1/V3 must respect the prompt budget.
4. **Eval gold at build scale (V6).** The S0 gold (human-verified spans, warning labels) was a mini-task; live measurement needs gold for a real chapter. How much, and authored when?
5. **Advisory→gating threshold (V6).** Which S0 metrics become release-gating, at what thresholds, and after how many baselined builds?

## Risks

- **Prompt overload.** Folding bundle + warnings + code links + proof status into one drafting prompt can degrade generation (the middle-chapter dip). Mitigation: V1/V3 budget the scaffold; surface only load-bearing context; measure with V6.
- **Over-gating stalls the build.** A too-eager warning/proof gate could block every chapter. Mitigation: V3/V4 default to advisory + explicit hedge/conjectural modes (per S2/S7), hard-fail only the narrow gated-sentence-escape; V6 thresholds are baselined before gating.
- **Measuring the wrong thing.** A live eval whose gold is thin or mis-specified produces misleading deltas. Mitigation: V6 reports `unscored` rather than false zeros (the S0 discipline) and reuses S0's honest-metric contract.
- **Integration churn in book-compose.** Wiring six surfaces into the draft loop touches the most quality-sensitive code. Mitigation: each sprint is one surface, behind the existing skill boundaries, with the S1–S7 contracts already audited.
