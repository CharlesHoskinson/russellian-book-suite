# Comprehensive Audit + Remediation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run a thorough, read-only, graphify-guided end-to-end audit of the whole repo, produce a verified findings report, then a prioritized remediation plan that also raises test coverage and hardens CI.

**Architecture:** Hybrid matrix — ~10 graphify-partitioned subsystems audited across the 7 `codex-review-protocol` dimensions + 3 extensions (verifier soundness, CI-infra, coverage). Parallel `Agent` subagents, then dedup → reconcile vs the 2026-05-29 audit → adversarial verification of every Critical/High → consolidated reports. Phase 2 turns verified findings into an OpenSpec change + sprint plan.

**Tech Stack:** `Agent` subagents (general-purpose + Explore), graphify (`explain`/`path` + `GRAPH_REPORT.md`), pytest/ruff for baseline, OpenSpec for remediation.

**Design spec:** `docs/superpowers/specs/2026-06-16-comprehensive-audit-design.md`
**Audit outputs:** `docs/audits/2026-06-16-comprehensive-audit/`
**Constraints:** audit is read-only (modifies no tracked file); all work via PR; no AI attribution.

---

### Task 1: Pre-flight baseline

**Files:**
- Create: `docs/audits/2026-06-16-comprehensive-audit/baseline.md`

- [ ] **Step 1:** Record `git rev-parse HEAD`, the date, and `git ls-files` counts per subsystem.
- [ ] **Step 2:** Run ruff: `python -m ruff check .` — capture verbatim (clean or N violations).
- [ ] **Step 3:** Run the three primary suites per `codex-review-protocol` pre-flight (`book-knowledge`, `book-qa`, `book-compose`) + `ci/` + `tools/build-voice-corpus`; record pass counts. A failing suite is finding #0.
- [ ] **Step 4:** Extract the prior-audit top items from `docs/audits/2026-05-29-suite-wide-end-to-end-review/` into a short "already-tracked" list to hand every agent.
- [ ] **Step 5:** Write `baseline.md` with the above. (No commit yet — audit dir is committed once at Task 7.)

**Expected:** baseline.md records commit, ruff result, suite pass counts, and the already-tracked list.

---

### Task 2: Audit batch A — Python skill subsystems (1–5)

**Files:**
- Working notes only (agent outputs collected in-session); no tracked file yet.

- [ ] **Step 1:** Dispatch 5 parallel `general-purpose` agents, one per subsystem: (1) book-knowledge [RDF/SPARQL/SHACL + claims ledger], (2) composition [book-compose/thesis/paragraph-weaver], (3) style/voice [russellian/feynman/triadic/halmos], (4) review-QA [book-review/review-conductor/book-qa/iacr-*], (5) neurosym-forge.
- [ ] **Step 2:** Each agent prompt includes: file scope via `git ls-files skills/<skill>`, dimensions D1–D7, the protocol's "What NOT to flag" list, the already-tracked list, and the structured return schema `[severity] file:line — problem — root cause — fix — confidence (read code, no speculation)`.
- [ ] **Step 3:** Each agent runs the subsystem's own pytest suite and reports pass/fail + any untested-path gaps (D3/D10).
- [ ] **Step 4:** Collect all five findings lists.

**Expected:** five structured findings lists, each anchored to `file:line`, with the subsystem's test result.

---

### Task 3: Audit batch B — verifiers, tools, CI (6–9)

