//! REQ-DSL-054: smt::check_value_sort_compat fails when an atom binds a
//! scalar value to a predicate the schema declared as `[:vector T]` /
//! `[:set T]`.
//!
//! The test drives the helper with a synthetic `is_vector` closure rather
//! than relying on the codegen-emitted `axioms::predicate_is_vector`, which
//! returns false for every name until the project's
//! `booklogic-schema.edn` declares a multi-valued predicate.

#![cfg(feature = "smt")]

use edn_rs::Edn;
use osmotic_pressure_verifier::ir::{self, Error};
use osmotic_pressure_verifier::smt::{self, check_value_sort_compat};

fn always_vector(_name: &str) -> bool { true }
fn never_vector(_name: &str) -> bool { false }

fn parse_edn(s: &str) -> Edn {
    s.parse().expect("parse Edn literal")
}

#[test]
fn scalar_int_value_for_vector_predicate_errors() {
    // REQ-DSL-054: int bound to a vector-typed predicate is a sort mismatch.
    let value = parse_edn("154");
    let res   = check_value_sort_compat("solutes_s", "atom-001", &value, always_vector);
    let err   = res.expect_err("scalar Int must be rejected against a vector predicate");
    let Error::Smt(msg) = err else { panic!("expected Error::Smt, got {err:?}") };
    assert!(msg.contains("sort mismatch"), "msg = {msg}");
    assert!(msg.contains("solutes_s"),     "msg = {msg}");
    assert!(msg.contains("[:vector"),      "msg = {msg}");
    assert!(msg.contains("scalar Int"),    "msg = {msg}");
}

#[test]
fn scalar_real_value_for_vector_predicate_errors() {
    let value = parse_edn("0.154");
    let res   = check_value_sort_compat("solutes_s", "atom-002", &value, always_vector);
    let err   = res.expect_err("scalar Real must be rejected against a vector predicate");
    let Error::Smt(msg) = err else { panic!("expected Error::Smt, got {err:?}") };
    assert!(msg.contains("scalar Real"), "msg = {msg}");
}

#[test]
fn scalar_string_value_for_vector_predicate_errors() {
    let value = parse_edn("\"foo\"");
    let res   = check_value_sort_compat("solutes_s", "atom-003", &value, always_vector);
    let err   = res.expect_err("scalar String must be rejected against a vector predicate");
    let Error::Smt(msg) = err else { panic!("expected Error::Smt, got {err:?}") };
    assert!(msg.contains("scalar String"), "msg = {msg}");
}

#[test]
fn vector_value_for_vector_predicate_passes() {
    // A genuinely multi-valued binding is accepted.
    let value = parse_edn("[0.1 0.2 0.3]");
    let res = check_value_sort_compat("solutes_s", "atom-004", &value, always_vector);
    assert!(res.is_ok(), "vector value must be accepted against a vector predicate: {res:?}");
}

#[test]
fn scalar_value_for_scalar_predicate_passes() {
    // The mismatch check is gated on the predicate being vector-typed;
    // scalar-on-scalar always passes through.
    let value = parse_edn("9");
    let res   = check_value_sort_compat("parishes-count_Bermuda", "atom-005", &value, never_vector);
    assert!(res.is_ok(), "scalar-on-scalar must pass: {res:?}");
}

// edn-rs 0.19 parses positive integer literals as Edn::UInt, not Edn::Int.
// Before the fix, bind_atoms hit the `_ => continue` arm for UInt values,
// silently dropping every positive-integer atom. Two contradictory UInt
// bindings on the same Z3 variable are unsatisfiable when bound; if they
// are dropped, the solver has no constraints and returns :sat instead.
#[test]
fn positive_integer_atom_binds_to_z3() {
    // Two expression atoms, same predicate+subject, contradictory values.
    // count_probe-x == 5  AND  count_probe-x == 99  =>  :unsat when bound.
    // Positive integer literals parse as Edn::UInt in edn-rs 0.19.
    let edn = r#"{:atoms [
        {:id "uint-a" :kind :expression :predicate :count :subject :probe-x :value 5}
        {:id "uint-b" :kind :expression :predicate :count :subject :probe-x :value 99}
    ]}"#;
    let formulas = ir::parse_formulas(edn)
        .expect("EDN must parse cleanly");
    // Verify that the parser did produce Edn::UInt for the value field,
    // confirming this test exercises the right code path.
    let values: Vec<_> = formulas.iter()
        .filter_map(|(_, atom)| atom.get(":value"))
        .collect();
    assert_eq!(values.len(), 2, "expected two atoms with :value");
    for v in &values {
        assert!(
            matches!(v, Edn::UInt(_)),
            "edn-rs 0.19 must parse positive int literal as Edn::UInt; got {v:?}"
        );
    }
    // With both atoms bound, the solver must find the system unsatisfiable
    // (count_probe-x cannot equal both 5 and 99 simultaneously).
    // Before the Edn::UInt fix, the atoms are silently dropped and the
    // solver returns :sat.
    let verdict = smt::check_all(&formulas)
        .expect("check_all must not error on well-formed UInt atoms");
    assert_eq!(
        verdict.status, "unsat",
        "contradictory UInt atom bindings must be detected as :unsat; \
         :sat means bind_atoms dropped the Edn::UInt values silently"
    );
}
