//! SMT verification entry point.
//!
//! Walk the atoms parsed by `ir::parse_formulas`. For each atom that
//! carries a typed `predicate`+`subject`+`value`, assert the equality
//! to a Z3 variable named `{predicate}_{subject}` with `assert_and_track`
//! using the atom's `id`. Context/opaque atoms are skipped.
//!
//! Before the per-atom assertions, call `crate::axioms::assert_axioms`
//! which projects override to install hard constraints (the v0.3 hook
//! contract).
//!
//! `solver.check()` returns Sat / Unsat / Unknown. On Unsat we read
//! the unsat core (a vector of tracker booleans) and translate the
//! tracker names back to ClaimIds.

use crate::ir::{Atom, ClaimId, Error, Verdict};

#[cfg(feature = "smt")]
use std::str::FromStr as _;
#[cfg(feature = "smt")]
use z3::{
    SatResult, Solver,
    ast::{Bool, Int, Real, String as Z3String},
};

#[cfg(feature = "smt")]
pub fn check_all(formulas: &[(ClaimId, Atom)]) -> Result<Verdict, Error> {
    use edn_rs::Edn;

    let solver = Solver::new();

    // Project-specific axioms (default no-op).
    crate::axioms::assert_axioms(&solver);

    let mut tracker_ids: Vec<ClaimId> = Vec::with_capacity(formulas.len());

    for (id, atom) in formulas {
        // Skip context / opaque / non-expression atoms.
        // Accept either Keyword or Str during migration; Keyword is canonical.
        let kind = match atom.get(":kind") {
            Some(Edn::Key(k)) => k.clone(),
            Some(Edn::Str(s)) => s.clone(),
            _ => "".to_string(),
        };
        if kind != ":expression" {
            continue;
        }
        // REQ-EDN-049: :predicate and :subject MUST be Keywords.
        // ingest_ledger now emits Keywords; the legacy Str fallback is
        // removed so any drift surfaces as a hard parse failure.
        let predicate = match atom.get(":predicate") {
            Some(Edn::Key(k)) => k.clone(),
            _ => continue,
        };
        let subject = match atom.get(":subject") {
            Some(Edn::Key(k)) => k.clone(),
            _ => continue,
        };
        let var_name = crate::canonical::canonical_var_name(&predicate, &subject);
        let tracker = Bool::new_const(id.as_str());

        let value = match atom.get(":value") {
            Some(v) => v,
            None => continue,
        };

        // For numeric predicates the codegen tells us which sort the axioms
        // reference. Without this query, an integer claim value (e.g. i=2)
        // would bind `Int::new_const("vant-hoff-i_s")` while the axiom
        // references `Real::new_const("vant-hoff-i_s")` — same name,
        // different Z3 sorts = two distinct symbols, leaving the axiom
        // predicate unbound and the solver free to pick arbitrary values
        // (the doctored-fixture :sat regression).
        // Use Real::from_rational_str (not from_rational) because z3-0.20's
        // from_rational(i64, i64) truncates the numerator to c_int (i32) before
        // calling Z3_mk_real. Numerator overflow corrupts π=780202.5 into a
        // negative value, leaving the axiom satisfiable for any input (the
        // sprint-5 doctored-fixture :sat regression).
        let want_real = crate::axioms::predicate_is_real(var_name.as_str());
        let assertion: Bool = match value {
            Edn::Int(n) => {
                if want_real {
                    let z3_var = Real::new_const(var_name.as_str());
                    let lit = Real::from_rational_str(&n.to_string(), "1")
                        .ok_or_else(|| Error::Smt(format!("from_rational_str({n}, 1) failed")))?;
                    z3_var.eq(&lit)
                } else {
                    let z3_var = Int::new_const(var_name.as_str());
                    z3_var.eq(&Int::from_i64(*n))
                }
            }
            Edn::Double(_) => {
                let v = value.to_float().unwrap_or(0.0);
                let z3_var = Real::new_const(var_name.as_str());
                // Scale by 1e6 to capture 6 decimal places; numerator can now
                // exceed i32 (covered by from_rational_str's BigInt parsing).
                let scale: i64 = 1_000_000;
                let numerator = (v * scale as f64).round() as i64;
                let lit = Real::from_rational_str(&numerator.to_string(), &scale.to_string())
                    .ok_or_else(|| {
                        Error::Smt(format!("from_rational_str({numerator}, {scale}) failed"))
                    })?;
                z3_var.eq(&lit)
            }
            Edn::Str(s) => {
                let z3_var = Z3String::new_const(var_name.as_str());
                let lit = Z3String::from_str(s)
                    .map_err(|_| Error::Smt(format!("invalid string literal: {s:?}")))?;
                z3_var.eq(&lit)
            }
            Edn::Bool(b) => {
                let z3_var = Bool::new_const(var_name.as_str());
                z3_var.eq(&Bool::from_bool(*b))
            }
            _ => continue,
        };
        solver.assert_and_track(&assertion, &tracker);
        tracker_ids.push(id.clone());
    }

    // Diagnostic: print the full solver state to stderr so failing fixtures
    // can be debugged. Gated on env var so production runs stay quiet.
    if std::env::var("VERIFIER_DEBUG_SMT").is_ok() {
        eprintln!("=== Z3 solver state ===\n{}", solver);
        eprintln!("=== /Z3 solver state ===");
    }

    match solver.check() {
        SatResult::Sat => Ok(Verdict {
            status: "sat".into(),
            core: Vec::new(),
            ..Default::default()
        }),
        SatResult::Unsat => {
            let core_bools = solver.get_unsat_core();
            let core_ids: Vec<ClaimId> = core_bools
                .iter()
                .map(|b| format!("{b}"))
                .map(|s| s.trim_matches('|').to_string())
                .filter(|s| tracker_ids.iter().any(|tid| tid == s))
                .collect();
            Ok(Verdict {
                status: "unsat".into(),
                core: core_ids,
                explanation: "Z3 reports unsat; offending atoms in core".into(),
                ..Default::default()
            })
        }
        SatResult::Unknown => Ok(Verdict {
            status: "unknown".into(),
            explanation: solver.get_reason_unknown().unwrap_or_default(),
            ..Default::default()
        }),
    }
}

