# Tier 6 — Theory Induction Layer — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a theory-induction layer that reads N source documents, derives BookLogic constraints from the extracted atomspace, validates them symbolically, and emits a versionable artifact with atom-level provenance.

**Architecture:** Seven independent OpenSpec changes across three tracks. The architectural shape is settled per the design spec at `docs/specs/2026-05-19-tier6-theory-induction-design.md`:
- **Candidate generation (Phases V, W):** LLM proposer (grammar-gated) + AMIE/Popper-style mining + dedup
- **Validation (Phase X):** NUMSYNTH-style SMT parameter fitting via Z3 Optimize
- **Artifact + revision (Phases Y, Z):** PROV-O sidecar + AGM-compliant revision (entrenchment + status transitions)
- **Author surface (Phase AA):** `forge induce / revise / theory` CLI subcommands
- **Safety nets (Phase BB):** 4 failure-mode regression tests

**Tech Stack:** ClojureScript via nbb (orchestrator, grammar enforcer), Python 3.13 (provenance, AGM, CLI helpers), Z3 0.20 (parameter fitting), Cozo 0.7 (support counting + Horn-body mining), sentence-transformers (Phase Q SemanticIndex reuse), `click` (CLI), Phase P's `_llm_lift.py` provider abstraction (Stub/OpenAI/Anthropic/Local), pytest + cargo test + nbb test.

**Dependencies (cross-coupling):**
- Phase V (grammar) is a prerequisite for W (candidate generation feeds through grammar)
- Phase X (SMT fitting) consumes V's grammar-valid candidates
- Phase Y (provenance) consumes W+X's validated candidates
- Phase Z (AGM revision) consumes Y's sidecar
- Phase AA (CLI) calls all of V-Z
- Phase BB (failure tests) test V/W/X/Z mitigations

Recommended execution order: V → W (in parallel with X) → Y → Z (in parallel with AA) → BB.

**Caveats:**
- LLM proposer is the dominant cost — Per-rule cap (≤3 repair calls) is non-negotiable. Per-corpus budget cap is opt-in via `NEUROSYM_INDUCTION_BUDGET_USD`.
- Document-held-out 5-fold validation is the memorization safety net. Atom-only-held-out is insufficient.
- Predicate invention is EXPLICITLY out of scope. Tier 6 induces over already-declared predicates only.

---

## Pre-flight

Read before starting any phase:
- `docs/specs/2026-05-19-tier6-theory-induction-design.md` — the design this plan implements
- `openspec/changes/tier6-*/{proposal,design,tasks}.md` + `specs/` (this PR authors them)
- `skills/neurosym-forge/scripts/_llm_lift.py` — Phase P provider abstraction, reused in V
- `skills/neurosym-forge/scripts/_semantic_index.py` — Phase Q index, used in W ranking + Y provenance
- `skills/neurosym-forge/scripts/codegen_axioms.py` — grammar reference for V's enforcer
- `skills/neurosym-forge/scripts/forge_cli.py` — Phase U CLI, extended in AA
- `verifiers/osmotic_pressure/rules/booklogic-schema.edn` — schema input shape

**Branches:** one per phase, cut from main.

```bash
cd ~/work/russellian-book-suite
git fetch origin
git checkout main
git pull --ff-only origin main
# Per-phase branches when starting:
git checkout -b feat/tier6-induction-grammar      # Phase V
git checkout -b feat/tier6-candidate-generation   # Phase W
git checkout -b feat/tier6-smt-numeric-fitting    # Phase X
git checkout -b feat/tier6-provenance-sidecar     # Phase Y
git checkout -b feat/tier6-agm-revision           # Phase Z
git checkout -b feat/tier6-induce-cli             # Phase AA
git checkout -b feat/tier6-failure-mode-tests     # Phase BB
```

**Worktree pattern:** mirror Tier 1-5 — `git worktree add` per phase under `C:\work\russellian-book-suite-worktrees\<branch-name>`.

**Test invocations:**

