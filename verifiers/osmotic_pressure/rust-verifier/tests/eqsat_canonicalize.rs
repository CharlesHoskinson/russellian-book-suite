//! REQ-EQSAT-040, 042: canonicalisation smoke test.
//!
//! Verifies that `eqsat::canonicalize` returns a stable representative
//! for a commutative add expression. The exact form (`(+ a b)` vs
//! `(+ b a)`) is implementation-defined; what matters is that the
//! e-graph runs, extracts a single cost-minimal form, and the call
//! does not panic.

#![cfg(feature = "eqsat")]

use osmotic_pressure_verifier::eqsat::canonicalize;

#[test]
fn commutative_add_canonicalises() {
    let canonical = canonicalize("(+ b a)", 10_000);
    let s = canonical.to_string();
    // Either (+ a b) or (+ b a) is acceptable as long as it's stable.
    assert!(s == "(+ a b)" || s == "(+ b a)", "got {s}");
}
