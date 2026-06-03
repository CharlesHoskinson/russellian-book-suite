# Post-#185 follow-ups Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Install the two new skills as `~/.claude/skills` junctions, then carve the four ready slices off `feat/rust-axum-v2-architecture` into scoped PRs to `main` and reconstruct the parent down to the parked V3 docs.

**Architecture:** Pure release/branch management of already-written, already-tested work. Part A (junctions) is independent and runs now. Part B (four scoped PRs + reconciliation) is gated on PR #185 merging; each PR is cut off updated `origin/main`, brings one slice's files, is verified against its affected test suite(s), passes a read-only QA audit, then is pushed and opened. Reconciliation reconstructs (does not rebase) the parent branch.

**Tech Stack:** git, GitHub (`gh`), PowerShell (junctions), per-skill `.venv` pytest. No application code is written.

**Spec:** `docs/superpowers/specs/2026-06-03-post-185-skill-install-and-branch-carve-design.md`

**Conventions:**
- Repo root: `C:\russellian-book-suite`. Parent branch with the source work: `feat/rust-axum-v2-architecture` (referred to below as `$P`).
- Per-skill tests run under that skill's own venv: `cd skills/<name> && .venv/Scripts/python.exe -m pytest tests/ -q`.
- Commit style: terse, imperative, no AI attribution.
- "QA audit" = dispatch the read-only auditor(s) described in the spec's *QA discipline* section (scope/leakage + affected-suite tests + regression) BEFORE pushing. Nothing is pushed until the audit is clean.
- Branch naming for PRs: `add-russellian-linters`, `add-book-knowledge-substance`, `add-syntopical-v0.3`, `add-scrapling-session`.

---

## File Structure (what each PR touches)

```
PR1 add-russellian-linters
  skills/russellian-style/scripts/lint_footnotes.py        (new)
  skills/russellian-style/scripts/lint_ai_staccato.py      (new)
  skills/russellian-style/tests/test_lint_footnotes.py     (new)
  skills/russellian-style/tests/test_lint_ai_staccato.py   (new)
  skills/russellian-style/assets/russellian-rules.json     (modify)
  skills/russellian-style/SKILL.md                         (modify)
  skills/book-compose/scripts/chapter_contract_check.py    (modify: +3 footnote lines)
  skills/book-compose/assets/chapter-contract.template.yaml(modify)

PR2 add-book-knowledge-substance
  skills/book-knowledge/scripts/source_substance.py        (new)
  skills/book-knowledge/scripts/verify_claim.py            (modify)
  skills/book-knowledge/tests/test_source_substance.py     (new)
  skills/book-knowledge/tests/fixtures/stub_source.md      (new)

PR3 add-syntopical-v0.3
  skills/syntopical-metabook/**                            (modify/add; 3 deletions)
  skills/neurosym-forge/scripts/forge_cli.py               (modify)
  skills/neurosym-forge/tests/test_forge_cli_meta.py       (new)
  sibling_skills/loader.py                                 (modify)
  sibling_skills/tests/test_loader.py                      (modify)
  docs/superpowers/specs/2026-05-31-syntopical-metabook-v0.3-generalization-design.md (new)
  docs/superpowers/plans/2026-05-31-syntopical-metabook-v0.3-generalization.md         (new)

PR4 add-scrapling-session
  skills/scrapling-fetch/scripts/session.py                (modify)
  skills/scrapling-fetch/tests/unit/test_session.py        (modify)

Reconciliation (feat/v3-architecture-docs)
  docs/superpowers/specs/2026-05-31-rust-axum-v2-architecture-design.md
  docs/superpowers/specs/2026-06-01-rbs-v3-architecture-design.md
  docs/superpowers/specs/2026-06-01-rbs-v3-skill-migration-plan-design.md
  docs/superpowers/specs/2026-06-01-rust-microservices-ascii-protocol.md
  docs/superpowers/specs/2026-06-01-skill-capability-protocol-design.md
```

---

## Task A1: Install skill junctions (Part A — run now, not gated on #185)

**Files:** none committed. Creates `~/.claude/skills/{feynman-style,halmos}` junctions.

- [ ] **Step 1: Confirm the repo is on a branch that has both skill dirs**

