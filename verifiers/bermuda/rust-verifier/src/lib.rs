#![deny(clippy::all)]
use napi_derive::napi;

mod axioms;
pub mod canonical;
mod eqsat;
mod ir;
mod kg;
mod smt;

#[cfg(feature = "pdf")]
mod typeset;

#[napi]
pub fn verify_formulas(formulas_edn: String) -> napi::Result<String> {
    let formulas = ir::parse_formulas(&formulas_edn)
        .map_err(|e| napi::Error::from_reason(format!("parse: {e}")))?;
    let verdict =
        smt::check_all(&formulas).map_err(|e| napi::Error::from_reason(format!("smt: {e}")))?;
    let kg_summary = kg::ingest_and_summarize(&verdict.verified)
        .map_err(|e| napi::Error::from_reason(format!("kg: {e}")))?;
    let mut out = verdict;
    out.graph_summary = Some(kg_summary);
    Ok(ir::emit_verdict(&out))
}

/// Run every `defquery` declared in `query_edn` via Cozo (REQ-DATALOG-040)
/// and return the serialised verdict slice that book-qa merges with the
/// SMT verdict. `query_edn` carries the shape
/// `{:queries [{:id "Q001" :source "?[c] := claim[c, _]"} ...]}`.
#[napi]
pub fn run_queries(query_edn: String) -> napi::Result<String> {
    let results = kg::run_queries(&query_edn)
        .map_err(|e| napi::Error::from_reason(format!("kg run_queries: {e}")))?;
    let mut verdict = ir::Verdict {
        status: "sat".into(),
        ..Default::default()
    };
    for r in results {
        verdict.queries.push(ir::QueryResult {
            name: r.name,
            rows: r.rows,
            sample: r.sample,
        });
    }
    Ok(ir::emit_verdict(&verdict))
}

#[napi]
pub fn saturate(terms_edn: String, rules_edn: String) -> napi::Result<String> {
    eqsat::saturate(&terms_edn, &rules_edn).map_err(|e| napi::Error::from_reason(e.to_string()))
}

#[cfg(feature = "pdf")]
#[napi]
pub fn render_pdf(latex: String, out_path: String) -> napi::Result<()> {
    typeset::render(&latex, &out_path).map_err(|e| napi::Error::from_reason(e.to_string()))
}
