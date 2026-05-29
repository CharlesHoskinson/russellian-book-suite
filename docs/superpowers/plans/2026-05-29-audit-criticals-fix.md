# Audit Criticals Fix — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax. **Every coding task is followed by a QA-agent verification step (the QA layer) — a fresh subagent that independently re-checks the fix before commit.**

**Goal:** Fix the seven critical findings from the 2026-05-29 suite-wide review (GitHub issues #135–#141).

**Architecture:** Five work items (two issues each collapse into one fix). Order by verifiability: Python + CI-config first (fully local), then the ClojureScript bridge (nbb/shadow-cljs), then the two Rust verifier fixes (cargo, Z3/cozo). Each fix is TDD-shaped and gated by an independent QA agent.

**Tech Stack:** Python 3.13/3.14 + pytest (book-qa), Bash/JSON (CI ruleset), ClojureScript via shadow-cljs/nbb (verifier orchestrator), Rust 1.96 edition 2024 + Z3 + Cozo (verifier core).

**Verified toolchain on this host:** rustc/cargo 1.96, cmake 4.3, JDK 21, nbb 1.4.207, shadow-cljs, Node 24, Python 3.14. Gap: `libclang` not on PATH (set `LIBCLANG_PATH` for the Z3 bindgen build); CI skips Windows cargo for the same Z3 reason, so Task 0 establishes the Z3 build or documents the CI fallback.

---

## The QA agent layer

After the coding agent finishes a task, dispatch a **separate QA subagent** with this contract:

> You are a QA reviewer. Do not edit code. Given finding `<issue#>` and the diff just produced on branch `fix/2026-05-29-audit-criticals`:
> 1. Re-read the original finding and the changed files.
> 2. Run the task's named test(s) and the affected skill/crate's full suite. Paste the real command output.
> 3. Confirm the change actually closes the finding (not a near-miss) and introduces no regression (no other test newly skipped/failed, no behavior narrowed).
> 4. Return `PASS` or `FAIL` with evidence (command output + file:line). Default to `FAIL` if you cannot run the verification.

Only commit a task after its QA agent returns `PASS`. On `FAIL`, the coding agent addresses the QA notes and the QA agent re-runs.

---

## Task 0: Branch + Rust/Z3 build prep

**Files:** none (environment).

- [ ] **Step 1:** Branch off `main` (not the review branch).

```bash
cd /c/Users/charl/russellian-book-suite
git fetch origin && git checkout -b fix/2026-05-29-audit-criticals origin/main
```

- [ ] **Step 2:** Establish a `book-qa` venv for local pytest (CLAUDE.md: each skill has its own `.venv`).

```bash
cd skills/book-qa && python -m venv .venv && .venv/Scripts/python.exe -m pip install -e .[dev]
.venv/Scripts/python.exe -m pytest tests/ -q   # baseline: expect green
```

- [ ] **Step 3:** Prep the Rust/Z3 build for Tasks 4–5. Set `LIBCLANG_PATH`, and enable a Z3 the `z3-sys` crate can find. Preferred: build the vendored Z3 via the `bundled` feature (cmake + MSVC + libclang are present).

```powershell
$env:LIBCLANG_PATH = "C:\Program Files\LLVM\bin"
# kg fix (Task 5) needs no Z3 — verify cozo path builds first:
cargo test --no-default-features --features kg --manifest-path verifiers/bermuda/rust-verifier/Cargo.toml
```

Expected: kg tests compile and run. If the `bundled`/system Z3 cannot be made to resolve on Windows after a reasonable attempt, record that in the task notes and fall back to **verify-by-inspection + push-to-CI** for the `smt`-feature parts of Task 4 (CI runs `cargo test --features smt` on Linux/macOS). Do not silently skip — log the fallback.

---

## Task 1: book-qa sentinel — route D9–D13 criticals to hard-fail (#135)

**Files:**
- Modify: `skills/book-qa/scripts/sentinel.py:30`
- Test: `skills/book-qa/tests/test_sentinel.py` (add case)

**Defect:** `HARD_FAIL_D_CLASSES = {"D1".."D8"}` only. `_is_hard_fail` already requires `severity == "critical"` for D-classes, but D9 (paragraph-orphan), D10 (transitive-contradiction), D11 (failed-entailment) and D13 (verification-unsat) — all critical per `SKILL.md:75-78,147` — are never in the set, so they route to the non-blocking soft gate. D12 (unadvanced-sub-argument) is `important`, so the severity guard keeps it soft even after the set widens.

- [ ] **Step 1: Write the failing test**

```python
# in skills/book-qa/tests/test_sentinel.py
import json
from pathlib import Path
from scripts.sentinel import aggregate

def test_critical_d9_d13_are_hard_fail(tmp_path: Path):
    qa = tmp_path / "qa"; qa.mkdir()
    (qa / "defects.json").write_text(json.dumps({"defects": [
        {"class": "D9",  "severity": "critical", "where": "ch01", "detail": "orphan"},
        {"class": "D11", "severity": "critical", "where": "ch02", "detail": "failed entailment"},
        {"class": "D13", "severity": "critical", "where": "doc",  "detail": "verification unsat"},
        {"class": "D12", "severity": "important", "where": "ch03", "detail": "unadvanced"},
    ]}), encoding="utf-8")
    report = aggregate(tmp_path)
    hard = {t["class"] for t in report.hard_fail_tickets}
    assert {"D9", "D11", "D13"} <= hard, hard
    assert "D12" not in hard  # important stays soft
    assert report.hard_fail_count >= 3
```

- [ ] **Step 2: Run it, verify it fails**

Run: `cd skills/book-qa && .venv/Scripts/python.exe -m pytest tests/test_sentinel.py::test_critical_d9_d13_are_hard_fail -q`
Expected: FAIL (D9/D11/D13 currently land in soft gate).

- [ ] **Step 3: Implement the fix**

```python
# sentinel.py:30 — widen the set; the severity=="critical" guard in
# _is_hard_fail keeps the `important` classes (e.g. D12) soft.
HARD_FAIL_D_CLASSES = {
    "D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8",
    "D9", "D10", "D11", "D12", "D13",
}
```

Also update the module docstring (`sentinel.py:8-14`) so the hard-fail policy text lists the reasoning classes.

- [ ] **Step 4: Run the test + full suite**

Run: `.venv/Scripts/python.exe -m pytest tests/ -q`
Expected: new test PASS, no regressions.

- [ ] **Step 5: QA agent** verifies finding #135 (see QA layer). Then commit.

```bash
git add skills/book-qa/scripts/sentinel.py skills/book-qa/tests/test_sentinel.py
git commit -m "book-qa: route critical D9-D13 reasoning defects to hard-fail gate"
```

---

## Task 2: Branch-protection required checks point at live jobs (#136, #137)

**Files:**
- Modify: `scripts/ruleset-apply.sh:40-47`
- Modify: `docs/operations/branch-protection.md` (the required-contexts list, ~line 11)

**Defect:** Both reference the old split-job contexts (`lint`, `scaffold-bake`, `regression (sprint-5)`, `verifier (bermuda)`, `verifier (osmotic-pressure)`) that `ci.yml` no longer emits — it collapsed them into `nix preflight (...)` + `cargo-test (...)` and an aggregator job named `ci required ✓` (`ci.yml:228-229`, `if: always()`, fails if any needed job failed). The aggregator is the intended single required context.

- [ ] **Step 1:** In `scripts/ruleset-apply.sh`, replace the six-entry `required_status_checks` list (lines 41-46) with the single live aggregator:

```bash
        "required_status_checks": [
          { "context": "ci required ✓" }
        ]
```

- [ ] **Step 2:** In `docs/operations/branch-protection.md`, update the required-status-check list to name only `ci required ✓`, and add a one-line note: required contexts must match `ci.yml` job `name:` values exactly; when CI jobs are renamed, update this doc and `ruleset-apply.sh` in the same change.

- [ ] **Step 3: Verify (no runtime).** Cross-check against `ci.yml`:

Run: `grep -nE "name:\s*ci required" .github/workflows/ci.yml` → confirms the context string exists.
Run: `grep -n "context" scripts/ruleset-apply.sh` → only `ci required ✓` remains.

- [ ] **Step 4: QA agent** confirms no stale context string survives in either file and the kept string matches `ci.yml` byte-for-byte (including the ✓). Then commit.

```bash
git add scripts/ruleset-apply.sh docs/operations/branch-protection.md
git commit -m "ci: require the live 'ci required' aggregator, drop stale split-job contexts"
```

> Note: applying the ruleset (`bash scripts/ruleset-apply.sh`) is an admin action against the live repo — out of scope here. The fix is correcting the config; the user applies it.

---

## Task 3: ClojureScript verifier bridge emits the flat atom contract (#138, #139)

**Files:**
- Modify: `verifiers/bermuda/cljs-orchestrator/src/main/bermuda/nl_to_fol.cljs`
- Modify: `verifiers/bermuda/cljs-orchestrator/src/main/bermuda/phases.cljs:19`
- Modify: `verifiers/bermuda/cljs-orchestrator/src/main/bermuda/ir.cljs` (the `Formula` malli schema)
- Test: `verifiers/bermuda/cljs-orchestrator/src/test/bermuda/nl_to_fol_test.cljs` (+ phases test)
- Apply the **same** changes to `verifiers/adsc-clinical/cljs-orchestrator/...` (the two copies diverged; reconcile both).

**Decision (grounded):** Fix the **cljs side**. The Rust `ir.rs` doc (`ir.rs:1-13`) and `parse_formulas`/`bind_atoms` define the canonical contract — a top-level `{:atoms [...]}` map whose atoms are **flat**: `{:kind :expression :id "<id>" :predicate <kw> :subject <kw> :value <scalar>}`. The Python ingesters already emit exactly this; `nl_to_fol` is the only producer emitting nested `:head`/`:args` expression trees, which `bind_atoms` skips (`smt.rs:328-351`). So cljs is the outlier.

- [ ] **Step 1: Write the failing test** (run under nbb — no native addon needed; asserts shape conformance to the Rust contract).

```clojure
;; src/test/bermuda/nl_to_fol_test.cljs
(ns bermuda.nl-to-fol-test
  (:require [clojure.test :refer [deftest is]]
            [bermuda.nl-to-fol :as t]))

(deftest legacy-claim-emits-flat-atom
  (let [claim {:id "clm-1" :s "Bermuda" :p "land-area-km2"
               :o {:kind :quantity :value 54 :unit "km2"} :c []}
        [atom] (t/translate-corpus [claim])]
    (is (= :expression (:kind atom)))
    (is (= "clm-1" (:id atom)))
    (is (keyword? (:predicate atom)))
    (is (keyword? (:subject atom)))
    (is (contains? atom :value))
    ;; the nested IR keys must be gone
    (is (not (contains? atom :head)))
    (is (not (contains? atom :args)))))
```

- [ ] **Step 2: Run it, verify it fails**

Run: `cd verifiers/bermuda && nbb -cp cljs-orchestrator/src/main:cljs-orchestrator/src/test -e "(require '[bermuda.nl-to-fol-test]) (cljs.test/run-tests 'bermuda.nl-to-fol-test)"`
(If nbb cannot resolve the meander dep, run via shadow-cljs `:test` build instead: `npx shadow-cljs compile test && node cljs-orchestrator/dist/test.js`.)
Expected: FAIL — current output has `:head`/`:args`, no `:predicate`/`:subject`.

- [ ] **Step 3: Rewrite `legacy-claim->formula`** to emit a flat atom. Replace the nested meander template (`nl_to_fol.cljs:21-47`) with:

```clojure
(defn- legacy-claim->formula [claim]
  (m/rewrite claim
    {:id ?id :s ?subj :p ?pred
     :o {:kind :quantity :value ?v :unit ?u}}
    {:kind :expression :id ?id
     :predicate ~(keyword ?pred)
     :subject   ~(keyword ?subj)
     :value     ~(to-si ?v ?u)}
    ?other {:kind :symbol :sort :formula}))
```

Update `event->formula` likewise so any atom it emits uses the flat `{:kind :expression :id .. :predicate .. :subject .. :value ..}` shape (or `{:kind :symbol ...}` / `nil` for non-atoms), matching `ir.rs`.

- [ ] **Step 4: Update the `Formula` malli schema** in `ir.cljs` to the flat shape so `phases/translate`'s `:post` and `phases/verify`'s `:pre` contracts accept the new atoms (read the current `ir.cljs` `Formula`/`ClaimOrEvent` defs and adjust; the schema must allow `{:kind :expression :id string :predicate keyword :subject keyword :value [:or int double string boolean]}` and the `{:kind :symbol ...}` variant).

- [ ] **Step 5: Wrap the verify payload** (`phases.cljs:19`) so `parse_formulas` finds top-level `:atoms`:

```clojure
(defn verify [formulas]
  {:pre  (m/validate [:vector ir/Formula] formulas)
   :post (m/validate ir/Verdict %)}
  (b/verify-formulas (pr-str {:version 1 :atoms formulas})))
```

- [ ] **Step 6: Run the cljs test suite**

Run (shadow-cljs): `cd verifiers/bermuda && npx shadow-cljs compile test && node cljs-orchestrator/dist/test.js`
Expected: new test PASS; existing nl_to_fol/phases tests updated to the flat shape and green.

- [ ] **Step 7:** Apply the identical edits to `verifiers/adsc-clinical/cljs-orchestrator/...` and run its test build.

- [ ] **Step 8: QA agent** verifies #138 + #139: the emitted atom matches `ir.rs:5-8` field-for-field, `pr-str {:atoms ...}` parses through `parse_formulas`' `:atoms` requirement, both verifier copies changed, and the malli contracts still hold. Then commit.

```bash
git add verifiers/bermuda/cljs-orchestrator verifiers/adsc-clinical/cljs-orchestrator
git commit -m "verifier(cljs): emit flat {:atoms [...]} contract the Rust SMT path consumes"
```

---

## Task 4: adsc-clinical smt.rs — add the Edn::UInt bind arm (#140)

**Files:**
- Modify: `verifiers/adsc-clinical/rust-verifier/src/smt.rs` (the `bind_atoms` value `match`, ~line 82)
- Test: `verifiers/adsc-clinical/rust-verifier/tests/` (add a golden/unit test) or `#[cfg(test)]` in smt.rs

**Defect:** `bermuda/smt.rs:371-377` has an `Edn::UInt(n)` arm (edn-rs renders bare non-negative ints as `UInt`); `adsc-clinical/smt.rs` lacks it, so a plain-integer constraint value (e.g. `:trial-n 15`) falls through `_ => continue` and is never asserted to Z3 — a silent false-`sat`.

- [ ] **Step 1: Write the failing test** — assert that a UInt-valued atom produces a tracked assertion (mirror bermuda's existing smt test for the int arm; read bermuda's test for the exact harness).

- [ ] **Step 2: Run it** (`cargo test --features smt --manifest-path verifiers/adsc-clinical/rust-verifier/Cargo.toml`, with `LIBCLANG_PATH` set). Expected: FAIL (value dropped). If Z3 can't be built locally per Task 0 fallback, mark the test added and verify by inspection + CI.

- [ ] **Step 3: Port the arm** from bermuda `smt.rs:371-377` into adsc-clinical's `bind_atoms` value match, immediately after the `Edn::Int(n)` arm:

```rust
            // edn-rs renders bare non-negative integers as `Edn::UInt`.
            Edn::UInt(n) => {
                let n_i64: i64 = (*n)
                    .try_into()
                    .map_err(|_| Error::Smt(format!("value too large to bind as Int: {n}")))?;
                let z3_var = Int::new_const(var_name.as_str());
                z3_var.eq(&Int::from_i64(n_i64))
            }
```

- [ ] **Step 4: Run tests** — new test PASS; `cargo test` green (or CI fallback logged).

- [ ] **Step 5: QA agent** verifies #140: the arm matches bermuda's semantics, a UInt value is now asserted (not skipped), and diffs adsc vs bermuda `bind_atoms` for any remaining divergence (note the separate `?`-strip var-name high finding at adsc `smt.rs:70` as follow-up, out of this critical's scope). Then commit.

```bash
git add verifiers/adsc-clinical/rust-verifier/src/smt.rs verifiers/adsc-clinical/rust-verifier/tests
git commit -m "verifier(adsc-clinical): bind Edn::UInt integer values to Z3 (fix silent false-sat)"
```

---

## Task 5: kg.rs queries undefined relations — fix the codegen, not the generated file (#141)

**Files:**
- Source of truth: `verifiers/bermuda/rules/booklogic/queries.edn` and the neurosym-forge `codegen_kg` template/script (find via `grep -rl codegen_kg skills/neurosym-forge`).
- Regenerated: `verifiers/bermuda/rust-verifier/src/kg.rs` (header: `GENERATED ... DO NOT EDIT BY HAND ... npm run codegen-kg`).

**Defect:** `kg.rs build_db` (`kg.rs:165-185`) creates only the `claim {id, source}` relation, but the generated `ingest_and_summarize` query (`kg.rs:193`) reads `claim/load-bearing` and `claim/posterior`, which never exist → cozo errors → `verify_formulas` returns `Err` on every default (kg-enabled) build.

- [ ] **Step 1: Locate the codegen.** `grep -rl "codegen_kg\|codegen-kg\|build_db\|load-bearing" skills/neurosym-forge verifiers/bermuda/rules` to find the template that emits `build_db` and the query, and `queries.edn` Q001.

- [ ] **Step 2: Write the failing test.** A `#[cfg(feature = "kg")]` Rust test that calls `kg::ingest_and_summarize(&claims)` with a sample claim and asserts it returns `Ok` (today it returns `Err` because the relations are missing).

- [ ] **Step 3: Run it** — `cargo test --no-default-features --features kg --manifest-path verifiers/bermuda/rust-verifier/Cargo.toml`. Expected: FAIL (`cozo run` error: unknown relation).

- [ ] **Step 4: Fix the codegen so the generated relations match the queries.** The query needs `claim/load-bearing[id, bool]` and `claim/posterior[id, float]` relations. The correct fix is in the codegen template: `build_db` must `:create` and `:put` those relations (sourced from the claim slice's load-bearing flag and posterior), OR the codegen must emit a relation-existence guard so a query against an unpopulated relation yields zero rows instead of erroring. Choose the populate-the-relations approach (matches the query's intent — flag low-confidence load-bearing claims). Edit `queries.edn`/template, then regenerate:

```bash
npm run codegen-kg   # regenerates kg.rs for every verifier
git diff --stat verifiers/*/rust-verifier/src/kg.rs
```

- [ ] **Step 5: Run the kg test suite** for bermuda (and any other regenerated verifier). Expected: `ingest_and_summarize` returns `Ok`; low-confidence-load-bearing rows surface as contradictions when seeded.

- [ ] **Step 6: QA agent** verifies #141: confirms the file was regenerated (not hand-edited — header intact), `build_db`'s relations now satisfy every relation the generated queries read, and the default-feature build no longer errors on `ingest_and_summarize`. Then commit.

```bash
git add verifiers/bermuda/rules verifiers/*/rust-verifier/src/kg.rs skills/neurosym-forge
git commit -m "verifier(kg): generate the claim relations the defquery reads (fix Err on every verify)"
```

---

## Self-review notes

- **Coverage:** #135→T1, #136+#137→T2, #138+#139→T3, #140→T4, #141→T5. All seven issues mapped.
- **Verifiability tiers:** T1 (Python) and T2 (config) verify fully locally. T3 verifies via shadow-cljs/nbb against the documented Rust contract (no native addon needed for shape conformance). T4/T5 need cargo; T5 (kg/cozo) needs no Z3, T4 (smt) needs Z3 — Task 0 establishes it or logs the CI fallback. No silent skips.
- **Ordering rationale:** independent fixes, ordered easy→hard so momentum and the QA loop are validated on the cheap ones first. T3's two copies and T5's codegen are the divergence/regeneration risks — QA agents explicitly check both.
- **Out of scope (not criticals):** the related highs (healer.py D9-D13 payloads, adsc `?`-strip var-name, eqsat panic-on-parse) are noted in QA steps as follow-ups, not fixed here.
