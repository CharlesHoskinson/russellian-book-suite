# BookLogic v0.4 PR-6 — Osmotic-pressure showcase Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up `verifiers/osmotic_pressure/` as a greenfield BookLogic-built verifier that proves the DSL is reusable on a non-book chemistry domain. The project compiles van 't Hoff's equation as a `defconstraint` with `~=` (3% tolerance) and emits `:sat` against a clean fixture and `:unsat` against a doctored one. A new CI job gates both verdicts.

**Architecture:** PR-6 is a pure consumer of the BookLogic stack that PR-4 (active forms — `defconstraint`, `axioms.rs` codegen, `~=` operator) and PR-5 (Z3 Cargo build on `ubuntu-latest`) shipped. No new compiler features. Steps:

1. Scaffold the project tree from the existing `skills/neurosym-forge/assets/project-template/` via `scaffold_project.py`.
2. Author four BookLogic source files (`sorts.edn`, `predicates.edn`, `lifts.edn`, `constraints.edn`).
3. Drop two JSONL fixture ledgers (`claims_clean.jsonl`, `claims_doctored.jsonl`) shaped like Bermuda's.
4. Invoke the BookLogic compiler to regenerate `rust-verifier/src/axioms.rs` from `constraints.edn`.
5. Build the verifier (`cargo build --features z3,bundled` — Linux is the gate; Windows may fail locally and that is acceptable).
6. Run the verifier end-to-end against both fixtures from Python smoke tests under `verifiers/osmotic_pressure/tests/`.
7. Add an `osmotic-pressure-smoke` job to `.github/workflows/ci.yml` that scaffolds, builds, verifies, and asserts verdicts.
8. Update mission spec § D5 footer noting PR-6 closure.

**Dependencies:** PR-4 (`defconstraint` + `axioms.rs` codegen + `~=` with `:tolerance`) and PR-5 (Z3 bundled CI build job + `bermuda-z3-verify` green) must be merged on `main` before this PR opens. PR-6 fails fast if either is missing because (a) the BookLogic compiler will not emit Z3 calls for `defconstraint` forms, and (b) the CI job has no working cargo+Z3 reference image. Verify both on a fresh `git pull` before starting Phase 1.

**Tech Stack:** Python 3.13, pytest (system Python at the repo root). `scripts.scaffold_project` from `skills/neurosym-forge`. The compiled Rust verifier uses `edn-rs` for the IR, `z3 0.20` with `bundled`. The Python smoke driver calls the existing `verify_formulas` napi entry point via `node cljs-orchestrator/dist/main.js verify ...` exactly as Bermuda does. No new Python deps.

**Mission-spec note:** The mission design spec (`docs/specs/2026-05-14-booklogic-v0.4-mission-design.md`) labels the osmotic-pressure deliverable **§ D5**. The Claude-only-finish design doc (`docs/specs/2026-05-17-booklogic-claude-only-finish-design.md`) calls it **PR-6** because it is the sixth PR in the slate. This plan uses "PR-6" throughout to stay consistent with the active branch name and the design doc; the mission-spec footer (Phase 7) updates under its own § D5 numbering.

---

## Pre-flight

Read these before starting:
- `docs/specs/2026-05-17-booklogic-claude-only-finish-design.md` § "PR-6 — Osmotic-pressure showcase (D6)"
- `docs/specs/2026-05-14-booklogic-v0.4-mission-design.md` § "D5 — osmotic-pressure showcase"
- `docs/plans/2026-05-14-booklogic-v0.4-pr1.md` (the canonical PR-style plan)
- `skills/neurosym-forge/scripts/scaffold_project.py` (the scaffolder this plan invokes)
- `skills/neurosym-forge/assets/project-template/` (the template tree the scaffolder copies; in particular `rust-verifier/src/axioms.rs.tmpl`, `rust-verifier/Cargo.toml.tmpl`, `rules/booklogic/{sorts,predicates,lifts}.edn.tmpl`, and `cljs-orchestrator/src/main/__project__/booklogic.cljs.tmpl`)
- `verifiers/bermuda/` end-to-end as a reference layout (especially `scripts/run_verification.py`, `scripts/__init__.py`, `pyproject.toml`, `rust-verifier/Cargo.toml`)
- `examples/bermuda-manual/claims/ledger.jsonl` for JSONL shape
- `.github/workflows/ci.yml` for the existing CI structure that the new job slots into

**Branch:** `feat/booklogic-pr6` cut from current `main`.

```bash
cd C:/work/russellian-book-suite
git fetch origin
git checkout main
git pull --ff-only origin main
git checkout -b feat/booklogic-pr6
```

**Confirm dependencies merged:**

```bash
# PR-4 — defconstraint codegen lands in booklogic.cljs.tmpl
grep -c "defconstraint" skills/neurosym-forge/assets/project-template/cljs-orchestrator/src/main/__project__/booklogic.cljs.tmpl
# Expected: at least 1 (the form recogniser and expander)

# PR-4 — ~= operator codegen
grep -c "tolerance" skills/neurosym-forge/assets/project-template/cljs-orchestrator/src/main/__project__/booklogic.cljs.tmpl
# Expected: at least 1

# PR-5 — bermuda-z3-build CI job
grep -c "bermuda-z3-build" .github/workflows/ci.yml
# Expected: 1
```

If any returns 0, **stop and surface a blocking question** before writing the plan; do not work around missing prerequisites.

**Test invocation.**

```bash
# Repo-root smoke (after Phase 5 lands):
cd C:/work/russellian-book-suite
python -m pytest verifiers/osmotic_pressure/tests/ -v

# Neurosym-forge baseline (must not regress):
cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest tests/ -q
```

**Commit hygiene:** terse, imperative, lowercase scope prefix (e.g. `verifiers/osmotic_pressure:`); no AI attribution; no Co-Authored-By; one problem per commit.

**Scope guard:** PR-6 ships sorts/predicates/lifts/constraints only — no queries, no remedies, no rules. The mission spec is explicit on this ("the seven minimal BookLogic forms — no queries or remedies for the showcase"). Resist scope creep.

---

## File Structure

### Created