#[cfg(not(feature = "smt"))]
pub fn check_all(_formulas: &[(ClaimId, Atom)]) -> Result<Verdict, Error> {
    Err(Error::Smt("compiled without `smt` feature".into()))
}

#[cfg(all(test, feature = "smt"))]
mod tests {
    //! Inline regression for #49 — doctored osmotic ledger must produce :unsat.
    //!
    //! Bypasses ingest_ledger.py. Builds atom EDN strings directly and parses
    //! them through `ir::parse_formulas`, so the test exercises the same
    //! type shape production code receives. If this test says `:sat`, the
    //! bug is in the SMT formulation (axioms.rs + check_all binding
    //! logic). If `:unsat`, the bug is upstream in the ingest pipeline.
    use super::*;
    use crate::ir::parse_formulas;

    fn ledger_edn(values: &[(&str, &str, &str, f64)]) -> String {
        // Each tuple is (claim_id, predicate, subject, value).
        // Always print a decimal point so EDN parses values as Double, not
        // Int (Rust's Display drops trailing zero on whole numbers).
        let mut atoms = String::new();
        for (id, pred, subj, val) in values {
            let val_str = if val.fract() == 0.0 {
                format!("{}.0", val)
            } else {
                format!("{}", val)
            };
            // REQ-EDN-049: emit :predicate and :subject as keywords
            // (matching what ingest_ledger now produces), not strings.
            atoms.push_str(&format!(
                "{{:id \"{id}\" :kind :expression :predicate :{pred} \
                 :subject :{subj} :value {val_str}}} ",
            ));
        }
        format!("{{:version 1 :atoms [{}]}}", atoms)
    }

    #[test]
    fn doctored_van_t_hoff_is_unsat() {
        let edn = ledger_edn(&[
            ("osm-doc-001", "vant-hoff-i", "s", 1.0),
            ("osm-doc-002", "molarity", "s", 0.154),
            ("osm-doc-003", "temperature-k", "s", 298.15),
            ("osm-doc-004", "osmotic-pressure-pa", "s", 780202.5),
        ]);
        let formulas = parse_formulas(&edn).expect("parse_formulas");
        let verdict = check_all(&formulas).expect("check_all");
        assert_eq!(
            verdict.status, "unsat",
            "doctored fixture (i=1, π=780202.5) violates van 't Hoff but \
             solver returned {}",
            verdict.status,
        );
    }

    #[test]
    fn clean_van_t_hoff_is_sat() {
        // π = 2 · 0.154 · 8.314 · 298.15 ≈ 763.27 Pa.
        let edn = ledger_edn(&[
            ("osm-clean-001", "vant-hoff-i", "s", 2.0),
            ("osm-clean-002", "molarity", "s", 0.154),
            ("osm-clean-003", "temperature-k", "s", 298.15),
            ("osm-clean-004", "osmotic-pressure-pa", "s", 763.27),
        ]);
        let formulas = parse_formulas(&edn).expect("parse_formulas");
        let verdict = check_all(&formulas).expect("check_all");
        assert_eq!(
            verdict.status, "sat",
            "clean fixture should be :sat, got {}",
            verdict.status,
        );
    }
}
