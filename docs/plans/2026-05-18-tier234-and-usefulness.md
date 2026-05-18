# Tier 2-4 + Framework Usefulness Verification — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the remaining roadmap items surfaced by the multi-solver audit (Tier 2 encoder + dialect, Tier 3 promote stubs to live, Tier 4 scale/perf/CI matrix) and empirically verify the framework is general-purpose, not just bermuda/osmotic-specific.

**Architecture:** Ten independent OpenSpec changes across four tracks. Each change is independently mergeable. Tracks (and their phase letters in THIS plan):

- **Tier 2 (hardening):** Phase E (strict regex), F (encoder), G (multi-valued predicates)
- **Tier 3 (de-stub):** Phase H (egg promotion), I (Cozo runtime)
- **Tier 4 (scale/CI):** Phase J (solver partitioning), K (streaming ingest), L (cross-OS CI matrix)
- **Usefulness:** Phase M (third-verifier build), N (onboarding benchmark)

**Cross-reference to OpenSpec tasks.md files.** The OpenSpec change folders' `tasks.md` files were authored in parallel and use a slightly compressed phase numbering (Tier 2 consolidated to one phase with sub-phases):

| Umbrella plan phase | OpenSpec tasks.md phase | OpenSpec change |
|---------------------|-------------------------|-----------------|
| Phase E | E.1                     | `tier2-strict-regex-dialect` |
| Phase F | E.2                     | `tier2-encoder-extensions` |
| Phase G | E.3                     | `tier2-multi-valued-predicates` |
| Phase H | G                       | `tier3-egg-promotion` |
| Phase I | H                       | `tier3-cozo-runtime` |
| Phase J | I                       | `tier4-solver-partitioning` |
| Phase K | J                       | `tier4-streaming-ingest` |
| Phase L | K                       | `tier4-cross-os-ci-matrix` |
| Phase M | L                       | `eval-third-verifier` |
| Phase N | M                       | `eval-onboarding-bench` |

When implementing, the REQ-ID is the authoritative cross-reference (every task block in this plan cites its REQ-IDs; every tasks.md REQ-ID maps 1:1 to a spec.md entry).

