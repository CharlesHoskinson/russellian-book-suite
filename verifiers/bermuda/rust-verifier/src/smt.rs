//! SMT verification entry point.
//!
//! Walk the atoms parsed by `ir::parse_formulas`. For each typed
//! `:expression` atom carrying `:predicate`+`:subject`+`:value`, bind
//! the value as an equality on `{predicate}_{subject}` and assert it
//! against a Z3 solver. Context/opaque atoms are skipped.
//!
//! As of Phase J (REQ-PERF-040..043) the entry point partitions atoms
//! by their `:subject` keyword and runs ONE Z3 solver per partition,
//! plus a final shared partition for cross-subject constraints. The
//! single-solver path that used to live here is now reachable via
//! `crate::axioms::assert_axioms` (the backward-compat aggregator) and
//! is no longer used by `check_all`.

use crate::ir::{Atom, ClaimId, Error, Verdict};

#[cfg(feature = "smt")]
use std::collections::BTreeMap;
#[cfg(feature = "smt")]
use std::str::FromStr as _;
#[cfg(feature = "smt")]
use z3::{
    Params, SatResult, Solver,
    ast::{Bool, Int, Real, String as Z3String},
};

/// REQ-DSL-054: check that a value's shape is compatible with the
/// declared return-sort of its predicate. Returns `Err(Error::Smt(...))`
/// when `is_vector` is true and the value is a scalar (Int/Real/Bool/Str);
/// returns `Ok(())` otherwise.
///
/// Extracted from `check_all` so cargo tests can drive the path with a
/// synthetic `is_vector` closure (the codegen-emitted
/// `axioms::predicate_is_vector` returns false for every name when no
/// vector predicate has been declared in `booklogic-schema.edn`).
#[cfg(feature = "smt")]
pub fn check_value_sort_compat(
    var_name: &str,
    atom_id: &str,
    value: &edn_rs::Edn,
    is_vector: impl Fn(&str) -> bool,
) -> Result<(), Error> {
    use edn_rs::Edn;
    if !is_vector(var_name) {
        return Ok(());
    }
    if matches!(value, Edn::Vector(_) | Edn::Set(_)) {
        return Ok(());
    }
    let value_shape = match value {
        Edn::Int(n)    => format!("scalar Int({n})"),
        Edn::Double(_) => format!("scalar Real({})", value.to_float().unwrap_or(0.0)),
        Edn::Str(s)    => format!("scalar String({s:?})"),
        Edn::Bool(b)   => format!("scalar Bool({b})"),
        other          => format!("{other:?}"),
    };
    Err(Error::Smt(format!(
        "sort mismatch: predicate {var_name:?} declared as \
         [:vector <T>] in booklogic-schema.edn, but atom \
         {atom_id:?} bound value as {value_shape}",
    )))
}

#[cfg(feature = "smt")]
const SHARED_BUCKET: &str = "_shared";

#[cfg(feature = "smt")]
struct PartitionVerdict {
    subject:        String,
    status:         &'static str,
    core:           Vec<ClaimId>,
    reason_unknown: String,
}

