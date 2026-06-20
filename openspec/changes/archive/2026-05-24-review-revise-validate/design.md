# Design — review-revise-validate cycle

**Capability slug:** `REVISE`
**Date:** 2026-05-24
**Status:** Draft, follows `proposal.md`

## 1. Pipeline

The cycle has six stages. Stages 1, 2, 5 reuse existing skills (subprocess invocations). Stages 3, 4, 6 are new Python modules in this skill.

```
                          ┌──────────────────────────────┐
                          │   chapter draft (.md)        │
                          └──────────────┬───────────────┘
                                         │
                                         ▼
   [1]  book-review --llm-backend ollama  (existing)
        7 personas × gemma4:31b → persona-review-*.md (×7)
                                         │
                                         ▼
   [2]  book-review aggregate_reviews.py  (existing)
        7 reviews → panel-summary-before.md
                                         │
                                         ▼
   [3]  synthesize_findings.py  (NEW)
        deterministic clustering → revision-instructions.md
                                         │
                                         ▼
   [4]  revise.py  (NEW)
        reviser persona via gemma4:31b → revisions.json
                                         │
                                         ▼
        apply_revisions.py  (NEW; same module)
        exact-match string replace → revised-chapter.md
                                         │
                                         ▼
   [5]  book-review on revised-chapter.md  (existing; second invocation)
        7 personas × gemma4:31b → panel-summary-after.md
                                         │
                                         ▼
   [6]  cycle_report.py  (NEW)
        diff before/after → cycle-report.md
```

## 2. Module-level design

### 2.1 `scripts/run_cycle.py` — orchestrator

CLI signature:

```
python -m scripts.run_cycle \
    --chapter-id ch-01 \
    --draft-path PATH \
    --workspace-dir PATH  (default: workspace/review-cycle/<chapter-id>/<ISO-timestamp>/)
    --model MODEL         (default: gemma4:31b; passed to both panel runs and reviser)
    [--skip-revise]       (run panel + aggregate only; no revision step)
    [--skip-revalidate]   (run through stage 4 then stop)
```

Sequentially invokes the 6 stages via `subprocess.run`. Writes a single timestamped working directory containing all artifacts. Exits 0 on success, 2 on unrecoverable error (apply failure, missing dependencies). Verbose progress to stdout; errors to stderr.

### 2.2 `scripts/synthesize_findings.py` — stage 3

Pure-Python. Reads the aggregator's per-persona findings (post-fix: structured frontmatter + body sections per persona).

Clustering algorithm:

1. Parse each review's Critical/Important/Minor sections, extracting line-range references where present (regex: `lines? (\d+)(?:-(\d+))?` and similar shapes the existing personas use).
2. Cluster findings whose line ranges overlap or are within 5 lines of each other.
3. Per cluster, compute `distinct_personas` (set), `severity_tier` (max across cluster), `theme_tags` (regex-classified: listicle, mechanical-parallel, hedging, formulaic, em-dash-overuse, jargon-density, lead-buried, etc. — pattern-match against finding text).
4. Sort clusters: severity DESC, distinct_personas DESC, line_position ASC.
5. Emit `revision-instructions.md`:

```markdown
# Revision instructions for ch-01

## Cluster 1 (Critical; 3 personas: gottlieb, ai-slop-detector, enjoyment-reader)
Lines 14-22 — theme: mechanical-parallel-structure
Personas converged on: "Four consecutive paragraphs beginning with 'This argument is not...'"
Fix recipe: vary sentence openings; merge if conceptually adjacent.
Original passage:
> <quoted original>

## Cluster 2 (Critical; 2 personas: gottlieb, ai-slop-detector)
...
```

The clusters become the input to the reviser. Only Critical and Important clusters are forwarded; Minor findings are reported but not revised (out of scope per success criteria).

### 2.3 `personas/reviser.md` — the new persona

YAML frontmatter:

```yaml
---
persona_id: reviser
display_name: Reviser
role: targeted-paragraph-rewriter
recommended_num_predict: 8192
---
```

Body (sketch, full text in tasks.md):

- "You read in the persona of a precision editor who applies specific revision instructions to a chapter."
- "You do not invent new content. You do not change passages that weren't flagged."
- "For each cluster in the revision instructions, identify the exact original paragraph(s), produce a revision, and emit a JSON object: `{original, revised, rationale}`."
- "If you cannot identify an exact original paragraph (because the cluster's line refs are imprecise), skip that cluster and note it in `unresolved` array."
- "Preserve author voice: rhythm, vocabulary register, sentence length variance."

### 2.4 `scripts/revise.py` — stage 4

Two phases:

**Phase A (revise):**
- Render the reviser prompt: persona body + chapter text + revision instructions
- Dispatch via `run_persona_via_ollama` with `model=gemma4:31b`, `think=True` (inherits default), `num_predict=8192` (from persona frontmatter)
- Parse the JSON array out of the response (the reviser is instructed to emit JSON; tolerate code-fenced output via existing `_strip_code_fence` helper)
- Write `revisions.json` and `revisions-raw-response.md` (the full reviser output for debugging)

**Phase B (apply):**
- For each `{original, revised, rationale}` entry, verify `original` appears verbatim in the chapter
- If any fails: write `revisions-apply-failures.json` with details and exit 2 (REQ-REVISE-002)
- If all succeed: apply exact-match string replacement; write `revised-chapter.md`

### 2.5 `scripts/cycle_report.py` — stage 6

Reads `panel-summary-before.md` + `panel-summary-after.md`. Extracts the per-persona verdict + critical/important/minor counts from each. Emits `cycle-report.md`:

