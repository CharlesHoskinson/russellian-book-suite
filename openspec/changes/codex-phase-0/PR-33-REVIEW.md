# PR-33 review — Codex Phase 0 bootstrap

**PR:** [#33](https://github.com/CharlesHoskinson/russellian-book-suite/pull/33)
**Branch:** `codex/phase-0-bootstrap`
**Head SHA:** `9a4aaa2c865a12c842d08595657e708a6024efb3`
**CI:** all checks green (cljs-integration, ci/lint-workflow, ci/book-qa py3.12+3.13, ci/book-thesis py3.12+3.13, ci/smoke-bermuda)
**Mergeable:** CLEAN
**Reviewer:** Claude
**Date:** 2026-05-15
**Verdict:** approve with follow-ups

## Summary

Codex delivered exactly what the brief asked of Phase 0: a wiki-only PR that seeds `docs/codex-wiki/` with six per-phase note stubs plus a cross-phase lessons file, and updates `00-index.md` to reflect Phase 0 readiness. Seven files changed, 141 / 5 add/del, no code touched, all CI green. The PR body's "Local QA evidence" section is honest about environment gaps. Two follow-ups land in Phase 1 pre-flight rather than blocking this merge: Codex's `book-knowledge` baseline run used the wrong invocation pattern and reported a phantom 11 failures, and three Phase 1-required tools (nbb, ruff, gh auth) are not currently usable on the worktree.

## A. Scope and structure

- **G1 (scope):** PR touches only `docs/codex-wiki/`. ✓
- **G2 (file set):** matches the brief's specified seven files: `00-index.md`, `01-audit-findings.md`, `02-pr3.5-notes.md`, `03-pr4-notes.md`, `04-pr5-notes.md`, `05-pr6-notes.md`, `99-lessons.md`. ✓
- **G3 (section template):** every per-phase file uses the spec's section template (`Context entering this phase`, `Decisions made`, `Surprises / unexpected complexity`, `Bugs found and fixed mid-phase`, `Open questions for Claude`, `Status`). ✓
- **G4 (cross-references):** `00-index.md:11-19` links resolve to the six per-phase files; `00-index.md:30` points correctly to the handoff design spec.
- **G5 (Phase 1 gate honoured):** Codex stopped at the seeded wiki and did not begin Phase 1 work. PR description states "Phase 1 starts only after the Phase 0 PR merges." ✓

## B. PR body claims walked

- "Run the Phase 0 baseline checks and included evidence in the PR body." — present, but invoked from repo root (`python -m pytest skills/book-knowledge/tests -q`) rather than the brief's `(cd skills/$s && .venv/Scripts/python.exe -m pytest tests/ -q)` pattern from `docs/handoffs/2026-05-15-codex-deep-review-and-implementation-brief.md:69-74`. See finding **[P1-001]**.
- "neurosym-forge 155 passed", "verifiers/bermuda 23 passed", "book-qa 47 passed" — replayed locally from skill dirs, all three confirmed green.
- "book-knowledge 11 failed, 130 passed" — replayed. From skill dir: **141 passed**. From repo root: **11 failed, 130 passed**. The failures are cwd-relative fixture paths in `test_ingest_markdown.py`, `test_ingest_pdf.py`, `test_skill_integration.py`, `test_validate_shacl.py`, `test_verify_claim.py`. Not a regression — invocation artifact.
- "Two subagent review gates passed" — accepted on assertion; both are internal to Codex's loop.

## C. Environment issues triaged

| Issue | Phase 1 blocker? | Resolution path |
|---|---|---|
| `gh auth status` reports invalid token | partial — Codex used the GitHub connector to open PR #33, which works for one-shot ops but not for `gh pr view --json comments` polling | **[P1-002]** — fix `gh auth login` before Phase 1; the brief expects Codex to poll its own PR comments via `gh` |
| `nbb` not on PATH | yes — Phase 1 audit reads CLJS templates and Phase 3+ will need to run `npm run test:booklogic` end-to-end | **[P1-003]** — `npm install -g nbb` (or `npx nbb` in scripts) before Phase 1 |
| `ruff` not on PATH; `python -m ruff` unavailable | yes — `codex-review-protocol.md:38` mandates ruff in Phase 1 baseline | **[P1-004]** — `pip install ruff` in each skill venv (or system-wide) before Phase 1 |
| Repo-root pytest invocation surfaced 11 cwd-dependent failures | no for this PR (docs-only); yes for accurate Phase 1 baseline | **[P1-001]** — re-run baselines per the brief's exact command before Phase 1 |

## D. Wiki content — read pass

- `00-index.md:7` reads "Phase 0 - bootstrap ready for review." — accurate.
- `00-index.md:14` uses the literal word "infinity" in the row label for `99-lessons.md`. Minor; the source spec used `∞`. Cosmetic, see **[P2-001]**.
- `00-index.md:19` says 99-lessons.md status is "started" while every other not-yet-active row says "not started". Defensible: the lessons file does contain one seed entry, but the spec's protocol lists three states (`not started` / `in progress` / `merged`). Cosmetic, see **[P2-002]**.
- `99-lessons.md:5-7` seed entry is a single honest line: "2026-05-15 - Phase 0 seeded the working wiki. No implementation lessons recorded yet." — exactly the discipline the brief asked for.
- Per-phase stub files all empty as expected; bullets read "No Phase N decisions recorded yet." which is the right placeholder shape for Codex to overwrite.

## E. AI-smell check

- No emoji in any wiki file. ✓
- No "Main theorem:", "Proof strategy:", "key insight", numbered proof steps. ✓
- PR title and body terse, imperative. ✓
- Commit message on `9a4aaa2` is conventionally formatted; no Co-Authored-By. ✓ (Note: cannot inspect commit message body from the API result; verify on merge.)

## Findings

### P0 (blocker)

None.

### P1 (must-fix before Phase 1 starts — not blocking this merge)

- **[P1-001]** Re-establish the book-knowledge baseline using the brief's exact command. The repo-root invocation reports 11 failures that are cwd artifacts only. Run `(cd skills/book-knowledge && .venv/Scripts/python.exe -m pytest tests/ -q)`; expected result is 141 passed. Update the wiki at `docs/codex-wiki/00-index.md` under a `## Baseline at handoff` section with the corrected counts.
- **[P1-002]** Restore `gh` auth on the codex worktree before Phase 1 (`gh auth login --scopes repo`). The brief assumes Codex polls its own PRs via `gh pr view <n> --json comments,reviews` — that path fails today.
- **[P1-003]** Install `nbb` on PATH (`npm install -g nbb`) or commit to invoking it through `npx` in every script the brief references. Phase 1 reads the CLJS compiler template and Phase 3+ runs `npm run test:booklogic`.
- **[P1-004]** Install `ruff` (`pip install ruff` in each skill venv, or system-wide) so the Phase 1 baseline can include the ruff pass that `codex-review-protocol.md:38` requires.

### P2 (post-merge polish)

- **[P2-001]** `docs/codex-wiki/00-index.md:14` — the row label `infinity` should be `∞` to match the source spec. One-character change.
- **[P2-002]** `docs/codex-wiki/00-index.md:19` — `99-lessons.md` status reads "started"; align to the spec's tri-state vocabulary (`not started` / `in progress` / `merged`).

## Verdict

**approve with follow-ups.** Merge PR #33 as-is. Before launching Codex into Phase 1, the user runs:

1. `gh auth login --scopes repo` on the codex worktree.
2. `npm install -g nbb` and `pip install ruff` (or per-venv).
3. Re-issue the bootstrap-resume prompt with one added instruction: "first task this session is to re-run baselines per the brief's exact command and write the result to `docs/codex-wiki/00-index.md` under `## Baseline at handoff` — ship that fix in the first Phase 1 commit."

P2 polish can be absorbed into any later wiki update.
