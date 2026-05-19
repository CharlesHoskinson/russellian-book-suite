# BookLogic v0.5 — Boolean Connectives + General Quantifiers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the BookLogic `:assert` grammar with **boolean head connectives** (`and`, `or`, `not`, `=>`) and **general quantifiers** (`forall`, `exists`) over the sort registry. This closes the remaining expressivity gap surfaced by EpochPoET's joint-threshold conjecture and provenance constraints — comparison + division + `ite` already landed in PR #80 (Tier 2F, REQ-SMT-040..045).

**Architecture:** `_emit_z3_block` (the assert-head dispatcher in `codegen_axioms.py`) gains four boolean arms (`and`/`or`/`not`/`=>`) and two quantifier arms (`forall`/`exists`). The boolean arms compose existing Bool-valued sub-expressions (each child must itself be a comparison, equality, approx-equality, or nested boolean). The quantifier arms introduce typed bound constants via Z3's `mk_forall_const` / `mk_exists_const` and thread a `bound_vars` dict through `_emit_expr_typed` so `?var` symbols inside the body resolve to the right Z3 const. Sort-keyword bindings are validated against the sort registry; an undeclared sort raises `CodegenError`. Backward compatibility is total: every existing constraint compiles byte-identical (deterministic-output test pins this).

**Tech Stack:** Python 3.11+ (codegen), Rust + `z3` 0.12 crate, EDN-on-disk handoff, pytest for codegen unit tests + cargo check for output compilability.