```
verifiers/osmotic_pressure/                       NEW (scaffolded in Phase 1)
├── .gitignore
├── README.md
├── SKILL.md
├── deps.edn
├── package.json
├── shadow-cljs.edn
├── pyproject.toml                                NEW (Phase 1 step 4 add)
├── scripts/
│   └── __init__.py                               NEW (Phase 1 step 4 add)
├── rules/
│   ├── .forge-version.edn
│   ├── seed.edn                                  scaffolded
│   ├── predicates.edn                            scaffolded stub; superseded by booklogic/
│   ├── grounded.edn                              scaffolded
│   ├── .checksums.edn                            scaffolded
│   └── booklogic/
│       ├── sorts.edn                             Phase 2 step 1 — overwrites stub
│       ├── predicates.edn                        Phase 2 step 2 — overwrites stub
│       ├── lifts.edn                             Phase 2 step 3 — overwrites stub
│       └── constraints.edn                       Phase 2 step 4 (NEW file)
├── cljs-orchestrator/
│   └── src/main/osmotic_pressure/
│       ├── booklogic.cljs                        scaffolded
│       ├── bridge.cljs
│       ├── core.cljs
│       ├── ir.cljs
│       ├── nl_to_fol.cljs
│       ├── phases.cljs
│       └── unify.cljs
├── rust-verifier/
│   ├── Cargo.toml                                scaffolded
│   ├── build.rs                                  scaffolded
│   └── src/
│       ├── axioms.rs                             Phase 4: regenerated from constraints.edn
│       ├── eqsat.rs
│       ├── ir.rs
│       ├── kg.rs
│       ├── lib.rs
│       ├── smt.rs
│       └── typeset.rs
├── templates/
│   ├── claim_table.tex.tera
│   └── report.tex.tera
├── fixtures/
│   ├── claims_clean.jsonl                        Phase 3 step 1 (NEW)
│   └── claims_doctored.jsonl                     Phase 3 step 2 (NEW)
└── tests/
    ├── __init__.py                               Phase 5 step 1 (NEW)
    ├── conftest.py                               Phase 5 step 1 (NEW)
    └── test_smoke.py                             Phase 5 step 2 (NEW)
```

### Modified

```
.github/workflows/ci.yml                          Phase 6 — add osmotic-pressure-smoke job
docs/specs/2026-05-14-booklogic-v0.4-mission-design.md   Phase 7 — § D5 footer
```

---

## Phase 1: Scaffold the project

### Task 1.1: Run the scaffolder

**Files:**
- Run: `python -m scripts.scaffold_project --name "Osmotic pressure" --slug osmotic_pressure --out verifiers/osmotic_pressure`

- [ ] **Step 1: Write the failing test.**

This is a meta-step: assert the target directory does not exist yet, then assert it exists with the expected layout after scaffolding.

Create a throwaway one-shot check (run inline; do not commit a test for the scaffolder — `skills/neurosym-forge/tests/test_scaffold_project.py` already covers it):

```bash
cd C:/work/russellian-book-suite
test ! -d verifiers/osmotic_pressure && echo "PRE-CHECK OK: target absent" || (echo "FAIL: target exists; aborting" && exit 1)
```

Expected output: `PRE-CHECK OK: target absent`.

- [ ] **Step 2: Run the scaffolder.**

```bash
cd C:/work/russellian-book-suite/skills/neurosym-forge
.venv/Scripts/python.exe -m scripts.scaffold_project \
  --name "Osmotic pressure" \
  --slug osmotic_pressure \
  --out ../../verifiers/osmotic_pressure
```

Expected stdout: `scaffolded osmotic_pressure at ../../verifiers/osmotic_pressure`.

- [ ] **Step 3: Verify the tree matches expectation.**

```bash
cd C:/work/russellian-book-suite
for p in \
  verifiers/osmotic_pressure/SKILL.md \
  verifiers/osmotic_pressure/README.md \
  verifiers/osmotic_pressure/shadow-cljs.edn \
  verifiers/osmotic_pressure/package.json \
  verifiers/osmotic_pressure/deps.edn \
  verifiers/osmotic_pressure/rules/seed.edn \
  verifiers/osmotic_pressure/rules/grounded.edn \
  verifiers/osmotic_pressure/rules/predicates.edn \
  verifiers/osmotic_pressure/rules/.forge-version.edn \
  verifiers/osmotic_pressure/rules/.checksums.edn \
  verifiers/osmotic_pressure/rules/booklogic/sorts.edn \
  verifiers/osmotic_pressure/rules/booklogic/predicates.edn \
  verifiers/osmotic_pressure/rules/booklogic/lifts.edn \
  verifiers/osmotic_pressure/cljs-orchestrator/src/main/osmotic_pressure/booklogic.cljs \
  verifiers/osmotic_pressure/cljs-orchestrator/src/main/osmotic_pressure/core.cljs \
  verifiers/osmotic_pressure/rust-verifier/Cargo.toml \
  verifiers/osmotic_pressure/rust-verifier/src/axioms.rs \
  verifiers/osmotic_pressure/rust-verifier/src/ir.rs \
  verifiers/osmotic_pressure/rust-verifier/src/smt.rs \
  verifiers/osmotic_pressure/rust-verifier/src/lib.rs ; do
  test -f "$p" && echo "OK $p" || (echo "MISSING $p" && exit 1)
done
```

Every line should be `OK <path>`. No `MISSING` lines.

- [ ] **Step 4: Add the project-level Python boilerplate the scaffolder does not emit.**

The scaffolder produces a CLJS+Rust verifier but not the Python test harness. Bermuda gets `scripts/__init__.py`, `pyproject.toml`, and `tests/conftest.py` by hand. Mirror that minimal Python layout so `python -m pytest verifiers/osmotic_pressure/tests/` resolves imports.

