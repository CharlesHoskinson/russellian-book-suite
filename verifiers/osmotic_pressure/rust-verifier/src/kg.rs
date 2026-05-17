// PLACEHOLDER: this stub kg.rs ships with the scaffold.
// `npm run codegen-kg` overwrites this file when rules/booklogic/queries.edn
// declares defquery forms. DO NOT edit by hand; edit queries.edn instead.

use crate::ir::{Claim, GraphSummary, Error};

#[cfg(feature = "kg")]
pub fn ingest_and_summarize(claims: &[Claim]) -> Result<GraphSummary, Error> {
    // No queries declared: return an empty summary.
    Ok(GraphSummary { claim_count: claims.len(), contradictions: vec![] })
}

#[cfg(not(feature = "kg"))]
pub fn ingest_and_summarize(claims: &[Claim]) -> Result<GraphSummary, Error> {
    Ok(GraphSummary { claim_count: claims.len(), contradictions: vec![] })
}