**Repo:** `/c/russellian-book-suite/`. Branch: `feat/booklogic-v0.5-extended-operators` (rebased onto current `origin/main` after PR #80 landed).

**Prior art (NOT redone here):**
- **PR #80 (Tier 2F, REQ-SMT-040..045)** shipped `<`, `<=`, `>`, `>=`, `/`, `ite` at both assert-head and sub-expression levels, plus the §2.5 DSL reference update. This plan is a strict delta on top of that work.
- **PR #76 (Tier 2-4 umbrella)** sketched a Phase G for vector-bounded `(forall ?x in vec ...)` desugaring. That is bounded quantification over a known-size vector and is orthogonal to the general construction over a sort registry that this plan adds.

**REQ ids reserved:** `REQ-SMT-046..050` (boolean connectives), `REQ-SMT-051..055` (general quantifiers), `REQ-BOOKLOGIC-051..053` (docs + SUPPORT_MATRIX sync). Numbers do not conflict with `REQ-SMT-040..045` (PR #80) or `REQ-BOOKLOGIC-040..050` (Tier 1D).

---

## File structure

```
russellian-book-suite/
├── skills/neurosym-forge/
│   ├── scripts/
│   │   └── codegen_axioms.py                    Modify — add 6 head arms + bound_vars threading
│   ├── tests/
│   │   ├── test_codegen_axioms.py               Extend — 7 boolean + 2 bound-var tests
│   │   ├── test_codegen_axioms_quantifiers.py   Create — 4 quantifier tests
│   │   └── golden/
│   │       └── extended_operators_v0_5.edn      Create — cross-language fixture
│   └── SUPPORT_MATRIX.md                        Modify — add boolean + quantifier rows
├── docs/
│   └── booklogic-dsl-reference.md               Modify — add §2.6 boolean, §2.7 quantifier
└── openspec/changes/
    └── booklogic-v0.5-boolean-quantifiers/      Create — REQ records
        ├── proposal.md
        ├── design.md
        └── tasks.md
```

---

## Phase A — OpenSpec change record (Task 0)

#### Task 0: OpenSpec record + branch readiness

**Files:**
- Create: `openspec/changes/booklogic-v0.5-boolean-quantifiers/proposal.md`
- Create: `openspec/changes/booklogic-v0.5-boolean-quantifiers/design.md`
- Create: `openspec/changes/booklogic-v0.5-boolean-quantifiers/tasks.md`

- [ ] **Step 1: Confirm branch state**

```bash
cd /c/russellian-book-suite
git rev-parse --abbrev-ref HEAD
# expect: feat/booklogic-v0.5-extended-operators
git log --oneline -3
# expect: the plan commit on top of PR #80 / #82 ancestry
```

- [ ] **Step 2: Author `proposal.md`** with the REQ list from the header above and an explicit "Out of scope" section that names:
  - Bounded `(forall ?x in vec ...)` (Tier 2 Phase G — separate work)
  - Trigger pattern annotations (deferred to Tier 5)
  - A new `D14` defect class (codegen already raises `CodegenError` loudly)
  - Ratio EDN literal parsing (`1/3` is rewritten to `(/ 1 3)` in v0.5; ratio parsing is a future EDN-reader change)

- [ ] **Step 3: Author `design.md`** — content is the "Architecture" paragraph above, fleshed out with the Z3 Rust API signatures (`Bool::and/or`, `<expr>.not()`, `<expr>.implies()`, `ctx.mk_forall_const(&bound, &body, &[], &[], &[], &[])`) and the `bound_vars: dict[str, str]` threading convention.

- [ ] **Step 4: Author `tasks.md`** — checklist mapping each REQ to its task in this plan.

- [ ] **Step 5: Commit**

```bash
git add openspec/changes/booklogic-v0.5-boolean-quantifiers/
git commit -m "openspec: v0.5 boolean connectives + general quantifiers (REQ-SMT-046..055, REQ-BOOKLOGIC-051..053)"
```

---

## Phase B — Boolean connectives (Tasks 1–2)

#### Task 1: Bool-subexpression encoder + `and` / `or`

**Files:**
- Modify: `skills/neurosym-forge/scripts/codegen_axioms.py:_emit_z3_block` and surrounding helpers
- Modify: `skills/neurosym-forge/tests/test_codegen_axioms.py` (3 new tests)

- [ ] **Step 1: Probe the post-#80 helpers**

```bash
cd /c/russellian-book-suite
grep -nE "_emit_bool|_emit_real_binop|_emit_ite|_emit_bool_assert_block|_emit_approx_block" skills/neurosym-forge/scripts/codegen_axioms.py | head -10
```

Find the post-#80 helper that wraps a Bool expression in `assert_and_track`. The plan calls it `_emit_bool_assert_block`; if PR #80 named it differently (e.g., `_assert_bool_track`, `_emit_assert_bool`), use whatever the actual name is in subsequent steps.

- [ ] **Step 2: Write the failing tests** (append to `tests/test_codegen_axioms.py`):

```python
def test_generate_and_assertion():
    # (and (< (:f-stake :e) 0.3) (>= (:domain-count :e) 3))
    constraints = [
        {Keyword("name"): Symbol("CB001"),
         Keyword("backend"): Keyword("z3"),
         Keyword("assert"): (Symbol("and"),
                             (Symbol("<"), (Keyword("f-stake"), Keyword("e")), 0.3),
                             (Symbol(">="), (Keyword("domain-count"), Keyword("e")), 3)),
         Keyword("track"): Keyword("CB001"),
         Keyword("on-unsat"): {Keyword("defect"): Keyword("D13"),
                               Keyword("severity"): Keyword("critical"),
                               Keyword("message"): "threshold fails"}}
    ]
    out = generate_axioms_source(constraints, [])
    assert "Bool::and" in out
    assert "Real::lt" in out
    assert "Real::ge" in out or "Int::ge" in out


def test_generate_or_assertion():
    constraints = _wrap_one(Symbol("or"),
                            (Symbol("="), (Keyword("status"), Keyword("e")), "ok"),
                            (Symbol("="), (Keyword("status"), Keyword("e")), "pending"))
    out = generate_axioms_source(constraints, [])
    assert "Bool::or" in out


def test_generate_nested_and_or():
    inner_or = (Symbol("or"),
                (Symbol("="), (Keyword("color"), Keyword("e")), "red"),
                (Symbol("="), (Keyword("color"), Keyword("e")), "blue"))
    body = (Symbol("and"),
            (Symbol(">="), (Keyword("count"), Keyword("e")), 1),
            inner_or)
    constraints = _wrap_one_form(body)
    out = generate_axioms_source(constraints, [])
    assert "Bool::and" in out
    assert "Bool::or" in out
```

Add helpers `_wrap_one(head, lhs, rhs)` and `_wrap_one_form(body)` if absent — both wrap an assert form into the canonical single-constraint list with default `:name`, `:backend :z3`, `:track`, and `:on-unsat` map.

- [ ] **Step 3: Run — expect 3 FAILs**

```bash
cd /c/russellian-book-suite/skills/neurosym-forge
./.venv/Scripts/python.exe -m pytest tests/test_codegen_axioms.py -k "and_assertion or or_assertion or nested_and_or" -v
```

Expected: `CodegenError: ... assert head 'and' not supported; expected one of [...]`.

- [ ] **Step 4: Implement the Bool-subexpression encoder**

Extract a helper `_emit_bool_subexpr(node, bound_vars=None)` near `_emit_real_binop`. It dispatches on the same heads `_emit_z3_block` does (`=`, `~=`/`approx=`, `<`, `<=`, `>`, `>=`, `ite`, plus the boolean heads added below) and returns the Bool-typed Rust expression *without* `assert_and_track`. Refactor the existing comparison and equality blocks to compose this helper internally where possible.

Then add to `_emit_z3_block` immediately after the `head == "ite"` arm:

```python
    if head == "and":
        if len(assert_) < 3:
            raise CodegenError(
                f"constraint {cid!r}: 'and' requires at least 2 operands, got {len(assert_)-1}"
            )
        parts = [_emit_bool_subexpr(child) for child in assert_[1:]]
        body = f"Bool::and(ctx, &[{', '.join('&' + p for p in parts)}])"
        return _emit_bool_assert_block(cid, body)
    if head == "or":
        if len(assert_) < 3:
            raise CodegenError(
                f"constraint {cid!r}: 'or' requires at least 2 operands, got {len(assert_)-1}"
            )
        parts = [_emit_bool_subexpr(child) for child in assert_[1:]]
        body = f"Bool::or(ctx, &[{', '.join('&' + p for p in parts)}])"
        return _emit_bool_assert_block(cid, body)
```

(Use the actual helper name from Step 1 if it differs from `_emit_bool_assert_block`.)

- [ ] **Step 5: Run — expect 3 PASS**

- [ ] **Step 6: Verify no regression**

```bash
./.venv/Scripts/python.exe -m pytest tests/ -q
```

- [ ] **Step 7: Commit**

```bash
cd /c/russellian-book-suite
git add skills/neurosym-forge/scripts/codegen_axioms.py skills/neurosym-forge/tests/test_codegen_axioms.py
git commit -m "feat(codegen): and / or in :assert (REQ-SMT-046, 047, 050)"
```

#### Task 2: `not` and `=>`

**Files:**
- Modify: `skills/neurosym-forge/scripts/codegen_axioms.py:_emit_z3_block`
- Modify: `skills/neurosym-forge/tests/test_codegen_axioms.py` (2 new tests)

- [ ] **Step 1: Write the failing tests**

```python
def test_generate_not_assertion():
    constraints = _wrap_one_form((Symbol("not"),
                                  (Symbol("="), (Keyword("status"), Keyword("e")), "failed")))
    out = generate_axioms_source(constraints, [])
    assert ".not()" in out


def test_generate_implies_assertion():
    premise = (Symbol("<"), (Keyword("f-stake"), Keyword("e")), 0.3)
    conclusion = (Symbol("<="), (Keyword("max-per-domain-fraction"), Keyword("e")), 0.25)
    constraints = _wrap_one(Symbol("=>"), premise, conclusion)
    out = generate_axioms_source(constraints, [])
    assert ".implies(" in out
```

- [ ] **Step 2: Run — expect 2 FAILs**

- [ ] **Step 3: Implement** — append to `_emit_z3_block`:

```python
    if head == "not":
        if len(assert_) != 2:
            raise CodegenError(
                f"constraint {cid!r}: 'not' requires exactly 1 operand, got {len(assert_)-1}"
            )
        inner = _emit_bool_subexpr(assert_[1])
        body = f"{inner}.not()"
        return _emit_bool_assert_block(cid, body)
    if head == "=>":
        if len(assert_) != 3:
            raise CodegenError(
                f"constraint {cid!r}: '=>' requires exactly 2 operands, got {len(assert_)-1}"
            )
        premise = _emit_bool_subexpr(assert_[1])
        conclusion = _emit_bool_subexpr(assert_[2])
        body = f"{premise}.implies(&{conclusion})"
        return _emit_bool_assert_block(cid, body)
```

- [ ] **Step 4: Run — expect 2 PASS**

- [ ] **Step 5: Commit**

```bash
git add skills/neurosym-forge/scripts/codegen_axioms.py skills/neurosym-forge/tests/test_codegen_axioms.py
git commit -m "feat(codegen): not and => in :assert (REQ-SMT-048, 049)"
```

---

## Phase C — Variable refs + general quantifiers (Tasks 3–4)

#### Task 3: Bound-variable resolution

**Files:**
- Modify: `skills/neurosym-forge/scripts/codegen_axioms.py` — thread `bound_vars` through `_emit_expr` / `_emit_expr_typed` / `_emit_bool_subexpr`
- Modify: `skills/neurosym-forge/tests/test_codegen_axioms.py` (2 new tests)

- [ ] **Step 1: Write the failing tests**

```python
def test_unbound_variable_reference_raises():
    # Plain `(= ?x 5)` outside any quantifier scope must raise.
    constraints = _wrap_one(Symbol("="), Symbol("?x"), 5)
    with pytest.raises(CodegenError, match=r"unbound variable '\?x'"):
        generate_axioms_source(constraints, [])


def test_bound_variable_reference_resolves_to_z3_const():
    from scripts.codegen_axioms import _emit_expr
    bound = {"?x": "x_const"}
    rendered = _emit_expr(Symbol("?x"), bound_vars=bound)
    assert rendered == "x_const"
```

- [ ] **Step 2: Run — expect 2 FAILs**

- [ ] **Step 3: Implement**

Add a `bound_vars: dict[str, str] | None = None` keyword parameter to `_emit_expr`, `_emit_expr_typed`, and `_emit_bool_subexpr`. Inside each, when a `Symbol` whose name starts with `?` appears:

```python
def _emit_expr(node, bound_vars=None):
    if isinstance(node, Symbol):
        name = str(node)
        if name.startswith("?"):
            if not bound_vars or name not in bound_vars:
                raise CodegenError(
                    f"unbound variable {name!r} (not in any forall/exists scope)"
                )
            return bound_vars[name]
        # fall through to existing Symbol handling
    # ... rest unchanged
```

Then grep every `_emit_expr(` / `_emit_expr_typed(` / `_emit_bool_subexpr(` callsite and thread `bound_vars=bound_vars` through. The default `None` preserves existing behaviour.

- [ ] **Step 4: Run — expect 2 PASS, no regression**

- [ ] **Step 5: Commit**

```bash
git add skills/neurosym-forge/scripts/codegen_axioms.py skills/neurosym-forge/tests/test_codegen_axioms.py
git commit -m "feat(codegen): bound variable resolution in expressions (REQ-SMT-053)"
```

#### Task 4: `forall` and `exists`

**Files:**
- Modify: `skills/neurosym-forge/scripts/codegen_axioms.py:_emit_z3_block`
- Modify: `skills/neurosym-forge/scripts/codegen_axioms.py:generate_axioms_source` (build declared-sort set; propagate)
- Create: `skills/neurosym-forge/tests/test_codegen_axioms_quantifiers.py` (4 tests)

- [ ] **Step 1: Write the failing tests** — create `tests/test_codegen_axioms_quantifiers.py`:

```python
import pytest
from scripts.codegen_axioms import generate_axioms_source, CodegenError
from scripts._edn_reader import Keyword, Symbol


def _quant(quant_head, bindings, body, sorts=None):
    return ([{Keyword("name"): Symbol("CQ001"),
              Keyword("backend"): Keyword("z3"),
              Keyword("assert"): (Symbol(quant_head), bindings, body),
              Keyword("track"): Keyword("CQ001"),
              Keyword("on-unsat"): {Keyword("defect"): Keyword("D13"),
                                    Keyword("severity"): Keyword("critical"),
                                    Keyword("message"): "quantifier check failed"}}],
            sorts or [])


def test_forall_single_var():
    constraints, sorts = _quant("forall",
                                [(Symbol("?o"), Keyword("proof-obligation"))],
                                (Symbol("="), Symbol("?o"), Keyword("special")),
                                sorts=[{Keyword("name"): Keyword("proof-obligation")}])
    out = generate_axioms_source(constraints, sorts)
    assert "mk_forall_const" in out


def test_exists_single_var():
    constraints, sorts = _quant("exists",
                                [(Symbol("?r"), Keyword("reference"))],
                                (Symbol("="), Symbol("?r"), Keyword("v2-spec")),
                                sorts=[{Keyword("name"): Keyword("reference")}])
    out = generate_axioms_source(constraints, sorts)
    assert "mk_exists_const" in out


def test_forall_two_vars_with_implication():
    # The EpochPoET C003 pattern.
    body = (Symbol("=>"),
            (Keyword("contradicts"), Symbol("?a"), Symbol("?b")),
            (Keyword("supersedes"), Symbol("?a"), Symbol("?b")))
    constraints, sorts = _quant("forall",
                                [(Symbol("?a"), Keyword("proof-obligation")),
                                 (Symbol("?b"), Keyword("proof-obligation"))],
                                body,
                                sorts=[{Keyword("name"): Keyword("proof-obligation")}])
    out = generate_axioms_source(constraints, sorts)
    assert "mk_forall_const" in out
    assert ".implies" in out


def test_undeclared_sort_in_binding_raises():
    constraints, sorts = _quant("forall",
                                [(Symbol("?x"), Keyword("nonexistent-sort"))],
                                (Symbol("="), Symbol("?x"), 5),
                                sorts=[])
    with pytest.raises(CodegenError, match=r"sort 'nonexistent-sort' not declared"):
        generate_axioms_source(constraints, sorts)
```

- [ ] **Step 2: Run — expect 4 FAILs**

- [ ] **Step 3: Build the declared-sort set in `generate_axioms_source`**

Top of `generate_axioms_source`:

```python
def generate_axioms_source(constraints, sorts):
    declared_sort_names = {
        (s[Keyword("name")].name if hasattr(s[Keyword("name")], "name") else str(s[Keyword("name")]))
        for s in sorts
        if isinstance(s, dict) and Keyword("name") in s
    }
    # ... existing code, threading declared_sort_names into _emit_z3_block callsite
```

Make `declared_sort_names` available inside `_emit_z3_block` either via parameter or via a closure binding.

- [ ] **Step 4: Add the quantifier arms to `_emit_z3_block`** (after the `=>` arm):

```python
    if head in ("forall", "exists"):
        if len(assert_) != 3:
            raise CodegenError(
                f"constraint {cid!r}: '{head}' requires (bindings, body), got {len(assert_)-1} args"
            )
        bindings, body_node = assert_[1], assert_[2]
        if not isinstance(bindings, (list, tuple, EdnList, EdnVector)):
            raise CodegenError(
                f"constraint {cid!r}: '{head}' bindings must be a vector, got {type(bindings).__name__}"
            )
        bound_vars: dict[str, str] = {}
        const_decls: list[str] = []
        for pair in bindings:
            if not (isinstance(pair, (list, tuple, EdnList, EdnVector)) and len(pair) == 2):
                raise CodegenError(
                    f"constraint {cid!r}: '{head}' binding must be (?var :sort), got {pair!r}"
                )
            var, sort_kw = pair[0], pair[1]
            if not (isinstance(var, Symbol) and str(var).startswith("?")):
                raise CodegenError(
                    f"constraint {cid!r}: '{head}' bound variable must start with '?', got {var!r}"
                )
            if not isinstance(sort_kw, Keyword):
                raise CodegenError(
                    f"constraint {cid!r}: '{head}' bound variable sort must be a Keyword, got {sort_kw!r}"
                )
            sort_name = sort_kw.name if hasattr(sort_kw, "name") else str(sort_kw)
            if sort_name not in declared_sort_names:
                raise CodegenError(
                    f"constraint {cid!r}: sort {sort_name!r} not declared in sorts.edn"
                )
            const_name = canonical_var_name(str(var)) + "_const"
            sort_const = canonical_var_name(sort_name) + "_sort"
            const_decls.append(
                f"let {const_name} = Datatype::new_const(ctx, {str(var)!r}, &{sort_const});"
            )
            bound_vars[str(var)] = const_name

        body_rendered = _emit_bool_subexpr(body_node, bound_vars=bound_vars)

        bound_refs = ", ".join(f"&{n}.clone().into()" for n in bound_vars.values())
        api = "mk_forall_const" if head == "forall" else "mk_exists_const"
        quantified = (
            "{ "
            + " ".join(const_decls)
            + f" ctx.{api}(&[{bound_refs}], &{body_rendered}, &[], &[], &[], &[])"
            + " }"
        )
        return _emit_bool_assert_block(cid, quantified)
```

- [ ] **Step 5: Add `Datatype` to the preamble imports**

```bash
grep -n "use z3" skills/neurosym-forge/scripts/codegen_axioms.py
```

Append `Datatype` to the `use z3::ast::{Bool, Int, Real, ...}` list in whatever preamble template the file emits.

- [ ] **Step 6: Run — expect 4 PASS**

- [ ] **Step 7: Verify osmotic_pressure still passes cargo check**

```bash
cd /c/russellian-book-suite/verifiers/osmotic_pressure
make clean && make build
cargo check 2>&1 | tail -5
```

- [ ] **Step 8: Commit**

```bash
cd /c/russellian-book-suite
git add skills/neurosym-forge/scripts/codegen_axioms.py skills/neurosym-forge/tests/test_codegen_axioms_quantifiers.py
git commit -m "feat(codegen): forall and exists quantifiers (REQ-SMT-051, 052, 054)"
```

---

## Phase D — Docs sync + golden fixture (Task 5)

#### Task 5: SUPPORT_MATRIX + DSL reference §2.6–§2.7 + golden fixture

**Files:**
- Modify: `skills/neurosym-forge/SUPPORT_MATRIX.md` (add 2 rows)
- Modify: `docs/booklogic-dsl-reference.md` (add §2.6 boolean, §2.7 quantifier)
- Create: `skills/neurosym-forge/tests/golden/extended_operators_v0_5.edn`
- Modify: `skills/neurosym-forge/tests/test_codegen_axioms.py` (1 golden-comparison test)

- [ ] **Step 1: Extend SUPPORT_MATRIX.md**

Add to the form-family table (after the post-#80 rows):

```markdown
| `defconstraint :assert (and / or / not / =>)`  | wired        | `codegen_axioms.py` | Z3           | **wired (v0.5)** |
| `defconstraint :assert (forall / exists)`      | wired        | `codegen_axioms.py` | Z3           | **wired (v0.5)** |
```

Add a note under the "Roadmap pointers" section:

> - Tier 5: explicit `:trigger` pattern annotations for quantifiers (replaces
>   the empty-patterns fallback that relies on Z3's MBQI).

- [ ] **Step 2: Add §2.6 to `docs/booklogic-dsl-reference.md`** with a table of `and`/`or`/`not`/`=>` arities and Z3 emit targets, plus a worked-example block: the EpochPoET joint-threshold conjecture written as `(and (>= ...) (< ...) (<= ...))`.

- [ ] **Step 3: Add §2.7** with a table of `forall`/`exists` arities and emit targets, plus the universal contradiction-with-supersession worked example. Include an implementation note that v0.5 emits empty trigger patterns; explicit triggers are deferred.

- [ ] **Step 4: Author `tests/golden/extended_operators_v0_5.edn`**:

```edn
{:cases
 [{:name "and-binary"
   :sorts []
   :assert (and (< (:f-stake :e) 0.3)
                (>= (:domain-count :e) 3))
   :expected-z3-call "Bool::and"}

  {:name "or-binary"
   :sorts []
   :assert (or (= (:status :e) "ok")
               (= (:status :e) "pending"))
   :expected-z3-call "Bool::or"}

  {:name "not-unary"
   :sorts []
   :assert (not (= (:status :e) "failed"))
   :expected-z3-call ".not()"}

  {:name "implies-binary"
   :sorts []
   :assert (=> (< (:f-stake :e) 0.3)
               (<= (:max-per-domain-fraction :e) 0.25))
   :expected-z3-call ".implies("}

  {:name "forall-implication"
   :sorts [(:proof-obligation)]
   :assert (forall [(?a :proof-obligation) (?b :proof-obligation)]
             (=> (:contradicts ?a ?b)
                 (:supersedes ?a ?b)))
   :expected-z3-call "mk_forall_const"}

  {:name "exists-asserted-by"
   :sorts [(:proof-obligation) (:reference)]
   :assert (forall [(?o :proof-obligation)]
             (exists [(?r :reference)] (:asserted-by ?o ?r)))
   :expected-z3-call "mk_forall_const"
   :expected-nested-call "mk_exists_const"}]}
```

- [ ] **Step 5: Add the golden-comparison test**

```python
def test_extended_operators_golden_fixture():
    fixture_path = Path(__file__).parent / "golden" / "extended_operators_v0_5.edn"
    fixture = read_edn_file(fixture_path)
    for case in fixture[Keyword("cases")]:
        constraints = [_constraint_from_case(case)]
        sorts = [{Keyword("name"): s[0]} for s in case.get(Keyword("sorts"), [])]
        out = generate_axioms_source(constraints, sorts)
        assert case[Keyword("expected-z3-call")] in out, (
            f"case {case[Keyword('name')]!r}: "
            f"expected {case[Keyword('expected-z3-call')]!r} in emitted source"
        )
        if Keyword("expected-nested-call") in case:
            assert case[Keyword("expected-nested-call")] in out
```

`_constraint_from_case(case)` wraps the case's `:assert` form into a single constraint dict with the standard `:name`, `:backend`, `:track`, `:on-unsat` boilerplate.

- [ ] **Step 6: Run the drift lint**

```bash
cd /c/russellian-book-suite/skills/neurosym-forge
./.venv/Scripts/python.exe -m pytest tests/test_support_matrix.py -v
```

Expected: passes.

- [ ] **Step 7: Commit**

```bash
cd /c/russellian-book-suite
git add skills/neurosym-forge/SUPPORT_MATRIX.md docs/booklogic-dsl-reference.md \
        skills/neurosym-forge/tests/golden/extended_operators_v0_5.edn \
        skills/neurosym-forge/tests/test_codegen_axioms.py
git commit -m "docs+test: SUPPORT_MATRIX + DSL ref + golden fixture for v0.5 booleans + quantifiers (REQ-BOOKLOGIC-051..053, REQ-SMT-055)"
```

---

## Phase E — End-to-end on EpochPoET (Task 6)

#### Task 6: Smoke-test on osmotic / bermuda + verify EpochPoET unblocks

**Files:** (no edits — verification step)

- [ ] **Step 1: osmotic + bermuda compile identically pre/post**

```bash
cd /c/russellian-book-suite/verifiers/osmotic_pressure && make clean && make build && cargo test --release 2>&1 | tail -10
cd /c/russellian-book-suite/verifiers/bermuda && make clean && make build && cargo test --release 2>&1 | tail -10
```

Expected: no new errors, no behaviour change.

- [ ] **Step 2: EpochPoET constraints.edn now codegens**

The EpochPoET verifier's `constraints.edn` uses syntax that needs this branch. With the branch checked out in `russellian-book-suite`, run the codegen against the EpochPoET sources (the `constraints.edn` will need its `1/3` and `1/4` ratio literals rewritten as `(/ 1 3)` and `(/ 1 4)` — that rewrite happens in the EpochPoET workspace as a follow-up to this PR, not here):

```bash
cd /c/russellian-book-suite/skills/neurosym-forge
./.venv/Scripts/python.exe -c "
from pathlib import Path
from scripts.codegen_axioms import generate_axioms_source
from scripts._io import read_edn_file
project = Path('C:/epochpoet/verifiers/epochpoet/rules/booklogic')
constraints = read_edn_file(project / 'constraints.edn')[Keyword('forms')] \
              if 'Keyword' in dir() else __import__('scripts._edn_reader', fromlist=['Keyword']).Keyword
# (Adapt to the actual EDN reader API as needed.)
"
```

The exact invocation depends on the EDN-reader API; the goal is to feed the EpochPoET `constraints.edn` to `generate_axioms_source` and confirm it returns Rust source containing `Bool::and`, `mk_forall_const`, and `mk_exists_const`. If the ratio literals are still a problem, document that and stop — that's the follow-up.

- [ ] **Step 3: No commit** (verification step).

---

## Phase F — PR (Task 7)

#### Task 7: Push + open PR

- [ ] **Step 1: Push**

```bash
cd /c/russellian-book-suite
git push -u origin feat/booklogic-v0.5-extended-operators
```

- [ ] **Step 2: Open PR**

```bash
gh pr create \
  --title "Tier 2: BookLogic v0.5 — boolean connectives + general quantifiers (REQ-SMT-046..055)" \
  --body "$(cat <<'EOF'
## Summary

Extends the BookLogic `:assert` grammar with boolean head connectives (and / or / not / =>) and general quantifiers (forall / exists) over the sort registry. Delta on top of PR #80 (Tier 2F), which shipped comparisons and ite.

- **REQ-SMT-046..050** — boolean connectives at assert head
- **REQ-SMT-051..055** — quantifiers + bound-variable refs + sort-registry validation + backwards-compat
- **REQ-BOOKLOGIC-051..053** — SUPPORT_MATRIX rows + DSL reference §2.6 / §2.7 + golden fixture

## Test plan

- [x] 5 new tests in `test_codegen_axioms.py` for and / or / not / => / nested
- [x] 4 new tests in `test_codegen_axioms_quantifiers.py` for forall / exists / two-var implies / undeclared-sort
- [x] 2 new tests for bound-variable resolution
- [x] Golden fixture comparison test
- [x] osmotic_pressure and bermuda verifiers continue to compile and test green
- [x] Drift lint passes (SUPPORT_MATRIX ↔ codegen consistency)
- [x] EpochPoET's `constraints.edn` codegens successfully against this branch (with `1/3` rewritten as `(/ 1 3)` follow-up)

## Motivation

The EpochPoET consensus-protocol verifier needs to express:
- Joint-threshold conjecture: `(and (>= domain-count 3) (< joint-corruption 1/3) ...)`
- Universal supersession: `(forall [(?a obligation) (?b obligation)] (=> (:contradicts ?a ?b) (or (:supersedes ?a ?b) (:supersedes ?b ?a))))`
- Existential provenance: `(forall [(?o obligation)] (exists [(?r reference)] (:asserted-by ?o ?r)))`

Boolean heads and general quantifiers are the missing primitives. Tier 2F (#80) shipped the comparisons.
EOF
)"
```

- [ ] **Step 3: Wait for CI green; merge**

```bash
gh pr merge --merge --delete-branch
```

---

## Self-review

**1. Spec coverage:**

| REQ id | Implementing task |
|---|---|
| SMT-046 (`and`) | Task 1 |
| SMT-047 (`or`) | Task 1 |
| SMT-048 (`not`) | Task 2 |
| SMT-049 (`=>`) | Task 2 |
| SMT-050 (Bool-subexpression helper) | Task 1 (helper extraction) |
| SMT-051 (`forall`) | Task 4 |
| SMT-052 (`exists`) | Task 4 |
| SMT-053 (bound-variable refs) | Task 3 |
| SMT-054 (sort-registry check) | Task 4 (`test_undeclared_sort_in_binding_raises`) |
| SMT-055 (cargo check + deterministic output) | Task 6 step 1 |
| BOOKLOGIC-051 (SUPPORT_MATRIX) | Task 5 step 1 |
| BOOKLOGIC-052 (DSL ref §2.6, §2.7) | Task 5 steps 2–3 |
| BOOKLOGIC-053 (golden fixture) | Task 5 steps 4–5 |

**2. Placeholder scan:** no TBDs. The one named-but-uncertain helper (`_emit_bool_assert_block`) is probed in Task 1 Step 1 before use; the plan substitutes the actual post-#80 name if it differs.

**3. Type consistency:** `bound_vars: dict[str, str]` (Python `str` → Rust identifier `str`) used uniformly across Tasks 3, 4, 5. `_emit_bool_subexpr(node, bound_vars=None)` is the canonical signature. `_emit_expr_typed(node, z3_type, bound_vars=None)` gains the third parameter (kept optional / default `None`).

**4. Gaps surfaced inline:**

- Helper naming uncertainty (probe in Task 1 Step 1) — addressed.
- Trigger patterns deferred (Tier 5) — out of scope.
- Ratio literal parsing deferred — EpochPoET rewrites `1/3` to `(/ 1 3)` in a follow-up commit after this PR lands.
- Tier 2-4 umbrella's Phase G (bounded `(forall ?x in vec ...)`) is orthogonal and proceeds independently; no coordination required.

---

## Execution

Subagent-driven recommended. Tasks 1, 2, 3, 4 are sequentially coupled (each adds to a shared dispatch function). Tasks 5 and 6 can run in parallel after Task 4. Task 7 is the PR.
