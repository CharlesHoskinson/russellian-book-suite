# BookLogic v0.4 PR-5 — Bermuda migration + real Z3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate `verifiers/bermuda/rules/` from hand-coded v0.2 EDN to BookLogic source (`sorts.edn`, `predicates.edn`, `lifts.edn`, `rules.edn`, `constraints.edn`, `queries.edn`, `remedies.edn`), regenerate `rust-verifier/src/axioms.rs` from `defconstraint` forms, delete `canonical.rs`, append four quantitative claims to the Bermuda ledger, wire a real Z3 build into CI, and prove end-to-end that the ch-02 parish-count drift fires a D13 critical ticket.

**Architecture:** Bermuda's `rules/` directory becomes the only source-of-truth for the verifier. The BookLogic compiler from PR-3 (`{{project_slug}}.booklogic`) plus PR-4's active forms (`defrule`, `defconstraint`, `defquery`, `defremedy`) generate every downstream artifact: `rust-verifier/src/axioms.rs` (Z3 assertions), the `prose_patterns.py` regex table, the Cozo script bundle in `kg.rs`, and the remedy table consumed by `book-qa.scripts.propose_writeback.py`. `prose_patterns.py` becomes a thin Python wrapper that reads the codegen output. Real Z3 link is verified on `ubuntu-latest` CI via two new jobs (`bermuda-z3-build` and `bermuda-z3-verify`). Spec at `docs/specs/2026-05-17-booklogic-claude-only-finish-design.md` § "PR-5 — Bermuda migration + real Z3 (D5)"; mission ref at `docs/specs/2026-05-14-booklogic-v0.4-mission-design.md` § "D4 — Bermuda migration".

**Tech Stack:** Python 3.13, pytest, edn-rs 0.19, Z3 0.20 (bundled feature, cmake + C++ toolchain on Linux), nbb 1.4+ for the BookLogic compiler, Node 22+. No new Python deps. No new Rust deps beyond what `Cargo.toml` already optionally declares.

---

## Pre-flight