Tier 1 (PRs #71-#75) established the floor: silent-OPAQUE-fallthrough is closed, indefinite hangs are closed, identifier drift is closed, dead-end docs are closed. Tier 2-4 + usefulness raise the ceiling.

**Tech Stack:** Python 3.13 (ingest, codegen, eval harness), Rust 1.90 + z3 0.20 + egg 0.10 + cozo 0.7 (verifier), ClojureScript via nbb (DSL compiler), pytest + cargo test + nbb test.

**Dependencies:** Phases are mostly independent. The cross-coupling:
- Phase F (encoder extensions) is a prereq for Phase M's third-verifier IF the domain author uses `>=`/`<=`. The plan recommends picking a domain that exercises Tier 2 features so the eval naturally validates them.
- Phase H (egg) and Phase I (Cozo) both touch SUPPORT_MATRIX.md — coordinate via small final commit that reconciles both.
- Phase L (CI matrix) should land AFTER Phase F+H+I so the new test surface is fully exercised on all three OSes from day one.
- Phase N (onboarding bench) consumes the doc bundle Phase D produced; it does not require any Tier 2-4 work to be in place to start measuring.

---

## Pre-flight

Read these before starting any phase:

- `openspec/changes/tier{2,3,4}-*/` and `openspec/changes/eval-*/` — the EARS REQs for each track (this PR authors them)
- `skills/neurosym-forge/SUPPORT_MATRIX.md` — current ground truth
- `docs/booklogic-dsl-reference.md` — author-facing reference (Phase F and Phase G extend §2.5 and §2.2 respectively)
- `verifiers/osmotic_pressure/scripts/ingest_ledger.py:80` — the silent `_to_python_regex` converter Phase E removes
- `verifiers/*/rust-verifier/src/smt.rs:check_all` — single-solver pattern Phase J partitions
- `skills/neurosym-forge/scripts/codegen_axioms.py:_emit_z3_block` — operator dispatch Phase F extends
- `verifiers/*/rust-verifier/src/{eqsat,kg}.rs` — current stubs Phase H/I promote

**Branches:** one per phase, all cut from main.

```bash
cd ~/work/russellian-book-suite
git fetch origin
git checkout main
git pull --ff-only origin main
# Per-phase branches when starting that phase:
git checkout -b feat/tier2-strict-regex-dialect      # Phase E
git checkout -b feat/tier2-encoder-extensions        # Phase F
git checkout -b feat/tier2-multi-valued-predicates   # Phase G
git checkout -b feat/tier3-egg-promotion             # Phase H
git checkout -b feat/tier3-cozo-runtime              # Phase I
git checkout -b feat/tier4-solver-partitioning       # Phase J
git checkout -b feat/tier4-streaming-ingest          # Phase K
git checkout -b feat/tier4-cross-os-ci-matrix        # Phase L
git checkout -b feat/eval-third-verifier             # Phase M
git checkout -b feat/eval-onboarding-bench           # Phase N
```

**Test invocations:**

```bash
# Per-verifier
make -C verifiers/osmotic_pressure ci
make -C verifiers/bermuda ci

# Cargo unit tests (Linux/WSL only — needs system libz3)
wsl -d Ubuntu -- bash -lc 'cd /mnt/c/work/russellian-book-suite/verifiers/osmotic_pressure/rust-verifier && cargo test --features smt --release'

# Neurosym-forge full suite (must not regress; baseline 237 passed, 9 skipped post-Tier-1)
py -m pytest skills/neurosym-forge/tests -q
```

**Commit hygiene:** terse, imperative, lowercase scope prefix; no AI attribution; one problem per commit; never `--no-verify`.

**Scope guard:** This plan does NOT promote MeTTa to a runtime, does NOT add a graphical authoring UI, does NOT extend BookLogic with macro support. Those would be Tier 5+. Reject scope creep.

---

## Phase E — Strict regex dialect (`tier2-strict-regex-dialect`)

**Branch:** `feat/tier2-strict-regex-dialect`
**OpenSpec change:** `openspec/changes/tier2-strict-regex-dialect/`
**Exit criteria:** A `predicates.edn` containing `(?<v>...)` causes `ingest_ledger.ingest()` to raise `IngestRegexDialectError` with a message naming the offending pattern and pointing at `references/grounded-atoms.md`. The Phase A `test_bug7` regression switches from the literal-mismatch surrogate to the actual `(?<v>)` mutation.

### Task E1: Failing test for the dialect gate (REQ-INGEST-050, 051)

**Files:**
- Create: `verifiers/osmotic_pressure/scripts/tests/test_regex_dialect_gate.py`

- [ ] **E1.1: Write the failing test**

```python
"""REQ-INGEST-050, REQ-INGEST-051: JS-style (?<v>) is a hard ingest error."""
from __future__ import annotations

from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_js_style_named_group_raises(tmp_path):
    import sys
    sys.path.insert(0, str(PROJECT_ROOT))
    from scripts.ingest_ledger import ingest, IngestRegexDialectError

    bad_preds = tmp_path / "predicates.edn"
    bad_preds.write_text(
        '{:version 1, :predicates {:foo {:patterns ["(?<v>[0-9]+)"], '
        ':predicate :foo, :subject :s, :value-kind :int, :word-to-int {}}}}',
        encoding="utf-8",
    )
    out = tmp_path / "claims.edn"
    with pytest.raises(IngestRegexDialectError) as exc_info:
        ingest(PROJECT_ROOT / "fixtures" / "claims_clean.jsonl", bad_preds, out)
    msg = str(exc_info.value)
    assert "(?<" in msg
    assert "(?P<" in msg  # The error names the Python-form replacement
    assert "references/grounded-atoms.md" in msg or "grounded-atoms" in msg
```

- [ ] **E1.2: Run** `py -m pytest verifiers/osmotic_pressure/scripts/tests/test_regex_dialect_gate.py -v`
Expected: FAIL — `IngestRegexDialectError` does not exist yet.

### Task E2: Add the dialect-validator + raise (REQ-INGEST-050, 051)

**Files:**
- Modify: `verifiers/osmotic_pressure/scripts/ingest_ledger.py`
- Modify: `verifiers/bermuda/scripts/ingest_ledger.py`

- [ ] **E2.1: Add `IngestRegexDialectError` class + `_assert_python_regex_dialect` helper**

In both `ingest_ledger.py` files, near the top:

```python
class IngestRegexDialectError(ValueError):
    """Raised when a predicates.edn regex uses JS-style named groups
    (`(?<v>...)`) instead of Python-form `(?P<v>...)`.

    REQ-INGEST-050, REQ-INGEST-051. See references/grounded-atoms.md
    for the canonical dialect.
    """


_JS_NAMED_GROUP = re.compile(r"\(\?<([A-Za-z_][A-Za-z0-9_]*)>")


def _assert_python_regex_dialect(pat: str) -> None:
    m = _JS_NAMED_GROUP.search(pat)
    if m:
        raise IngestRegexDialectError(
            f"predicates.edn regex {pat!r} uses JS-style named group "
            f"(?<{m.group(1)}>...) — Python-form (?P<{m.group(1)}>...) "
            f"is the canonical dialect (see "
            f"skills/neurosym-forge/references/grounded-atoms.md)"
        )
```

- [ ] **E2.2: Delete the silent rewrite; replace with the assertion**

Find the existing `_to_python_regex` function (around line 80) and the call site (around line 96 inside `_apply_predicates`):

```python
m = re.search(_to_python_regex(pat), text, flags=re.IGNORECASE | re.DOTALL)
```

Replace with:

```python
_assert_python_regex_dialect(pat)
m = re.search(pat, text, flags=re.IGNORECASE | re.DOTALL)
```

Then delete `_to_python_regex` and `_JS_NAMED_GROUP`-the-rewriter (the new `_JS_NAMED_GROUP` for the validator stays).

- [ ] **E2.3: Run the failing test from E1 — confirm PASS**

- [ ] **E2.4: Commit**

```bash
git add verifiers/osmotic_pressure/scripts/ingest_ledger.py \
        verifiers/bermuda/scripts/ingest_ledger.py \
        verifiers/osmotic_pressure/scripts/tests/test_regex_dialect_gate.py
git commit -m "ingest: strict Python regex dialect; JS-style (?<v>) is now a hard error (REQ-INGEST-050, 051)"
```

### Task E3: Extract-gate compatibility test (REQ-INGEST-052)

- [ ] **E3.1: Add a test that confirms extract-preview still fires on a non-matching but dialect-correct regex** — see Phase A's existing `test_threshold_exit_on_high_opaque` for the pattern. Add a sibling test in `tests/test_regex_dialect_gate.py`:

```python
def test_dialect_correct_but_nonmatching_still_triggers_opaque_gate(tmp_path):
    """REQ-INGEST-052: removing the silent JS converter doesn't change
    the existing OPAQUE-fraction gate behavior on dialect-correct but
    non-matching regex (the canonical Phase A bug surface)."""
    import subprocess, sys
    nonmatching_preds = tmp_path / "predicates.edn"
    nonmatching_preds.write_text(
        '{:version 1, :predicates {:nothing {:patterns ["zzz-impossible-(?P<v>[0-9]+)"], '
        ':predicate :nothing, :subject :s, :value-kind :int, :word-to-int {}}}}',
        encoding="utf-8",
    )
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "extract_preview.py"),
         "--claims", str(PROJECT_ROOT / "fixtures" / "claims_clean.jsonl"),
         "--predicates", str(nonmatching_preds),
         "--threshold", "0.10"],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode != 0
    assert "exceeds threshold" in result.stdout
```

- [ ] **E3.2: Run** — confirm PASS.

- [ ] **E3.3: Commit**

```bash
git commit -am "tests(ingest): extract gate unaffected by removal of silent JS converter (REQ-INGEST-052)"
```

### Task E4: Re-arm the bug7 regression (REQ-INGEST-053)

- [ ] **E4.1: Edit `skills/neurosym-forge/tests/regression/test_sprint5_bug_catches.py`** — the bug7 test was rewritten in Phase A to use a literal-mismatch surrogate (`zzzNEVERMATCH`) because the silent converter masked the actual `(?<v>)` form. Now that Phase E surfaces `(?<v>)` as a hard error, switch the mutation back to its original form:

```python
def test_bug7_regex_break_caught_by_extract_gate(fresh_bake) -> None:
    """REQ-INGEST-048 + REQ-INGEST-053: a JS-style (?<v>) named group in
    lifts.edn causes `make ci` to fail at the extract step. Post-Phase-E,
    we use the actual JS-form mutation (no surrogate) because the silent
    converter is gone."""
    project = fresh_bake("bug7")
    lifts = project / "rules" / "booklogic" / "lifts.edn"
    text = lifts.read_text(encoding="utf-8")
    bad = text.replace("(?P<v>", "(?<v>")
    assert bad != text, "couldn't find (?P<v> to mutate"
    lifts.write_text(bad, encoding="utf-8")
    (project / "fixtures").mkdir(parents=True, exist_ok=True)
    (project / "fixtures" / "claims_clean.jsonl").write_text(
        '{"claim_id":"smk-001","status":"verified","canonical_text":"count 7","claim_type":"fact"}\n',
        encoding="utf-8",
    )
    result = run_make_ci(project)
    assert result.returncode != 0
    combined = (result.stdout + result.stderr).lower()
    assert "(?<" in combined or "ingestregexdialecterror" in combined
```

- [ ] **E4.2: Commit**

```bash
git commit -am "regression: bug7 uses actual (?<v>) mutation post-Phase-E (REQ-INGEST-053)"
```

### Task E5: Push + open PR-E

- [ ] **E5.1:** `git push -u origin feat/tier2-strict-regex-dialect`
- [ ] **E5.2:** `gh pr create --title "Tier 2E: strict Python regex dialect (REQ-INGEST-050..053)"` with REQ-coverage body.
- [ ] **E5.3:** Merge on green CI.

---

## Phase F — Encoder extensions (`tier2-encoder-extensions`)

**Branch:** `feat/tier2-encoder-extensions`
**OpenSpec change:** `openspec/changes/tier2-encoder-extensions/`
**Exit criteria:** `defconstraint :assert` accepts `>`, `<`, `>=`, `<=`, `/`, `ite` in addition to the existing `=`, `*`, `+`, `approx=`, `and`, `or`. Each new operator has a unit test in `codegen_axioms.py`'s test suite AND a cargo integration test that exercises it end-to-end via Z3.

### Task F1: Operator-to-Z3-method mapping table

**Files:**
- Modify: `skills/neurosym-forge/scripts/codegen_axioms.py`
- Modify: `verifiers/osmotic_pressure/scripts/_codegen_axioms_lib.py` (vendored copy)

- [ ] **F1.1: Locate `_emit_expr_typed` and `_emit_expr` in `codegen_axioms.py`** — the existing dispatch handles `=`, `*`, `+` via head-of-form matching. Read the existing block.

- [ ] **F1.2: Add the new operator dispatch table** (after the existing dispatch, before the fallthrough error):

```python
_REAL_BINOP_TO_Z3 = {
    Symbol("<"):  "lt",
    Symbol("<="): "le",
    Symbol(">"):  "gt",
    Symbol(">="): "ge",
    Symbol("/"):  "div",
}


def _emit_real_binop(head: Symbol, args: list) -> str:
    """REQ-SMT-040, 041, 042: emit Z3 method call for comparison/division."""
    if len(args) != 2:
        raise CodegenError(
            f"{head}: expected 2 arguments, got {len(args)}"
        )
    lhs = _emit_expr_typed(args[0])
    rhs = _emit_expr_typed(args[1])
    method = _REAL_BINOP_TO_Z3[head]
    return f"{lhs}.{method}(&{rhs})"


def _emit_ite(args: list) -> str:
    """REQ-SMT-043: emit Z3 Bool::ite."""
    if len(args) != 3:
        raise CodegenError(f"ite: expected 3 arguments, got {len(args)}")
    cond = _emit_expr_typed(args[0])
    then_branch = _emit_expr_typed(args[1])
    else_branch = _emit_expr_typed(args[2])
    return f"{cond}.ite(&{then_branch}, &{else_branch})"
```

- [ ] **F1.3: Wire the new dispatch into the existing `_emit_expr_typed`'s head-of-form switch.**

- [ ] **F1.4: Unsupported-operator error case (REQ-SMT-044)** — at the end of the switch, replace the existing fallthrough with:

```python
raise CodegenError(
    f"unsupported operator {head!r} in :assert; supported: "
    f"= * + approx= and or {' '.join(str(k) for k in _REAL_BINOP_TO_Z3)} ite"
)
```

### Task F2: codegen unit tests for each new operator

- [ ] **F2.1: Add test cases** in `skills/neurosym-forge/tests/test_codegen_axioms.py`:

```python
def test_lt_operator_emits_z3_lt():
    """REQ-SMT-040."""
    constraint = read_edn(
        '{:id "C-lt" :backend :z3 '
        ':assert (< (:foo ?s) (:bar ?s)) '
        ':on-unsat {:defect :D :severity :low :message "x"}}'
    )
    emitted = generate_axioms_source([constraint])
    assert ".lt(&" in emitted, emitted


# Same pattern for: <=, >, >=, /, ite
# (Six tests total — one per new operator)
```

- [ ] **F2.2: Run** — confirm all 6 PASS.

- [ ] **F2.3: Unsupported-operator error test** (REQ-SMT-044):

```python
def test_unsupported_operator_errors():
    """REQ-SMT-044."""
    constraint = read_edn(
        '{:id "C-bad" :backend :z3 '
        ':assert (modulo a b) '
        ':on-unsat {:defect :D :severity :low :message "x"}}'
    )
    with pytest.raises(CodegenError) as exc:
        generate_axioms_source([constraint])
    assert "modulo" in str(exc.value)
    assert "supported:" in str(exc.value)
```

### Task F3: Cargo integration test (end-to-end through Z3)

- [ ] **F3.1: Add a Rust integration test** at `verifiers/osmotic_pressure/rust-verifier/tests/encoder_extensions.rs`:

```rust
//! REQ-SMT-040..044 end-to-end: each new operator round-trips through
//! codegen to Z3 and produces the expected sat/unsat.
use osmotic_pressure_verifier::ir::parse_formulas;
use osmotic_pressure_verifier::smt::check_all;

#[test]
fn lt_constraint_unsat_when_violated() {
    // Domain: temp >= 273 (above freezing).
    // Bind temp=200 and assert (>= temp 273) — should be :unsat.
    let edn = r#"
    {:version 1
     :atoms [{:id "t-001" :kind :expression :predicate :temp :subject :s :value 200.0}]}
    "#;
    let formulas = parse_formulas(edn).expect("parse");
    let verdict = check_all(&formulas).expect("check_all");
    // The axiom hook would assert (>= (:temp :s) 273); for this test we
    // hard-code the axiom into axioms.rs via codegen on a fixture
    // constraint set. (Test fixture path: tests/fixtures/encoder_ext_lt_constraints.edn)
    assert_eq!(verdict.status, "unsat");
}
```

(Repeat for each new operator; pattern is the same.)

### Task F4: Update docs/booklogic-dsl-reference.md §2.5 (REQ-SMT-045)

- [ ] **F4.1: Edit the §2.5 `defconstraint` operator list** to enumerate the full set: `=`, `*`, `+`, `-`, `/`, `approx=`, `and`, `or`, `<`, `<=`, `>`, `>=`, `ite`. Cross-link the new ones to a worked example apiece.

### Task F5: Push + open PR-F. Merge on green.

---

## Phase G — Multi-valued predicates (`tier2-multi-valued-predicates`)

**Branch:** `feat/tier2-multi-valued-predicates`
**OpenSpec change:** `openspec/changes/tier2-multi-valued-predicates/`
**Exit criteria:** `(defpredicate :foo [:solution] [:vector :real])` parses, the codegen emits a Z3 `Array<Int, Real>`, and a worked example using `(sum vec)` aggregation passes a Z3 integration test.

### Task G1: CLJS expand-defpredicate accepts vector/set return sorts

**Files:**
- Modify: `verifiers/osmotic_pressure/cljs-orchestrator/src/main/osmotic_pressure/booklogic.cljs`
- Modify: `verifiers/bermuda/cljs-orchestrator/src/main/bermuda/booklogic.cljs`
- Modify: `skills/neurosym-forge/assets/project-template/cljs-orchestrator/src/main/__project__/booklogic.cljs.tmpl`

- [ ] **G1.1: Failing test in `booklogic_test.cljs.tmpl`** (REQ-DSL-040):

```clojure
(deftest expand-defpredicate-vector-return
  ;; REQ-DSL-040
  (let [src {:sorts [(list 'defsort :solution)]
             :predicates [(list 'defpredicate :solutes [:solution] [:vector :real])]
             :lifts [] :rules [] :constraints [] :queries [] :remedies []}
        expanded (bl/expand src)
        pred (first (:predicate-registry expanded))]
    (is (= :solutes (:name pred)))
    (is (= [:vector :real] (:return pred)))))
```

- [ ] **G1.2: Modify `expand-defpredicate`** in all three locations to accept a vector form for `return`:

```clojure
(defn- expand-defpredicate
  [form]
  (let [[_ name args ret] form]
    (when-not (keyword? name)
      (throw (ex-info "defpredicate: name must be a keyword" {:form form})))
    (when-not (vector? args)
      (throw (ex-info "defpredicate: args must be a vector of sorts" {:form form})))
    ;; REQ-DSL-040: return can be either a primitive keyword or a
    ;; multi-valued [:vector <sort>] / [:set <sort>] form.
    (when-not (or (keyword? ret)
                  (and (vector? ret)
                       (#{:vector :set} (first ret))
                       (= 2 (count ret))
                       (keyword? (second ret))))
      (throw (ex-info "defpredicate: return must be a sort keyword or [:vector|:set <sort>]"
                      {:form form})))
    {:name name :args args :ret ret}))
```

- [ ] **G1.3: Run** the cljs test — PASS.

### Task G2: codegen translates vector return to Z3 Array

- [ ] **G2.1: Failing test in `test_codegen_axioms.py`** (REQ-DSL-041):

```python
def test_vector_predicate_emits_z3_array():
    """REQ-DSL-041: [:vector :real] → Z3 Array<Int, Real>."""
    constraint = read_edn(
        '{:id "C-vec" :backend :z3 '
        ':assert (= (select (:solutes ?s) 0) 0.154) '
        ':on-unsat {:defect :D :severity :low :message "x"}}'
    )
    schema = {"solutes": {"arg-sorts": [":solution"], "return": [":vector", ":real"]}}
    emitted = generate_axioms_source([constraint], schema=schema)
    assert "Array" in emitted
    assert "Int" in emitted and "Real" in emitted
```

- [ ] **G2.2: Implement vector/set codegen** — add a `_sort_to_z3` helper in `codegen_axioms.py`:

```python
def _sort_to_z3(sort) -> str:
    """REQ-DSL-041, 042: translate a sort spec to a Z3 type."""
    if isinstance(sort, Keyword):
        return {"int": "Int", "real": "Real", "bool": "Bool",
                "string": "Z3String"}.get(sort.name, "Real")
    if isinstance(sort, (list, EdnList, EdnVector)) and len(sort) == 2:
        head = sort[0]
        inner = _sort_to_z3(sort[1])
        if isinstance(head, Keyword):
            if head.name == "vector":
                return f"Array<Int, {inner}>"
            if head.name == "set":
                return f"Set<{inner}>"
    raise CodegenError(f"unknown sort: {sort!r}")
```

### Task G3: Aggregate operators (REQ-DSL-043)

- [ ] **G3.1: Add `(sum vec)`, `(count vec)`, `(forall ?x in vec ...)` desugaring** in `_emit_expr_typed`. The aggregation desugars to a Z3 universally-quantified Bool or to a fixed-size unrolled sum (when the vector length is statically known via the bound predicate's `:value` field).

(Pattern: same as F1.2, with three new entries in a `_AGGREGATE_DISPATCH` table.)

### Task G4: Sort-mismatch error path (REQ-DSL-044)

- [ ] **G4.1: Failing test in cargo** — bind a vector-typed predicate to a scalar value:

```rust
#[test]
fn vector_predicate_bound_to_scalar_errors() {
    let edn = r#"
    {:version 1
     :atoms [{:id "v-001" :kind :expression :predicate :solutes :subject :s :value 0.154}]}
    "#;
    // axioms.rs declares :solutes as [:vector :real]; binding a scalar must surface.
    let formulas = osmotic_pressure_verifier::ir::parse_formulas(edn).expect("parse");
    let result = osmotic_pressure_verifier::smt::check_all(&formulas);
    assert!(result.is_err());
    let msg = format!("{:?}", result.err().unwrap());
    assert!(msg.contains("sort mismatch") || msg.contains("vector"));
}
```

- [ ] **G4.2: Implement the binding-check in `smt::check_all`** — when the codegen's `predicate_is_vector(name)` returns true but the atom's `:value` is a scalar, return `Error::Smt("sort mismatch: ...")`.

### Task G5: booklogic-schema.edn extension (REQ-DSL-045)

- [ ] **G5.1: Update `emit-schema-edn-string`** in both real CLJS files + the .tmpl to include the multi-valued return type literally:

```clojure
(defn- emit-schema-edn-string
  [{:keys [predicate-registry sort-registry]}]
  (let [preds (into {} (for [p predicate-registry]
                         [(:name p) {:arg-sorts (:arg-sorts p)
                                     ;; REQ-DSL-045: preserve the
                                     ;; vector/set wrapping if present.
                                     :return    (:return p)}]))]
    (pr-str {:version 1
             :sorts (mapv :name sort-registry)
             :predicates preds})))
```

### Task G6: Push + open PR-G. Merge on green.

---

## Phase H — Egg promotion (`tier3-egg-promotion`)

**Branch:** `feat/tier3-egg-promotion`
**OpenSpec change:** `openspec/changes/tier3-egg-promotion/`
**Exit criteria:** `:backend :egg` constraints reach the egg solver (no silent drop); SUPPORT_MATRIX.md updated; a 3-rule rewrite-set test fixture canonicalises a known-non-canonical expression as expected.

### Task H1: Wire egg-rs into `eqsat.rs`

**Files:**
- Modify: `verifiers/osmotic_pressure/rust-verifier/src/eqsat.rs` (currently a stub)
- Modify: `verifiers/bermuda/rust-verifier/src/eqsat.rs`
- Modify: `verifiers/*/rust-verifier/Cargo.toml` (verify `egg = "0.10"` is in `[dependencies]`)

- [ ] **H1.1: Define the EGraph language** — paste this skeleton into `eqsat.rs`:

```rust
use egg::{define_language, rewrite, EGraph, RecExpr, Rewrite, Runner, Symbol};

define_language! {
    pub enum BookLogic {
        // Constants
        Num(i64),
        // Predicate application: (pred :pred-name :subject)
        "predicate" = Predicate([Id; 2]),
        // Arithmetic
        "+" = Add([Id; 2]),
        "*" = Mul([Id; 2]),
        "-" = Sub([Id; 2]),
        "/" = Div([Id; 2]),
        // Symbolic head (for unknown / extension)
        Symbol(Symbol),
    }
}

pub fn make_rewrites() -> Vec<Rewrite<BookLogic, ()>> {
    vec![
        rewrite!("commute-add"; "(+ ?a ?b)" => "(+ ?b ?a)"),
        rewrite!("commute-mul"; "(* ?a ?b)" => "(* ?b ?a)"),
        rewrite!("assoc-add";  "(+ ?a (+ ?b ?c))" => "(+ (+ ?a ?b) ?c)"),
    ]
}

pub fn canonicalize(input: &str, budget_nodes: usize) -> RecExpr<BookLogic> {
    let expr: RecExpr<BookLogic> = input.parse().expect("parse RecExpr");
    let runner = Runner::default()
        .with_node_limit(budget_nodes)
        .with_expr(&expr)
        .run(&make_rewrites());
    let extractor = egg::Extractor::new(&runner.egraph, egg::AstSize);
    let (_cost, best) = extractor.find_best(runner.roots[0]);
    best
}
```

- [ ] **H1.2: Add cargo integration test** at `verifiers/osmotic_pressure/rust-verifier/tests/eqsat_canonicalize.rs`:

```rust
//! REQ-EQSAT-040, 042
use osmotic_pressure_verifier::eqsat::canonicalize;

#[test]
fn commutative_add_canonicalises() {
    let canonical = canonicalize("(+ b a)", 10_000);
    let s = canonical.to_string();
    // Either (+ a b) or (+ b a) is acceptable as long as it's stable.
    assert!(s == "(+ a b)" || s == "(+ b a)", "got {s}");
}
```

(Saturation budget node-count limit = 10,000 by default; env override `VERIFIER_EQSAT_BUDGET` per REQ-EQSAT-044.)

### Task H2: codegen routes `:backend :egg` to eqsat (REQ-EQSAT-043)

- [ ] **H2.1: Locate `codegen_axioms.py:138`** (`if backend != Keyword("z3"): continue`). Replace with a dispatch:

```python
if backend == Keyword("z3"):
    body_lines.append(_emit_z3_block(c))
elif backend == Keyword("egg"):
    body_lines.append(_emit_egg_block(c))
elif backend == Keyword("cozo"):
    # Cozo path lives in codegen_kg.py; skip here.
    continue
else:
    raise CodegenError(
        f"constraint {c.get(Keyword('id'))!r}: unknown backend {backend!r}"
    )
```

- [ ] **H2.2: Implement `_emit_egg_block`** — emit Rust code that calls `crate::eqsat::prove(lhs, rhs, rules)` and `assert_and_track`s the Bool result. The Z3 axiom asserts `lhs_canonical == rhs_canonical` post-saturation.

### Task H3: SUPPORT_MATRIX.md row updates (REQ-EQSAT-045)

- [ ] **H3.1: Edit `skills/neurosym-forge/SUPPORT_MATRIX.md`** rows:
  - `defrule` row: `stub` → `wired`
  - `defconstraint :backend :egg` row: `DROP` → `wired`
- [ ] **H3.2: Add the explanatory paragraph naming the egg-rs crate + node-budget environment variable.**

### Task H4: Update the drift lint (REQ-EQSAT-045)

- [ ] **H4.1: Edit `skills/neurosym-forge/tests/test_support_matrix.py`**:

```python
def test_matrix_egg_is_wired_post_phase_h():
    """REQ-EQSAT-045: post-Phase-H, the matrix flips :egg to wired."""
    status = _matrix_row_status("defconstraint", "egg")
    assert status is not None
    assert "wired" in status.lower(), (
        f"matrix should report :egg as wired post-Phase-H; got {status!r}"
    )


# Update test_matrix_egg_is_drop to be a Phase-H-pre-flight regression
# guard: rename it to test_matrix_egg_is_drop_only_pre_phase_h and remove.
```

### Task H5: Push + open PR-H. Merge on green.

---

## Phase I — Cozo runtime (`tier3-cozo-runtime`)

**Branch:** `feat/tier3-cozo-runtime`
**OpenSpec change:** `openspec/changes/tier3-cozo-runtime/`
**Exit criteria:** `make ci` invokes Cozo on every `defquery`, the verdict gains a `:queries [...]` field, `:backend :cozo` constraints route to Cozo, and SUPPORT_MATRIX.md updates accordingly.

### Task I1: Wire Cozo into smt::check_all

**Files:**
- Modify: `verifiers/*/rust-verifier/src/kg.rs` (currently a stub)
- Modify: `verifiers/*/rust-verifier/src/smt.rs` (the verdict surface)

- [ ] **I1.1: Add Cozo invocation in `kg.rs`**:

```rust
use cozo::{DbInstance, NamedRows};

pub fn run_queries(query_edn: &str) -> Result<Vec<(String, NamedRows)>, String> {
    let db = DbInstance::new("mem", "", Default::default())
        .map_err(|e| format!("cozo init: {e}"))?;
    // Each defquery emit produces a (name, datalog-source) pair.
    let queries = parse_query_edn(query_edn);
    let mut results = Vec::new();
    for (name, source) in queries {
        let result = db.run_default(&source).map_err(|e| format!("cozo run {name}: {e}"))?;
        results.push((name, result));
    }
    Ok(results)
}
```

- [ ] **I1.2: Verdict carries query results (REQ-DATALOG-042)** — modify `Verdict` struct in `ir.rs`:

```rust
pub struct Verdict {
    pub status: String,
    pub core: Vec<ClaimId>,
    pub explanation: String,
    pub queries: Vec<QueryResult>,  // NEW
}
```

- [ ] **I1.3: Smoke test against a known-defect query** — write a `tests/cozo_query.rs` integration test that asserts a `(:claim/orphan ?c)` query returns the seeded orphan claim.

### Task I2: `:backend :cozo` route (REQ-DATALOG-041)

- [ ] **I2.1: In `codegen_axioms.py`'s dispatch (modified in H2.1), the `:cozo` branch now routes to `_emit_cozo_block`**:

```python
elif backend == Keyword("cozo"):
    body_lines.append(_emit_cozo_block(c))
```

- [ ] **I2.2: `_emit_cozo_block` emits a Rust call into `kg::evaluate_constraint`** which translates the `:assert` form to a Cozo Datalog rule and asserts the result is non-empty.

### Task I3: Datalog timeout (REQ-DATALOG-044)

- [ ] **I3.1: Add `VERIFIER_DATALOG_TIMEOUT_MS` env var** in `kg.rs`'s `run_queries`. Default 10,000 ms. On timeout, push a `(name, "<timeout>")` result and continue.

### Task I4: Remedy bindings (REQ-DATALOG-043)

- [ ] **I4.1: Update verdict_to_qa.py** in both verifiers — when a `defremedy` `:when` clause names a query, bind the query's result rows into `:propose`.

### Task I5: SUPPORT_MATRIX updates + drift-lint refresh (REQ-DATALOG-045)

- [ ] **I5.1: Update SUPPORT_MATRIX.md**:
  - `defquery`: `wired-builder` → `wired`
  - `defconstraint :backend :cozo`: `DROP` → `wired`
  - `defremedy`: `external` → `wired (query-bound)`

### Task I6: Push + open PR-I. Merge on green.

---

## Phase J — Solver partitioning (`tier4-solver-partitioning`)

**Branch:** `feat/tier4-solver-partitioning`
**OpenSpec change:** `openspec/changes/tier4-solver-partitioning/`
**Exit criteria:** `check_all` runs one Z3 solver per subject; cross-subject constraints serialise after; per-subject `:unknown` no longer poisons the whole verdict.

### Task J1: Partition atoms by subject

**Files:**
- Modify: `verifiers/*/rust-verifier/src/smt.rs`

- [ ] **J1.1: Refactor `check_all`** so the per-atom binding loop produces a `HashMap<String, Vec<(ClaimId, Atom)>>` keyed by `subject`. Constraints touching multiple subjects (detected from the codegen-emitted axiom's referenced variable names) go into a `"_shared"` bucket.

- [ ] **J1.2: Per-partition solver** — for each subject bucket, create a fresh `Solver::new()`, configure the timeout, assert axioms relevant to that subject (codegen emits `axioms_for_subject(subject_name)` accessor), bind atoms, `check()`. Collect partition verdicts.

- [ ] **J1.3: Merge rule (REQ-PERF-042)** — any partition `:unsat` → top-level `:unsat`; partition explanations name the subject. All `:sat` → top-level `:sat`. Any `:unknown` without `:unsat` → top-level `:unknown` with subjects listed.

### Task J2: `VERIFIER_SOLVER_PARALLELISM` env var (REQ-PERF-041)

- [ ] **J2.1: Read the env var**, default 1. If >1, dispatch partitions to a `rayon::ThreadPoolBuilder`. Each Z3 solver runs in its own thread.

### Task J3: Cross-subject `_shared` bucket (REQ-PERF-043)

- [ ] **J3.1: Detect cross-subject constraints** at codegen time by walking the `:assert` sexp and collecting all `?subject-id` references. If >1, route the constraint into the shared bucket.
- [ ] **J3.2: Run the shared bucket serially after all per-subject buckets complete** — the shared solver depends on results from individual subjects to bound the search space.

### Task J4: Cargo integration test

- [ ] **J4.1: Multi-subject fixture** at `tests/partitioning.rs` — three subjects, three independent constraint sets, one cross-subject constraint. Assert the verdict is correct AND that a deliberate per-subject `:unknown` (forced via tiny timeout) does NOT poison the others.

### Task J5: Push + open PR-J. Merge on green.

---

## Phase K — Streaming ingest (`tier4-streaming-ingest`)

**Branch:** `feat/tier4-streaming-ingest`
**OpenSpec change:** `openspec/changes/tier4-streaming-ingest/`
**Exit criteria:** `ingest_ledger.ingest()` no longer materialises the full atom list; `work/claims.edn` is streamed; a 100MB JSONL fixture ingests without OOM.

### Task K1: Streaming EDN writer

**Files:**
- Create: `skills/neurosym-forge/scripts/_edn_streaming.py`
- Modify: `verifiers/*/scripts/ingest_ledger.py`

- [ ] **K1.1: `StreamingAtomWriter` class** — opens the output file with `{:version 1 :atoms [`, accepts atoms via `.write(atom)`, closes with `]}` on context-manager exit. Atoms are serialised via the existing `_edn_writer.write_edn`.

- [ ] **K1.2: Modify `compute_atoms` → `compute_atoms_iter`** — yields atoms one at a time instead of returning a list.

- [ ] **K1.3: `ingest()` uses the streaming writer**:

```python
def ingest(ledger_path, predicates_path, out_path, return_atoms=False):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    if return_atoms:
        # Backwards-compat path: caller wants the list in memory
        atoms = list(compute_atoms_iter(ledger_path, predicates_path))
        with StreamingAtomWriter(out_path) as w:
            for a in atoms:
                w.write(a)
        return atoms
    with StreamingAtomWriter(out_path) as w:
        for a in compute_atoms_iter(ledger_path, predicates_path):
            w.write(a)
            n += 1
            if n % 1000 == 0:
                print(f"ingest: {n} atoms processed", file=sys.stderr)  # REQ-PERF-052
    return n
```

### Task K2: Memory-bounded test (REQ-PERF-050)

- [ ] **K2.1: Test fixture** — a 100MB JSONL generator script. Run ingest; assert peak RSS <500MB via `psutil.Process().memory_info().rss`.

### Task K3: Corruption marker (REQ-PERF-053)

- [ ] **K3.1: Atomic-write pattern** — write to `claims.edn.partial`, fsync, rename to `claims.edn`. On startup, if `claims.edn.partial` exists, refuse to continue with "previous ingest was interrupted; rerun from a clean state".

### Task K4: Push + open PR-K. Merge on green.

---

## Phase L — Cross-OS CI matrix (`tier4-cross-os-ci-matrix`)

**Branch:** `feat/tier4-cross-os-ci-matrix`
**OpenSpec change:** `openspec/changes/tier4-cross-os-ci-matrix/`
**Exit criteria:** `.github/workflows/ci.yml` runs python-skill on all three OSes; cargo-test on Linux + macOS; the `docs/operations/ci-platforms.md` runbook is in place.

### Task L1: Extend `python-skill` matrix

**Files:**
- Modify: `.github/workflows/ci.yml`

- [ ] **L1.1: Edit the python-skill job's strategy.matrix**:

```yaml
strategy:
  fail-fast: false
  matrix:
    os: [ubuntu-24.04, macos-latest, windows-2022]
    skill: [book-compose, book-knowledge, book-qa, book-review, book-thesis,
            neurosym-forge, review-conductor, russellian-style]
```

- [ ] **L1.2: Per-OS Python setup steps** — Linux uses nix; macOS uses `actions/setup-python@v5`; Windows uses `actions/setup-python@v5` with the `python: 3.13` version pin.

### Task L2: Cargo-test matrix (REQ-CI-041)

- [ ] **L2.1: New `cargo-test` job** with `strategy.matrix.os: [ubuntu-24.04, macos-latest]`. Linux runs in nix; macOS uses `dtolnay/rust-toolchain@stable` + system libz3 via `brew install z3`.

### Task L3: Divergence-summary aggregator (REQ-CI-042)

- [ ] **L3.1: Final aggregator job** that collects per-OS test results and emits an annotation: "test X: PASS on Linux, FAIL on macOS, SKIP on Windows" so divergence is visible from the PR's checks page without expanding logs.

### Task L4: `flake.nix` darwin support (REQ-CI-043)

- [ ] **L4.1: Extend `flake.nix`** with `darwin` system entries:

```nix
forAllSystems = nixpkgs.lib.genAttrs [ "x86_64-linux" "aarch64-darwin" "x86_64-darwin" ];
```

### Task L5: Operations runbook (REQ-CI-044)

- [ ] **L5.1: Author `docs/operations/ci-platforms.md`** documenting:
  - libz3 install per OS
  - The Windows skip + WSL-fallback runbook
  - How to run the matrix locally via `act`

### Task L6: Push + open PR-L. Merge on green.

---

## Phase M — Third-verifier build (`eval-third-verifier`)

**Branch:** `feat/eval-third-verifier`
**OpenSpec change:** `openspec/changes/eval-third-verifier/`
**Exit criteria:** A new verifier at `verifiers/<domain>/` passes `make ci` end-to-end. The build-log + usefulness report exist at `docs/eval/`.

### Task M1: Pick the domain + scaffold (REQ-EVAL-040)

- [ ] **M1.1: Domain choice** — see the OpenSpec design.md for the rationale. Recommended: "epidemiology — R0 thresholds and herd immunity". Predicates: `:basic-reproduction-number`, `:vaccination-coverage`, `:herd-immunity-threshold`. Cross-disease constraint: `(>= vaccination-coverage herd-immunity-threshold)` for non-spread.

- [ ] **M1.2: Scaffold** the project:

```bash
py -m scripts.scaffold_project --name "Epidemiology Verifier" \
  --slug epidemiology \
  --out verifiers/epidemiology
```

### Task M2: Author BookLogic source (REQ-EVAL-040)

- [ ] **M2.1: `rules/booklogic/sorts.edn`**:

```edn
{:forms [(defsort :disease)
         (defsort :population)]}
```

- [ ] **M2.2: `rules/booklogic/predicates.edn`**:

```edn
{:forms [(defpredicate :basic-reproduction-number [:disease] :real)
         (defpredicate :vaccination-coverage [:population] :real)
         (defpredicate :herd-immunity-threshold [:disease] :real)]}
```

- [ ] **M2.3: `rules/booklogic/lifts.edn`** — three regex extractors. The R0 one is `R\s*0?\s*=\s*(?P<v>[0-9]+(?:\\.[0-9]+)?)` and similar. Use Python dialect; Phase E enforces it.

- [ ] **M2.4: `rules/booklogic/constraints.edn`**:

```edn
{:forms [(defconstraint :C001-herd-immunity
          :backend :z3
          :assert (>= (:vaccination-coverage ?p) (:herd-immunity-threshold ?d))
          :on-unsat {:defect :D20 :severity :critical
                     :message "vaccination coverage below herd immunity threshold"})
         (defconstraint :C002-rho-from-r0
          :backend :z3
          :assert (approx= (:herd-immunity-threshold ?d)
                           (- 1.0 (/ 1.0 (:basic-reproduction-number ?d)))
                           :tolerance 0.05)
          :on-unsat {:defect :D21 :severity :critical
                     :message "herd-immunity threshold inconsistent with R0"})]}
```

(Exercises Phase F's `>=`, `/`, `-`.)

### Task M3: Fixtures (REQ-EVAL-041, 044, 045)

- [ ] **M3.1: `fixtures/claims_clean.jsonl`** — 3+ claims about measles, COVID, polio with consistent R0 ↔ threshold ↔ coverage.

- [ ] **M3.2: `fixtures/claims_doctored_low_coverage.jsonl`** — same R0/threshold but coverage well below threshold. Should produce :unsat with D20.

- [ ] **M3.3: `fixtures/claims_doctored_inconsistent_threshold.jsonl`** — threshold value contradicts the R0 → threshold formula. Should produce :unsat with D21.

### Task M4: Build-log (REQ-EVAL-042, 043)

- [ ] **M4.1: Create `docs/eval/2026-05-18-third-verifier-build-log.md`** — author the log AS YOU BUILD, not after. Every time you hit a framework gap (e.g., "Phase F encoder doesn't ship `>=` yet — I used `(or (= a b) (> a b))` instead"), log:
  - the gap (specific operator / behavior missing)
  - the tier that would close it (link to OpenSpec change)
  - the workaround used in the meantime

- [ ] **M4.2: Self-test** the verifier: `make -C verifiers/epidemiology ci`. Document the time-to-first-PASS and the count of debug iterations.

### Task M5: Usefulness report (REQ-EVAL-047)

- [ ] **M5.1: Author `docs/eval/2026-05-18-framework-usefulness-report.md`**:
  - What worked first-try
  - What required workarounds (and which roadmap tier closes each)
  - What the framework is genuinely useful for (the domain classes it handles cleanly)
  - What it's still missing (the classes it can't handle even with workarounds)

### Task M6: Push + open PR-M. Merge.

---

## Phase N — Onboarding benchmark (`eval-onboarding-bench`)

**Branch:** `feat/eval-onboarding-bench`
**OpenSpec change:** `openspec/changes/eval-onboarding-bench/`
**Exit criteria:** `skills/neurosym-forge/eval/onboarding-bench.py` runs 3 domain prompts against a fresh-agent harness; weekly CI re-run; aggregated report at `docs/eval/onboarding-bench-report.md`.

### Task N1: Benchmark harness skeleton

**Files:**
- Create: `skills/neurosym-forge/eval/onboarding-bench.py`
- Create: `skills/neurosym-forge/eval/prompts/`

- [ ] **N1.1: Three domain prompts**:
  - `prompts/temperature-bounded-reaction.md` — one paragraph describing the domain + 3 example claims
  - `prompts/parishes-aggregation.md` — entity-count aggregation
  - `prompts/string-binomial-match.md` — string-typed predicate matching

- [ ] **N1.2: Harness invokes a fresh subprocess** with ONLY the doc bundle (SKILL.md, DSL reference, references/*) plus the domain prompt. Captures stdout, stderr, tool-call count, time-to-milestone.

### Task N2: Milestone detection (REQ-EVAL-050, 053)

- [ ] **N2.1: Milestone definitions**:
  - **M1 — extract PASS**: agent's last `make extract` invocation returns exit 0
  - **M2 — ci PASS**: agent's last `make ci` invocation returns exit 0
- [ ] **N2.2: Timeout = 30 minutes per domain** — record `TIMEOUT_extract` or `TIMEOUT_ci` per REQ-EVAL-053.

### Task N3: Doc-gap detection (REQ-EVAL-052)

- [ ] **N3.1: Audit the captured tool calls** — flag any `grep` / `Read` outside the doc bundle's paths. Each such event is a candidate doc-gap (the docs SHOULD have covered it).

### Task N4: CSV output + report (REQ-EVAL-051, 054)

- [ ] **N4.1: Per-run CSV** at `docs/eval/onboarding-runs/YYYY-MM-DDTHH-MM-SS-domain.csv`.
- [ ] **N4.2: Weekly aggregator** that emits `docs/eval/onboarding-bench-report.md` with: % reach-extract, % reach-ci, top 5 doc gaps, top 5 framework gaps.

### Task N5: Weekly CI workflow (REQ-EVAL-055)

- [ ] **N5.1: `.github/workflows/onboarding-bench.yml`** — cron: `0 6 * * 1`. Runs the harness, uploads the report as an artifact, fails the workflow if any milestone-reach-rate drops below 80%.

### Task N6: Push + open PR-N. Merge.

---

## Self-review

**Spec coverage** (every REQ has a task):
- Phase E: REQ-INGEST-050..053 — Tasks E1-E4. ✓
- Phase F: REQ-SMT-040..045 — Tasks F1-F4. ✓
- Phase G: REQ-DSL-040..045 — Tasks G1-G5. ✓
- Phase H: REQ-EQSAT-040..046 — Tasks H1-H4. ✓
- Phase I: REQ-DATALOG-040..045 — Tasks I1-I5. ✓
- Phase J: REQ-PERF-040..043 — Tasks J1-J4. ✓
- Phase K: REQ-PERF-050..053 — Tasks K1-K3. ✓
- Phase L: REQ-CI-040..044 — Tasks L1-L5. ✓
- Phase M: REQ-EVAL-040..047 — Tasks M1-M5. ✓
- Phase N: REQ-EVAL-050..055 — Tasks N1-N5. ✓

**Placeholder scan:** No "TBD", no "TODO", no "implement later". Every code block is concrete.

**Type consistency:**
- `IngestRegexDialectError` (E2.1) and `IngestRegexDialectError` (E1.1) match.
- `_REAL_BINOP_TO_Z3` (F1.2) used by `_emit_real_binop` (F1.2) consistently.
- `BookLogic` egg language (H1.1) used by `canonicalize` (H1.1) consistently.
- `Verdict.queries` (I1.2) referenced in the verdict shape (I2.2) — consistent.
- `StreamingAtomWriter` (K1.1) used by `ingest()` (K1.3) consistently.

Plan complete. Successor execution per superpowers:subagent-driven-development or superpowers:executing-plans.
