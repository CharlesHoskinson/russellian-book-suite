//! REQ-DATALOG-040: `kg::run_queries` runs every defquery declared in
//! the `:queries` EDN payload against an in-memory Cozo instance and
//! returns a per-query `QueryRunResult` with a row count.
//!
//! The test below seeds a single Datalog source that surfaces a known
//! orphan claim, runs it through `run_queries`, and asserts the row
//! count matches. The test is gated on the `kg` feature so a build
//! without Cozo skips it.
#![cfg(feature = "kg")]

use osmotic_pressure_verifier::kg;

const ORPHAN_QUERY_EDN: &str = r#"
{:queries [
  {:id "Q001-orphan-claims"
   :source "?[c] := c = 'clm-orphan-001'"}
]}
"#;

const TWO_QUERIES_EDN: &str = r#"
{:queries [
  {:id "Q001-orphan-claims"
   :source "?[c] := c = 'clm-orphan-001'"}
  {:id "Q002-empty"
   :source "?[c] := c = 'clm-x', c = 'clm-y'"}
]}
"#;

#[test]
fn run_queries_surfaces_the_orphan_row() {
    let results = kg::run_queries(ORPHAN_QUERY_EDN)
        .expect("run_queries should not error on a well-formed payload");
    assert_eq!(results.len(), 1, "expected one query result, got {results:?}");
    let r = &results[0];
    assert_eq!(r.name, "Q001-orphan-claims");
    assert_eq!(r.rows, 1, "orphan query should match exactly one row");
    assert!(!r.timed_out);
    assert!(r.sample.is_some(), "non-empty result should carry a sample row");
}

#[test]
fn empty_result_set_is_still_reported() {
    let results = kg::run_queries(TWO_QUERIES_EDN)
        .expect("run_queries should not error on a well-formed payload");
    assert_eq!(results.len(), 2);
    let q2 = results.iter().find(|r| r.name == "Q002-empty").expect("Q002 missing");
    assert_eq!(q2.rows, 0, "empty query result must still appear");
    assert!(!q2.timed_out);
}

#[test]
fn missing_source_is_a_parse_error() {
    let bad = r#"{:queries [{:id "Q001"}]}"#;
    let err = kg::run_queries(bad).expect_err("missing :source must error");
    assert!(err.contains("source"), "error should name the missing field, got {err:?}");
}

#[test]
fn timeout_env_var_short_circuits_long_query() {
    // REQ-DATALOG-044: a query that cannot complete within
    // VERIFIER_DATALOG_TIMEOUT_MS is marked timed_out without
    // panicking. We force a 1 ms timeout to flush the channel before
    // even a trivial query finishes; the result MAY still complete in
    // time on a fast machine, so the assertion is "no panic; result
    // present in the vector".
    let prev = std::env::var("VERIFIER_DATALOG_TIMEOUT_MS").ok();
    // SAFETY: tests run single-threaded here; set/unset is symmetric.
    unsafe { std::env::set_var("VERIFIER_DATALOG_TIMEOUT_MS", "1"); }
    let results = kg::run_queries(ORPHAN_QUERY_EDN).expect("no error");
    unsafe {
        match prev {
            Some(v) => std::env::set_var("VERIFIER_DATALOG_TIMEOUT_MS", v),
            None => std::env::remove_var("VERIFIER_DATALOG_TIMEOUT_MS"),
        }
    }
    assert_eq!(results.len(), 1, "timeout still records a result row");
    // Either the query completed in < 1 ms or it timed out; both are
    // legal outcomes. The contract is: run_queries does NOT panic and
    // returns one entry per declared query.
    let r = &results[0];
    if r.timed_out {
        assert_eq!(r.sample.as_deref(), Some("<timeout>"));
    }
}