Run (PowerShell):
```powershell
git -C C:\russellian-book-suite rev-parse --abbrev-ref HEAD
Test-Path C:\russellian-book-suite\skills\feynman-style\SKILL.md, C:\russellian-book-suite\skills\halmos\SKILL.md
```
Expected: a branch that contains both dirs (e.g. `add-halmos-and-feynman-skills`, or `main` after #185 merges); both `Test-Path` results `True`. If `False`, check out a branch that has the skills first.

- [ ] **Step 2: Confirm the junctions do not already exist**

Run:
```powershell
"feynman-style","halmos" | ForEach-Object { Test-Path "$env:USERPROFILE\.claude\skills\$_" }
```
Expected: `False`, `False`. If `True`, inspect the existing target before recreating.

- [ ] **Step 3: Create the two junctions**

Run:
```powershell
New-Item -ItemType Junction -Path "$env:USERPROFILE\.claude\skills\feynman-style" -Target "C:\russellian-book-suite\skills\feynman-style"
New-Item -ItemType Junction -Path "$env:USERPROFILE\.claude\skills\halmos" -Target "C:\russellian-book-suite\skills\halmos"
```
Expected: each prints a directory entry for the new junction.

- [ ] **Step 4: Verify junction targets resolve**

Run:
```powershell
"feynman-style","halmos" | ForEach-Object { $t=(Get-Item "$env:USERPROFILE\.claude\skills\$_").Target; "$_ -> $t" }
```
Expected:
```
feynman-style -> C:\russellian-book-suite\skills\feynman-style
halmos -> C:\russellian-book-suite\skills\halmos
```

- [ ] **Step 5: Verify SKILL.md is readable through each junction**

Run:
```powershell
Get-Content "$env:USERPROFILE\.claude\skills\feynman-style\SKILL.md" -TotalCount 3
Get-Content "$env:USERPROFILE\.claude\skills\halmos\SKILL.md" -TotalCount 3
```
Expected: each prints the YAML frontmatter opening (`---`, `name: ...`).

- [ ] **Step 6: Verify each skill's tests run through the junctioned path**

Run:
```powershell
& "$env:USERPROFILE\.claude\skills\feynman-style\.venv\Scripts\python.exe" -m pytest "$env:USERPROFILE\.claude\skills\feynman-style\tests" -q
& "$env:USERPROFILE\.claude\skills\halmos\.venv\Scripts\python.exe" -m pytest "$env:USERPROFILE\.claude\skills\halmos\tests" -q
```
Expected: feynman-style `40 passed`; halmos `29 passed`. (The venv lives in the repo dir and is reached through the junction.)
If pytest can't resolve imports when invoked via the junction path, instead `cd` into the junction dir and run `.venv/Scripts/python.exe -m pytest tests/ -q` — report which form worked.

- [ ] **Step 7: Confirm humanizer (feynman's catalog dependency) is present**

Run:
```powershell
Test-Path "$env:USERPROFILE\.claude\skills\humanizer\SKILL.md"
```
Expected: `True` (humanizer is a real installed dir). If `False`, note it — feynman's `lint_ai_vocabulary` humanizer-catalog branch will be skipped (it degrades gracefully), but flag for the user.

- [ ] **Step 8: Report (no commit)**

Report the resolved targets, the two test counts, and the humanizer presence. No git changes are made by this task.

---

## Task B0: Precondition — #185 merged, main updated (gates all of Part B)

**Files:** none.

- [ ] **Step 1: Confirm PR #185 is merged**

Run:
```bash
gh pr view 185 --json state,mergedAt --jq '.state + " " + (.mergedAt // "not-merged")'
```
Expected: `MERGED <timestamp>`. If `OPEN`, STOP — Part B is blocked until #185 merges. Do Part A and wait.

- [ ] **Step 2: Fetch updated main and confirm it has both skills**

Run:
```bash
cd C:/russellian-book-suite && git fetch origin main
git ls-tree origin/main --name-only skills/ | grep -E "feynman-style|halmos"
```
Expected: both `skills/feynman-style` and `skills/halmos` listed (proves #185 landed).

- [ ] **Step 3: Confirm the parent branch is still present locally**

Run:
```bash
git -C C:/russellian-book-suite branch --list feat/rust-axum-v2-architecture
```
Expected: the branch is listed. It is the source (`$P`) for all four slices.

---

## Task B1: PR 1 — russellian-style linters (+ footnote re-wire)

**Files:** see PR1 block above. This is the only slice that touches a file #185 also changed (`chapter_contract_check.py`); it re-adds the 3 footnote lines that were stripped from #185.

- [ ] **Step 1: Cut the scoped branch off updated main**

```bash
cd C:/russellian-book-suite && git fetch origin main && git checkout -b add-russellian-linters origin/main
```
Expected: `Switched to a new branch 'add-russellian-linters'`.

- [ ] **Step 2: Bring the russellian-style slice files wholesale (all clean adds/mods)**

```bash
git checkout feat/rust-axum-v2-architecture -- \
  skills/russellian-style/scripts/lint_footnotes.py \
  skills/russellian-style/scripts/lint_ai_staccato.py \
  skills/russellian-style/tests/test_lint_footnotes.py \
  skills/russellian-style/tests/test_lint_ai_staccato.py \
  skills/russellian-style/assets/russellian-rules.json \
  skills/russellian-style/SKILL.md
```
Expected: no output (success).

- [ ] **Step 3: Re-apply the footnote wiring to book-compose**

The parent's `chapter_contract_check.py` equals post-#185 main's version PLUS the 3 footnote lines, so bringing it wholesale re-adds exactly the footnote wiring. Also bring the template.

```bash
git checkout feat/rust-axum-v2-architecture -- \
  skills/book-compose/scripts/chapter_contract_check.py \
  skills/book-compose/assets/chapter-contract.template.yaml
```

- [ ] **Step 4: Verify the book-compose delta is ONLY the footnote wiring**

```bash
git --no-pager diff --cached origin/main -- skills/book-compose/scripts/chapter_contract_check.py
```
Expected: exactly three added lines —
```
+    lint_footnotes = load_russellian_style_module("lint_footnotes")
+    footnotes = lint_footnotes.lint_footnotes(draft_path)
+        "footnote_orphan_count":        len(footnotes),
```
If the diff shows anything else (e.g. #185 was changed in review so the halmos/feynman content differs), STOP and reconcile: keep main's halmos+feynman structure and add ONLY the three footnote lines by hand. Do not regress halmos/feynman wiring.

- [ ] **Step 5: Run the affected suites**

```bash
cd skills/russellian-style && .venv/Scripts/python.exe -m pytest tests/ -q; cd ../..
cd skills/book-compose && .venv/Scripts/python.exe -m pytest tests/ -q; cd ../..
```
Expected: russellian-style all green (including `test_lint_footnotes` and `test_lint_ai_staccato`). book-compose: all green EXCEPT the known pre-existing `test_persona_review_pass::test_run_panel_returns_verdict_dict` (1 failed) — verify it is pre-existing with `git --no-pager diff --stat origin/main HEAD -- skills/book-compose/scripts/persona_review_pass.py skills/review-conductor` (empty = unchanged from main = not a regression). Any OTHER failure is a real regression — fix before continuing.

- [ ] **Step 6: QA audit (read-only) before push**

Dispatch a read-only auditor: confirm (a) `git diff --name-only origin/main HEAD` lists ONLY the 8 PR1 files; (b) no `*.pdf`/`.venv`/`__pycache__`/`egg-info` committed; (c) the book-compose diff is only the 3 footnote lines; (d) russellian tests green + book-compose's only failure is the pre-existing persona one (empty-diff proof). Proceed only if clean.

- [ ] **Step 7: Commit and push**

```bash
cd C:/russellian-book-suite
git add skills/russellian-style skills/book-compose/scripts/chapter_contract_check.py skills/book-compose/assets/chapter-contract.template.yaml
git commit -m "Add russellian-style footnote + ai-staccato linters; wire footnote_orphan_count into book-compose gate"
git push -u origin add-russellian-linters
```

- [ ] **Step 8: Open the PR**

```bash
gh pr create --base main --head add-russellian-linters --title "Add russellian-style footnote + ai-staccato linters" --body "Adds lint_footnotes (footnote-integrity) and lint_ai_staccato (antithesis-cadence) to russellian-style, and wires footnote_orphan_count into book-compose's chapter gate. Tests: russellian-style suite green; book-compose green (1 pre-existing unrelated persona-test failure, byte-identical to main)."
```
Expected: prints the PR URL.

---

## Task B2: PR 2 — book-knowledge improvements

**Files:** see PR2 block. Self-contained.

- [ ] **Step 1: Cut the scoped branch**

```bash
cd C:/russellian-book-suite && git fetch origin main && git checkout -b add-book-knowledge-substance origin/main
```

- [ ] **Step 2: Bring the slice files**

```bash
git checkout feat/rust-axum-v2-architecture -- \
  skills/book-knowledge/scripts/source_substance.py \
  skills/book-knowledge/scripts/verify_claim.py \
  skills/book-knowledge/tests/test_source_substance.py \
  skills/book-knowledge/tests/fixtures/stub_source.md
```

- [ ] **Step 3: Run the affected suite**

```bash
cd skills/book-knowledge && .venv/Scripts/python.exe -m pytest tests/ -q; cd ../..
```
Expected: all green (including `test_source_substance`). If book-knowledge has no venv, create one mirroring its pyproject (`py -3.13 -m venv .venv; .venv/Scripts/python.exe -m pip install -e .[dev]`) and report.

- [ ] **Step 4: QA audit (read-only)**

Confirm `git diff --name-only origin/main HEAD` lists ONLY the 4 PR2 files; no binaries/venv/cache; book-knowledge suite green. Proceed only if clean.

- [ ] **Step 5: Commit, push, PR**

```bash
git add skills/book-knowledge
git commit -m "Add book-knowledge source_substance scoring and verify_claim PDF layout-repair fallback"
git push -u origin add-book-knowledge-substance
gh pr create --base main --head add-book-knowledge-substance --title "Add book-knowledge source-substance scoring + verify_claim PDF fallback" --body "Self-contained book-knowledge additions: source_substance.py scoring + verify_claim layout-repair PDF fallback / per-doc extraction cache, with tests."
```
Expected: prints the PR URL.

---

## Task B3: PR 3 — syntopical-metabook v0.3 (handles deletions)

**Files:** see PR3 block. Largest slice; includes 3 DELETIONS and the top-level loader fix.

- [ ] **Step 1: Cut the scoped branch**

```bash
cd C:/russellian-book-suite && git fetch origin main && git checkout -b add-syntopical-v0.3 origin/main
```

- [ ] **Step 2: Bring the directories wholesale (adds + modifications)**

```bash
git checkout feat/rust-axum-v2-architecture -- \
  skills/syntopical-metabook \
  skills/neurosym-forge \
  sibling_skills/loader.py \
  sibling_skills/tests/test_loader.py \
  docs/superpowers/specs/2026-05-31-syntopical-metabook-v0.3-generalization-design.md \
  docs/superpowers/plans/2026-05-31-syntopical-metabook-v0.3-generalization.md
```
Note: `git checkout <tree> -- <dir>` adds/updates files present in the parent tree but does NOT remove files that the parent deleted. Handle deletions in Step 3.

- [ ] **Step 3: Apply the parent's deletions (the conformance re-theme + removed example schools)**

```bash
git rm -q \
  skills/syntopical-metabook/tests/conformance/test_epochpoet_governance.py \
  skills/syntopical-metabook/tests/fixtures/workspaces/three-schools/syntopical/schools/algorand.edn \
  skills/syntopical-metabook/tests/fixtures/workspaces/three-schools/syntopical/schools/praos.edn
```
Expected: three `rm` confirmations. (These were removed on the parent when the conformance test was re-themed from epochpoet-specific to neutral; the new `test_neutral_workspace.py` + `neutral-conformance` fixtures arrive via Step 2.)

- [ ] **Step 4: Confirm the branch matches the parent's syntopical/neurosym/loader state exactly**

```bash
git add -A skills/syntopical-metabook skills/neurosym-forge sibling_skills
git --no-pager diff --stat feat/rust-axum-v2-architecture -- skills/syntopical-metabook skills/neurosym-forge sibling_skills
```
Expected: EMPTY (the branch's tree for these paths now equals the parent's — no missed add or stale delete). If non-empty, reconcile the listed files.

- [ ] **Step 5: Run the affected suites**

```bash
cd skills/syntopical-metabook && .venv/Scripts/python.exe -m pytest tests/ -q; cd ../..
cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest tests/ -q 2>/dev/null || echo "neurosym-forge: check venv/test layout"; cd ../..
.venv-or-runner for sibling_skills: run its loader test the way the repo runs sibling_skills tests (e.g. from repo root: a python with the package importable). Confirm sibling_skills/tests/test_loader.py passes.
```
Expected: syntopical-metabook suite green (governance, conformance `test_neutral_workspace`, staleness, constraints reader); neurosym-forge meta test green; sibling_skills loader test green. Investigate any failure before continuing.

- [ ] **Step 6: QA audit (read-only)**

Confirm `git diff --name-only origin/main HEAD` lists ONLY syntopical-metabook/**, neurosym-forge/**, sibling_skills/{loader.py,tests/test_loader.py}, and the 2 syntopical docs; the 3 deletions are present (status `D` for the epochpoet test + algorand/praos edn); no binaries/venv/cache; suites green. Proceed only if clean.

- [ ] **Step 7: Commit, push, PR**

```bash
git commit -m "Add syntopical-metabook v0.3: domain-neutral governance, acquire/synthesize, neurosym-forge meta, loader fix"
git push -u origin add-syntopical-v0.3
gh pr create --base main --head add-syntopical-v0.3 --title "syntopical-metabook v0.3 generalization" --body "Domain-neutral governance (constraints.edn-driven), acquire/synthesize pipelines, neurosym-forge meta subcommands, conformance re-theme (epochpoet -> neutral workspace), and the sibling_skills loader fix. Tests: syntopical-metabook + neurosym-forge + sibling_skills loader green."
```
Expected: prints the PR URL.

---

## Task B4: PR 4 — scrapling-fetch session

**Files:** see PR4 block. Small, self-contained.

- [ ] **Step 1: Cut the scoped branch**

```bash
cd C:/russellian-book-suite && git fetch origin main && git checkout -b add-scrapling-session origin/main
```

- [ ] **Step 2: Bring the slice files**

```bash
git checkout feat/rust-axum-v2-architecture -- \
  skills/scrapling-fetch/scripts/session.py \
  skills/scrapling-fetch/tests/unit/test_session.py
```

- [ ] **Step 3: Run the affected suite**

```bash
cd skills/scrapling-fetch && .venv/Scripts/python.exe -m pytest tests/ -q; cd ../..
```
Expected: scrapling-fetch suite green (live tests may skip without network — that is acceptable; unit/test_session must pass).

- [ ] **Step 4: QA audit (read-only)**

Confirm `git diff --name-only origin/main HEAD` lists ONLY the 2 PR4 files; no binaries/venv/cache; suite green. Proceed only if clean.

- [ ] **Step 5: Commit, push, PR**

```bash
git add skills/scrapling-fetch
git commit -m "Update scrapling-fetch session handling"
git push -u origin add-scrapling-session
gh pr create --base main --head add-scrapling-session --title "scrapling-fetch session update" --body "Self-contained change to scrapling-fetch session handling with its unit test."
```
Expected: prints the PR URL.

---

## Task B5: Reconciliation — reconstruct feat/v3-architecture-docs, retire the parent

**Files:** the 5 V3 docs (see Reconciliation block). Gated on PRs 1–4 all merged.

- [ ] **Step 1: Confirm PRs 1–4 are merged**

```bash
for b in add-russellian-linters add-book-knowledge-substance add-syntopical-v0.3 add-scrapling-session; do
  echo -n "$b: "; gh pr list --head "$b" --state merged --json number --jq '.[0].number // "NOT MERGED"';
done
```
Expected: each prints a merged PR number. If any is `NOT MERGED`, STOP — reconciliation waits until all four land.

- [ ] **Step 2: Verify main now carries all four slices**

```bash
cd C:/russellian-book-suite && git fetch origin main
git ls-tree origin/main --name-only skills/russellian-style/scripts/lint_footnotes.py skills/book-knowledge/scripts/source_substance.py skills/syntopical-metabook/scripts/governance/_constraints.py skills/scrapling-fetch/scripts/session.py
```
Expected: all four representative files listed (proves the slices merged).

- [ ] **Step 3: Cut the V3-docs branch off updated main and bring ONLY the V3 docs**

```bash
git checkout -b feat/v3-architecture-docs origin/main
git checkout feat/rust-axum-v2-architecture -- \
  docs/superpowers/specs/2026-05-31-rust-axum-v2-architecture-design.md \
  docs/superpowers/specs/2026-06-01-rbs-v3-architecture-design.md \
  docs/superpowers/specs/2026-06-01-rbs-v3-skill-migration-plan-design.md \
  docs/superpowers/specs/2026-06-01-rust-microservices-ascii-protocol.md \
  docs/superpowers/specs/2026-06-01-skill-capability-protocol-design.md
```

- [ ] **Step 4: Confirm NOTHING beyond the V3 docs differs from main**

```bash
git add -A docs && git --no-pager diff --cached --name-only origin/main
```
Expected: exactly the 5 V3 doc paths, nothing else. If other paths appear, unstage them — only the V3 docs belong here.

Also double-check no additional V3/microservices doc was missed:
```bash
git --no-pager diff --name-only origin/main feat/rust-axum-v2-architecture -- docs | grep -iE "v3|microservice|capability|axum-v2"
```
Expected: the same 5 files (all now staged). If extra files appear, add them in Step 3.

- [ ] **Step 5: Commit the parked V3 docs (no PR — not ready)**

```bash
git commit -m "Park V3/microservices architecture docs (not yet ready for main)"
```
Do NOT open a PR — this branch is the parked home of the not-ready V3 work.

- [ ] **Step 6: Verify the parent's only remaining unique content was the V3 docs, then retire it**

```bash
git --no-pager diff --stat origin/main feat/rust-axum-v2-architecture -- ':(exclude)docs'
```
Expected: EMPTY (every non-doc change on the parent has now reached main via #185 + PRs 1–4). If non-empty, a slice was missed — investigate before deleting anything.

Once Step 6 is empty AND `feat/v3-architecture-docs` is confirmed to hold the V3 docs:
```bash
git checkout feat/v3-architecture-docs
git branch -D feat/rust-axum-v2-architecture
```
(Use `-D`; the branch's content is preserved in `main` + `feat/v3-architecture-docs`.) If `feat/rust-axum-v2-architecture` was ever pushed and you want the remote tidy, optionally `git push origin --delete feat/rust-axum-v2-architecture` — confirm with the user first (remote deletion).

- [ ] **Step 7: Report**

Report: the 4 merged PR numbers, that main carries all four slices, the new `feat/v3-architecture-docs` branch SHA + its file list, and confirmation the old parent branch was retired with nothing lost.

---

## Self-Review Notes (completed during planning)

- **Spec coverage:** Part A → Task A1 (all 8 verification steps incl. humanizer). Part B four PRs → B1–B4; reconciliation → B5; precondition gating → B0. QA discipline → the "QA audit" step in each of B1–B4. Out-of-scope V3 docs → parked in B5, never PR'd.
- **Exact paths:** every file path is enumerated from the actual `git diff` against the parent (no globs except the deliberate `skills/syntopical-metabook` directory checkout in B3, whose deletions are handled explicitly in B3 Step 3).
- **Deletion handling:** B3 Step 3 `git rm`s the three files the parent deleted (epochpoet conformance test + algorand/praos schools); B3 Step 4 proves the tree matches the parent exactly.
- **Footnote re-wire correctness:** B1 Step 4 asserts the book-compose delta is exactly the 3 footnote lines and halts if #185 diverged in review.
- **Ordering:** B0 gates all of Part B on #185; B5 gates on B1–B4; B1–B4 are mutually independent (disjoint footprints), so they may run in any order or in parallel.
- **No placeholders:** every step has exact commands + expected output. The one soft spot — running the `sibling_skills` loader test (B3 Step 5) — names the file to run and says to use the repo's existing method; if the executor finds no venv for a skill (book-knowledge B2, neurosym/sibling_skills B3), the step says to create/locate it and report rather than guess.
