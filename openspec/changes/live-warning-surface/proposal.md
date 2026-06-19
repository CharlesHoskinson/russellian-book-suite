# Change: live-warning-surface

**Sprint:** V3 of the v0.6 "claim-first prose, live" mission
**Branch:** `plan/v0.6-live-integration` (roadmap); execution branch `feat/live-warning-surface`
**Capability:** `claim-first-drafting` (extend)
**Roadmap:** `docs/specs/2026-06-18-kg-prose-live-integration-roadmap-design.md`
**Depends on:** V1 `live-chapter-bundle-input` (the scaffold this change folds the surface into). Consumes the landed S3 argumentation, S4 contradiction-workbench, and S5 effective-confidence relations.

## Why

The S3 grounded-acceptability warnings, the S4 contradiction alerts, and the S5 effective-confidence signal are built and tested, but they are invisible to the writer: `run_argumentation`, `contradiction_workbench`, and `effective_confidence` are imported by zero live modules. The drafting scaffold V1 hands the writer never says that a load-bearing claim rests on a defeated argument, contradicts another claim, or has eroded support.

V3 folds those three surfaces into the V1 scaffold as caveats the drafting prompt must respect. The writer is warned when a load-bearing claim is contested or under undefended attack, when a claim sits on both sides of a contradiction, and when a claim's effective confidence has eroded below threshold — and the prompt instructs the matching prose response (defend, downgrade, do-not-assert-both, hedge-and-name-the-reason). This is deterministic: it consumes the landed S3/S4/S5 relations and adds no new analysis.

## What

1. The scaffold gains a warning surface drawn from S3 grounded-acceptability warnings (contested-load-bearing/undefended-attack, axiom-only, unsupported-load-bearing), S4 contradiction alerts, and S5 effective-confidence.
2. A contested-load-bearing claim's warning instructs the writer to defend or downgrade it.
3. A claim that appears in a contradiction alert is flagged so the writer does not assert both sides.
4. A claim whose effective-confidence is below the configured threshold instructs hedged phrasing naming the support-erosion reason.
5. The surface is deterministic over a ledger snapshot.
6. The surface respects the per-prompt budget — only load-bearing or in-scope warnings, honoring the known middle-chapter quality dip.

This is wiring, not new analysis: book-compose consumes the landed S3/S4/S5 relations via `sibling_skills` and the surface stays read-only over the ledger.

## Scope

- This change ships the warning surface folded into the V1 scaffold.
- It does **not** add the bundle scaffold itself (V1), the writer-assertion contract (V2), the proof gate (V4), code grounding (V5), or any new S3/S4/S5 analysis.
- It does not recompute argumentation acceptability, contradiction normalization, or effective confidence — it consumes the landed relations.

## Requirements

See `specs/claim-first-drafting/spec.md` (EARS). Summary:

| REQ id | Pattern | One-line |
|---|---|---|
| REQ-DRAFT-007 | Ubiquitous | The scaffold carries a warning surface drawn from S3 grounded warnings, S4 contradiction alerts, and S5 effective-confidence |
| REQ-DRAFT-008 | Event-driven | When a load-bearing claim carries a contested-load-bearing or undefended-attack warning, the prompt instructs defend-or-downgrade |
| REQ-DRAFT-009 | Event-driven | When a claim appears in a contradiction alert, the scaffold flags the conflict so the writer does not assert both sides |
| REQ-DRAFT-010 | Event-driven | When a claim's effective-confidence is below threshold, the prompt instructs hedged phrasing naming the support-erosion reason |
| REQ-DRAFT-011 | Ubiquitous | The warning surface is deterministic over a ledger snapshot and consumes the landed S3/S4/S5 relations without new analysis |
| REQ-DRAFT-012 | Ubiquitous | The warning surface respects the per-prompt budget, surfacing only load-bearing or in-scope warnings |

## Out of scope

- The bundle scaffold and its prompt construction (V1).
- The writer-assertion contract and sentence-level faithfulness checks (V2).
- The proof-obligation gate and `qa/gated-sentences.jsonl` (V4).
- Code↔claim grounding (V5) and live eval (V6).
- Any new S3 argumentation, S4 contradiction-workbench, or S5 effective-confidence analysis.
