# CI Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Kill the HuggingFace model-download flake class, guard against zero-marked windows-canary skills at PR time, path-gate the python matrix, and beat the June 16 node24 deadline.

**Architecture:** Five fixes (F1–F5 in the spec), one commit each, on branch `ci/hardening`, landed as a single PR whose own CI run exercises F1 and F3. The canary guard is a new stdlib-only `ci/` linter module following the `lint_no_direct_http` pattern; everything else is workflow/config edits.

**Tech Stack:** GitHub Actions YAML, bash steps, Python 3 stdlib (ci/ package), pytest.

**Spec:** `docs/superpowers/specs/2026-06-03-ci-hardening-design.md`

**Conventions:**
- Repo root `C:\russellian-book-suite`, branch `ci/hardening` (cut from origin/main; spec committed at 1e40abc).
- Commit style: terse, imperative, no AI attribution.
- Line numbers below reference `.github/workflows/ci.yml` at this branch's HEAD — re-verify before each edit; earlier tasks shift later line numbers.
- The `ci/` package has its own venv at `ci/.venv` (Windows: `ci\.venv\Scripts\python.exe`). If pytest is missing there, run ci tests with any python that has pytest (e.g. `py -3.13 -m pytest` after `py -3.13 -m pip install pytest`) — the module under test is stdlib-only.

---

## File Structure

```
Task 1 (F2)  ci/check_windows_canary.py            (new: matrix parse + marker scan + main)
             ci/test_check_windows_canary.py       (new: unit tests)
             .github/workflows/ci.yml              (lint job: add guard to invariant-linters step)
Task 2 (F1)  .github/workflows/ci.yml              (python-skill-matrix: HF cache + warmup steps, pytest env)
             .github/workflows/nightly-flake-drift.yml (windows-full-canary: same for neurosym-forge)
             .github/workflows/ci-legacy.yml        (test-neurosym-forge: same IF it installs semantic)
Task 3 (F3)  .github/workflows/ci.yml              (changes job: python filter + narrowed rust filter;
                                                    python-skill-matrix: needs+if; required: aggregation)
Task 4 (F4)  .github/actions/setup-book-python/action.yml (setup-python v5.6.0 -> v6.2.0)
             .github/dependabot.yml                (new github-actions entry for the composite dir)
Task 5 (F5)  .github/workflows/ci.yml              (concurrency comment)
```

---

## Task 1: F2 — windows-canary zero-marking guard (TDD)

**Files:**
- Create: `ci/check_windows_canary.py`
- Create: `ci/test_check_windows_canary.py`
- Modify: `.github/workflows/ci.yml:43-46` (invariant-linters step in the `lint` job)

- [ ] **Step 1: Confirm branch and ci/ test baseline**

```powershell
git -C C:\russellian-book-suite rev-parse --abbrev-ref HEAD   # expect ci/hardening
cd C:\russellian-book-suite
py -3.13 -m pytest ci/ -q                                      # baseline; record pass count
```
(If `py -3.13` lacks pytest: `py -3.13 -m pip install pytest`.)

- [ ] **Step 2: Write the failing test**

Create `ci/test_check_windows_canary.py`:

```python
"""Tests for ci/check_windows_canary.py (windows-canary zero-marking guard)."""
from __future__ import annotations

import textwrap

from ci.check_windows_canary import full_pytest_matrix_skills, skills_missing_canary

WORKFLOW_FIXTURE = textwrap.dedent(
    """\
    jobs:
      python-skill-matrix:
        strategy:
          matrix:
            os: [ubuntu-24.04, macos-15, windows-2022]
            skill:
              - alpha
              - beta
              - gamma
            include:
              - skill: alpha
                constraints: skills/alpha/constraints.txt
              - skill: delta
                os: ubuntu-24.04
                extra: none
                smoke: import
              - skill: epsilon
                os: ubuntu-24.04
                smoke: import
    """
)


def test_parses_skill_axis_and_excludes_smoke_rows():
    skills = full_pytest_matrix_skills(WORKFLOW_FIXTURE)
    # axis skills run full pytest on Windows; smoke-only include rows do not
    assert skills == {"alpha", "beta", "gamma"}


def test_missing_canary_detection(tmp_path):
    skills_dir = tmp_path / "skills"
    # alpha: marked test -> ok
    a = skills_dir / "alpha" / "tests"
    a.mkdir(parents=True)
    (a / "test_x.py").write_text(
        "import pytest\npytestmark = pytest.mark.windows_canary\n", encoding="utf-8"
    )
    # beta: tests exist but none marked -> flagged
    b = skills_dir / "beta" / "tests"
    b.mkdir(parents=True)
    (b / "test_y.py").write_text("def test_y():\n    assert True\n", encoding="utf-8")
    # gamma: decorator-style marker in a subdir -> ok
    g = skills_dir / "gamma" / "tests" / "unit"
    g.mkdir(parents=True)
    (g / "test_z.py").write_text(
        "import pytest\n@pytest.mark.windows_canary\ndef test_z():\n    assert True\n",
        encoding="utf-8",
    )
    missing = skills_missing_canary({"alpha", "beta", "gamma"}, skills_dir)
    assert missing == ["beta"]


def test_real_workflow_parses_and_repo_is_clean():
    # The guard must hold on the actual repo: parse the real ci.yml and
    # confirm every full-pytest matrix skill has at least one marked test.
    from ci.check_windows_canary import REPO_ROOT, WORKFLOW_PATH

    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    skills = full_pytest_matrix_skills(text)
    assert "neurosym-forge" in skills and "paragraph-weaver" in skills
    assert "syntopical-metabook" not in skills  # smoke-only row
    assert skills_missing_canary(skills, REPO_ROOT / "skills") == []
```

