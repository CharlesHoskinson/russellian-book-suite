# Change: kg-advanced-semantics

**Sprint:** S9 of the v0.5 KG-for-prose mission (speculative stub)
**Branch:** n/a (no execution branch until each item graduates to its own sprint)
**Capability:** spans several — no single new capability is claimed yet
**Roadmap:** `docs/specs/2026-06-17-kg-prose-enhancement-roadmap-design.md`
**Depends on:** S3 (`argumentation`, grounded acceptability), S6 (`homoiconic-kg` deterministic code↔claim links), S7 (`proof-obligations`). Each S9 item sits on top of a deterministic layer those sprints ship.

## Why

The brief's speculative tranche is small and explicitly gated: pursue these only after the deterministic layers beneath them are in place. Premature investment is a documented risk — treating learned link prediction as an unreviewed fact ingester, or autoformalization as a one-shot validator, both fail loudly. This stub records the three items, their dependencies, and their graduation criteria so they are tracked but not prematurely built. *Evidence C/B depending on the item.*

## What

1. **Learned code↔claim ranking.** Embeddings (TransE/RotatE) or a GNN link-prediction model with uncertainty calibration, used as a *second-stage candidate ranker* over the deterministic link-evidence from S6 — never an unreviewed fact ingester. The deterministic linker proposes; the model only reorders candidates within the reviewed set. *Depends on S6. Evidence B.*
2. **Richer argumentation semantics.** Preferred / stable / ASPIC+ semantics in a dedicated ASP solver (not plain Datalog) for deeper *offline* audits, layered over S3's grounded acceptability. Grounded semantics stay the online writer-warning surface; the ASP solver runs only as an offline audit pass. *Depends on S3. Evidence B.*
3. **Autoformalization loops for complex mathematical prose.** Tightly scoped NL→formal translation feeding S7's proof-obligation workflow, with explicit uncertainty labeling on every produced obligation. It is a proof-obligation *producer*, never a one-shot validator: discharge stays with S7's checkers. *Depends on S7. Evidence C.*

## Graduation criteria

Each item leaves this stub for its own sprint only when its gate is met:

1. **Learned ranking** graduates when S6's deterministic links have measured precision/recall and a ranking model is shown to improve recall *without* dropping precision below the S6 baseline.
2. **Richer semantics** graduates when grounded semantics (S3) prove insufficient for the writer-warning surface on real chapters.
3. **Autoformalization** graduates when S7's bounded SMT obligations and the hand-curated Lean subset have measured discharge rates and demonstrated author value — and then only as a proof-obligation producer, never a one-shot validator.

## Requirements (deferred)

No EARS spec delta accompanies this change. Requirements are authored when each item graduates to its own sprint, against the codebase state at that sprint's kickoff. Candidate REQ slugs each item would use:

| Item | Candidate slug | Disposition |
|---|---|---|
| Learned code↔claim ranking | `KG` (extends `homoiconic-kg`, REQ-KG-0n…) | Extends S6's `link-evidence` relation with a ranked candidate stage |
| Richer argumentation semantics | `ARG` extension, or a new offline-audit slug | Adds preferred/stable/ASPIC+ over S3's grounded surface |
| Autoformalization loops | `PROOF` (extends `proof-obligations`) | Adds an NL→formal obligation producer ahead of S7's checker dispatch |

## Out of scope

- Any implementation. This change declares the three items and their graduation gates; it ships no code.
- Any EARS requirements. Spec deltas are deferred until each item graduates to its own sprint (see *Requirements (deferred)*).
- Promoting any item to the production path. Learned ranking stays a candidate reorderer behind the deterministic S6 linker; ASP semantics stay offline-audit-only behind S3's grounded surface; autoformalization stays a producer behind S7's checkers.
