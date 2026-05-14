# Smoke results

Date: 2026-05-13

Run: `.venv/Scripts/python.exe -m pytest tests/ -q`

Result: 62 passed, 0 failed

Test modules:

- test_anthropic_compliance.py — 6 tests
- test_trigger_calibration.py — 2 tests
- test_io.py — 4 tests
- test_sort_registry.py — 9 tests
- test_atom.py — 6 tests
- test_rewrite_rule.py — 5 tests
- test_lint_atomspace.py — 5 tests
- test_lint_rewrite_coverage.py — 3 tests
- test_scaffold_project.py — 5 tests
- test_add_sort.py — 4 tests
- test_add_rewrite_rule.py — 5 tests
- test_add_grounded_atom.py — 4 tests
- test_render_call_graph.py — 2 tests
- test_verify_claims.py — 2 tests

Total: 62

## Integration smoke (manual)

Scaffolded `C:\Users\charl\AppData\Local\Temp\_int_smoke_osmotic` with neurosym-forge v0.1.0.
- scaffold_project: PASS
- add_sort ":molarity": PASS
- lint_atomspace: PASS
- lint_rewrite_coverage: PASS

Did not run `npm install` / `npm run build` — CLJS+Rust toolchain
verification is deferred to a follow-up plan.