Create `verifiers/osmotic_pressure/pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "osmotic-pressure-verifier"
version = "0.1.0"
description = "Osmotic-pressure neurosymbolic verifier (BookLogic showcase)"
authors = [{name = "Charles Hoskinson"}]
license = {text = "MIT"}
requires-python = ">=3.13"
dependencies = []

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
]

[tool.setuptools]
packages = ["scripts"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

Create `verifiers/osmotic_pressure/scripts/__init__.py` (copied verbatim from `verifiers/bermuda/scripts/__init__.py`, only the comment header changed):

```python
"""Osmotic-pressure verifier — Python package init.

Extends the scripts package path to include neurosym-forge's scripts/ so
that `from scripts._edn_reader import ...` resolves correctly regardless of
whether modules are loaded as a package (-m scripts.foo) or directly.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Repo root is three levels up from this file:
# __init__.py -> scripts/ -> osmotic_pressure/ -> verifiers/ -> repo-root
_REPO_ROOT = Path(__file__).resolve().parents[3]
_FORGE_SCRIPTS_DIR = str(_REPO_ROOT / "skills" / "neurosym-forge" / "scripts")

# Extend this package's search path so `from scripts._edn_reader import ...`
# finds forge's modules. Guard against double-insertion.
if _FORGE_SCRIPTS_DIR not in __path__:
    __path__.insert(0, _FORGE_SCRIPTS_DIR)
```

- [ ] **Step 5: Sanity-check imports.**

```bash
cd C:/work/russellian-book-suite/verifiers/osmotic_pressure
python -c "from scripts._edn_reader import Keyword; print(Keyword('ok'))"
```

Expected: `:ok`.

- [ ] **Step 6: Commit.**

```bash
cd C:/work/russellian-book-suite
git add verifiers/osmotic_pressure/
git commit -m "verifiers/osmotic_pressure: scaffold from neurosym-forge template"
```

---

## Phase 2: Author BookLogic source

Each task in this phase follows the five TDD steps. The compiler test fixture in `skills/neurosym-forge/tests/test_cljs_integration.py` exercises BookLogic source via the CLJS compiler against arbitrary projects; we reuse that path by pointing the compiler at the new project's `rules/booklogic/` directory.

### Task 2.1: `sorts.edn`

**Files:**
- Modify: `verifiers/osmotic_pressure/rules/booklogic/sorts.edn`
- Create: `verifiers/osmotic_pressure/tests/test_booklogic_compiles.py`

- [ ] **Step 1: Write the failing test.**

Create `verifiers/osmotic_pressure/tests/__init__.py` (empty) and `verifiers/osmotic_pressure/tests/conftest.py`:

```python
"""Shared pytest fixtures for verifiers/osmotic_pressure/."""
from __future__ import annotations

from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = PROJECT_ROOT.parent.parent


@pytest.fixture()
def project_root() -> Path:
    return PROJECT_ROOT


@pytest.fixture()
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture()
def fixtures_dir() -> Path:
    return PROJECT_ROOT / "fixtures"


@pytest.fixture()
def tmp_work(tmp_path: Path) -> Path:
    work = tmp_path / "work"
    work.mkdir()
    return work
```

Create `verifiers/osmotic_pressure/tests/test_booklogic_compiles.py`:

```python
"""BookLogic source compiles cleanly via the CLJS expander.

Each test runs the nbb-driven compiler entrypoint
(`nbb -m osmotic_pressure.booklogic <project-root>`) against the project's
rules/booklogic/ directory and asserts exit code 0. The compiler enforces
the structural validation rules (defsort/defpredicate/deflift/defconstraint
shapes; predicate sort references; lift -> predicate references; tolerance
on ~=).
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest


def _have_nbb() -> bool:
    return shutil.which("nbb") is not None or shutil.which("nbb.cmd") is not None


pytestmark = pytest.mark.skipif(not _have_nbb(),
                                reason="nbb not on PATH; CI installs it")


def _run_compiler(project_root: Path) -> subprocess.CompletedProcess:
    """Invoke the CLJS booklogic compiler on the project root."""
    return subprocess.run(
        ["nbb", "-m", "osmotic_pressure.booklogic", str(project_root)],
        cwd=str(project_root),
        check=False,
        capture_output=True,
        text=True,
    )


def test_sorts_compiles(project_root: Path) -> None:
    result = _run_compiler(project_root)
    assert result.returncode == 0, (
        f"compiler failed:\nstdout={result.stdout}\nstderr={result.stderr}"
    )
    # Expect the one-line report
    assert "compiled" in result.stdout
    assert "1 sorts" in result.stdout
```

- [ ] **Step 2: Run, expect FAIL.**

```bash
cd C:/work/russellian-book-suite
python -m pytest verifiers/osmotic_pressure/tests/test_booklogic_compiles.py::test_sorts_compiles -v
```

Expected: SKIPPED if nbb is not installed locally (this is the Windows-local norm), or FAIL on Linux because `sorts.edn` is the stub `{:forms []}` (0 sorts, not 1).

If skipped locally, that is acceptable: CI runs the test on `ubuntu-latest` (Phase 6) and will fail there until Step 3 lands. Document the local skip in the smoke-results notes at PR time.

- [ ] **Step 3: Write `sorts.edn`.**

Overwrite `verifiers/osmotic_pressure/rules/booklogic/sorts.edn`:

```clojure
{:forms
 [(defsort :solution)]}
```

- [ ] **Step 4: Run, expect PASS (Linux) or SKIP (Windows).**

```bash
cd C:/work/russellian-book-suite
python -m pytest verifiers/osmotic_pressure/tests/test_booklogic_compiles.py::test_sorts_compiles -v
```

Expected: PASS on Linux with nbb; SKIP on Windows. CI is the truth.

- [ ] **Step 5: Commit.**

```bash
git add verifiers/osmotic_pressure/rules/booklogic/sorts.edn \
        verifiers/osmotic_pressure/tests/__init__.py \
        verifiers/osmotic_pressure/tests/conftest.py \
        verifiers/osmotic_pressure/tests/test_booklogic_compiles.py
git commit -m "verifiers/osmotic_pressure: defsort :solution"
```

### Task 2.2: `predicates.edn`

**Files:**
- Modify: `verifiers/osmotic_pressure/rules/booklogic/predicates.edn`
- Modify: `verifiers/osmotic_pressure/tests/test_booklogic_compiles.py`

The four predicates come straight from the mission spec § D5:

```
(defpredicate :osmotic-pressure-pa [:solution] :real)
(defpredicate :vant-hoff-i         [:solution] :real)
(defpredicate :molarity            [:solution] :real)
(defpredicate :temperature-k       [:solution] :real)
```

- [ ] **Step 1: Append the failing test.**

Append to `verifiers/osmotic_pressure/tests/test_booklogic_compiles.py`:

```python
def test_predicates_compile(project_root: Path) -> None:
    result = _run_compiler(project_root)
    assert result.returncode == 0, (
        f"compiler failed:\nstdout={result.stdout}\nstderr={result.stderr}"
    )
    assert "4 predicates" in result.stdout
```

- [ ] **Step 2: Run, expect FAIL.**

```bash
cd C:/work/russellian-book-suite
python -m pytest verifiers/osmotic_pressure/tests/test_booklogic_compiles.py::test_predicates_compile -v
```

Expected: FAIL on Linux (0 predicates declared); SKIP on Windows.

- [ ] **Step 3: Write `predicates.edn`.**

Overwrite `verifiers/osmotic_pressure/rules/booklogic/predicates.edn`:

```clojure
{:forms
 [(defpredicate :osmotic-pressure-pa [:solution] :real)
  (defpredicate :vant-hoff-i         [:solution] :real)
  (defpredicate :molarity            [:solution] :real)
  (defpredicate :temperature-k       [:solution] :real)]}
```

- [ ] **Step 4: Run, expect PASS / SKIP.**

```bash
cd C:/work/russellian-book-suite
python -m pytest verifiers/osmotic_pressure/tests/test_booklogic_compiles.py::test_predicates_compile -v
```

- [ ] **Step 5: Commit.**

```bash
git add verifiers/osmotic_pressure/rules/booklogic/predicates.edn \
        verifiers/osmotic_pressure/tests/test_booklogic_compiles.py
