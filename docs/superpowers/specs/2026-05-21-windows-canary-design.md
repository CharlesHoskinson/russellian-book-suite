# Windows canary — design

**Status:** Design draft, awaiting user review and follow-up implementation plan.

## 1. Goal and scope

**Goal.** Cut the Windows neurosym-forge matrix cell from 446s to ~90s and equivalently shrink the other Windows cells. Achieved by running only Windows-relevant tests (those exercising `subprocess`, paths, line endings, symlinks, file locking, sockets) on Windows. Net effects: saves runner-minutes on every push, sharpens the Windows signal (a Windows failure points at the ~50 marked test files rather than all ~500 tests in a cell), preserves full coverage on ubuntu and macOS.

**Critical-path context.** The wall-time long pole on a push to `main` is `nix preflight` at 457s, not Windows neurosym-forge at 446s. This design does not reduce wall-time-to-feedback; it reduces runner-minute cost and improves Windows signal quality. Cutting the wall-time critical path is the separate cachix follow-up.

**Scope (one PR).**
1. Register a `windows_canary` pytest marker in each skill's `pyproject.toml` / `pytest.ini`.
2. Pre-seed the marker on day one by tagging ~50 tests across the 8 skills using a mechanical heuristic (no editorial judgement on day one).
3. CI matrix: filter the Windows-2022 cells to `-m windows_canary` via a `runner.os` conditional in the existing `pytest` step. ubuntu and macos cells run unfiltered.
4. Add a nightly `windows-full-canary` job to `.github/workflows/nightly-flake-drift.yml` that runs the unfiltered Windows suite — catches under-tagging within 24h.
5. Author-facing one-pager at `docs/operations/windows-canary.md` documenting when to tag.

**Non-goals.** Tagging beyond what's mechanically detectable on day one (later PRs can extend per-test). Touching `nix preflight` (separate cachix follow-up). Changing what runs on ubuntu or macos. Adding alerts / Slack wiring for nightly failures (the existing on-call CI review is sufficient).

## 2. Marker registration and tagging convention

### 2.1 The marker

`@pytest.mark.windows_canary` — registered per-skill in each `pyproject.toml`:

```toml
[tool.pytest.ini_options]
markers = [
    "windows_canary: test exercises platform-sensitive behaviour and must run on Windows",
]
```

Registration makes pytest emit a hard error on typos (`pytest -m windows_canay` fails fast rather than silently matching nothing).

### 2.2 Day-one tagging — mechanical heuristic

A test file becomes a `windows_canary` candidate if its source contains any of:

- `subprocess.` — test shells out; path separators, PATHEXT, line-ending behaviour all differ on Windows
- `tempfile.` — Windows temp paths differ; the `TEMP` env var matters
- `shutil.` calls that touch files — file locking semantics differ
- `Path(...).write_text(...)` or `.write_bytes(...)` — newline normalisation
- `Path(...).symlink_to(...)` or `os.symlink` — Windows symlinks need Developer Mode or admin
- `os.rename` / `os.replace` on existing files — Windows can't replace an open file
- `socket.` — winsock vs BSD semantics
- Test files matching `test_*cli*.py`, `test_*scaffold*.py`, `test_*ingest*.py`, `test_*workspace*.py` — heuristic backstop for tests that don't match the import-pattern triggers but exercise Windows-sensitive surfaces

The sweep is a one-time script that adds `pytestmark = pytest.mark.windows_canary` at the module top of each matching file. No per-function tagging on day one — too granular for the gain.

### 2.3 Estimated coverage

From the grep done during exploration: 14 subprocess-using files in `neurosym-forge` (`test_forge_cli*.py`, `test_scaffold_*.py`, `test_cljs_integration.py`, `test_lint_*.py`, `test_verify_claims.py`, `test_onboarding_bench.py`, etc.), plus equivalents in book-knowledge (PDF ingest, manifest writes), book-compose (sibling-skill symlinks), book-qa, syntopical-metabook. Total ~50 test files across the 8 skills, ~250 tests. Roughly half the current Windows test count, but a much larger fraction of the wall-time since the tagged tests are the slow ones.

### 2.4 What does NOT get tagged on day one

Pure-logic tests: EDN readers / writers, codegen, golden round-trips, validation schemas, dataclass round-trips, in-memory data structure tests. These are the ~500 tests that contribute almost no Windows-specific signal but currently dominate the Windows wall-time.

### 2.5 Future tagging

Authors add `pytestmark = pytest.mark.windows_canary` (file-level) or `@pytest.mark.windows_canary` (function-level) when they write a test touching one of the trigger surfaces. The nightly canary catches mistakes; the playbook tells them when to remember.

### 2.6 Pure-text skill coverage

The four pure-text skills (`russellian-style`, `book-review`, `review-conductor`, `book-thesis`) lack subprocess / I/O tests and will have zero day-one tags. To keep the Windows matrix cell from collecting zero tests (pytest exits 5, CI reads as failure), tag exactly one smoke test per such skill — `test_skill_api.py::test_module_importable` or equivalent. Gives the Windows cell a baseline collectable; cell completes in ~10s.

## 3. CI matrix wiring

Two changes to `.github/workflows/ci.yml`.

### 3.1 Per-OS filter via `runner.os` conditional

