# Change: live-eval-gate

**Sprint:** V6 of the v0.6 "claim-first prose, live" mission (the capstone)
**Branch:** `plan/v0.6-live-integration` (roadmap); execution branch `feat/live-eval-gate`
**Capability:** `kg-prose-eval` (extend)
**Roadmap:** `docs/specs/2026-06-18-kg-prose-live-integration-roadmap-design.md`
**Depends on:** V1–V5 (it measures the fully integrated pipeline) and the landed S0 `kg-prose-eval` harness.

## Why

The S0 `kg-prose-eval` harness is built and tested, but it runs only on a frozen mini-task — never on a real book build. Every metric it computes is measured against a fixture, so none of v0.5's reasoning surface has ever been scored on a sentence of actually-drafted prose.

V6 runs S0 over an actual chapter build. It computes the live metrics — the decisive claim-first-vs-flat delta, sentence-level attribution precision/recall, internal FActScore, argument-closure %, contradiction catch-rate, proof-obligation discharge + gated-sentence-escape rate, and code-link precision/recall — and emits a build report. It is the capstone that turns S0 from a harness into a quality signal, and it produces the measurements the S9 speculative tranche graduates against: learned code↔claim ranking needs S6 link precision/recall on real chapters, richer argument semantics needs grounded-insufficiency proven on real chapters, and autoformalization needs S7 discharge rates.

## What

1. When a real chapter build completes, the S0 harness runs over its side products and prose, computing the six metric families on the live build.
2. The live eval emits a per-chapter and aggregated build report across attribution, factuality, reasoning, contradiction, rigor, and fusion.
3. A declared comparative metric (claim-first vs. flat) records both arms and reports the delta on the real build.
4. Where gold is absent for a live chapter, the dependent metric reports `unscored` (not a false zero) — the S0 honesty contract on the live path.
5. The live eval is advisory by default; a configurable metric subset becomes a release-gate signal once baselined.
6. The live eval reads the build's side products read-only and is deterministic given the build snapshot and stubbed model seams.

Ownership: book-knowledge and book-qa run the harness over the build; the eval is read-only over the build outputs.

## Scope

- This change ships the live eval over a real build, the build report, and the advisory/gating switch.
- It does **not** add the S0 harness or the metrics themselves — those landed in the S0 `kg-prose-eval` change and are reused unchanged.
- It does **not** perform S9 graduation — that is deferred until these measurements exist.
- The live model seams are stubbed in tests.

## Requirements

See `specs/kg-prose-eval/spec.md` (EARS). Summary:

| REQ id | Pattern | One-line |
|---|---|---|
| REQ-EVAL-008 | Event-driven | When a real chapter build completes, the S0 harness runs over its side products and prose, computing the six metric families on the live build |
| REQ-EVAL-009 | Ubiquitous | The live eval emits a per-chapter and aggregated build report across the six metric families |
| REQ-EVAL-010 | Optional | Where a comparative metric is declared (claim-first vs. flat), the live eval records both arms and reports the delta on the real build |
| REQ-EVAL-011 | State-driven | While gold is absent for a live chapter, the dependent metric reports `unscored` rather than a false zero |
| REQ-EVAL-012 | Ubiquitous | The live eval is advisory by default; a configurable metric subset becomes a release-gate signal once baselined |
| REQ-EVAL-013 | Ubiquitous | The live eval reads the build's side products read-only and is deterministic given the build snapshot and stubbed model seams |

## Out of scope

- The S0 harness and its metric definitions (landed in the S0 `kg-prose-eval` change — reuse).
- S9 graduation (learned code↔claim ranking, ASPIC+/preferred semantics, autoformalization) — deferred until these measurements exist.
- The live model seams (faithfulness/decomposer and any judge) — stubbed in tests.
- Any change to the v0.5 reasoning surface or to the V1–V5 wiring this change measures.
