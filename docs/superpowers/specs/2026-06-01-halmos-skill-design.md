# halmos — sequential cross-chapter linkage review (design)

**Date:** 2026-06-01
**Status:** approved (design); ready for implementation plan
**Skill home:** `C:\russellian-book-suite\skills\halmos\`

## Purpose

As chapters are drafted sequentially, `halmos` reviews each new chapter N against the
chapters already written (1…N−1) to audit their **connective tissue**: concept linkage,
argument continuity, flow, and consistency. It is named for Paul Halmos (1916–2006), the
mathematician celebrated as an expositor, whose *How to Write Mathematics* (1970)
prescribes the **spiral method**: build exposition so each pass recalls and refines what
came before and the reader is *always prepared* for what is next. `halmos` enforces that
spiral across chapter boundaries.

It fills the one gap in the suite. `book-thesis` checks logical entailment and
contradiction against thesis nodes; `review-conductor` runs persona panels on a single
chapter; neither audits whether chapter N **recalls, reuses, and builds on** the prior
chapters. `halmos` does exactly that, and it soft-gates the chapter on broken links, the
way the persona panel soft-gates on a gating critical.

## The Halmos doctrine (the checks)

Grounded in Halmos's documented principles (spiral exposition; recall prior material when
reused; say something; motivate before defining; consistent terminology and notation).

| Check | What it catches | Severity |
|---|---|---|
| `orphan-reference` | N leans on a concept/term as if established, but no earlier chapter (nor N itself) introduced it | critical |
| `broken-handoff` | N−1's closing promise is not picked up by N's opening, or N opens on something never set up | critical |
| `continuity-gap` | N's argument skips a rung — assumes a step the prior chapters never built | critical (clear skip) / important (soft) |
| `missed-recall` | N reuses an earlier concept without recalling it, so the reader is not kept prepared | important |
| `spiral-stall` | N merely repeats a prior concept instead of refining or extending it | important |
| `terminology-drift` | the same concept is named differently across chapters | important |
| `premature-definition` | a new concept is defined before it is motivated | minor |

`spiral_coherence` verdict is one of `tight | acceptable | loose`, summarizing the whole.

## Architecture

Hybrid: a deterministic concept graph does the mechanical bookkeeping; a Halmos-reviewer
agent does the judgment the graph cannot.

### Components (one file, one responsibility)

1. **`scripts/concept_ledger.py`** — maintains `halmos/concepts.jsonl`. Each record is one
   concept: `{concept, slug, gloss, introduced_in, aliases[], source: claim|device}`.
   Concepts are harvested from two places, reusing existing infrastructure:
   - the **verified claim ledger** (`book-knowledge.ledger`): each verified claim's
     `supports_chapters` and `canonical_text` yields claim-backed concepts;
   - a **named-device extractor** over each chapter draft: capitalized multi-word terms and
     book coinages (e.g., "authority airgap", "Bounded Polis", "Sovereign Horizon",
     "logic monopoly") with a one-line gloss taken from the sentence that introduces them.
   Idempotent: running it for chapters 1…N (re)builds the ledger; `introduced_in` is the
   earliest chapter a concept appears in.
   Public: `build_concept_ledger(workspace) -> Path`.

2. **`scripts/build_linkage.py`** — for chapter N, computes the deterministic linkage and
   writes `halmos/linkage/ch-NN.json`:
   - `references`: prior concepts N mentions (match slug/alias in N's normalized text);
   - `introduces`: concepts whose `introduced_in == N`;
   - `seam`: `{prev_close, this_open, status}` where status ∈ `clean|broken|unknown` from a
     keyword/overlap test on N−1's last body paragraph vs N's first;
   - `flags`: mechanical `orphan-reference` (a concept-shaped term used in N that is neither
     in the ledger nor introduced by N), `terminology-drift` candidates (alias of a prior
     concept appearing where the canonical term is expected), `missed-recall` candidates (a
     prior concept used in N with no nearby recall cue).
   Public: `build_linkage(workspace, chapter_id) -> dict`.

3. **`scripts/dispatch_halmos_review.py`** — builds the agent payload and dispatches one
   **Halmos-reviewer** subagent. Payload = chapter N draft + a **priors digest** (for each
   prior chapter: title, one-line thesis from its contract `purpose`, the concepts it
   introduced with glosses, and its closing handoff paragraph) + the deterministic
   `linkage.json`. The agent applies `references/halmos-doctrine.md` and returns structured
   findings: per-prior-chapter linkage notes, the per-check findings with severities, and a
   `spiral_coherence` verdict. Dispatcher is a caller-provided callable (review-conductor
   pattern) so it is testable with a stub.
   Public: `dispatch_halmos_review(workspace, chapter_id, dispatcher=None) -> dict`.

4. **`scripts/aggregate_halmos.py`** — merges the deterministic flags and the agent findings
   into `chapters/drafts/<id>/halmos-review.md` and `chapters/drafts/<id>/halmos-verdict.json`.
   The verdict carries `halmos_critical_count`, `important_count`, `minor_count`,
   `spiral_coherence`, and `per_prior_chapter`. Deterministic critical flags
   (orphan-reference, broken-handoff) are merged with the agent's, deduplicated by
   (check, concept/seam).
   Public: `aggregate_halmos(workspace, chapter_id, agent_findings, linkage) -> Path`.

5. **`scripts/conductor.py`** — the public entrypoint that runs 1→4 in order and returns the
   verdict. Public: `run_halmos(workspace, chapter_id, dispatcher=None) -> dict`.

6. **`references/halmos-doctrine.md`** — the doctrine and the reviewer brief (the Halmos
   lens, with citations to *How to Write Mathematics* and the spiral method), plus the
   per-check definitions and a severity rubric. This is the agent's persona file.

7. **`skill_api.py`** — exports `build_concept_ledger`, `build_linkage`,
   `dispatch_halmos_review`, `aggregate_halmos`, `run_halmos`, with a `SKILL_API_VERSION`.

### Contract integration (book-compose)

`chapter_contract_check.py` gains one acceptance-test metric, `halmos_critical_count`, read
from `chapters/drafts/<id>/halmos-verdict.json` (mtime ≥ draft mtime, exactly like the
persona-verdict gate). Chapter contracts may then add `- halmos_critical_count == 0` to
`acceptance_tests`. If the verdict file is absent or stale, the metric reports "review not
run" (gate unsatisfied), mirroring `persona_reviews_complete == False`.

## Data flow

```
draft chapter N (existing Task 3)
  -> build_concept_ledger(workspace)            # idempotent, covers 1..N
  -> build_linkage(workspace, ch-NN)            # deterministic flags + seam
  -> dispatch_halmos_review(workspace, ch-NN)   # Halmos-reviewer agent
  -> aggregate_halmos(...)                       # halmos-review.md + halmos-verdict.json
  -> fix any halmos_critical_count > 0; re-run
  -> chapter_contract_check reads the gate
