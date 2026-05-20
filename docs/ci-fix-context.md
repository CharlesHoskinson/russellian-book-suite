# CI fix context — russellian-book-suite

This document is the full comprehension package for an agent tasked with returning the CI pipeline to fully green and substantially faster. Read it top to bottom before drafting any patch.

## 1. Repository at a glance

- GitHub: `CharlesHoskinson/russellian-book-suite`
- Stack: 10 Python skill packages under `skills/`, 2 Rust verifier projects under `verifiers/`, a ClojureScript orchestrator (nbb) per scaffolded verifier
- Python pin: `3.13` on CI (most skills require `>=3.11`)
- The codebase is the host framework for a neurosymbolic book-verification system: PDF → typed claims (book-knowledge) → BookLogic DSL → Z3 / egg / Cozo / LLM-lift verification (neurosym-forge) → publication overlay
- Tier 1–6 has shipped (~75 merged PRs, ~200 EARS REQs). The most recent Tier 6 (theory induction) work landed via admin-merge with the failures listed in §3 already present

## 2. Current CI shape

Two workflow files matter:

### `.github/workflows/ci.yml`

Four jobs run on every push to `main` and every PR:

| Job | Matrix | Runtime (recent) | What it does |
|---|---|---|---|
| `python-skill-matrix` | 8 skills × 3 OSes = 24 cells | 20s–80s per cell, all parallel | `pytest tests/ -v` for each skill, after the `setup-book-python` composite action installs `pip install -e .[ci]` (or `[dev]` for neurosym-forge) |
| `cargo-test` | 2 verifiers × 2 OSes = 4 cells | 25s–55s per cell | `cargo test --features smt --manifest-path verifiers/<v>/rust-verifier/Cargo.toml`. Windows is intentionally skipped — z3 pkg-config probe doesn't find libz3 on win runners |
| `nix preflight` | 1 cell, ubuntu-24.04 | ~7 min (Nix install + cache) | `nix develop -c make preflight` chaining lint + scaffold-bake + regression + verifier checks |
| `ci-divergence-summary` + `required` | aggregator | <10s | Posts a per-OS divergence table to step summary, then `required` aggregates `needs.*.result` into one ✓/✗ |

Concurrency group cancels in-progress PR runs on new pushes; `main` runs are never cancelled.

### `.github/actions/setup-book-python/action.yml`

Composite action with `actions/setup-python` + cache + `pip install -e .[<extra>]`. Used by every cell of `python-skill-matrix`.

### Known timing characteristics