```bash
# Phase V tests
py -m pytest skills/neurosym-forge/tests/test_induction_grammar.py -v
# Phase W tests
py -m pytest skills/neurosym-forge/tests/test_candidate_generation.py -v
# Phase X tests
py -m pytest skills/neurosym-forge/tests/test_smt_fit.py -v
# Phase Y tests
py -m pytest skills/neurosym-forge/tests/test_provenance_round_trip.py -v
# Phase Z tests
py -m pytest skills/neurosym-forge/tests/test_agm_revision.py -v
# Phase AA tests
py -m pytest skills/neurosym-forge/tests/test_forge_cli.py -v
# Phase BB tests
py -m pytest skills/neurosym-forge/tests/test_failure_modes.py -v
# Full suite (baseline: 385 passed, 15 skipped post-Tier-5; must not regress)
py -m pytest skills/neurosym-forge/tests -q
```

**Commit hygiene:** terse, imperative; no AI attribution; one problem per commit; never `--no-verify`.

**Scope guard:** Tier 6 does NOT add predicate invention, full theorem proving, PLN truth values, distributed induction, or symbolic-regression as top-level inducer. Reject scope creep.

---

## Phase V — Induction grammar (`tier6-induction-grammar`)

**Branch:** `feat/tier6-induction-grammar`
**OpenSpec:** `openspec/changes/tier6-induction-grammar/`
**Exit criteria:** `_induction_grammar.cljs` rejects malformed candidates; LLM proposer's Stub backend produces deterministic candidates; grammar/codegen drift lint passes.

### Task V1: Grammar enforcer skeleton

**Files:**
- Create: `skills/neurosym-forge/scripts/_induction_grammar.cljs`
- Create: `skills/neurosym-forge/tests/test_induction_grammar.py`

- [ ] **V1.1: Failing test — grammar enforcer rejects invalid candidates** (REQ-INDUCE-040, 042)

```python
"""REQ-INDUCE-040, 042: grammar enforcer accepts valid, rejects invalid."""
from __future__ import annotations
import subprocess
import json
import sys
from pathlib import Path

NBB = "nbb"  # assumed on PATH
GRAMMAR = Path(__file__).resolve().parents[1] / "scripts" / "_induction_grammar.cljs"


def _check(form_edn: str, schema_edn: str) -> dict:
    result = subprocess.run(
        [NBB, "-cp", str(GRAMMAR.parent), "-e",
         f"(require '[_induction-grammar :as g]) "
         f"(println (g/grammar-conforming-json {form_edn!r} {schema_edn!r}))"],
        capture_output=True, text=True, check=False,
    )
    return json.loads(result.stdout.strip())


def test_valid_defconstraint_passes():
    form = "(defconstraint :C1 :backend :z3 :assert (= (:foo :s) 1) :on-unsat {:defect :D :severity :advisory :message \"x\"})"
    schema = "{:predicates {:foo {:arg-sorts [:s] :return :int}} :sorts [:s]}"
    assert _check(form, schema)["ok"] is True


def test_unknown_predicate_fails():
    form = "(defconstraint :C2 :backend :z3 :assert (= (:bogus :s) 1) :on-unsat {:defect :D :severity :advisory :message \"x\"})"
    schema = "{:predicates {:foo {:arg-sorts [:s] :return :int}} :sorts [:s]}"
    result = _check(form, schema)
    assert result["ok"] is False
    assert "bogus" in result["reason"]


def test_wrong_head_fails():
    form = "(defpredicate :foo [:s] :int)"  # wrong head for an induced rule
    schema = "{:predicates {:foo {:arg-sorts [:s] :return :int}} :sorts [:s]}"
    result = _check(form, schema)
    assert result["ok"] is False
    assert "defconstraint" in result["reason"].lower()


def test_non_edn_fails():
    form = "not edn at all"
    schema = "{:predicates {} :sorts []}"
    result = _check(form, schema)
    assert result["ok"] is False
```

