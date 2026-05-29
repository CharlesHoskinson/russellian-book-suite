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
    /// Cozo `defquery` outcomes (REQ-DATALOG-042). Each entry names a
    /// query that ran during the smoke step; `rows` is the number of
    /// result rows; `sample` is an optional `Debug`-rendered first
    /// row (or `<timeout>` when the timeout fired).
    #[serde(default)]
    pub queries: Vec<QueryResult>,
    /// `defconstraint :backend :cozo` defects (REQ-DATALOG-041).
    /// Each entry names a constraint that produced at least one
    /// witness row; `rows` is the violation count.
    #[serde(default)]
    pub cozo_defects: Vec<QueryResult>,
    /// `defconstraint :scope :corpus` defects (REQ-CORPUS-053).
    /// Each entry names a corpus-scope constraint that returned
    /// `:unsat` on the corpus solver and the subjects whose atoms
    /// participated in the unsat core.
    #[serde(default)]
    pub corpus_defects: Vec<CorpusDefect>,
    /// Top-k similar claims per defect (REQ-RETRIEVAL-044). Each
    /// entry pairs a defect's claim id with the top-3 most-similar
    /// OTHER claims as `(claim_id, cosine_score)` pairs. Populated by
    /// the Python `verdict_to_qa` layer from the
    /// `work/semantic-index.npz` produced by `make index-semantic`.
    /// Empty when the .npz is missing — semantic retrieval is
    /// advisory, not gating.
    #[serde(default)]
    pub semantic_neighbours: Vec<NeighbourEntry>,
}

/// REQ-CORPUS-053: per-defect record for `:scope :corpus` constraints
/// that returned `:unsat` on the corpus solver. `conflicting_subjects`
/// names every subject whose atoms participated in the unsat core;
/// `explanation` is a human-readable rendering suitable for
/// `verdict_to_qa.py` to lift into a QA defect.
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct CorpusDefect {
    pub id: String,
    #[serde(default)]
    pub conflicting_subjects: Vec<String>,
    #[serde(default)]
    pub explanation: String,
}

/// Top-k semantic neighbours attached to a defect (REQ-RETRIEVAL-044).
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct NeighbourEntry {
    pub defect_claim_id: String,
    /// `(other_claim_id, cosine_score)` pairs sorted descending by
    /// score; ties broken lexicographically by `other_claim_id`.
    pub top_k: Vec<(String, f32)>,
}

/// Per-query summary recorded on the verdict. `sample` is `Some` for
/// non-empty result sets and `Some("<timeout>")` when the per-query
/// timeout fired.
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct QueryResult {
    pub name: String,
    pub rows: usize,
    #[serde(default)]
    pub sample: Option<String>,
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
    out.push_str("\" :queries [");
    for (i, qr) in v.queries.iter().enumerate() {
        if i > 0 {
            out.push(' ');
        }
        out.push_str("{:name \"");
        out.push_str(&edn_escape(&qr.name));
        out.push_str("\" :rows ");
        out.push_str(&qr.rows.to_string());
        out.push('}');
    }
    out.push_str("] :cozo-defects [");
    for (i, qr) in v.cozo_defects.iter().enumerate() {
        if i > 0 {
            out.push(' ');
        }
        out.push_str("{:name \"");
        out.push_str(&edn_escape(&qr.name));
        out.push_str("\" :rows ");
        out.push_str(&qr.rows.to_string());
        out.push('}');
    }
    // REQ-CORPUS-053: serialise corpus-scope defects.
    out.push_str("] :corpus-defects [");
    for (i, cd) in v.corpus_defects.iter().enumerate() {
        if i > 0 {
            out.push(' ');
        }
        out.push_str("{:constraint-id \"");
        out.push_str(&edn_escape(&cd.id));
        out.push_str("\" :subjects [");
        for (j, s) in cd.conflicting_subjects.iter().enumerate() {
            if j > 0 {
                out.push(' ');
            }
            out.push('"');
            out.push_str(&edn_escape(s));
            out.push('"');
        }
        out.push_str("] :explanation \"");
        out.push_str(&edn_escape(&cd.explanation));
        out.push_str("\"}");
    }
    // Serialise the kg graph summary so the contradiction data lib.rs
    // computes (claim count + contradiction pairs) reaches the cljs
    // consumer instead of being silently dropped on the EDN return trip.
    if let Some(gs) = &v.graph_summary {
        out.push_str("] :graph-summary {:claim-count ");
        out.push_str(&gs.claim_count.to_string());
        out.push_str(" :contradictions [");
        for (i, (claim_id, reason)) in gs.contradictions.iter().enumerate() {
            if i > 0 {
                out.push(' ');
            }
            out.push_str("{:claim-id \"");
            out.push_str(&edn_escape(claim_id));
            out.push_str("\" :reason \"");
            out.push_str(&edn_escape(reason));
            out.push_str("\"}");
        }
        out.push_str("]}}");
    } else {
        out.push_str("]}");
    }
    out
}

fn edn_escape(s: &str) -> String {
    s.replace('\\', "\\\\").replace('"', "\\\"")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn emit_verdict_serialises_graph_summary_when_present() {
        let v = Verdict {
            status: "sat".into(),
            graph_summary: Some(GraphSummary {
                claim_count: 3,
                contradictions: vec![(
                    "C001".to_string(),
                    "posterior-floor/warning/Q001".to_string(),
                )],
            }),
            ..Default::default()
        };
        let edn = emit_verdict(&v);
        assert!(edn.contains(":graph-summary"), "got {edn}");
        assert!(edn.contains(":claim-count 3"), "got {edn}");
        assert!(edn.contains("C001"), "got {edn}");
        assert!(edn.contains("posterior-floor/warning/Q001"), "got {edn}");
    }

    #[test]
    fn emit_verdict_omits_graph_summary_when_absent() {
        let v = Verdict {
            status: "sat".into(),
            ..Default::default()
        };
        let edn = emit_verdict(&v);
        assert!(!edn.contains(":graph-summary"), "got {edn}");
        assert!(edn.ends_with("]}"), "got {edn}");
    }
}
