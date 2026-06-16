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

use crate::ir::{Atom, Claim, ClaimId, Error, Verdict};

#[cfg(feature = "smt")]
use std::str::FromStr as _;
#[cfg(feature = "smt")]
use z3::{
    Params, SatResult, Solver,
    ast::{Bool, Int, Real, String as Z3String},
};

#[cfg(feature = "smt")]
pub fn check_all(formulas: &[(ClaimId, Atom)]) -> Result<Verdict, Error> {
    use edn_rs::Edn;

    let solver = Solver::new();

    // Z3 solver timeout. Default 30,000 ms; override via
    // VERIFIER_SOLVER_TIMEOUT_MS env var. Without a timeout an
    // undecidable or hard QF_NRA instance hangs the verifier process
    // indefinitely (REQ-VERIFIER-BUILD-040, REQ-VERIFIER-BUILD-041).
    let timeout_ms: u32 = std::env::var("VERIFIER_SOLVER_TIMEOUT_MS")
        .ok()
        .and_then(|s| s.parse().ok())
        .unwrap_or(30_000);
    let mut params = Params::new();
    params.set_u32("timeout", timeout_ms);
    solver.set_params(&params);

    // Project-specific axioms (default no-op).
    crate::axioms::assert_axioms(&solver);

    let mut tracker_ids: Vec<ClaimId> = Vec::with_capacity(formulas.len());
    // H-03: the claims actually asserted into the solver — i.e. the
    // `:expression` atoms with a bindable predicate/subject/value. This
    // is the set the kg layer ingests (lib.rs feeds `verdict.verified`
    // into `kg::ingest_and_summarize`). Atoms have no `:source` key in
    // the IR (only :id/:kind/:predicate/:subject/:value), so `source` is
    // empty; only the claim id and count matter to the kg relation.
    let mut verified: Vec<Claim> = Vec::with_capacity(formulas.len());

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
        let predicate = match atom.get(":predicate") {
            Some(Edn::Key(k)) => k.clone(),
            Some(Edn::Str(s)) => s.clone(),
            _ => continue,
        };
        let subject = match atom.get(":subject") {
            Some(Edn::Key(k)) => k.clone(),
            Some(Edn::Str(s)) => s.clone(),
            _ => continue,
        };
        let var_name = crate::var_name::canonical_var_name(&predicate, &subject);
        let tracker = Bool::new_const(id.as_str());

        let value = match atom.get(":value") {
            Some(v) => v,
            None => continue,
        };

        // Bind the value in the same Z3 sort the codegen-emitted axiom
        // uses for this symbol. A predicate the codegen promoted to Real
        // (because a float literal appears in its constraint subtree)
        // must have its integer-valued atoms bound as Real too; otherwise
        // the Int const and the Real axiom const are distinct Z3 symbols
        // and the binding never constrains the axiom (a silent false-sat).
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
            // edn-rs renders bare non-negative integers as `Edn::UInt`
            // rather than `Edn::Int`. Bind them identically so those
            // values are asserted to Z3 instead of silently dropped.
            Edn::UInt(n) => {
                let n_i64: i64 = (*n)
                    .try_into()
                    .map_err(|_| Error::Smt(format!("value too large to bind as Int: {n}")))?;
                if want_real {
                    let z3_var = Real::new_const(var_name.as_str());
                    let lit =
                        Real::from_rational_str(&n_i64.to_string(), "1").ok_or_else(|| {
                            Error::Smt(format!("from_rational_str({n_i64}, 1) failed"))
                        })?;
                    z3_var.eq(&lit)
                } else {
                    let z3_var = Int::new_const(var_name.as_str());
                    z3_var.eq(&Int::from_i64(n_i64))
                }
            }
            // Encode the double as the exact rational `round(v * 1e6) / 1e6`.
            // The fixed 1e6 scale is a known soundness limitation: values
            // with more than ~6 fractional digits are rounded. Overflow of
            // the scaled numerator past i64 is rejected rather than letting
            // an `as i64` cast saturate to i64::MAX and silently corrupt
            // the encoded value.
            Edn::Double(_) => {
                let v = value.to_float().unwrap_or(0.0);
                let z3_var = Real::new_const(var_name.as_str());
                let scale: i64 = 1_000_000;
                let scaled = (v * scale as f64).round();
                if !scaled.is_finite() || scaled > i64::MAX as f64 || scaled < i64::MIN as f64 {
                    return Err(Error::Smt(format!(
                        "double value {v} out of range for the fixed 1e6-scale \
                         rational encoding (scaled numerator overflows i64)"
                    )));
                }
                let numerator = scaled as i64;
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
        verified.push(Claim {
            id: id.clone(),
            source: String::new(),
        });
    }

    let mut verdict = match solver.check() {
        SatResult::Sat => Verdict {
            status: "sat".into(),
            core: Vec::new(),
            ..Default::default()
        },
        SatResult::Unsat => {
            let core_bools = solver.get_unsat_core();
            let core_ids: Vec<ClaimId> = core_bools
                .iter()
                .map(|b| format!("{b}"))
                .map(|s| s.trim_matches('|').to_string())
                .filter(|s| tracker_ids.iter().any(|tid| tid == s))
                .collect();
            Verdict {
                status: "unsat".into(),
                core: core_ids,
                explanation: "Z3 reports unsat; offending atoms in core".into(),
                ..Default::default()
            }
        }
        SatResult::Unknown => Verdict {
            status: "unknown".into(),
            explanation: solver.get_reason_unknown().unwrap_or_default(),
            ..Default::default()
        },
    };
    // H-03: carry the asserted claims out so lib.rs's kg block ingests
    // real claims instead of an empty slice (claim_count was always 0).
    verdict.verified = verified;
    Ok(verdict)
}

