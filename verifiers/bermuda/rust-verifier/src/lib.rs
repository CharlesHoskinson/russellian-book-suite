#![deny(clippy::all)]
use napi_derive::napi;

mod axioms;
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

#[napi]
pub fn saturate(terms_edn: String, rules_edn: String) -> napi::Result<String> {
    eqsat::saturate(&terms_edn, &rules_edn).map_err(|e| napi::Error::from_reason(e.to_string()))
}

#[cfg(feature = "pdf")]
#[napi]
pub fn render_pdf(latex: String, out_path: String) -> napi::Result<()> {
    typeset::render(&latex, &out_path).map_err(|e| napi::Error::from_reason(e.to_string()))
}
