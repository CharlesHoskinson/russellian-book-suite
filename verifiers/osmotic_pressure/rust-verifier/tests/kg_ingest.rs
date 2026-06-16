//! kg-cozo-single-quote-escape: claim ids/sources containing
//! backslashes or quotes must not break the Cozo insert. The prior
//! string-interpolation path only escaped `'` and produced invalid
//! Cozo escapes for backslashes (e.g. a Windows path `C:\Users`);
//! parameterised inputs avoid manual escaping entirely.
#![cfg(feature = "kg")]

use osmotic_pressure_verifier::ir::Claim;
use osmotic_pressure_verifier::kg;

// H-03: the kg layer must receive the claims that were asserted into the
// solver, not an empty slice. `check_all` now populates
// `Verdict.verified`; feeding that into `ingest_and_summarize` (the exact
// hand-off lib.rs performs) must yield a non-zero `claim_count`. Before
// the fix `verdict.verified` was always empty, so `claim_count` was 0.
// This drives the real population path (parse -> check_all -> verified)
// rather than hand-made claims.
#[cfg(feature = "smt")]
#[test]
fn check_all_populates_verified_and_kg_sees_real_claims() {
    use osmotic_pressure_verifier::ir::parse_formulas;
    use osmotic_pressure_verifier::smt;

    let edn = r#"{:version 1 :atoms [
        {:id "clm-001" :kind :expression :predicate :some-pred :subject :s :value 5}
        {:id "clm-002" :kind :expression :predicate :other-pred :subject :s :value 7}
    ]}"#;
    let formulas = parse_formulas(edn).expect("parse_formulas");
    let verdict = smt::check_all(&formulas).expect("check_all");
    assert_eq!(
        verdict.verified.len(),
        2,
        "check_all must carry the asserted claims out on Verdict.verified; got {verdict:?}"
    );
    let summary = kg::ingest_and_summarize(&verdict.verified)
        .expect("ingest_and_summarize over verified claims");
    assert!(
        summary.claim_count > 0,
        "kg must see the real claims fed from the lib path; claim_count was {}",
        summary.claim_count
    );
    assert_eq!(summary.claim_count, 2);
}

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