```

`run_halmos` chains all four. The skill is invoked per chapter, after the draft exists and
before (or alongside) the persona panel.

## Boundaries

- **Reads:** `chapters/drafts/`, `chapters/contracts/`, the claim ledger (`claims/`), the
  thesis (`thesis/`, `.knowledge/`).
- **Writes:** `halmos/` (concepts.jsonl, linkage/) and
  `chapters/drafts/<id>/{halmos-review.md, halmos-verdict.json}` only.
- **Network:** none — `halmos` is pure analysis.
- **Reuses (via the sibling-skills loader):** `book-knowledge` (ledger, workspace),
  `book-thesis` (handoff/thesis helpers) where useful. Does not depend on `russellian-style`.
- **Relationship to siblings:** distinct from `book-thesis` (logical entailment) and
  `review-conductor` (persona panel); complementary to `paragraph-weaver` (intra-chapter).

## Testing

- Unit tests (deterministic, no agent): concept harvesting and earliest-introduction;
  orphan-reference detection on a fixture where a chapter references an unestablished term;
  seam matching (clean vs broken handoff); terminology-drift detection; aggregation and the
  `halmos_critical_count` rollup; the contract metric reader (present/stale/absent).
- Stub-dispatcher integration test for `dispatch_halmos_review` and `run_halmos` (the
  review-conductor approach), asserting the verdict shape and gate computation.
- A `chapter_contract_check` test that the new metric gates correctly.

## Out of scope (YAGNI)

- No prose rewriting (that is russellian-style / the drafter).
- No new network fetching.
- No automatic fixing of linkage breaks — `halmos` reports and gates; the drafter fixes.
- No replacement of the book-thesis entailment pass; `halmos` is the expository complement,
  not the logical one.
