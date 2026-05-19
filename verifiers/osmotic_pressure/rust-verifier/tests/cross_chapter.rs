//! REQ-CORPUS-050..056: corpus-scope integration test.
//!
//! Drives the full `verify_formulas` path with a 2-subject ledger where
//! the same logical trial (`mizuno-2008`) reports `:trial-n` in two
//! chapters. The corpus-scope constraint `C050-trial-n-agrees` asserts
//! the two values must be equal. When they disagree, the verdict must:
//!
//! - report top-level `:status :unsat`
//! - carry exactly one `:corpus-defects` entry
//! - name both chapter subjects in that entry's `:subjects` field
//!
//! When they agree, the verdict must be `:sat` and `:corpus-defects`
//! must be empty.
//!
//! The test is feature-gated on `smt` because non-feature builds return
//! an error verdict from `check_all`.

#![cfg(feature = "smt")]

use std::sync::Mutex;

/// Lock around tests that mutate process-global env vars; matches the
/// pattern in `tests/partitioning.rs`.
static ENV_LOCK: Mutex<()> = Mutex::new(());

fn ledger_edn(values: &[(&str, &str, &str, i64)]) -> String {
    let mut atoms = String::new();
    for (id, pred, subj, val) in values {
        atoms.push_str(&format!(
            "{{:id \"{id}\" :kind :expression :predicate :{pred} \
             :subject :{subj} :value {val}}} ",
        ));
    }
    format!("{{:version 1 :atoms [{}]}}", atoms)
}

fn extract_status(verdict_edn: &str) -> String {
    let needle = ":status :";
    let i = verdict_edn.find(needle).expect("status keyword in verdict EDN");
    let rest = &verdict_edn[i + needle.len()..];
    let end = rest
        .find(|c: char| c.is_whitespace() || c == '}')
        .unwrap_or(rest.len());
    rest[..end].to_string()
}

#[test]
fn two_subject_disagreement_surfaces_corpus_defect() {
    let _guard = ENV_LOCK.lock().unwrap_or_else(|e| e.into_inner());
    // REQ-CORPUS-052, 053, 056: a 2-subject corpus where the two
    // chapters disagree on `:trial-n`. The corpus solver sees both
    // bindings and the equality axiom flips it to :unsat. The verdict's
    // :corpus-defects field names both subjects.
    let prev = std::env::var("VERIFIER_SOLVER_TIMEOUT_MS").ok();
    unsafe { std::env::set_var("VERIFIER_SOLVER_TIMEOUT_MS", "30000"); }

    // chap-a reports trial-n = 15; chap-b reports trial-n = 5.
    // The corpus-scope C050 axiom asserts the two must be equal.
    let edn = ledger_edn(&[
        ("clm-a-1", "trial-n", "mizuno-2008-chap-a", 15),
        ("clm-b-1", "trial-n", "mizuno-2008-chap-b",  5),
    ]);
    let out = osmotic_pressure_verifier::verify_formulas(edn)
        .expect("verify_formulas");
    unsafe {
        match prev {
            Some(v) => std::env::set_var("VERIFIER_SOLVER_TIMEOUT_MS", v),
            None    => std::env::remove_var("VERIFIER_SOLVER_TIMEOUT_MS"),
        }
    }

    let status = extract_status(&out);
    assert_eq!(
        status, "unsat",
        "corpus-scope disagreement should surface :unsat, got {status:?}\n{out}",
    );
    // The verdict EDN must carry a :corpus-defects vector with at least
    // one entry naming C050-trial-n-agrees.
    assert!(
        out.contains(":corpus-defects ["),
        "verdict must serialise :corpus-defects field: {out}",
    );
    assert!(
        out.contains("C050-trial-n-agrees"),
        "corpus defect entry must name the firing constraint: {out}",
    );
    // Both chapter subjects must appear in the :subjects vector of the
    // corpus-defect entry. The serialiser writes them as quoted strings
    // adjacent to the :subjects keyword.
    let cd_start = out
        .find(":corpus-defects [")
        .expect("verdict carries :corpus-defects");
    let cd_slice = &out[cd_start..];
    assert!(
        cd_slice.contains("\"mizuno-2008-chap-a\""),
        "corpus defect must name chap-a subject: {cd_slice}",
    );
    assert!(
        cd_slice.contains("\"mizuno-2008-chap-b\""),
        "corpus defect must name chap-b subject: {cd_slice}",
    );
}

