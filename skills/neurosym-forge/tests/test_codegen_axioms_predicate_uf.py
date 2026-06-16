"""REQ-SMT-056..061 — predicate-as-uninterpreted-function semantics (v0.6).

v0.5 wired quantifiers structurally but lowered a Keyword-headed predicate inside
a quantifier body to an opaque `Bool::new_const`, so the bound variables never
entered the predicate and the quantifier constrained nothing. v0.6 declares
Bool-returning predicates with non-empty :arg-sorts as Z3 uninterpreted functions
(`FuncDecl`) and emits `<pred>_fn.apply(&[...])`, so quantified properties bind.
"""
import pytest

pytestmark = pytest.mark.windows_canary

from scripts.codegen_axioms import generate_axioms_source, CodegenError
from scripts._edn_reader import Keyword, Symbol


def _kw(name):
    return Keyword(name)


def _bool_pred_schema():
    """`:contradicts`/`:supersedes` over two proof-obligations, returning Bool."""
    sig = {_kw("arg-sorts"): [_kw("proof-obligation"), _kw("proof-obligation")],
           _kw("return"): _kw("bool")}
    return {_kw("contradicts"): sig, _kw("supersedes"): sig}


def _forall_constraint(body):
    return [{
        _kw("id"): "C003",
        _kw("backend"): _kw("z3"),
        _kw("assert"): (
            Symbol("forall"),
            [(Symbol("?a"), _kw("proof-obligation")),
             (Symbol("?b"), _kw("proof-obligation"))],
            body,
        ),
        _kw("track"): _kw("C003"),
        _kw("on-unsat"): {_kw("defect"): _kw("D13"),
                          _kw("severity"): _kw("critical"),
                          _kw("message"): "supersession check failed"},
    }]


_SORTS = [{_kw("name"): _kw("proof-obligation")}]


def test_predicate_in_forall_emits_apply():
    """REQ-SMT-058: a schema-declared Bool predicate inside a quantifier body
    emits `<pred>_fn.apply(...)`, not an opaque `Bool::new_const`."""
    body = (Symbol("=>"),
            (_kw("contradicts"), Symbol("?a"), Symbol("?b")),
            (_kw("supersedes"), Symbol("?a"), Symbol("?b")))
    out = generate_axioms_source(_forall_constraint(body),
                                 schema=_bool_pred_schema(), sorts=_SORTS)
    assert "contradicts_fn.apply(" in out
    assert "supersedes_fn.apply(" in out


def test_no_opaque_bool_for_registered_predicate():
    """REQ-SMT-058: the opaque-Bool fallback must NOT fire for a registered
    predicate (this is the v0.5 soundness bug)."""
    body = (Symbol("=>"),
            (_kw("contradicts"), Symbol("?a"), Symbol("?b")),
            (_kw("supersedes"), Symbol("?a"), Symbol("?b")))
    out = generate_axioms_source(_forall_constraint(body),
                                 schema=_bool_pred_schema(), sorts=_SORTS)
    assert 'Bool::new_const("contradicts_a_b")' not in out
    assert 'Bool::new_const("supersedes_a_b")' not in out


def test_funcdecl_declared_once_per_block():
    """REQ-SMT-057: a predicate referenced twice in one body declares its
    FuncDecl exactly once."""
    body = (Symbol("=>"),
            (_kw("contradicts"), Symbol("?a"), Symbol("?b")),
            (_kw("contradicts"), Symbol("?b"), Symbol("?a")))
    out = generate_axioms_source(_forall_constraint(body),
                                 schema=_bool_pred_schema(), sorts=_SORTS)
    assert out.count('FuncDecl::new("contradicts"') == 1


def test_funcdecl_range_is_bool():
    """REQ-SMT-057: the emitted FuncDecl ranges over Bool with two arg sorts."""
    body = (_kw("contradicts"), Symbol("?a"), Symbol("?b"))
    out = generate_axioms_source(_forall_constraint(body),
                                 schema=_bool_pred_schema(), sorts=_SORTS)
    assert ("FuncDecl::new(\"contradicts\", "
            "&[&proof_obligation_sort, &proof_obligation_sort], "
            "&Sort::bool())") in out


