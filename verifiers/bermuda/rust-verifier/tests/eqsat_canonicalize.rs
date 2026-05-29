//! REQ-EQSAT-040, 042: canonicalisation smoke test.
//!
//! Verifies that `eqsat::canonicalize` returns a stable representative
//! for a commutative add expression and propagates a parse error as
//! `Err` instead of panicking across the napi FFI boundary.

#![cfg(feature = "eqsat")]

use bermuda_verifier::eqsat::{canonicalize, saturate};

#[test]
fn commutative_add_canonicalises() {
    let canonical = canonicalize("(+ b a)", 10_000).expect("parse");
    let s = canonical.to_string();
    // Either (+ a b) or (+ b a) is acceptable as long as it's stable.
    assert!(s == "(+ a b)" || s == "(+ b a)", "got {s}");
}

#[test]
fn malformed_input_returns_err_not_panic() {
    // An unparseable s-expression must surface as a recoverable Err so
    // the napi wrapper returns a JS-catchable error rather than
    // aborting the process. `(+ (` is unbalanced and never parses.
    let r = canonicalize("(+ (", 10_000);
    assert!(r.is_err(), "malformed input must be Err, got {r:?}");
}

#[test]
fn saturate_propagates_parse_error() {
    let r = saturate("(+ (", "");
    assert!(r.is_err(), "saturate must propagate parse Err, got {r:?}");
}
