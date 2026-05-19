//! Intermediate representation between Python ingest/extract and the SMT
//! solver. The Python helpers write real EDN files with shape:
//!
//! {:version 1
//!  :atoms [
//!    {:kind :expression :id "clm-..." :predicate :x :subject :Y :value 9 ...}
//!    {:kind :symbol     :id "..."     :name :CONTEXT :context true ...}
//!  ]}
//!
//! `parse_formulas` returns one `(ClaimId, edn_rs::Edn)` per atom;
//! `smt::check_all` does typed dispatch on the Edn value.
//!
//! `emit_verdict` produces hand-rolled EDN so the CLJS bridge receives real
//! keywords on the return trip.

use serde::{Deserialize, Serialize};
use thiserror::Error;

#[derive(Debug, Error)]
pub enum Error {
    #[error("parse: {0}")]
    Parse(String),
    #[error("smt: {0}")]
    Smt(String),
    #[error("kg: {0}")]
    Kg(String),
}

pub type ClaimId = String;

/// An atom from the Python ingester / prose extractor.
///
/// Represented as a raw `edn_rs::Edn` so the SMT walk in `smt.rs`
/// can dispatch on `:kind` and `:predicate` without committing to a fixed
/// Rust enum (which would need updates every time the predicate map grows).
pub type Atom = edn_rs::Edn;

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct Verdict {
    pub status: String,
    #[serde(default)]
    pub verified: Vec<Claim>,
    #[serde(default)]
    pub core: Vec<ClaimId>,
    #[serde(default)]
    pub explanation: String,
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

/// Parse the EDN atomspace into a vector of (id, atom) pairs.
pub fn parse_formulas(edn: &str) -> Result<Vec<(ClaimId, Atom)>, Error> {
    use edn_rs::{Edn, EdnError};
    let parsed: Edn = edn
        .parse::<Edn>()
        .map_err(|e: EdnError| Error::Parse(e.to_string()))?;
    let atoms = match parsed.get(":atoms") {
        Some(Edn::Vector(v)) => v.clone().to_vec(),
        Some(_) | None => return Err(Error::Parse("missing or non-vector :atoms".into())),
    };
    let mut out = Vec::with_capacity(atoms.len());
    for a in atoms {
        let id = match a.get(":id") {
            Some(Edn::Str(s)) => s.clone(),
            _ => "?".to_string(),
        };
        out.push((id, a));
    }
    Ok(out)
}

/// Emit the verdict as an EDN map so the CLJS bridge receives real keywords.
pub fn emit_verdict(v: &Verdict) -> String {
    let mut out = String::from("{:status :");
    out.push_str(&v.status);
    out.push_str(" :core [");
    for (i, claim_id) in v.core.iter().enumerate() {
        if i > 0 {
            out.push(' ');
        }
        out.push('"');
        out.push_str(&edn_escape(claim_id));
        out.push('"');
    }
    out.push_str("] :explanation \"");
    out.push_str(&edn_escape(&v.explanation));
    out.push_str("\"}");
    out
}

fn edn_escape(s: &str) -> String {
    s.replace('\\', "\\\\").replace('"', "\\\"")
}
