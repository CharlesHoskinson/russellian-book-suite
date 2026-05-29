//! Issue #141: `ingest_and_summarize` must not return `Err` on a default
//! (kg-enabled) build. The generated Q001 query reads the relations
//! `claim/load-bearing` and `claim/posterior`; `build_db` must declare
//! every relation the generated queries reference, or Cozo errors on the
//! unknown relation and the verifier fails every call.
#![cfg(feature = "kg")]

use bermuda_verifier::ir::Claim;
use bermuda_verifier::kg;

#[test]
fn ingest_and_summarize_is_ok_for_plain_claims() {
    let claims = vec![
        Claim {
            id: "clm-001".into(),
            source: "raw/intro.md".into(),
        },
        Claim {
            id: "clm-002".into(),
            source: "raw/methods.md".into(),
        },
    ];
    let summary = kg::ingest_and_summarize(&claims)
        .expect("ingest_and_summarize must return Ok for the default kg build (issue #141)");
    assert_eq!(summary.claim_count, 2);
}

#[test]
fn ingest_and_summarize_is_ok_for_empty_claims() {
    let summary =
        kg::ingest_and_summarize(&[]).expect("ingest_and_summarize must return Ok for no claims");
    assert_eq!(summary.claim_count, 0);
}

// A claim source containing a backslash (e.g. a Windows path) or a
// single quote must not break the Cozo insert. String interpolation
// that only escapes `'` mishandles backslashes (Cozo single-quoted
// literals use C-style escapes), so `C:\Users` becomes an invalid
// escape and the insert errors. Parameterised inputs avoid this.
#[test]
fn ingest_and_summarize_handles_backslash_and_quote_in_source() {
    let claims = vec![
        Claim {
            id: "clm-001".into(),
            source: r"C:\Users\charl\raw\intro.md".into(),
        },
        Claim {
            id: "clm-002".into(),
            source: "it's a \\regex\\ with 'quotes'".into(),
        },
    ];
    let summary = kg::ingest_and_summarize(&claims)
        .expect("ingest must tolerate backslashes and quotes in claim source");
    assert_eq!(summary.claim_count, 2);
}
