# book-compose Robust Linter-Test Gating Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace book-compose's hand-maintained conftest skip-filename list with a `needs_spacy_model` pytest marker driven by the actual prerequisite, and remove the now-stale `~/.claude` sibling gate so repo-first tests run.

**Architecture:** A `conftest.py` that (1) registers a `needs_spacy_model` marker, (2) skips marked items when the `en_core_web_sm` model is absent, and (3) no longer gates on `~/.claude` sibling installs. Each test module that transitively loads the russellian-style / feynman-style NLP linters carries the marker. Marking completeness is proven empirically by a model-off run that must produce only clean skips + passes (no `E050` errors).

**Tech Stack:** pytest, spaCy (`en_core_web_sm`), the book-compose per-skill venv at `skills/book-compose/.venv/Scripts/python.exe`. Spec: `docs/superpowers/specs/2026-06-17-book-compose-test-deps-design.md`.

## Global Constraints

- **Test-infrastructure only.** No production module changes. No `pyproject.toml` dependency changes (`spacy` is already declared; the `ci` extra deliberately omits the model).
- **No auto-download at test time.** The skip engages when the model is absent; it is never fetched during a run.
- Run tests with the skill venv: `cd skills/book-compose && .venv/Scripts/python.exe -m pytest …`.
- Commit author is the repo default (Charles Hoskinson); no AI attribution in messages.
- Work in `C:\russellian-book-suite`.

---

### Task 1: Replace the conftest gate with the marker mechanism

Rewrite `tests/conftest.py`: register the `needs_spacy_model` marker, add a skip hook that fires only when the model is absent, and DELETE the `_sibling_skills_installed()` gate + `collect_ignore_glob`. With the model present on this box, the full suite must stay green AND the four previously sibling-gated files must now collect and pass.

**Files:**
- Modify: `skills/book-compose/tests/conftest.py` (full rewrite)

**Interfaces:**
- Produces: a pytest marker named `needs_spacy_model` that other test modules apply via `pytestmark`. Skip semantics: when `spacy.load("en_core_web_sm")` fails at conftest import, every item whose keywords include `needs_spacy_model` is skipped with reason `"en_core_web_sm spaCy model not installed"`.

- [ ] **Step 1: Record the current (gated) baseline**

Run: `cd /c/russellian-book-suite/skills/book-compose && .venv/Scripts/python.exe -m pytest tests/ -q 2>&1 | tail -3`
Expected: `122 passed` (the model + click are installed on this box; the four sibling-gated files are still being IGNORED by the old gate, so they are NOT in this count).

- [ ] **Step 2: Rewrite `conftest.py`**

Replace the entire file `skills/book-compose/tests/conftest.py` with:

```python
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))


def _spacy_model_available() -> bool:
    try:
        import spacy

        spacy.load("en_core_web_sm")
        return True
    except Exception:
        return False


# Computed once at collection import: loading the model per test would be wasteful.
_SPACY_MODEL_AVAILABLE = _spacy_model_available()


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "needs_spacy_model: test transitively loads the russellian-style / "
        "feynman-style NLP linters and requires the en_core_web_sm spaCy model; "
        "skipped when the model is not installed.",
    )


def pytest_collection_modifyitems(config, items):
    """Skip marked tests when the spaCy model is absent.

    Replaces the former hand-maintained filename list (which drifted: it missed
    test_halmos_gate.py and test_feynman_final_stage.py). The former
    ~/.claude sibling gate is gone — sibling resolution is repo-first, so those
    tests run from the in-repo siblings.
    """
    if _SPACY_MODEL_AVAILABLE:
        return
    skip = pytest.mark.skip(reason="en_core_web_sm spaCy model not installed")
    for item in items:
        if "needs_spacy_model" in item.keywords:
            item.add_marker(skip)
```

- [ ] **Step 3: Verify the marker is registered**

Run: `cd /c/russellian-book-suite/skills/book-compose && .venv/Scripts/python.exe -m pytest --markers 2>&1 | grep needs_spacy_model`
Expected: one line beginning `@pytest.mark.needs_spacy_model:` describing the marker (proves `pytest_configure` registered it; no `PytestUnknownMarkWarning` later).

- [ ] **Step 4: Run the full suite (model present) — de-gated files now run**

