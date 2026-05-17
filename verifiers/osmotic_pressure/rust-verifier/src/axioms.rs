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