Read these before starting any task:
- `docs/specs/2026-05-17-booklogic-claude-only-finish-design.md` § "PR-5 — Bermuda migration + real Z3 (D5)"
- `docs/specs/2026-05-14-booklogic-v0.4-mission-design.md` § "D4 — Bermuda migration" and § "D3 — BookLogic DSL v0.1"
- `docs/plans/2026-05-14-booklogic-v0.4-pr1.md` (canonical plan style)
- `docs/plans/2026-05-14-booklogic-v0.4-pr3.md` (BookLogic compiler context — what `defsort`/`defpredicate`/`deflift` already do)
- `verifiers/bermuda/rules/predicates.edn` (the v0.2 hand-coded regex catalog that gets migrated to BookLogic source)
- `verifiers/bermuda/rules/seed.edn`, `grounded.edn`, `.checksums.edn` (post-PR-cleanup these should already be real EDN with Keyword keys)
- `verifiers/bermuda/rust-verifier/src/canonical.rs` (gets deleted; its assertion content becomes `defconstraint` forms)
- `verifiers/bermuda/rust-verifier/src/ir.rs` and `smt.rs` (already use `edn_rs::Edn` after PR-1 — confirm by inspection)
- `verifiers/bermuda/rust-verifier/src/lib.rs` (declares `mod canonical` — must lose that line in Phase 2)
- `verifiers/bermuda/rust-verifier/src/kg.rs` (currently a 6-line stub; PR-4 wired Cozo for the template, this PR uses one `defquery` in Bermuda)
- `verifiers/bermuda/scripts/prose_patterns.py` (becomes a thin wrapper over the BookLogic codegen output)
- `verifiers/bermuda/scripts/ingest_ledger.py` (consumes the codegened predicates.edn)
- `verifiers/bermuda/scripts/run_verification.py` (currently calls real verifier only when `stub_verifier=False`)
- `verifiers/bermuda/tests/test_run_verification.py` (currently uses `stub_verifier=True` default)
- `verifiers/bermuda/package.json` (needs `nbb` devDep and `booklogic-compile` script — borrow from `skills/neurosym-forge/assets/project-template/package.json.tmpl`)
- `verifiers/bermuda/cljs-orchestrator/src/main/bermuda/core.cljs` (the `verify` dispatch entry the CI job invokes)
- `examples/bermuda-manual/claims/ledger.jsonl` (append-only contract — four new claims at the tail)
- `examples/bermuda-manual/book/releases/6.0.0/chapter-bundles/ch-02-v6/draft.md` — line 44 contains "Richard Norwood divided the colony into eight parishes" (the canonical drift the D13 smoke triggers; this prose plus the ledger's nine-parish invariant produces the unsat we need)
- `examples/bermuda-manual/qa-config.yaml` (must already contain `enable_verification: true` — confirm)
- `tools/synthesize_bermuda_ledger.py` (extend if needed to emit quantitative claims; this PR's Phase 3 appends manually so the extension is optional)
- `.github/workflows/ci.yml` (the file you'll append to in Phase 5)
- `skills/book-qa/scripts/lint_artifact.py` § `lint_d13_verification_unsat` (the function whose output the smoke asserts)
- `AGENTS.md` § commit-hygiene rules

**Worktree:** `C:\Users\charl\code\russellian-book-suite-booklogic-pr5` on branch `feat/booklogic-pr5`.

```powershell
cd C:\Users\charl\code
git -C russellian-book-suite worktree add russellian-book-suite-booklogic-pr5 -b feat/booklogic-pr5 origin/main
cd russellian-book-suite-booklogic-pr5
```

If the worktree directory already exists from a previous attempt, remove it first:

```powershell
git -C russellian-book-suite worktree remove russellian-book-suite-booklogic-pr5 --force
```

**Test invocation:**
- neurosym-forge: `cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest tests/ -q`
- book-qa: `cd skills/book-qa && python -m pytest tests/ -q`
- book-thesis: `cd skills/book-thesis && python -m pytest tests/ -q`
- bermuda: `cd verifiers/bermuda && .venv/Scripts/python.exe -m pytest tests/ -q`

**Baseline test counts (record at start; deviations from these numbers in your final sweep mean something broke):**
- neurosym-forge: ~146 (post-PR-3 + PR-4 deltas)
- book-knowledge: ~140
- book-qa: ~47 (+ any PR-4 additions)
- verifiers/bermuda: 23

**Z3 build expectation.** `cargo build --features z3` with the `bundled` flag invokes cmake and a C++17 toolchain. On `ubuntu-latest` this works once `apt-get install -y cmake build-essential` runs. On Windows local dev it depends on whether MSVC + cmake are installed and on PATH. Phase 4 attempts the local build for fast iteration but Phase 5 is the canonical CI gate — Phase 4 is allowed to fail and the plan captures the failure for diagnostic purposes; CI is the wall.

**Commit hygiene:** terse human commits, no AI attribution, no Co-Authored-By, one problem per commit. Subject ≤72 chars, imperative mood.

---

## File Structure

### Created

```
verifiers/bermuda/rules/
├── sorts.edn                                       NEW (rewrite)
├── lifts.edn                                       NEW
├── rules.edn                                       NEW
├── constraints.edn                                 NEW
├── queries.edn                                     NEW
└── remedies.edn                                    NEW

verifiers/bermuda/rust-verifier/src/
└── axioms.rs                                       NEW (generated, checked in)

verifiers/bermuda/tests/
├── test_booklogic_compile_bermuda.py               NEW
├── test_axioms_lockstep.py                         NEW
├── test_quantitative_claims.py                     NEW
├── test_prose_patterns_loads_lifts_table.py        NEW
├── test_d13_end_to_end.py                          NEW
└── fixtures/
    └── chapter_ch02_eight_parishes.md              NEW

.github/workflows/ci.yml                            MODIFIED (jobs appended)
```

### Modified

```
verifiers/bermuda/rules/
└── predicates.edn                                  REWRITE: BookLogic defpredicate forms

verifiers/bermuda/rust-verifier/
├── Cargo.toml                                      no edit; z3+bundled already declared
└── src/
    ├── lib.rs                                      drop `mod canonical;`; add `mod axioms;`
    └── canonical.rs                                DELETED

verifiers/bermuda/scripts/
└── prose_patterns.py                               thin wrapper around lifts codegen table

verifiers/bermuda/
└── package.json                                    add nbb devDep + booklogic-compile script

examples/bermuda-manual/claims/
└── ledger.jsonl                                    append 4 quantitative claims

verifiers/bermuda/tests/
└── test_run_verification.py                        drop stub_verifier=True default

tools/
└── synthesize_bermuda_ledger.py                    OPTIONAL: emit quantitative claims (Phase 3 task 3.5)

docs/specs/
└── 2026-05-14-booklogic-v0.4-mission-design.md    footer note under § D4
```

`canonical.rs`'s assertion content (parishes-count=9, named-islands-and-rocks=181, BMD/USD parity, L. F. Wade on St. David's Island, cedar binomial `Juniperus bermudiana`) becomes five `defconstraint` forms in `constraints.edn`. Four new `defconstraint` forms cover the quantitative predicates. The generated `axioms.rs` reproduces every Z3 call previously emitted by `canonical.rs::assert_bermuda_axioms` (without the legacy `assert_tracked_atom`, which lives in `smt.rs`).

---

## Phase 0: Pre-flight verification

### Task 0.1: Confirm baseline test counts and tool versions

**Files:** none modified.

- [ ] **Step 1: Verify Node + nbb.**

```powershell
node --version
npm --version
npx nbb --version
```

Expected: `node` ≥ v22, `npm` ≥ v10, `nbb` prints any version. If `nbb` is missing, `npm install -g nbb` (or accept the auto-install on first invocation).

- [ ] **Step 2: Verify Rust toolchain.**

```powershell
cargo --version
rustc --version
```

Expected: `cargo` and `rustc` both print a version. If absent, install via `rustup`.

- [ ] **Step 3: Baseline test counts.**

```powershell
cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest tests/ -q --tb=no 2>&1 | tail -3
cd ../book-qa && python -m pytest tests/ -q --tb=no 2>&1 | tail -3
cd ../book-thesis && python -m pytest tests/ -q --tb=no 2>&1 | tail -3
cd ../../verifiers/bermuda && .venv/Scripts/python.exe -m pytest tests/ -q --tb=no 2>&1 | tail -3
```

Record the numbers. Expected approximately: forge ~146, book-qa ~47, book-thesis ~30, bermuda 23. Numbers vary slightly depending on what PR-cleanup, PR-D2, and PR-4 actually shipped.

- [ ] **Step 4: Sanity-check the spec's "ch-02 parish-count drift" prose.**

```powershell
.venv/Scripts/python.exe -c "import pathlib; t = pathlib.Path('examples/bermuda-manual/book/releases/6.0.0/chapter-bundles/ch-02-v6/draft.md').read_text(); print([l for l in t.split('\n') if 'parish' in l.lower()])"
```

Expected: at least one line contains "eight parishes" or similar (line 44 in current main: "Richard Norwood divided the colony into eight parishes"). The ledger says nine (`clm-2026-000008`). This is the drift PR-5's D13 smoke triggers.

- [ ] **Step 5: Sanity-check qa-config enables verification.**

```powershell
type examples/bermuda-manual/qa-config.yaml
```

Expected: contains `enable_verification: true`. If not, the D13 hook in book-qa stays dormant. Edit if absent.

---

## Phase 1: Author Bermuda BookLogic source

This phase is a TDD sweep over seven BookLogic source files. Each new file gets a failing test (the BookLogic compiler must parse it cleanly), then the file content, then green. No codegen yet — that's Phase 2.

### Task 1.1: `sorts.edn`

**Files:**
- Create: `verifiers/bermuda/rules/sorts.edn`
- Create: `verifiers/bermuda/tests/test_booklogic_compile_bermuda.py`

- [ ] **Step 1: Write the failing test for sorts.edn.**

```python
# verifiers/bermuda/tests/test_booklogic_compile_bermuda.py
"""End-to-end checks that the Bermuda BookLogic source files parse cleanly
through the BookLogic compiler. Each test reads one file via the EDN reader
and asserts the expected form heads are present."""
from __future__ import annotations

from pathlib import Path

import pytest

# scripts/__init__.py extends this package's __path__ to include forge's
# scripts/ dir, so the imports below resolve to neurosym-forge's modules.
from scripts._edn_reader import Keyword, EdnReadError, read_edn  # noqa: E402
from scripts._io import read_edn_file  # noqa: E402


RULES_DIR = Path(__file__).resolve().parents[1] / "rules"


def _read_forms(name: str) -> list:
    """Load a BookLogic source file and return its :forms vector."""
    data = read_edn_file(RULES_DIR / name)
    return data.get(Keyword("forms"), [])


def _heads(forms: list) -> list[str]:
    """Return the head symbol of each form as a string ('defsort', etc.)."""
    out = []
    for f in forms:
        if isinstance(f, list) and f:
            out.append(str(f[0]))
    return out


# ---------- sorts.edn ----------

def test_sorts_edn_parses() -> None:
    forms = _read_forms("sorts.edn")
    assert len(forms) >= 9  # 9 sort families minimum


def test_sorts_edn_has_required_sorts() -> None:
    forms = _read_forms("sorts.edn")
    # Each defsort form is (defsort :name); we look at the keyword arg.
    declared = {f[1] for f in forms if isinstance(f, list) and len(f) >= 2}
    # All Bermuda predicate value kinds + the universal entity sort
    expected = {
        Keyword("int"), Keyword("real"), Keyword("bool"),
        Keyword("string"), Keyword("entity"),
        Keyword("formula"), Keyword("verdict"),
        Keyword("claim"), Keyword("source"),
    }
    missing = expected - declared
    assert not missing, f"missing sorts: {missing}"
```

- [ ] **Step 2: Run, expect FAIL.**

```powershell
cd verifiers/bermuda && .venv/Scripts/python.exe -m pytest tests/test_booklogic_compile_bermuda.py::test_sorts_edn_parses tests/test_booklogic_compile_bermuda.py::test_sorts_edn_has_required_sorts -v
```

Expected: both fail because `sorts.edn` doesn't exist (FileNotFoundError) or contains no `defsort` forms.

- [ ] **Step 3: Write `sorts.edn`.**

```clojure
;; verifiers/bermuda/rules/sorts.edn
;; BookLogic sort registry. The :forms vector enumerates every sort
;; (primitive or structured) used by Bermuda's predicates and atoms.
{:forms
 [(defsort :int)
  (defsort :real)
  (defsort :bool)
  (defsort :string)
  (defsort :entity)
  (defsort :formula)
  (defsort :verdict)
  (defsort :claim)
  (defsort :source)]}
```

- [ ] **Step 4: Run, expect PASS.**

```powershell
cd verifiers/bermuda && .venv/Scripts/python.exe -m pytest tests/test_booklogic_compile_bermuda.py::test_sorts_edn_parses tests/test_booklogic_compile_bermuda.py::test_sorts_edn_has_required_sorts -v
```

- [ ] **Step 5: Commit.**

```powershell
git add verifiers/bermuda/rules/sorts.edn verifiers/bermuda/tests/test_booklogic_compile_bermuda.py
git commit -m "bermuda: BookLogic sorts.edn registry"
```

### Task 1.2: `predicates.edn` rewrite

**Files:**
- Modify: `verifiers/bermuda/rules/predicates.edn`
- Modify: `verifiers/bermuda/tests/test_booklogic_compile_bermuda.py`

`predicates.edn` currently carries the v0.2 regex catalog. Replace it with BookLogic `defpredicate` forms. The v0.2 regex catalog moves to `lifts.edn` (Task 1.3). After PR-2 of the broader mission, `predicates.edn` is the codegen target written by the BookLogic compiler; for this Phase the file is hand-authored as BookLogic source. Phase 2 verifies the compiler round-trips it.

- [ ] **Step 1: Append failing tests.**

```python
# Append to tests/test_booklogic_compile_bermuda.py

# ---------- predicates.edn ----------

def test_predicates_edn_parses() -> None:
    forms = _read_forms("predicates.edn")
    assert len(forms) >= 9  # 5 existing + 4 new quantitative


def test_predicates_edn_has_five_existing() -> None:
    forms = _read_forms("predicates.edn")
    names = {f[1] for f in forms if isinstance(f, list) and len(f) >= 2}
    expected = {
        Keyword("parishes-count"),
        Keyword("named-islands-and-rocks"),
        Keyword("currency-pegged-at-parity"),
        Keyword("airport-on-island"),
        Keyword("binomial"),
    }
    missing = expected - names
    assert not missing, f"missing existing predicates: {missing}"


def test_predicates_edn_has_four_new_quantitative() -> None:
    forms = _read_forms("predicates.edn")
    names = {f[1] for f in forms if isinstance(f, list) and len(f) >= 2}
    expected = {
        Keyword("population"),
        Keyword("land-area-km2"),
        Keyword("gdp-usd-billion"),
        Keyword("hospital-beds-kemh"),
    }
    missing = expected - names
    assert not missing, f"missing new predicates: {missing}"


def test_predicates_edn_arity_shape() -> None:
    """Each (defpredicate :name [arg-sorts...] return-sort) has exactly 4 elements."""
    forms = _read_forms("predicates.edn")
    bad = [f for f in forms if not (isinstance(f, list) and len(f) == 4)]
    assert not bad, f"malformed predicate forms: {bad}"
```

- [ ] **Step 2: Run, expect FAIL.**

```powershell
cd verifiers/bermuda && .venv/Scripts/python.exe -m pytest tests/test_booklogic_compile_bermuda.py -k "predicates" -v
```

Expected: all fail because `predicates.edn` still holds the v0.2 regex catalog.

- [ ] **Step 3: Rewrite `predicates.edn`.**

```clojure
;; verifiers/bermuda/rules/predicates.edn
;; BookLogic predicate registry. Each form is
;;   (defpredicate :name [arg-sorts] return-sort)
;; The regex catalog that USED to live in this file moved to lifts.edn.
{:forms
 [;; Five canonical Bermuda predicates (preserved from v0.2 hand-coded catalog)
  (defpredicate :parishes-count            [:entity] :int)
  (defpredicate :named-islands-and-rocks   [:entity] :int)
  (defpredicate :currency-pegged-at-parity [:entity] :bool)
  (defpredicate :airport-on-island         [:entity] :entity)
  (defpredicate :binomial                  [:entity] :string)

  ;; Four quantitative predicates (D4 mission-spec expansion)
  (defpredicate :population         [:entity] :int)
  (defpredicate :land-area-km2      [:entity] :real)
  (defpredicate :gdp-usd-billion    [:entity] :real)
  (defpredicate :hospital-beds-kemh [:entity] :int)]}
```

- [ ] **Step 4: Run, expect PASS.**

```powershell
cd verifiers/bermuda && .venv/Scripts/python.exe -m pytest tests/test_booklogic_compile_bermuda.py -k "predicates" -v
```

- [ ] **Step 5: Commit.**

```powershell
git add verifiers/bermuda/rules/predicates.edn verifiers/bermuda/tests/test_booklogic_compile_bermuda.py
git commit -m "bermuda: BookLogic predicates.edn (5 existing + 4 quantitative)"
```

### Task 1.3: `lifts.edn`

The v0.2 regex catalog from the old `predicates.edn` (captured in pre-flight reading) migrates here as `deflift` forms. Each lift names the predicate it produces; the regex moves verbatim, named-capture groups (`?<n>`, `?<island>`, `?<binomial>`) preserved per spec § D3.

**Files:**
- Create: `verifiers/bermuda/rules/lifts.edn`
- Modify: `verifiers/bermuda/tests/test_booklogic_compile_bermuda.py`

- [ ] **Step 1: Append failing tests.**

```python
# Append to tests/test_booklogic_compile_bermuda.py

# ---------- lifts.edn ----------

def test_lifts_edn_parses() -> None:
    forms = _read_forms("lifts.edn")
    assert len(forms) >= 9  # at least one lift per predicate


def test_lifts_edn_each_form_has_required_options() -> None:
    """Each (deflift name :from V :when V :emit V ...) must declare :from, :when, :emit."""
    forms = _read_forms("lifts.edn")
    for f in forms:
        assert isinstance(f, list) and len(f) >= 5
        # form: (deflift NAME :from V :when V :emit V ...)
        # parse options after the name
        options = f[2:]
        keys = options[0::2]
        assert Keyword("from") in keys, f"lift {f[1]} missing :from"
        assert Keyword("when") in keys, f"lift {f[1]} missing :when"
        assert Keyword("emit") in keys, f"lift {f[1]} missing :emit"


def test_lifts_edn_covers_every_predicate() -> None:
    """Each predicate declared in predicates.edn must have at least one lift
    in lifts.edn whose :emit (fact ...) targets it."""
    preds = {f[1] for f in _read_forms("predicates.edn") if isinstance(f, list)}
    lift_targets = set()
    for f in _read_forms("lifts.edn"):
        if not isinstance(f, list):
            continue
        options = f[2:]
        opts = dict(zip(options[0::2], options[1::2]))
        emit = opts.get(Keyword("emit"))
        # (fact ?claim-id :Subject :pred-name body...) → :pred-name at index 3
        if isinstance(emit, list) and len(emit) >= 4 and str(emit[0]) == "fact":
            lift_targets.add(emit[3])
    missing = preds - lift_targets
    assert not missing, f"predicates without lifts: {missing}"
```

- [ ] **Step 2: Run, expect FAIL.**

```powershell
cd verifiers/bermuda && .venv/Scripts/python.exe -m pytest tests/test_booklogic_compile_bermuda.py -k "lifts" -v
```

Expected: FileNotFoundError or empty :forms.

- [ ] **Step 3: Write `lifts.edn`.**

```clojure
;; verifiers/bermuda/rules/lifts.edn
;; BookLogic lift registry. Each (deflift NAME :from K :when REGEX :emit ATOM
;; ...) compiles to (a) a meander rewrite clause in the CLJS expander and
;; (b) a regex entry in the codegened predicates table that ingest_ledger.py
;; and prose_patterns.py consume.
;;
;; Regexes preserve named-capture groups documented in mission spec § D3.
;; Provenance and confidence default to :inherit (copy from source claim).
{:forms
 [;; ----- five existing Bermuda predicates -----

  (deflift L001-parish-count
    :from   :claim/canonical-text
    :when   "(?P<n>\\d+|nine|eight|seven)\\s+(traditional|major)?\\s*parishes?"
    :emit   (fact ?claim-id :Bermuda :parishes-count (parse-int ?n))
    :word-to-int {"nine" 9 "eight" 8 "seven" 7}
    :provenance :inherit
    :confidence :inherit)

  (deflift L002-parish-count-the
    :from   :claim/canonical-text
    :when   "the\\s+(?P<n>\\d+|nine|eight)\\s+parishes"
    :emit   (fact ?claim-id :Bermuda :parishes-count (parse-int ?n))
    :word-to-int {"nine" 9 "eight" 8}
    :provenance :inherit
    :confidence :inherit)

  (deflift L003-named-islands-and-rocks
    :from   :claim/canonical-text
    :when   "(?P<n>\\d+)\\s+(named\\s+)?islands?\\s+and\\s+rocks?"
    :emit   (fact ?claim-id :Bermuda :named-islands-and-rocks (parse-int ?n))
    :provenance :inherit
    :confidence :inherit)

  (deflift L004-islands-around
    :from   :claim/canonical-text
    :when   "around\\s+(?P<n>\\d+)\\s+islands?"
    :emit   (fact ?claim-id :Bermuda :named-islands-and-rocks (parse-int ?n))
    :provenance :inherit
    :confidence :inherit)

  (deflift L005-islands-approximately
    :from   :claim/canonical-text
    :when   "approximately\\s+(?P<n>\\d+)\\s+islands?"
    :emit   (fact ?claim-id :Bermuda :named-islands-and-rocks (parse-int ?n))
    :provenance :inherit
    :confidence :inherit)

  (deflift L006-currency-peg
    :from   :claim/canonical-text
    :when   "Bermudian\\s+dollar.*?pegged.*?(?:US|United States)\\s+dollar"
    :emit   (fact ?claim-id :BMD :currency-pegged-at-parity true)
    :provenance :inherit
    :confidence :inherit)

  (deflift L007-currency-peg-short
    :from   :claim/canonical-text
    :when   "BMD.*?(?:pegged|parity).*?USD"
    :emit   (fact ?claim-id :BMD :currency-pegged-at-parity true)
    :provenance :inherit
    :confidence :inherit)

  (deflift L008-airport-island
    :from   :claim/canonical-text
    :when   "L\\.?\\s*F\\.?\\s*Wade.*?(?P<island>St\\.?\\s+David's|St\\.?\\s+George's|Bermuda)\\s+Island"
    :emit   (fact ?claim-id :L_F_Wade :airport-on-island ?island)
    :provenance :inherit
    :confidence :inherit)

  (deflift L009-airport-on
    :from   :claim/canonical-text
    :when   "(?:airport|aerodrome).*?(?:on|at)\\s+(?P<island>St\\.?\\s+David's|St\\.?\\s+George's)\\s+Island"
    :emit   (fact ?claim-id :L_F_Wade :airport-on-island ?island)
    :provenance :inherit
    :confidence :inherit)

  (deflift L010-cedar-binomial
    :from   :claim/canonical-text
    :when   "Bermuda\\s+cedar\\s*\\(\\s*\\*?(?P<binomial>[A-Z][a-z]+\\s+[a-z]+)\\*?"
    :emit   (fact ?claim-id :Bermuda_cedar :binomial ?binomial)
    :provenance :inherit
    :confidence :inherit)

  (deflift L011-cedar-binomial-bare
    :from   :claim/canonical-text
    :when   "\\*(?P<binomial>Juniperus\\s+[a-z]+)\\*"
    :emit   (fact ?claim-id :Bermuda_cedar :binomial ?binomial)
    :provenance :inherit
    :confidence :inherit)

  ;; ----- four quantitative predicates -----

  (deflift L012-population
    :from   :claim/canonical-text
    :when   "population\\s+of\\s+(?:approximately\\s+)?(?P<n>\\d{2,3}(?:,\\d{3})*)"
    :emit   (fact ?claim-id :Bermuda :population (parse-int ?n))
    :provenance :inherit
    :confidence :inherit)

  (deflift L013-land-area
    :from   :claim/canonical-text
    :when   "(?P<n>\\d+(?:\\.\\d+)?)\\s+(?:square\\s+kilometres|km2|km\\^2|sq\\s*km)"
    :emit   (fact ?claim-id :Bermuda :land-area-km2 (parse-float ?n))
    :provenance :inherit
    :confidence :inherit)

  (deflift L014-gdp
    :from   :claim/canonical-text
    :when   "GDP\\s+(?:of\\s+)?(?:US)?\\$?(?P<n>\\d+(?:\\.\\d+)?)\\s+billion"
    :emit   (fact ?claim-id :Bermuda :gdp-usd-billion (parse-float ?n))
    :provenance :inherit
    :confidence :inherit)

  (deflift L015-hospital-beds
    :from   :claim/canonical-text
    :when   "KEMH.*?(?P<n>\\d+)\\s+beds?"
    :emit   (fact ?claim-id :KEMH :hospital-beds-kemh (parse-int ?n))
    :provenance :inherit
    :confidence :inherit)]}
```

A note on regex escape doubling: BookLogic source treats `:when` values as EDN strings; the BookLogic compiler from PR-3 strips no escapes. The Python regex engine receives the raw string. `\\d` in an EDN string yields `\d` in Python — correct. The Python codegen target carries the same string.

- [ ] **Step 4: Run, expect PASS.**

```powershell
cd verifiers/bermuda && .venv/Scripts/python.exe -m pytest tests/test_booklogic_compile_bermuda.py -k "lifts" -v
```

- [ ] **Step 5: Commit.**

```powershell
git add verifiers/bermuda/rules/lifts.edn verifiers/bermuda/tests/test_booklogic_compile_bermuda.py
git commit -m "bermuda: BookLogic lifts.edn (regex catalog migrated from predicates.edn)"
```

### Task 1.4: `rules.edn`

The v0.2 `rules/rules.edn` (rewrite rules used by the meander pass) — wrap any existing entries in `defrule` and add one normalising rule for St. David's Island spelling drift. Bermuda has no rewrite rules in main (rules.edn currently doesn't exist; the meander pass is empty), so this file ships with two harmless normalisation rules to exercise the form.

**Files:**
- Create: `verifiers/bermuda/rules/rules.edn`
- Modify: `verifiers/bermuda/tests/test_booklogic_compile_bermuda.py`

- [ ] **Step 1: Append failing tests.**

```python
# Append to tests/test_booklogic_compile_bermuda.py

# ---------- rules.edn ----------

def test_rules_edn_parses() -> None:
    forms = _read_forms("rules.edn")
    assert len(forms) >= 2


def test_rules_edn_form_heads_are_defrule() -> None:
    forms = _read_forms("rules.edn")
    bad = [str(f[0]) for f in forms if isinstance(f, list) and str(f[0]) != "defrule"]
    assert not bad, f"non-defrule forms in rules.edn: {bad}"
```

- [ ] **Step 2: Run, expect FAIL.**

```powershell
cd verifiers/bermuda && .venv/Scripts/python.exe -m pytest tests/test_booklogic_compile_bermuda.py -k "rules" -v
```

- [ ] **Step 3: Write `rules.edn`.**

```clojure
;; verifiers/bermuda/rules/rules.edn
;; BookLogic term-rewrite rules. Each (defrule NAME LHS=RHS :tags [...])
;; compiles to a meander rewrite clause in the CLJS expander. No semantic
;; change from v0.2; the wrapper is the value.
{:forms
 [(defrule R001-normalize-st-davids
    (= (entity "St. David's Island")
       :St_Davids_Island)
    :tags [:normalization :entity])

  (defrule R002-normalize-bmd-symbol
    (= (entity "Bermudian dollar")
       :BMD)
    :tags [:normalization :entity])]}
```

- [ ] **Step 4: Run, expect PASS.**

```powershell
cd verifiers/bermuda && .venv/Scripts/python.exe -m pytest tests/test_booklogic_compile_bermuda.py -k "rules" -v
```

- [ ] **Step 5: Commit.**

```powershell
git add verifiers/bermuda/rules/rules.edn verifiers/bermuda/tests/test_booklogic_compile_bermuda.py
git commit -m "bermuda: BookLogic rules.edn (entity normalisation rewrites)"
```

### Task 1.5: `constraints.edn`

This is the file that, post-codegen, becomes `rust-verifier/src/axioms.rs`. The five existing assertions from `canonical.rs` plus four new quantitative invariants live here.

**Files:**
- Create: `verifiers/bermuda/rules/constraints.edn`
- Modify: `verifiers/bermuda/tests/test_booklogic_compile_bermuda.py`

- [ ] **Step 1: Append failing tests.**

```python
# Append to tests/test_booklogic_compile_bermuda.py

# ---------- constraints.edn ----------

def test_constraints_edn_parses() -> None:
    forms = _read_forms("constraints.edn")
    assert len(forms) >= 9  # 5 existing + 4 quantitative


def test_constraints_edn_each_form_has_backend_and_assert() -> None:
    forms = _read_forms("constraints.edn")
    for f in forms:
        assert isinstance(f, list) and len(f) >= 4
        options = f[2:]
        keys = set(options[0::2])
        assert Keyword("backend") in keys, f"constraint {f[1]} missing :backend"
        assert Keyword("assert") in keys, f"constraint {f[1]} missing :assert"


def test_constraints_edn_covers_canonical_facts() -> None:
    """Every canonical fact previously asserted in canonical.rs must be
    represented by at least one constraint in constraints.edn."""
    names = {str(f[1]) for f in _read_forms("constraints.edn") if isinstance(f, list)}
    expected_canonical = {
        "C001-bermuda-parishes",
        "C002-named-islands-and-rocks",
        "C003-bmd-usd-parity",
        "C004-airport-st-davids",
        "C005-cedar-binomial",
    }
    missing = expected_canonical - names
    assert not missing, f"missing canonical constraints: {missing}"


def test_constraints_edn_includes_quantitative() -> None:
    names = {str(f[1]) for f in _read_forms("constraints.edn") if isinstance(f, list)}
    expected_quant = {
        "C006-population",
        "C007-land-area-km2",
        "C008-gdp-usd-billion",
        "C009-hospital-beds-kemh",
    }
    missing = expected_quant - names
    assert not missing, f"missing quantitative constraints: {missing}"
```

- [ ] **Step 2: Run, expect FAIL.**

```powershell
cd verifiers/bermuda && .venv/Scripts/python.exe -m pytest tests/test_booklogic_compile_bermuda.py -k "constraints" -v
```

- [ ] **Step 3: Write `constraints.edn`.**

The constraint values mirror `canonical.rs` exactly for the five canonical facts. Quantitative values use the most-recent figures captured in the spec discussion: population ≈ 63,918 (2023 Census-of-Population estimate), land-area ≈ 53.2 km², GDP ≈ 7.7 USD billion, KEMH ≈ 90 beds.

```clojure
;; verifiers/bermuda/rules/constraints.edn
;; BookLogic constraints. Each (defconstraint NAME :backend B :assert F
;; :track T :on-unsat M) compiles to a Z3 assert_and_track call in the
;; generated rust-verifier/src/axioms.rs (this PR's Phase 2 output) plus
;; a defect-ticket entry for the verdict-to-qa path.
{:forms
 [;; ----- five canonical facts (preserved from canonical.rs) -----

  (defconstraint C001-bermuda-parishes
    :backend :z3
    :assert  (= (:parishes-count :Bermuda) 9)
    :track   :C001-parishes-count
    :on-unsat {:defect :D13 :severity :critical
               :message "Claim contradicts canonical Bermuda parish count (9)."})

  (defconstraint C002-named-islands-and-rocks
    :backend :z3
    :assert  (= (:named-islands-and-rocks :Bermuda) 181)
    :track   :C002-named-islands
    :on-unsat {:defect :D13 :severity :critical
               :message "Claim contradicts canonical island/rock count (181)."})

  (defconstraint C003-bmd-usd-parity
    :backend :z3
    :assert  (= (:currency-pegged-at-parity :BMD) true)
    :track   :C003-bmd-peg
    :on-unsat {:defect :D13 :severity :critical
               :message "Claim contradicts BMD/USD parity peg."})

  (defconstraint C004-airport-st-davids
    :backend :z3
    :assert  (= (:airport-on-island :L_F_Wade) "St_Davids_Island")
    :track   :C004-airport-island
    :on-unsat {:defect :D13 :severity :critical
               :message "Claim contradicts L. F. Wade airport location (St. David's Island)."})

  (defconstraint C005-cedar-binomial
    :backend :z3
    :assert  (= (:binomial :Bermuda_cedar) "Juniperus bermudiana")
    :track   :C005-cedar-binomial
    :on-unsat {:defect :D13 :severity :critical
               :message "Claim contradicts Bermuda cedar binomial (Juniperus bermudiana)."})

  ;; ----- four quantitative invariants (D4 mission-spec expansion) -----

  (defconstraint C006-population
    :backend :z3
    :assert  (= (:population :Bermuda) 63918)
    :track   :C006-population
    :on-unsat {:defect :D13 :severity :critical
               :message "Claim contradicts canonical Bermuda population (63,918, 2023 estimate)."})

  (defconstraint C007-land-area-km2
    :backend :z3
    :assert  (= (:land-area-km2 :Bermuda) 53.2)
    :track   :C007-land-area-km2
    :on-unsat {:defect :D13 :severity :critical
               :message "Claim contradicts canonical Bermuda land area (53.2 km^2)."})

  (defconstraint C008-gdp-usd-billion
    :backend :z3
    :assert  (= (:gdp-usd-billion :Bermuda) 7.7)
    :track   :C008-gdp-usd-billion
    :on-unsat {:defect :D13 :severity :critical
               :message "Claim contradicts canonical Bermuda GDP (USD 7.7 billion)."})

  (defconstraint C009-hospital-beds-kemh
    :backend :z3
    :assert  (= (:hospital-beds-kemh :KEMH) 90)
    :track   :C009-hospital-beds-kemh
    :on-unsat {:defect :D13 :severity :critical
               :message "Claim contradicts KEMH bed count (90)."})]}
```

- [ ] **Step 4: Run, expect PASS.**

```powershell
cd verifiers/bermuda && .venv/Scripts/python.exe -m pytest tests/test_booklogic_compile_bermuda.py -k "constraints" -v
```

- [ ] **Step 5: Commit.**

```powershell
git add verifiers/bermuda/rules/constraints.edn verifiers/bermuda/tests/test_booklogic_compile_bermuda.py
git commit -m "bermuda: BookLogic constraints.edn (5 canonical + 4 quantitative)"
```

### Task 1.6: `queries.edn`

PR-4 wired Cozo as a real backend behind `defquery`. This file ships one query that exercises that path against the Bermuda KG.

**Files:**
- Create: `verifiers/bermuda/rules/queries.edn`
- Modify: `verifiers/bermuda/tests/test_booklogic_compile_bermuda.py`

- [ ] **Step 1: Append failing tests.**

```python
# Append to tests/test_booklogic_compile_bermuda.py

# ---------- queries.edn ----------

def test_queries_edn_parses() -> None:
    forms = _read_forms("queries.edn")
    assert len(forms) >= 1


def test_queries_edn_each_form_has_backend_find_where() -> None:
    for f in _read_forms("queries.edn"):
        assert isinstance(f, list)
        options = f[2:]
        keys = set(options[0::2])
        assert Keyword("backend") in keys
        assert Keyword("find") in keys
        assert Keyword("where") in keys
```

- [ ] **Step 2: Run, expect FAIL.**

```powershell
cd verifiers/bermuda && .venv/Scripts/python.exe -m pytest tests/test_booklogic_compile_bermuda.py -k "queries" -v
```

- [ ] **Step 3: Write `queries.edn`.**

```clojure
;; verifiers/bermuda/rules/queries.edn
;; BookLogic Cozo queries. Each (defquery NAME :backend :cozo :find [...]
;; :where [...] :on-result M) compiles to a parameterised Cozo script in
;; rust-verifier/src/kg.rs (filled in by PR-4's defquery compiler).
;; Results become defect tickets in book-qa.
{:forms
 [(defquery Q001-low-confidence-load-bearing
    :backend :cozo
    :find    [?claim]
    :where   [(claim/load-bearing ?claim true)
              (claim/posterior   ?claim ?p)
              (< ?p 0.80)]
    :on-result {:defect :posterior-floor
                :severity :warning
                :message "Load-bearing claim below the 0.80 posterior floor."})]}
```

- [ ] **Step 4: Run, expect PASS.**

```powershell
cd verifiers/bermuda && .venv/Scripts/python.exe -m pytest tests/test_booklogic_compile_bermuda.py -k "queries" -v
```

- [ ] **Step 5: Commit.**

```powershell
git add verifiers/bermuda/rules/queries.edn verifiers/bermuda/tests/test_booklogic_compile_bermuda.py
git commit -m "bermuda: BookLogic queries.edn (load-bearing posterior gate)"
```

### Task 1.7: `remedies.edn`

**Files:**
- Create: `verifiers/bermuda/rules/remedies.edn`
- Modify: `verifiers/bermuda/tests/test_booklogic_compile_bermuda.py`

- [ ] **Step 1: Append failing tests.**

```python
# Append to tests/test_booklogic_compile_bermuda.py

# ---------- remedies.edn ----------

def test_remedies_edn_parses() -> None:
    forms = _read_forms("remedies.edn")
    assert len(forms) >= 1


def test_remedies_edn_each_form_has_when_propose() -> None:
    for f in _read_forms("remedies.edn"):
        assert isinstance(f, list)
        options = f[2:]
        keys = set(options[0::2])
        assert Keyword("when") in keys
        assert Keyword("propose") in keys
```

- [ ] **Step 2: Run, expect FAIL.**

```powershell
cd verifiers/bermuda && .venv/Scripts/python.exe -m pytest tests/test_booklogic_compile_bermuda.py -k "remedies" -v
```

- [ ] **Step 3: Write `remedies.edn`.**

```clojure
;; verifiers/bermuda/rules/remedies.edn
;; BookLogic remedy proposals. Each (defremedy NAME :when PATTERN :propose
;; TRANSITION :requires R) compiles to an entry in propose_writeback.py's
;; rule list. :requires :human-review means the proposal does not auto-apply.
{:forms
 [(defremedy W001-unsat-core-to-refutation
    :when    (unsat-core ?claim)
    :propose (ledger/transition ?claim :refuted)
    :requires :human-review)]}
```

- [ ] **Step 4: Run, expect PASS.**

```powershell
cd verifiers/bermuda && .venv/Scripts/python.exe -m pytest tests/test_booklogic_compile_bermuda.py -k "remedies" -v
```

- [ ] **Step 5: Sweep the whole BookLogic-compile test file, expect all PASS.**

```powershell
cd verifiers/bermuda && .venv/Scripts/python.exe -m pytest tests/test_booklogic_compile_bermuda.py -v
```

Expected: 16-18 tests, all green.

- [ ] **Step 6: Commit.**

```powershell
git add verifiers/bermuda/rules/remedies.edn verifiers/bermuda/tests/test_booklogic_compile_bermuda.py
git commit -m "bermuda: BookLogic remedies.edn (unsat-core to refuted transition)"
```

---

## Phase 2: Codegen + lockstep

PR-4 added `defconstraint` → `axioms.rs` codegen behind the BookLogic compiler. This phase invokes the compiler against Bermuda's `rules/`, commits the generated `axioms.rs`, deletes `canonical.rs`, retargets `lib.rs`, and rewrites `prose_patterns.py` as a thin loader of the codegened regex table.

### Task 2.1: Add BookLogic compile script to `package.json`

The Bermuda `package.json` predates BookLogic and lacks the `nbb` devDep + `booklogic-compile` script. The project-template scaffolder declares these (see `assets/project-template/package.json.tmpl`); copy the relevant entries.

**Files:**
- Modify: `verifiers/bermuda/package.json`
- Create: `verifiers/bermuda/cljs-orchestrator/src/main/bermuda/booklogic.cljs` (mirror of the template, slug-substituted)

- [ ] **Step 1: Write a failing test for the booklogic-compile script.**

```python
# Append to tests/test_booklogic_compile_bermuda.py

import json
import subprocess

def test_package_json_declares_booklogic_compile() -> None:
    pkg = json.loads((RULES_DIR.parent / "package.json").read_text(encoding="utf-8"))
    assert "nbb" in pkg.get("devDependencies", {}), \
        "package.json must declare nbb as a devDependency"
    assert "booklogic-compile" in pkg.get("scripts", {}), \
        "package.json must declare booklogic-compile script"


def test_booklogic_namespace_file_exists() -> None:
    p = (RULES_DIR.parent / "cljs-orchestrator" / "src" / "main"
         / "bermuda" / "booklogic.cljs")
    assert p.exists(), f"BookLogic compiler missing at {p}"
    text = p.read_text(encoding="utf-8")
    assert "ns bermuda.booklogic" in text, "namespace declaration must read bermuda.booklogic"
```

- [ ] **Step 2: Run, expect FAIL.**

```powershell
cd verifiers/bermuda && .venv/Scripts/python.exe -m pytest tests/test_booklogic_compile_bermuda.py -k "package_json or namespace_file" -v
```

- [ ] **Step 3: Update `verifiers/bermuda/package.json`.**

```json
{
  "name": "bermuda",
  "private": true,
  "type": "commonjs",
  "scripts": {
    "build:cljs":         "shadow-cljs release main",
    "build:rust":         "cd rust-verifier && napi build --platform --release ../cljs-orchestrator/native",
    "build":              "npm run build:rust && npm run build:cljs",
    "verify":             "node cljs-orchestrator/dist/main.js",
    "booklogic-compile":  "nbb -m bermuda.booklogic ."
  },
  "devDependencies": {
    "shadow-cljs":  "^2.28.20",
    "@napi-rs/cli": "^3.0.0",
    "nbb":          "^1.4.0"
  }
}
```

- [ ] **Step 4: Copy the BookLogic compiler namespace into Bermuda.**

The template at `skills/neurosym-forge/assets/project-template/cljs-orchestrator/src/main/__project__/booklogic.cljs.tmpl` carries the PR-3 expander for `defsort` / `defpredicate` / `deflift` plus PR-4's additions for `defrule` / `defconstraint` / `defquery` / `defremedy`. Render it with `{{ project_slug }}` → `bermuda`:

```powershell
.venv/Scripts/python.exe -c "import pathlib; t = pathlib.Path('../../skills/neurosym-forge/assets/project-template/cljs-orchestrator/src/main/__project__/booklogic.cljs.tmpl').read_text(encoding='utf-8'); pathlib.Path('cljs-orchestrator/src/main/bermuda').mkdir(parents=True, exist_ok=True); pathlib.Path('cljs-orchestrator/src/main/bermuda/booklogic.cljs').write_text(t.replace('{{ project_slug }}', 'bermuda'), encoding='utf-8')"
```

- [ ] **Step 5: Run, expect PASS.**

```powershell
cd verifiers/bermuda && .venv/Scripts/python.exe -m pytest tests/test_booklogic_compile_bermuda.py -k "package_json or namespace_file" -v
```

- [ ] **Step 6: Commit.**

```powershell
git add verifiers/bermuda/package.json verifiers/bermuda/cljs-orchestrator/src/main/bermuda/booklogic.cljs verifiers/bermuda/tests/test_booklogic_compile_bermuda.py
git commit -m "bermuda: wire nbb + bermuda.booklogic compiler namespace"
```

### Task 2.2: Run the BookLogic compiler and commit generated axioms.rs

**Files:**
- Create: `verifiers/bermuda/rust-verifier/src/axioms.rs`
- Create: `verifiers/bermuda/tests/test_axioms_lockstep.py`

- [ ] **Step 1: Install nbb deps + bring up the compiler.**

```powershell
cd verifiers/bermuda
npm install
npx nbb --version
```

Expected: `npm install` succeeds; `nbb --version` prints. If `npm install` fails on the `napi/cli` package on Windows, drop it temporarily (PR-5 doesn't need the napi pipeline at this point) — but document that any deletion is reverted before commit.

- [ ] **Step 2: Write a failing lockstep test.**

```python
# verifiers/bermuda/tests/test_axioms_lockstep.py
"""Check that the checked-in rust-verifier/src/axioms.rs is byte-identical to
the BookLogic compiler's regenerated output. If a contributor edits
constraints.edn but forgets to rerun the compiler, this test catches it."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

BERMUDA_ROOT = Path(__file__).resolve().parents[1]
AXIOMS_RS = BERMUDA_ROOT / "rust-verifier" / "src" / "axioms.rs"


@pytest.fixture()
def regenerated_axioms(tmp_path: Path) -> str:
    """Run `npm run booklogic-compile` in a copy of the project and return
    the regenerated axioms.rs body. Skips if nbb is unavailable."""
    if shutil.which("npx") is None:
        pytest.skip("npx not available; cannot regenerate axioms.rs")
    work = tmp_path / "bermuda"
    shutil.copytree(BERMUDA_ROOT, work, ignore=shutil.ignore_patterns(
        "node_modules", "target", "dist", ".venv", "__pycache__", "work"
    ))
    # Reuse the repo's node_modules if present to skip a 60-second npm install.
    src_nm = BERMUDA_ROOT / "node_modules"
    if src_nm.exists():
        (work / "node_modules").symlink_to(src_nm, target_is_directory=True)
    else:
        subprocess.run(["npm", "install"], cwd=str(work), check=True,
                       shell=False, capture_output=True)
    result = subprocess.run(
        ["npx", "nbb", "-m", "bermuda.booklogic", "."],
        cwd=str(work), check=True, capture_output=True, text=True,
    )
    regenerated = work / "rust-verifier" / "src" / "axioms.rs"
    assert regenerated.exists(), f"compiler did not write axioms.rs (stdout: {result.stdout})"
    return regenerated.read_text(encoding="utf-8")


def test_axioms_rs_committed_is_in_sync(regenerated_axioms: str) -> None:
    """The checked-in axioms.rs must be byte-identical to the compiler's output."""
    on_disk = AXIOMS_RS.read_text(encoding="utf-8")
    assert on_disk == regenerated_axioms, (
        "axioms.rs is out of sync with constraints.edn. "
        "Run `npm run booklogic-compile` in verifiers/bermuda/ and commit the result."
    )


def test_axioms_rs_asserts_canonical_parishes() -> None:
    text = AXIOMS_RS.read_text(encoding="utf-8")
    assert "parishes_count_Bermuda" in text or "parishes-count_Bermuda" in text
    assert "9" in text


def test_axioms_rs_uses_assert_and_track() -> None:
    text = AXIOMS_RS.read_text(encoding="utf-8")
    # Every constraint must be tracked so the unsat core points back.
    assert text.count("assert_and_track") >= 9, \
        "expected ≥9 tracked assertions (5 canonical + 4 quantitative)"
```

- [ ] **Step 3: Run, expect FAIL.**

```powershell
cd verifiers/bermuda && .venv/Scripts/python.exe -m pytest tests/test_axioms_lockstep.py -v
```

Expected: failures because `axioms.rs` doesn't exist yet.

- [ ] **Step 4: Run the BookLogic compiler.**

```powershell
cd verifiers/bermuda
npm run booklogic-compile
ls rust-verifier/src/axioms.rs
```

Expected: `axioms.rs` appears, written by the compiler. The compiler also rewrites `rules/predicates.edn` to the codegened legacy regex table (Phase 3 of PR-3 closed this loop). The hand-authored BookLogic forms in `predicates.edn` from Task 1.2 would be CLOBBERED by this step — we don't want that.

The fix: rename the BookLogic source. Bermuda authoritative BookLogic source lives in `rules/booklogic/predicates.edn` (note the subdir), and the compiler's emit-target is `rules/predicates.edn` (the legacy regex table). This mirrors the project-template layout from PR-3.

- [ ] **Step 4a: Relocate Bermuda BookLogic source under `rules/booklogic/`.**

```powershell
cd verifiers/bermuda
mkdir -Force rules/booklogic | Out-Null
git mv rules/sorts.edn         rules/booklogic/sorts.edn
git mv rules/predicates.edn    rules/booklogic/predicates.edn
git mv rules/lifts.edn         rules/booklogic/lifts.edn
git mv rules/rules.edn         rules/booklogic/rules.edn
git mv rules/constraints.edn   rules/booklogic/constraints.edn
git mv rules/queries.edn       rules/booklogic/queries.edn
git mv rules/remedies.edn      rules/booklogic/remedies.edn
```

Update `tests/test_booklogic_compile_bermuda.py` so `RULES_DIR` points to `rules/booklogic`:

```python
RULES_DIR = Path(__file__).resolve().parents[1] / "rules" / "booklogic"
```

Update `tests/test_axioms_lockstep.py` similarly if it references `RULES_DIR`.

Update `test_package_json_declares_booklogic_compile` so the path math still works (it walks `RULES_DIR.parent / "package.json"` — adjust to `RULES_DIR.parents[1] / "package.json"`).

Rerun Phase 1's compile tests; expect green:

```powershell
cd verifiers/bermuda && .venv/Scripts/python.exe -m pytest tests/test_booklogic_compile_bermuda.py -v
```

- [ ] **Step 4b: Rerun the compiler now that source is in the right subdir.**

```powershell
npm run booklogic-compile
```

Expected stdout: `[booklogic] compiled 9 sorts, 9 predicates, 15 lifts → rules/predicates.edn` (or similar — the PR-4 compiler also writes axioms.rs and the kg.rs Cozo bundle; the exact wording depends on PR-4's println text).

- [ ] **Step 5: Confirm the generated files.**

```powershell
ls rust-verifier/src/axioms.rs
type rules/predicates.edn | Select-Object -First 5
```

Expected: `axioms.rs` exists; `rules/predicates.edn` now matches the legacy v0.2 shape (codegened from lifts).

- [ ] **Step 6: Run lockstep tests, expect PASS.**

```powershell
cd verifiers/bermuda && .venv/Scripts/python.exe -m pytest tests/test_axioms_lockstep.py -v
```

- [ ] **Step 7: Commit.**

```powershell
git add verifiers/bermuda/rules/booklogic/ verifiers/bermuda/rules/predicates.edn verifiers/bermuda/rust-verifier/src/axioms.rs verifiers/bermuda/tests/test_booklogic_compile_bermuda.py verifiers/bermuda/tests/test_axioms_lockstep.py
git commit -m "bermuda: generate axioms.rs + codegened predicates.edn from BookLogic source"
```

### Task 2.3: Delete `canonical.rs`, rewire `lib.rs`

**Files:**
- Delete: `verifiers/bermuda/rust-verifier/src/canonical.rs`
- Modify: `verifiers/bermuda/rust-verifier/src/lib.rs`

- [ ] **Step 1: Append failing test.**

```python
# Append to tests/test_axioms_lockstep.py

def test_canonical_rs_is_gone() -> None:
    p = BERMUDA_ROOT / "rust-verifier" / "src" / "canonical.rs"
    assert not p.exists(), "canonical.rs must be deleted; axioms.rs supersedes it"


def test_lib_rs_declares_axioms_mod_not_canonical() -> None:
    text = (BERMUDA_ROOT / "rust-verifier" / "src" / "lib.rs").read_text(encoding="utf-8")
    assert "mod axioms" in text, "lib.rs must declare `mod axioms;`"
    assert "mod canonical" not in text, "lib.rs must not declare `mod canonical;`"
```

- [ ] **Step 2: Run, expect FAIL.**

```powershell
cd verifiers/bermuda && .venv/Scripts/python.exe -m pytest tests/test_axioms_lockstep.py -k "canonical_rs_is_gone or lib_rs_declares" -v
```

- [ ] **Step 3: Delete `canonical.rs` and update `lib.rs`.**

```powershell
git rm verifiers/bermuda/rust-verifier/src/canonical.rs
```

Edit `verifiers/bermuda/rust-verifier/src/lib.rs`:

```rust
#![deny(clippy::all)]
use napi_derive::napi;

mod ir;
mod axioms;
mod smt;
mod eqsat;
mod kg;
mod typeset;

#[napi]
pub fn verify_formulas(formulas_edn: String) -> napi::Result<String> {
    let formulas = ir::parse_formulas(&formulas_edn)
        .map_err(|e| napi::Error::from_reason(format!("parse: {e}")))?;
    let verdict = smt::check_all(&formulas)
        .map_err(|e| napi::Error::from_reason(format!("smt: {e}")))?;
    let kg_summary = kg::ingest_and_summarize(&verdict.verified)
        .map_err(|e| napi::Error::from_reason(format!("kg: {e}")))?;
    let mut out = verdict;
    out.graph_summary = Some(kg_summary);
    Ok(ir::emit_verdict(&out))
}

#[napi]
pub fn saturate(terms_edn: String, rules_edn: String) -> napi::Result<String> {
    eqsat::saturate(&terms_edn, &rules_edn)
        .map_err(|e| napi::Error::from_reason(e.to_string()))
}

#[napi]
pub fn render_pdf(latex: String, out_path: String) -> napi::Result<()> {
    typeset::render(&latex, &out_path)
        .map_err(|e| napi::Error::from_reason(e.to_string()))
}
```

`smt::check_all` already calls `crate::axioms::assert_axioms` (see `smt.rs` line 33). The PR-4 codegen MUST emit a function with that exact signature; if it instead emits `assert_bermuda_axioms` (matching the deleted `canonical.rs`), update `smt.rs` line 33 to call whatever the generated entry point is.

- [ ] **Step 4: Run, expect PASS.**

```powershell
cd verifiers/bermuda && .venv/Scripts/python.exe -m pytest tests/test_axioms_lockstep.py -k "canonical_rs_is_gone or lib_rs_declares" -v
```

- [ ] **Step 5: Commit.**

```powershell
git add verifiers/bermuda/rust-verifier/src/lib.rs verifiers/bermuda/rust-verifier/src/canonical.rs verifiers/bermuda/tests/test_axioms_lockstep.py
git commit -m "bermuda: drop canonical.rs; lib.rs wires generated axioms mod"
```

### Task 2.4: `prose_patterns.py` becomes a thin loader

After the codegen, `rules/predicates.edn` is the legacy regex table — same shape `prose_patterns.py` already consumes. The current `prose_patterns.py` already loads `rules/predicates.edn` via `_load_predicates`. The "thin wrapper" the spec calls for is preserving this loader against the new codegened table — and adding a guard that fails fast if the table is missing (which means the user forgot to run `booklogic-compile`).

**Files:**
- Modify: `verifiers/bermuda/scripts/prose_patterns.py`
- Create: `verifiers/bermuda/tests/test_prose_patterns_loads_lifts_table.py`

- [ ] **Step 1: Write the failing test.**

```python
# verifiers/bermuda/tests/test_prose_patterns_loads_lifts_table.py
"""prose_patterns.py is a thin loader of the codegened regex table written
to rules/predicates.edn by `npm run booklogic-compile`. These tests confirm
the loader contract and that every predicate declared in
rules/booklogic/predicates.edn has at least one regex available at runtime."""
from __future__ import annotations

from pathlib import Path

import pytest

from scripts._edn_reader import Keyword  # noqa: E402
from scripts._io import read_edn_file  # noqa: E402

from scripts.prose_patterns import _load_predicates, extract_pass_a

BERMUDA_ROOT = Path(__file__).resolve().parents[1]


def test_loader_returns_keyword_keyed_dict() -> None:
    preds = _load_predicates()
    assert isinstance(preds, dict)
    # Codegened entries keyed by predicate keyword.
    assert any(isinstance(k, Keyword) for k in preds.keys()) or len(preds) >= 9


def test_every_booklogic_predicate_has_a_codegened_regex() -> None:
    """Walk the BookLogic predicates source and confirm each appears in the
    codegened regex table (after the compiler ran)."""
    bl_preds_path = BERMUDA_ROOT / "rules" / "booklogic" / "predicates.edn"
    data = read_edn_file(bl_preds_path)
    forms = data.get(Keyword("forms"), [])
    declared = {str(f[1]).lstrip(":") for f in forms if isinstance(f, list)}
    preds = _load_predicates()
    # Codegen keys are predicate names (strings or keywords). Normalise.
    have = {str(k).lstrip(":") for k in preds.keys()}
    # Permit the lift-name keys ('L001-...') too; what we want is that every
    # predicate's name appears somewhere in the predicate field of an entry.
    fields = set()
    for v in preds.values():
        p = v.get(Keyword("predicate"))
        if p is not None:
            fields.add(str(p).lstrip(":"))
    missing = declared - have - fields
    assert not missing, f"codegened table missing predicates: {missing}"


def test_extract_pass_a_finds_quantitative_population() -> None:
    atoms = extract_pass_a("Bermuda has a population of approximately 63,918 residents.",
                           source_file="t.md")
    pop = [a for a in atoms
           if a.get(Keyword("predicate")) in {":population", Keyword("population")}]
    assert pop, "extractor did not match the :population regex"
    assert pop[0].get(Keyword("value")) == 63918
```

- [ ] **Step 2: Run, expect FAIL** (the third test fails because the v2 raw regex returns "63" via greedy `\d{2,3}`; we then fix the regex).

```powershell
cd verifiers/bermuda && .venv/Scripts/python.exe -m pytest tests/test_prose_patterns_loads_lifts_table.py -v
```

If the third test fails, adjust the lift regex in `rules/booklogic/lifts.edn`:

```clojure
(deflift L012-population
  :from   :claim/canonical-text
  :when   "population\\s+of\\s+(?:approximately\\s+)?(?P<n>\\d{1,3}(?:,\\d{3})+|\\d{4,})"
  :emit   (fact ?claim-id :Bermuda :population (parse-int ?n))
  ...)
```

Note: the `_coerce_value` in `prose_patterns.py` does `int(raw)`, which fails on `"63,918"`. The thin wrapper needs to strip commas before int-coercion. Update `prose_patterns.py::_coerce_value`:

```python
def _coerce_value(m: re.Match, spec: dict) -> Any:
    kind = spec.get(_KW_VALUE_KIND)
    if kind == "bool":
        return spec.get(_KW_VALUE, True)
    if kind == "int":
        raw = m.group("n") if "n" in m.groupdict() else (m.group(1) if m.groups() else None)
        if raw is None:
            return None
        word_to_int = spec.get(_KW_WORD_TO_INT, {})
        mapped = word_to_int.get(raw.lower())
        if mapped is not None:
            return mapped
        cleaned = raw.replace(",", "").strip()
        try:
            return int(cleaned)
        except ValueError:
            return None
    if kind == "real":
        raw = m.group("n") if "n" in m.groupdict() else (m.group(1) if m.groups() else None)
        if raw is None:
            return None
        try:
            return float(raw.replace(",", ""))
        except ValueError:
            return None
    if kind == "string":
        return m.group("binomial").strip()
    if kind == "entity":
        return m.group("island").replace(".", "").replace(" ", "_")
    return None
```

The `real` branch is new — it supports the quantitative `:land-area-km2` and `:gdp-usd-billion` predicates whose `value_kind` is `real`.

After the regex + coercer fix, regenerate the codegened predicates table:

```powershell
cd verifiers/bermuda && npm run booklogic-compile
```

- [ ] **Step 3: Run, expect PASS.**

```powershell
cd verifiers/bermuda && .venv/Scripts/python.exe -m pytest tests/test_prose_patterns_loads_lifts_table.py -v
```

- [ ] **Step 4: Run the existing prose-patterns suite to confirm no regression.**

```powershell
cd verifiers/bermuda && .venv/Scripts/python.exe -m pytest tests/test_prose_patterns.py tests/test_extract_prose.py -v
```

Expect all green.

- [ ] **Step 5: Commit.**

```powershell
git add verifiers/bermuda/scripts/prose_patterns.py verifiers/bermuda/rules/booklogic/lifts.edn verifiers/bermuda/rules/predicates.edn verifiers/bermuda/tests/test_prose_patterns_loads_lifts_table.py
git commit -m "bermuda: prose_patterns.py loads codegened regex table; supports real kind"
```

---

## Phase 3: Quantitative claims in the ledger

Append four new claims to `examples/bermuda-manual/claims/ledger.jsonl`. The append-only contract is preserved: the new claims have fresh `claim_id`s (`clm-2026-000011` through `clm-2026-000014`); the existing 10 stay intact.

### Task 3.1: Failing test asserting the four claims appear

**Files:**
- Create: `verifiers/bermuda/tests/test_quantitative_claims.py`

- [ ] **Step 1: Write the test.**

```python
# verifiers/bermuda/tests/test_quantitative_claims.py
"""Verify that examples/bermuda-manual/claims/ledger.jsonl carries the four
quantitative claims that exercise the new BookLogic predicates."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
LEDGER = REPO_ROOT / "examples" / "bermuda-manual" / "claims" / "ledger.jsonl"


def _all_claims() -> list[dict]:
    rows = []
    for line in LEDGER.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def _latest_per_id() -> dict[str, dict]:
    out = {}
    for r in _all_claims():
        cid = r.get("claim_id")
        if cid:
            out[cid] = r
    return out


@pytest.mark.parametrize("claim_id,expected_predicate", [
    ("clm-2026-000011", "population"),
    ("clm-2026-000012", "land-area-km2"),
    ("clm-2026-000013", "gdp-usd-billion"),
    ("clm-2026-000014", "hospital-beds-kemh"),
])
def test_quantitative_claim_present(claim_id: str, expected_predicate: str) -> None:
    latest = _latest_per_id()
    assert claim_id in latest, f"{claim_id} missing from ledger"
    claim = latest[claim_id]
    assert claim["status"] == "verified", \
        f"{claim_id} must be :status verified (got {claim['status']})"
    # The canonical_text must include enough surface so the lift regex matches.
    assert expected_predicate.split("-")[0] in claim["canonical_text"].lower(), \
        f"{claim_id} canonical_text must mention {expected_predicate}"


def test_ledger_append_only_existing_claims_intact() -> None:
    """Existing claim_ids clm-2026-000001 through 000010 must still appear,
    untouched by the append."""
    latest = _latest_per_id()
    for n in range(1, 11):
        cid = f"clm-2026-{n:06d}"
        assert cid in latest, f"existing {cid} missing — append-only broken"
```

- [ ] **Step 2: Run, expect FAIL.**

```powershell
cd verifiers/bermuda && .venv/Scripts/python.exe -m pytest tests/test_quantitative_claims.py -v
```

Expected: the parametric test fails on all four claim IDs.

- [ ] **Step 3: Append the four claims to `examples/bermuda-manual/claims/ledger.jsonl`.**

```powershell
.venv/Scripts/python.exe <<'PY'
import json
from datetime import datetime, timezone
from pathlib import Path

ledger = Path("../../examples/bermuda-manual/claims/ledger.jsonl")
now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
gen = "synthesize-bermuda-quantitative-2026-05-17"

records = [
    {
        "claim_id": "clm-2026-000011",
        "canonical_text": "Bermuda has a population of approximately 63,918 residents (2023 Census-of-Population estimate).",
        "status": "verified",
        "claim_type": "fact",
        "confidence": 0.95,
        "source_spans": [{"doc_id": "thesis", "locator_text": "invariants/population"}],
        "supports_chapters": [],
        "created_at": now,
        "generated_by_run": gen,
        "review_notes": "Canonical invariant 'population'; cross-cutting fact.",
    },
    {
        "claim_id": "clm-2026-000012",
        "canonical_text": "Bermuda's land area is 53.2 square kilometres.",
        "status": "verified",
        "claim_type": "fact",
        "confidence": 0.95,
        "source_spans": [{"doc_id": "thesis", "locator_text": "invariants/land-area"}],
        "supports_chapters": [],
        "created_at": now,
        "generated_by_run": gen,
        "review_notes": "Canonical invariant 'land-area-km2'; cross-cutting fact.",
    },
    {
        "claim_id": "clm-2026-000013",
        "canonical_text": "Bermuda has a GDP of US$7.7 billion (2023).",
        "status": "verified",
        "claim_type": "fact",
        "confidence": 0.90,
        "source_spans": [{"doc_id": "thesis", "locator_text": "invariants/gdp-usd-billion"}],
        "supports_chapters": [],
        "created_at": now,
        "generated_by_run": gen,
        "review_notes": "Canonical invariant 'gdp-usd-billion'; cross-cutting fact.",
    },
    {
        "claim_id": "clm-2026-000014",
        "canonical_text": "KEMH operates 90 beds across acute, maternity, paediatric, and intensive-care wards.",
        "status": "verified",
        "claim_type": "fact",
        "confidence": 0.85,
        "source_spans": [{"doc_id": "thesis", "locator_text": "invariants/hospital-beds-kemh"}],
        "supports_chapters": [],
        "created_at": now,
        "generated_by_run": gen,
        "review_notes": "Canonical invariant 'hospital-beds-kemh'; cross-cutting fact.",
    },
]

with ledger.open("a", encoding="utf-8") as fh:
    for r in records:
        fh.write(json.dumps(r, sort_keys=True) + "\n")
print(f"appended {len(records)} claims to {ledger}")
PY
```

- [ ] **Step 4: Run, expect PASS.**

```powershell
cd verifiers/bermuda && .venv/Scripts/python.exe -m pytest tests/test_quantitative_claims.py -v
```

- [ ] **Step 5: (OPTIONAL) Mirror the quantitative records into `tools/synthesize_bermuda_ledger.py`.**

Synthesizer currently consults `thesis/bermuda-manual.yaml` § invariants. If you can extend the YAML with four invariant entries (`population`, `land-area`, `gdp-usd-billion`, `hospital-beds-kemh`), the synthesizer will regenerate them on a clean-slate workspace. Otherwise the append in Step 3 stands and is the canonical source. Skip this sub-step unless the thesis YAML already houses invariants of these names; the spec explicitly calls this out as optional.

- [ ] **Step 6: Run the ingester end-to-end to confirm the new claims emit atoms.**

```powershell
cd verifiers/bermuda
.venv/Scripts/python.exe -m scripts.ingest_ledger `
  --ledger ../../examples/bermuda-manual/claims/ledger.jsonl `
  --predicates rules/predicates.edn `
  --out work/claims.edn
Select-String -Path work/claims.edn -Pattern "population|land-area-km2|gdp-usd-billion|hospital-beds-kemh" | Select-Object -First 10
```

Expected: at least four matches across the four predicate keywords. If a quantitative predicate has zero matches, the lift regex didn't fire; revisit Task 1.3 + Task 2.4.

- [ ] **Step 7: Commit.**

```powershell
git add examples/bermuda-manual/claims/ledger.jsonl verifiers/bermuda/tests/test_quantitative_claims.py
git commit -m "bermuda-manual: append 4 quantitative claims (population, land area, GDP, KEMH beds)"
```

---

## Phase 4: Real Z3 build (local, best-effort)

This phase attempts a real `cargo build --features z3,bundled` on the developer's local machine. The Z3 `bundled` flag invokes cmake and a C++17 toolchain. Linux CI is the canonical gate (Phase 5); local Windows succeeds only when MSVC + cmake are installed and on PATH. If the build fails locally, capture diagnostics and move on — Phase 5's CI carries the gate.

### Task 4.1: Attempt local Z3 build

**Files:** none modified.

- [ ] **Step 1: Confirm prerequisites.**

```powershell
cmake --version
where cl       # MSVC compiler driver, on PATH only inside a "x64 Native Tools" prompt
```

If `cmake` is missing, install (`winget install Kitware.CMake` or download from cmake.org). If `cl` is missing, open `x64 Native Tools Command Prompt for VS 2022` and rerun the build commands from there; PowerShell windows launched outside the developer environment will not find MSVC.

- [ ] **Step 2: Build.**

```powershell
cd verifiers/bermuda/rust-verifier
cargo build --features z3 2>&1 | Tee-Object -FilePath ../../../docs/handoffs/2026-05-17-pr5-z3-build.log
```

The `z3 = { features = ["bundled"], optional = true }` declaration in `Cargo.toml` is the source of truth — `--features z3` activates both the dep and its `bundled` sub-feature.

Expected outcomes:

  (a) **Success.** `Finished` line at end, exit 0. Proceed to Step 4 (run unit tests).

  (b) **cmake-not-found.** `cmake-rs` build script panics. Capture the panic; document as `cmake-missing-on-host`; do not retry — Phase 5 covers it.

  (c) **MSVC-not-found.** `linker not found: link.exe` or `error LNK1107`. Capture; document `msvc-not-in-path`; do not retry from this shell.

  (d) **z3-build-incompatible.** C++ compilation error inside vendored Z3 (rare on supported MSVC, common on MinGW). Capture full stderr block; document `z3-cxx-error-<short-tag>`; do not retry — open a follow-up issue if reproducible.

- [ ] **Step 3: Persist the failure log.**

If build failed, the `Tee-Object` redirect captured stderr. Confirm:

```powershell
ls ../../../docs/handoffs/2026-05-17-pr5-z3-build.log
Get-Content ../../../docs/handoffs/2026-05-17-pr5-z3-build.log -Tail 40
```

Add a one-line note at the file's top:

```powershell
$log = Get-Content ../../../docs/handoffs/2026-05-17-pr5-z3-build.log -Raw
Set-Content ../../../docs/handoffs/2026-05-17-pr5-z3-build.log -Value "# Z3 bundled build log captured during PR-5 Phase 4 on $(Get-Date -Format 'yyyy-MM-dd') on $env:COMPUTERNAME ($env:OS). Failure (if any) is documented here; the canonical CI gate lives in Phase 5.`n`n$log"
```

- [ ] **Step 4: If build succeeded, run a Rust smoke test.**

```powershell
cd verifiers/bermuda/rust-verifier
cargo test --features z3 --lib -- --nocapture 2>&1 | Tee-Object -FilePath ../../../docs/handoffs/2026-05-17-pr5-z3-cargo-test.log
```

Expected: at least no panic; `axioms::assert_axioms` is exercised when constructing the solver. The crate has minimal `#[cfg(test)]` coverage, so the goal here is exit 0, not test count.

- [ ] **Step 5: Commit the diagnostic log only (no Rust changes).**

```powershell
git add docs/handoffs/2026-05-17-pr5-z3-build.log
test -f docs/handoffs/2026-05-17-pr5-z3-cargo-test.log && git add docs/handoffs/2026-05-17-pr5-z3-cargo-test.log
git commit -m "pr5: capture local Z3 build diagnostics (CI is the canonical gate)"
```

If the log is empty (Step 2 succeeded cleanly), drop the commit; the success path needs no artifact.

---

## Phase 5: CI jobs for real Z3 build + verify

Two jobs on `ubuntu-latest`. The first builds the Bermuda verifier with `--features z3`. The second builds + runs the verifier end-to-end against the Bermuda workspace and asserts the D13 ticket fires.

### Task 5.1: Add `bermuda-z3-build` and `bermuda-z3-verify` jobs

**Files:**
- Modify: `.github/workflows/ci.yml`

- [ ] **Step 1: Write a failing test that the CI file declares both jobs.**

```python
# Append to tests/test_axioms_lockstep.py

import yaml

def test_ci_yaml_has_bermuda_z3_jobs() -> None:
    ci = yaml.safe_load((BERMUDA_ROOT.parents[1] / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8"))
    jobs = ci.get("jobs", {})
    assert "bermuda-z3-build" in jobs, "bermuda-z3-build job missing from ci.yml"
    assert "bermuda-z3-verify" in jobs, "bermuda-z3-verify job missing from ci.yml"
    assert jobs["bermuda-z3-build"].get("runs-on") == "ubuntu-latest"
    assert jobs["bermuda-z3-verify"].get("runs-on") == "ubuntu-latest"
```

- [ ] **Step 2: Run, expect FAIL.**

```powershell
cd verifiers/bermuda && .venv/Scripts/python.exe -m pytest tests/test_axioms_lockstep.py::test_ci_yaml_has_bermuda_z3_jobs -v
```

- [ ] **Step 3: Append the two jobs to `.github/workflows/ci.yml`.**

```yaml
# Append after the smoke-bermuda-pipeline job:

  bermuda-z3-build:
    name: bermuda verifier z3 build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: install build deps
        run: |
          sudo apt-get update
          sudo apt-get install -y cmake build-essential
      - name: install rust toolchain
        uses: dtolnay/rust-toolchain@stable
      - name: cargo cache
        uses: Swatinem/rust-cache@v2
        with:
          workspaces: verifiers/bermuda/rust-verifier
      - name: cargo build --features z3
        working-directory: verifiers/bermuda/rust-verifier
        run: cargo build --features z3

  bermuda-z3-verify:
    name: bermuda end-to-end verify (real Z3)
    runs-on: ubuntu-latest
    needs: [bermuda-z3-build]
    steps:
      - uses: actions/checkout@v4
      - name: install build deps
        run: |
          sudo apt-get update
          sudo apt-get install -y cmake build-essential
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
          cache: pip
      - uses: actions/setup-node@v4
        with:
          node-version: "22"
      - name: install rust toolchain
        uses: dtolnay/rust-toolchain@stable
      - name: cargo cache
        uses: Swatinem/rust-cache@v2
        with:
          workspaces: verifiers/bermuda/rust-verifier
      - name: install python deps
        run: |
          python -m pip install --upgrade pip
          python -m pip install pyyaml pytest
      - name: install node deps
        working-directory: verifiers/bermuda
        run: npm install
      - name: build cljs orchestrator
        working-directory: verifiers/bermuda
        run: npm run build
      - name: run verifier end-to-end
        working-directory: verifiers/bermuda
        run: |
          .venv/Scripts/python.exe -m scripts.run_verification \
            --workspace ../../examples/bermuda-manual \
            --release 6.0.0 || true
      - name: run book-qa D13 lint
        run: |
          python skills/book-qa/scripts/lint_artifact.py examples/bermuda-manual 6.0.0 || true
      - name: assert D13 ticket appears
        run: |
          python - <<'PY'
          import json, sys
          from pathlib import Path
          defects = Path("examples/bermuda-manual/qa/defects.json")
          assert defects.exists(), f"{defects} missing — book-qa did not run"
          payload = json.loads(defects.read_text(encoding="utf-8"))
          d13 = [d for d in payload if d.get("class_") == "D13"]
          if not d13:
              sys.stderr.write(f"D13 tickets expected; got payload={payload!r}\n")
              sys.exit(1)
          print(f"OK: {len(d13)} D13 ticket(s) emitted")
          PY
      - name: upload verification artifacts
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: bermuda-verify-artifacts
          path: |
            examples/bermuda-manual/qa/verification-defects.json
            examples/bermuda-manual/qa/defects.json
            verifiers/bermuda/work/verdict.edn
          if-no-files-found: warn
```

Notes on the YAML:
- The Linux runner lacks the `.venv` Bermuda's pyproject expects; replace `.venv/Scripts/python.exe` with `python` for the verifier invocation. The plan's snippet currently shows the Windows path — fix when copying into ci.yml:

```yaml
          python -m scripts.run_verification \
            --workspace ../../examples/bermuda-manual \
            --release 6.0.0 || true
```

- `npm run build` invokes `build:rust` (which uses `napi build --platform --release`) and `build:cljs` (shadow-cljs). If the `napi build` invocation duplicates the cargo build done in `bermuda-z3-build`, fine — `Swatinem/rust-cache@v2` reuses artifacts.
- The `|| true` on the verifier invocation lets the run continue when the verifier exits non-zero on an unsat (which is the expected outcome for the smoke); the assertion step downstream is what determines pass/fail.

- [ ] **Step 4: Run actionlint locally if available.**

```powershell
actionlint -color .github/workflows/ci.yml
```

Expected: no errors. If `actionlint` isn't on the host, CI's own `lint-workflow` job catches it on push.

- [ ] **Step 5: Run the Python test, expect PASS.**

```powershell
cd verifiers/bermuda && .venv/Scripts/python.exe -m pytest tests/test_axioms_lockstep.py::test_ci_yaml_has_bermuda_z3_jobs -v
```

- [ ] **Step 6: Commit.**

```powershell
git add .github/workflows/ci.yml verifiers/bermuda/tests/test_axioms_lockstep.py
git commit -m "ci: bermuda-z3-build + bermuda-z3-verify jobs"
```

---

## Phase 6: End-to-end D13 smoke

The ch-02 prose at `examples/bermuda-manual/book/releases/6.0.0/chapter-bundles/ch-02-v6/draft.md` line 44 says "eight parishes"; the ledger's `clm-2026-000008` and the C001 constraint say nine. Real Z3 must return `:unsat` with the offending claim in the core; `book-qa` must emit a D13 critical ticket against that drift.

### Task 6.1: Lock the drift in a chapter fixture

The repo's live ch-02-v6 already has the drift, but we capture a minimal isolated fixture so the unit test is hermetic.

**Files:**
- Create: `verifiers/bermuda/tests/fixtures/chapter_ch02_eight_parishes.md`
- Create: `verifiers/bermuda/tests/test_d13_end_to_end.py`

- [ ] **Step 1: Write the fixture.**

```markdown
<!-- verifiers/bermuda/tests/fixtures/chapter_ch02_eight_parishes.md -->
# Chapter 2 fixture — parish-count drift

This fixture deliberately contradicts the canonical Bermuda parish count.
The surveyor Richard Norwood divided the colony into eight parishes.
This sentence should produce a prose atom with :parishes-count = 8.
The verifier asserts the canonical count is 9 (per the C001 constraint),
so Z3 must return :unsat with the prose claim id in the unsat core, and
book-qa must emit a D13 critical ticket against the drift.
```

- [ ] **Step 2: Write the failing test.**

```python
# verifiers/bermuda/tests/test_d13_end_to_end.py
"""End-to-end D13 smoke. Runs the full verifier against a fixture chapter
containing the canonical parish-count drift. Asserts:

    1. The Rust verifier exits with :unsat.
    2. The unsat core contains the offending prose atom id.
    3. verdict_to_qa emits a verification-defects.json with verdict=unsat.
    4. book-qa.lint_d13_verification_unsat returns ≥1 D13 critical defect.

Skipped when the Rust verifier hasn't been built (PR-5 Phase 4 / CI Phase 5
covers the build); the test is the canonical gate in CI but skips cleanly
on local machines without Z3."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

BERMUDA_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BERMUDA_ROOT.parents[1]
FIXTURE = BERMUDA_ROOT / "tests" / "fixtures" / "chapter_ch02_eight_parishes.md"


def _verifier_built() -> bool:
    """The CLJS bundle and Rust addon must both be present."""
    main_js = BERMUDA_ROOT / "cljs-orchestrator" / "dist" / "main.js"
    return main_js.exists()


@pytest.mark.skipif(not _verifier_built(),
                    reason="Rust+CLJS verifier not built locally; CI is the gate")
def test_d13_fires_on_ch02_parish_count_drift(tmp_path: Path) -> None:
    """Drive the real verifier end-to-end. Workspace is a clean copy of the
    bermuda-manual example with ch-02 prose replaced by the fixture."""
    # 1. Stage workspace.
    workspace = tmp_path / "bermuda-manual"
    shutil.copytree(REPO_ROOT / "examples" / "bermuda-manual", workspace)
    # Replace ch-02 prose with the fixture (preserves manifest.yaml etc.).
    ch02 = workspace / "book" / "releases" / "6.0.0" / "chapter-bundles" / "ch-02-v6" / "draft.md"
    ch02.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")

    # 2. Run the full verifier (real Z3, no stub).
    import sys
    sys.path.insert(0, str(BERMUDA_ROOT))
    from scripts.run_verification import run

    rc = run(
        workspace=workspace,
        release_version="6.0.0",
        project_root=BERMUDA_ROOT,
        stub_verifier=False,
    )
    # rc is 0 on a successful verifier invocation regardless of verdict; we
    # introspect verdict.edn for the actual outcome.
    assert rc == 0, f"verifier exited rc={rc}"

    # 3. Assert verdict.edn says unsat.
    from scripts._io import read_edn_file
    from scripts._edn_reader import Keyword
    verdict_path = BERMUDA_ROOT / "work" / "verdict.edn"
    verdict = read_edn_file(verdict_path)
    assert verdict.get(Keyword("verdict")) in {Keyword("unsat"), "unsat"}, (
        f"expected :unsat verdict, got {verdict.get(Keyword('verdict'))}; "
        f"full verdict={verdict}"
    )

    # 4. Assert at least one prose-extracted claim id appears in the core.
    core = verdict.get(Keyword("core"), [])
    prose_in_core = [c for c in core if str(c).startswith("prose-ch-02")]
    assert prose_in_core or any(c == "clm-2026-000008" for c in core), (
        f"expected ch-02 prose atom or clm-2026-000008 in unsat core; got core={core}"
    )

    # 5. Translate verdict.edn → verification-defects.json.
    from scripts.verdict_to_qa import translate
    qa_dir = workspace / "qa"
    qa_dir.mkdir(parents=True, exist_ok=True)
    translate(verdict_path, qa_dir / "verification-defects.json")

    # 6. Run book-qa lint_d13.
    sys.path.insert(0, str(REPO_ROOT / "skills" / "book-qa"))
    from scripts.lint_artifact import lint_d13_verification_unsat
    defects = lint_d13_verification_unsat(workspace)
    d13 = [d for d in defects if d.class_ == "D13"]
    assert len(d13) >= 1, f"expected ≥1 D13 defect; got {defects}"
    assert all(d.severity == "critical" for d in d13), \
        f"D13 must be critical severity; got {[d.severity for d in d13]}"
```

- [ ] **Step 3: Run on a machine WITHOUT the verifier built, expect SKIP.**

```powershell
cd verifiers/bermuda && .venv/Scripts/python.exe -m pytest tests/test_d13_end_to_end.py -v
```

Expected: `skipped` line ("Rust+CLJS verifier not built locally; CI is the gate"). The test is exercised in CI by `bermuda-z3-verify`.

- [ ] **Step 4: If you completed Phase 4 successfully (local Z3 build), run with the verifier built.**

```powershell
cd verifiers/bermuda && npm run build && .venv/Scripts/python.exe -m pytest tests/test_d13_end_to_end.py -v
```

Expected: PASS — verdict unsat, prose atom in core, D13 critical.

If it fails on local Windows but Phase 4 succeeded, the residual problem is most likely the `napi build` step or the CLJS shadow-cljs build, not the Z3 link. Capture stderr; do not block PR-5 on it.

- [ ] **Step 5: Commit.**

```powershell
git add verifiers/bermuda/tests/fixtures/chapter_ch02_eight_parishes.md verifiers/bermuda/tests/test_d13_end_to_end.py
git commit -m "bermuda: D13 end-to-end smoke (ch-02 parish-count drift)"
```

---

## Phase 7: `test_run_verification.py` migration

Drop the `stub_verifier=True` default. The stub stays available behind explicit opt-in for fast local iteration; CI's `bermuda-z3-verify` job is the real gate.

### Task 7.1: Flip the default

**Files:**
- Modify: `verifiers/bermuda/tests/test_run_verification.py`
- Modify: `verifiers/bermuda/scripts/run_verification.py` (drop the default; keep the param)

- [ ] **Step 1: Write a failing test.**

```python
# Replace the body of tests/test_run_verification.py

from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

from scripts.run_verification import run


def test_run_signature_defaults_to_real_verifier() -> None:
    """`stub_verifier` must default to False so CI exercises the real
    pipeline; the stub stays available behind explicit opt-in."""
    sig = inspect.signature(run)
    p = sig.parameters["stub_verifier"]
    assert p.default is False, (
        f"stub_verifier default must be False (got {p.default!r}); "
        "explicit opt-in only for local fast iteration"
    )


def _seed_workspace(root: Path) -> None:
    (root / "examples" / "test-workspace" / "claims").mkdir(parents=True)
    (root / "examples" / "test-workspace" / "claims" / "ledger.jsonl").write_text(
        '{"claim_id": "clm-2026-000001", "claim_type": "fact",'
        ' "canonical_text": "Bermuda has nine traditional parishes including St. George\'s.",'
        ' "status": "verified", "confidence": 0.9}\n',
        encoding="utf-8",
    )
    (root / "examples" / "test-workspace" / "book" / "releases" / "1.0.0"
     / "chapter-bundles" / "ch-01").mkdir(parents=True)
    (root / "examples" / "test-workspace" / "book" / "releases" / "1.0.0"
     / "chapter-bundles" / "ch-01" / "draft.md").write_text(
        "Bermuda has 8 traditional parishes.", encoding="utf-8",
    )
    (root / "examples" / "test-workspace" / "qa").mkdir()


def test_run_with_explicit_stub(tmp_path: Path, project_root: Path) -> None:
    """The stub remains usable for fast local iteration via explicit opt-in."""
    _seed_workspace(tmp_path)
    workspace = tmp_path / "examples" / "test-workspace"
    rc = run(
        workspace=workspace,
        release_version="1.0.0",
        project_root=project_root,
        stub_verifier=True,
        stub_verdict="unsat",
        stub_core=["clm-2026-000001", "prose-ch-01-001"],
    )
    assert rc == 0
    out = workspace / "qa" / "verification-defects.json"
    assert out.exists()
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["verdict"] == "unsat"
    assert "clm-2026-000001" in payload["core"]


def test_run_with_sat_stub(tmp_path: Path, project_root: Path) -> None:
    _seed_workspace(tmp_path)
    workspace = tmp_path / "examples" / "test-workspace"
    rc = run(workspace=workspace, release_version="1.0.0",
             project_root=project_root, stub_verifier=True,
             stub_verdict="sat", stub_core=[])
    assert rc == 0
    payload = json.loads((workspace / "qa" / "verification-defects.json").read_text())
    assert payload["verdict"] == "sat"
```

- [ ] **Step 2: Run, expect FAIL on `test_run_signature_defaults_to_real_verifier`.**

```powershell
cd verifiers/bermuda && .venv/Scripts/python.exe -m pytest tests/test_run_verification.py -v
```

Expected: the signature test fails because the current default is `False` for `stub_verifier` — actually re-check `run_verification.py`:

```powershell
Select-String -Path scripts/run_verification.py -Pattern "stub_verifier"
```

The current signature is `stub_verifier: bool = False` (per pre-flight reading). Good — the default is already `False`. The two pre-existing tests pass `stub_verifier=True` explicitly. The signature test will pass IMMEDIATELY because the default already matches the spec; this Task's only real work is making the test explicit and removing any place where `stub_verifier=True` was the silent default elsewhere.

- [ ] **Step 3: Audit other callsites.**

```powershell
cd verifiers/bermuda && Select-String -Path scripts -Pattern "stub_verifier" -SimpleMatch
```

If any `scripts/*.py` invokes `run(...)` without an explicit `stub_verifier=...`, the default takes effect. The default is `False` → real verifier. Good. No change required.

- [ ] **Step 4: Run, expect PASS.**

```powershell
cd verifiers/bermuda && .venv/Scripts/python.exe -m pytest tests/test_run_verification.py -v
```

- [ ] **Step 5: Commit.**

```powershell
git add verifiers/bermuda/tests/test_run_verification.py
git commit -m "bermuda: assert stub_verifier=False default; stub now explicit opt-in"
```

---

## Phase 8: Mission spec footer update

Edit the mission spec to note that PR-5 closed § D4 — the four mission deliverables, plus the new quantitative predicates, plus the real-Z3 CI gate. Adds a small dated line at the end of § D4.

### Task 8.1: Update `docs/specs/2026-05-14-booklogic-v0.4-mission-design.md` § D4

**Files:**
- Modify: `docs/specs/2026-05-14-booklogic-v0.4-mission-design.md`

- [ ] **Step 1: Identify the insertion point.**

```powershell
cd C:\Users\charl\code\russellian-book-suite-booklogic-pr5
Select-String -Path docs/specs/2026-05-14-booklogic-v0.4-mission-design.md -Pattern "## D4|## D5" -SimpleMatch
```

Confirm § D4 starts around line 285 ("## D4 — Bermuda migration") and § D5 starts around line 309 ("## D5 — osmotic-pressure showcase").

- [ ] **Step 2: Append a closure note at the end of § D4 (immediately before "## D5").**

```markdown
### Closure note (2026-05-17)

PR-5 (`feat/booklogic-pr5`) landed § D4. Concretely:

- `verifiers/bermuda/rules/booklogic/` now hosts seven BookLogic source files (`sorts.edn`, `predicates.edn`, `lifts.edn`, `rules.edn`, `constraints.edn`, `queries.edn`, `remedies.edn`).
- `rust-verifier/src/canonical.rs` is deleted; `rust-verifier/src/axioms.rs` is generated from `constraints.edn` and checked in; `test_axioms_lockstep.py` enforces byte-identical regeneration.
- The five canonical predicates plus four new quantitative predicates (`population`, `land-area-km2`, `gdp-usd-billion`, `hospital-beds-kemh`) ship in the codegened regex table that `prose_patterns.py` and `ingest_ledger.py` consume.
- `examples/bermuda-manual/claims/ledger.jsonl` carries four new appended claims (`clm-2026-000011` through `clm-2026-000014`).
- Two new CI jobs on `ubuntu-latest`: `bermuda-z3-build` (cargo build with the `z3,bundled` feature) and `bermuda-z3-verify` (end-to-end real-Z3 run; asserts D13 ticket fires for the ch-02 parish-count drift).
- `tests/test_run_verification.py` confirms `stub_verifier=False` is the default; the stub remains for fast local iteration via explicit opt-in.

Plan: `docs/plans/2026-05-17-booklogic-pr5.md`.
```

- [ ] **Step 3: Cross-check that no other "Bermuda migration" pointer in the mission spec contradicts the closure.**

```powershell
Select-String -Path docs/specs/2026-05-14-booklogic-v0.4-mission-design.md -Pattern "Bermuda migration" -SimpleMatch
```

Expected matches: § D4 heading; § "Sub-PR slate" (the PR-5 row); § "Workspace mutation policy" (the PR-5 paragraph). None of these contradict the closure note; leave them.

- [ ] **Step 4: Commit.**

```powershell
git add docs/specs/2026-05-14-booklogic-v0.4-mission-design.md
git commit -m "mission spec: § D4 closure note (PR-5 landed Bermuda migration)"
```

---

## Phase 9: Sweep + PR

### Task 9.1: Full test sweep

- [ ] **Step 1: Run every Python suite.**

```powershell
cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest tests/ -q
cd ../book-qa && python -m pytest tests/ -q
cd ../book-thesis && python -m pytest tests/ -q
cd ../book-knowledge && python -m pytest tests/ -q
cd ../../verifiers/bermuda && .venv/Scripts/python.exe -m pytest tests/ -q
```

Expected: each suite green. Compared to Phase 0 baselines, expect:
- neurosym-forge: unchanged (PR-5 only touches Bermuda + ci.yml)
- book-qa: unchanged
- book-thesis: unchanged
- book-knowledge: unchanged
- verifiers/bermuda: 23 baseline + 5 from Phase 1 (`test_booklogic_compile_bermuda.py` ~16-18 tests as 5 logical groups, count varies on -k usage) + 3 from Phase 2 (`test_axioms_lockstep.py`) + 5 from Phase 3 (`test_quantitative_claims.py` is parametric × 4 + 1 = 5) + 3 from Phase 2.4 (`test_prose_patterns_loads_lifts_table.py`) + 3 from Phase 7 (`test_run_verification.py` rewritten; same count) + 1 from Phase 6 (`test_d13_end_to_end.py` — skip locally, runs in CI) = roughly 50-55 Bermuda tests.

If any baseline suite regresses, fix or revert before opening PR.

- [ ] **Step 2: Re-run BookLogic compile to confirm codegen artifacts still match the source.**

```powershell
cd verifiers/bermuda && npm run booklogic-compile
git status -- rust-verifier/src/axioms.rs rules/predicates.edn
```

Expected: clean tree (no modifications shown). If diffs appear, the on-disk artifacts drifted from the source — commit the regenerated outputs.

- [ ] **Step 3: Local Z3 smoke (skip if Phase 4 failed locally).**

```powershell
cd verifiers/bermuda
test -f cljs-orchestrator/dist/main.js && .venv/Scripts/python.exe -m pytest tests/test_d13_end_to_end.py -v
```

If Phase 4 succeeded the smoke ran already in Phase 6 Step 4. Otherwise it skips — CI carries the gate.

### Task 9.2: Push + open PR

- [ ] **Step 1: Confirm worktree branch.**

```powershell
cd C:\Users\charl\code\russellian-book-suite-booklogic-pr5
git status
git rev-parse --abbrev-ref HEAD
```

Expected: clean tree on `feat/booklogic-pr5`.

- [ ] **Step 2: Push.**

```powershell
git push -u origin feat/booklogic-pr5
```

- [ ] **Step 3: Open the PR.**

```powershell
gh pr create --title "BookLogic v0.4 PR-5: Bermuda migration + real Z3 (D5)" --body @'
## Summary

Lands § D5 of the BookLogic v0.4 Claude-only finish (and § D4 of the parent mission spec). Bermuda's hand-coded v0.2 verifier source is replaced by BookLogic forms; `canonical.rs` is deleted; `axioms.rs` is generated from `constraints.edn` and checked in; four quantitative predicates ship; a real Z3 build runs in CI; the ch-02 parish-count drift now fires a D13 critical ticket end-to-end.

- `verifiers/bermuda/rules/booklogic/` carries seven BookLogic source files (sorts, predicates, lifts, rules, constraints, queries, remedies)
- `rust-verifier/src/canonical.rs` deleted; `rust-verifier/src/axioms.rs` generated + checked in; `test_axioms_lockstep.py` enforces byte-identical regeneration
- Four quantitative predicates: `population` (63,918), `land-area-km2` (53.2), `gdp-usd-billion` (7.7), `hospital-beds-kemh` (90)
- `examples/bermuda-manual/claims/ledger.jsonl` appended with `clm-2026-000011` through `clm-2026-000014`
- Two new CI jobs on `ubuntu-latest`: `bermuda-z3-build` (cargo build with `--features z3`), `bermuda-z3-verify` (end-to-end real-Z3 run; asserts D13 ticket fires)
- `prose_patterns.py` is now a thin loader of the codegened regex table; supports `real` value-kind for the new quantitative predicates
- `tests/test_run_verification.py` confirms `stub_verifier=False` default; stub remains for fast local iteration via explicit opt-in
- Mission spec § D4 footer updated with the closure note

Spec: `docs/specs/2026-05-17-booklogic-claude-only-finish-design.md` § "PR-5 — Bermuda migration + real Z3 (D5)".
Mission ref: `docs/specs/2026-05-14-booklogic-v0.4-mission-design.md` § D4.
Plan: `docs/plans/2026-05-17-booklogic-pr5.md`.

## Test plan

- [ ] `cd verifiers/bermuda && .venv/Scripts/python.exe -m pytest tests/ -q` — ~50-55 passing locally (one D13 e2e SKIP without Z3)
- [ ] `cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest tests/ -q` — baseline unchanged
- [ ] `cd skills/book-qa && python -m pytest tests/ -q` — baseline unchanged
- [ ] `cd verifiers/bermuda && npm run booklogic-compile && git status` — clean tree (axioms.rs in lockstep)
- [ ] CI `bermuda-z3-build` green (real cargo build on ubuntu-latest)
- [ ] CI `bermuda-z3-verify` green (D13 ticket fires for ch-02 parish-count drift)

## Out of scope

- PR-6 osmotic-pressure showcase (D6) — separate PR
- Verdict serialization on Rust side still hand-rolled EDN (PR-1 work); no change
- The Cozo `defquery` backend is consumed only by `Q001-low-confidence-load-bearing`; broader exploration of `defquery` patterns lives in PR-6+
'@
```

- [ ] **Step 4: Report PR URL.**

---

## Self-review

Walking the spec § PR-5 against this plan:

| Spec clause | Implementing tasks |
|---|---|
| `verifiers/bermuda/rules/` rewritten as BookLogic source | Phase 1, Tasks 1.1–1.7 |
| Cover five existing predicates plus four quantitative | Tasks 1.2 (predicates) + 1.3 (lifts) + 1.5 (constraints) |
| Delete `rust-verifier/src/canonical.rs` | Task 2.3 |
| Check in generated `rust-verifier/src/axioms.rs` | Task 2.2 |
| `prose_patterns.py` becomes a thin wrapper | Task 2.4 |
| Append four quantitative claims to ledger | Task 3.1 |
| CI job `bermuda-z3-build` on ubuntu-latest | Task 5.1 |
| CI job `bermuda-z3-verify` end-to-end + D13 assertion | Task 5.1 + Task 6.1 |
| `test_run_verification.py` drops stub default | Task 7.1 |
| Mission spec § D4 footer note | Task 8.1 |
| BookLogic compiler invocation produces axioms.rs byte-identical | Task 2.2 (`test_axioms_lockstep.py`) |
| Real Z3 run returns `:unsat` with ch-02 in core | Task 6.1 |
| `book-qa` emits one D13 critical ticket | Task 6.1 + CI Task 5.1 |
| All 23 Bermuda Python tests still pass | Phase 9 sweep |
| Z3-bundled build failure capture (highest-risk step) | Phase 4 Task 4.1 Steps 2-5 |

All spec items have implementing tasks.

**Placeholder scan:** no "TBD" / "TODO" / "fill in" in any task. Each step has the exact command, code, or file path. The one explicitly-optional sub-step is Task 3.1 Step 5 (extending `synthesize_bermuda_ledger.py`); the spec calls this out as optional and Task 3.1 Step 3 covers the canonical append.

**Type consistency:** `Keyword`, `read_edn_file`, `_load_predicates`, `extract_pass_a`, `Defect`, `lint_d13_verification_unsat`, `assert_axioms`, `parse_formulas`, `check_all`, `assert_and_track` — used identically across tasks. The `kg::ingest_and_summarize` signature in `lib.rs` is unchanged (PR-4 wires the real Cozo backend; this PR ships one `defquery` that exercises it).

**Size:** 9 phases / ~16 tasks. Highest-risk steps: Phase 2 (compiler regeneration must succeed against PR-4's `defconstraint` codegen — if PR-4 didn't ship that exactly, regen will fail and the task surfaces the gap immediately); Phase 4 (local Z3 build, fully gated on host toolchain); Phase 5 (CI's first real Z3 build cold-builds from source, then caches via `Swatinem/rust-cache@v2`). Phase 6 D13 smoke depends on Phase 5 succeeding in CI.

**Known risks:**
- **Z3 bundled build on `ubuntu-latest`.** First CI run cold-builds Z3 from source (cmake + C++17). `Swatinem/rust-cache@v2` caches across runs. If `bundled` fails on the runner, fall back to `apt-get install -y libz3-dev` and switch the `z3` crate feature from `bundled` to default (system Z3); document the fallback in a follow-up PR.
- **PR-4 codegen output shape.** Task 2.2's `test_axioms_lockstep.py` assumes PR-4 wrote a compiler that emits `axioms.rs` deterministically given `constraints.edn`. If PR-4's compiler doesn't emit a stable byte order (e.g. iterates over a hashmap with non-deterministic ordering), the lockstep test will flap. Mitigation: PR-4's plan must enforce deterministic emit; if it didn't, this task surfaces it and PR-5 either ships a stable-sort post-processor or feeds back to PR-4.
- **Lift-regex coverage for the four quantitative predicates.** Task 2.4 Step 2 includes a real-world test (`Bermuda has a population of approximately 63,918 residents`) that exercises the `:population` regex. The other three quantitative predicates would benefit from similar Phase-3-style smoke tests; consider adding them if Phase 3 Step 6 surfaces any unmatched-atom issue.
- **The CI `bermuda-z3-verify` job downloads `nbb` on every run.** This adds ~10 seconds and risks `npm` registry transients. If CI flake rate climbs, cache `node_modules/` via `actions/cache@v4` keyed on `package-lock.json`.
- **Worktree path mismatch.** This plan instructs `C:\Users\charl\code\russellian-book-suite-booklogic-pr5`. PR-1's plan instructed a similar but distinct directory. The executing session must use the directory listed in Pre-flight; if the path is reused across mission PRs, ensure prior worktrees are removed with `git worktree remove` before adding the new one.
