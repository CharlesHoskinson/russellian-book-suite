# Suite-wide end-to-end review — design

**Date:** 2026-05-29
**Status:** Approved (brainstorm), pending implementation plan
**Scope:** Whole repository — all 7 core skills, `neurosym-forge`, `tools/`, `ci/`, the `verifiers/` Rust+cljs layer, the CI/CD system, and the docs/audit conventions.

## Goal

Produce a trustworthy, committable audit of the entire suite across four lenses: correctness & bugs, CI/CD health, architecture & maintainability, and security & supply chain. The output is an audit bundle under `docs/audits/`, written to the same standard the suite imposes on its own prose, and cross-referenced against the eight still-open recommendations in `docs/audits/2026-05-21-suite-wide-linter-review.md`.

The review is **static analysis and reasoning over source and configuration**. Agents read, grep, and reason; they do not execute the CI pipeline or the full test suite, because the suite targets Ubuntu + Nix/WSL and this review runs on Windows. Where dynamic confirmation is required, a finding is marked **needs-runtime-verification** rather than asserted as passing or failing.

## Orchestration shape (Hybrid, "C")

Findings that are local to one component (bugs, internal coupling) are owned by **subsystem agents**, which have locality. Findings that are properties of the whole repository (CI correctness, supply-chain risk) are owned by **cross-cutting agents**, which have a repo-wide view. Every finding then passes an independent skeptic before it can enter the bundle. The adversarial-verify pass is the mechanism that makes the bundle committable: it exists to kill plausible-but-wrong findings.

## Agent roster

### Subsystem agents (lens: correctness + architecture)

One agent each:

- `book-knowledge` — claim ingestion, belief graph, conflict detection, ledger.
- `book-thesis` — argument-spine consistency, thesis-derived defects.
- `book-compose` — chapter orchestration, build/release pipeline, preflight, humanizer/persona passes.
- `russellian-style` — the seventeen prose linters and the three system-prompt voice modes.
- `book-review` — the seven-persona editorial panel.
- `review-conductor` — verdict aggregation.
- `book-qa` — the twenty-eight-check release gate.
- `neurosym-forge` — the Python verifier scaffolder plus the `.cljs` theory-induction scripts.
- `tools/` + `ci/` — `build-russell-corpus`, `russellian-style-audit`, `readme-lint`, and the `ci/` invariant linters (`lint_no_shadow_writes`, `no_direct_http`, import-linter).

### Domain-tuned language agents

Split out because the Rust and Clojure layers are a verifier core and a logic-translation layer, not generic code. There are two near-duplicate verifier instances (`verifiers/bermuda` and `verifiers/adsc-clinical`); divergence between them is itself a finding, so both language agents diff the two copies.

- **Rust verifier agent.** Tuned for: `unsafe`/panic/`unwrap` discipline and error handling; SMT/Z3 encoding soundness (`smt.rs`); equality-saturation correctness (`eqsat.rs` — rule application and termination); IR typing (`ir.rs`, `typeset.rs`, `var_name.rs`); the knowledge-graph layer (`kg.rs`); `build.rs` and Cargo pinning. Note at intake: `adsc-clinical` is missing `Cargo.lock` and `var_name.rs` relative to `bermuda`.
- **Clojure/cljs agent.** Tuned for: unification correctness (`unify.cljs` — occurs-check, substitution); NL→FOL translation soundness (`nl_to_fol.cljs`); booklogic DSL semantics (`booklogic.cljs`) and edn rule-set wellformedness (`sorts`/`predicates`/`constraints`/`lifts`/`rules`/`queries`/`remedies.edn`); theory induction (`induce_theory.cljs`); nbb/shadow-cljs idioms.

### Shared seam

The cljs↔Rust bridge/IR contract (`bridge.cljs` ↔ `ir.rs`/`lib.rs` serialization) is assigned explicitly so neither language agent half-covers it: the Clojure agent owns the cljs side, the Rust agent owns the Rust side, and synthesis reconciles the contract as one finding-set.

### Cross-cutting agents (run concurrently with subsystem agents)

- **CI/CD agent.** All five workflows (`ci.yml`, `ci-budget.yml`, `ci-legacy.yml`, `nightly-flake-drift.yml`, `onboarding-bench.yml`), the `setup-book-python` composite action, caching and cost, flake-drift handling, branch protection, and Nix/WSL reproducibility drift.
- **Security / supply-chain agent.** Dependabot config, GitHub Action SHA-pinning, secrets handling, dependency risk, and whether the repo's own invariants (`no_direct_http`, `no_shadow_writes`, import-linter) actually hold against the code.

## Pipeline

- **Phase 0 — Acquire & map (done inline before fan-out).** Clone the repo read-only; enumerate skills, `tools/`, `ci/`, `verifiers/`, workflows, and the custom action; tag files by language. Output is the concrete shard list the agents fan out over — the shape is discovered, not assumed.
- **Phase 1 — Deep review (parallel, pipelined).** Subsystem + language + cross-cutting agents emit structured findings: `{id, area, file, line, claim, severity, suggested_fix, confidence}`.
- **Phase 2 — Adversarial verify (pipelined off Phase 1).** Each finding is handed to an independent skeptic prompted to refute it against the actual code, defaulting to "not a real issue" when uncertain. Survivors carry a verdict plus evidence.
- **Phase 3 — Synthesize & write bundle.** Dedup across agents, severity-rank, reconcile the bridge seam, cross-reference the eight open recommendations, and write the bundle.

## Deliverable

A committable audit bundle at `docs/audits/2026-05-29-suite-wide-end-to-end-review/`:

- `README.md` — executive summary and a severity-ranked findings table (`severity | area | file:line | finding | fix | confidence | status`).
- Per-area findings files for the four lenses.
- A short section reconciling findings against the eight open recommendations (confirmed / superseded / newly raised).

Severity and confidence live in the findings table, not as parenthetical tags in the prose. The bundle is written as a single synthesized voice — no agent scaffolding is surfaced, and no epistemic-status labels appear in the prose.

## Boundaries / non-goals

- Does not run CI, the Nix shell, or the full test suite (Linux/Nix toolchain; review host is Windows). Runtime claims are flagged, not asserted.
- Does not modify suite code or fix findings; this review produces the audit only.
- Does not push to the remote or open PRs without explicit instruction.

## Success criteria

- Every committed finding survived an independent adversarial-verify pass with cited evidence (file:line).
- All four lenses and every roster shard are covered, with any intentionally dropped coverage logged explicitly.
- The bundle matches the existing `docs/audits/` format and is reconciled against the open-recommendations list.