- [ ] **Step 1:** Dispatch 4 parallel agents: (6) verifiers-Rust [4 crates — D8: `unsafe`, `unwrap`/panic on external input, SMT/eqsat/kg soundness, napi/cdylib FFI], (7) verifiers-cljs/EDN [orchestrators + `rules/booklogic/*.edn`, the `EdnReader` god-node cluster], (8) tools [build-voice-corpus, build-russell-corpus, readme-lint, synthesis/tagging], (9) CI/Nix/build [reconcile PRs #224/#225 + the deferred items from `russellian-book-suite-ci` memory].
- [ ] **Step 2:** Rust/cljs agents note they cannot run cargo/nix locally; static analysis + CI signal only.
- [ ] **Step 3:** Collect all four findings lists.

**Expected:** four structured findings lists covering the non-Python subsystems.

---

### Task 4: Cross-cutting + graphify coverage (10)

- [ ] **Step 1:** Dispatch 1 agent for cross-cutting: schema↔`.rq`↔SHACL consistency (every predicate in `assets/queries/*.rq` projected by `project_graph.py`), docs↔code drift, `examples/bermuda-manual` integrity, and the 7 import cycles + cross-community bridges from `graphify-out/GRAPH_REPORT.md`.
- [ ] **Step 2:** Dispatch 1 coverage agent: map all collected findings back to graphify communities; list any high-centrality community (degree-ranked in `GRAPH_REPORT.md`) with zero findings coverage as a gap to sweep.
- [ ] **Step 3:** If the coverage agent flags an uncovered high-centrality community, dispatch a targeted follow-up agent for it.

**Expected:** cross-cutting findings + a coverage map showing every high-centrality community has been looked at.

---

### Task 5: Synthesis — dedup + reconcile

- [ ] **Step 1:** Merge all findings; dedup by `file:line` + problem.
- [ ] **Step 2:** Reconcile vs `docs/audits/2026-05-29-suite-wide-end-to-end-review/`: tag each finding fixed / still-open / new. Drop anything on the "What NOT to flag" list or already tracked-and-unchanged.
- [ ] **Step 3:** Produce one merged, severity-sorted list (Critical/Important/Minor) with `[C-/I-/M-]` IDs.

**Expected:** a single deduped, reconciled findings list.

---

### Task 6: Adversarial verification of Critical/High

- [ ] **Step 1:** For each Critical/Important finding, dispatch an independent skeptic agent prompted to REFUTE it (read the actual code; default to "refuted" if uncertain).
- [ ] **Step 2:** Drop or downgrade findings the skeptic refutes; keep only confirmed ones with the verification note.

**Expected:** every surviving Critical/Important is adversarially confirmed.

---

### Task 7: Assemble findings reports

**Files:**
- Create: `docs/audits/2026-06-16-comprehensive-audit/README.md` (exec summary, baseline, severity counts, go/no-go)
- Create: `findings-correctness.md`, `findings-security.md`, `findings-tests.md`, `findings-schema.md`, `findings-docs.md`, `findings-architecture.md`, `findings-verifiers.md`, `findings-cicd.md`
- Create: `reconciliation.md`, `coverage-map.md`

- [ ] **Step 1:** Write each findings file in the protocol's Critical/Important/Minor format with `file:line` anchors and concrete fixes.
- [ ] **Step 2:** Write `README.md` exec summary with severity counts and a releasable-state verdict.
- [ ] **Step 3:** Commit the audit dir on the audit branch.

```bash
git add docs/audits/2026-06-16-comprehensive-audit/
git commit -m "docs: comprehensive end-to-end audit findings"
```

**Expected:** complete, committed findings reports.

---

### Task 8: Remediation plan (from verified findings)

**Files:**
- Create: `openspec/changes/audit-remediation-2026-06/proposal.md` (+ `tasks.md`, spec deltas with REQ-IDs)
- Create: `docs/superpowers/plans/2026-06-16-audit-remediation.md` (TDD sprint plan)

- [ ] **Step 1:** Group verified findings into themed work items; assign severity × leverage priority.
- [ ] **Step 2:** Write the OpenSpec change proposal + spec deltas per AGENTS.md conventions.
- [ ] **Step 3:** Write the remediation plan as bite-sized TDD tasks (failing test → fix → green → commit), one per work item, with a dedicated **test-coverage + CI track** (per-subsystem coverage targets, deferred CI items, orphaned-cljs/verifier gaps).
- [ ] **Step 4:** Commit; open the PR with the audit + plans.

**Expected:** an executable remediation plan grounded in real, verified findings, plus a coverage/CI track.