#[test]
fn two_subject_agreement_keeps_corpus_clean() {
    let _guard = ENV_LOCK.lock().unwrap_or_else(|e| e.into_inner());
    // REQ-CORPUS-052: when both chapters agree on :trial-n the corpus
    // solver is :sat and the verdict carries an empty :corpus-defects
    // vector.
    let prev = std::env::var("VERIFIER_SOLVER_TIMEOUT_MS").ok();
    unsafe { std::env::set_var("VERIFIER_SOLVER_TIMEOUT_MS", "30000"); }

    let edn = ledger_edn(&[
        ("clm-a-1", "trial-n", "mizuno-2008-chap-a", 15),
        ("clm-b-1", "trial-n", "mizuno-2008-chap-b", 15),
    ]);
    let out = osmotic_pressure_verifier::verify_formulas(edn)
        .expect("verify_formulas");
    unsafe {
        match prev {
            Some(v) => std::env::set_var("VERIFIER_SOLVER_TIMEOUT_MS", v),
            None    => std::env::remove_var("VERIFIER_SOLVER_TIMEOUT_MS"),
        }
    }

    let status = extract_status(&out);
    assert_eq!(
        status, "sat",
        "matched corpus values should keep the verdict :sat, got {status:?}\n{out}",
    );
    // The :corpus-defects vector must serialise as empty.
    assert!(
        out.contains(":corpus-defects []"),
        "verdict must carry an empty :corpus-defects vector when no \
         corpus-scope constraint fires: {out}",
    );
}

#[test]
fn corpus_partition_does_not_affect_per_subject_paths() {
    let _guard = ENV_LOCK.lock().unwrap_or_else(|e| e.into_inner());
    // REQ-CORPUS-050: default `:scope :subject` constraints (Phase J)
    // continue to behave identically. The clean van 't Hoff fixture
    // exercised by `tests/partitioning.rs` is still :sat with no
    // corpus-defects, because no `:trial-n` atom is present.
    let prev = std::env::var("VERIFIER_SOLVER_TIMEOUT_MS").ok();
    unsafe { std::env::set_var("VERIFIER_SOLVER_TIMEOUT_MS", "30000"); }

    // Standard subject `:s` van 't Hoff fixture — no cross-chapter atoms.
    let edn = format!(
        "{{:version 1 :atoms [\
         {{:id \"osm-001\" :kind :expression :predicate :vant-hoff-i :subject :s :value 2.0}} \
         {{:id \"osm-002\" :kind :expression :predicate :molarity :subject :s :value 0.154}} \
         {{:id \"osm-003\" :kind :expression :predicate :temperature-k :subject :s :value 298.15}} \
         {{:id \"osm-004\" :kind :expression :predicate :osmotic-pressure-pa :subject :s :value 763.27}} \
         ]}}",
    );
    let out = osmotic_pressure_verifier::verify_formulas(edn)
        .expect("verify_formulas");
    unsafe {
        match prev {
            Some(v) => std::env::set_var("VERIFIER_SOLVER_TIMEOUT_MS", v),
            None    => std::env::remove_var("VERIFIER_SOLVER_TIMEOUT_MS"),
        }
    }

    let status = extract_status(&out);
    assert_eq!(status, "sat", "clean van 't Hoff fixture should remain :sat after corpus path is wired in: {out}");
    assert!(
        out.contains(":corpus-defects []"),
        "no :trial-n atoms => empty corpus-defects: {out}",
    );
}
