# Comprehensive end-to-end audit + remediation — design

**Date:** 2026-06-16
**Status:** approved (design)
**Baseline commit:** e0ae731 (main)
**Author:** audit working session

## Context

The suite has grown since the last whole-repo pass (`docs/audits/2026-05-29-suite-wide-end-to-end-review/`, ~350 KB across correctness/security/architecture/cicd, plus `2026-05-29-ci-system-audit/`). New since then: the `triadic-voice` skill, `tools/build-voice-corpus`, expanded verifier coverage, and a CI overhaul (PRs #224/#225 on 2026-06-16). A graphify knowledge graph now exists at `graphify-out/` (16,264 nodes, 22,391 edges, 1,394 communities) and is used to guarantee audit coverage.

This design covers a thorough end-to-end audit of the entire codebase and all features, followed by a remediation plan that also raises test coverage and hardens CI.

## Goals

1. Surface every Critical/Important defect across the whole repo with `file:line` precision and a concrete fix.
2. Guarantee coverage — no subsystem or graphify community left unaudited.
3. Reconcile against the 2026-05-29 audit: which findings were fixed, which remain, what is new.
4. Produce a prioritized remediation plan (OpenSpec change + sprint plan) plus a dedicated test-coverage + CI track.

## Non-goals

- Fixing anything during the audit phase (audit is **read-only**, per `docs/operations/codex-review-protocol.md`).
- Re-litigating items on the protocol's "What NOT to flag" list or already tracked in the 2026-05-29 audit (unless regressed).
- Style/house-prose opinions on the bermuda manuscript (intentional, per protocol).

## Approach

**Hybrid matrix (chosen).** Graphify-partition the repo into ~10 coherent subsystems; audit each across the review dimensions with a focused agent; then a cross-cutting pass, reconciliation against the prior audit, and adversarial verification of every Critical/High before it enters the report.

Alternatives considered: dimension-led (7 whole-repo agents — too shallow on big subsystems) and subsystem-led only (dimension rigor drifts, cross-cutting issues slip). The hybrid keeps per-subsystem depth and consistent dimension coverage.

## Audit dimensions

The seven dimensions from `docs/operations/codex-review-protocol.md`, plus three extensions the protocol under-covers:

| # | Dimension | Depth | Notes |
|---|---|---|---|
| D1 | Correctness | deep | append-only `claims/*.jsonl`, `latest_per`, state-machine DAG (`proposed→verified→disputed→{refuted,superseded}`), guarded `json.loads`, LLM-output shape validation |
| D2 | Security | deep | local-only (no `requests`/`urllib`/`httpx` in prod), `shell=True`, path traversal vs `workspace_root`, dependency CVEs, no `eval`/`pickle` of untrusted input |
| D3 | Tests | deep | untested paths (healer, state-machine recovery), positive-fire SPARQL tests, no live-LLM (inject `Callable[[str],str]`), assertion quality |
| D4 | Schema/data | medium | JSON Schema `additionalProperties:false`, ID patterns, SHACL `sh:in` ↔ enum, every `.rq` predicate projected by `project_graph.py` |
| D5 | Docs | medium | SKILL.md ↔ `scripts/`, runbook commands, recent spec ↔ shipped code, README accuracy |
| D6 | Architecture | light | skill ownership boundaries, sibling-skill imports, layering, import cycles |
| D7 | Performance | light | O(N²) ledger scans, unbounded loops, race conditions on append-only files |
| **D8** | **Verifier soundness (Rust/cljs)** | **deep (new)** | `unsafe`, panics/`unwrap` on external input, SMT/eqsat/kg correctness, EDN reader (`EdnVector`/`EdnList`/`Symbol` god nodes), napi boundary, cdylib panics across FFI |
| **D9** | **CI/build-infra** | **medium (new)** | reconcile PRs #224/#225 + the deferred items (env-indirection, compute_matrix empty-os guard, dynamic-import lint bypass, darwin flake gap, Clojure CVE cadence) |
| **D10** | **Test-coverage measurement** | **medium (new)** | real coverage % per subsystem, gap map, flakiness/network-in-test risks — feeds the remediation coverage track |

## Subsystem partition (graphify-anchored)

God nodes confirm the cores to prioritize: `frequencies`/`Keyword`/`abstract_inverted_index` (KG indexing), `WorkspaceLayout`/`init_workspace()`/`append_claim()` (workspace + ledger), `EdnVector`/`EdnList`/`Symbol` (EDN reader shared across verifiers).

1. **book-knowledge** — RDF/SPARQL/SHACL + claims ledger (core, deepest)
2. **composition** — book-compose, book-thesis, paragraph-weaver
3. **style/voice** — russellian-style, feynman-style, triadic-voice, halmos
4. **review/QA** — book-review, review-conductor, book-qa, iacr-review, iacr-math-prose
5. **neurosym-forge** — scaffolding + booklogic
6. **verifiers-Rust** — adsc-clinical, bermuda, epidemiology, osmotic_pressure crates
7. **verifiers-cljs/EDN** — orchestrators + `rules/booklogic/*.edn`
8. **tools** — build-voice-corpus, build-russell-corpus, readme-lint, synthesis/tagging one-shots
9. **CI/Nix/build** — workflows, `ci/`, `nix/`, Makefiles
10. **cross-cutting** — schema↔query↔SHACL consistency, docs↔code drift, `examples/bermuda-manual` integrity, the 7 import cycles + cross-community bridges graphify flagged

## Execution model

- Parallel `Agent` subagents (not the cloud Workflow tool), batched by subsystem. Each agent is handed: its file scope (`git ls-files`), the relevant dimensions, the protocol's "What NOT to flag" list, and the prior-audit summary so it does not re-litigate tracked items.
- Each returns a structured findings list: `[severity] file:line — problem — root cause — fix — confidence`.
- Synthesis: dedup → reconcile vs 2026-05-29 → **adversarially verify every Critical/High** with independent skeptic agents prompted to refute → drop unconfirmed.
- Coverage check: a final agent maps findings back to graphify communities and flags any high-centrality community with zero coverage for a follow-up sweep.

## Outputs

Audit (`docs/audits/2026-06-16-comprehensive-audit/`):
- `README.md` — executive summary, baseline (tests/ruff/commit), severity counts, go/no-go
- `findings-correctness.md`, `findings-security.md`, `findings-tests.md`, `findings-schema.md`, `findings-docs.md`, `findings-architecture.md`, `findings-verifiers.md`, `findings-cicd.md`
- `reconciliation.md` — prior-audit deltas (fixed / still-open / new)
- `coverage-map.md` — graphify community coverage + measured test-coverage gaps

Output format follows the protocol's Critical/Important/Minor with `[C-001]` style IDs and `file:line` anchors.

## Phase 2 — remediation plan (from verified findings)

1. **OpenSpec change** under `openspec/changes/<change>/` (proposal + spec deltas + REQ-IDs) for the substantive fixes, per AGENTS.md.
2. **Phased sprint plan** in `docs/superpowers/plans/2026-06-16-audit-remediation.md`, prioritized by severity × leverage, each task TDD-shaped (failing test → fix → green).
3. **Test-coverage + CI track** — per-subsystem coverage targets, the deferred CI items, the orphaned-cljs/verifier gaps, flakiness fixes.

## Constraints & conventions

- Audit phase: read-only, modifies no tracked file.
- All work via PR (never push to main directly); no AI attribution / Co-Authored-By; terse commits; one problem per PR.
- `git ls-files` is the authoritative file list; skip the AGENTS.md "out of scope" paths.

## Success criteria

- Every subsystem and every high-centrality graphify community has explicit coverage.
- Every Critical/High finding is adversarially verified and carries a concrete fix.
- Reconciliation clearly separates fixed / still-open / new vs the 2026-05-29 audit.
- The remediation plan is executable: ordered, TDD-shaped, with coverage and CI targets.
