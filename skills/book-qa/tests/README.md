# book-qa tests

Fixture-based pytest suite for `scripts.lint_artifact`. Each defect class
D1-D8 has one dirty fixture (must trip the linter) and one clean fixture
(must not), plus a single end-to-end smoke fixture that exercises every band
simultaneously.

## Layout

```
tests/
  __init__.py
  conftest.py                 # stage_release fixture (builds tmp workspaces)
  test_lint_artifact.py       # D1-D8 dirty/clean pairs + smoke + parametric sweep
  fixtures/
    d1_dirty.md  d1_clean.md
    d2_dirty.md  d2_clean.md
    d3_dirty.md  d3_clean.md
    d4_dirty.md  d4_clean.md
    d5_dirty.md  d5_clean.md
    d6_dirty.md  d6_clean.md
    d7_md_stub.md d7_dirty.html d7_clean.html
    d8_dirty.md  d8_clean.md
    placeholder.png            # 1x1 PNG staged for D3/D8 clean
    smoke_clean.md smoke_clean.html
```

## Run

From the skill root (`skills/book-qa/`):

```sh
python -m pytest tests/ -v
```

The `conftest.py` prepends `skills/book-qa/` to `sys.path` so
`from scripts.lint_artifact import lint_artifact` resolves regardless of the
invocation directory.

## Notes

- Clean fixtures only guarantee the *target* defect class is absent. They
  may still emit other classes (e.g. the D1 clean fixture is too short to
  satisfy the D5 word-count band). The smoke test is the single fixture
  designed to satisfy every band at once.
- D7 needs an HTML pair; the markdown stub `d7_md_stub.md` exists only
  because `lint_artifact` requires `manuscript.md` on disk.
- D3 and D8 clean fixtures reference `figures/placeholder.png`; the
  conftest helper stages the bundled 1x1 PNG into the workspace.
