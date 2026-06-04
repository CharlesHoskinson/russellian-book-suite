# halmos

A sequential cross-chapter linkage reviewer. When chapter N is drafted, `halmos` audits how
it builds on chapters 1…N−1 — concept linkage, the N−1→N handoff seam, and spiral coherence
in the sense of Paul Halmos's *How to Write Mathematics* — and soft-gates
the chapter on broken links (`halmos_critical_count == 0`). It complements `book-thesis`
(logical entailment) and `review-conductor` (persona panel); it is the expository, not the
logical, complement.

## Run
```python
from skill_api import run_halmos
verdict = run_halmos(workspace, "ch-09", dispatcher=my_task_dispatcher)
```
`run_halmos` chains: `build_concept_ledger` → `build_linkage` → `dispatch_halmos_review` →
`aggregate_halmos`. See `SKILL.md` for the public surface and `references/halmos-doctrine.md`
for the reviewer brief.

## Data shapes
```
halmos/concepts.jsonl       {"concept","slug","gloss","introduced_in","intro_n","aliases","source"}
halmos/linkage/ch-NN.json   {"chapter_id","n","references":[slug],"introduces":[slug],
                             "seam":{"prev_close","this_open","status","overlap"},"flags":[...]}
chapters/drafts/<id>/halmos-verdict.json
                            {"chapter_id","halmos_critical_count","important_count",
                             "minor_count","spiral_coherence","per_prior_chapter","reviews_complete"}
chapters/drafts/<id>/halmos-review.md   human-readable report
```

## Tests
`cd skills/halmos && .venv/Scripts/python.exe -m pytest tests/ -q`  (stdlib only).
