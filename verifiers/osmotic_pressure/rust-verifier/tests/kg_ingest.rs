//! kg-cozo-single-quote-escape: claim ids/sources containing
//! backslashes or quotes must not break the Cozo insert. The prior
//! string-interpolation path only escaped `'` and produced invalid
//! Cozo escapes for backslashes (e.g. a Windows path `C:\Users`);
//! parameterised inputs avoid manual escaping entirely.
#![cfg(feature = "kg")]

use osmotic_pressure_verifier::ir::Claim;
use osmotic_pressure_verifier::kg;

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