git commit -m "verifiers/osmotic_pressure: defpredicate van 't Hoff inputs and pressure"
```

### Task 2.3: `lifts.edn`

**Files:**
- Modify: `verifiers/osmotic_pressure/rules/booklogic/lifts.edn`
- Modify: `verifiers/osmotic_pressure/tests/test_booklogic_compiles.py`

At least one lift must map natural-language claims to predicates. We add one canonical lift per predicate keyed on the JSONL `canonical_text` slot. The regex shape mirrors what the CLJS expander expects (`(fact ?claim-id :Subject :pred body)`).

- [ ] **Step 1: Append the failing test.**

```python
def test_lifts_compile(project_root: Path) -> None:
    result = _run_compiler(project_root)
    assert result.returncode == 0, (
        f"compiler failed:\nstdout={result.stdout}\nstderr={result.stderr}"
    )
    # At least one lift; we ship four for symmetry with the four predicates.
    assert "4 lifts" in result.stdout
```

- [ ] **Step 2: Run, expect FAIL on Linux / SKIP locally.**

- [ ] **Step 3: Write `lifts.edn`.**

Overwrite `verifiers/osmotic_pressure/rules/booklogic/lifts.edn`:

```clojure
{:forms
 [(deflift L001-osmotic-pressure-pa
    :from :claim/canonical-text
    :when "(?i)osmotic\\s+pressure\\s*(?:=|is|of)?\\s*(?<v>[0-9]+(?:\\.[0-9]+)?)\\s*Pa"
    :emit (fact ?claim-id :sol :osmotic-pressure-pa (parse-float ?v)))

  (deflift L002-vant-hoff-i
    :from :claim/canonical-text
    :when "(?i)van[' ]?t\\s*Hoff(?:\\s+factor)?\\s*(?:i\\s*)?(?:=|is|of)?\\s*(?<v>[0-9]+(?:\\.[0-9]+)?)"
    :emit (fact ?claim-id :sol :vant-hoff-i (parse-float ?v)))

  (deflift L003-molarity
    :from :claim/canonical-text
    :when "(?i)molarity\\s*(?:M\\s*)?(?:=|is|of)?\\s*(?<v>[0-9]+(?:\\.[0-9]+)?)"
    :emit (fact ?claim-id :sol :molarity (parse-float ?v)))

  (deflift L004-temperature-k
    :from :claim/canonical-text
    :when "(?i)temperature\\s*(?:T\\s*)?(?:=|is|of)?\\s*(?<v>[0-9]+(?:\\.[0-9]+)?)\\s*K"
    :emit (fact ?claim-id :sol :temperature-k (parse-float ?v)))]}
```

- [ ] **Step 4: Run, expect PASS / SKIP.**

- [ ] **Step 5: Commit.**

```bash
git add verifiers/osmotic_pressure/rules/booklogic/lifts.edn \
        verifiers/osmotic_pressure/tests/test_booklogic_compiles.py
git commit -m "verifiers/osmotic_pressure: deflift four van 't Hoff inputs"
```

### Task 2.4: `constraints.edn`

**Files:**
- Create: `verifiers/osmotic_pressure/rules/booklogic/constraints.edn`
- Modify: `verifiers/osmotic_pressure/tests/test_booklogic_compiles.py`

The single constraint is van 't Hoff with `~=` and `:tolerance 0.03`, lifted verbatim from the mission spec § D5.

- [ ] **Step 1: Append the failing test.**

```python
def test_constraint_compiles(project_root: Path) -> None:
    result = _run_compiler(project_root)
    assert result.returncode == 0, (
        f"compiler failed:\nstdout={result.stdout}\nstderr={result.stderr}"
    )
    # When PR-4 landed defconstraint, the report line gained a 'constraints' field.
    assert "1 constraints" in result.stdout

    # The codegen target — axioms.rs — must now carry the constraint name.
    axioms = (project_root / "rust-verifier" / "src" / "axioms.rs").read_text(
        encoding="utf-8"
    )
    assert "C001-vant-hoff" in axioms or "C001_vant_hoff" in axioms
    # ~= compiles to a |a - b| <= eps form; the tolerance literal must survive.
    assert "0.03" in axioms
```

- [ ] **Step 2: Run, expect FAIL on Linux / SKIP locally.**

```bash
cd C:/work/russellian-book-suite
python -m pytest verifiers/osmotic_pressure/tests/test_booklogic_compiles.py::test_constraint_compiles -v
```

- [ ] **Step 3: Write `constraints.edn`.**

Create `verifiers/osmotic_pressure/rules/booklogic/constraints.edn`:

```clojure
{:forms
 [(defconstraint C001-vant-hoff
    :backend :z3
    :assert (~= (:osmotic-pressure-pa ?s)
                (* (:vant-hoff-i ?s) (:molarity ?s) 8.314 (:temperature-k ?s))
                :tolerance 0.03)
    :track :claim/id
    :on-unsat {:defect :D13
               :severity :critical
               :message "van 't Hoff equation violated"})]}
```

- [ ] **Step 4: Run, expect PASS / SKIP.**

Note: the assertion text in Step 1 references `axioms.rs`, which is regenerated by Phase 4 (Task 4.1). Until then this test fails on the `axioms.rs` substring check even on Linux. That is intentional: leave the test failing at the end of Phase 2; Phase 4 closes it. The compiler-exit-0 assertion alone passes once `constraints.edn` exists.

To split the gating cleanly, refactor the test now:

```python
def test_constraint_compiler_accepts(project_root: Path) -> None:
    """Compiler exits 0 with the constraint declared."""
    result = _run_compiler(project_root)
    assert result.returncode == 0, (
        f"compiler failed:\nstdout={result.stdout}\nstderr={result.stderr}"
    )
    assert "1 constraints" in result.stdout


def test_constraint_codegen_lands_in_axioms_rs(project_root: Path) -> None:
    """axioms.rs carries the constraint name and tolerance literal.

    Runs the compiler then reads axioms.rs. Marked xfail until Phase 4
    regenerates axioms.rs from the BookLogic source.
    """
    _run_compiler(project_root)
    axioms = (project_root / "rust-verifier" / "src" / "axioms.rs").read_text(
        encoding="utf-8"
    )
    assert "C001-vant-hoff" in axioms or "C001_vant_hoff" in axioms
    assert "0.03" in axioms
```

Replace the original `test_constraint_compiles` with the two above.

Re-run; `test_constraint_compiler_accepts` passes (Linux) / skips (Windows); `test_constraint_codegen_lands_in_axioms_rs` fails (Linux) / skips (Windows). Phase 4 closes the second.

- [ ] **Step 5: Commit.**

```bash
git add verifiers/osmotic_pressure/rules/booklogic/constraints.edn \
        verifiers/osmotic_pressure/tests/test_booklogic_compiles.py
