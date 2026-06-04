//! REQ-SMT (sort soundness): integer-valued atoms bound to a
//! Real-typed predicate must be encoded in the Real sort so they share
//! a Z3 symbol with the codegen-emitted axiom constant, and Double
//! encoding must not silently saturate on overflow.
//!
//! `land-area-km2_Bermuda` is declared Real by the generated axiom
//! (`axioms::predicate_is_real` returns true) with value 53.2. Binding
//! an integer 53 to it as an Int const would create a *distinct* Z3
//! symbol from the Real axiom const of the same name, so the
//! constraint would never interact (a silent false-sat). Bound in the
//! Real sort, 53 != 53.2 and the system is unsat.

#![cfg(feature = "smt")]

use bermuda_verifier::ir;
use bermuda_verifier::smt;

#[test]
fn integer_value_on_real_predicate_shares_real_sort() {
    // C007-land-area-km2 asserts land-area-km2_Bermuda == 53.2 (Real).
    // An atom binding the integer 53 to the same predicate/subject must
    // be encoded as Real(53), conflicting with 53.2 -> unsat. If it is
    // bound as Int (the bug), the symbols differ and Z3 returns sat.
    let edn = r#"{:atoms [
        {:id "la1" :kind :expression :predicate :land-area-km2 :subject :Bermuda :value 53}
    ]}"#;
    let formulas = ir::parse_formulas(edn).expect("parse");
    let verdict = smt::check_all(&formulas).expect("check");
    assert_eq!(
        verdict.status, "unsat",
        "integer 53 bound to Real predicate land-area-km2_Bermuda must \
         share the Real sort and conflict with the 53.2 axiom; got {verdict:?}"
    );
}

#[test]
fn double_overflow_is_rejected_not_saturated() {
    // 1e19 * 1_000_000 overflows i64 and (pre-fix) saturates to
    // i64::MAX, silently corrupting the encoded rational. The encoder
    // must instead surface an Error rather than produce a wrong const.
    let edn = r#"{:atoms [
        {:id "ov1" :kind :expression :predicate :gdp-usd-billion :subject :Bermuda :value 1.0e19}
    ]}"#;
    let formulas = ir::parse_formulas(edn).expect("parse");
    let res = smt::check_all(&formulas);
    assert!(
        res.is_err(),
        "a double whose scaled value overflows i64 must be rejected, \
         not silently saturated; got {res:?}"
    );
}
