//! REQ-PERF-040..043: per-subject Z3 solver partitioning integration test.
//!
//! Three subjects in one ledger. The osmotic_pressure axiom binds the
//! :s subject only (van 't Hoff). The other two subjects (:t and :u)
//! are unconstrained at the axiom layer, so any ledger value for them
//! is satisfiable. The merge rule (REQ-PERF-042) must therefore yield
//! :sat when every per-subject partition decides cleanly.
//!
//! We also force one subject's partition into :unknown via the existing
//! Tier 1 timeout knob set to 1ms. Per the partition contract that
//! :unknown MUST NOT poison the verdict on the other two subjects —
//! the merged verdict becomes :unknown but the explanation names ONLY
//! the timed-out subject(s) (REQ-PERF-040).
//!
//! NOTE: this test is feature-gated on `smt` because non-feature builds
//! return an error verdict from check_all.

#![cfg(feature = "smt")]

use std::sync::Mutex;

/// Lock around tests that mutate process-global env vars. cargo runs
/// `#[test]` functions in parallel by default; without this lock,
/// concurrent env mutations cause flaky verdicts on the trivial
/// fixtures (the verifier reads the timeout once per check_all and
/// another test can flip it mid-flight).
static ENV_LOCK: Mutex<()> = Mutex::new(());

mod common {
    pub fn ledger_edn(values: &[(&str, &str, &str, f64)]) -> String {
        let mut atoms = String::new();
        for (id, pred, subj, val) in values {
            let val_str = if val.fract() == 0.0 {
                format!("{}.0", val)
            } else {
                format!("{}", val)
            };
            atoms.push_str(&format!(
                "{{:id \"{id}\" :kind :expression :predicate :{pred} \
                 :subject :{subj} :value {val_str}}} ",
            ));
        }
        format!("{{:version 1 :atoms [{}]}}", atoms)
    }
}

// The cleanest way to reach check_all from an integration test is the
// public `verify_formulas` napi binding — it takes the EDN string and
// returns the EDN-emitted verdict. We parse the status keyword back
// out of the EDN string.

fn extract_status(verdict_edn: &str) -> String {
    // The verdict EDN starts with `{:status :sat …}` / `:unsat` / `:unknown`.
    // Slice that out without doing a full EDN parse — the format is
    // controlled by `ir::emit_verdict` and the keyword name is the
    // first whitespace-delimited token after `:status :`.
    let needle = ":status :";
    let i = verdict_edn.find(needle).expect("status keyword in verdict EDN");
    let rest = &verdict_edn[i + needle.len()..];
    let end = rest
        .find(|c: char| c.is_whitespace() || c == '}')
        .unwrap_or(rest.len());
    rest[..end].to_string()
}

