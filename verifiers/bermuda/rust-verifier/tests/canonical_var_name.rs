//! REQ-EDN-046: Rust canonical_var_name matches the cross-language golden vectors.
use bermuda_verifier::canonical::canonical_var_name;
use edn_rs::Edn;
use std::fs;
use std::path::PathBuf;

fn golden_path() -> PathBuf {
    // Cargo runs tests from the rust-verifier crate dir. Climb 3 levels
    // to reach the repo root, then descend into the skill goldens dir.
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .unwrap() // verifiers/bermuda
        .parent()
        .unwrap() // verifiers
        .parent()
        .unwrap() // repo root
        .join("skills/neurosym-forge/tests/golden/canonical_var_name.edn")
}

fn strip_keyword_prefix(s: &str) -> String {
    s.trim_start_matches(':').to_string()
}

#[test]
fn matches_golden_vectors() {
    let raw = fs::read_to_string(golden_path()).expect("read golden");
    let edn: Edn = raw.parse().expect("parse golden");
    let rows: Vec<Edn> = match edn {
        Edn::Vector(v) => v.to_vec(),
        other => panic!("expected golden to be a vector, got {other:?}"),
    };
    for row in rows {
        let pred = row.get(":predicate").expect("predicate");
        let subj = row.get(":subject").expect("subject");
        let want = row.get(":want").expect("want");
        let pred_str = match pred {
            Edn::Key(k) => strip_keyword_prefix(k),
            Edn::Str(s) => s.clone(),
            other => panic!("predicate must be key or str, got {other:?}"),
        };
        let subj_str = match subj {
            Edn::Key(k) => strip_keyword_prefix(k),
            Edn::Str(s) => s.clone(),
            other => panic!("subject must be key or str, got {other:?}"),
        };
        let want_str = match want {
            Edn::Str(s) => s.clone(),
            other => panic!("want must be string, got {other:?}"),
        };
        let got = canonical_var_name(&pred_str, &subj_str);
        assert_eq!(got, want_str, "({pred_str:?}, {subj_str:?})");
    }
}
