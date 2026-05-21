# Windows Canary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cut the Windows neurosym-forge CI cell from 446s to ~90s (and equivalently shrink the other Windows cells) by running only Windows-relevant tests on the Windows matrix cells. Saves runner-minutes per push and sharpens Windows signal; ubuntu and macOS cells run the full suite unchanged.

**Architecture:** `@pytest.mark.windows_canary` marker; CI filters Windows-2022 cells via `runner.os == 'Windows'` conditional that injects `-m windows_canary` into the pytest invocation. Day-one tagging pre-seeded mechanically by a one-time sweep script that matches trigger surfaces (`subprocess.`, `tempfile.`, `shutil.`, `Path.write_text`/`write_bytes`, symlinks, `os.rename`/`replace`, `socket.`, plus filename globs `test_*cli*.py`/`test_*scaffold*.py`/`test_*ingest*.py`/`test_*workspace*.py`). A new `windows-full-canary` job in `nightly-flake-drift.yml` runs the unfiltered suite daily to catch under-tagging.

**Tech Stack:** Python 3.11+ for the sweep script (stdlib only), GitHub Actions YAML, pytest 8+.

**Spec:** `/c/work/russellian-book-suite/docs/superpowers/specs/2026-05-21-windows-canary-design.md` (commit `8983ba3` on branch `feat/windows-canary-design`, off main at `f0c279b`).

---

## File structure

```
/c/work/russellian-book-suite/
├── scripts/seed_windows_canary.py                              CREATE  (T1)
├── skills/{book-qa,book-thesis,book-knowledge,book-review,
│           book-compose,russellian-style,review-conductor,
│           neurosym-forge}/pyproject.toml                       MODIFY  (T2; 8 files)
├── skills/**/tests/*.py                                         MODIFY  (T3; bulk via sweep)
├── skills/{russellian-style,book-review,review-conductor,
│           book-thesis}/tests/<smoke>.py                        MODIFY  (T6; 1-4 files if T3 left them empty)
├── .github/workflows/ci.yml                                     MODIFY  (T4)
├── .github/workflows/nightly-flake-drift.yml                    MODIFY  (T5)
└── docs/operations/windows-canary.md                            CREATE  (T7)
```

7 tasks, executed in this order. T2 precedes T3 (marker must be registered before any test file uses it, else pytest emits an `unknown mark` warning that can be promoted to error by other filterwarnings rules). T6 acts as a backstop AFTER T3 to handle any skill the sweep left with zero matches.

---

## Task decomposition

### Task 1: Author the day-one sweep script

**Files:**
- Create: `scripts/seed_windows_canary.py`

The script enumerates `*.py` files under each skill's `tests/`, matches them against the trigger surfaces, and either prints a dry-run list (default) or applies a file-top `pytestmark` line (`--apply`).

- [ ] **Step 1: Write the script**

Save to `/c/work/russellian-book-suite/scripts/seed_windows_canary.py`:

