# PR-N review — Codex Phase 1 deep audit

**PR:** [#N](https://github.com/CharlesHoskinson/russellian-book-suite/pull/N) <!-- TBD -->
**Branch:** `codex/phase-1-audit`
**Head SHA:** `TBD`
**CI:** TBD
**Mergeable:** TBD
**Reviewer:** Claude
**Date:** TBD
**Verdict:** TBD <!-- approve | approve with follow-ups | request changes | block -->

## Summary

<!--
4–6 sentences. State what the PR ships (the audit document + wiki housekeeping),
the load-bearing pieces (Critical / Important counts; whether the PR-3.5 portability
section is present and useful), and the one or two findings that drove the verdict.
Surface credibility issues up front: did the audit miss a file in scope? Are the
severity ratings calibrated? Does the QA evidence use the right invocation form?
-->

## A. Scope and deliverable

Acceptance gates from the resume prompt and the brief:

- **G1** (single-deliverable): PR touches `docs/codex-wiki/01-audit-findings.md`, `docs/codex-wiki/00-index.md`, `docs/codex-wiki/99-lessons.md`, and nothing else. No code, no template, no asset changes. ☐
- **G2** (BLOCKED resolved): the `## BLOCKED` section added in `ae197bf` is removed from `00-index.md`. ☐
- **G3** (index housekeeping): Phase 0.5 row reads `merged 1ae3d2e`; Phase 1 row reads `in progress` with `2026-05-15` (or the PR date). ☐
- **G4** (lessons appended): `99-lessons.md` carries the env-fix entry for the `gh` token refresh and `python -m ruff` invocation. ☐
- **G5** (read-only): no file outside `docs/codex-wiki/` is modified. Confirm with `git diff --name-only origin/main...HEAD`. ☐

## B. Audit coverage

The brief (`docs/handoffs/2026-05-15-codex-deep-review-and-implementation-brief.md`, Phase 1 section) lists the in-scope file set. Confirm every listed surface is read and cited at least once in `01-audit-findings.md`:

- `skills/neurosym-forge/scripts/*.py` (every file) ☐
- `skills/neurosym-forge/assets/project-template/**` (every file) ☐
- `skills/neurosym-forge/tests/**` (every file) ☐
- `skills/book-knowledge/scripts/export_symbolic_trace.py` ☐
- `skills/book-knowledge/scripts/load_symbolic_trace.py` ☐
- `skills/book-knowledge/tests/test_export_symbolic_trace.py` ☐
- `skills/book-knowledge/tests/test_load_symbolic_trace.py` ☐
- `skills/book-knowledge/assets/ingest-trace.schema.json` ☐
- `verifiers/bermuda/scripts/*.py` (every file) ☐
- `verifiers/bermuda/rust-verifier/src/*.rs` (every file) ☐
- `verifiers/bermuda/rules/predicates.edn` ☐
- `verifiers/bermuda/tests/**` ☐

Mission-specific extras the brief mandates (each must produce at least one finding *or* an explicit "no defect found" line):

- EDN reader/writer round-trip + edge cases (empty maps, nested vectors, regex patterns, Unicode, `^{...}` reader-metadata discard) ☐
- Scaffolder Windows path bugs, junction-link assumptions, template-substitution leaks (`__project__` / `{{ project_slug }}` escapes) ☐
- PR-3 CLJS compiler completeness vs `docs/specs/2026-05-14-booklogic-v0.4-pr3-design.md` ☐
- PR-3 hidden coupling between forms (e.g., `expand-defpredicate` accidentally depending on sort-registry order) ☐
- PR-3 missing validation (e.g., predicate referencing absent `defsort`) ☐
- PR-3 `infer-value-kind` body-index correctness ☐
- PR-3 error message actionability (does the offending form appear in the message?) ☐
- Rust verifier scaffold: `unsafe` blocks, panic-on-input paths, missing `Result` wrapping ☐
- Bermuda Python ingesters: PR-3.5 portability narrative for each ingester ☐

## C. Protocol compliance

Apply `docs/operations/codex-review-protocol.md`. Confirm:

- **Seven dimensions covered.** Correctness, security, tests (deep); schema/data, documentation (medium); architecture/layering, performance/robustness (light sanity check). ☐
- **Severity buckets.** Critical / Important / Minor. Counts reported in PR body and in the audit doc. ☐
- **`file:line` precision on every finding.** Spot-check at least 5 randomly-sampled findings. ☐
- **No floating assertions.** Every claim cites a path or names a test function. ☐
- **"What NOT to flag" list honoured.** Cross-check against the protocol's intentional-design list (`claim_type` confidence vs posterior, `proposed-transitions.jsonl` overwrite, `exception_queries` `NotImplementedError` guard, two `sibling_skills.py` factoring, etc.). Any false positive against this list is a P1. ☐
- **Output format match.** Single markdown document, executive summary, findings buckets, cross-cutting concerns, test/tooling sections, next steps. ☐

## D. Audit quality — spot-check

Pick three findings (one Critical if any, one Important, one Minor) and read the cited code to confirm:

- **Spot-check 1 (Critical or Important):** `<file:line>` — quote the audit's claim in one sentence; confirm or refute against current code; record verdict. TBD ☐
- **Spot-check 2 (Important):** `<file:line>` — TBD ☐
- **Spot-check 3 (Minor):** `<file:line>` — TBD ☐

If any spot-check refutes the audit's claim, that is a P1 (calibration failure on a sampled finding implies the rest of the bucket is suspect).

## E. PR-3.5 portability assessment section

The brief requires an extra section after `Next steps`:

```markdown
## PR-3.5 portability assessment

For each Python ingester slated for CLJS port (PR-3.5), one paragraph covering:
- What it does, mechanically
- The hardest part to port faithfully
- Suggested CLJS approach
- Test fixtures that must survive the port
```

Confirm:

- Section present at end of `01-audit-findings.md`. ☐
- One paragraph per ingester (the ingesters slated for port: `ingest_ledger.py`, `extract_prose.py`, `verdict_to_qa.py`, `run_verification.py`). ☐
- Each paragraph carries the four sub-points (mechanics, hardest part, suggested approach, test fixtures). ☐
- Suggested approaches are concrete (name a CLJS namespace or library), not "use a CLJS equivalent." ☐

## F. Wiki housekeeping (already covered in G2–G4 but verify content)

- `00-index.md`'s `## Baseline at handoff` table is unchanged unless an explicit re-baselining note is added (Phase 1 should not modify pre-existing baseline counts). ☐
- `00-index.md`'s decision log carries no spurious entries. ☐
- `99-lessons.md` env-fix entry is concise (one line) and dated `2026-05-15`. ☐

## G. PR body, QA evidence, AI-smell check

PR body template (from `docs/specs/2026-05-15-codex-handoff-design.md` "Review handoff" section):

- `## For reviewer (Claude)` section present with Phase / Spec / Plan / Wiki fields. ☐
- `### What to verify` lists at least three concrete bullets. ☐
- `### What I am uncertain about` is honest (one or two doubts) or empty. ☐
- `### Local QA evidence` shows pytest counts for all 9 suites matching the recorded baseline (650 total). ☐
- Ruff results use `python -m ruff check ...` (the documented form for this worktree). ☐
- Critical / Important counts from the audit doc are echoed in the PR body. ☐

AI-smell check:

- No emoji in PR body, audit doc, or wiki updates. ☐
- No "Main theorem:", "Proof strategy:", "key insight", numbered proof steps, six-level emoji-bulleted lists. ☐
- Commit messages on the branch are terse, imperative, ≤72 char subject. ☐
- No `Co-Authored-By` lines. ☐
- No AI attribution in any new file. ☐

## Findings

### P0 (blocker)

<!-- Empty until populated. P0 = security, broken invariant, or build/test broken at HEAD. -->

None. <!-- TBD -->

### P1 (must-fix before merge)

<!--
Examples that would land here:
- Audit missed a file in the brief's in-scope list.
- A spot-checked finding is wrong (calibration failure).
- "What NOT to flag" violation (audit re-litigates an intentional design choice).
- PR-3.5 portability section missing or skips an ingester.
- Wiki housekeeping incomplete (BLOCKED still present, index row not flipped).
- PR body template skipped or QA evidence faked / from wrong invocation.
-->

TBD

### P2 (post-merge follow-up)

<!--
Examples:
- Audit doc has formatting nits (heading levels off, trailing whitespace).
- A finding's recommended fix is correct but could include a snippet.
- 99-lessons.md entry could be expanded with one more sentence.
-->

TBD

## What was NOT verified

- DEFER-TO-CI: full pytest replay across all 9 suites — the audit is read-only and the baseline is locked at `1ae3d2e`; CI confirms no regression on the wiki-only diff.
- NOT-RUN-LOCALLY: nbb integration tests — Phase 1 doesn't touch CLJS templates, so nbb wasn't re-invoked.
- NOT-VERIFIABLE: subjective calibration of every Minor finding — only sampled.

## Verdict

**TBD.** <!-- approve | approve with follow-ups | request changes | block -->

<!--
If approve with follow-ups, list each P1/P2 here with file:line + suggested change so the
author (Codex on the next session) can act from the review alone.

If approve, post `gh pr review <N> --approve` with this file's body, then
`gh pr merge <N> --squash --delete-branch`. Pull main locally afterward.

If request changes, post `gh pr review <N> --request-changes` with this body and ping
Codex via the resume prompt with a one-line summary of what to fix.
-->
