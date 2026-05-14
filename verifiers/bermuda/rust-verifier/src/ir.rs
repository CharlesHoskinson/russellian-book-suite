use serde::{Deserialize, Serialize};
use thiserror::Error;

#[derive(Debug, Error)]
pub enum Error {
    #[error("parse: {0}")]
    Parse(String),
    #[error("not a bool formula: {0}")]
    NotBoolFormula(String),
}

pub type ClaimId = String;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Formula {
    // Filled in per project. The scaffold ships an opaque value; users replace
    // it with their own Formula AST in this file.
    pub raw: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct Verdict {
    pub status: String,
    #[serde(default)]
    pub verified: Vec<Claim>,
    #[serde(default)]
    pub core: Vec<ClaimId>,
    #[serde(default)]
    pub proofs: Vec<serde_json::Value>,
    #[serde(default)]
    pub graph_summary: Option<GraphSummary>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct GraphSummary {
    pub claim_count: usize,
    pub contradictions: Vec<(String, String)>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct Claim {
    pub id: ClaimId,
    pub source: String,
}

pub fn parse_formulas(_edn: &str) -> Result<Vec<(ClaimId, Formula)>, Error> {
    // TODO: parse EDN here using edn-rs. The scaffold returns empty.
    Ok(Vec::new())
}

pub fn emit_verdict(v: &Verdict) -> String {
    serde_json::to_string(v).unwrap_or_else(|_| "{\"status\":\"unknown\"}".to_string())
}