def test_ground_arg_resolves_to_sorted_const():
    """REQ-SMT-058: a non-?var argument becomes a sort-typed Dynamic const."""
    body = (_kw("contradicts"), Symbol("?a"), _kw("genesis"))
    out = generate_axioms_source(_forall_constraint(body),
                                 schema=_bool_pred_schema(), sorts=_SORTS)
    assert 'Dynamic::new_const("genesis", &proof_obligation_sort)' in out


def test_arity_mismatch_raises():
    """REQ-SMT-059: too many arguments for a 2-arg predicate raises."""
    body = (_kw("contradicts"), Symbol("?a"), Symbol("?b"), Symbol("?a"))
    with pytest.raises(CodegenError, match=r"contradicts.*arity mismatch"):
        generate_axioms_source(_forall_constraint(body),
                               schema=_bool_pred_schema(), sorts=_SORTS)


def test_unbound_variable_raises():
    """REQ-SMT-058: a predicate argument not bound by any quantifier raises."""
    body = (_kw("contradicts"), Symbol("?a"), Symbol("?z"))
    with pytest.raises(CodegenError, match=r"unbound variable '\?z'"):
        generate_axioms_source(_forall_constraint(body),
                               schema=_bool_pred_schema(), sorts=_SORTS)


def test_nil_arity_predicate_keeps_opaque_bool():
    """REQ-SMT-061: a predicate absent from the registry (no arg-sorts) keeps
    the legacy opaque-Bool emission — the path the shipped verifiers use."""
    body = (Symbol("=>"),
            (_kw("contradicts"), Symbol("?a"), Symbol("?b")),
            (_kw("flagged"), Symbol("?a")))
    schema = dict(_bool_pred_schema())
    schema[_kw("flagged")] = {_kw("arg-sorts"): None, _kw("return"): None}
    out = generate_axioms_source(_forall_constraint(body), schema=schema, sorts=_SORTS)
    assert "contradicts_fn.apply(" in out          # registered -> UF
    assert 'Bool::new_const("flagged_a")' in out    # nil-arity -> opaque


def test_soundness_shape_exposes_opaque_collision():
    """REQ-SMT-060 (unit): `(forall [?a] (:p ?a))` and `(exists [?b] (not (:p ?b)))`
    must both apply the SAME FuncDecl to their own bound const. Under the opaque
    encoder these were named `p_a` vs `p_b` — distinct Bools — so z3 saw no
    contradiction (the soundness bug). Under the UF encoder both are `p_fn.apply`,
    so z3 can refute the pair.
    """
    schema = {_kw("p"): {_kw("arg-sorts"): [_kw("obligation")], _kw("return"): _kw("bool")}}
    sorts = [{_kw("name"): _kw("obligation")}]
    universal = {
        _kw("id"): "U1", _kw("backend"): _kw("z3"),
        _kw("assert"): (Symbol("forall"), [(Symbol("?a"), _kw("obligation"))],
                        (_kw("p"), Symbol("?a"))),
        _kw("track"): _kw("U1"),
        _kw("on-unsat"): {_kw("defect"): _kw("D13"), _kw("severity"): _kw("critical"),
                          _kw("message"): "u"},
    }
    witness = {
        _kw("id"): "W1", _kw("backend"): _kw("z3"),
        _kw("assert"): (Symbol("exists"), [(Symbol("?b"), _kw("obligation"))],
                        (Symbol("not"), (_kw("p"), Symbol("?b")))),
        _kw("track"): _kw("W1"),
        _kw("on-unsat"): {_kw("defect"): _kw("D13"), _kw("severity"): _kw("critical"),
                          _kw("message"): "w"},
    }
    out = generate_axioms_source([universal, witness], schema=schema, sorts=sorts)
    assert out.count('FuncDecl::new("p"') == 2       # one per block, same Z3 decl
    assert "p_fn.apply(&[&a_const])" in out
    assert "p_fn.apply(&[&b_const])" in out
    assert 'Bool::new_const("p_a")' not in out
    assert 'Bool::new_const("p_b")' not in out