#[cfg(feature = "smt")]
pub fn check_all(formulas: &[(ClaimId, Atom)]) -> Result<Verdict, Error> {
    let timeout_ms: u32 = std::env::var("VERIFIER_SOLVER_TIMEOUT_MS")
        .ok()
        .and_then(|s| s.parse().ok())
        .unwrap_or(30_000);

    let parallelism: usize = std::env::var("VERIFIER_SOLVER_PARALLELISM")
        .ok()
        .and_then(|s| s.parse().ok())
        .filter(|n: &usize| *n > 0)
        .unwrap_or(1);

    let mut per_subject: BTreeMap<String, Vec<(ClaimId, Atom)>> = BTreeMap::new();
    for (id, atom) in formulas {
        let subject = match atom_subject(atom) {
            Some(s) => s,
            None    => SHARED_BUCKET.to_string(),
        };
        per_subject.entry(subject).or_default().push((id.clone(), atom.clone()));
    }

    let mut partition_inputs: Vec<(String, Vec<(ClaimId, Atom)>)> = per_subject
        .into_iter()
        .filter(|(k, _)| k != SHARED_BUCKET)
        .collect();
    let known_subjects: Vec<String> = crate::axioms::axioms_subjects()
        .iter()
        .map(|s| (*s).to_string())
        .collect();
    let seen: std::collections::BTreeSet<String> =
        partition_inputs.iter().map(|(k, _)| k.clone()).collect();
    for subject in known_subjects {
        if !seen.contains(&subject) {
            partition_inputs.push((subject, Vec::new()));
        }
    }
    partition_inputs.sort_by(|a, b| a.0.cmp(&b.0));

    let per_partition_verdicts: Vec<PartitionVerdict> = if parallelism > 1 {
        let pool = rayon::ThreadPoolBuilder::new()
            .num_threads(parallelism)
            .build()
            .map_err(|e| Error::Smt(format!("rayon pool: {e}")))?;
        pool.install(|| {
            use rayon::prelude::*;
            partition_inputs
                .par_iter()
                .map(|(subject, atoms)| {
                    solve_partition(subject, atoms, timeout_ms)
                })
                .collect::<Result<Vec<_>, _>>()
        })?
    } else {
        let mut out = Vec::with_capacity(partition_inputs.len());
        for (subject, atoms) in &partition_inputs {
            out.push(solve_partition(subject, atoms, timeout_ms)?);
        }
        out
    };

    let shared_atoms: Vec<(ClaimId, Atom)> = Vec::new();
    let shared_verdict = solve_shared_partition(&shared_atoms, timeout_ms)?;

    Ok(merge_verdicts(&per_partition_verdicts, &shared_verdict))
}

#[cfg(feature = "smt")]
fn solve_partition(
    subject:    &str,
    atoms:      &[(ClaimId, Atom)],
    timeout_ms: u32,
) -> Result<PartitionVerdict, Error> {
    let solver = Solver::new();
    let mut params = Params::new();
    params.set_u32("timeout", timeout_ms);
    solver.set_params(&params);

    crate::axioms::axioms_for_subject(&solver, subject);
    let tracker_ids = bind_atoms(&solver, atoms)?;

    Ok(collect_partition_verdict(&solver, subject, &tracker_ids))
}

#[cfg(feature = "smt")]
fn solve_shared_partition(
    atoms:      &[(ClaimId, Atom)],
    timeout_ms: u32,
) -> Result<PartitionVerdict, Error> {
    let solver = Solver::new();
    let mut params = Params::new();
    params.set_u32("timeout", timeout_ms);
    solver.set_params(&params);

    crate::axioms::axioms_shared(&solver);
    let tracker_ids = bind_atoms(&solver, atoms)?;

    Ok(collect_partition_verdict(&solver, SHARED_BUCKET, &tracker_ids))
}

#[cfg(feature = "smt")]
fn collect_partition_verdict(
    solver:      &Solver,
    subject:     &str,
    tracker_ids: &[ClaimId],
) -> PartitionVerdict {
    match solver.check() {
        SatResult::Sat => PartitionVerdict {
            subject:        subject.to_string(),
            status:         "sat",
            core:           Vec::new(),
            reason_unknown: String::new(),
        },
        SatResult::Unsat => {
            let core_ids: Vec<ClaimId> = solver
                .get_unsat_core()
                .iter()
                .map(|b| format!("{b}"))
                .map(|s| s.trim_matches('|').to_string())
                .filter(|s| tracker_ids.iter().any(|tid| tid == s))
                .collect();
            PartitionVerdict {
                subject:        subject.to_string(),
                status:         "unsat",
                core:           core_ids,
                reason_unknown: String::new(),
            }
        }
        SatResult::Unknown => PartitionVerdict {
            subject:        subject.to_string(),
            status:         "unknown",
            core:           Vec::new(),
            reason_unknown: solver.get_reason_unknown().unwrap_or_default(),
        },
    }
}