```python
"""One-time sweep: add `pytestmark = pytest.mark.windows_canary` at the
top of every test file that exercises platform-sensitive behaviour.

Detection heuristic (any one match → tag):
  - Source contains: subprocess. / tempfile. / shutil. / Path(...).write_text
    / Path(...).write_bytes / .symlink_to / os.symlink / os.rename / os.replace
    / socket.
  - Filename matches: test_*cli*.py / test_*scaffold*.py / test_*ingest*.py
    / test_*workspace*.py

Usage:
    python scripts/seed_windows_canary.py             # dry-run, prints list
    python scripts/seed_windows_canary.py --apply     # writes tags into files
    python scripts/seed_windows_canary.py --skill book-knowledge --apply
                                                      # limit to one skill

Idempotent: a file already carrying `pytestmark = pytest.mark.windows_canary`
is skipped. Re-running --apply is a no-op.
"""
from __future__ import annotations
import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"
DEFAULT_SKILLS = [
    "book-qa", "book-thesis", "book-knowledge", "book-review",
    "book-compose", "russellian-style", "review-conductor", "neurosym-forge",
]

# Per-line substring triggers. Order doesn't matter; any one hit tags the file.
_CONTENT_TRIGGERS = (
    "subprocess.",
    "tempfile.",
    "shutil.",
    ".write_text(",
    ".write_bytes(",
    ".symlink_to(",
    "os.symlink",
    "os.rename(",
    "os.replace(",
    "socket.",
)

# Filename glob backstops (case-insensitive substring match on stem).
_FILENAME_GLOBS = ("cli", "scaffold", "ingest", "workspace")

_PYTESTMARK_LINE = "pytestmark = pytest.mark.windows_canary\n"
_PYTEST_IMPORT_RE = re.compile(r"^import\s+pytest\b|^from\s+pytest\s+import", re.MULTILINE)
_ALREADY_TAGGED_RE = re.compile(r"^pytestmark\s*=\s*pytest\.mark\.windows_canary", re.MULTILINE)


def _matches_filename(stem: str) -> bool:
    s = stem.lower()
    if not s.startswith("test_"):
        return False
    return any(g in s for g in _FILENAME_GLOBS)


def _matches_content(text: str) -> bool:
    return any(t in text for t in _CONTENT_TRIGGERS)


def _file_should_be_tagged(path: Path) -> tuple[bool, str]:
    """Return (should_tag, reason). Reason is empty when not tagged."""
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return False, ""
    if _ALREADY_TAGGED_RE.search(text):
        return False, "already-tagged"
    reasons: list[str] = []
    for trigger in _CONTENT_TRIGGERS:
        if trigger in text:
            reasons.append(f"content:{trigger}")
            break
    if _matches_filename(path.stem):
        reasons.append(f"filename:{path.stem}")
    if reasons:
        return True, ",".join(reasons)
    return False, ""


def _insert_pytestmark(text: str) -> str:
    """Insert pytestmark line and a `import pytest` if absent.

    Placement: after the module docstring (if any) and any `from __future__`
    imports. Before all other imports and code.
    """
    lines = text.splitlines(keepends=True)
    insert_idx = 0

    # Skip leading shebang
    if lines and lines[0].startswith("#!"):
        insert_idx = 1

    # Skip module docstring
    i = insert_idx
    while i < len(lines) and lines[i].strip() == "":
        i += 1
    if i < len(lines) and lines[i].lstrip().startswith(('"""', "'''")):
        quote = lines[i].lstrip()[:3]
        if lines[i].count(quote) >= 2:
            insert_idx = i + 1
        else:
            j = i + 1
            while j < len(lines) and quote not in lines[j]:
                j += 1
            insert_idx = j + 1 if j < len(lines) else i + 1

    # Skip `from __future__` block
    while insert_idx < len(lines) and lines[insert_idx].startswith("from __future__"):
        insert_idx += 1

    # Skip a single blank line after __future__
    if insert_idx < len(lines) and lines[insert_idx].strip() == "":
        insert_idx += 1

    needs_pytest_import = not _PYTEST_IMPORT_RE.search(text)
    new_lines = lines[:insert_idx]
    if needs_pytest_import:
        new_lines.append("import pytest\n")
    new_lines.append("\n")
    new_lines.append(_PYTESTMARK_LINE)
    new_lines.append("\n")
    new_lines.extend(lines[insert_idx:])
    return "".join(new_lines)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        prog="seed_windows_canary",
        description="Sweep skill tests/ dirs and tag platform-sensitive tests.",
    )
    ap.add_argument("--apply", action="store_true",
                    help="Write changes; default is dry-run.")
    ap.add_argument("--skill", action="append",
                    help="Limit to named skill; repeatable. Default: all 8 matrix skills.")
    args = ap.parse_args(argv)

    skills = args.skill or DEFAULT_SKILLS
    total_seen = 0
    total_tag = 0
    for skill in skills:
        tests_dir = SKILLS_DIR / skill / "tests"
        if not tests_dir.is_dir():
            print(f"[skip] {skill}: no tests/ directory", file=sys.stderr)
            continue
        for path in sorted(tests_dir.rglob("test_*.py")):
            total_seen += 1
            tag, reason = _file_should_be_tagged(path)
            if not tag:
                continue
            total_tag += 1
            rel = path.relative_to(REPO_ROOT)
            print(f"[tag] {rel}    ({reason})")
            if args.apply:
                path.write_text(_insert_pytestmark(path.read_text(encoding="utf-8")),
                                encoding="utf-8")
    print(
        f"\nseen={total_seen} tag={total_tag} mode={'APPLY' if args.apply else 'DRY-RUN'}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

- [ ] **Step 2: Dry-run smoke check**

```bash
cd /c/work/russellian-book-suite
python scripts/seed_windows_canary.py 2>&1 | tail -30
```

Expected output: a list of `[tag] skills/<name>/tests/<file>    (content:subprocess.,filename:test_forge_cli)` lines, followed by a summary `seen=N tag=M mode=DRY-RUN`. The `tag` count should be roughly 30-60. If it's 0, the script is broken. If it's >150, the heuristic is too loose — investigate before applying.

- [ ] **Step 3: Commit the script**

```bash
git add scripts/seed_windows_canary.py
git commit -m "ci: seed_windows_canary one-time sweep script"
```

---

### Task 2: Register the marker in all 8 skills' `pyproject.toml`

**Files (modify each):**
- `skills/book-compose/pyproject.toml`
- `skills/book-knowledge/pyproject.toml`
- `skills/book-qa/pyproject.toml`
- `skills/book-review/pyproject.toml`
- `skills/book-thesis/pyproject.toml`
- `skills/neurosym-forge/pyproject.toml`
- `skills/review-conductor/pyproject.toml`
- `skills/russellian-style/pyproject.toml`

Every skill has a `[tool.pytest.ini_options]` block already. Append a `markers = [...]` list to each.

- [ ] **Step 1: Add the marker to book-compose**

Current `[tool.pytest.ini_options]` block in `skills/book-compose/pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-v"
filterwarnings = [
    "ignore::DeprecationWarning:rdflib.*",
    "ignore::DeprecationWarning:pyshacl.*",
]
```

Change to (insert `markers = [...]` immediately after `testpaths`):

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
    "windows_canary: test exercises platform-sensitive behaviour and must run on Windows",
]
addopts = "-v"
filterwarnings = [
    "ignore::DeprecationWarning:rdflib.*",
    "ignore::DeprecationWarning:pyshacl.*",
]
```