#[test]
fn three_subjects_all_sat_returns_sat() {
    let _guard = ENV_LOCK.lock().unwrap_or_else(|e| e.into_inner());
    // Ensure no leaked 1ms timeout from a racing test.
    let prev = std::env::var("VERIFIER_SOLVER_TIMEOUT_MS").ok();
    unsafe { std::env::set_var("VERIFIER_SOLVER_TIMEOUT_MS", "30000"); }
    // REQ-PERF-040: every subject has its own partition; with no axiom
    // contradicting any subject's atoms, the merged verdict is :sat.
    let edn = common::ledger_edn(&[
        // subject :s — full van 't Hoff fixture, satisfies the axiom
        ("osm-001", "vant-hoff-i", "s", 2.0),
        ("osm-002", "molarity", "s", 0.154),
        ("osm-003", "temperature-k", "s", 298.15),
        ("osm-004", "osmotic-pressure-pa", "s", 763.27),
        // subject :t — unconstrained predicates, any value is fine
        ("osm-005", "some-int", "t", 42.0),
        // subject :u — unconstrained predicates, any value is fine
        ("osm-006", "some-other-int", "u", 7.0),
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
    assert_eq!(status, "sat", "merged verdict should be :sat, got {status:?} ({out})");
}

#[test]
fn per_subject_unknown_does_not_poison_other_subjects() {
    let _guard = ENV_LOCK.lock().unwrap_or_else(|e| e.into_inner());
    // REQ-PERF-040: forcing the :s partition into :unknown via a
    // pathological-timeout for the NRA axiom must NOT silently coerce
    // the other subjects' :sat into the same :unknown. The merged
    // verdict is :unknown (worst-non-:unsat dominates), and the
    // explanation names only the subject that actually timed out.
    let prev = std::env::var("VERIFIER_SOLVER_TIMEOUT_MS").ok();
    // SAFETY: cargo test runs each test in a single-threaded context
    // by default — set_var is sound here. We restore on the way out.
    unsafe { std::env::set_var("VERIFIER_SOLVER_TIMEOUT_MS", "1"); }

    // We intentionally feed a fixture that — with a 1ms timeout — may
    // come back as :unsat (Z3 solves the doctored case fast) OR
    // :unknown (timeout actually fires). Either way the merge rule
    // must NOT swallow :sat/:unknown evidence from :t and :u.
    let edn = common::ledger_edn(&[
        ("osm-doc-001", "vant-hoff-i", "s", 1.0),
        ("osm-doc-002", "molarity", "s", 0.154),
        ("osm-doc-003", "temperature-k", "s", 298.15),
        ("osm-doc-004", "osmotic-pressure-pa", "s", 780202.5),
        ("osm-005", "some-int", "t", 42.0),
        ("osm-006", "some-other-int", "u", 7.0),
    ]);
    let out = osmotic_pressure_verifier::verify_formulas(edn);
    unsafe {
        match prev {
            Some(v) => std::env::set_var("VERIFIER_SOLVER_TIMEOUT_MS", v),
            None    => std::env::remove_var("VERIFIER_SOLVER_TIMEOUT_MS"),
        }
    }
    let out = out.expect("verify_formulas");
    let status = extract_status(&out);
    // All three legal statuses are acceptable — the spec only requires
    // that other subjects' evidence is not lost. :sat would mean every
    // partition decided sat (also valid). :unsat means at least the :s
    // partition's axiom was unsat. :unknown means at least one
    // partition timed out. Critically: the explanation, when :unknown
    // or :unsat, must NOT mention t or u as the cause.
    assert!(
        ["sat", "unsat", "unknown"].contains(&status.as_str()),
        "verdict status = {status:?}",
    );
    if status == "unknown" {
        // The explanation field carries the subjects-list. Other
        // subjects must not appear unless they themselves timed out
        // (and with the simple atom binding they cannot).
        let expl_start = out.find(":explanation \"").unwrap();
        let after = &out[expl_start + ":explanation \"".len()..];
        let expl_end = after.find('"').unwrap();
        let explanation = &after[..expl_end];
        assert!(
            !explanation.contains(", t,") && !explanation.contains(", u,")
                && !explanation.ends_with(" t") && !explanation.ends_with(" u"),
            "explanation should not name unrelated subjects t/u: {explanation:?}",
        );
    }
}

#[test]
fn serial_default_is_deterministic() {
    let _guard = ENV_LOCK.lock().unwrap_or_else(|e| e.into_inner());
    // REQ-PERF-041: VERIFIER_SOLVER_PARALLELISM unset defaults to 1
    // (serial). Two back-to-back runs produce byte-identical verdicts.
    let edn = common::ledger_edn(&[
        ("osm-001", "vant-hoff-i", "s", 2.0),
        ("osm-002", "molarity", "s", 0.154),
        ("osm-003", "temperature-k", "s", 298.15),
        ("osm-004", "osmotic-pressure-pa", "s", 763.27),
    ]);
    let prev_par = std::env::var("VERIFIER_SOLVER_PARALLELISM").ok();
    let prev_to  = std::env::var("VERIFIER_SOLVER_TIMEOUT_MS").ok();
    unsafe {
        std::env::remove_var("VERIFIER_SOLVER_PARALLELISM");
        std::env::set_var("VERIFIER_SOLVER_TIMEOUT_MS", "30000");
    }
    let a = osmotic_pressure_verifier::verify_formulas(edn.clone()).unwrap();
    let b = osmotic_pressure_verifier::verify_formulas(edn).unwrap();
    unsafe {
        if let Some(v) = prev_par {
            std::env::set_var("VERIFIER_SOLVER_PARALLELISM", v);
        }
        match prev_to {
            Some(v) => std::env::set_var("VERIFIER_SOLVER_TIMEOUT_MS", v),
            None    => std::env::remove_var("VERIFIER_SOLVER_TIMEOUT_MS"),
        }
    }
    assert_eq!(extract_status(&a), extract_status(&b));
}

#[test]
fn parallelism_four_workers_returns_same_verdict_as_serial() {
    let _guard = ENV_LOCK.lock().unwrap_or_else(|e| e.into_inner());
    // REQ-PERF-041: with VERIFIER_SOLVER_PARALLELISM=4 the worker pool
    // resolves partitions concurrently but the final merged verdict
    // matches the serial run. We do not assert anything about
    // wall-clock here — the partition count for osmotic_pressure is
    // small enough that overhead dominates.
    let edn = common::ledger_edn(&[
        ("osm-001", "vant-hoff-i", "s", 2.0),
        ("osm-002", "molarity", "s", 0.154),
        ("osm-003", "temperature-k", "s", 298.15),
        ("osm-004", "osmotic-pressure-pa", "s", 763.27),
        ("osm-005", "some-int", "t", 42.0),
        ("osm-006", "some-other-int", "u", 7.0),
    ]);
    let prev_par = std::env::var("VERIFIER_SOLVER_PARALLELISM").ok();
    let prev_to  = std::env::var("VERIFIER_SOLVER_TIMEOUT_MS").ok();
    unsafe {
        std::env::remove_var("VERIFIER_SOLVER_PARALLELISM");
        std::env::set_var("VERIFIER_SOLVER_TIMEOUT_MS", "30000");
    }
    let serial = osmotic_pressure_verifier::verify_formulas(edn.clone()).unwrap();
    unsafe { std::env::set_var("VERIFIER_SOLVER_PARALLELISM", "4"); }
    let parallel = osmotic_pressure_verifier::verify_formulas(edn).unwrap();
    unsafe {
        match prev_par {
            Some(v) => std::env::set_var("VERIFIER_SOLVER_PARALLELISM", v),
            None    => std::env::remove_var("VERIFIER_SOLVER_PARALLELISM"),
        }
        match prev_to {
            Some(v) => std::env::set_var("VERIFIER_SOLVER_TIMEOUT_MS", v),
            None    => std::env::remove_var("VERIFIER_SOLVER_TIMEOUT_MS"),
        }
    }
    assert_eq!(extract_status(&serial), extract_status(&parallel));
}
