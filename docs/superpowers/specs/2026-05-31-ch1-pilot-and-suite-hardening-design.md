# Chapter 1 Pipeline Pilot + Suite Hardening — Design

Date: 2026-05-31. Status: approved (direction + key decisions).

## Goal

Run "Intelligence Is Not Civilization" (ch1 of *Agentic Civilizations*) through the
real book-suite pipeline end to end, fixing the empty-ledger root cause for its
claims and leaving a repeatable template for ch2–15. Every suite bug we hit while
doing this gets fixed in the canonical repo under test and review, not worked
around. Add a standing review + QA layer to the process.

## Two tracks

### Content track (the pilot)
Run ch1 through, each stage gated:
1. **Contract** — author `chapters/contracts/ch-01.yaml` (purpose, ~6 claims, must_include, evidence_requirements, `prose_mode: narrative-editorial`, acceptance_tests). Template for later chapters.
2. **Promote claims** (book-knowledge) — locate spans in sources 017, 073, 002 for ch1's load-bearing claims; `verify_claim` source-span confirmation; proposed→verified. ~6 claims, not the whole book. This fixes the empty ledger that forced the original bypass.
3. **Entailment** (book-thesis) — `dispatch_entailment` per ch1 paragraph against thesis nodes; record verdicts.
4. **Style calibration** (russellian-style) — full 12-linter set + `score_russell_delta` + `retrieve_corpus_anchor`; bring delta from 0.819 inside the band (<0.786) by matching real Russell paragraph-motion; keep staccato/burstiness at 0.
5. **Contract-check** (book-compose) — `chapter_contract_check` against the contract's acceptance tests (hedge/passive/listicle/rhythm/citation/`ai_fingerprint==0`).
6. **Persona review** (review-conductor) — panel on ch1 (≥ Gottlieb, Domain Expert, AI-Slop Detector); soft-gate on criticals.
7. **book-qa** — `lint_artifact` D1–D8.

Decision: keep the v1.5 prose and run it through the gates; do not regenerate via
compose drafting (that path produced the original sludge). Compose validates and
calibrates; it does not rewrite from scratch.

### Suite-hardening track (TDD on the suite)
When a stage hits a real tool bug:
1. Reproduce with a **failing test** in the skill's `tests/`.
2. Fix the code in `C:\russellian-book-suite`.
3. **Gate:** that skill's `pytest` goes green and stays green.
4. **Review:** code-review the diff — lightweight by default (review note + ledger entry); escalate to an independent `code-reviewer` subagent for non-trivial fixes.
5. **Log** in the bug ledger.

## Bug #0: copy divergence (do first)

Runtime resolves siblings at `~/.agents/skills/`; the tested repo is
`C:\russellian-book-suite`. Decision: **unify on the canonical repo** — replace the
6 stale real-dir copies in `~/.agents/skills` (book-knowledge, book-thesis,
book-compose, book-qa, book-review, russellian-style) with symlinks/junctions to
`C:\russellian-book-suite\skills`. Diff each first; flag any meaningful divergence
before linking. The other suite skills there are already symlinks. After this,
repo fixes take effect at runtime and there is one source of truth.

## Review + QA layer (standing)

- Every content stage emits a short gate report, checked before proceeding.
- Every skill fix is test-gated (pytest green) and review-gated (code review).
- Nothing is "done" on assertion alone; the gate or the test says so.
- Bug ledger: `docs/audits/2026-05-31-pilot-bug-ledger.md`, seeded from the existing
  `docs/audits/2026-05-29-suite-wide-end-to-end-review`. Each entry: id, symptom,
  root cause, fix (files), test added, pytest status, review verdict, date.

## Known-broken, fix-if-hit (per the 2026-05-29 review)
`propagate_belief` (ignores claim graph), D9 orphan hard-gate (compose doesn't emit
`supports:`), neurosym D13 (not production-ready). Not on the ch1 critical path;
fixed only if a stage actually needs them.

## Success criteria
- ch1 passes stages 4–7 gates with ledger-backed claims (stage 2 done).
- Runtime unified to canonical; `make`-level pytest for touched skills green.
- Every bug hit is fixed + tested + reviewed + logged.
- A one-page "how to run a chapter" note for ch2–15.