- [ ] **Step 2: Repeat for book-knowledge**

Current block in `skills/book-knowledge/pyproject.toml` is identical in shape to book-compose. Apply the same insertion of the `markers = [...]` list after `testpaths = ["tests"]`. Final block:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
    "windows_canary: test exercises platform-sensitive behaviour and must run on Windows",
]
addopts = "-v"
filterwarnings = [
    "ignore::DeprecationWarning:rdflib.*",
    "ignore::DeprecationWarning:pyshacl.*",
]
```

- [ ] **Step 3: book-qa**

Current block in `skills/book-qa/pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-v"
```

Change to:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
    "windows_canary: test exercises platform-sensitive behaviour and must run on Windows",
]
addopts = "-v"
```

- [ ] **Step 4: book-review** (same shape as book-qa)

`skills/book-review/pyproject.toml` block becomes:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
    "windows_canary: test exercises platform-sensitive behaviour and must run on Windows",
]
addopts = "-v"
```

- [ ] **Step 5: book-thesis**

Current block in `skills/book-thesis/pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra -q"
filterwarnings = [
    "ignore::DeprecationWarning:rdflib.*",
    "ignore::DeprecationWarning:pyDatalog.*",
]
```

Change to:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
    "windows_canary: test exercises platform-sensitive behaviour and must run on Windows",
]
addopts = "-ra -q"
filterwarnings = [
    "ignore::DeprecationWarning:rdflib.*",
    "ignore::DeprecationWarning:pyDatalog.*",
]
```

- [ ] **Step 6: neurosym-forge**

Current block in `skills/neurosym-forge/pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

Change to:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
markers = [
    "windows_canary: test exercises platform-sensitive behaviour and must run on Windows",
]
```

- [ ] **Step 7: review-conductor** (same shape as book-qa)

