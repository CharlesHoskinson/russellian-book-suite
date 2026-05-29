"""REQ-INDUCE-050..057: candidate-generation orchestrator.

Main loop for the Tier 6 candidate-generation stage. Mirrors the CLJS
entry point ``induce_theory.cljs`` line-for-line so the framework's
first nbb-driven Python-equivalent stays in sync.

Pipeline:
  1. Load schema (rules/booklogic-schema.edn) and atomspace
     (rules/atomspace.edn).
  2. Run Horn-body mining over the atomspace.
  3. Run Popper-style typed search over the schema.
  4. For each Phase Q semantic cluster, invoke the LLM proposer (Phase V
     when available, else the StubProposer fallback).
  5. Dedup by canonical S-expr form (REQ-INDUCE-052).
  6. Rank by semantic coherence when Phase Q is available
     (REQ-INDUCE-053).
  7. Persist the queue to work/induction/candidates.edn with rejection
     reasons retained (REQ-INDUCE-055).

The budget tracker (REQ-INDUCE-056) halts the LLM source when
``NEUROSYM_INDUCTION_BUDGET_USD`` is exceeded; Horn-body and Popper
sources are unaffected.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from scripts import _induction_sources as sources
from scripts import _induction_validator as _validator
from scripts._edn_reader import Keyword
from scripts._io import read_edn_file, write_edn_file


# ---------------------------------------------------------------------------
# Schema + atomspace loading
# ---------------------------------------------------------------------------


def load_schema(project_root: Path) -> dict[str, Any]:
    schema_path = project_root / "rules" / "booklogic-schema.edn"
    if not schema_path.exists():
        return {Keyword("version"): 1, Keyword("predicates"): {}, Keyword("sorts"): []}
    return read_edn_file(schema_path)


def load_atoms(project_root: Path) -> list[dict[str, Any]]:
    atoms_path = project_root / "rules" / "atomspace.edn"
    if not atoms_path.exists():
        return []
    data = read_edn_file(atoms_path)
    raw = data.get(Keyword("atoms"), [])
    out: list[dict[str, Any]] = []
    for a in raw:
        pred = a.get(Keyword("predicate"))
        subj = a.get(Keyword("subject"))
        out.append(
            {
                "claim_id": a.get(Keyword("claim-id")),
                "document": a.get(Keyword("document")),
                "predicate": pred.name if isinstance(pred, Keyword) else str(pred),
                "subject": subj.name if isinstance(subj, Keyword) else str(subj),
                "value": a.get(Keyword("value")),
            }
        )
    return out


# ---------------------------------------------------------------------------
# Phase Q semantic-index probe (REQ-INDUCE-053)
# ---------------------------------------------------------------------------


def _try_load_semantic_index(project_root: Path) -> Optional[Any]:
    """REQ-INDUCE-053: probe for Phase Q's persisted SemanticIndex.

    Returns the loaded index when available; ``None`` when absent
    (graceful degradation — ranking falls back to insertion order).
    """
    cache_path = project_root / "work" / "semantic-index.npz"
    if not cache_path.exists():
        return None
    try:
        from scripts._semantic_index import SemanticIndex  # type: ignore

        idx = SemanticIndex(cache_path=cache_path)
        idx.load()
        if idx.count() == 0:
            return None
        return _CosineWrapper(idx)
    except Exception:
        return None


class _CosineWrapper:
    """Adapt ``SemanticIndex`` to the ranking helper's ``cosine`` API."""

    def __init__(self, idx: Any) -> None:
        self._idx = idx
        try:
            self._ids = list(idx._claim_ids)  # type: ignore[attr-defined]
            self._embs = list(idx._embeddings)  # type: ignore[attr-defined]
        except Exception:
            self._ids = []
            self._embs = []

    def cosine(self, a: str, b: str) -> float:
        if a == b:
            return 1.0
        if a not in self._ids or b not in self._ids:
            return 0.0
        import numpy as np

        i = self._ids.index(a)
        j = self._ids.index(b)
        return float(np.dot(self._embs[i], self._embs[j]))


# ---------------------------------------------------------------------------
# Cluster discovery
# ---------------------------------------------------------------------------


