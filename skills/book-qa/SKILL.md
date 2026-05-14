# book-qa

Post-build mechanical and editorial defect-gating for non-fiction book artefacts. Runs after `book-compose.build_book` and before shipping; the last gate.

## What it owns

- Deterministic linting of built artefacts for mechanical defects D1-D8.
- Per-chapter editorial sweep C1-C15 via a fresh-context agent swarm returning JSON tickets.
- Aggregation into a single defect ledger with critical / important / minor classification.
- Bounded-iteration patch loop for critical defects via isolated-context healers.
- House-style canon at `checklists/house-style.yaml`; waivers at `<workspace>/qa-waivers.yaml`.

## What it does NOT own

- Source ingestion, claims, wiki state — `book-knowledge`.
- Chapter drafting, outlines, release-bundle assembly — `book-compose`.
- Sentence-grain prose rewriting — `russellian-style`.
- Pre-build qualitative persona judgement — `book-review`.
- Anything before `build_book` has produced an artefact.

## Architecture

```
build_book artefact
        │
        ▼
┌───────────────────┐
│ 1. Linter         │  lint_artifact.py
│    D1-D8, det.    │  pure Python, hard-fail on critical
└─────────┬─────────┘
          ▼
┌───────────────────┐
│ 2. Chapter swarm  │  dispatch_chapter_qa.py
│    C1-C15, 10x    │  fresh-context agents, JSON tickets only
└─────────┬─────────┘
          ▼
┌───────────────────┐
│ 3. Sentinel       │  sentinel.py
│    aggregate +    │  Python set-diff over D + C tickets
│    classify       │
└─────────┬─────────┘
          ▼
┌───────────────────┐
│ 4. Healer         │  healer.py
│    patch critical │  isolated-context agent per defect class,
│    max 3 iters    │  sees ticket + span only
└─────────┬─────────┘
          ▼
   release bundle
```

## Defect taxonomy

Mechanical (`lint_artifact.py`, deterministic):

- D1 orphan citation tokens (`[clm-...]`, bare `clm-NNNN-NNNNNN`, "Claim ledger:")
- D2 raw markdown bleed inside HTML blocks
- D3 broken cross-references (figure paths, footnote ref/def, ToC vs heading drift)
- D4 heading hierarchy violations
- D5 count-contract failures (word / footnote / figure counts outside bands)
- D6 paragraph-length variance outside [0.4, 1.2]
- D7 CSS reset clobber (Tailwind preflight overriding heading sizes)
- D8 asset 404s
- D9 paragraph-orphan (critical; from `book-thesis` `qa/supports-defects.json`)
- D10 transitive-contradiction (critical; from `book-thesis` `qa/datalog-defects.json`)
- D11 failed-entailment (critical; from `qa/entailment-results.json` verdicts `contradicts`/`unrelated`)
- D12 unadvanced-sub-argument (important; from `book-thesis` supports-defects summary)

Writeback-consumed categories (Stage 4, healer → book-knowledge ledger):
- `unsupported_claim` — claims lacking verified sources post-healer; proposal for D11-class transition
- `refuted_by_new_source` — claim contradicted by source added post-healer; proposal for supersede
- `addressed_rival` — counter-claim addressed in healer patch; proposal for addressed transition

Editorial (Stage-2 swarm, per chapter):

- C1 heading hierarchy
- C2 cross-references
- C3 footnote quality (substantive, semantic names)
- C4 citation noise (no internal IDs)
- C5 HTML block hygiene
- C6 terminology consistency (against `house-style.yaml`)
- C7 scene anchoring
- C8 sidebar quality (<=3 sentences)
- C9 table quality (numeric right-align)
- C10 paragraph length variance
- C11 Russell-style discipline (hedges, em-dash-as-comma)
- C12 citation completeness for numeric/surprising claims
- C13 closing strength
- C14 image alt-text quality
- C15 print-ready format (<=120-char lines)

## Scripts

- `lint_artifact.py` — deterministic mechanical linting (D1-D8).
- `dispatch_chapter_qa.py` — per-chapter editorial swarm dispatch (C1-C15).
- `sentinel.py` — ticket aggregation and classification (severity rubric).
- `healer.py` — isolated-context patch loop, max 3 iterations per defect class.
- `propose_writeback.py` — reads qa/lint-findings.json + qa/swarm-findings.json, emits claims/proposed-transitions.jsonl + qa/ledger-writeback-<version>.md
- `transition_rules.py` — pure-function mapping from QA ticket class to proposed ledger transition

## Composes with

- `book-compose` — `build_book` invokes `lint_artifact` as a gate; `--qa` flag skips during iteration.
- `book-review` — pre-build qualitative review; orthogonal scope, both ship.
- `russellian-style` — its linters back C11 judgement by Stage-2 agents.
- `book-knowledge` — read-only; claim IDs flagged by D1/C4 trace back to its ledger. `propose_writeback` writes claims/proposed-transitions.jsonl + qa/ledger-writeback-<version>.md; `apply_writeback` (in book-knowledge) commits transitions.
- `book-thesis` — writes D9-D12 inputs before `lint_artifact` reads them.

## Usage

```bash
# Stage 1 alone (fast, deterministic)
python scripts/lint_artifact.py <workspace> <version>

# Full QA pass (Stages 1-3)
python scripts/dispatch_chapter_qa.py <workspace> <version>
python scripts/sentinel.py <workspace>

# Apply patches (Stage 4)
python scripts/healer.py <workspace> --max-iterations 3
```

Waivers: add to `<workspace>/qa-waivers.yaml` to acknowledge an intentional, out-of-policy defect for one chapter.

## Tests

- `tests/test_lint_artifact.py` — fixture per D1-D8 rule.
- `tests/test_sentinel_writeback.py` — sentinel + writeback integration.
- `tests/test_propose_writeback.py` — ledger transition proposal correctness.
- `tests/test_transition_rules.py` — QA ticket class to transition mapping.

## Configuration

Place a `qa-config.yaml` file at the workspace root to opt into optional checks. Currently one knob is supported:

- `enable_verification: true` — activates D13 verification-unsat gating. Without this key (or with it set to `false`), D13 is skipped entirely so workspaces that have not yet wired up a neurosym-forge verifier run cleanly.