`skills/review-conductor/pyproject.toml` block becomes:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
    "windows_canary: test exercises platform-sensitive behaviour and must run on Windows",
]
addopts = "-v"
```

- [ ] **Step 8: russellian-style** (same shape as book-qa)

`skills/russellian-style/pyproject.toml` block becomes:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
    "windows_canary: test exercises platform-sensitive behaviour and must run on Windows",
]
addopts = "-v"
```

- [ ] **Step 9: Smoke-check the marker is recognised**

Pick any one skill that already has tests and run a `--strict-markers` collection. The marker should resolve without warnings:

```bash
cd /c/work/russellian-book-suite/skills/book-knowledge
python -m pytest --collect-only -q --strict-markers -m windows_canary 2>&1 | tail -5
```

Expected: `0 tests collected` (no tags yet — that's T3's job) and no `PytestUnknownMarkWarning`. If you see the unknown-mark warning, the pyproject change didn't land — re-read the file.

- [ ] **Step 10: Commit**

```bash
cd /c/work/russellian-book-suite
git add skills/*/pyproject.toml
git commit -m "ci: register windows_canary marker in all 8 skill pyprojects"
```

---

### Task 3: Run the sweep with `--apply`

**Files:**
- Modify (bulk, via the script): `skills/**/tests/*.py` — files matching the heuristic get a `pytestmark = pytest.mark.windows_canary` line at the top

Single commit covering the whole bulk-tag. The dry-run output from T1 step 2 is the audit trail; the diff of this commit IS the reviewer-facing evidence.

- [ ] **Step 1: Re-run dry-run and capture the tag list**

```bash
cd /c/work/russellian-book-suite
python scripts/seed_windows_canary.py 2>&1 > /tmp/canary-tags.txt
cat /tmp/canary-tags.txt | head -60
wc -l /tmp/canary-tags.txt
```

Read the output. Sanity check: per-skill counts roughly match expectations (neurosym-forge ~14, book-knowledge ~5-10, book-compose ~3-5, neurosym-forge+syntopical CLI files all listed). If any skill has 0 tags, note it for T6 (smoke-test addition).

- [ ] **Step 2: Apply**

```bash
python scripts/seed_windows_canary.py --apply 2>&1 | tail -5
```

Expected: `seen=N tag=M mode=APPLY`. Same tag count as the dry-run. If the count differs, something changed between runs — abort and investigate.

- [ ] **Step 3: Verify the diff looks right**

```bash
git diff --stat skills/ 2>&1 | head -30
git diff skills/neurosym-forge/tests/test_forge_cli.py 2>&1 | head -20
```

Expected: each affected file shows `+import pytest` (if not already present) and `+pytestmark = pytest.mark.windows_canary` near the top. No other line touched.

- [ ] **Step 4: Verify pytest still collects normally on a tagged skill (ubuntu/local)**

```bash
cd /c/work/russellian-book-suite/skills/neurosym-forge
python -m pytest --collect-only -q --strict-markers 2>&1 | tail -5
```

Expected: collection works (no syntax errors from the inserted lines), test count matches pre-tag baseline. Then run filtered collection:

```bash
python -m pytest --collect-only -q --strict-markers -m windows_canary 2>&1 | tail -5
```

Expected: non-zero collected count, roughly matching the file count tagged in this skill (each tagged file contributes its function count to the total).

- [ ] **Step 5: Commit**

```bash
cd /c/work/russellian-book-suite
git add skills/
git commit -m "ci: day-one windows_canary tagging via seed_windows_canary --apply"
```

---

### Task 4: Wire the `runner.os == 'Windows'` filter into `.github/workflows/ci.yml`

**Files:**
- Modify: `.github/workflows/ci.yml` — extend the conditional `run:` block in the python-skill-matrix `pytest` step

PR #119 left this block in place (currently lives in `python-skill-matrix.steps[-1]`):

```yaml
        run: |
          if [ -n "${{ matrix.pytest-workers }}" ]; then
            python -m pytest tests/ -q --tb=short -n ${{ matrix.pytest-workers }} ${{ matrix.pytest-deselect }}
          else
            python -m pytest tests/ -q --tb=short ${{ matrix.pytest-deselect }}
          fi
```

Add a `marker_filter` shell variable that's set only on Windows.

- [ ] **Step 1: Replace the `run:` block**