Modify the existing conditional `run:` block in the python-skill-matrix `pytest` step (introduced by PR #119):

```yaml
        run: |
          marker_filter=""
          if [ "${{ runner.os }}" = "Windows" ]; then
            marker_filter="-m windows_canary"
          fi
          if [ -n "${{ matrix.pytest-workers }}" ]; then
            python -m pytest tests/ -q --tb=short $marker_filter -n ${{ matrix.pytest-workers }} ${{ matrix.pytest-deselect }}
          else
            python -m pytest tests/ -q --tb=short $marker_filter ${{ matrix.pytest-deselect }}
          fi
```

`runner.os` is a built-in GitHub Actions context — `Windows` / `Linux` / `macOS`. No new matrix attribute needed.

### 3.2 Zero-tagged-tests guard

If a skill has zero tests tagged `windows_canary`, pytest exits 5 ("no tests collected") which CI reads as failure. Two defences:

- Day-one sweep guarantees ≥1 marker per skill that has subprocess tests (`book-knowledge`, `book-compose`, `book-qa`, `neurosym-forge`, `syntopical-metabook`).
- Pure-text skills get exactly one `test_module_importable` tag each (§2.6).

### 3.3 Aggregators

The `required` and `ci-divergence-summary` jobs handle filtered runs correctly without changes — both already process `success` regardless of test count.

## 4. Nightly safety net

### 4.1 New job in `nightly-flake-drift.yml`: `windows-full-canary`

Runs the unfiltered Windows suite once daily. Catches under-tagging within 24h.

```yaml
  windows-full-canary:
    name: windows full suite (catches under-tagging)
    runs-on: windows-2022
    strategy:
      fail-fast: false
      matrix:
        skill:
          - book-qa
          - book-thesis
          - book-knowledge
          - book-review
          - book-compose
          - russellian-style
          - review-conductor
          - neurosym-forge
        include:
          - skill: book-compose
            siblings: book-knowledge russellian-style book-review review-conductor
            pytest-deselect: "--deselect tests/test_sibling_skills.py::test_sibling_python_uses_skill_venv"
          - skill: neurosym-forge
            extra: dev,semantic
    steps:
      - uses: actions/checkout@v4
      - uses: ./.github/actions/setup-book-python
        with:
          python-version: "3.13"
          skill-path: skills/${{ matrix.skill }}
          extra: ${{ matrix.extra || 'ci' }}
      - name: symlink siblings
        if: matrix.siblings != ''
        uses: actions/github-script@v8
        with:
          # Body identical to ci.yml's symlink step — see that file for the
          # canonical script. Avoid duplicating it here; the plan will copy
          # the exact lines at implementation time.
          script: ""
      - name: pytest (unfiltered)
        working-directory: skills/${{ matrix.skill }}
        shell: bash
        run: python -m pytest tests/ -q --tb=short ${{ matrix.pytest-deselect }}
```

No `-m` filter on this job — that's the whole point. Schedule already exists in `nightly-flake-drift.yml` (currently runs at 10:19 UTC per recent run history).

### 4.2 Failure response policy

Documented in `docs/operations/windows-canary.md`:

When `windows-full-canary` fails but PR CI is green:
1. Failing test names tell us which tests have Windows-specific failure modes that the marker missed.
2. Add `@pytest.mark.windows_canary` to each, ship a small follow-up PR.
3. Don't gate releases on this — it's an early-warning, not a blocker.

When `windows-full-canary` passes for 30 consecutive days, the under-tagging risk is empirically low and the nightly could downgrade to weekly. Documented as a future tuning lever; not part of this PR.

### 4.3 No alerts wiring

Job's red/green status is visible on the Actions page. No PagerDuty, no Slack notifications. The existing on-call review of nightly CI is sufficient given the impact tier (under-tagging → eventual Windows-specific regression, never a security or correctness issue).

## 5. Playbook + verification + rollback

### 5.1 `docs/operations/windows-canary.md`

One-page author guide covering:

1. **What the marker means.** "This test exercises a code path that could plausibly fail on Windows but pass on Linux."
2. **When to tag.** `subprocess`, `tempfile`, file write (line endings), symlink, file lock/rename, socket, shelling out. When in doubt: tag. Over-tagging costs runner-minutes; under-tagging costs Windows-specific regressions slipping in.
3. **How to tag.** File-level `pytestmark = pytest.mark.windows_canary` for a whole module of OS-sensitive tests, or per-function `@pytest.mark.windows_canary`.
4. **What the nightly catches.** Under-tagging — full Windows suite runs once daily.
5. **Skill-wide tag.** Set `pytestmark = pytest.mark.windows_canary` at the top of `conftest.py` to apply the marker to every test under that conftest's scope.

### 5.2 Verification path

1. **Local sweep dry-run** — script enumerates files matching the trigger surfaces and prints the list of files that would be tagged. Reviewer eyeballs to confirm nothing surprising.
2. **Local Windows-emulation** — `pytest -m windows_canary` from each skill root; confirm collected count is non-zero per skill and total runs in under ~60s on local machine.
3. **PR CI** — Windows cells should show "passed" with much shorter wall-time than before (target: neurosym-forge Windows ≤ 120s). ubuntu / macos cells unchanged.
4. **Post-merge** — watch the next 3 main-branch runs to confirm timings hold.
5. **Nightly canary** — first nightly run validates that the unfiltered full Windows suite still passes. Subsequent nightly runs serve as the under-tagging detector.

### 5.3 Rollback plan

If Windows cells start producing false negatives (a Windows-specific regression slips through the PR gate and shows up only in nightly), and the under-tagging rate is unacceptable: revert by removing the `runner.os == "Windows"` conditional in `ci.yml`. The markers themselves stay (they document intent); only the CI filter goes. Single-file revert.

## 6. Open follow-ups (out of scope for this PR)

- **Cachix migration for `nix preflight`** — the actual wall-time long pole. Documented in the Gemini brief context doc; planned separately.
- **Per-function tagging refinement** — day-one is file-level only. If a particular file ends up over-tagged (e.g. one subprocess test plus 50 pure-logic tests in the same file), a later PR can split the file or move to per-function tags.
- **Nightly cadence downgrade** — after 30 days of green nightly canary, evaluate moving from daily to weekly.
