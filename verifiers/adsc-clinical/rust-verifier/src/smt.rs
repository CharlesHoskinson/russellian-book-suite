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
    Params, SatResult, Solver,
    ast::{Bool, Int, Real, String as Z3String},
};

/// REQ-DSL-054: check that a value's shape is compatible with the
/// declared return-sort of its predicate. Returns `Err(Error::Smt(...))`
/// when `is_vector` is true and the value is a scalar (Int/Real/Bool/Str);
/// returns `Ok(())` otherwise.
///
/// Extracted so cargo tests can drive the path with a synthetic
/// `is_vector` closure (the codegen-emitted `axioms::predicate_is_vector`
/// returns false for every name when no vector predicate has been
/// declared in `booklogic-schema.edn`).
#[cfg(feature = "smt")]
pub fn check_value_sort_compat(
    var_name: &str,
    atom_id: &str,
    value: &edn_rs::Edn,
    is_vector: impl Fn(&str) -> bool,
) -> Result<(), Error> {
    use edn_rs::Edn;
    if !is_vector(var_name) {
        return Ok(());
    }
    if matches!(value, Edn::Vector(_) | Edn::Set(_)) {
        return Ok(());
    }
    let value_shape = match value {
        Edn::Int(n) => format!("scalar Int({n})"),
        Edn::UInt(n) => format!("scalar Int({n})"),
        Edn::Double(_) => format!("scalar Real({})", value.to_float().unwrap_or(0.0)),
        Edn::Str(s) => format!("scalar String({s:?})"),
        Edn::Bool(b) => format!("scalar Bool({b})"),
        other => format!("{other:?}"),
    };
    Err(Error::Smt(format!(
        "sort mismatch: predicate {var_name:?} declared as \
         [:vector <T>] in booklogic-schema.edn, but atom \
         {atom_id:?} bound value as {value_shape}",
    )))
}

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

        // REQ-DSL-054: fail loudly when an atom binds a scalar value to
        // a predicate the schema declared as `[:vector T]` / `[:set T]`.
        check_value_sort_compat(
            var_name.as_str(),
            id.as_str(),
            value,
            crate::axioms::predicate_is_vector,
        )?;

        let assertion: Bool = match value {
            Edn::Int(n) => {
                let z3_var = Int::new_const(var_name.as_str());
                z3_var.eq(&Int::from_i64(*n))
            }
            // edn-rs renders bare non-negative integers (e.g. `:trial-n 15`)
            // as `Edn::UInt` rather than `Edn::Int`. Bind them identically so
            // those values are asserted to Z3 instead of silently dropped.
            Edn::UInt(n) => {
                let n_i64: i64 = (*n)
                    .try_into()
                    .map_err(|_| Error::Smt(format!("value too large to bind as Int: {n}")))?;
                let z3_var = Int::new_const(var_name.as_str());
                z3_var.eq(&Int::from_i64(n_i64))
            }
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
    use crate::ir::{parse_formulas, Error};

    // edn-rs renders bare non-negative integers (e.g. `:trial-n 15`) as
    // `Edn::UInt`, not `Edn::Int`. The bind walk must assert those values to
    // Z3 just like signed ints; otherwise they fall through to `_ => continue`
    // and the constraint is silently dropped (a false `sat`).
    //
    // Two atoms pin the same `{predicate}_{subject}` Z3 var to two distinct
    // bare integers. If both UInt values are bound, the conjunction is `unsat`.
    // If the UInt arm is missing they are dropped and Z3 reports `sat`.
    #[test]
    fn binds_bare_unsigned_integer_value() {
        let edn = r#"{:atoms [
            {:id "a1" :kind :expression :predicate :trial-n :subject :study :value 15}
            {:id "a2" :kind :expression :predicate :trial-n :subject :study :value 16}
        ]}"#;
        let formulas = parse_formulas(edn).expect("parse");
        let verdict = super::check_all(&formulas).expect("check");
        assert_eq!(
            verdict.status, "unsat",
            "bare unsigned integer values must be bound to Z3; got {verdict:?}"
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

    // REQ-DSL-054: binding a scalar to a predicate the schema declared as
    // `[:vector T]` is a sort mismatch and must be rejected. Driven with a
    // synthetic always-vector closure since the placeholder
    // `predicate_is_vector` returns false for every name.
    #[test]
    fn scalar_for_vector_predicate_errors() {
        use edn_rs::Edn;
        let value: Edn = "154".parse().expect("parse edn");
        let res =
            super::check_value_sort_compat("doses_p", "atom-1", &value, |_| true);
        let err = res.expect_err("scalar bound to vector predicate must be rejected");
        let Error::Smt(msg) = err else {
            panic!("expected Error::Smt, got {err:?}")
        };
        assert!(msg.contains("sort mismatch"), "msg = {msg}");
    }

    // A double whose scaled numerator overflows i64 must be rejected
    // rather than silently saturated to i64::MAX.
    #[test]
    fn double_overflow_is_rejected() {
        let edn = r#"{:atoms [
            {:id "ov" :kind :expression :predicate :rate :subject :s :value 1.0e19}
        ]}"#;
        let formulas = parse_formulas(edn).expect("parse");
        assert!(
            super::check_all(&formulas).is_err(),
            "overflowing double must be rejected, not saturated"
        );
    }
}
