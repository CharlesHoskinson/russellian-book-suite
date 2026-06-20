# HFR v2 PR Reconciliation & Landing — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax. **This is a git/ops runbook, not a code plan** — steps are exact commands with expected output. Three steps are **GATES** marked ⛔ that require explicit human approval before running (pushing `main`, merging the PR) or are external waits (CI). Do not run a ⛔ step without the operator's go-ahead.

**Goal:** Reconcile the HFR v2 feature branch `hfr-v2-liveliness` (PR #262) with current `main` and land it as one PR with the full CI matrix green, losing no work from either side.

**Architecture:** Merge `origin/main` into the branch (one merge commit), resolve the only 2 conflicts by taking the branch's verified-superset versions, verify the merged tree structurally + run the locally-feasible suites, then push so #262 is conflict-free and let CI be the authoritative comprehensive gate before merging.

**Tech Stack:** git, GitHub CLI (`gh`), per-skill Python venvs (3.14), spaCy `en_core_web_sm` (for the voice suites; best-effort locally, gated by CI).

**Spec:** `docs/superpowers/specs/2026-06-20-hfr-v2-pr-reconciliation-design.md`.

**Working directory:** `c:\russellian-book-suite` (a normal clone, not a worktree). All `git`/`gh` run from there.

---

## Pre-flight facts (verified 2026-06-20, re-confirm in Task 1)

- Current branch: `hfr-v2-liveliness` @ `ebf1f44` (15 voice-eval commits + the reconciliation design doc); working tree clean.
- `origin/main` @ `e5683be`. Local `main` @ `0d10513` = `e5683be` + 2 bermuda re-bake commits (`0952562`, `0d10513`), **unpushed**.
- Merge-base of `main` and the branch: `52632ec`.
- Trial merge of `main` into the branch conflicts in exactly 2 files, both `add/add`, both branch-superset:
  `skills/liveliness-signals/pyproject.toml`, `skills/liveliness-signals/skill_api.py`.

---

## Task 1: Pre-flight verification + land the bermuda commits on `origin/main`

**Goal:** confirm the starting state and (recommended) push the 2 already-done bermuda commits to `origin/main` first, so #262 stays purely HFR v2.

- [ ] **Step 1: Confirm clean starting state**

```bash
cd /c/russellian-book-suite
git status -sb
git rev-parse --abbrev-ref HEAD          # expect: hfr-v2-liveliness
git fetch origin
```
Expected: working tree clean; on `hfr-v2-liveliness`.

- [ ] **Step 2: Confirm the 2 local-main commits are exactly the bermuda re-bake**

```bash
git --no-pager log --oneline origin/main..main
git --no-pager diff --stat origin/main..main
```
Expected: exactly two commits — `0952562 fix(verifiers): rebake bermuda axioms ...` and `0d10513 docs(plans): record booklogic PR-4/PR-5 ...`; the diffstat touches only `verifiers/bermuda/**` and `docs/plans/2026-05-17-booklogic-pr{4,5}.md`. If anything else appears, STOP and report.

- [ ] **Step 3 ⛔ GATE (push `main`): land bermuda on `origin/main`**

This pushes `main`. **Requires operator go-ahead.** If declined, skip to Task 1 Step 4b.

```bash
git push origin main
```
Expected: `e5683be..0d10513  main -> main` (fast-forward).

Then re-fetch so `origin/main` is current locally:
```bash
git fetch origin
git rev-parse --short origin/main         # expect: 0d10513
```

- [ ] **Step 4a (if Step 3 ran): note that the merge base is now `0d10513`** — bermuda will be in #262's base, not its delta. Proceed to Task 2.

- [ ] **Step 4b (only if Step 3 was declined): record the deferral** — the merge in Task 2 will use `origin/main`=`e5683be` (no bermuda); the bermuda fix stays as unpushed local `main` and does NOT land via #262. Note this in the final report. Proceed to Task 2 either way (the 2 liveliness conflicts are identical regardless, since bermuda commits don't touch `liveliness-signals`).

---

## Task 2: Merge `origin/main` into the branch and resolve the 2 conflicts

- [ ] **Step 1: Start the merge (expect 2 conflicts)**

```bash
cd /c/russellian-book-suite
git merge origin/main --no-edit
```
Expected: merge pauses with
`CONFLICT (add/add): Merge conflict in skills/liveliness-signals/pyproject.toml`
`CONFLICT (add/add): Merge conflict in skills/liveliness-signals/skill_api.py`
and a clean auto-merge of `.github/ci/skills-matrix.json`. Confirm the conflict set is exactly those 2 files:
```bash
git diff --name-only --diff-filter=U
```
Expected: exactly the two `skills/liveliness-signals/` files. If any other file conflicts, STOP and report.

- [ ] **Step 2: Resolve both conflicts by taking the branch (ours) superset**

On `hfr-v2-liveliness`, HEAD is "ours" (the branch). The branch versions are verified supersets (pyproject adds `click`/`typer`; skill_api adds `load_profile`/`score_passage`/`SIGNAL_NAMES`).

```bash
git checkout --ours skills/liveliness-signals/pyproject.toml skills/liveliness-signals/skill_api.py
git add skills/liveliness-signals/pyproject.toml skills/liveliness-signals/skill_api.py
```

- [ ] **Step 3: Verify the resolved files are the supersets (not the scaffold)**

```bash
grep -q 'click>=8' skills/liveliness-signals/pyproject.toml && echo "pyproject OK (click present)" || echo "FAIL pyproject"
grep -q 'def score_passage' skills/liveliness-signals/skill_api.py && grep -q 'SIGNAL_NAMES' skills/liveliness-signals/skill_api.py && echo "skill_api OK" || echo "FAIL skill_api"
```
Expected: `pyproject OK (click present)` and `skill_api OK`. If either FAILs, STOP (the wrong side was taken).

- [ ] **Step 4: Complete the merge commit**

```bash
git commit --no-edit
git --no-pager log --oneline -1            # expect a "Merge ... origin/main ..." commit
git status -sb                              # expect clean, ahead of origin/hfr-v2-liveliness
```

---

## Task 3: Merge-correctness structural checks (no tests yet)

Confirm the merged tree is the union of both sides — nothing dropped.

- [ ] **Step 1: Files main brought are present (design-KG + bermuda re-bake)**

```bash
for f in \
  skills/book-knowledge/scripts/project_design_kg.py \
  skills/book-knowledge/scripts/design_kg_queries.py \
  skills/book-knowledge/scripts/live_eval_gate.py \
  skills/book-compose/tests/test_live_warning_surface.py \
  docs/operations/design-intelligence-kg.md \
  openspec/changes/repo-design-intelligence-kg/proposal.md ; do
  test -f "$f" && echo "present: $f" || echo "MISSING: $f"
done
```
Expected: all `present:`. (If `git push origin main` ran in Task 1) also:
```bash
test -f verifiers/bermuda/rules/booklogic-schema.edn && echo "bermuda rebake present" || echo "bermuda rebake ABSENT (expected only if Task 1 Step 3 was declined)"
```

- [ ] **Step 2: Branch feature files survived the merge**

```bash
ls skills/voice-eval/scripts/*.py | wc -l            # expect 12 (11 helpers + __init__)
test -f skills/triadic-voice-v2/scripts/brief.py && echo "triadic-voice-v2 OK"
test -f skills/russellian-style/assets/russellian-rules-v2.json && echo "v2 ruleset OK"
ls skills/liveliness-signals/scripts/signal_*.py | wc -l   # expect 8
```
Expected: `12`, `triadic-voice-v2 OK`, `v2 ruleset OK`, `8`.

- [ ] **Step 3: `skills-matrix.json` is the correct union and valid JSON**

```bash
python -c "import json; d=json.load(open('.github/ci/skills-matrix.json')); s=[x['skill'] for x in d['skills']]; assert s.count('liveliness-signals')==1, 'dup/missing liveliness'; assert 'voice-eval' in s, 'voice-eval missing'; print('matrix OK:', [x for x in s if x in ('liveliness-signals','voice-eval')])"
```
Expected: `matrix OK: ['liveliness-signals', 'voice-eval']` (order may differ). Any AssertionError → STOP.

- [ ] **Step 4: main's CI/dependabot liveliness registration is present**

```bash
grep -q 'liveliness' .github/dependabot.yml && echo "dependabot OK"
grep -qi 'liveliness' .github/workflows/ci.yml && echo "ci.yml OK" || echo "ci.yml: liveliness via matrix only (OK if matrix has it)"
```
Expected: `dependabot OK` (ci.yml mention is informational — the skill runs via the matrix entry confirmed in Step 3).

---

## Task 4: Local verification (the feasible suites)

Run what this machine can without heavy model/Cozo installs; the rest is CI's job (Task 6).

- [ ] **Step 1: voice-eval — must be green**

```bash
cd /c/russellian-book-suite/skills/voice-eval
.venv/Scripts/python.exe -m pytest tests/ -q
.venv/Scripts/python.exe -m ruff check .
```
Expected: `30 passed`; `All checks passed!`. (The venv from the build session persists; if absent, `python -m venv .venv && .venv/Scripts/python.exe -m pip install -e ".[dev]"` first.)

- [ ] **Step 2: triadic-voice-v2 — stdlib, must be green**

```bash
cd /c/russellian-book-suite/skills/triadic-voice-v2
test -d .venv || (python -m venv .venv && .venv/Scripts/python.exe -m pip install -q -e ".[dev]")
.venv/Scripts/python.exe -m pytest tests/ -q
```
Expected: all pass (stdlib helpers; no spaCy).

- [ ] **Step 3: russellian-style + liveliness-signals — best-effort (needs spaCy model)**

```bash
cd /c/russellian-book-suite/skills/liveliness-signals
test -d .venv || python -m venv .venv
.venv/Scripts/python.exe -m pip install -q -e ".[dev]"
.venv/Scripts/python.exe -m spacy download en_core_web_sm   # may need network; if it fails, SKIP this skill locally
.venv/Scripts/python.exe -m pytest tests/ -q
```
Expected: green if the model installs. **If the spaCy model download fails (no network/permission), do NOT treat it as a failure** — record "deferred to CI" and continue. Repeat for `skills/russellian-style` the same way (its suite also needs the model).

- [ ] **Step 4: Record the local result** — note which suites ran green and which were deferred to CI. No commit (read-only verification).

---

## Task 5: Push the reconciled branch and confirm #262 is conflict-free

- [ ] **Step 1: Push the merge (+ the spec/plan docs) to the PR branch**

```bash
cd /c/russellian-book-suite
git push origin hfr-v2-liveliness
```
Expected: fast-forward push of the merge commit + doc commits; no rejection.

- [ ] **Step 2: Confirm the PR is now mergeable**

```bash
gh pr view 262 --json mergeable,mergeStateStatus,baseRefName,headRefName
```
Expected: `"mergeable":"MERGEABLE"` and `baseRefName":"main"`. If `CONFLICTING`, STOP and report (should not happen — the branch now contains `origin/main`).

---

## Task 6 ⛔ GATE (external wait): CI must go green on #262

- [ ] **Step 1: Watch the PR checks**

```bash
gh pr checks 262 --watch
```
Wait for completion. Expected: all required checks `pass` (the python-skill matrix across all skills incl. `liveliness-signals`/`voice-eval`, the design-KG deterministic-contract job, nix preflight, cargo-test, lint/actionlint).

- [ ] **Step 2: If any check is red — triage loop (do not merge)**

```bash
gh pr checks 262          # identify the failing job
gh run view <run-id> --log-failed | tail -120   # read the failure
```
Fix the root cause on the branch (commit + `git push origin hfr-v2-liveliness`), then return to Step 1. Common expected categories and first move:
- A **liveliness-signals / russellian-style** test failure → likely a real interaction between the v2 ruleset and the merged tree; read the assertion, fix in the owning skill.
- A **design-KG** job failure → main's design-KG work expects something the merge changed; reconcile in `book-knowledge`.
- A **lint/ruff/actionlint** failure → fix formatting/config.
Do not proceed to Task 7 until Step 1 shows all-green.

---

## Task 7 ⛔ GATE (merge the PR): land #262 into `main`

**Requires operator go-ahead.** Only after Task 6 is all-green.

- [ ] **Step 1: Merge with a merge commit (preserve the 5-plan history)**

```bash
gh pr merge 262 --merge
```
Expected: PR #262 reported `MERGED`. (Use `--merge`, not `--squash`, to keep the per-plan commits.)

- [ ] **Step 2: Confirm**

```bash
gh pr view 262 --json state,mergedAt
```
Expected: `"state":"MERGED"`.

---

## Task 8: Post-merge cleanup + local reconciliation

- [ ] **Step 1: Fast-forward local `main` to the merged remote**

```bash
cd /c/russellian-book-suite
git checkout main
git fetch origin
git merge --ff-only origin/main
git --no-pager log --oneline -3
```
Expected: local `main` advances to the merge commit; clean.

- [ ] **Step 2: Delete the local feature branch (now merged)**

```bash
git branch -d hfr-v2-liveliness
```
Expected: `Deleted branch hfr-v2-liveliness`. (If git refuses with "not fully merged" because of the merge-commit topology, verify the work is in `origin/main` first, then `git branch -D`.)

- [ ] **Step 3: Delete the remote branch (if `gh` didn't auto-delete on merge)**

```bash
git ls-remote --heads origin hfr-v2-liveliness     # empty if already deleted
git push origin --delete hfr-v2-liveliness 2>/dev/null || echo "already deleted"
```

- [ ] **Step 4: Final confirmation**

```bash
git status -sb                      # on main, up to date with origin/main
git --no-pager log --oneline -1     # the merge commit
```
Record: PR #262 merged, local + remote reconciled, branch removed.

---

## Definition of Done

- `origin/main` contains the full HFR v2 feature (Plans 1–5) + the prior design-KG thread, with no work lost from either side.
- The 2 liveliness conflicts were resolved to the branch supersets; `skills-matrix.json` is the correct union.
- CI was green on #262 before merge; #262 is `MERGED` with a merge commit.
- Local `main` fast-forwarded; feature branch deleted locally and remotely.
- (If Task 1 Step 3 ran) the bermuda re-bake is on `origin/main`; otherwise it's recorded as still-local.

## Human-approval GATES (do not run without go-ahead)

| Step | Action | Why gated |
|---|---|---|
| Task 1 Step 3 | `git push origin main` | Publishes to the default branch |
| Task 6 | wait for CI | External; must be all-green |
| Task 7 Step 1 | `gh pr merge 262 --merge` | Irreversible integration into `main` |