Run: `cd /c/russellian-book-suite/skills/book-compose && .venv/Scripts/python.exe -m pytest tests/ -q 2>&1 | tail -5`
Expected: all pass, and the count is HIGHER than Step 1's 122 (the four files `test_preflight.py`, `test_query_chapter_evidence.py`, `test_sibling_skills.py`, `test_persona_review_pass.py` are no longer ignored). If any of those four fails or errors, STOP and inspect — it reveals a real gap previously masked by the gate (handle it before continuing; a model error there means it also needs the marker — defer that to Task 3).

- [ ] **Step 5: Commit**

```bash
cd /c/russellian-book-suite
git add skills/book-compose/tests/conftest.py
git commit -m "test(book-compose): marker-driven spaCy-model skip; drop stale sibling gate

Replace conftest's hand-maintained skip filename list with a needs_spacy_model
marker + a skip hook that fires only when en_core_web_sm is absent. Remove the
~/.claude _sibling_skills_installed gate and collect_ignore_glob: sibling
resolution is repo-first now, so those tests run from the in-repo siblings."
```

---

### Task 2: Mark the known model-dependent test modules

Add `needs_spacy_model` to the five modules that transitively load the NLP linters. Each already declares `pytestmark = pytest.mark.windows_canary`, so convert each to a list carrying both marks. With the model present, the marker is a no-op and the suite stays green.

**Files:**
- Modify: `skills/book-compose/tests/test_chapter_contract_check.py:3`
- Modify: `skills/book-compose/tests/test_persona_metrics.py:3`
- Modify: `skills/book-compose/tests/test_skill_integration.py:3`
- Modify: `skills/book-compose/tests/test_halmos_gate.py:2`
- Modify: `skills/book-compose/tests/test_feynman_final_stage.py:13`

**Interfaces:**
- Consumes: the `needs_spacy_model` marker from Task 1.

- [ ] **Step 1: Apply the marker to all five modules**

In each file, replace the existing line:

```python
pytestmark = pytest.mark.windows_canary
```

with:

```python
pytestmark = [pytest.mark.windows_canary, pytest.mark.needs_spacy_model]
```

(All five currently have the single-mark form. `test_halmos_gate.py` has it on line 2; `test_chapter_contract_check.py` / `test_persona_metrics.py` / `test_skill_integration.py` on line 3; `test_feynman_final_stage.py` on line 13. Each has `import pytest` already.)

- [ ] **Step 2: Verify these tests still run and pass (model present)**

Run: `cd /c/russellian-book-suite/skills/book-compose && .venv/Scripts/python.exe -m pytest tests/test_chapter_contract_check.py tests/test_persona_metrics.py tests/test_skill_integration.py tests/test_halmos_gate.py tests/test_feynman_final_stage.py -q 2>&1 | tail -4`
Expected: all pass (the marker does nothing while the model is installed). No `PytestUnknownMarkWarning`.

- [ ] **Step 3: Run the full suite to confirm no regression**

Run: `cd /c/russellian-book-suite/skills/book-compose && .venv/Scripts/python.exe -m pytest tests/ -q 2>&1 | tail -4`
Expected: same all-pass count as Task 1 Step 4.

- [ ] **Step 4: Commit**

```bash
cd /c/russellian-book-suite
git add skills/book-compose/tests/test_chapter_contract_check.py \
        skills/book-compose/tests/test_persona_metrics.py \
        skills/book-compose/tests/test_skill_integration.py \
        skills/book-compose/tests/test_halmos_gate.py \
        skills/book-compose/tests/test_feynman_final_stage.py
git commit -m "test(book-compose): mark model-dependent modules needs_spacy_model

Tag the five test modules that transitively load the spaCy/feynman NLP linters
(incl. test_halmos_gate and test_feynman_final_stage, which the old filename
list missed) so they skip cleanly when en_core_web_sm is absent."
```

---

### Task 3: Empirically verify marking completeness (model-off run)

This is the step that ends the drift: with the model genuinely uninstalled, the full suite must produce ONLY clean skips + passes — zero `E050` model errors. Any file that still errors is model-dependent-but-unmarked; mark it and repeat. Restore the model at the end.

