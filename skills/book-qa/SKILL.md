# book-qa

Post-build mechanical and editorial defect-gating for non-fiction book artefacts. Sibling to `russellian-style` (sentence-grain), `book-knowledge` (claim ledger), `book-compose` (orchestrator), and `book-review` (qualitative personas).

## Where it sits in the pipeline

```
chapter drafts → russellian + book-craft → book-review personas → book-compose.build_book → manuscript.{md,html,pdf}
                                                                                                    │
                                                                                                    ▼
                                                                                              book-qa (here)
                                                                                                    │
                                                                                                    ▼
                                                                                              release bundle
```

`book-qa` runs AFTER `build_book` and BEFORE shipping. It is the last gate.

## Architecture (Generator-Verifier with Deterministic Gate)

Four stages, executed in order:

1. **Deterministic linter** (`lint_artifact.py`) — pure Python, catches D1–D8 mechanical defects in seconds with zero variance. Hard-fail on critical.
2. **Per-chapter swarm** (`dispatch_chapter_qa.py`) — 10 fresh-context agents in randomised order, each applying the 15-item checklist (`checklists/chapter-qa.md`) to one chapter, returning structured JSON tickets only.
3. **Sentinel** (`sentinel.py`) — aggregates Stage-1 + Stage-2 findings into a single defect ledger; classifies critical / important / minor.
4. **Healer** (`healer.py`) — for each critical defect, dispatch an isolated-context patch agent that sees ONLY the defect ticket and the affected span. Bounded to 3 iterations per defect class.

## Defect taxonomy (D1–D8 mechanical, C1–C15 editorial)

### D1–D8 — caught deterministically by `lint_artifact.py`

- **D1** orphan citation tokens — `[clm-...]`, bare `clm-NNNN-NNNNNN`, "Claim ledger:", numeric `[^N]: clm-` patterns
- **D2** raw markdown bleed inside HTML blocks
- **D3** broken cross-references — figure paths, footnote ref/def integrity, ToC vs heading drift
- **D4** heading hierarchy violations
- **D5** count-contract failures — word / footnote / figure counts per chapter outside bands
- **D6** paragraph-length variance outside [0.4, 1.2] coefficient
- **D7** CSS reset clobber — Tailwind preflight overriding heading sizes with no override
- **D8** asset 404s

### C1–C15 — judged per-chapter by Stage-2 agents

- **C1** heading hierarchy
- **C2** cross-references
- **C3** footnote quality (substantive, semantic names)
- **C4** citation noise (no internal IDs)
- **C5** HTML block hygiene
- **C6** terminology consistency (against `checklists/house-style.yaml`)
- **C7** scene anchoring
- **C8** sidebar quality (≤3 sentences)
- **C9** table quality (numeric column right-alignment)
- **C10** paragraph length variance
- **C11** Russell-style discipline (hedges, em-dash-as-comma)
- **C12** citation completeness for numeric/surprising claims
- **C13** closing strength
- **C14** image alt-text quality
- **C15** print-ready format (≤120-char lines)

## Why the swarm rather than one fat reviewer

Three reasons from the research and our own experience:

1. **Context rot.** Information in the middle of a long context window suffers >30% accuracy drop. A single reviewer scanning 10 chapters drops middle chapters. Ten fresh-context reviewers — one per chapter — never enter the "middle" of anything.
2. **Behavioural drift.** Agents running long dispatches drift toward generic findings. Narrow prompts ("audit ONE chapter against 15 numbered checks") defeat the drift.
3. **Structured output isolation.** Each agent returns a JSON ticket list, never prose. The Sentinel aggregator is a Python set-diff, not a re-reading.

## Usage

```bash
# Stage 1 alone (fast, deterministic)
python scripts/lint_artifact.py /path/to/workspace 3.0.0

# Full QA pass (Stage 1 + 2 + 3)
python scripts/dispatch_chapter_qa.py /path/to/workspace 3.0.0
python scripts/sentinel.py /path/to/workspace

# Apply patches (Stage 4)
python scripts/healer.py /path/to/workspace --max-iterations 3
```

## House style and waivers

- Canonical-term list lives at `checklists/house-style.yaml`. The Stage-2 swarm reads it to judge terminology drift (C6).
- Soft-gate waivers live at the workspace level: `<workspace>/qa-waivers.yaml`. Use to acknowledge a defect that is intentionally out of policy for one chapter.

## Tests

- `tests/test_lint_artifact.py` — fixture per D1–D8 rule.
- `tests/test_sentinel.py` — aggregation correctness.
- `tests/test_healer.py` — bounded-iteration convergence.

## Composes with

- **book-compose** — `build_book` should invoke `lint_artifact` as a gate; add `--qa` flag to skip during iteration.
- **book-review** — different lifecycle stage (pre-build qualitative review) and orthogonal in scope. Both ship.
- **russellian-style** — its linters are the basis of C11 judgments by Stage-2 agents.