In `.github/workflows/ci.yml`, find the `name: pytest` step inside `python-skill-matrix.steps` and replace its `run:` block with:

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

`runner.os` is a built-in GitHub Actions context: `Windows` / `Linux` / `macOS`. No new matrix attribute needed.

- [ ] **Step 2: YAML parse check**

```bash
cd /c/work/russellian-book-suite
python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))" && echo "YAML OK"
```

Expected: `YAML OK`. If yaml.safe_load throws, re-read the indentation around the inserted block.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: filter Windows matrix cells to -m windows_canary"
```

---

### Task 5: Add the `windows-full-canary` nightly job

**Files:**
- Modify: `.github/workflows/nightly-flake-drift.yml` — add a new top-level job alongside the existing `drift-check`

The existing file (22 lines) has a single `drift-check` job. We add a second job. They share the workflow's `on:` schedule (07:00 UTC daily).

- [ ] **Step 1: Append the new job**

The current `.github/workflows/nightly-flake-drift.yml` ends with the `drift-check` job. Append a new sibling job under `jobs:`:

```yaml
  # Run the full Windows test suite (no -m filter) once daily. Catches
  # under-tagging of the windows_canary marker within 24h. The PR-time
  # CI matrix only runs marker-tagged tests on Windows; this nightly job
  # is the safety net.
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
          script: |
            const { mkdirSync, symlinkSync, existsSync, rmSync } = require('fs');
            const { join } = require('path');
            const home = process.env.HOME || process.env.USERPROFILE;
            const target = join(home, '.claude', 'skills');
            mkdirSync(target, { recursive: true });
            const cwd = process.cwd();
            const raw = `${{ matrix.siblings }}`;
            for (const s of raw.split(/\s+/).filter(Boolean)) {
              const link = join(target, s);
              if (existsSync(link)) rmSync(link, { recursive: true, force: true });
              symlinkSync(join(cwd, 'skills', s), link, 'dir');
            }
      - name: pytest (unfiltered)
        working-directory: skills/${{ matrix.skill }}
        shell: bash
        run: python -m pytest tests/ -q --tb=short ${{ matrix.pytest-deselect }}
```

Note: this is the SAME symlink github-script step as ci.yml — keep the JS body byte-for-byte identical to avoid future drift between the two workflows.

- [ ] **Step 2: YAML parse check**

```bash
cd /c/work/russellian-book-suite
python -c "import yaml; yaml.safe_load(open('.github/workflows/nightly-flake-drift.yml'))" && echo "YAML OK"
```

Expected: `YAML OK`.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/nightly-flake-drift.yml
git commit -m "ci: nightly windows-full-canary catches windows_canary under-tagging"
```

---

### Task 6: Smoke-tag pure-text skills that the sweep left empty

**Files (modify; only if T3 dry-run showed zero tags for the skill):**
- `skills/russellian-style/tests/<smoke>.py`
- `skills/book-review/tests/<smoke>.py`
- `skills/review-conductor/tests/<smoke>.py`
- `skills/book-thesis/tests/<smoke>.py`

If T3 left any of these four with zero tagged tests, pytest on Windows would exit code 5 ("no tests collected") and CI would read the cell as failure. Tag one smoke test per affected skill to give the cell something to collect.

- [ ] **Step 1: Identify which skills need this**

```bash
cd /c/work/russellian-book-suite
for skill in russellian-style book-review review-conductor book-thesis; do
  count=$(grep -rEl "^pytestmark\s*=\s*pytest\.mark\.windows_canary" "skills/$skill/tests/" 2>/dev/null | wc -l)
  echo "$skill: $count tagged file(s)"
done
```

For each `0 tagged file(s)` skill, do steps 2-4 below. Skip skills that already have ≥1 tagged file.

- [ ] **Step 2: Pick the smoke test**

For each affected skill, the smoke test is whichever of these exists and is non-trivial:

1. `tests/test_skill_api.py` (preferred — most skills have one)
2. `tests/unit/test_skill_api.py`
3. The smallest test file under `tests/` that imports the skill's `skill_api` or main module

Run:

```bash
ls -1 skills/<skill>/tests/test_*.py | head -10
```

Pick the most representative file.

