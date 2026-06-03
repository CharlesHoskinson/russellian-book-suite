# Carve Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Unbreak main's Windows CI leg, land the four carve PRs (#191–#194), run B5 reconciliation, and drain the nine dependabot PRs.

**Architecture:** Five sequential phases, each ending in a read-only QA-agent gate. Phase 0 fixes main (paragraph-weaver windows-canary markers) — the single change that clears `ci-required` everywhere. Phases 1–2 land the carve PRs (lazy-import fix on #193). Phase 3 reconstructs the parked-docs branch and retires four local branches. Phase 4 applies a CI-judged merge rule to dependabot.

**Tech Stack:** git, `gh`, per-skill `.venv` pytest, PowerShell.

**Spec:** `docs/superpowers/specs/2026-06-03-carve-completion-design.md`

**Conventions:**
- Repo root `C:\russellian-book-suite`. All `git`/`gh` commands run there.
- Merge method: `gh pr merge <n> --merge --delete-branch` (merge commits, repo precedent).
- "Wait for green": poll `gh pr checks <n>` until no `pending`/`fail` rows besides known-skipped (`budget-check` shows `skipping` — that is fine). A `fail` row means STOP and diagnose; do not merge.
- "QA gate": dispatch a read-only subagent with the exact checklist in the task. Nothing pushes/merges/deletes until it reports clean.
- Commit style: terse, imperative, no AI attribution.
- Already done before this plan: branch `fix/paragraph-weaver-windows-canary` exists, cut from `origin/main`, with commit `4888ee0` (carve-completion design + recovered post-185 spec/plan docs).

---

## File Structure

```
Phase 0 (branch fix/paragraph-weaver-windows-canary)
  skills/paragraph-weaver/pyproject.toml          (modify: register marker)
  skills/paragraph-weaver/tests/*.py              (modify: 15 files, pytestmark)
  docs/superpowers/specs/2026-06-03-carve-completion-design.md            (already committed, 4888ee0)
  docs/superpowers/specs/2026-06-03-post-185-skill-install-and-branch-carve-design.md (already committed)
  docs/superpowers/plans/2026-06-03-post-185-skill-install-and-branch-carve.md        (already committed)
  docs/superpowers/plans/2026-06-03-carve-completion.md                   (this file)

Phase 2 (branch add-syntopical-v0.3)
  skills/syntopical-metabook/scripts/acquire/expand_seeds.py        (modify)
  skills/syntopical-metabook/scripts/acquire/download_and_ingest.py (modify)
  skills/syntopical-metabook/scripts/gap/coverage_report.py         (modify)
  skills/syntopical-metabook/scripts/synthesize/topic_map.py        (modify)
  skills/syntopical-metabook/scripts/synthesize/disputed_questions.py (modify)
  skills/syntopical-metabook/scripts/synthesize/concept_reconcile.py  (modify)
  skills/syntopical-metabook/tests/unit/test_smoke_import.py        (create)

Phase 3 (branch feat/v3-architecture-docs, new)
  docs/superpowers/specs/2026-05-31-rust-axum-v2-architecture-design.md
  docs/superpowers/specs/2026-06-01-rbs-v3-architecture-design.md
  docs/superpowers/specs/2026-06-01-rbs-v3-skill-migration-plan-design.md
  docs/superpowers/specs/2026-06-01-rust-microservices-ascii-protocol.md
  docs/superpowers/specs/2026-06-01-skill-capability-protocol-design.md
```

---

## Task 1: paragraph-weaver venv + marker registration

**Files:**
- Modify: `skills/paragraph-weaver/pyproject.toml`

- [ ] **Step 1: Confirm we are on the phase-0 branch**

```powershell
git -C C:\russellian-book-suite rev-parse --abbrev-ref HEAD
```
Expected: `fix/paragraph-weaver-windows-canary`.

- [ ] **Step 2: Create the skill venv (none exists)**

```powershell
cd C:\russellian-book-suite\skills\paragraph-weaver
py -3.13 -m venv .venv
.venv\Scripts\python.exe -m pip install -q -e .[dev]
```
Expected: pip finishes with `Successfully installed ... paragraph-weaver ... pytest ...`. `.venv` is gitignored — verify with `git status --short` showing no `.venv` entries.

- [ ] **Step 3: Baseline — full suite green, canary selection empty**

```powershell
.venv\Scripts\python.exe -m pytest tests/ -q
.venv\Scripts\python.exe -m pytest tests/ -q -m windows_canary
```
Expected: first run all pass; second run exits 5 with `no tests ran` (reproduces the CI failure locally).

- [ ] **Step 4: Register the marker in pyproject.toml**

In `skills/paragraph-weaver/pyproject.toml`, change:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra -q"
```

to:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra -q"
markers = [
    "windows_canary: test exercises platform-sensitive behaviour and must run on Windows",
]
```

(Wording copied verbatim from `skills/feynman-style/pyproject.toml`.)

- [ ] **Step 5: Commit**

```powershell
git -C C:\russellian-book-suite add skills/paragraph-weaver/pyproject.toml
git -C C:\russellian-book-suite commit -m "paragraph-weaver: register windows_canary marker"
```

---

## Task 2: pytestmark in all 15 test files

**Files:**
- Modify: all of `skills/paragraph-weaver/tests/test_argument.py`, `test_cycles.py`, `test_end_to_end.py`, `test_feasibility.py`, `test_features.py`, `test_gate.py`, `test_graph.py`, `test_order.py`, `test_report.py`, `test_scaffold.py`, `test_skill_api.py`, `test_skill_doc.py`, `test_stubs.py`, `test_targets_base.py`, `test_weave.py`

- [ ] **Step 1: Add the marker to each file, by hand (no sweep tool)**

Every file starts with a `# tests/<name>.py` comment then `from __future__ import annotations`. For the 14 files that do NOT already import pytest, insert immediately after the `from __future__` line:

```python
import pytest

pytestmark = pytest.mark.windows_canary
```

For `test_targets_base.py` (already has `import pytest` in its import block), add only this line directly after its existing `import pytest` line:

```python
pytestmark = pytest.mark.windows_canary
```

CRITICAL (this is the bug that killed the 05-21 sweep): `pytestmark = pytest.mark.windows_canary` must appear AFTER an `import pytest` in the same file — never before it.

- [ ] **Step 2: Verify every file has both lines in the right order**

```powershell
cd C:\russellian-book-suite\skills\paragraph-weaver
Get-ChildItem tests\test_*.py | ForEach-Object { $c = Get-Content $_ -Raw; $ok = ($c -match '(?s)import pytest.*pytestmark = pytest\.mark\.windows_canary'); "{0} {1}" -f ($ok ? 'OK ' : 'BAD'), $_.Name }
```
Expected: 15 lines, all `OK`.

- [ ] **Step 3: Run the canary selection — must collect everything**

```powershell
.venv\Scripts\python.exe -m pytest tests/ -q -m windows_canary
```
Expected: all tests run and pass, `0 deselected`. Exit code 0. (If any test fails, it failed for a real Windows reason — fix or report, do not unmark.)

- [ ] **Step 4: Run the full suite unfiltered (no regression)**

```powershell
.venv\Scripts\python.exe -m pytest tests/ -q
```
Expected: identical pass count to Task 1 Step 3 baseline.

- [ ] **Step 5: Commit**

```powershell
git -C C:\russellian-book-suite add skills/paragraph-weaver/tests
git -C C:\russellian-book-suite commit -m "paragraph-weaver: mark all tests windows_canary (fix exit-5 Windows CI leg)"
```

---

## Task 3: Phase-0 QA gate, push, PR, merge

**Files:** none new. Also commit this plan file if not yet committed.

- [ ] **Step 1: Commit the plan document**

```powershell
git -C C:\russellian-book-suite add docs/superpowers/plans/2026-06-03-carve-completion.md
git -C C:\russellian-book-suite commit -m "Plan: carve completion"
```

- [ ] **Step 2: QA gate — dispatch a read-only auditor subagent**

Checklist for the auditor (must verify against the live repo, not trust claims):
1. `git diff --name-only origin/main HEAD` lists ONLY: `skills/paragraph-weaver/pyproject.toml`, the 15 test files, and the 4 docs files (2 specs, 2 plans). Nothing else.
2. No `.venv`, `__pycache__`, `*.egg-info`, or binary files in the diff.
3. Re-run both pytest commands (canary-filtered and unfiltered) in `skills/paragraph-weaver` and confirm green / non-empty collection independently.
4. Every test file matches the `import pytest` → `pytestmark` ordering (re-run the Step-2 scan from Task 2).
Proceed only on a clean report.

- [ ] **Step 3: Push and open the PR**

```powershell
git -C C:\russellian-book-suite push -u origin fix/paragraph-weaver-windows-canary
gh pr create --repo CharlesHoskinson/russellian-book-suite --base main --head fix/paragraph-weaver-windows-canary --title "Fix paragraph-weaver Windows CI leg: windows_canary markers" --body "The Windows python-skill leg runs pytest -m windows_canary; paragraph-weaver had no marked tests and no registered marker, so pytest exited 5 (no tests collected) and reddened ci-required on every PR. Registers the marker and marks all test files, matching the feynman-style convention. Also lands the post-185 carve spec/plan docs and the carve-completion design + plan."
```
Expected: PR URL printed.

- [ ] **Step 4: Wait for green, then merge**

Poll until done (re-run every few minutes):
```powershell
gh pr checks <PR#> --repo CharlesHoskinson/russellian-book-suite
```
Expected: all pass (especially `python-skill (paragraph-weaver / windows-2022)`). Then:
```powershell
gh pr merge <PR#> --repo CharlesHoskinson/russellian-book-suite --merge --delete-branch
```

- [ ] **Step 5: Confirm main is green end-to-end**

```powershell
git -C C:\russellian-book-suite fetch origin
gh run list --repo CharlesHoskinson/russellian-book-suite --branch main --limit 1
```
Expected: the merge-triggered run completes `success` — first green main since 2026-05-29. If the run is still in progress, wait for it before Phase 1.

---

## Task 4: Phase 1 — update and merge #191, #192, #194

**Files:** none (branch management only).

- [ ] **Step 1: Update each PR branch so it contains main's Windows fix**

```powershell
foreach ($n in 191,192,194) { gh pr update-branch $n --repo CharlesHoskinson/russellian-book-suite }
```
Expected: each succeeds (creates a merge-from-main commit on the PR branch). If a branch reports conflicts, STOP for that PR and resolve by checking out the branch and merging `origin/main` manually — the three footprints are disjoint from the fix, so conflicts are unexpected.

- [ ] **Step 2: Wait for green on all three**

```powershell
foreach ($n in 191,192,194) { Write-Host "== PR $n =="; gh pr checks $n --repo CharlesHoskinson/russellian-book-suite | Select-String -Pattern 'fail|pending' }
```
Re-run until no `fail`/`pending` lines (besides `budget-check  skipping`). Any `fail` → STOP, fetch the job log, diagnose before merging anything.

- [ ] **Step 3: Merge in order 191 → 192 → 194**

```powershell
foreach ($n in 191,192,194) { gh pr merge $n --repo CharlesHoskinson/russellian-book-suite --merge --delete-branch }
```

- [ ] **Step 4: QA gate — dispatch a read-only auditor subagent**

Checklist:
1. `gh pr view <n> --json state,mergedAt` shows `MERGED` for 191, 192, 194.
2. After `git fetch origin`, `git ls-tree origin/main --name-only` contains: `skills/russellian-style/scripts/lint_footnotes.py`, `skills/russellian-style/scripts/lint_ai_staccato.py` (191); `skills/book-knowledge/scripts/source_substance.py`, `skills/book-knowledge/tests/fixtures/stub_source.md` (192); `skills/scrapling-fetch/scripts/session.py` with the PR's changes (194 — verify via `git log -1 origin/main -- skills/scrapling-fetch/scripts/session.py` touching the merge).
3. The post-merge main CI run is green (or still running with no failures yet — if running, wait).
4. Remote branches `add-russellian-linters`, `add-book-knowledge-substance`, `add-scrapling-session` are deleted.

---

## Task 5: Phase 2 — lazy sibling_skills imports on add-syntopical-v0.3 (TDD)

**Files:**
- Modify: the six scripts listed in File Structure
- Create: `skills/syntopical-metabook/tests/unit/test_smoke_import.py`

- [ ] **Step 1: Check out the PR branch and update it from main**

```powershell
git -C C:\russellian-book-suite checkout add-syntopical-v0.3
git -C C:\russellian-book-suite fetch origin
git -C C:\russellian-book-suite merge origin/main -m "Merge main (windows-canary fix + phase-1 merges)"
```
Expected: clean merge (syntopical's footprint is disjoint from phases 0–1). Conflicts → STOP and reconcile by hand.

- [ ] **Step 2: Confirm the venv reproduces the CI failure (RED)**

The skill venv does NOT have `sibling_skills` installed (tests get it via conftest sys.path injection, which `python -c` bypasses — exactly like CI):

```powershell
cd C:\russellian-book-suite\skills\syntopical-metabook
.venv\Scripts\python.exe -c "import sibling_skills" 2>&1
.venv\Scripts\python.exe -c "import skill_api; print('import OK', skill_api.API_VERSION)" 2>&1
```
Expected: BOTH fail with `ModuleNotFoundError: No module named 'sibling_skills'`. If the first import unexpectedly succeeds, the venv has the package installed and this simulation is vacuous — note it and rely on the grep check (Step 6) + CI instead.

- [ ] **Step 3: Write the failing regression test**

Create `skills/syntopical-metabook/tests/unit/test_smoke_import.py`:

```python
"""CI import-smoke regression guard.

The CI smoke leg runs `python -c "import skill_api"` from the skill dir with
only the base package installed — no repo-root sys.path injection, so the
sibling_skills package is unavailable. skill_api's public surface must import
without it (loaders are lazy; they resolve siblings at call time).
"""
from __future__ import annotations
import os
import subprocess
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[2]


def test_skill_api_imports_without_sibling_skills():
    env = {**os.environ, "PYTHONPATH": ""}
    probe = subprocess.run(
        [sys.executable, "-c", "import sibling_skills"],
        cwd=SKILL_ROOT, env=env, capture_output=True, text=True,
    )
    if probe.returncode == 0:
        import pytest
        pytest.skip("sibling_skills importable in this interpreter; simulation vacuous")
    result = subprocess.run(
        [sys.executable, "-c", "import skill_api; print(skill_api.API_VERSION)"],
        cwd=SKILL_ROOT, env=env, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
```

- [ ] **Step 4: Run it — must FAIL**

```powershell
.venv\Scripts\python.exe -m pytest tests/unit/test_smoke_import.py -q
```
Expected: 1 failed, stderr in the assertion message showing `ModuleNotFoundError: No module named 'sibling_skills'`.

- [ ] **Step 5: Apply the lazy-import edit to all six scripts**

In each file, DELETE the module-level line `from sibling_skills import load_skill_api`, and ADD the same line as the first statement inside every function that calls `load_skill_api`. Exact sites:

`scripts/acquire/expand_seeds.py` — delete line 11; in `_fetch_neighbors` add the import before the `sf = load_skill_api("scrapling-fetch", expected_major=0)` line (~line 33).

`scripts/acquire/download_and_ingest.py` — delete line 11; calls sit at ~lines 32/36/40 — read the file, identify each enclosing function, add the import as its first statement (once per function, even if it calls the loader twice).

`scripts/gap/coverage_report.py` — delete line 5; the two wrappers become:

```python
def _load_book_knowledge():
    from sibling_skills import load_skill_api
    return load_skill_api("book-knowledge", expected_major=0)


def _load_book_thesis():
    from sibling_skills import load_skill_api
    return load_skill_api("book-thesis", expected_major=0)
```

`scripts/synthesize/topic_map.py` — delete line 6; same two-wrapper edit as coverage_report.

`scripts/synthesize/disputed_questions.py` — delete line 7; same edit to its `_load_book_knowledge` wrapper.

`scripts/synthesize/concept_reconcile.py` — delete line 6; same edit to its `_load_book_knowledge` wrapper.

(Tests monkeypatch the `_load_*` wrappers, never `load_skill_api` itself — verified — so function-scoped imports do not break any test.)

- [ ] **Step 6: Static check — nothing reachable from skill_api imports sibling_skills at module level**

```powershell
git -C C:\russellian-book-suite grep -n "^from sibling_skills" -- skills/syntopical-metabook
git -C C:\russellian-book-suite grep -n "^import sibling_skills" -- skills/syntopical-metabook
```
Expected: no matches (all remaining `from sibling_skills` lines are indented = function-scoped).

- [ ] **Step 7: Run the regression test — must PASS (GREEN)**

```powershell
.venv\Scripts\python.exe -m pytest tests/unit/test_smoke_import.py -q
```
Expected: 1 passed. Also re-run the raw simulation:
```powershell
.venv\Scripts\python.exe -c "import skill_api; print('import OK', skill_api.API_VERSION)"
```
Expected: `import OK (0, 3)` (or current API_VERSION tuple).

- [ ] **Step 8: Full suite — no regression**

```powershell
.venv\Scripts\python.exe -m pytest tests/ -q
```
Expected: everything green (104 tests: the 103 from the carve work + the new smoke guard). Any failure → diagnose; the lazy-import edit must not change behavior when siblings resolve.

- [ ] **Step 9: Commit and push**

```powershell
git -C C:\russellian-book-suite add skills/syntopical-metabook
git -C C:\russellian-book-suite commit -m "syntopical-metabook: lazy sibling_skills imports; smoke-import regression test"
git -C C:\russellian-book-suite push origin add-syntopical-v0.3
```

---

## Task 6: Phase-2 QA gate and merge #193

**Files:** none.

- [ ] **Step 1: QA gate — dispatch a read-only auditor subagent**

Checklist:
1. `git diff --name-only origin/main add-syntopical-v0.3` adds nothing outside the PR-3 footprint (syntopical-metabook/**, neurosym-forge/**, sibling_skills/{loader.py,tests/}, the 2 syntopical docs) plus the new `tests/unit/test_smoke_import.py` and the merge-from-main commit.
2. The six scripts have no module-level `sibling_skills` import (re-run the grep from Task 5 Step 6).
3. Re-run `tests/unit/test_smoke_import.py` and the full syntopical suite independently — green.
4. No binaries/venv/cache in the new commits.

- [ ] **Step 2: Wait for green on #193**

```powershell
gh pr checks 193 --repo CharlesHoskinson/russellian-book-suite
```
Re-run until clean. The `python-skill (syntopical-metabook / ubuntu-24.04)` import-smoke leg must pass now. Any `fail` → fetch log, diagnose, fix on the branch.

- [ ] **Step 3: Merge**

```powershell
gh pr merge 193 --repo CharlesHoskinson/russellian-book-suite --merge --delete-branch
```

- [ ] **Step 4: Verify main green**

```powershell
git -C C:\russellian-book-suite fetch origin
gh run list --repo CharlesHoskinson/russellian-book-suite --branch main --limit 1
```
Expected: post-merge run success (wait for completion).

---

## Task 7: Phase 3 — B5 reconciliation

**Files:** the five V3 docs (see File Structure), new branch `feat/v3-architecture-docs`.

- [ ] **Step 1: Confirm all four carve slices are on main**

```powershell
git -C C:\russellian-book-suite fetch origin
git -C C:\russellian-book-suite ls-tree origin/main --name-only skills/russellian-style/scripts/lint_footnotes.py skills/book-knowledge/scripts/source_substance.py skills/syntopical-metabook/skill_api.py skills/scrapling-fetch/scripts/session.py
```
Expected: all four paths listed.

- [ ] **Step 2: Cut the parked-docs branch and bring ONLY the five V3 docs**

```powershell
git -C C:\russellian-book-suite checkout -b feat/v3-architecture-docs origin/main
git -C C:\russellian-book-suite checkout feat/rust-axum-v2-architecture -- docs/superpowers/specs/2026-05-31-rust-axum-v2-architecture-design.md docs/superpowers/specs/2026-06-01-rbs-v3-architecture-design.md docs/superpowers/specs/2026-06-01-rbs-v3-skill-migration-plan-design.md docs/superpowers/specs/2026-06-01-rust-microservices-ascii-protocol.md docs/superpowers/specs/2026-06-01-skill-capability-protocol-design.md
```
If any path is missing from the parent, list `git ls-tree feat/rust-axum-v2-architecture --name-only docs/superpowers/specs/` and reconcile — do not guess.

- [ ] **Step 3: Prove the staged set is exactly the five docs**

```powershell
git -C C:\russellian-book-suite diff --cached --name-only origin/main
```
Expected: exactly the 5 paths. Extra paths → unstage them.

- [ ] **Step 4: Commit (no PR — parked)**

```powershell
git -C C:\russellian-book-suite commit -m "Park V3/microservices architecture docs (not ready for main)"
```

- [ ] **Step 5: Uniqueness proofs — the parent holds nothing else**

```powershell
git -C C:\russellian-book-suite diff --stat origin/main feat/rust-axum-v2-architecture -- ":(exclude)docs"
git -C C:\russellian-book-suite diff --name-only origin/main feat/rust-axum-v2-architecture -- docs
```
Expected: first command EMPTY; second lists ONLY the 5 V3 docs (now preserved on `feat/v3-architecture-docs`) and possibly docs that exist on main but not the parent (those appear as main-side adds — verify direction with `--diff-filter` if unsure: `git diff --diff-filter=D --name-only feat/rust-axum-v2-architecture origin/main -- docs` shows what the parent has that main lacks). If ANY non-doc content or unexpected doc is unique to the parent: HALT, report, delete nothing.

- [ ] **Step 6: QA gate — dispatch a read-only auditor subagent**

Checklist:
1. Re-run both uniqueness proofs from Step 5 independently; confirm empty / five-docs-only.
2. `feat/v3-architecture-docs` contains the 5 docs (`git ls-tree feat/v3-architecture-docs --name-only docs/superpowers/specs/ | grep -iE "v3|axum|microservice|capability"`).
3. Confirm `docs/superpowers/specs/2026-06-03-post-185-skill-install-and-branch-carve-design.md` and the two plan docs are on `origin/main` (they landed via Phase 0) — this is the precondition for deleting `plan/post-185-followups`.
4. Confirm `feat/syntopical-metabook-v0.3-generalization` and `feat/feynman-style-skill` have no unique content: for each, `git diff --stat origin/main <branch> -- ":(exclude)docs"` empty AND any doc-side remainder is within the 5 parked docs. Report exact findings.

- [ ] **Step 7: Retire the four local branches (only after a clean QA report)**

```powershell
git -C C:\russellian-book-suite checkout feat/v3-architecture-docs
git -C C:\russellian-book-suite branch -D feat/rust-axum-v2-architecture feat/syntopical-metabook-v0.3-generalization feat/feynman-style-skill plan/post-185-followups
```
Expected: four `Deleted branch` lines. These were never pushed (no remote counterparts) — content is preserved on `main` + `feat/v3-architecture-docs`.

---

## Task 8: Phase 4 — dependabot drain

**Files:** none (PR management). PRs: #179, #180, #181, #182, #186, #187, #188, #189, #190.

- [ ] **Step 1: Trigger rebases (dependabot-native, not update-branch)**

```powershell
foreach ($n in 179,180,181,182,186,187,188,189,190) { gh pr comment $n --repo CharlesHoskinson/russellian-book-suite --body "@dependabot rebase" }
```
Expected: 9 comment URLs. Dependabot force-pushes each branch onto current main within a few minutes.

- [ ] **Step 2: Wait for CI on all nine**

```powershell
foreach ($n in 179,180,181,182,186,187,188,189,190) { $bad = gh pr checks $n --repo CharlesHoskinson/russellian-book-suite 2>$null | Select-String 'fail|pending' | Where-Object { $_ -notmatch 'budget-check' }; Write-Host ("PR {0}: {1}" -f $n, ($bad ? "NOT READY ($($bad.Count))" : 'GREEN')) }
```
Re-run until each PR is `GREEN` or stably failing.

- [ ] **Step 3: Apply the merge rule**

For each GREEN PR:
```powershell
gh pr merge <n> --repo CharlesHoskinson/russellian-book-suite --merge
```
(Dependabot deletes its own branches.) Merge sequentially, re-checking the next PR's freshness — after each merge, dependabot rebases the remainder automatically; if a PR goes stale (`BEHIND`), comment `@dependabot rebase` again and wait.

For each RED PR: fetch the failing job log (`gh run view --job <id> --log-failed`), diagnose briefly. Trivial fix (e.g. a lockfile regen) → apply on the branch via a normal commit and re-wait. Non-trivial (e.g. shadow-cljs 3.x breaks a verifier build) → leave open with a findings comment:
```powershell
gh pr comment <n> --repo CharlesHoskinson/russellian-book-suite --body "<one-paragraph diagnosis: failing job, root cause, what a fix needs>"
```

- [ ] **Step 4: QA gate — dispatch a read-only auditor subagent**

Checklist:
1. For every merged dependabot PR: state `MERGED`, and the post-merge main run is green.
2. For every left-open PR: a findings comment exists and accurately names the failing job.
3. `gh pr list --state open` shows no carve PRs remaining (#191–#194 all merged) — only deliberately-open dependabot PRs (if any) remain.
4. Local repo: `git -C C:\russellian-book-suite status` clean on `feat/v3-architecture-docs` (except the pre-existing untracked conlang files); `main` fast-forwards cleanly.

---

## Task 9: Wrap-up

**Files:** scratchpad + memory updates (outside repo).

- [ ] **Step 1: Sync local main**

```powershell
git -C C:\russellian-book-suite checkout main
git -C C:\russellian-book-suite pull --ff-only origin main
```

- [ ] **Step 2: Record final state**

Scratchpad `context` entry: phases 0–4 outcomes, merged PR numbers, any dependabot PRs left open with reasons, branch inventory after retirement. Update memory `project_post185_carve.md`: arc complete (or note residue), V3 docs now parked on `feat/v3-architecture-docs` so the local-branch GOTCHA is resolved.

- [ ] **Step 3: Report to user**

Merged PRs with numbers; main CI status; parked-docs branch SHA + file list; retired branches; dependabot scoreboard (merged / left-open with one-line reasons).

---

## Self-Review Notes

- **Spec coverage:** Phase 0 → Tasks 1–3; Phase 1 → Task 4; Phase 2 → Tasks 5–6; Phase 3 → Task 7; Phase 4 → Task 8; QA discipline → the QA-gate step in Tasks 3, 4, 6, 7, 8. Out-of-scope items untouched.
- **The 05-21 failure mode** (pytestmark before `import pytest`) is called out at the exact step where it could recur (Task 2 Step 1) with a mechanical verification (Task 2 Step 2).
- **TDD:** the #193 fix has a genuine red/green cycle (Task 5 Steps 2–4 red, 5–7 green) plus a durable regression test that self-skips if the simulation ever becomes vacuous.
- **Halt conditions:** every irreversible action (merge, branch deletion) sits behind an explicit green/empty check; Phase 3 deletes nothing on a non-empty proof.
- **Dependabot freshness:** Task 8 Step 3 handles the rebase churn that sequential merges cause.
