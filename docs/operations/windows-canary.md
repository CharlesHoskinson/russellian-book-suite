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