def _atom_clusters(atoms: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    """Group atoms by predicate; each predicate is one cluster.

    REQ-INDUCE-051(c): the LLM proposer is invoked once per cluster.
    Tier 7 will replace this with Phase Q-driven embedding clusters;
    for Tier 6 a predicate-grouped cluster is the deterministic
    minimum.
    """
    by_pred: dict[str, list[dict[str, Any]]] = {}
    for a in atoms:
        by_pred.setdefault(a["predicate"], []).append(a)
    return [by_pred[k] for k in sorted(by_pred.keys())]


# ---------------------------------------------------------------------------
# Held-out document folds (REQ-TEST-043)
# ---------------------------------------------------------------------------


def _build_document_folds(
    atoms: list[dict[str, Any]], n_folds: int = 5
) -> list[list[dict[str, Any]]]:
    """Partition the atomspace into per-document value maps split across
    folds for held-out validation.

    Each document becomes one flat dict ``predicate-name -> value`` (the
    shape ``validate_with_holdout`` evaluates a candidate's :assert
    against). Documents are assigned round-robin to ``n_folds`` folds so
    the split is deterministic. Returns ``[]`` when there are no
    documents (holdout is then skipped).
    """
    by_doc: dict[str, dict[str, Any]] = {}
    for a in atoms:
        doc = a.get("document")
        if doc is None:
            continue
        value = a.get("value")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            # Non-numeric predicate values cannot drive the comparator
            # evaluator; presence is recorded as 1 so existence-style
            # rules still see the predicate.
            value = 1
        by_doc.setdefault(doc, {})[a["predicate"]] = value
    docs = [by_doc[k] for k in sorted(by_doc.keys())]
    if not docs:
        return []
    n = max(1, min(n_folds, len(docs)))
    folds: list[list[dict[str, Any]]] = [[] for _ in range(n)]
    for i, doc in enumerate(docs):
        folds[i % n].append(doc)
    return [f for f in folds if f]


def _parse_candidate_edn(edn: Optional[str]):
    """Parse a candidate's raw EDN string into the reader's AST, or None
    when absent / unparseable."""
    if not edn:
        return None
    try:
        from scripts._edn_reader import read_edn

        return read_edn(edn)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def _candidate_to_edn(c: dict[str, Any], cid: str) -> dict[Any, Any]:
    return {
        Keyword("id"): cid,
        Keyword("canonical-form"): c["canonical_form"],
        Keyword("origin"): list(c.get("origin", [])),
        Keyword("cited-atoms"): list(c.get("cited_atoms", [])),
        Keyword("coherence"): c.get("coherence"),
        Keyword("support"): c.get("support"),
        Keyword("literal-count"): c.get("literal_count", 0),
        Keyword("status"): Keyword(c.get("status", "pending")),
        Keyword("rejection-reason"): (
            Keyword(c["rejection_reason"])
            if c.get("rejection_reason")
            else None
        ),
    }


def _read_budget_env() -> Optional[float]:
    """REQ-INDUCE-056: read NEUROSYM_INDUCTION_BUDGET_USD from the
    environment. Returns None when unset (no cap)."""
    raw = os.environ.get("NEUROSYM_INDUCTION_BUDGET_USD")
    if raw is None or raw == "":
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _persist_budget(project_root: Path, budget: sources.BudgetTracker) -> None:
    """REQ-INDUCE-056: log the run's final spend + halt status to
    work/induction/budget.json so callers can audit cost discipline."""
    out_dir = project_root / "work" / "induction"
    out_dir.mkdir(parents=True, exist_ok=True)
    data = {
        "limit_usd": budget.limit_usd,
        "spent_usd": budget.spent_usd,
        "llm_halted": bool(budget.halted),
    }
    (out_dir / "budget.json").write_text(
        json.dumps(data, indent=2), encoding="utf-8", newline="\n"
    )


def _persist_queue(
    project_root: Path,
    *,
    survivors: list[dict[str, Any]],
    rejected: list[dict[str, Any]],
    corpus_size: int,
) -> None:
    out_dir = project_root / "work" / "induction"
    out_dir.mkdir(parents=True, exist_ok=True)
    queue: list[dict[Any, Any]] = []
    for i, c in enumerate(survivors):
        queue.append(_candidate_to_edn(c, f"c-{i:03d}"))
    for j, c in enumerate(rejected):
        queue.append(_candidate_to_edn(c, f"r-{j:03d}"))
    payload = {
        Keyword("version"): 1,
        Keyword("generated-at"): datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        Keyword("corpus-size"): corpus_size,
        Keyword("candidates"): queue,
    }
    write_edn_file(out_dir / "candidates.edn", payload)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def run(project_root: Path) -> int:
    """Run the orchestrator end-to-end against ``project_root``.

    Returns 0 on success, non-zero on infrastructural error.
    """
    sources.reset_warnings()
    schema = load_schema(project_root)
    atoms = load_atoms(project_root)

    # Source 1 — Horn-body mining
    horn_cands = sources.horn_mine(atoms, schema)

    # Source 2 — Popper-style typed search
    popper_cands = sources.popper_search(schema)

    # Source 3 — LLM proposer (Phase V or Stub fallback) — budget-tracked
    budget = sources.BudgetTracker(limit_usd=_read_budget_env())
    llm_cands: list[dict[str, Any]] = []
    provider = sources.StubProposer()
    for cluster in _atom_clusters(atoms):
        if budget.halted:
            break
        cands = sources.llm_propose(
            schema=schema,
            cluster=cluster,
            provider=provider,
            budget=budget,
        )
        llm_cands.extend(cands)
        if budget.halted:
            break

    # Dedup with rejection logging (REQ-INDUCE-052, 055)
    all_cands = horn_cands + popper_cands + llm_cands
    survivors, rejected = sources.dedup_with_rejection_log(all_cands)

    # Grammar gate (REQ-INDUCE-040): the FIRST gate — every surviving
    # candidate is checked against the supported operator set, the
    # schema's predicates, and the circular-definition rule BEFORE any
    # solver call. Non-conforming forms are routed into rejected with the
    # grammar-fail tag rather than persisted as accepted.
    gate_kept: list[dict[str, Any]] = []
    for c in survivors:
        parsed = _parse_candidate_edn(c.get("edn"))
        result = (
            _validator.grammar_conforming(parsed, schema)
            if parsed is not None
            else _validator.GrammarResult(False, ":grammar-fail/non-edn")
        )
        if result.ok:
            gate_kept.append(c)
        else:
            entry = dict(c)
            entry["status"] = "rejected"
            # Store the grammar-fail tag without the leading colon to match
            # the EDN-keyword serialisation other rejection reasons use.
            entry["rejection_reason"] = (result.tag or ":grammar-fail").lstrip(":")
            rejected.append(entry)
    survivors = gate_kept

    # Held-out validation (REQ-TEST-043): reject candidates that fit the
    # corpus but fail a held-out document fold (memorisation defence).
    # Survivors whose :assert fails any fold are routed into rejected with
    # reason :memorization before persistence, rather than accepted.
    folds = _build_document_folds(atoms)
    if folds:
        kept: list[dict[str, Any]] = []
        for c in survivors:
            parsed = _parse_candidate_edn(c.get("edn"))
            result = (
                validate_with_holdout(parsed, folds) if parsed is not None
                else HoldoutResult(rejected=False)
            )
            if result.rejected:
                entry = dict(c)
                entry["status"] = "rejected"
                entry["rejection_reason"] = "memorization"
                rejected.append(entry)
            else:
                kept.append(c)
        survivors = kept

    # Rank by semantic coherence when Phase Q is available (REQ-INDUCE-053)
    sem_index = _try_load_semantic_index(project_root)
    survivors = sources.rank_by_semantic_coherence(survivors, sem_index)

    _persist_queue(
        project_root,
        survivors=survivors,
        rejected=rejected,
        corpus_size=len(atoms),
    )
    _persist_budget(project_root, budget)
    return 0


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: induce_theory <project-root>", file=sys.stderr)
        return 2
    return run(Path(argv[0]))


class HoldoutResult:
    """Outcome of a document-held-out validation pass."""

    def __init__(
        self,
        rejected: bool,
        reason: str | None = None,
        failing_folds: list[int] | None = None,
    ) -> None:
        self.rejected = rejected
        self.reason = reason
        self.failing_folds = failing_folds or []


def _extract_assert_form(candidate):
    """Pull the value following `:assert` from a parsed `defconstraint`
    form. The EDN reader yields a list whose elements alternate
    keyword/value after the rule name; scan the tail for `:assert`.

    Returns None when the candidate is not a defconstraint list or has
    no `:assert` option.
    """
    if not isinstance(candidate, list):
        return None
    items = list(candidate)
    for i, item in enumerate(items):
        if getattr(item, "name", None) == "assert" and i + 1 < len(items):
            return items[i + 1]
    return None


_COMPARATORS = {
    ">=": lambda a, b: a >= b,
    ">": lambda a, b: a > b,
    "<=": lambda a, b: a <= b,
    "<": lambda a, b: a < b,
    "=": lambda a, b: a == b,
    "~=": lambda a, b: a != b,
}


def _eval_assert(form, doc: dict):
    """Evaluate a parsed `:assert` form against one document dict.

    A document is a flat map predicate-name -> value. A predicate call
    `(:name ?d)` resolves to `doc[name]`; comparators (`>= > <= < = ~=`)
    and the boolean connectives `and`/`or`/`not` are evaluated
    structurally. Anything we cannot evaluate (unknown op, missing
    predicate value) is treated as unsatisfied so an un-interpretable
    rule never silently "passes".

    Returns a bool.
    """
    # Predicate call: (:name ?d) -> doc value (truthy-as-presence handled
    # by the caller via comparators).
    if isinstance(form, list) and form and isinstance(form[0], Keyword):
        return doc.get(form[0].name)

    if not isinstance(form, list) or not form:
        return bool(form)

    head = getattr(form[0], "name", str(form[0]))
    args = list(form[1:])

    if head in _COMPARATORS and len(args) == 2:
        left = _resolve_term(args[0], doc)
        right = _resolve_term(args[1], doc)
        if left is None or right is None:
            return False
        try:
            return _COMPARATORS[head](left, right)
        except TypeError:
            return False
    if head == "approx=" and len(args) >= 2:
        left = _resolve_term(args[0], doc)
        right = _resolve_term(args[1], doc)
        tol = 0.0
        for i, a in enumerate(args):
            if getattr(a, "name", None) == "tolerance" and i + 1 < len(args):
                tol = _resolve_term(args[i + 1], doc) or 0.0
        if left is None or right is None:
            return False
        try:
            return abs(left - right) <= tol
        except TypeError:
            return False
    if head == "and":
        return all(bool(_eval_assert(a, doc)) for a in args)
    if head == "or":
        return any(bool(_eval_assert(a, doc)) for a in args)
    if head == "not" and len(args) == 1:
        return not bool(_eval_assert(args[0], doc))
    if head in ("=>", "implies") and len(args) == 2:
        # Material implication, evaluated per document: a predicate-call
        # premise/conclusion is "present/true" when its value is truthy.
        premise = _eval_assert(args[0], doc)
        conclusion = _eval_assert(args[1], doc)
        return (not bool(premise)) or bool(conclusion)
    # Unknown / unsupported operator: cannot interpret -> unsatisfied.
    return False


def _resolve_term(term, doc: dict):
    """Resolve an argument term to a scalar: a predicate call resolves to
    the document's value; a number resolves to itself; anything else is
    None (un-resolvable)."""
    if isinstance(term, list) and term and isinstance(term[0], Keyword):
        return doc.get(term[0].name)
    if isinstance(term, (int, float)):
        return term
    return None


def validate_with_holdout(
    candidate, folds: list[list[dict]], threshold: float = 0.5
) -> HoldoutResult:
    """Document-held-out validation against the memorization-vs-induction
    failure mode.

    The candidate's `:assert` form is parsed and evaluated per document:
    for each fold, sat-rate is the fraction of documents that satisfy the
    candidate's own assertion. Folds whose sat-rate falls below
    `threshold` are reported as failing. If any fold fails, reject with
    `:memorization` — a rule that "works" only because it memorised the
    documents in the training fold cannot withstand a held-out fold drawn
    from the same corpus.

    The evaluator (`_eval_assert`) supports comparators and boolean
    connectives over predicate-call terms `(:name ?d)` resolved against
    the per-document value map. An un-interpretable rule evaluates as
    unsatisfied on every document, so a malformed candidate fails rather
    than silently passing.
    """
    assert_form = _extract_assert_form(candidate)
    failing: list[int] = []
    for idx, fold in enumerate(folds):
        if not fold:
            continue
        if assert_form is None:
            # No parseable assertion: cannot validate; treat as failing
            # so an un-interpretable candidate is rejected, not accepted.
            failing.append(idx)
            continue
        sat = sum(1 for doc in fold if _eval_assert(assert_form, doc)) / len(fold)
        if sat < threshold:
            failing.append(idx)
    if failing:
        return HoldoutResult(
            rejected=True, reason=":memorization", failing_folds=failing
        )
    return HoldoutResult(rejected=False)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))
