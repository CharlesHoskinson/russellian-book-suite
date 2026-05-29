//! Equality-saturation backend (egg-rs 0.10) for BookLogic.
//!
//! REQ-EQSAT-040: live `egg::Runner` integration replacing the prior stub.
//! REQ-EQSAT-041, 042: canonicalise expressions via `egg::Extractor::new(_, AstSize)`.
//! REQ-EQSAT-043: `prove_equiv` powers `defconstraint :backend :egg`.
//! REQ-EQSAT-044: saturation budget honours `VERIFIER_EQSAT_BUDGET` (default 10_000 nodes).
//!
//! The BookLogic language is intentionally small: arithmetic, predicate
//! application, and symbolic atoms. The codegen-emitted Rust calls
//! `crate::eqsat::prove_equiv(...)` to discharge `:egg`-backed
//! constraints; that result is wrapped in a Z3 boolean tracker on the
//! Z3 side so unsat-core reporting still works.

use egg::{AstSize, Extractor, Id, RecExpr, Rewrite, Runner, Symbol, define_language, rewrite};

define_language! {
    pub enum BookLogic {
        // Constants
        Num(i64),
        // Predicate application: (predicate :pred-name :subject)
        "predicate" = Predicate([Id; 2]),
        // Arithmetic
        "+" = Add([Id; 2]),
        "*" = Mul([Id; 2]),
        "-" = Sub([Id; 2]),
        "/" = Div([Id; 2]),
        // Symbolic head (predicate names, subjects, variables)
        Symbol(Symbol),
    }
}

/// Default node-count budget for saturation. Overridable via
/// `VERIFIER_EQSAT_BUDGET` per REQ-EQSAT-044.
pub const DEFAULT_BUDGET_NODES: usize = 10_000;

/// Read the node-count budget from `VERIFIER_EQSAT_BUDGET`, falling
/// back to `DEFAULT_BUDGET_NODES`.
pub fn budget_from_env() -> usize {
    std::env::var("VERIFIER_EQSAT_BUDGET")
        .ok()
        .and_then(|s| s.parse::<usize>().ok())
        .unwrap_or(DEFAULT_BUDGET_NODES)
}

/// Default rewrite set: commutativity of `+` / `*` and associativity of
/// `+`. Sufficient to canonicalise the v0.4 fixture surface.
pub fn make_rewrites() -> Vec<Rewrite<BookLogic, ()>> {
    vec![
        rewrite!("commute-add"; "(+ ?a ?b)" => "(+ ?b ?a)"),
        rewrite!("commute-mul"; "(* ?a ?b)" => "(* ?b ?a)"),
        rewrite!("assoc-add";  "(+ ?a (+ ?b ?c))" => "(+ (+ ?a ?b) ?c)"),
    ]
}

/// Saturate `input` against `make_rewrites()` and extract the
/// cost-minimal canonical form via `AstSize`. `budget_nodes` caps the
/// runner's `with_node_limit` so divergent rewrite sets terminate.
pub fn canonicalize(input: &str, budget_nodes: usize) -> Result<RecExpr<BookLogic>, String> {
    let expr: RecExpr<BookLogic> = input
        .parse()
        .map_err(|e| format!("parse RecExpr: {e}"))?;
    let runner = Runner::default()
        .with_node_limit(budget_nodes)
        .with_expr(&expr)
        .run(&make_rewrites());
    let extractor = Extractor::new(&runner.egraph, AstSize);
    let (_cost, best) = extractor.find_best(runner.roots[0]);
    Ok(best)
}

/// Result of an `:egg`-backed equivalence proof. `Proved` means egg
/// observed `lhs` and `rhs` in the same e-class within budget;
/// `NotProved` means the runner stopped (any `StopReason`) without
/// merging them. `prove_equiv` does not currently emit `Disproved`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ProofResult {
    Proved,
    NotProved,
}

/// Prove that `lhs` and `rhs` are equivalent under `rewrites`. Used by
/// codegen for `defconstraint :backend :egg`.
pub fn prove_equiv(lhs: &str, rhs: &str, rewrites: &[Rewrite<BookLogic, ()>]) -> ProofResult {
    let lhs_expr: RecExpr<BookLogic> = match lhs.parse() {
        Ok(e) => e,
        Err(_) => return ProofResult::NotProved,
    };
    let rhs_expr: RecExpr<BookLogic> = match rhs.parse() {
        Ok(e) => e,
        Err(_) => return ProofResult::NotProved,
    };
    let runner = Runner::default()
        .with_node_limit(budget_from_env())
        .with_expr(&lhs_expr)
        .with_expr(&rhs_expr)
        .run(rewrites);
    let l_root = runner.egraph.find(runner.roots[0]);
    let r_root = runner.egraph.find(runner.roots[1]);
    if l_root == r_root {
        ProofResult::Proved
    } else {
        ProofResult::NotProved
    }
}

/// Back-compat entry point exposed via napi. Kept so the existing JS
/// `saturate(termsEdn, rulesEdn)` shim keeps compiling. The real work
/// happens in `canonicalize` / `prove_equiv`; this returns a JSON
/// summary of the canonical form for the supplied terms.
pub fn saturate(terms_edn: &str, _rules_edn: &str) -> Result<String, String> {
    // The legacy shim takes an EDN string; for v0.4 we parse it as a
    // single RecExpr in s-expression form and surface the canonical
    // form. EDN-to-s-expression translation is a Phase-I concern.
    let best = canonicalize(terms_edn, budget_from_env())?;
    Ok(format!(
        "{{\"cost\":{},\"form\":\"{}\"}}",
        best.as_ref().len(),
        best
    ))
}