**Files:**
- Possibly modify: any additional `tests/test_*.py` revealed to need the marker (apply the same `pytestmark` list conversion as Task 2).

- [ ] **Step 1: Uninstall the spaCy model**

Run: `cd /c/russellian-book-suite/skills/book-compose && .venv/Scripts/python.exe -m pip uninstall -y en-core-web-sm 2>&1 | tail -2`
Expected: `Successfully uninstalled en-core-web-sm-…` (or "not installed", in which case it is already absent).

- [ ] **Step 2: Run the full suite with the model absent**

Run: `cd /c/russellian-book-suite/skills/book-compose && .venv/Scripts/python.exe -m pytest tests/ -q -rE 2>&1 | tail -25`
Expected: a mix of `passed` and `skipped`, with NO `errors` and NO failures. The `-rE` flag lists any errored tests. The marked modules from Task 2 appear as skipped.

- [ ] **Step 3: If any test ERRORED with `E050`, mark it and re-run**

For each errored test file, open it and convert its `pytestmark` to include `pytest.mark.needs_spacy_model` (list form, exactly as Task 2 Step 1 — if it has no `pytestmark` yet, add `pytestmark = pytest.mark.needs_spacy_model` after its `import pytest`; add `import pytest` if missing). Then re-run Step 2. Repeat until Step 2 shows zero errors.

If Step 2 already showed zero errors, this step is a no-op (the Task 2 set was complete) — note that in the commit/PR.

- [ ] **Step 4: Confirm the de-gated sibling tests pass model-absent**

In the Step 2 output, confirm `test_preflight.py`, `test_query_chapter_evidence.py`, `test_sibling_skills.py`, and `test_persona_review_pass.py` show as passed (not errored, not skipped). They must work from the in-repo siblings without the model. If any errors with `E050`, it also needs the marker (handle via Step 3); if it errors for another reason, STOP and investigate — it is a real gap.

- [ ] **Step 5: Reinstall the model**

Run: `cd /c/russellian-book-suite/skills/book-compose && .venv/Scripts/python.exe -m spacy download en_core_web_sm 2>&1 | tail -2`
Expected: `Download and installation successful`.

- [ ] **Step 6: Final full-green run (model restored)**

Run: `cd /c/russellian-book-suite/skills/book-compose && .venv/Scripts/python.exe -m pytest tests/ -q 2>&1 | tail -4`
Expected: all pass (same count as Task 2 Step 3 — markers are no-ops with the model present).

- [ ] **Step 7: Commit any additional markers (skip if none added)**

```bash
cd /c/russellian-book-suite
git add skills/book-compose/tests/
git commit -m "test(book-compose): mark remaining model-dependent tests found by model-off run

Empirical completeness pass: with en_core_web_sm uninstalled, the full suite now
produces only clean skips + passes (no E050 errors), and the de-gated sibling
tests pass from the in-repo siblings."
```

(If Step 3 added no markers, there is nothing to commit here — record "model-off run was clean with the Task 2 set; no additional markers needed" in the PR description instead.)

---

## Self-Review

**Spec coverage:**
- Spec §1 (marker + skip hook in conftest; delete sibling gate) → Task 1. ✓
- Spec §2 (mark model-dependent tests; empirical completeness) → Task 2 (known set) + Task 3 (empirical confirmation). ✓
- Spec §3 (de-gate sibling tests; verify they pass) → Task 1 Step 4 (collected, model present) + Task 3 Step 4 (pass, model absent). ✓
- Spec §4 (no pyproject change) → Global Constraints; no task edits pyproject. ✓
- Spec §5 (verification: model present all-pass; model absent clean skips; forgot-marker errors loudly; CI installs model) → Task 2 Step 3 (present), Task 3 Steps 2/4 (absent), and the forgot-marker error mode is exactly what Task 3 Step 3 surfaces. ✓

**Placeholder scan:** No TBD/TODO; every code/edit step shows exact content; commands have expected output. Task 3 Step 3 is conditional-but-concrete (exact edit shape given). ✓

**Type/name consistency:** Marker name `needs_spacy_model` is identical across Task 1 (registration + hook keyword), Task 2 (pytestmark), and Task 3. Skip reason string consistent. The `pytestmark` list form is identical in Tasks 2 and 3. ✓
