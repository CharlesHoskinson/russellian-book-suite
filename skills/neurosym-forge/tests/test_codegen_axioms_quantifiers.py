"""REQ-SMT-051, 052, 054 — quantifier support in :assert heads."""
import pytest
from scripts.codegen_axioms import generate_axioms_source, CodegenError
from scripts._edn_reader import Keyword, Symbol


def _quant(quant_head, bindings, body, sorts=None):
    constraint = {
        Keyword("id"): "CQ001",
        Keyword("backend"): Keyword("z3"),
        Keyword("assert"): (Symbol(quant_head), bindings, body),
        Keyword("track"): Keyword("CQ001"),
        Keyword("on-unsat"): {Keyword("defect"): Keyword("D13"),
                              Keyword("severity"): Keyword("critical"),
                              Keyword("message"): "quantifier check failed"},
    }
    return [constraint], (sorts or [])


def test_forall_single_var():
    constraints, sorts = _quant(
        "forall",
        [(Symbol("?o"), Keyword("proof-obligation"))],
        (Symbol("="), Symbol("?o"), Keyword("special")),
        sorts=[{Keyword("name"): Keyword("proof-obligation")}],
    )
    out = generate_axioms_source(constraints, sorts=sorts)
    assert "mk_forall_const" in out


def test_exists_single_var():
    constraints, sorts = _quant(
        "exists",
        [(Symbol("?r"), Keyword("reference"))],
        (Symbol("="), Symbol("?r"), Keyword("v2-spec")),
        sorts=[{Keyword("name"): Keyword("reference")}],
    )
    out = generate_axioms_source(constraints, sorts=sorts)
    assert "mk_exists_const" in out


def test_forall_two_vars_with_implication():
    """The EpochPoET C003 pattern."""
    body = (Symbol("=>"),
            (Keyword("contradicts"), Symbol("?a"), Symbol("?b")),
            (Keyword("supersedes"), Symbol("?a"), Symbol("?b")))
    constraints, sorts = _quant(
        "forall",
        [(Symbol("?a"), Keyword("proof-obligation")),
         (Symbol("?b"), Keyword("proof-obligation"))],
        body,
        sorts=[{Keyword("name"): Keyword("proof-obligation")}],
    )
    out = generate_axioms_source(constraints, sorts=sorts)
    assert "mk_forall_const" in out
    assert ".implies" in out


def test_undeclared_sort_in_binding_raises():
    constraints, sorts = _quant(
        "forall",
        [(Symbol("?x"), Keyword("nonexistent-sort"))],
        (Symbol("="), Symbol("?x"), 5),
        sorts=[],
    )
    with pytest.raises(CodegenError, match=r"sort 'nonexistent-sort' not declared"):
        generate_axioms_source(constraints, sorts=sorts)


def test_nested_quantifier_exists_inside_forall():
    """The EpochPoET C004 pattern: forall over obligations, exists over references."""
    body = (Symbol("exists"),
            [(Symbol("?r"), Keyword("reference"))],
            (Symbol("="), Symbol("?r"), Symbol("?o")))
    constraints, sorts = _quant(
        "forall",
        [(Symbol("?o"), Keyword("proof-obligation"))],
        body,
        sorts=[{Keyword("name"): Keyword("proof-obligation")},
               {Keyword("name"): Keyword("reference")}],
    )
    out = generate_axioms_source(constraints, sorts=sorts)
    assert "mk_forall_const" in out
    assert "mk_exists_const" in out