#[cfg(not(feature = "smt"))]
pub fn check_all(_formulas: &[(ClaimId, Atom)]) -> Result<Verdict, Error> {
    Err(Error::Smt("compiled without `smt` feature".into()))
}

#[cfg(all(test, feature = "smt"))]
mod tests {
    use crate::ir::parse_formulas;

    // A predicate the codegen declared Real (`vaccination-coverage_p`)
    // must bind an integer-valued atom in the Real sort so it shares a
    // Z3 symbol with the Real axiom/double bindings. Here the same
    // predicate is pinned to integer 5 and to double 6.0; if the integer
    // were bound as an Int const it would be a *distinct* symbol from the
    // Real 6.0 const and Z3 would report sat. Sharing the Real sort makes
    // 5 != 6.0 unsat.
    #[test]
    fn integer_on_real_predicate_shares_real_sort() {
        let edn = r#"{:atoms [
            {:id "r1" :kind :expression :predicate :vaccination-coverage :subject :p :value 5}
            {:id "r2" :kind :expression :predicate :vaccination-coverage :subject :p :value 6.0}
        ]}"#;
        let formulas = parse_formulas(edn).expect("parse");
        let verdict = super::check_all(&formulas).expect("check");
        assert_eq!(
            verdict.status, "unsat",
            "integer bound to a Real predicate must share the Real sort; got {verdict:?}"
        );
    }

    // A double whose scaled numerator overflows i64 must be rejected
    // rather than silently saturated to i64::MAX (which corrupts the
    // encoded rational).
    #[test]
    fn double_overflow_is_rejected() {
        let edn = r#"{:atoms [
            {:id "ov" :kind :expression :predicate :basic-reproduction-number :subject :d :value 1.0e19}
        ]}"#;
        let formulas = parse_formulas(edn).expect("parse");
        assert!(
            super::check_all(&formulas).is_err(),
            "overflowing double must be rejected, not saturated"
        );
    }

    // The Z3 var name must be the cross-language canonical form, which
    // strips BOTH `:` and `?` prefixes. A `?`-prefixed string predicate
    // and a `:`-keyword predicate that denote the same identifier must
    // map to the SAME Z3 symbol. Here `?dose`/`?p` (string) and
    // `:dose`/`:p` (keyword) both canonicalise to `dose_p`; binding them
    // to contradictory values is unsat only when they share the symbol.
    // With the old `trim_start_matches(':')` the `?`-prefixed atom yields
    // `?dose_?p`, a distinct symbol, and Z3 returns sat.
    #[test]
    fn question_prefixed_predicate_canonicalises_to_same_symbol() {
        let edn = r#"{:atoms [
            {:id "q1" :kind :expression :predicate "?dose" :subject "?p" :value 5}
            {:id "q2" :kind :expression :predicate :dose :subject :p :value 6}
        ]}"#;
        let formulas = parse_formulas(edn).expect("parse");
        let verdict = super::check_all(&formulas).expect("check");
        assert_eq!(
            verdict.status, "unsat",
            "?-prefixed and :-prefixed forms of the same identifier must \
             share a canonical Z3 symbol; got {verdict:?}"
        );
    }

    // H-03: the kg layer must receive the claims that were asserted into
    // the solver, not an empty slice. `check_all` now populates
    // `Verdict.verified`; feeding that into `ingest_and_summarize` (the
    // exact hand-off lib.rs performs) must yield a non-zero `claim_count`.
    // Before the fix `verdict.verified` was always empty -> claim_count 0.
    // (adsc-clinical/epidemiology ship as cdylib-only, so this lib-path
    // test must be inline rather than an external integration test.)
    #[cfg(feature = "kg")]
    #[test]
    fn check_all_populates_verified_and_kg_sees_real_claims() {
        let edn = r#"{:atoms [
            {:id "clm-001" :kind :expression :predicate :some-pred :subject :s :value 5}
            {:id "clm-002" :kind :expression :predicate :other-pred :subject :s :value 7}
        ]}"#;
        let formulas = parse_formulas(edn).expect("parse");
        let verdict = super::check_all(&formulas).expect("check");
        assert_eq!(
            verdict.verified.len(),
            2,
            "check_all must carry the asserted claims out on Verdict.verified; got {verdict:?}"
        );
        let summary = crate::kg::ingest_and_summarize(&verdict.verified)
            .expect("ingest_and_summarize over verified claims");
        assert!(
            summary.claim_count > 0,
            "kg must see the real claims fed from the lib path; claim_count was {}",
            summary.claim_count
        );
        assert_eq!(summary.claim_count, 2);
    }
}
