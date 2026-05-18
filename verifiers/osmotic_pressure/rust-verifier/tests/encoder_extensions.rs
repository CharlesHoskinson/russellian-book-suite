//! REQ-SMT-040..043: encoder-extension integration smoke tests.
//!
//! The Python `codegen_axioms` lowering for new operators emits these
//! Z3 method calls verbatim:
//!
//!   <  -> Real::lt    /  -> Real::div
//!   <= -> Real::le    ite -> Bool::ite
//!   >  -> Real::gt
//!   >= -> Real::ge
//!
//! This test pins the z3-0.20 API contract those emitters depend on by
//! constructing the same shapes the codegen would output and asking Z3
//! whether the result matches our hand-derived expectation. If the
//! crate ever renames or re-signatures any of these methods, this
//! integration test fails BEFORE we ship a broken `axioms.rs`.
#![cfg(feature = "smt")]

use z3::{
    SatResult, Solver,
    ast::{Bool, Real},
};

#[test]
fn lt_le_gt_ge_round_trip_through_z3() {
    // x : Real, constrain 1 <= x < 2 and x >= 1.5; expect SAT.
    let solver = Solver::new();
    let x = Real::new_const("x");
    let one = Real::from_rational(1, 1);
    let one_half = Real::from_rational(3, 2);
    let two = Real::from_rational(2, 1);

    solver.assert(&one.le(&x));      // 1 <= x
    solver.assert(&x.lt(&two));      // x < 2
    solver.assert(&x.ge(&one_half)); // x >= 1.5
    assert_eq!(solver.check(), SatResult::Sat);

    // Add a contradiction with `>` and the result must flip to UNSAT.
    solver.assert(&one.gt(&x)); // 1 > x  conflicts with x >= 1.5
    assert_eq!(solver.check(), SatResult::Unsat);
}

#[test]
fn division_subexpression_compiles_and_solves() {
    // y / 2 == 3  =>  y = 6
    let solver = Solver::new();
    let y = Real::new_const("y");
    let two = Real::from_rational(2, 1);
    let three = Real::from_rational(3, 1);
    let six = Real::from_rational(6, 1);

    let quotient = y.div(&two);
    solver.assert(&quotient.eq(&three));
    solver.assert(&y.eq(&six));
    assert_eq!(solver.check(), SatResult::Sat);
}

#[test]
fn ite_branches_on_real_predicate() {
    // ite(x < 0, -1, 1) with x = 5 should pick the else branch; with
    // x = -5 it should pick the then branch.
    let solver = Solver::new();
    let x = Real::new_const("x_ite");
    let zero = Real::from_rational(0, 1);
    let neg_one = Real::from_rational(-1, 1);
    let one = Real::from_rational(1, 1);

    let cond: Bool = x.lt(&zero);
    let selected: Real = cond.ite(&neg_one, &one);

    solver.push();
    solver.assert(&x.eq(&Real::from_rational(5, 1)));
    solver.assert(&selected.eq(&one));
    assert_eq!(
        solver.check(),
        SatResult::Sat,
        "x=5 should pick the else branch (1)",
    );
    solver.pop(1);

    solver.assert(&x.eq(&Real::from_rational(-5, 1)));
    solver.assert(&selected.eq(&one));
    assert_eq!(
        solver.check(),
        SatResult::Unsat,
        "x=-5 picks the then branch (-1), so selected==1 must be UNSAT",
    );
}