```markdown
# Cycle report — ch-01 — <timestamp>

## Verdicts

| Persona | Before | After |
|---|---|---|
| gottlieb | NEEDS_WORK | APPROVED_WITH_NOTES |
| ai-slop-detector | APPROVED_WITH_NOTES | APPROVED |
| ...

## Findings counts

|             | Before | After | Delta |
|-------------|--------|-------|-------|
| Critical    | N      | M     | (-K)  |
| Important   | N      | M     | (-K)  |
| Minor       | N      | M     | (-K)  |

## Resolved (in before, gone in after)

- gottlieb: "Four consecutive 'This argument is not...'" — RESOLVED
- ...

## Regressions (NEW in after — flagged per REQ-REVISE-005)

- (if any; this is the loud signal that revision introduced new issues)

## Net interpretation

<one paragraph summarizing whether the cycle moved the chapter forward>
```

## 3. EARS requirements

### REQ-REVISE-001 — Ubiquitous

The system shall run all six stages without operator intervention given `--chapter-id`, `--draft-path`, and an Ollama daemon serving the requested model.

### REQ-REVISE-002 — Event-driven

When the reviser's JSON output references an `original` paragraph that does not appear verbatim in the source chapter, the system shall halt with exit code 2 and write `revisions-apply-failures.json` listing the offending paragraphs.

### REQ-REVISE-003 — Ubiquitous

The system shall emit `cycle-report.md` containing before/after panel-finding counts (Critical, Important, Minor) in a comparison table at the top of the file.

### REQ-REVISE-004 — Optional feature

Where `book-knowledge` is wired into the workspace (workspace contains a `claims/` directory with a non-empty `ledger.jsonl`), the system may invoke `book-knowledge claim_validator.py` against `revised-chapter.md` as a post-apply check. The check's output is appended to `cycle-report.md` under `## Post-apply claim validation`.

### REQ-REVISE-005 — Unwanted behaviour

If the after-panel Critical count exceeds the before-panel Critical count, the system shall include a prominent `## ⚠ REGRESSION` block at the top of `cycle-report.md` (above the verdicts table) listing the new Critical findings.

### REQ-REVISE-006 — Ubiquitous

The system shall invoke `book-review aggregate_reviews.py` (the existing aggregator) for both the before and after panel runs. The system shall not implement a parallel aggregation path.

### REQ-REVISE-007 — Event-driven

When the before-panel finds zero Critical findings (sum across all personas), the system shall skip stages 3, 4, and 5 (synthesis, revision, re-validation) and emit `cycle-report.md` with a single section stating "no Critical findings; revision skipped".

### REQ-REVISE-008 — Ubiquitous

The reviser persona's frontmatter shall include `recommended_num_predict: 8192`. Lower budgets starve the JSON output (the reviser emits one JSON object per cluster, which typically requires 100-300 tokens per cluster plus reasoning overhead).

## 4. Workspace layout

Each cycle invocation creates an ISO-timestamped workspace:

```
workspace/review-cycle/<chapter-id>/<ISO-timestamp>/
  panel-before/
    persona-review-<persona-id>.md  (×7)
  panel-summary-before.md            (from aggregate_reviews)
  revision-instructions.md           (from synthesize_findings)
  revisions.json                     (from reviser, parsed)
  revisions-raw-response.md          (from reviser, raw)
  revised-chapter.md                 (from apply step)
  panel-after/
    persona-review-<persona-id>.md  (×7)
  panel-summary-after.md             (from aggregate_reviews; second run)
  cycle-report.md                    (from cycle_report)
```

Workspace is self-contained; can be moved, archived, diffed against earlier cycles.

## 5. Test strategy

- `synthesize_findings.py`: unit tests with synthetic aggregator output covering empty-input, single-cluster, multi-cluster, and overlapping-line-range cases.
- `revise.py` Phase B (apply): unit tests with mocked LLM output for happy path, missing-original failure, multiple replacements in one chapter.
- `cycle_report.py`: unit tests with synthetic before/after summaries covering improvement, regression, and unchanged cases.
- Stage 4 (reviser dispatch): mocked `make_ollama_call` returning canned JSON; assert end-to-end pipeline.
- End-to-end smoke (gemma3:4b for speed): one persona, tiny chapter, complete cycle.

## 6. Architectural decisions (rationale for future reference)

### 6.1 Why paragraph-rewrites, not unified diff

Diff context lines fail on long prose: whitespace/line-wrap drift makes the diff unappliable. JSON paragraph pairs use exact-match string replacement — robust, bounded output size, every rewrite is traceable to a rationale.

### 6.2 Why single-pass, not auto-iteration

Auto-iteration was considered (loop until Critical count is 0 or N=3 max). Rejected because:
- Wall-clock unpredictable
- Risk of iterative drift away from author voice
- Operator-driven re-runs are simple and keep the human in the loop

### 6.3 Why local-LLM, not Claude subagent revision

User decision in brainstorming. Tradeoffs:
- gemma4:31b prose quality < Claude on long-form, but adequate for paragraph-level rewrites against specific instructions
- Local: reproducible, no API cost, offline-capable
- The author can always run the cycle, then do a final Claude-pass manually if needed

### 6.4 Why reuse `aggregate_reviews.py`, not build new

Audit theme 1 just fixed the artifact contract so this aggregator works against ollama-generated artifacts. Reusing it means the cycle's findings shape matches the rest of the suite. Forking would re-introduce the silent-skip class of bugs the audit caught.

### 6.5 Why subprocess composition, not in-process imports

The 6 skills in russellian-book-suite each have their own .venv. Importing across venv boundaries is fragile. Subprocess invocation respects venv isolation and matches the operator-facing pattern.