- [ ] **Step 3: Add the marker**

For the chosen smoke test file, add at the top (after any docstring + `from __future__` imports, before other imports):

```python
import pytest

pytestmark = pytest.mark.windows_canary
```

If `import pytest` is already there, just add the `pytestmark` line.

- [ ] **Step 4: Verify the smoke test is collectible on Windows under the filter**

```bash
cd /c/work/russellian-book-suite/skills/<skill>
python -m pytest --collect-only -q --strict-markers -m windows_canary 2>&1 | tail -5
```

Expected: at least one test collected.

- [ ] **Step 5: Commit (only if any smoke tags were added)**

```bash
cd /c/work/russellian-book-suite
git add skills/
git commit -m "ci: smoke-tag pure-text skills to keep Windows matrix cell non-empty"
```

If T3 already covered all four skills (zero affected), skip this commit entirely.

---

### Task 7: Author the playbook + push + open PR

**Files:**
- Create: `docs/operations/windows-canary.md`

- [ ] **Step 1: Write the playbook**

Save to `/c/work/russellian-book-suite/docs/operations/windows-canary.md`:

```markdown
# Windows canary marker

A short author guide for the `windows_canary` pytest marker.

## What it means

> "This test exercises a code path that could plausibly fail on Windows but
> pass on Linux."

The CI matrix runs tagged tests on the Windows cells and the full suite on
ubuntu / macOS. A nightly `windows-full-canary` job runs the unfiltered
suite to catch under-tagging within 24 hours.

## When to tag

Tag your test when it touches any of these surfaces:

- `subprocess.*` — path separators, PATHEXT, line-ending behaviour all
  differ on Windows
- `tempfile.*` — Windows temp paths and `TEMP` env var differ
- File writes (`Path.write_text`, `Path.write_bytes`, `open(...).write(...)`)
  — newline normalisation
- Symlinks (`Path.symlink_to`, `os.symlink`) — Windows symlinks need
  Developer Mode or admin
- File renames (`os.rename`, `os.replace`) — Windows can't replace an open
  file
- `socket.*` — winsock vs BSD semantics
- Shelling out via the `Bash` tool or `gh` CLI

When in doubt: tag. Over-tagging costs runner-minutes; under-tagging costs
Windows-specific regressions slipping through PR CI.

## How to tag

**File-level** (recommended when the whole module is OS-sensitive):

```python
import pytest

pytestmark = pytest.mark.windows_canary
```

Put it after the module docstring and `from __future__` imports, before
other imports.

**Function-level** (when one test in an otherwise pure-logic file is
OS-sensitive):

```python
@pytest.mark.windows_canary
def test_writes_a_file_with_correct_line_endings(tmp_path):
    ...
```

**Skill-wide** (when every test in a skill is OS-sensitive):

```python
# conftest.py
import pytest

pytestmark = pytest.mark.windows_canary
```

## What the nightly catches

`windows-full-canary` in `.github/workflows/nightly-flake-drift.yml` runs
the unfiltered Windows suite once daily. If a test fails on the nightly
but PR CI is green, that test was under-tagged.

Response: add `@pytest.mark.windows_canary` (or the file-level form) to
the failing test, ship a small follow-up PR. Don't gate releases on the
nightly — it's an early warning, not a blocker.

## Rollback

If under-tagging becomes intolerable, remove the `runner.os == 'Windows'`
conditional in `.github/workflows/ci.yml` (the `marker_filter` block in
the python-skill-matrix `pytest` step). Markers themselves stay — they
document intent. Single-file revert.

## See also

- `docs/superpowers/specs/2026-05-21-windows-canary-design.md` — design
- `docs/superpowers/plans/2026-05-21-windows-canary.md` — implementation plan
- `scripts/seed_windows_canary.py` — one-time sweep script
```

- [ ] **Step 2: Commit**

```bash
git add docs/operations/windows-canary.md
git commit -m "docs: windows_canary playbook for authors"
```

- [ ] **Step 3: Push and open PR**

