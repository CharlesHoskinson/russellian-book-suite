//! REQ-EDN-048: golden EDN files parse with edn-rs and field types
//! match expectations (Edn::Key for keyword fields, Edn::Double for
//! real-typed values).
use edn_rs::Edn;
use std::fs;
use std::path::PathBuf;

fn golden_dir() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .unwrap()
        .parent()
        .unwrap()
        .parent()
        .unwrap()
        .join("skills/neurosym-forge/tests/golden")
}

#[test]
fn expression_atom_value_is_double() {
    let raw = fs::read_to_string(golden_dir().join("expression_atom.edn")).unwrap();
    let edn: Edn = raw.parse().unwrap();
    let value = edn.get(":value").expect("value");
    assert!(
        matches!(value, Edn::Double(_)),
        "expected Double, got {value:?}"
    );
}

#[test]
fn opaque_atom_kind_is_keyword() {
    let raw = fs::read_to_string(golden_dir().join("opaque_atom.edn")).unwrap();
    let edn: Edn = raw.parse().unwrap();
    let kind = edn.get(":kind").expect("kind");
    assert!(matches!(kind, Edn::Key(_)), "expected Key, got {kind:?}");
}

#[test]
fn verdict_status_is_keyword() {
    let raw = fs::read_to_string(golden_dir().join("verdict.edn")).unwrap();
    let edn: Edn = raw.parse().unwrap();
    let status = edn.get(":status").expect("status");
    assert!(
        matches!(status, Edn::Key(_)),
        "expected Key, got {status:?}"
    );
}
