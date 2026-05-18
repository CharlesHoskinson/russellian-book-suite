#![deny(clippy::all)]
use napi_derive::napi;

mod axioms;
pub mod canonical;
mod ir;
mod smt;

#[cfg(feature = "eqsat")]
mod eqsat;

#[cfg(feature = "kg")]
pub mod kg;

#[cfg(feature = "pdf")]
mod typeset;

#[napi]
pub fn verify_formulas(formulas_edn: String) -> napi::Result<String> {
    let formulas = ir::parse_formulas(&formulas_edn)
        .map_err(|e| napi::Error::from_reason(format!("parse: {e}")))?;
    let verdict =
        smt::check_all(&formulas).map_err(|e| napi::Error::from_reason(format!("smt: {e}")))?;
    #[cfg(feature = "kg")]
    let verdict = {
        let mut v = verdict;
        let kg_summary = kg::ingest_and_summarize(&v.verified)
            .map_err(|e| napi::Error::from_reason(format!("kg: {e}")))?;
        v.graph_summary = Some(kg_summary);
        v
    };
    Ok(ir::emit_verdict(&verdict))
}

/// Run every `defquery` declared in `query_edn` via Cozo (REQ-DATALOG-040)
/// and return the serialised verdict slice that book-qa merges with the
/// SMT verdict. `query_edn` carries the shape
/// `{:queries [{:id "Q001" :source "?[c] := claim[c, _]"} ...]}`.
#[cfg(feature = "kg")]
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

#[cfg(feature = "eqsat")]
#[napi]
pub fn saturate(terms_edn: String, rules_edn: String) -> napi::Result<String> {
    eqsat::saturate(&terms_edn, &rules_edn).map_err(|e| napi::Error::from_reason(e.to_string()))
}

#[cfg(feature = "pdf")]
#[napi]
pub fn render_pdf(latex: String, out_path: String) -> napi::Result<()> {
    typeset::render(&latex, &out_path).map_err(|e| napi::Error::from_reason(e.to_string()))
}
