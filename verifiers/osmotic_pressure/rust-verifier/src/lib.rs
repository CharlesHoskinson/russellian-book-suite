#![deny(clippy::all)]
use napi_derive::napi;

mod axioms;
mod ir;
mod smt;

#[cfg(feature = "eqsat")]
mod eqsat;

#[cfg(feature = "kg")]
mod kg;

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