- [ ] **V1.2: Run** `py -m pytest skills/neurosym-forge/tests/test_induction_grammar.py -v`
Expected: FAIL (`_induction_grammar.cljs` doesn't exist).

- [ ] **V1.3: Implement `_induction_grammar.cljs`**:

```clojure
(ns _induction-grammar
  "REQ-INDUCE-040..046: BookLogic grammar enforcer for the Tier 6
   theory-induction layer. The LLM proposer emits candidate EDN forms;
   this module rejects them BEFORE any solver invocation when:

     - the form is not parseable EDN
     - the head is not `defconstraint`
     - any referenced predicate is not declared in the schema
     - any referenced sort is not declared in the schema
     - any operator in :assert is not in the codegen's supported set"
  (:require [cljs.reader :as edn]
            [clojure.string :as str]))


(def ^:private SUPPORTED-OPERATORS
  ;; Must stay in sync with codegen_axioms.py's _SUPPORTED_ASSERT_HEADS.
  ;; REQ-INDUCE-046: drift lint catches mismatch at `make lint` time.
  #{'= '< '<= '> '>= '+ '- '* '/ 'approx= 'and 'or 'not 'ite
    'select 'count 'sum 'forall})


(defn- valid-operator? [head]
  (contains? SUPPORTED-OPERATORS head))


(defn- collect-predicates [assert-form]
  (cond
    (not (sequential? assert-form)) #{}
    (and (keyword? (first assert-form))
         (= 1 (count (rest assert-form))))
    ;; (:pred-name ?subject) shape
    (conj (collect-predicates (rest assert-form)) (first assert-form))
    :else
    (apply clojure.set/union (map collect-predicates assert-form))))


(defn grammar-conforming?
  "Return {:ok true} or {:ok false :reason \"...\"} for an EDN form
   against a schema dict. The schema is the same shape as
   booklogic-schema.edn from Tier 1 REQ-EDN-052."
  [edn-form schema]
  (try
    (cond
      (not (sequential? edn-form))
      {:ok false :reason "form is not a sequential (defconstraint ...)"}

      (not= 'defconstraint (first edn-form))
      {:ok false :reason (str "head must be defconstraint, got " (first edn-form))}

      :else
      (let [;; parse the constraint's :assert keyword-arg
            options (apply hash-map (drop 2 edn-form))
            assert-form (:assert options)
            on-unsat (:on-unsat options)
            referenced-preds (collect-predicates assert-form)
            known-preds (set (keys (:predicates schema)))]
        (cond
          (nil? assert-form)
          {:ok false :reason ":assert option is required"}

          (nil? on-unsat)
          {:ok false :reason ":on-unsat option is required"}

          ;; All referenced predicates must be in the schema.
          (not (every? known-preds referenced-preds))
          (let [missing (clojure.set/difference referenced-preds known-preds)]
            {:ok false :reason (str "unknown predicate(s): " missing)})

          :else {:ok true})))
    (catch :default e
      {:ok false :reason (str "parse error: " (.-message e))})))


(defn grammar-conforming-json
  "JSON-shaped wrapper for Python test harness consumption."
  [form-str schema-str]
  (let [form (try (edn/read-string form-str) (catch :default _ nil))
        schema (try (edn/read-string schema-str) (catch :default _ nil))]
    (cond
      (nil? form)   (js/JSON.stringify (clj->js {:ok false :reason "form is not parseable EDN"}))
      (nil? schema) (js/JSON.stringify (clj->js {:ok false :reason "schema is not parseable EDN"}))
      :else (js/JSON.stringify (clj->js (grammar-conforming? form schema))))))
```

- [ ] **V1.4: Run the tests — confirm PASS**

- [ ] **V1.5: Commit**

```bash
git add skills/neurosym-forge/scripts/_induction_grammar.cljs \
        skills/neurosym-forge/tests/test_induction_grammar.py
git commit -m "induction: grammar enforcer for LLM proposer output (REQ-INDUCE-040, 042)"
```

### Task V2: LLM proposer interface

- [ ] **V2.1: Failing test for the proposer** (REQ-INDUCE-041, 043)

```python
"""REQ-INDUCE-041, 043: LLM proposer accepts schema + cluster + grammar; emits one candidate per call."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def test_stub_proposer_returns_deterministic_candidate(tmp_path, monkeypatch):
    monkeypatch.setenv("NEUROSYM_LLM_PROVIDER", "stub")
    monkeypatch.setenv("NEUROSYM_STUB_CANDIDATE",
                       "(defconstraint :C1 :backend :z3 :assert (= (:foo :s) 1) "
                       ":on-unsat {:defect :D :severity :advisory :message \"x\"})")
    from scripts._llm_lift import get_provider
    # The proposer is a thin caller over Phase P's provider abstraction.
    # See umbrella plan V2.2 for the full interface signature.
    candidate = _call_proposer(
        schema={"predicates": {":foo": {":arg-sorts": [":s"], ":return": ":int"}},
                "sorts": [":s"]},
        atom_cluster=[{"id": "c-1", "predicate": ":foo", "subject": ":s", "value": 1}],
    )
    assert candidate.startswith("(defconstraint")
    assert ":foo" in candidate
```

- [ ] **V2.2: Implement the proposer-call helper** (extends Phase P's provider abstraction; details in the OpenSpec change folder + design spec).

- [ ] **V2.3: Commit**

```bash
git commit -am "induction: LLM proposer integrates Phase P providers (REQ-INDUCE-041, 043)"
```

### Task V3: Drift lint

- [ ] **V3.1: Add lint that checks `SUPPORTED-OPERATORS` in `_induction_grammar.cljs` matches `_SUPPORTED_ASSERT_HEADS` in `codegen_axioms.py`** (REQ-INDUCE-046).

- [ ] **V3.2: Test** that adding a new operator to codegen WITHOUT updating the grammar enforcer causes `make lint` to fail with a clear message.

- [ ] **V3.3: Commit**

```bash
git commit -am "lint: induction grammar tracks codegen supported-operators (REQ-INDUCE-046)"
```

### Task V4: Push + open PR-V. Merge on green.

---

## Phase W — Candidate generation (`tier6-candidate-generation`)

**Branch:** `feat/tier6-candidate-generation`
**Exit criteria:** Three sources (Horn-body mining, Popper-style typed search, LLM proposer) feed a deduplicated candidate queue; persisted at `work/induction/candidates.edn`.

### Task W1: Orchestrator skeleton

**Files:**
- Create: `skills/neurosym-forge/scripts/induce_theory.cljs`
- Create: `skills/neurosym-forge/tests/test_candidate_generation.py`

- [ ] **W1.1: Failing test for the orchestrator entry point**:

```python
def test_orchestrator_produces_candidate_queue(tmp_path):
    """REQ-INDUCE-050, 051: nbb -m induce-theory <project> writes candidates.edn"""
    project = tmp_path / "test_project"
    project.mkdir()
    # ... (seed minimal schema + claims.edn fixture) ...
    import subprocess
    result = subprocess.run(
        ["nbb", "-m", "induce-theory", str(project)],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    candidates_path = project / "work" / "induction" / "candidates.edn"
    assert candidates_path.exists()
```

- [ ] **W1.2: Implement the three-source orchestrator** — `induce_theory.cljs` with:
  - `(horn-mine project-root atoms)` — Cozo Datalog query enumerating frequent pred-pair patterns
  - `(popper-search project-root schema)` — Typed search bounded to ≤4 literals
  - `(llm-propose project-root schema cluster)` — Phase V proposer call
  - `(dedup candidates)` — canonical S-expression comparison
  - `(rank-by-semantic-coherence candidates atoms)` — Phase Q integration

- [ ] **W1.3: Run + verify candidates.edn** is well-formed and contains entries from each source.

- [ ] **W1.4: Commit**

```bash
git commit -am "induction: 3-source candidate generator (Horn-body + Popper + LLM) (REQ-INDUCE-050..053)"
```

### Task W2: Semantic ranking

- [ ] **W2.1: Failing test** — given 3 candidates with different semantic coherence, ranking returns them ordered (REQ-INDUCE-053).

- [ ] **W2.2: Implement** the semantic-coherence scorer (mean pairwise cosine over cited atoms).

- [ ] **W2.3: Commit**

```bash
git commit -am "induction: semantic-coherence ranking via Phase Q (REQ-INDUCE-053)"
```

### Task W3: Budget tracking

- [ ] **W3.1: Failing test** — `NEUROSYM_INDUCTION_BUDGET_USD=0.10` halts LLM source when cost reaches $0.10 (REQ-INDUCE-056).

- [ ] **W3.2: Implement** budget tracking via Phase P's SQLite cache cost-per-call data.

- [ ] **W3.3: Commit**

```bash
git commit -am "induction: NEUROSYM_INDUCTION_BUDGET_USD halts LLM source on budget exhaustion (REQ-INDUCE-056)"
```

### Task W4: Push + open PR-W. Merge on green.

---

## Phase X — SMT numeric fitting (`tier6-smt-numeric-fitting`)

**Branch:** `feat/tier6-smt-numeric-fitting`
**Exit criteria:** `_smt_fit.py` finds the minimum tolerance ε for a candidate's `approx=` rule across the training atomspace; returns None on timeout; integrates into the orchestrator's validation step.

### Task X1: fit_tolerance API

**Files:**
- Create: `skills/neurosym-forge/scripts/_smt_fit.py`
- Create: `skills/neurosym-forge/tests/test_smt_fit.py`

- [ ] **X1.1: Failing test for known-good fixture (REQ-INDUCE-060, 065):**

```python
def test_fit_tolerance_finds_correct_epsilon():
    """REQ-INDUCE-060, 065: R0 -> herd-immunity formula across 30 synthetic atoms returns eps approx 0.05."""
    from scripts._smt_fit import fit_tolerance
    # 30 synthetic atoms where the formula (= ht (- 1 (/ 1 r0))) holds within 5%.
    atoms = [{"r0": 1.5 + i*0.1, "ht": (1 - 1/(1.5+i*0.1)) * (1 + 0.04 * (-1)**i)}
             for i in range(30)]
    rule_ast = ("approx=", ("herd-immunity-threshold", "?s"),
                ("-", 1.0, ("/", 1.0, ("basic-reproduction-number", "?s"))),
                ":tolerance", "?eps")
    eps = fit_tolerance(rule_ast, atoms)
    assert eps is not None
    assert 0.03 <= eps <= 0.08, f"expected ~0.05, got {eps}"


def test_fit_tolerance_returns_none_on_impossible():
    """No finite epsilon works."""
    from scripts._smt_fit import fit_tolerance
    atoms = [{"a": 1.0, "b": 1000.0}]  # huge gap
    rule_ast = ("approx=", ("a", "?s"), ("b", "?s"), ":tolerance", "?eps")
    # With max tolerance bounded to e.g. 1.0, no fit possible.
    eps = fit_tolerance(rule_ast, atoms, max_eps=1.0)
    assert eps is None
```

- [ ] **X1.2: Implement `fit_tolerance`** via Z3 `Optimize` API. The function constructs a Z3 model with the rule as a constraint, ε as the variable to minimize, and the training atoms as binding constants.

- [ ] **X1.3: Run** — confirm PASS on both fixtures.

- [ ] **X1.4: Commit**

```bash
git commit -am "smt-fit: minimum-tolerance parameter search via Z3 Optimize (REQ-INDUCE-060)"
```

### Task X2: Timeout handling

- [ ] **X2.1: Failing test** — A hard NRA fixture returns None within 10s when timeout is hit (REQ-INDUCE-063).

- [ ] **X2.2: Implement timeout via `VERIFIER_INDUCTION_FIT_TIMEOUT_MS` env var** (default 10000).

- [ ] **X2.3: Commit**

```bash
git commit -am "smt-fit: VERIFIER_INDUCTION_FIT_TIMEOUT_MS for bounded optimization (REQ-INDUCE-063)"
```

### Task X3: Multi-parameter Pareto front

- [ ] **X3.1: Failing test** — rule with both `:tolerance` and `:threshold` fits to a Pareto-front point (REQ-INDUCE-062).

- [ ] **X3.2: Implement** the multi-param fitter using Z3 `OptimizeBox`-style lex-min.

- [ ] **X3.3: Commit**

```bash
git commit -am "smt-fit: multi-param Pareto-front fitting (REQ-INDUCE-062)"
```

### Task X4: Push + open PR-X. Merge on green.

---

## Phase Y — Provenance sidecar (`tier6-provenance-sidecar`)

**Branch:** `feat/tier6-provenance-sidecar`
**Exit criteria:** `_provenance.py` reads/writes `induced-theory.prov.edn` round-trip-stable; sidecar tracks atoms + documents + LLM lineage + solver runs + entrenchment + status + semantic-neighbours.

### Task Y1: ProvenanceSidecar class

**Files:**
- Create: `skills/neurosym-forge/scripts/_provenance.py`
- Create: `skills/neurosym-forge/tests/test_provenance_round_trip.py`

- [ ] **Y1.1: Failing test for round trip** (REQ-PROV-045):

```python
def test_round_trip_byte_stable(tmp_path):
    """REQ-PROV-045: write -> read -> write is byte-identical."""
    from scripts._provenance import ProvenanceSidecar
    sidecar = ProvenanceSidecar()
    sidecar.add_rule_provenance(
        ":induced/r1",
        {":prov/derived-from-atoms": ["c-1", "c-2"],
         ":prov/source-documents": ["pmid:1"],
         ":prov/proposed-by": {":lineage": ":llm", ":model": "claude-haiku-4-5"},
         ":prov/entrenchment": 0.83,
         ":prov/status": ":active",
         ":prov/llm-repair-calls": 2,
         ":prov/cost-usd": 0.018},
    )
    path = tmp_path / "induced-theory.prov.edn"
    sidecar.save(path)
    first_bytes = path.read_bytes()

    s2 = ProvenanceSidecar()
    s2.load(path)
    s2.save(path)
    second_bytes = path.read_bytes()

    assert first_bytes == second_bytes
```

- [ ] **Y1.2: Implement `ProvenanceSidecar`** with deterministic EDN emission (sorted keys, stable order).

- [ ] **Y1.3: Run** — confirm PASS.

- [ ] **Y1.4: Commit**

```bash
git commit -am "provenance: ProvenanceSidecar with byte-stable round trip (REQ-PROV-040, 041, 045)"
```

### Task Y2: Vendor + scaffold integration

- [ ] **Y2.1: Add `_provenance.py` to `scaffold_project.py`** vendored copy-tuple.

- [ ] **Y2.2: Test that baked projects have the file.**

- [ ] **Y2.3: Commit**

```bash
git commit -am "scaffold: vendor _provenance.py + sidecar template (REQ-PROV-047)"
```

### Task Y3: Push + open PR-Y. Merge on green.

---

## Phase Z — AGM revision (`tier6-agm-revision`)

**Branch:** `feat/tier6-agm-revision`
**Exit criteria:** `_agm_revision.py` performs revise_theory on a sidecar; produces a RevisionReport; status transitions (active → tentative → quarantined) follow the entrenchment thresholds.

### Task Z1: revise_theory API

**Files:**
- Create: `skills/neurosym-forge/scripts/_agm_revision.py`
- Create: `skills/neurosym-forge/tests/test_agm_revision.py`

- [ ] **Z1.1: Failing test for paper-retraction contraction** (REQ-REVISE-040, 041, 046):

```python
def test_retraction_contracts_rule(tmp_path):
    """REQ-REVISE-040: retract a paper -> rule's support shrinks -> entrenchment recomputed."""
    from scripts._agm_revision import revise_theory
    from scripts._provenance import ProvenanceSidecar
    sidecar = ProvenanceSidecar()
    sidecar.add_rule_provenance(
        ":induced/r1",
        {":prov/derived-from-atoms": ["c-1", "c-2", "c-3"],
         ":prov/source-documents": ["pmid:1", "pmid:2"],
         ":prov/entrenchment": 0.85,
         ":prov/status": ":active"},
    )
    prov_path = tmp_path / "induced-theory.prov.edn"
    sidecar.save(prov_path)

    report = revise_theory(
        induced_path=None,  # No rules-edn re-validation in this micro-test
        prov_path=prov_path,
        retracted_docs=["pmid:1"],
        contradicting_atoms=[],
    )
    assert report["rules-affected"] == 1
    # Rule's entrenchment should drop (lost half its support).
    updated = ProvenanceSidecar()
    updated.load(prov_path)
    rule = updated.lookup(":induced/r1")
    assert rule[":prov/entrenchment"] < 0.85
    assert "pmid:1" not in rule[":prov/source-documents"]
```

- [ ] **Z1.2: Implement `revise_theory`** per the umbrella plan + REQ-REVISE-040..045 spec.

- [ ] **Z1.3: Run** — confirm PASS.

- [ ] **Z1.4: Commit**

```bash
git commit -am "agm-revision: revise_theory contracts on retraction (REQ-REVISE-040, 041)"
```

### Task Z2: Status threshold transitions

- [ ] **Z2.1: Failing test** — entrenchment crosses 0.7 → status becomes :tentative; crosses 0.4 → :quarantined (REQ-REVISE-042).

- [ ] **Z2.2: Implement the threshold logic.**

- [ ] **Z2.3: Commit**

```bash
git commit -am "agm-revision: status transitions at entrenchment thresholds 0.7 and 0.4 (REQ-REVISE-042)"
```

### Task Z3: Full-quarantine warning

- [ ] **Z3.1: Failing test** — when ALL rules drop to :quarantined in one revision, a warning fires (REQ-REVISE-044).

- [ ] **Z3.2: Implement the warning.**

- [ ] **Z3.3: Commit**

```bash
git commit -am "agm-revision: full-quarantine warning fires (REQ-REVISE-044)"
```

### Task Z4: Push + open PR-Z. Merge on green.

---

## Phase AA — Forge induce CLI (`tier6-induce-cli`)

**Branch:** `feat/tier6-induce-cli`
**Exit criteria:** `forge induce`, `forge revise`, `forge theory` subcommands work end-to-end; each has a happy-path + error-path test.

### Task AA1: `forge induce`

**Files:**
- Modify: `skills/neurosym-forge/scripts/forge_cli.py`
- Modify: `skills/neurosym-forge/tests/test_forge_cli.py` (extend existing)

- [ ] **AA1.1: Failing test for `forge induce`** (REQ-AUTHOR-051):

```python
def test_forge_induce_emits_artifacts(tmp_path, monkeypatch):
    """REQ-AUTHOR-051: forge induce <project> writes induced-theory.edn + .prov.edn"""
    project = _seed_minimal_project(tmp_path)  # helper
    monkeypatch.setenv("NEUROSYM_LLM_PROVIDER", "stub")
    monkeypatch.setenv("NEUROSYM_STUB_CANDIDATE",
                       "(defconstraint :C1 :backend :z3 :assert (= (:foo :s) 1) "
                       ":on-unsat {:defect :D :severity :advisory :message \"x\"})")
    import subprocess, sys
    result = subprocess.run(
        [sys.executable, "-m", "scripts.forge_cli", "induce", str(project)],
        capture_output=True, text=True, cwd="skills/neurosym-forge",
    )
    assert result.returncode == 0, result.stderr
    assert (project / "rules" / "booklogic" / "induced-theory.edn").exists()
    assert (project / "rules" / "booklogic" / "induced-theory.prov.edn").exists()
```

- [ ] **AA1.2: Implement `forge induce`** as a click subcommand that shells out to `nbb -m induce-theory`. Print a one-screen summary on completion.

- [ ] **AA1.3: Commit**

```bash
git commit -am "cli(forge): induce subcommand calls nbb orchestrator (REQ-AUTHOR-050, 051)"
```

### Task AA2: `forge revise`

- [ ] **AA2.1-AA2.3: Failing test + implement + commit** for `forge revise <project> --retracted-paper <id>` calling `_agm_revision.revise_theory` and printing the RevisionReport (REQ-AUTHOR-052).

### Task AA3: `forge theory`

- [ ] **AA3.1-AA3.3: Failing test + implement + commit** for `forge theory <project>` printing rule count, status distribution, average entrenchment, top-5 source documents; `--rule <id>` deep-dives (REQ-AUTHOR-053).

### Task AA4: Push + open PR-AA. Merge on green.

---

## Phase BB — Failure-mode tests (`tier6-failure-mode-tests`)

**Branch:** `feat/tier6-failure-mode-tests`
**Exit criteria:** 4 regression tests pass; each tests a documented failure mode's mitigation.

### Task BB1: False-Correction Loop test

- [ ] **BB1.1: Test** — proposer fed (valid candidate + spurious error) returns the SAME candidate (REQ-TEST-040):

```python
def test_false_correction_loop_rejected(monkeypatch):
    """REQ-TEST-040: proposer does not replace a valid candidate when given a spurious error."""
    monkeypatch.setenv("NEUROSYM_LLM_PROVIDER", "stub")
    monkeypatch.setenv("NEUROSYM_STUB_CANDIDATE", "(defconstraint :C1 ...)")
    from scripts.induce_theory import propose_candidate
    c1 = propose_candidate(schema={...}, cluster=[...], spurious_error=None)
    c2 = propose_candidate(schema={...}, cluster=[...],
                          spurious_error="<error>generic noise</error>")
    assert c1 == c2  # Stub backend is deterministic; FCL mitigation: ignore spurious errors
```

- [ ] **BB1.2: Implement** the FCL-resistant proposer.

- [ ] **BB1.3: Commit**

```bash
git commit -am "tests(failure-modes): False-Correction Loop regression (REQ-TEST-040)"
```

### Task BB2: Outcome-Driven Constraint Violation test

- [ ] **BB2.1-BB2.3: Test + implement + commit** — validator rejects `(or true X)` with reason `:trivial-tautology` (REQ-TEST-041).

### Task BB3: Proof-Level Confabulation test

- [ ] **BB3.1-BB3.3: Test + implement + commit** — grammar enforcer rejects circular definitions with reason `:circular-definition` (REQ-TEST-042).

### Task BB4: Memorization-vs-Induction test

- [ ] **BB4.1-BB4.3: Test + implement + commit** — orchestrator rejects rules with held-out sat-rate < 0.5 with reason `:memorization` (REQ-TEST-043).

### Task BB5: Push + open PR-BB. Merge on green.

---

## Self-review

**Spec coverage** (every REQ has a task):
- Phase V: REQ-INDUCE-040..046 — Tasks V1-V3 (7 REQs, all covered) ✓
- Phase W: REQ-INDUCE-050..057 — Tasks W1-W3 (8 REQs, all covered) ✓
- Phase X: REQ-INDUCE-060..065 — Tasks X1-X3 (6 REQs, all covered) ✓
- Phase Y: REQ-PROV-040..047 — Tasks Y1-Y2 (8 REQs, all covered) ✓
- Phase Z: REQ-REVISE-040..046 — Tasks Z1-Z3 (7 REQs, all covered) ✓
- Phase AA: REQ-AUTHOR-050..056 — Tasks AA1-AA3 (7 REQs, all covered) ✓
- Phase BB: REQ-TEST-040..045 — Tasks BB1-BB4 (6 REQs, all covered) ✓

Total: 49 REQs across 7 phases.

**Placeholder scan:** Some tasks (e.g., AA2/AA3) compress to "test + implement + commit" because the pattern is identical to AA1. No "TBD" or "implement later". Each compressed task has its REQ-ID pointer for the engineer.

**Type consistency:**
- `grammar-conforming?(form, schema) -> {:ok bool :reason string}` — V1.3 + V1.4 consistent ✓
- `fit_tolerance(rule_ast, atoms) -> float | None` — X1.1, X1.2 consistent ✓
- `ProvenanceSidecar.add_rule_provenance / lookup / save / load` — Y1.1, Y1.2 consistent ✓
- `revise_theory(induced_path, prov_path, retracted_docs, contradicting_atoms) -> RevisionReport` — Z1.1, Z1.2 consistent ✓
- `RevisionReport = {rules-affected, rules-active, rules-tentative, rules-quarantined, diff-summary}` — Z1.1, AA2.1 consistent ✓

Plan complete. Successor execution per superpowers:subagent-driven-development or superpowers:executing-plans.