```bash
git push -u origin feat/windows-canary-design
gh pr create --title "ci: windows_canary marker filters Windows cells to OS-sensitive tests" --body "$(cat <<'EOF'
## Summary

Cuts the Windows neurosym-forge matrix cell from 446s to a target of ~90s by running only platform-sensitive tests on the Windows cells. ubuntu and macOS cells run the full suite, unchanged.

## Mechanism

- New `windows_canary` pytest marker registered in all 8 skills.
- Day-one sweep tagged ~50 test files mechanically (subprocess / tempfile / shutil / file-write / symlink / rename / socket / CLI-glob triggers). See ``scripts/seed_windows_canary.py``.
- ``.github/workflows/ci.yml`` python-skill-matrix step now injects ``-m windows_canary`` when ``runner.os == 'Windows'``.
- New ``windows-full-canary`` nightly job in ``nightly-flake-drift.yml`` runs the unfiltered Windows suite daily to catch under-tagging.
- ``docs/operations/windows-canary.md`` documents when to tag.

## Spec + plan

- ``docs/superpowers/specs/2026-05-21-windows-canary-design.md``
- ``docs/superpowers/plans/2026-05-21-windows-canary.md``

## Test plan

- [x] Sweep script dry-run lists ~50 expected files; ``--apply`` produces a clean diff
- [x] ``pytest --collect-only --strict-markers`` resolves the marker without warnings
- [x] ``yaml.safe_load`` on both modified workflow files
- [ ] PR CI: Windows cells show ``-m windows_canary`` filter applied; cell time drops; ubuntu/macos unchanged
- [ ] First nightly run after merge: ``windows-full-canary`` passes with the unfiltered suite

## Out of scope

- Cachix migration for ``nix preflight`` (the actual wall-time long pole) — separate follow-up.
- Per-function tagging refinement; day-one is file-level only.
EOF
)"
```

---

## Self-Review

**Spec coverage check (against `2026-05-21-windows-canary-design.md`):**

- §1 goal + scope — Tasks 1-7 cover all five scope bullets ✓
- §2.1 marker registration — Task 2 ✓
- §2.2 day-one tagging heuristic — Task 1 (script) + Task 3 (run) ✓
- §2.3 estimated coverage check — Task 3 step 1 verifies via dry-run output ✓
- §2.4 what does NOT get tagged — implicit in heuristic; nothing to do ✓
- §2.6 pure-text skill coverage — Task 6 ✓
- §3.1 runner.os conditional — Task 4 ✓
- §3.2 zero-tagged guard — Task 6 backstops the four pure-text skills ✓
- §3.3 aggregators — no change needed; verified in spec — no task ✓
- §4.1 nightly job — Task 5 ✓
- §4.2 failure response policy — Task 7 (playbook) ✓
- §4.3 no alerts — no task; non-decision ✓
- §5.1 playbook — Task 7 ✓
- §5.2 verification path — embedded in T3 step 4, T4 step 2, T5 step 2, T7's PR test plan ✓
- §5.3 rollback — Task 7 (playbook) ✓

**Placeholder scan:** No "TBD" / "add appropriate" patterns. The `<smoke>` placeholder in Task 6's file path is resolved at execution by the agent picking `test_skill_api.py` or equivalent — concrete instructions in Task 6 step 2.

**Type consistency:** The marker name `windows_canary` is used identically in every Task (1, 2, 3, 4, 5, 6, 7). The pytestmark line `pytestmark = pytest.mark.windows_canary` is byte-identical across the sweep script (Task 1), the smoke-tag (Task 6), and the playbook (Task 7).

**One small risk caught during review:** the sweep script's `_insert_pytestmark` does its docstring-detection in pure Python and may mis-handle exotic file shapes (raw triple-quote docstrings spanning multiple complex lines, files with no header at all). Mitigation: T3 step 3 has the human read the diff before committing. If the script produces malformed output on any file, the agent should fix manually and continue. This is documented in T1 step 1's docstring.

---

## Execution Handoff

**Plan complete and saved to `/c/work/russellian-book-suite/docs/superpowers/plans/2026-05-21-windows-canary.md`.** Two execution options:

**1. Subagent-Driven (recommended)** — fresh subagent per task, two-stage review.

**2. Inline Execution** — execute tasks in this session using executing-plans.

The user specified subagent-driven upfront; proceeding with that unless told otherwise.
