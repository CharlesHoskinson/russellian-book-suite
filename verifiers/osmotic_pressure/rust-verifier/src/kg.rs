// Hand-written kg.rs for the Tier 3 Cozo runtime promotion. The Phase H
// codegen rewrites this file when rules/booklogic/queries.edn declares
// defquery forms; the rewrite layers per-query dispatch on top of the
// `run_queries` / `evaluate_constraint` API exposed here. The stub
// shape (`ingest_and_summarize` over an empty claim graph) is preserved
// so the no-queries case keeps compiling.

use crate::ir::{Claim, Error, GraphSummary};

#[cfg(feature = "kg")]
use cozo::{DbInstance, NamedRows};

/// Default Cozo query timeout in milliseconds. Overridden by the
/// `VERIFIER_DATALOG_TIMEOUT_MS` env var. REQ-DATALOG-044.
pub const DEFAULT_DATALOG_TIMEOUT_MS: u64 = 10_000;

fn datalog_timeout_ms() -> u64 {
    std::env::var("VERIFIER_DATALOG_TIMEOUT_MS")
        .ok()
        .and_then(|s| s.parse().ok())
        .unwrap_or(DEFAULT_DATALOG_TIMEOUT_MS)
}

/// Result of running a single defquery against the in-memory Cozo
/// instance. `sample` carries either a short Debug-rendered row
/// (used by the verdict surface) or `"<timeout>"` when the per-query
/// timeout fires.
#[derive(Debug, Clone)]
pub struct QueryRunResult {
    pub name: String,
    pub rows: usize,
    pub sample: Option<String>,
    pub timed_out: bool,
}

/// Parse a list of `(name, datalog-source)` pairs from a defquery EDN
/// payload of the shape
/// `{:queries [{:id "Q001" :source "?[c] := claim[c, _]"} ...]}`.
#[cfg(feature = "kg")]
pub fn parse_query_edn(query_edn: &str) -> Result<Vec<(String, String)>, String> {
    use edn_rs::{Edn, EdnError};
    let parsed: Edn = query_edn
        .parse::<Edn>()
        .map_err(|e: EdnError| format!("parse: {e}"))?;
    let queries = match parsed.get(":queries") {
        Some(Edn::Vector(v)) => v.clone().to_vec(),
        Some(Edn::List(l)) => l.clone().to_vec(),
        Some(_) | None => return Err("missing or non-vector :queries".into()),
    };
    let mut out = Vec::with_capacity(queries.len());
    for q in queries {
        let id = match q.get(":id") {
            Some(Edn::Str(s)) => s.clone(),
            Some(Edn::Key(k)) => k.trim_start_matches(':').to_string(),
            _ => return Err("query missing :id".into()),
        };
        let source = match q.get(":source") {
            Some(Edn::Str(s)) => s.clone(),
            _ => return Err(format!("query {id} missing :source")),
        };
        out.push((id, source));
    }
    Ok(out)
}

#[cfg(feature = "kg")]
fn run_one_script(
    db: &DbInstance,
    name: &str,
    source: &str,
    timeout_ms: u64,
) -> Result<NamedRows, String> {
    use std::sync::mpsc;
    use std::thread;
    use std::time::Duration;

    let (tx, rx) = mpsc::channel::<Result<NamedRows, String>>();
    let source_owned = source.to_string();
    let name_owned = name.to_string();
    // DbInstance is internally Arc'd; cloning is cheap. We move a clone
    // into the worker thread so the timeout can return early without
    // aborting the script.
    let db_clone = db.clone();
    thread::spawn(move || {
        let result = db_clone
            .run_script(
                &source_owned,
                Default::default(),
                cozo::ScriptMutability::Immutable,
            )
            .map_err(|e| format!("cozo run {name_owned}: {e}"));
        let _ = tx.send(result);
    });
    match rx.recv_timeout(Duration::from_millis(timeout_ms)) {
        Ok(r) => r,
        Err(mpsc::RecvTimeoutError::Timeout) => Err("<timeout>".into()),
        Err(e) => Err(format!("cozo channel: {e}")),
    }
}

/// Run a Datalog source as a one-shot constraint check against a fresh
/// in-memory Cozo instance. The constraint is treated as a witness
/// query: a non-empty result means the constraint produced a defect
/// row, so the row count is returned to the caller. REQ-DATALOG-041.
#[cfg(feature = "kg")]
pub fn evaluate_constraint(name: &str, datalog_source: &str) -> Result<usize, String> {
    let db = DbInstance::new("mem", "", "").map_err(|e| format!("cozo init: {e}"))?;
    let timeout_ms = datalog_timeout_ms();
    let rows = run_one_script(&db, name, datalog_source, timeout_ms)?;
    Ok(rows.rows.len())
}

#[cfg(not(feature = "kg"))]
pub fn evaluate_constraint(_name: &str, _datalog_source: &str) -> Result<usize, String> {
    Err("compiled without `kg` feature".into())
}

/// Run every defquery declared in `query_edn` against an in-memory
/// Cozo instance and collect the resulting `NamedRows`. A query that
/// exceeds `VERIFIER_DATALOG_TIMEOUT_MS` (default 10_000 ms) is
/// recorded as a timeout result and the loop continues without
/// panicking. REQ-DATALOG-040, REQ-DATALOG-044.
#[cfg(feature = "kg")]
pub fn run_queries(query_edn: &str) -> Result<Vec<QueryRunResult>, String> {
    let db = DbInstance::new("mem", "", "").map_err(|e| format!("cozo init: {e}"))?;
    let timeout_ms = datalog_timeout_ms();
    let queries = parse_query_edn(query_edn)?;
    let mut results = Vec::with_capacity(queries.len());
    for (name, source) in queries {
        match run_one_script(&db, &name, &source, timeout_ms) {
            Ok(rows) => {
                let row_count = rows.rows.len();
                let sample = rows.rows.first().map(|r| format!("{r:?}"));
                results.push(QueryRunResult {
                    name,
                    rows: row_count,
                    sample,
                    timed_out: false,
                });
            }
            Err(e) if e == "<timeout>" => {
                results.push(QueryRunResult {
                    name,
                    rows: 0,
                    sample: Some("<timeout>".into()),
                    timed_out: true,
                });
            }
            Err(e) => {
                results.push(QueryRunResult {
                    name,
                    rows: 0,
                    sample: Some(format!("<error: {e}>")),
                    timed_out: false,
                });
            }
        }
    }
    Ok(results)
}

#[cfg(not(feature = "kg"))]
pub fn run_queries(_query_edn: &str) -> Result<Vec<QueryRunResult>, String> {
    Ok(vec![])
}

#[cfg(feature = "kg")]
pub fn ingest_and_summarize(claims: &[Claim]) -> Result<GraphSummary, Error> {
    // No queries declared by hand: return an empty summary. The
    // generated `kg.rs` (post-codegen) overrides this with per-query
    // dispatch.
    Ok(GraphSummary {
        claim_count: claims.len(),
        contradictions: vec![],
    })
}

#[cfg(not(feature = "kg"))]
pub fn ingest_and_summarize(claims: &[Claim]) -> Result<GraphSummary, Error> {
    Ok(GraphSummary {
        claim_count: claims.len(),
        contradictions: vec![],
    })
}