- The 24-cell python-skill matrix totals ~ 8 min wall-clock at parallelism but burns ~12 minute-CPU per push
- `nix preflight` is the long tail at ~7 min — it pays the full Nix install cost every run because `magic-nix-cache` is rate-limited
- The `neurosym-forge` cells are the slowest python-skill cells: 240s ubuntu, 250s macOS, 480s Windows on the failing run (a clean run is faster — these include the 22 known failures and pytest's verbose tracebacks)

## 3. The 22 failing tests (full list with root causes)

All failures are in `skills/neurosym-forge` and have been present on `main` since the Tier 6 merge sequence. Triaged into 4 classes:

### Class A — AGM revision prov-schema drift (15 tests)

Files: `skills/neurosym-forge/tests/test_agm_revision.py`

```
test_retraction_contracts_rule
test_revise_theory_signature_and_in_place_sidecar_mutation
test_unaffected_rule_left_untouched
test_single_paper_one_rule_contracts
test_single_paper_five_rules_contract
test_entrenchment_formula_clamps_to_unit_interval
test_status_thresholds_deterministic
test_status_threshold_boundary_at_0_7_inclusive
test_no_promote_up_in_tier_six
test_quarantined_rule_persists_in_sidecar
test_contradicting_atom_downgrades_active_to_tentative
test_full_quarantine_warning_fires
test_no_warning_when_some_rules_remain_active
test_revision_report_shape_and_counts
test_revision_report_kebab_case_indexing
```

All raise the same shape:

```
ValueError: rule ':induced/r1' missing required prov keys:
  :prov/contradiction-atoms, :prov/cost-usd, :prov/llm-repair-calls,
  :prov/proposed-by, :prov/validated-by
```

**Root cause.** Test fixtures build prov dicts with the 4 keys actually exercised by each test (`:prov/derived-from-atoms`, `:prov/source-documents`, `:prov/entrenchment`, `:prov/status`). The validator at `scripts/_provenance.py:_validate_prov_dict` requires the full **9-key closed schema** (`_REQUIRED_KEYS`):

```python
_REQUIRED_KEYS = frozenset({
    ":prov/derived-from-atoms", ":prov/source-documents",
    ":prov/contradiction-atoms", ":prov/proposed-by",
    ":prov/validated-by", ":prov/entrenchment", ":prov/status",
    ":prov/llm-repair-calls", ":prov/cost-usd",
})
```

The fixtures and the validator were written by different PRs in the Tier 6 sequence (Phase Y for `_provenance.py`, Phase Z for `_agm_revision.py` tests). They diverged.

**Acceptable fixes** (pick whichever is cleanest):
- Make `ProvenanceSidecar.add_rule_provenance` default-fill missing required keys to empty/zero values when the caller passes a partial dict, then let `_validate_prov_dict` see a complete dict
- Update `test_agm_revision._seed_sidecar` to compose a helper that fills the 5 missing keys with `[]`, `{}`, `0`, etc. and have each test override only the keys it cares about
- Add a `from_partial(rule_id, partial: dict) -> dict` factory in `_provenance` and call it from the test helper

Production code paths already produce full prov dicts (the orchestrator + LLM proposer fill all 9 keys); only the test fixtures are short.

### Class B — Failure-mode test imports missing symbols (2 tests)

File: `skills/neurosym-forge/tests/test_failure_modes.py`

```
test_false_correction_loop_rejected
  → ImportError: cannot import name 'propose_repair' from 'scripts._induction_proposer'
test_memorization_vs_induction_rejected
  → ImportError: cannot import name 'validate_with_holdout' from 'scripts._induction_orchestrator'
```

**Root cause.** Phase BB tests reference symbols that Phase V/W never exposed. The test author used `_has_module(...)` branching with stub fallbacks at the top of the file, but the import at lines 275 and 374 is **inside the test function bodies** and runs unconditionally.

**Acceptable fixes:**
- Add `propose_repair` to `_induction_proposer.py` (a thin wrapper around the existing `LLMLiftProvider.propose_repair` if it exists, or a stub that returns the input unchanged so the test can exercise the repair-loop budget cap)
- Add `validate_with_holdout` to `_induction_orchestrator.py` (a thin wrapper around the 5-fold document-held-out validation already implemented in `_induction_sources.py` or wherever the validator lives)
- Or move the imports inside the existing `_has_module(...)` gate so the tests skip cleanly when the symbol is absent

Inspect the existing code first — these symbols may already exist under different names.

### Class C — Seed-template count and content (3 tests)

File: `skills/neurosym-forge/tests/test_seed_template_annotations.py`

```
test_seed_has_example_form[induced-theory.prov.edn.tmpl]
  → AssertionError: induced-theory.prov.edn.tmpl has no commented-out example form
test_seed_has_silent_failure_notes[induced-theory.prov.edn.tmpl]
  → AssertionError: induced-theory.prov.edn.tmpl has no 'common silent failures' notes
test_all_seven_seeds_present
  → AssertionError: missing seeds: set(); extra: {'induced-theory.prov.edn.tmpl'}
```

**Root cause.** A new Tier 6 PR added `induced-theory.prov.edn.tmpl` under `skills/neurosym-forge/assets/project-template/rules/booklogic/`. The seed-annotations test contract (REQ-BOOKLOGIC-046) requires every `.edn.tmpl` to ship (a) a commented-out example form whose comment line contains `(def...` or `(approx=` or `(=`, and (b) a "common silent failures" comment block. The new template ships only schema commentary.

Also, the canonical seed list in `test_all_seven_seeds_present` is hard-coded to 7 specific filenames; the new template is the 8th.

**Acceptable fixes:**
- Add a commented-out example block to `induced-theory.prov.edn.tmpl` (start with `;; EXAMPLE (commented out — uncomment and edit for your domain):` followed by an example map entry on a `;;` line, plus a `;; COMMON SILENT FAILURES:` block)
- Update the expected-set in `test_all_seven_seeds_present` to include `induced-theory.prov.edn.tmpl` (and rename the test if appropriate)

### Class D — Nix preflight: rustfmt drift (1 job)

File: `verifiers/bermuda/rust-verifier/src/smt.rs:409, 446`

`make lint` invokes `cargo fmt --check` which fails on two formatting differences in `merge_verdicts` (function signature wrap) and a closure block (`.map(|(s, r)| { if r.is_empty() { ... } else { ... } })` vs the inline form).

**Fix.** One-liner: `cargo fmt --manifest-path verifiers/bermuda/rust-verifier/Cargo.toml`. Commit the reformat.

Also confirm no other files drift by running `make lint` locally.

## 4. Production files relevant to the fix

### `skills/neurosym-forge/scripts/_provenance.py`

Owns `ProvenanceSidecar` (load/save EDN), the `:prov/*` closed schema (`_REQUIRED_KEYS`, `_OPTIONAL_KEYS`, `_ALL_KEYS`), `_CANONICAL_KEY_ORDER` for byte-stable output, and `_validate_prov_dict(rule_id, prov)`. Read this file end-to-end before patching — the validator is intentionally strict because the AGM revision logic in `_agm_revision.py` relies on every key being present.

### `skills/neurosym-forge/scripts/_agm_revision.py`

Implements `revise_theory(induced_path, prov_path, retracted_docs, contradicting_atoms) -> RevisionReport`. Entrenchment formula: `(held-out-sat-rate × support-doc-count) / max`. Thresholds: `0.7` (active) / `0.4` (tentative) / `<0.4` (quarantined). The tests in test_agm_revision.py exercise these threshold transitions and the no-promote-up invariant.

### `skills/neurosym-forge/scripts/_induction_proposer.py`

Wraps Phase P's `LLMLiftProvider` with an induction-specific prompt. Class B's `propose_repair` symbol is expected here.

### `skills/neurosym-forge/scripts/_induction_orchestrator.py`

Dispatches Horn-body / Popper / LLM proposers, dedupes, applies budget cap, returns surviving candidates. Class B's `validate_with_holdout` symbol is expected here.

### `skills/neurosym-forge/assets/project-template/rules/booklogic/induced-theory.prov.edn.tmpl`

The 8th seed file under the booklogic template directory. Lacks the example-form and silent-failures comment blocks the test contract requires.

### `verifiers/bermuda/rust-verifier/src/smt.rs`

Compiles fine; only rustfmt-formatting drift at lines 409 and 446.

## 5. Speed-up opportunities

The CI is correct in shape but slow. Concrete levers (in priority order):

1. **Cache pip wheels across cells.** `setup-book-python` enables `actions/setup-python`'s built-in pip cache, but each skill installs into a fresh venv. Pre-build a wheel-cache layer keyed on `pyproject.toml` hash. This cuts ~10s per cell × 24 cells = ~4 min CPU per push.
2. **Drop pytest `-v` in the matrix.** Verbose output adds ~5s per cell on Windows alone. Use `--tb=short -q` and rely on the divergence summary aggregator for at-a-glance status. Reviewers can re-run a single cell with `-v` on demand.
3. **Cache the Nix store between `nix preflight` runs.** Currently `magic-nix-cache` is rate-limited (visible in the failure log: `ResourceExhausted: rate limit exceeded`). Switch to `cachix` with a project-owned cache, or fall back to a `actions/cache@v4` step keyed on `flake.lock` hashing the entire `/nix/store`.
4. **Split `nix preflight` into a fast lint cell + a slow regression cell.** Today it's one job at ~7 min wall. `make lint` is ~1 min; `make regression` + verifiers is the rest. A separate `nix-lint` job gives PR authors fast lint feedback while the longer job runs in parallel.
5. **Skip cargo-test on PRs that don't touch Rust.** Use `dorny/paths-filter@v3` to gate `cargo-test` and `nix preflight` on changes under `verifiers/`, `*.rs`, `Cargo.toml`, `flake.nix`, `Makefile`, and the `.github/workflows/` files themselves.
6. **Parallelise pytest inside each cell.** Most skills have <100 tests but `neurosym-forge` has ~500. Adding `pytest-xdist` to the `[dev]` extras and running `pytest -n auto` cuts the neurosym-forge cell from ~240s to ~80s on ubuntu.
7. **Skip slow per-skill tests on PRs.** Mark `test_cljs_integration`, `test_scaffold_bake`, and any test that shells out to `nbb` / `cargo` with `@pytest.mark.slow`, then default to `--deselect mark slow` on PRs while keeping them on the nightly `nightly-flake-drift` workflow.

Items 1, 2, 5, 6 are independently safe. Item 3 needs auth setup (cachix token) but pays back the most absolute wall time. Item 4 needs a small Makefile refactor.

## 6. Constraints and non-goals

**Hard constraints**
- No new dependencies unless absolutely required (CI pipeline-installs from `pyproject.toml`; new deps slow every cell)
- Cannot use `--no-verify` on commits, cannot bypass signing, cannot push to `main`
- No AI attribution in commits, no `Co-Authored-By: Claude`, terse commit messages
- Python 3.13 is the CI target; do not raise the minimum without coordination
- Windows must stay in the matrix (REQ-CI-040); contributor base includes Windows users
- The 5-fold document-held-out validation and the closed `:prov/*` schema are correctness contracts from Tier 6 — do not loosen them by accident

**Non-goals**
- Not touching the test contracts (the tests assert real behaviour — fix the schema or production code, not the assertion text)
- Not rewriting `_provenance.py`'s validator — it's intentionally strict; the test fixtures need to comply
- Not adding `# type: ignore` or `# noqa` to silence linters; fix the underlying issue
- Not introducing a `pytest.skip` to make a red test green — that's hiding the failure

## 7. Success criteria

A PR (or chained PRs) merged onto `main` such that:

1. `gh run list --branch main --status completed --limit 1 --json conclusion` returns `[{"conclusion":"success"}]`
2. `gh pr checks <new-pr>` shows zero failures on a fresh PR against post-fix main
3. Total CI wall time for a typical PR (no Rust changes) is ≤ 4 minutes
4. `neurosym-forge` python-skill cell is ≤ 90s on ubuntu, ≤ 180s on Windows
5. `nix preflight` is either split into `nix-lint` (≤ 2 min) + `nix-regression` (≤ 8 min), or kept as one but with a project-owned cache that lands under 4 min
6. No test is `@pytest.mark.skip`'d to achieve the green state. `@pytest.mark.slow`-gated deselects on PRs are acceptable if the gated tests still run on nightly

## 8. Suggested PR sequence

Independent PRs, each merge-able on its own merits:

1. **PR-1: `fix: cargo fmt drift in bermuda smt.rs`** — pure reformat, unblocks `nix preflight`
2. **PR-2: `fix: agm-revision tests build prov dicts via from_partial helper`** — closes Class A
3. **PR-3: `fix: induction proposer/orchestrator expose propose_repair + validate_with_holdout`** — closes Class B
4. **PR-4: `fix: induced-theory.prov.edn.tmpl gets example + silent-failures block; update seed-count test`** — closes Class C
5. **PR-5: `ci: pytest -q --tb=short, pip wheel cache, paths-filter on cargo/nix`** — speed-up items 1, 2, 5
6. **PR-6: `ci: pytest-xdist for neurosym-forge`** — speed-up item 6
7. **PR-7: `ci: split nix preflight into lint + regression`** — speed-up item 4

PR-1 through PR-4 are bug fixes and should land first; PR-5 through PR-7 are pure CI optimisation. Each PR's commit message should be a single terse line; no AI attribution.