- [ ] **Step 3: Run it — must FAIL (module does not exist)**

```powershell
py -3.13 -m pytest ci/test_check_windows_canary.py -q
```
Expected: collection error `ModuleNotFoundError: No module named 'ci.check_windows_canary'`.

- [ ] **Step 4: Write the implementation**

Create `ci/check_windows_canary.py`:

```python
"""Windows-canary zero-marking guard.

The python-skill matrix runs `pytest -m windows_canary` on Windows. A matrix
skill whose tests/ contains zero windows_canary marks makes pytest exit 5
(no tests collected), reddening ci-required on every PR (the 2026-06-03
paragraph-weaver incident). This guard fails the cheap lint job instead,
naming the skill and the fix.

Smoke-only matrix rows (`smoke: import`) never run pytest and are exempt.

Run as a check:  python -m ci.check_windows_canary   (exits non-zero on violations)
Tested by:       ci/test_check_windows_canary.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "ci.yml"

_MARKER_RE = re.compile(r"pytest\.mark\.windows_canary|pytestmark\s*=.*windows_canary")


def full_pytest_matrix_skills(workflow_text: str) -> set[str]:
    """Skills on the matrix `skill:` axis (full pytest on Windows).

    Include-only rows are added by `include:` entries; any row carrying
    `smoke: import` is exempt (and removed even if it also sits on the axis).
    """
    lines = workflow_text.splitlines()
    axis: set[str] = set()
    in_skill_axis = False
    skill_indent = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if re.match(r"^skill:\s*$", stripped):
            in_skill_axis = True
            skill_indent = len(line) - len(line.lstrip())
            continue
        if in_skill_axis:
            indent = len(line) - len(line.lstrip())
            m = re.match(r"^-\s*([A-Za-z0-9_-]+)\s*$", stripped)
            if m and indent > skill_indent:
                axis.add(m.group(1))
                continue
            if stripped and indent <= skill_indent:
                in_skill_axis = False
    # Collect smoke-only skills from include rows: a `- skill: X` bullet whose
    # following sibling keys (same indent, until the next `- `) contain
    # `smoke: import`.
    smoke: set[str] = set()
    for i, line in enumerate(lines):
        m = re.match(r"^(\s*)-\s*skill:\s*([A-Za-z0-9_-]+)\s*$", line)
        if not m:
            continue
        row_indent, skill = len(m.group(1)), m.group(2)
        for j in range(i + 1, len(lines)):
            nxt = lines[j]
            if not nxt.strip():
                continue
            nxt_indent = len(nxt) - len(nxt.lstrip())
            if nxt_indent <= row_indent or nxt.lstrip().startswith("- "):
                break
            if re.match(r"^smoke:\s*import\s*$", nxt.strip()):
                smoke.add(skill)
                break
    return axis - smoke


def skills_missing_canary(skills: set[str], skills_dir: Path) -> list[str]:
    """Skills whose tests/ tree contains no windows_canary marker."""
    missing: list[str] = []
    for skill in sorted(skills):
        tests_dir = skills_dir / skill / "tests"
        marked = any(
            _MARKER_RE.search(p.read_text(encoding="utf-8", errors="replace"))
            for p in tests_dir.rglob("test_*.py")
        ) if tests_dir.is_dir() else False
        if not marked:
            missing.append(skill)
    return missing


def main() -> int:
    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    skills = full_pytest_matrix_skills(text)
    if not skills:
        print("check_windows_canary: parsed ZERO matrix skills from ci.yml — parser drift; failing closed")
        return 1
    missing = skills_missing_canary(skills, REPO_ROOT / "skills")
    if missing:
        for skill in missing:
            print(
                f"skills/{skill}/tests has NO windows_canary-marked test. The Windows "
                f"matrix leg runs `pytest -m windows_canary` and will exit 5 (no tests "
                f"collected). Fix: add `import pytest` + `pytestmark = pytest.mark."
                f"windows_canary` to its test files (see skills/feynman-style/tests for "
                f"the pattern) and register the marker in pyproject.toml."
            )
        return 1
    print(f"check_windows_canary: OK ({len(skills)} matrix skills all have marked tests)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Run the tests — must PASS, then mutation-check**

```powershell
py -3.13 -m pytest ci/test_check_windows_canary.py -q     # expect 3 passed
py -3.13 -m ci.check_windows_canary                        # expect OK line, exit 0
```
Mutation check (proves the guard bites): temporarily rename `skills/paragraph-weaver/tests/test_argument.py`'s `pytestmark` line (e.g. sed to `pytestmark_X`)… simpler: run with a doctored skills dir is already covered by `test_missing_canary_detection`. Skip live mutation; the unit test covers it.

- [ ] **Step 6: Run the full ci/ suite (no regression) and wire into the lint job**

```powershell
py -3.13 -m pytest ci/ -q    # baseline count + 3 new
```

In `.github/workflows/ci.yml`, extend the invariant-linters step (lines 43–46):

```yaml
      - name: invariant linters (NFR-4 no-direct-http, NFR-5 no-shadow-writes, windows-canary guard, ci tests)
        run: |
          nix develop -c python -m ci.lint_no_direct_http
          nix develop -c python -m ci.check_windows_canary
          nix develop -c python -m pytest ci/ -q
```

- [ ] **Step 7: Commit**

```powershell
git -C C:\russellian-book-suite add ci/check_windows_canary.py ci/test_check_windows_canary.py .github/workflows/ci.yml
git -C C:\russellian-book-suite commit -m "ci: guard against zero windows_canary marks per matrix skill (lint-time)"
```

---

## Task 2: F1 — HF model cache + offline mode

**Files:**
- Modify: `.github/workflows/ci.yml` (python-skill-matrix steps, after the spaCy install step ~line 250; pytest step env ~line 260)
- Modify: `.github/workflows/nightly-flake-drift.yml` (windows-full-canary job)
- Modify: `.github/workflows/ci-legacy.yml` (test-neurosym-forge — conditional, see Step 3)

- [ ] **Step 1: Add cache + warmup steps to python-skill-matrix**

Insert AFTER the `install spaCy model` step (ends ~line 250) and BEFORE `import smoke`:

```yaml
      # neurosym-forge's semantic-index tests load the all-MiniLM-L6-v2
      # sentence-transformers model. Without a persisted cache every xdist
      # worker revalidates per-file metadata against huggingface.co (HEAD
      # requests); parallel workers trip HF Hub's 429 rate limit and the
      # semantic tests fail or hang (#192/#194/#197/#203, all 2026-06-03).
      # Cache the model keyed on its pinned name, warm it once per run on a
      # miss, then run pytest with HF_HUB_OFFLINE=1 so no leg touches the
      # network for the model. Key is OS-scoped: the HF cache uses symlinks
      # on Linux/macOS but copies on Windows.
      - name: cache HF model (all-MiniLM-L6-v2)
        if: matrix.skill == 'neurosym-forge'
        uses: actions/cache@27d5ce7f107fe9357f9df03efb73ab90386fccae # v5.0.5
        with:
          path: hf-cache
          key: hf-model-all-MiniLM-L6-v2-${{ runner.os }}-v1
      - name: warm HF model cache (neurosym-forge)
        if: matrix.skill == 'neurosym-forge'
        shell: bash
        env:
          HF_HOME: ${{ github.workspace }}/hf-cache
        run: |
          retry() {
            for i in 1 2 3; do
              "$@" && return 0
              echo "attempt $i failed; retrying in $((i * 5))s" >&2
              sleep $((i * 5))
            done
            return 1
          }
          if [ ! -d "$HF_HOME/hub/models--sentence-transformers--all-MiniLM-L6-v2" ]; then
            retry python -c "from huggingface_hub import snapshot_download; snapshot_download('sentence-transformers/all-MiniLM-L6-v2')"
          else
            echo "HF model cache hit; skipping warmup"
          fi
```

- [ ] **Step 2: Point the pytest step at the cache, offline**

The pytest step (currently ~line 260) gains an `env:` block. Expressions degrade to harmless values for every other skill:

```yaml
      - name: pytest
        if: matrix.smoke != 'import'
        working-directory: skills/${{ matrix.skill }}
        shell: bash
        env:
          # neurosym-forge only: read the warmed model cache, never the network.
          HF_HOME: ${{ matrix.skill == 'neurosym-forge' && format('{0}/hf-cache', github.workspace) || format('{0}/hf-unused', runner.temp) }}
          HF_HUB_OFFLINE: ${{ matrix.skill == 'neurosym-forge' && '1' || '0' }}
        run: |
          (run block unchanged)
```

- [ ] **Step 3: Apply the same pattern to the nightly + legacy neurosym legs**

Read `.github/workflows/nightly-flake-drift.yml` (windows-full-canary job): it includes neurosym-forge in its matrix. Add the same two steps (cache + warmup) guarded by `if: matrix.skill == 'neurosym-forge'` before its pytest step and the same `env:` block on its pytest step.

Read `.github/workflows/ci-legacy.yml` `test-neurosym-forge` job: check whether it installs the `semantic` extra (grep for `semantic` in that job). If YES, apply the same cache+warmup+env pattern (unconditional — the job is neurosym-only). If NO, leave it and note that in the commit message.

- [ ] **Step 4: actionlint the edited workflows locally if available; else rely on the actionlint CI job**

```powershell
git -C C:\russellian-book-suite diff --stat
```
Visually confirm only the three workflow files changed.

- [ ] **Step 5: Commit**

```powershell
git -C C:\russellian-book-suite add .github/workflows
git -C C:\russellian-book-suite commit -m "ci: cache all-MiniLM-L6-v2 and run neurosym-forge pytest with HF_HUB_OFFLINE (kill 429 flake)"
```

---

## Task 3: F3 — path-gate python matrix, narrow cargo trigger

**Files:**
- Modify: `.github/workflows/ci.yml` — `changes` job (~lines 83–113), `python-skill-matrix` header (~line 123), `required` job aggregation (~lines 396–447), comment above `python-skill-matrix`.

- [ ] **Step 1: Extend the changes job with a python filter and narrow rust**

Replace the `changes` job's outputs + filter block with:

```yaml
    outputs:
      rust: ${{ steps.filter.outputs.rust }}
      python: ${{ steps.filter.outputs.python }}
    steps:
      - uses: actions/checkout@df4cb1c069e1874edd31b4311f1884172cec0e10 # v6.0.3
      - uses: dorny/paths-filter@fbd0ab8f3e69293af611ebaee6363fc25e6d187d # v4.0.1
        id: filter
        with:
          filters: |
            # rust gates cargo-test (verifier crate compilation only). The old
            # filter included skills/** and interpreted-language globs, which
            # made every python PR pay 4 cargo jobs for crates it cannot affect.
            rust:
              - 'verifiers/**'
              - '**/*.rs'
              - '**/Cargo.toml'
              - '**/Cargo.lock'
              - 'flake.nix'
              - 'flake.lock'
              - 'Makefile'
              - '.github/workflows/ci.yml'
            # python gates the 35-job python-skill matrix. Verifier-only and
            # docs-only PRs skip it (the 2026-06-03 dependabot flood queued
            # ~12h of matrix runs for one-line verifier bumps).
            python:
              - 'skills/**'
              - 'sibling_skills/**'
              - 'ci/**'
              - '.github/workflows/ci.yml'
              - '.github/actions/setup-book-python/**'
```

Also update the job's leading comment (lines 80–82) to mention both outputs.

- [ ] **Step 2: preflight keeps a broad trigger**

`preflight`'s `if:` becomes (it spans both worlds via `make preflight`):

```yaml
    if: github.event_name != 'pull_request' || needs.changes.outputs.rust == 'true' || needs.changes.outputs.python == 'true'
```

Note the shape change from `== 'push'` to `!= 'pull_request'`: this keeps preflight (and the gates below) running on `merge_group` events, where dorny's filter has no PR diff to inspect. Apply the same shape to `cargo-test`'s condition:

```yaml
    if: github.event_name != 'pull_request' || needs.changes.outputs.rust == 'true'
```

- [ ] **Step 3: Gate python-skill-matrix**

Add to the job header (after `runs-on`/`timeout-minutes`, before `strategy`):

```yaml
    needs: [changes]
    if: github.event_name != 'pull_request' || needs.changes.outputs.python == 'true'
```

- [ ] **Step 4: Update the required-job aggregation**

In the `aggregate` step: move `python-skill-matrix` from `require_success` to `require_not_failed`, and update the step comment:

```yaml
      # Fail-closed aggregation. Always-run jobs (lint, actionlint,
      # ci-divergence-summary) MUST be 'success' — a 'skipped' there means the
      # gate did not actually run and is now treated as a failure. Change-scoped
      # jobs (preflight, cargo-test, python-skill-matrix) are legitimately
      # 'skipped' when the PR diff does not touch their inputs, so they accept
      # 'success' OR 'skipped' but never 'failure'/'cancelled'.
```

and in the body:

```bash
          require_success lint "$LINT"
          require_success actionlint "$ACTIONLINT"
          require_success ci-divergence-summary "$DIVERGENCE"
          require_not_failed python-skill-matrix "$PYTHON_SKILL"
          require_not_failed preflight "$PREFLIGHT"
          require_not_failed cargo-test "$CARGO_TEST"
```

`ci-divergence-summary` needs no change — its `render()` already maps `skipped` to `skip` and it runs `if: always()`.

- [ ] **Step 5: Sanity-read the whole edited ci.yml once** — every `needs:` reference resolves, no duplicate keys, the python-skill-matrix job now has `needs: [changes]` and both aggregator jobs still list it.

- [ ] **Step 6: Commit**

```powershell
git -C C:\russellian-book-suite add .github/workflows/ci.yml
git -C C:\russellian-book-suite commit -m "ci: path-gate python matrix; narrow cargo trigger to verifier inputs"
```

---

## Task 4: F4 — composite action to setup-python v6 + dependabot coverage

**Files:**
- Modify: `.github/actions/setup-book-python/action.yml` (the `uses:` line)
- Modify: `.github/dependabot.yml` (new entry)

- [ ] **Step 1: Bump the pin**

In `action.yml`, replace:

```yaml
    - uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065 # v5.6.0
```

with the SHA `ci-legacy.yml` already trusts:

```yaml
    - uses: actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405 # v6.2.0
```

- [ ] **Step 2: Add dependabot coverage for the composite dir**

In `.github/dependabot.yml`, after the existing `github-actions` entry, add:

```yaml
  # Composite-action internals are not scanned by the root github-actions
  # entry (the v5.6.0 setup-python pin went stale unnoticed); scan them
  # explicitly.
  - package-ecosystem: github-actions
    directory: /.github/actions/setup-book-python
    schedule:
      interval: weekly
    groups:
      actions-composite:
        patterns:
          - "*"
```

- [ ] **Step 3: Commit**

```powershell
git -C C:\russellian-book-suite add .github/actions/setup-book-python/action.yml .github/dependabot.yml
git -C C:\russellian-book-suite commit -m "ci: setup-python v6 in composite action (node24); dependabot scans composite pins"
```

---

## Task 5: F5 — document main-run supersession

**Files:**
- Modify: `.github/workflows/ci.yml:11-13` (concurrency block)

- [ ] **Step 1: Add the comment**

```yaml
# cancel-in-progress protects RUNNING main builds, but GitHub keeps at most
# one QUEUED run per concurrency group: rapid sequential merges supersede
# queued main runs, which then show as 'cancelled'. That is by design — the
# newest run validates the cumulative tree. Expect cancelled main runs after
# merge bursts; only the latest one needs to be green.
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: ${{ github.ref != 'refs/heads/main' }}
```

- [ ] **Step 2: Commit**

```powershell
git -C C:\russellian-book-suite add .github/workflows/ci.yml
git -C C:\russellian-book-suite commit -m "ci: document queued-main-run supersession at the concurrency block"
```

---

## Task 6: QA gate, push, PR, verify, merge

**Files:** none new.

- [ ] **Step 1: QA gate — dispatch a read-only auditor subagent**

Checklist (verify live, trust nothing):
1. `git diff --name-only origin/main HEAD` = exactly: `ci/check_windows_canary.py`, `ci/test_check_windows_canary.py`, `.github/workflows/ci.yml`, `.github/workflows/nightly-flake-drift.yml`, `.github/workflows/ci-legacy.yml` (only if Task 2 Step 3 touched it), `.github/actions/setup-book-python/action.yml`, `.github/dependabot.yml`, `docs/superpowers/specs/2026-06-03-ci-hardening-design.md`, `docs/superpowers/plans/2026-06-03-ci-hardening.md` (this file — commit it in this task if not yet).
2. Re-run `py -3.13 -m pytest ci/ -q` and `py -3.13 -m ci.check_windows_canary` — green.
3. ci.yml consistency: `python-skill-matrix` has `needs: [changes]`; `required` uses `require_not_failed` for python-skill-matrix and `require_success` for exactly lint/actionlint/ci-divergence-summary; the changes job exposes both outputs; the rust filter no longer contains `skills/**` or `**/*.py`; the HF cache/warmup steps are neurosym-guarded; the pytest env block uses the exact expressions from Task 2 Step 2.
4. No stray files, no binaries.

- [ ] **Step 2: Commit the plan, push, open the PR**

```powershell
git -C C:\russellian-book-suite add docs/superpowers/plans/2026-06-03-ci-hardening.md
git -C C:\russellian-book-suite commit -m "Plan: CI hardening"
git -C C:\russellian-book-suite push -u origin ci/hardening
gh pr create --repo CharlesHoskinson/russellian-book-suite --base main --head ci/hardening --title "CI hardening: HF model cache, canary guard, path-gated matrix, node24" --body "Four fixes from the 2026-06-03 carve-arc findings: (1) cache all-MiniLM-L6-v2 + HF_HUB_OFFLINE on neurosym-forge legs — kills the 429/hang flake that hit #192/#194/#197/#203; (2) lint-time guard failing fast when a matrix skill has zero windows_canary marks (the #195 incident class); (3) python path filter gating the 35-job matrix + narrowed cargo trigger — verifier-only and docs-only PRs stop paying the full matrix; (4) setup-python v6 in the composite action ahead of the June 16 node24 cutoff, plus dependabot coverage for composite pins. Also documents queued-main-run supersession. Spec: docs/superpowers/specs/2026-06-03-ci-hardening-design.md"
```

- [ ] **Step 3: Verify on the PR's own run**

This PR touches `.github/**` + `ci/**`, so the full matrix runs (proving F3's filter triggers). Confirm:
- `lint` green (guard executed — find `check_windows_canary: OK` in its log);
- the neurosym-forge legs green with the `warm HF model cache` step present; no `HTTP Error 429` anywhere in their logs;
- all checks green → merge: `gh pr merge <n> --repo CharlesHoskinson/russellian-book-suite --merge --delete-branch`.

If the neurosym legs flake on the FIRST run (cache cold, warmup itself rate-limited): rerun failed jobs once; the cache saves from the second run onward.

- [ ] **Step 4: Post-merge F3 proof (cheap, real)**

After merge, push a one-line docs-only branch and open a draft PR:

```powershell
git -C C:\russellian-book-suite checkout -b test/f3-docs-only origin/main
# append a blank line to README.md, commit "docs: f3 gate probe", push, open DRAFT PR
```
Expected: `python-skill-matrix`, `preflight`, `cargo-test` all SKIPPED; `lint`, `actionlint`, `ci-divergence-summary`, `ci-required` green. Then close the draft PR unmerged and delete the branch. Record the observation.

- [ ] **Step 5: Update memory/scratchpad and report**

Scratchpad `context` entry: CI hardening landed (PR number, the four fixes, F3 proof result). Update `reference_ci_cleanup.md` memory: HF flake fixed (cache+offline), canary guard exists, python matrix path-gated, node24 done — and remove any now-stale claims.

---

## Self-Review Notes

- **Spec coverage:** F1→Task 2, F2→Task 1, F3→Task 3, F4→Task 4, F5→Task 5, verification→Task 6 (incl. the docs-only F3 probe). Out-of-scope items untouched.
- **TDD:** the only new code (canary guard) has a genuine red/green cycle with a fixture test, a tmp-dir behavior test, and a live-repo invariant test that doubles as the production check.
- **merge_group regression risk** (a skipped matrix auto-greening in a merge queue) is addressed by the `!= 'pull_request'` condition shape in Task 3 Steps 2–3 — filters only gate on actual PR events.
- **Fail-closed parser:** the guard errors when it parses zero skills, so ci.yml structure drift cannot silently disable it.
- **Type consistency:** `full_pytest_matrix_skills`/`skills_missing_canary` names match between test and implementation; `REPO_ROOT`/`WORKFLOW_PATH` exported for the live test.