git commit -m "verifiers/osmotic_pressure: defconstraint van 't Hoff with 3% tolerance"
```

---

## Phase 3: Fixture ledgers

### Task 3.1: `claims_clean.jsonl`

**Files:**
- Create: `verifiers/osmotic_pressure/fixtures/claims_clean.jsonl`

Per mission spec § D5: i=2, M=0.154, T=298.15, π=780202.5 → expect `:sat`.

Sanity-check the math: π = i × M × R × T = 2 × 0.154 × 8.314 × 298.15 ≈ 763.0 kPa.
Spec value 780202.5 Pa ≈ 780.2 kPa. (780.2 − 763.0) / 763.0 ≈ 2.25%. Inside the 0.03 tolerance — so the clean fixture satisfies the constraint. Good.

- [ ] **Step 1: Write the fixture.**

One JSONL line per claim. Shape matches Bermuda's `claims/ledger.jsonl` (book-knowledge format). Fields used by ingestion: `claim_id`, `claim_type`, `canonical_text`, `status`, `confidence`, `source_spans`, `supports_chapters`. The `canonical_text` is what the lifts.edn regexes match against.

Create `verifiers/osmotic_pressure/fixtures/claims_clean.jsonl`:

```jsonl
{"claim_id": "osm-clean-001", "claim_type": "fact", "canonical_text": "van 't Hoff factor i = 2", "status": "verified", "confidence": 1.0, "source_spans": [{"doc_id": "vant-hoff-textbook", "locator_text": "i=2 for NaCl in dilute aqueous solution"}], "supports_chapters": []}
{"claim_id": "osm-clean-002", "claim_type": "fact", "canonical_text": "Molarity M = 0.154", "status": "verified", "confidence": 1.0, "source_spans": [{"doc_id": "vant-hoff-textbook", "locator_text": "isotonic saline 0.154 mol/L"}], "supports_chapters": []}
{"claim_id": "osm-clean-003", "claim_type": "fact", "canonical_text": "Temperature T = 298.15 K", "status": "verified", "confidence": 1.0, "source_spans": [{"doc_id": "vant-hoff-textbook", "locator_text": "STP 298.15 K"}], "supports_chapters": []}
{"claim_id": "osm-clean-004", "claim_type": "fact", "canonical_text": "Osmotic pressure = 780202.5 Pa", "status": "verified", "confidence": 1.0, "source_spans": [{"doc_id": "vant-hoff-textbook", "locator_text": "measured pi ~ 780 kPa"}], "supports_chapters": []}
```

(No trailing newline policy beyond what jsonl convention dictates — one object per line, file ends with `\n`.)

- [ ] **Step 2: Commit.**

```bash
git add verifiers/osmotic_pressure/fixtures/claims_clean.jsonl
git commit -m "verifiers/osmotic_pressure: clean fixture (i=2, sat path)"
```

### Task 3.2: `claims_doctored.jsonl`

**Files:**
- Create: `verifiers/osmotic_pressure/fixtures/claims_doctored.jsonl`

Same M/T/π; flip i from 2 to 1.

Recompute: with i=1, M=0.154, T=298.15, R=8.314 → 381.5 kPa expected. Measured 780.2 kPa. Discrepancy ≈ 104% — well outside the 3% tolerance. Expect `:unsat` with the i=1 claim id (`osm-doc-001`) in the core.

- [ ] **Step 1: Write the fixture.**

Create `verifiers/osmotic_pressure/fixtures/claims_doctored.jsonl`:

```jsonl
{"claim_id": "osm-doc-001", "claim_type": "fact", "canonical_text": "van 't Hoff factor i = 1", "status": "verified", "confidence": 1.0, "source_spans": [{"doc_id": "doctored", "locator_text": "wrongly recorded as non-dissociating"}], "supports_chapters": []}
{"claim_id": "osm-doc-002", "claim_type": "fact", "canonical_text": "Molarity M = 0.154", "status": "verified", "confidence": 1.0, "source_spans": [{"doc_id": "doctored", "locator_text": "M unchanged"}], "supports_chapters": []}
{"claim_id": "osm-doc-003", "claim_type": "fact", "canonical_text": "Temperature T = 298.15 K", "status": "verified", "confidence": 1.0, "source_spans": [{"doc_id": "doctored", "locator_text": "T unchanged"}], "supports_chapters": []}
{"claim_id": "osm-doc-004", "claim_type": "fact", "canonical_text": "Osmotic pressure = 780202.5 Pa", "status": "verified", "confidence": 1.0, "source_spans": [{"doc_id": "doctored", "locator_text": "pi unchanged"}], "supports_chapters": []}
```

- [ ] **Step 2: Commit.**

```bash
git add verifiers/osmotic_pressure/fixtures/claims_doctored.jsonl
git commit -m "verifiers/osmotic_pressure: doctored fixture (i=1, unsat path)"
```

---

## Phase 4: Codegen and build

### Task 4.1: Regenerate `axioms.rs` from `constraints.edn`

**Files:**
- Modify: `verifiers/osmotic_pressure/rust-verifier/src/axioms.rs`

The CLJS BookLogic compiler (delivered by PR-4) reads `rules/booklogic/constraints.edn` and emits `rust-verifier/src/axioms.rs`. PR-4 also delivers a `nbb` target that orchestrates this (the same `-main` already used in Phase 2 — when `constraints.edn` is present it additionally writes `axioms.rs`).

- [ ] **Step 1: Re-run the compiler.**

```bash
cd C:/work/russellian-book-suite/verifiers/osmotic_pressure
nbb -m osmotic_pressure.booklogic .
```

Expected stdout: `[booklogic] compiled 1 sorts, 4 predicates, 4 lifts, 1 constraints -> ...`.

- [ ] **Step 2: Verify the codegen test now passes.**

```bash
cd C:/work/russellian-book-suite
python -m pytest verifiers/osmotic_pressure/tests/test_booklogic_compiles.py::test_constraint_codegen_lands_in_axioms_rs -v
```

Expected: PASS on Linux. Locally on Windows, SKIP.

- [ ] **Step 3: Inspect the generated file.**

```bash
head -40 C:/work/russellian-book-suite/verifiers/osmotic_pressure/rust-verifier/src/axioms.rs
```

It should contain a Z3 `assert_and_track` for the van 't Hoff constraint using `|lhs - rhs| <= 0.03 * |rhs|` (or the equivalent absolute desugaring PR-4 chose), tracked by `"C001-vant-hoff"`.

- [ ] **Step 4: Commit.**

```bash
cd C:/work/russellian-book-suite
git add verifiers/osmotic_pressure/rust-verifier/src/axioms.rs
git commit -m "verifiers/osmotic_pressure: regenerate axioms.rs from constraints.edn"
```

### Task 4.2: `cargo build`

- [ ] **Step 1: Build.**

```bash
cd C:/work/russellian-book-suite
cargo build --manifest-path verifiers/osmotic_pressure/rust-verifier/Cargo.toml --features z3,bundled
```

The `z3,bundled` features feed Cargo's feature parser; equivalent to `--features z3` plus the bundled-z3 sub-feature already enabled on the `z3` dep in `Cargo.toml.tmpl` (`z3 = { ..., features = ["bundled"], optional = true }`).

Expected: `Finished release [...]` or `Finished dev [...]` with zero errors. Warnings are tolerable.

- [ ] **Step 2: Note local-platform tolerance.**

On Windows the bundled Z3 build via CMake / MSVC may fail (the v0.3 mission spec flagged this; PR-5 designated `ubuntu-latest` as the canonical gate). If the build fails locally, capture the error tail in `verifiers/osmotic_pressure/tests/smoke-results.md` and proceed. CI is the truth.

```bash
# If the local build fails, log it:
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) local cargo build failed on Windows; falling back to CI gate" \
  >> verifiers/osmotic_pressure/tests/smoke-results.md
