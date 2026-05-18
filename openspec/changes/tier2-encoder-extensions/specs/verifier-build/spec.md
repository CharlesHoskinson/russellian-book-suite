# Capability delta: verifier-build — change: tier2-encoder-extensions

## ADD

### REQ-SMT-040 — Ubiquitous

The codegen `_emit_z3_block` in `skills/neurosym-forge/scripts/codegen_axioms.py`
SHALL translate `(< a b)` to `Real::lt(&a, &b)` when either operand is
Real-typed and to `Int::lt(&a, &b)` otherwise; `(<= a b)` translates
analogously to `Real::le` / `Int::le`.

**Rationale:** Strict inequalities are the most common assert head for
range constraints. Lifting them to Z3 unlocks the temperature-window,
pH-band, and concentration-floor patterns the framework's third
verifier already needs.
**Tested by:** `skills/neurosym-forge/scripts/tests/test_codegen_axioms_operators.py::test_lt_le_emit_real_lt_le` (added in E2.1.1)

### REQ-SMT-041 — Ubiquitous

The codegen SHALL translate `(> a b)` to `Real::gt(&a, &b)` / `Int::gt`
and `(>= a b)` to `Real::ge(&a, &b)` / `Int::ge`, with the Real-vs-Int
choice made by the same `_subtree_has_float` rule used by REQ-SMT-040.

**Rationale:** `>` and `>=` are the symmetric pair to `<` / `<=` and
must arrive together — splitting them across changes would leave a
half-supported range-constraint surface.
**Tested by:** `test_codegen_axioms_operators.py::test_gt_ge_emit_real_gt_ge` (added in E2.1.3)

### REQ-SMT-042 — Ubiquitous

The codegen SHALL translate `(/ a b)` to `Real::div(&a, &b)` when
either operand is Real-typed and to `Int::div(&a, &b)` otherwise, with
the Real-vs-Int choice made by `_subtree_has_float`.

**Rationale:** Many physical-quantity constraints need a ratio
(`(/ :concentration-mol-l :density-g-l)`); arithmetic-only forms
(`*`, `+`, `-`) cannot express those without auxiliary predicates.
`Int::div` matches the SMT-LIB `div` semantics shipped by z3-rs 0.20.
**Tested by:** `test_codegen_axioms_operators.py::test_div_emits_real_div_for_real_operands` (added in E2.2.1)

### REQ-SMT-043 — Ubiquitous

The codegen SHALL translate `(ite cond then-expr else-expr)` to
`<Branch>::ite(&cond, &then, &else)` where `<Branch>` is the Z3 sort of
`then-expr` (`Real`, `Int`, `Bool`, or `Z3String`); `cond` SHALL be
required to be of `Bool` sort.

**Rationale:** Conditional branches are the lone three-arity case in
the SMT-LIB op set we want to support. They enable tax-bracket,
phase-transition, and piecewise-linear constraints that today require
inflating the constraint set with `or`-of-conjunction encodings.
**Tested by:** `test_codegen_axioms_operators.py::test_ite_emits_typed_branch` (added in E2.2.3)

### REQ-SMT-044 — Unwanted behaviour

IF `_emit_z3_block` encounters an assert head that is not in the
authoritative `_SUPPORTED_ASSERT_HEADS` tuple (the canonical list of
heads this codegen understands), THEN the codegen SHALL raise a
`CodegenError` whose message:
1. quotes the unknown head,
2. enumerates `_SUPPORTED_ASSERT_HEADS` in full, and
3. links to `docs/booklogic-dsl-reference.md` § 2.5.

**Rationale:** Authors must be able to discover the supported operator
surface through the failure message itself, without grepping the
codegen source.
**Tested by:** `test_codegen_axioms_operators.py::test_unknown_head_error_enumerates_supported_set` (added in E2.3.1)

### REQ-SMT-045 — Ubiquitous

`docs/booklogic-dsl-reference.md` § 2.5 (`defconstraint :assert`)
SHALL enumerate the full supported assert-head set:
`=`, `approx=`, `~=`, `+`, `-`, `*`, `/`, `<`, `<=`, `>`, `>=`,
`and`, `or`, `ite` — with at least one worked example for each of the
six new heads (`<`, `<=`, `>`, `>=`, `/`, `ite`) and a cross-link to
`_SUPPORTED_ASSERT_HEADS` for the authoritative source.

**Rationale:** The reference doc is the author-facing surface; without
the enumeration the new operators are not discoverable.
**Tested by:** `skills/neurosym-forge/tests/test_dsl_reference_drift.py::test_section_2_5_lists_supported_assert_heads` (added in E2.5.1)
