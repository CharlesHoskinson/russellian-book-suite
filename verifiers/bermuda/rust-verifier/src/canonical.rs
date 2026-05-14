//! Bermuda canonical facts encoded as Z3 hard constraints (axioms).
//!
//! These are NOT wrapped in `assert_and_track` because they are
//! definitionally true. A contradiction with one of these is by
//! definition a defect in the ledger or prose, not in the canonical
//! facts themselves.

use z3::ast::{Ast, Bool, Int, Real, String as Z3String};
use z3::{Context, Solver};

pub fn assert_bermuda_axioms<'ctx>(ctx: &'ctx Context, solver: &Solver<'ctx>) {
    // Parish count: Bermuda has 9 traditional parishes.
    let parishes_count = Int::new_const(ctx, "parishes_count_Bermuda");
    solver.assert(&parishes_count._eq(&Int::from_i64(ctx, 9)));

    // Named islands and rocks: 181.
    let islands = Int::new_const(ctx, "named_islands_and_rocks_Bermuda");
    solver.assert(&islands._eq(&Int::from_i64(ctx, 181)));

    // Currency peg: BMD pegged at parity with USD.
    let bmd_peg = Real::new_const(ctx, "currency_pegged_at_parity_BMD_USD");
    solver.assert(&bmd_peg._eq(&Real::from_real(ctx, 1, 1)));

    // Airport location: L. F. Wade is on St. David's Island.
    let lfw_island = Z3String::new_const(ctx, "airport_on_island_L_F_Wade");
    solver.assert(&lfw_island._eq(&Z3String::from_str(ctx, "St_Davids_Island")
        .expect("valid utf-8")));

    // Cedar binomial.
    let cedar = Z3String::new_const(ctx, "binomial_Bermuda_cedar");
    solver.assert(&cedar._eq(&Z3String::from_str(ctx, "Juniperus bermudiana")
        .expect("valid utf-8")));
}

/// Bind a prose-extracted or ledger-extracted atom to its Z3 variable.
///
/// For an atom `{:predicate :parishes-count :subject :Bermuda :value 9}`,
/// emits a tracked assertion `parishes_count_Bermuda = 9`. The tracker
/// uses the atom's `:id` so the unsat core points back to it.
pub fn assert_tracked_atom<'ctx>(
    ctx: &'ctx Context,
    solver: &Solver<'ctx>,
    predicate: &str,
    subject: &str,
    value: &serde_json::Value,
    atom_id: &str,
) {
    let var_name = format!("{}_{}", predicate.trim_start_matches(':'),
                           subject.trim_start_matches(':'));
    let tracker = Bool::new_const(ctx, atom_id);

    let assertion: Bool = match value {
        serde_json::Value::Number(n) if n.is_i64() => {
            let z3_var = Int::new_const(ctx, &var_name);
            z3_var._eq(&Int::from_i64(ctx, n.as_i64().unwrap()))
        }
        serde_json::Value::String(s) => {
            let z3_var = Z3String::new_const(ctx, &var_name);
            z3_var._eq(&Z3String::from_str(ctx, s).unwrap())
        }
        serde_json::Value::Bool(b) => {
            let z3_var = Bool::new_const(ctx, &var_name);
            z3_var._eq(&Bool::from_bool(ctx, *b))
        }
        _ => {
            // Unknown value kind — skip silently (caller logs)
            return;
        }
    };
    solver.assert_and_track(&assertion, &tracker);
}
