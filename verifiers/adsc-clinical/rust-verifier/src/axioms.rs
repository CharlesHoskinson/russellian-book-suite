// PLACEHOLDER: this no-op axioms hook ships with the scaffold.
// `npm run codegen-axioms` overwrites this file with generated source
// when rules/booklogic/constraints.edn declares defconstraint forms.
// DO NOT edit by hand; edit constraints.edn instead.

#[cfg(feature = "smt")]
use z3::Solver;

#[cfg(feature = "smt")]
pub fn assert_axioms(_solver: &Solver) {
    // No-op default; replaced by codegen_axioms.run().
}

#[cfg(not(feature = "smt"))]
pub fn assert_axioms() {
    // No-op default.
}

/// True if the named predicate-subject symbol should be bound as
/// `z3::ast::Real` rather than `z3::ast::Int`. The placeholder scaffold
/// declares no Real predicates; `codegen_axioms` overwrites this when
/// constraints.edn promotes a subtree to Real. smt.rs queries it to keep
/// value-bindings in the same Z3 sort as the axioms reference.
#[allow(dead_code)]
pub fn predicate_is_real(_name: &str) -> bool {
    false
}

/// True if the named predicate-subject symbol carries a multi-valued
/// `[:vector <T>]` return-sort. smt.rs queries this to fail loudly when
/// an atom binds a scalar to a vector-typed predicate (REQ-DSL-054). The
/// placeholder scaffold declares no vector predicates; `codegen_axioms`
/// overwrites this from booklogic-schema.edn.
pub fn predicate_is_vector(_name: &str) -> bool {
    false
}