#[cfg(feature = "smt")]
fn bind_atoms(
    solver: &Solver,
    atoms:  &[(ClaimId, Atom)],
) -> Result<Vec<ClaimId>, Error> {
    use edn_rs::Edn;
    let mut tracker_ids: Vec<ClaimId> = Vec::with_capacity(atoms.len());

    for (id, atom) in atoms {
        let kind = match atom.get(":kind") {
            Some(Edn::Key(k)) => k.clone(),
            Some(Edn::Str(s)) => s.clone(),
            _ => "".to_string(),
        };
        if kind != ":expression" {
            continue;
        }
        let predicate = match atom.get(":predicate") {
            Some(Edn::Key(k)) => k.clone(),
            _ => continue,
        };
        let subject = match atom.get(":subject") {
            Some(Edn::Key(k)) => k.clone(),
            _ => continue,
        };
        let var_name = crate::var_name::canonical_var_name(&predicate, &subject);
        let tracker = Bool::new_const(id.as_str());

        let value = match atom.get(":value") {
            Some(v) => v,
            None => continue,
        };

        // REQ-DSL-054: fail loudly when an atom binds a scalar value to
        // a predicate the schema declared as `[:vector T]` / `[:set T]`.
        check_value_sort_compat(
            var_name.as_str(),
            id.as_str(),
            value,
            crate::axioms::predicate_is_vector,
        )?;

        let assertion: Bool = match value {
            Edn::Int(n) => {
                let z3_var = Int::new_const(var_name.as_str());
                z3_var.eq(&Int::from_i64(*n))
            }
            Edn::Double(_) => {
                let v = value.to_float().unwrap_or(0.0);
                let z3_var = Real::new_const(var_name.as_str());
                let numerator = (v * 1_000_000.0) as i64;
                z3_var.eq(&Real::from_rational(numerator, 1_000_000))
            }
            Edn::Str(s) => {
                let z3_var = Z3String::new_const(var_name.as_str());
                let lit = Z3String::from_str(s)
                    .map_err(|_| Error::Smt(format!("invalid string literal: {s:?}")))?;
                z3_var.eq(&lit)
            }
            Edn::Bool(b) => {
                let z3_var = Bool::new_const(var_name.as_str());
                z3_var.eq(&Bool::from_bool(*b))
            }
            _ => continue,
        };
        solver.assert_and_track(&assertion, &tracker);
        tracker_ids.push(id.clone());
    }
    Ok(tracker_ids)
}

#[cfg(feature = "smt")]
fn atom_subject(atom: &Atom) -> Option<String> {
    use edn_rs::Edn;
    match atom.get(":subject") {
        Some(Edn::Key(k)) => Some(k.trim_start_matches(':').to_string()),
        Some(Edn::Str(s)) => Some(s.trim_start_matches(':').to_string()),
        _ => None,
    }
}

#[cfg(feature = "smt")]
fn merge_verdicts(
    per_subject: &[PartitionVerdict],
    shared:      &PartitionVerdict,
) -> Verdict {
    let all: Vec<&PartitionVerdict> = per_subject.iter().chain(std::iter::once(shared)).collect();

    let unsat_subjects: Vec<&str> = all
        .iter()
        .filter(|v| v.status == "unsat")
        .map(|v| v.subject.as_str())
        .collect();
    if !unsat_subjects.is_empty() {
        let mut core: Vec<ClaimId> = Vec::new();
        for v in &all {
            if v.status == "unsat" {
                core.extend(v.core.iter().cloned());
            }
        }
        return Verdict {
            status: "unsat".into(),
            core,
            explanation: format!(
                "Z3 reports unsat in subject(s): {}",
                unsat_subjects.join(", "),
            ),
            ..Default::default()
        };
    }

    let unknown_subjects: Vec<(String, String)> = all
        .iter()
        .filter(|v| v.status == "unknown")
        .map(|v| (v.subject.clone(), v.reason_unknown.clone()))
        .collect();
    if !unknown_subjects.is_empty() {
        let detail = unknown_subjects
            .iter()
            .map(|(s, r)| if r.is_empty() { s.clone() } else { format!("{s} ({r})") })
            .collect::<Vec<_>>()
            .join(", ");
        return Verdict {
            status: "unknown".into(),
            core: Vec::new(),
            explanation: format!("Z3 reports unknown in subject(s): {detail}"),
            ..Default::default()
        };
    }

    Verdict {
        status: "sat".into(),
        core: Vec::new(),
        ..Default::default()
    }
}

#[cfg(not(feature = "smt"))]
pub fn check_all(_formulas: &[(ClaimId, Atom)]) -> Result<Verdict, Error> {
    Err(Error::Smt("compiled without `smt` feature".into()))
}
