# book-compose linter-test gating — robust model marker, drop stale sibling gate

**Date:** 2026-06-17
**Status:** Design approved; pending implementation plan.

## Problem

`book-compose`'s test suite has linter-backed tests that transitively load
`russellian-style` / `feynman-style` NLP linters, which require `spacy` plus the
`en_core_web_sm` model. The gating for these prerequisites lives in
`skills/book-compose/tests/conftest.py` as a **hand-maintained list of test
filenames**:

```python
if not _spacy_model_available():
    _skip += ["test_chapter_contract_check.py", "test_persona_metrics.py", "test_skill_integration.py"]
if not _sibling_skills_installed():   # checks ~/.claude/skills/book-knowledge
    _skip += ["test_preflight.py", "test_query_chapter_evidence.py", "test_sibling_skills.py", "test_persona_review_pass.py"]
collect_ignore_glob = _skip
```

Two drift bugs result:

1. **The model list is incomplete.** `test_halmos_gate.py` and
   `test_feynman_final_stage.py` both reach the NLP linters but were never added.
   On a box without the model they **error** (`OSError: [E050] Can't find model
   'en_core_web_sm'`) instead of skipping — the 11 failures observed during the
   post-cutover audit. Any *new* linter-backed test drifts the same way.

2. **The sibling gate is stale.** The homoiconic-KG cutover made book-compose's
   sibling resolution **repo-first** (`_repo_sibling`, P5.1 + the F0 hardening),
   so `test_preflight`, `test_query_chapter_evidence`, `test_sibling_skills`, and
   `test_persona_review_pass` now work from the in-repo siblings (always present
   in a checkout) and no longer need a `~/.claude/skills/*` install. But the gate
   still **skips** them when book-knowledge isn't globally installed, silently
   hiding test files that would now pass — masking real coverage and potential
   regressions.

The "declare deps vs skip-when-absent" question is already settled in the repo:
`spacy` is a declared dependency, the `ci` extra deliberately omits only the
model, and a conftest skip-gate exists. The defect is the gate's **brittleness
and staleness**, not the high-level strategy.

## Goal

Make prerequisite gating self-maintaining: a marker driven by the actual
prerequisite, not a filename list — and remove the now-incorrect sibling gate so
repo-first tests run and contribute coverage.

## Non-goals

- No change to `pyproject.toml` dependencies (see Dependencies below).
- No change to any production module — this is test-infrastructure only.
- No auto-download of the model at test time (network at test time is undesirable).
- No change to how the linters themselves work.

## Design

### 1. Marker + skip hook (`tests/conftest.py`)

- Keep `sys.path.insert(0, str(ROOT))` and `_spacy_model_available()`.
- Compute model availability **once** into a module-level bool (avoid reloading
  the model per test).
- `pytest_configure(config)`: register the `needs_spacy_model` marker via
  `config.addinivalue_line("markers", ...)` so there is no unknown-mark warning.
- `pytest_collection_modifyitems(config, items)`: when the model is absent, add
  `pytest.mark.skip(reason="en_core_web_sm not installed")` to every item whose
  keywords include `needs_spacy_model`.
- **Delete** `_sibling_skills_installed()`, its skip list, and the
  `collect_ignore_glob` assignment entirely.

### 2. Mark the model-dependent tests

- Add `pytestmark = pytest.mark.needs_spacy_model` at module top to each test
  file that transitively loads the spacy / feynman NLP linters.
- **Known set** (from a static scan of `chapter_contract_check` /
  `load_russellian_style_module` / `load_feynman_style_module` call sites):
  `test_chapter_contract_check`, `test_persona_metrics`, `test_skill_integration`,
  `test_halmos_gate`, `test_feynman_final_stage`.
- **The complete set is determined empirically, not by static guess:** uninstall
  the model, run the full suite, mark every test file that raises the `E050`
  model error, and repeat until a model-absent run yields only clean skips and
  passes. This is the step that ends the drift.

### 3. De-gate the sibling tests

- Removing the sibling gate lets `test_preflight`, `test_query_chapter_evidence`,
  `test_sibling_skills`, and `test_persona_review_pass` collect and run. After the
  repo-first F0 fix they resolve siblings from the in-repo checkout, so they pass
  without any `~/.claude` install. Any of them that *also* needs the model picks
  up the marker during the Section 2 empirical pass.

### 4. Dependencies (no pyproject change)

- `spacy>=3.7,<4.0` is already declared in both `dependencies` and the `ci`
  extra; the `ci` extra intentionally omits the `en_core_web_sm` model.
- The transient `ModuleNotFoundError: No module named 'click'` seen during the
  audit was a partial-venv artifact (`spacy → typer → click` is transitive). Once
  the marker gate skips model-less tests, the `spacy.cli` import path that needs
  `click` is never reached on those boxes, so it is not a separate concern. No
  dependency edits; the existing "install the model for full coverage" comment in
  `pyproject.toml` stays.

## Verification (acceptance criteria)

- **Model present** (current box state): every marked test runs and passes — full
  real coverage.
- **Model absent:** marked tests **skip** (no errors); all unmarked tests,
  including the four de-gated ones, run and pass. Validated by toggling the model
  on this box: uninstall → run → confirm clean skips + passes → reinstall.
- **Forgot-the-marker failure mode:** a new linter-backed test without the marker
  *errors loudly* on a model-less box — the intended signal, not a silent skip.
- CI / nightly installs the model (per the existing pyproject comment), so marked
  tests execute there; the skip engages only on dev boxes without the model.

## Scope / units touched

- `skills/book-compose/tests/conftest.py` — marker registration + skip hook;
  remove the sibling gate and `collect_ignore_glob`.
- `pytestmark` line added to ~5 test modules (exact set confirmed empirically).
- No production code.

## Risks

- **Incomplete marking** is mitigated by the empirical model-off pass — the only
  way a test can be model-dependent and unmarked is to error visibly on a
  model-less run, which the verification pass surfaces.
- **A de-gated sibling test failing** would reveal a real gap previously masked
  by the gate; that is a feature (it surfaces during implementation), not a
  regression introduced here.