```

- [ ] **Step 3: If the build succeeded, commit only a no-op marker.**

There is nothing to commit from a successful build (Cargo artifacts are gitignored). If the local build failed and produced a smoke-results note, commit it:

```bash
cd C:/work/russellian-book-suite
git add verifiers/osmotic_pressure/tests/smoke-results.md 2>/dev/null || true
git diff --staged --quiet || git commit -m "verifiers/osmotic_pressure: note local build status"
```

---

## Phase 5: End-to-end smoke

### Task 5.1: Smoke test harness

**Files:**
- Create: `verifiers/osmotic_pressure/tests/test_smoke.py`

The harness wraps `verifiers/bermuda/scripts/run_verification.py`'s shape: it builds the `claims.edn` from a JSONL fixture, invokes the Rust verifier through the cljs orchestrator, reads `work/verdict.edn`, asserts on `:verdict` and `:core`.

For the osmotic-pressure project we ingest directly via the BookLogic-generated regex table: that's what the project's compiled `cljs-orchestrator/src/main/osmotic_pressure/booklogic.cljs` emits to `rules/predicates.edn` as a side-effect of compilation. Bermuda's `scripts.ingest_ledger.ingest` consumes exactly that file shape; PR-6 reuses it without modification.

- [ ] **Step 1: Write the failing tests.**

Create `verifiers/osmotic_pressure/tests/test_smoke.py`:

```python
"""End-to-end smoke for the osmotic-pressure verifier.

Pipeline per fixture:
  1. ingest_ledger      fixtures/claims_*.jsonl -> work/claims.edn
                        (uses rules/predicates.edn regen'd by the BookLogic
                         compiler in Phase 4)
  2. verify             node cljs-orchestrator/dist/main.js verify
                        work/claims.edn work/verdict.edn
  3. read verdict       parse work/verdict.edn (EDN) and assert :verdict / :core

The tests skip when the verifier dist is not built (local Windows-only
case). CI builds the verifier before invoking pytest.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from scripts._edn_reader import Keyword, read_edn
from scripts._io import read_edn_file
from scripts.ingest_ledger import ingest


_KW_VERDICT = Keyword("verdict")
_KW_STATUS = Keyword("status")
_KW_CORE = Keyword("core")


def _verifier_main_js(project_root: Path) -> Path:
    return project_root / "cljs-orchestrator" / "dist" / "main.js"


def _have_verifier(project_root: Path) -> bool:
    return _verifier_main_js(project_root).exists()


def _have_node() -> bool:
    return shutil.which("node") is not None or shutil.which("node.exe") is not None


pytestmark = pytest.mark.skipif(
    not _have_node(),
    reason="node not on PATH; CI sets up Node 22",
)


def _run_verifier(project_root: Path, claims_edn: Path, verdict_edn: Path) -> None:
    subprocess.run(
        ["node", str(_verifier_main_js(project_root)),
         "verify", str(claims_edn), str(verdict_edn)],
        check=True, cwd=str(project_root),
    )


def _verdict_status(verdict_edn: Path) -> str:
    """Return ':sat' / ':unsat' / ':unknown' from a verdict.edn file."""
    payload = read_edn_file(verdict_edn)
    # Accept either :verdict (PR-4 schema) or :status (legacy ir.rs emit_verdict
    # which currently writes :status). PR-5 unifies these; until then accept both.
    for key in (_KW_VERDICT, _KW_STATUS):
        v = payload.get(key)
        if v is None:
            continue
        return str(v) if isinstance(v, Keyword) else v
    raise AssertionError(f"verdict.edn missing :verdict / :status: {payload!r}")


def _verdict_core(verdict_edn: Path) -> list[str]:
    payload = read_edn_file(verdict_edn)
    core = payload.get(_KW_CORE, [])
    return list(core)


def test_clean_fixture_is_sat(project_root: Path, tmp_work: Path) -> None:
    if not _have_verifier(project_root):
        pytest.skip(f"verifier not built ({_verifier_main_js(project_root)})")

    claims_edn = tmp_work / "claims.edn"
    verdict_edn = tmp_work / "verdict.edn"
    ingest(
        project_root / "fixtures" / "claims_clean.jsonl",
        project_root / "rules" / "predicates.edn",
        claims_edn,
    )
    _run_verifier(project_root, claims_edn, verdict_edn)

    status = _verdict_status(verdict_edn)
    assert status in (":sat", "sat"), (
        f"expected :sat for clean fixture, got {status!r}"
    )


def test_doctored_fixture_is_unsat_with_i1_in_core(
    project_root: Path, tmp_work: Path,
) -> None:
    if not _have_verifier(project_root):
        pytest.skip(f"verifier not built ({_verifier_main_js(project_root)})")

    claims_edn = tmp_work / "claims.edn"
    verdict_edn = tmp_work / "verdict.edn"
    ingest(
        project_root / "fixtures" / "claims_doctored.jsonl",
        project_root / "rules" / "predicates.edn",
        claims_edn,
    )
    _run_verifier(project_root, claims_edn, verdict_edn)

    status = _verdict_status(verdict_edn)
    assert status in (":unsat", "unsat"), (
        f"expected :unsat for doctored fixture, got {status!r}"
    )
    core = _verdict_core(verdict_edn)
    assert "osm-doc-001" in core, (
        f"expected i=1 claim 'osm-doc-001' in unsat core, got {core!r}"
    )
```

- [ ] **Step 2: Run, expect SKIP locally (no dist/main.js).**

```bash
cd C:/work/russellian-book-suite
python -m pytest verifiers/osmotic_pressure/tests/test_smoke.py -v
```

Both tests SKIP unless a Linux dev box with the verifier built is at hand. CI gates the truth (Phase 6).

- [ ] **Step 3: If on Linux with cargo+node, build and run locally for the optional inner loop.**

```bash
cd C:/work/russellian-book-suite/verifiers/osmotic_pressure
npm install
npm run build
cd ../..
python -m pytest verifiers/osmotic_pressure/tests/test_smoke.py -v
```

Both tests should pass.

- [ ] **Step 4: Commit.**

```bash
cd C:/work/russellian-book-suite
git add verifiers/osmotic_pressure/tests/test_smoke.py
git commit -m "verifiers/osmotic_pressure: end-to-end smoke (clean sat, doctored unsat)"
```

---

## Phase 6: CI job

### Task 6.1: Add `osmotic-pressure-smoke` to `.github/workflows/ci.yml`

**Files:**
- Modify: `.github/workflows/ci.yml`

The job mirrors the `smoke-bermuda-pipeline` shape: checkout, setup Python + Node + Rust, install nbb, scaffold (if absent — defensive, since the project is now in tree), compile BookLogic source, build the verifier with z3+bundled, run pytest on the smoke harness.

- [ ] **Step 1: Append the job to `ci.yml`.**

Exact YAML diff to add at end of `.github/workflows/ci.yml` (after `smoke-bermuda-pipeline`):

```yaml

  osmotic-pressure-smoke:
    name: smoke (osmotic-pressure verifier)
    runs-on: ubuntu-latest
    needs: [test-book-qa]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
          cache: pip
      - uses: actions/setup-node@v4
        with:
          node-version: "22"
      - uses: dtolnay/rust-toolchain@stable
      - name: install python deps
        run: |
          python -m pip install --upgrade pip
          python -m pip install pytest
      - name: install nbb
        run: npm install -g nbb
      - name: install z3 build prerequisites
        run: |
          sudo apt-get update
          sudo apt-get install -y cmake clang libclang-dev
      - name: confirm scaffold present in tree
        run: |
          test -d verifiers/osmotic_pressure || (echo "scaffold missing"; exit 1)
          test -f verifiers/osmotic_pressure/rules/booklogic/constraints.edn \
            || (echo "constraints.edn missing"; exit 1)
      - name: install project npm deps
        working-directory: verifiers/osmotic_pressure
        run: npm install
      - name: compile booklogic source
        working-directory: verifiers/osmotic_pressure
        run: nbb -m osmotic_pressure.booklogic .
      - name: build rust verifier (z3 bundled)
        run: |
          cargo build \
            --manifest-path verifiers/osmotic_pressure/rust-verifier/Cargo.toml \
            --features z3,bundled
      - name: build cljs verifier bundle
        working-directory: verifiers/osmotic_pressure
        run: npm run build
      - name: pytest smoke (sat + unsat verdicts)
        run: |
          python -m pytest verifiers/osmotic_pressure/tests/ -v
      - name: upload verdict artifacts
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: osmotic-pressure-verdicts
          path: |
            verifiers/osmotic_pressure/work/verdict.edn
          if-no-files-found: warn
```

Notes on the YAML:
- `needs: [test-book-qa]` keeps the dependency graph shallow — book-qa green is the baseline; we do not need book-thesis for the chemistry showcase.
- `dtolnay/rust-toolchain@stable` matches the action used by the PR-5 `bermuda-z3-build` job; if PR-5 chose a different action name, mirror it here for consistency.
- `cmake clang libclang-dev` are the bundled-z3 build prerequisites Bermuda's PR-5 job installs; same set works here.
- The `upload-artifact` step is `if: always()` so a failing verdict still uploads `verdict.edn` for diagnosis.

- [ ] **Step 2: Lint the workflow.**

```bash
cd C:/work/russellian-book-suite
# If actionlint is installed locally:
actionlint .github/workflows/ci.yml || true
# Otherwise CI's lint-workflow job catches issues.
```

- [ ] **Step 3: Commit.**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: osmotic-pressure-smoke (scaffold, build, sat+unsat gate)"
```

---

## Phase 7: Mission spec footer update

### Task 7.1: Update `§ D5 — osmotic-pressure showcase` footer

**Files:**
- Modify: `docs/specs/2026-05-14-booklogic-v0.4-mission-design.md`

The mission spec's § D5 ends at line 337 with the sentence on `~=`. PR-6 adds a footer note immediately after that section's last paragraph, before the next `##` heading.

- [ ] **Step 1: Locate the insertion point.**

The current section is at line 309 (`## D5 — osmotic-pressure showcase`) and runs through ~ line 337. Insert a new paragraph just before the next `## ` heading (which is `## Sub-PR slate` at line 339).

- [ ] **Step 2: Insert the footer.**

Append the following paragraph at the end of § D5 (immediately before `## Sub-PR slate`):

```markdown

**PR-6 closure (2026-05-17):** Delivered as `verifiers/osmotic_pressure/`. The
project ships sorts/predicates/lifts/constraints only (no queries or remedies,
per the showcase scope). `axioms.rs` is regenerated from `constraints.edn` by
the BookLogic compiler; both fixture verdicts (`:sat` on clean, `:unsat` on
i=1 doctored) are gated by the `osmotic-pressure-smoke` CI job on
`ubuntu-latest`. The design-doc `docs/specs/2026-05-17-booklogic-claude-only-finish-design.md`
tracks this same deliverable under its own numbering as PR-6.
```

- [ ] **Step 3: Verify no other heading was disturbed.**

```bash
cd C:/work/russellian-book-suite
grep -n "^## " docs/specs/2026-05-14-booklogic-v0.4-mission-design.md
```

Expect the heading list to be unchanged except for the new content sitting between `## D5` and `## Sub-PR slate`.

- [ ] **Step 4: Commit.**

```bash
git add docs/specs/2026-05-14-booklogic-v0.4-mission-design.md
git commit -m "docs(mission-spec): note PR-6 closure under § D5"
```

---

## Phase 8: PR

### Task 8.1: Full sweep

- [ ] **Step 1: Run all suites.**

```bash
cd C:/work/russellian-book-suite
# Neurosym-forge must not regress.
(cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest tests/ -q)
# Book-qa, book-thesis must not regress.
(cd skills/book-qa && python -m pytest tests/ -q)
(cd skills/book-thesis && python -m pytest tests/ -q)
# Bermuda must not regress.
(cd verifiers/bermuda && .venv/Scripts/python.exe -m pytest tests/ -q)
# Osmotic-pressure (local SKIPs are tolerable; CI is the gate).
python -m pytest verifiers/osmotic_pressure/tests/ -v
```

Expected: every suite green (allowing for SKIPs on the osmotic-pressure smoke when local dist is absent). No FAIL anywhere.

- [ ] **Step 2: Push.**

```bash
cd C:/work/russellian-book-suite
git push -u origin feat/booklogic-pr6
```

- [ ] **Step 3: Open the PR.**

```bash
gh pr create --title "BookLogic v0.4 PR-6: osmotic-pressure showcase (D6)" --body "$(cat <<'EOF'
## Summary

Lands the sixth and final sub-PR of the BookLogic v0.4 mission: a non-book
chemistry domain built entirely on BookLogic source, proving the DSL is
reusable beyond the Bermuda case.

- New: `verifiers/osmotic_pressure/` scaffolded from
  `skills/neurosym-forge/assets/project-template/`
- BookLogic source: one `defsort` (`:solution`), four `defpredicate` forms
  (osmotic-pressure-pa, vant-hoff-i, molarity, temperature-k), four
  `deflift` forms (one per predicate), one `defconstraint` (van 't Hoff
  with `~=` and `:tolerance 0.03`)
- `axioms.rs` regenerated from `constraints.edn` via the PR-4 BookLogic
  compiler; no hand-edits
- Two JSONL fixture ledgers under `verifiers/osmotic_pressure/fixtures/`:
  - `claims_clean.jsonl` (i=2) -> `:sat`
  - `claims_doctored.jsonl` (i=1) -> `:unsat`, `osm-doc-001` in core
- Python smoke harness under `verifiers/osmotic_pressure/tests/` that
  ingests each fixture, runs the verifier, asserts the verdict
- New CI job `osmotic-pressure-smoke` on `ubuntu-latest`: scaffolds,
  compiles BookLogic, builds the Rust verifier with `z3,bundled`, builds
  the CLJS bundle, runs pytest on the smoke harness, uploads
  `verdict.edn` as an artifact
- Mission-spec § D5 footer notes the closure

Spec: `docs/specs/2026-05-17-booklogic-claude-only-finish-design.md` §
"PR-6 — Osmotic-pressure showcase (D6)" and
`docs/specs/2026-05-14-booklogic-v0.4-mission-design.md` § "D5".
Plan: `docs/plans/2026-05-17-booklogic-pr6.md`.

## Test plan

- [ ] CI: `osmotic-pressure-smoke` green
- [ ] CI: existing `smoke-bermuda-pipeline`, `bermuda-z3-build`,
      `bermuda-z3-verify`, `cljs-bermuda-test`, `BookLogic CLJS
      integration` all unchanged
- [ ] Local (Linux dev box with nbb + node + rustc + z3 prereqs):
      `python -m pytest verifiers/osmotic_pressure/tests/ -v` green

## Out of scope

- No `defquery` / `defremedy` (showcase explicitly excludes them per mission spec)
- No additional predicates beyond the four van 't Hoff inputs and pressure
- No prose extraction (chemistry domain has no book prose)
EOF
)"
```

- [ ] **Step 4: Report PR URL.**

---

## Self-review

Walking the design doc § PR-6 against this plan:

| Spec clause | Implementing tasks |
|---|---|
| Greenfield `verifiers/osmotic_pressure/` | 1.1 |
| `rules/sorts.edn` with `defsort :solution` | 2.1 |
| `rules/predicates.edn` with four predicates | 2.2 |
| `rules/lifts.edn` mapping NL claims to predicates | 2.3 |
| `rules/constraints.edn` with `~=` and `:tolerance 0.03` | 2.4 |
| Scaffold via `scaffold_project.py` | 1.1 |
| Generated `axioms.rs` with `~=` 3% tolerance | 4.1 |
| `claims_clean.jsonl` (i=2, M=0.154, T=298.15, π=780202.5) -> `:sat` | 3.1, 5.1 |
| `claims_doctored.jsonl` (i=1, same M/T/π) -> `:unsat` with core | 3.2, 5.1 |
| New CI job `osmotic-pressure-smoke` | 6.1 |
| Demonstrates `~=` codegen | 2.4 + 4.1 |
| No queries or remedies for the showcase | scope guard in pre-flight |

All spec items have implementing tasks.

**Mission spec § D5 / design doc PR-6 numbering reconciliation:** documented in pre-flight and Phase 7; mission spec is updated under its own § D5; the plan uses PR-6 throughout for consistency with the branch and the design doc.

**Placeholder scan:** no "TBD", "TODO", "fill in" appear in any task body or in the code-producing steps. Every file gets a complete body; every shell command is exact.

**Type consistency:** `Keyword`, `read_edn_file`, `read_edn`, `ingest` are all imports already present in the codebase (verified by reading `verifiers/bermuda/scripts/run_verification.py` and `verifiers/bermuda/scripts/ingest_ledger.py`). The smoke harness reuses Bermuda's import pattern (the `scripts/__init__.py` path-extension trick).

**Verdict shape:** the test accepts both `:verdict` and `:status` keys because the current `verifiers/bermuda/rust-verifier/src/ir.rs::emit_verdict` writes `:status` while PR-4's revamped emitter writes `:verdict`. Once PR-5 merged the change, this dual-accept can be tightened in a follow-up; PR-6 stays compatible to avoid coupling to PR-5's exact emit shape.

**Effort:** spec said ~1.5 days. This plan is ~1.5 days: Phase 1 is 30 minutes (scaffolder is one command + boilerplate); Phase 2 is 2–3 hours (four files, mostly mechanical from the mission-spec text); Phase 3 is 30 minutes (two short JSONL fixtures); Phase 4 is 30 minutes (compiler invocation + visual confirmation); Phase 5 is 2 hours (writing the smoke harness, especially handling the verdict-shape duality); Phase 6 is 1 hour (CI YAML and a local actionlint pass); Phase 7 + 8 are 30 minutes.

**Known risks:**
- `~=` codegen — PR-4 must already emit a Z3 `assert_and_track` with the desugared `|a-b| <= eps * |rhs|` (or absolute). If PR-4 chose absolute tolerance instead of relative, the clean-fixture pressure (780202.5 Pa vs expected ≈763 kPa absolute) sits well outside any sensible absolute epsilon. The plan's 0.03 figure assumes **relative** tolerance per the mission spec's "3% tolerance" phrasing. If PR-4 went absolute, the fixture numbers need to shift so the clean case stays satisfying; bring this up in PR review before merging.
- Windows-local build — bundled Z3 fails on MSVC for many setups. The plan explicitly delegates the gate to `ubuntu-latest`. Local SKIPs are tolerable.
- Verdict-key churn — PR-4 / PR-5 may have already unified `:status` / `:verdict`. The smoke test accepts both; if review prefers the strict shape, tighten in the same PR.
