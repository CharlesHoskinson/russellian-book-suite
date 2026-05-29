"""REQ-INDUCE-050..057: candidate sources for theory induction.

Phase W of the Tier 6 theory-induction layer. Three candidate sources,
one uniform shape:

  candidate = {
    "id":              str,
    "canonical_form":  str,        # alpha-canonicalised S-expr key
    "edn":             str,        # raw EDN (defconstraint form)
    "cited_atoms":     list[str],  # claim/atom ids that motivated this candidate
    "origin":          list[Kw],   # union of source tags (horn-body | popper | llm)
    "support":         int | None, # Horn-body co-occurrence count when known
    "coherence":       float | None,
    "literal_count":   int,
    "status":          "pending" | "rejected",
    "rejection_reason": str | None,
  }

The orchestrator (`_induction_orchestrator`) calls these helpers and the
nbb-driven CLJS wrapper (`induce_theory.cljs`) mirrors the same logic
for production runs against a project root.
"""
from __future__ import annotations

import itertools
import os
import re
import statistics
import threading
from collections import Counter, defaultdict
from typing import Any, Iterable, Optional

from scripts._edn_reader import Keyword


# ---------------------------------------------------------------------------
# Source tags + per-source caps
# ---------------------------------------------------------------------------


HORN_BODY = Keyword("horn-body")
POPPER = Keyword("popper")
LLM = Keyword("llm")


_DEFAULT_CAP = 20


def per_source_cap() -> int:
    """Read ``NEUROSYM_INDUCTION_CANDIDATES_PER_SOURCE`` (default 20).

    REQ-INDUCE-051: per-source cap prevents any one source from
    saturating the queue. The env var is read fresh on every call so
    tests can flip it via ``monkeypatch.setenv``.
    """
    raw = os.environ.get("NEUROSYM_INDUCTION_CANDIDATES_PER_SOURCE")
    if raw is None or raw == "":
        return _DEFAULT_CAP
    try:
        return max(0, int(raw))
    except ValueError:
        return _DEFAULT_CAP


# ---------------------------------------------------------------------------
# Phase V conditional import
# ---------------------------------------------------------------------------


PHASE_V_AVAILABLE = False
_phase_v_propose = None
try:
    from scripts._induction_proposer import propose_constraint as _phase_v_propose  # type: ignore

    PHASE_V_AVAILABLE = True
except Exception:
    PHASE_V_AVAILABLE = False
    _phase_v_propose = None


# ---------------------------------------------------------------------------
# Warning buffer (thread-local so concurrent calls don't bleed)
# ---------------------------------------------------------------------------


_warnings_local = threading.local()


def _push_warning(w: dict[str, Any]) -> None:
    if not hasattr(_warnings_local, "buf"):
        _warnings_local.buf = []
    _warnings_local.buf.append(w)


def last_warnings() -> list[dict[str, Any]]:
    """Return and clear the per-thread warning buffer.

    Tests inspect this after running a source to assert the structured
    warning shape (REQ-INDUCE-054 small-corpus skip).
    """
    buf = list(getattr(_warnings_local, "buf", []))
    _warnings_local.buf = []
    return buf


def reset_warnings() -> None:
    _warnings_local.buf = []


# ---------------------------------------------------------------------------
# Canonical S-expression form (REQ-INDUCE-052)
# ---------------------------------------------------------------------------


_VAR_RE = re.compile(r"\?[A-Za-z_][A-Za-z0-9_-]*")


def canonical_constraint_form(edn: str) -> str:
    """Alpha-rename logic variables to a canonical sequence.

    First occurrence of ``?xxx`` becomes ``?v0``, the second distinct
    becomes ``?v1``, and so on. Whitespace is collapsed so syntactically
    different but structurally identical forms compare equal.

    This is the dedup key. Two candidates produced by different sources
    that share the same canonical_form collapse to one entry with the
    union of origin tags.
    """
    mapping: dict[str, str] = {}
    counter = itertools.count()

    def repl(match: re.Match[str]) -> str:
        name = match.group(0)
        if name not in mapping:
            mapping[name] = f"?v{next(counter)}"
        return mapping[name]

    renamed = _VAR_RE.sub(repl, edn)
    # Collapse whitespace runs to a single space.
    return re.sub(r"\s+", " ", renamed).strip()


# ---------------------------------------------------------------------------
# Source 1 — Horn-body mining
# ---------------------------------------------------------------------------


def horn_mine(atoms: list[dict[str, Any]], schema: dict[str, Any]) -> list[dict[str, Any]]:
    """REQ-INDUCE-051(a), 054: enumerate frequent predicate-pair
    co-occurrence patterns over the atomspace.

    Each surviving pair is wrapped in a ``defconstraint`` candidate
    template ``(=> (predicate-A ?d) (predicate-B ?d))``. The
    support count (number of documents in which both predicates appear)
    becomes the candidate's :support metadata.

    REQ-INDUCE-054: when the atomspace has fewer than 10 atoms, the
    source emits a structured warning and returns []. Popper + LLM
    still run downstream.
    """
    if len(atoms) < 10:
        _push_warning(
            {
                "warning": "corpus-too-small",
                "n": len(atoms),
                "threshold": 10,
                "source": "horn-body",
            }
        )
        return []

    # Group predicates by (document, subject) so pair-counting respects
    # the subject identity (R0(measles) and threshold(measles) co-occur;
    # R0(measles) and coverage(p1) do not — different subjects).
    by_key: dict[tuple[str, str], set[str]] = defaultdict(set)
    for a in atoms:
        doc = a["document"]
        subj = a["subject"]
        pred = a["predicate"]
        by_key[(doc, subj)].add(pred)

    pair_count: Counter[tuple[str, str]] = Counter()
    pair_atoms: dict[tuple[str, str], set[str]] = defaultdict(set)
    for (doc, subj), preds in by_key.items():
        for p1, p2 in itertools.combinations(sorted(preds), 2):
            pair_count[(p1, p2)] += 1
            for a in atoms:
                if (
                    a["document"] == doc
                    and a["subject"] == subj
                    and a["predicate"] in (p1, p2)
                ):
                    pair_atoms[(p1, p2)].add(a["claim_id"])

    cap = per_source_cap()
    sorted_pairs = pair_count.most_common()
    out: list[dict[str, Any]] = []
    for (p1, p2), support in sorted_pairs[:cap]:
        edn = (
            f"(defconstraint :induced/{p1}-{p2}\n"
            f"  :backend :z3\n"
            f"  :assert (=> (:{p1} ?d) (:{p2} ?d))\n"
            f"  :on-unsat {{:defect :D-induced-h :severity :advisory\n"
            f'             :message "Horn-body co-occurrence: {p1} → {p2}"}})'
        )
        out.append(
            {
                "id": f"horn-{p1}-{p2}",
                "canonical_form": canonical_constraint_form(edn),
                "edn": edn,
                "cited_atoms": sorted(pair_atoms[(p1, p2)]),
                "origin": [HORN_BODY],
                "support": support,
                "coherence": None,
                "literal_count": 2,
                "status": "pending",
                "rejection_reason": None,
            }
        )
    return out


# ---------------------------------------------------------------------------
# Source 2 — Popper-style typed search
# ---------------------------------------------------------------------------


def _schema_predicates(schema: dict[str, Any]) -> list[tuple[str, list[Keyword], Keyword]]:
    """Return [(name, arg-sorts, return)] tuples from a parsed schema.

    The schema is the EDN dict at ``rules/booklogic-schema.edn``; the
    reader yields Keyword keys and Keyword name elements.
    """
    preds = schema.get(Keyword("predicates"), {})
    out: list[tuple[str, list[Keyword], Keyword]] = []
    for name_kw, sig in preds.items():
        name = name_kw.name if isinstance(name_kw, Keyword) else str(name_kw)
        arg_sorts = sig.get(Keyword("arg-sorts"), []) or []
        ret = sig.get(Keyword("return"))
        out.append((name, list(arg_sorts), ret))
    return out


def _return_inner_sort(ret: Any) -> Any:
    """Strip a one-layer container wrapper from a return sort, mirroring the
    cljs booklogic ``return-inner-sort``. A scalar keyword passes through; a
    ``[:vector T]`` / ``[:set T]`` container yields its inner sort T."""
    if (
        isinstance(ret, (list, tuple))
        and len(ret) == 2
        and ret[0] in (Keyword("vector"), Keyword("set"))
    ):
        return ret[1]
    return ret


def popper_search(schema: dict[str, Any]) -> list[dict[str, Any]]:
    """REQ-INDUCE-051(b): typed top-down enumeration up to 4-literal
    rule bodies. Mode declarations are derived mechanically from the
    schema's :arg-sorts and :return.

    For each pair of predicates returning :real with matching binding
    sort, emit ``(approx= (:P ?d) (:Q ?d) :tolerance ε)`` where ε is a
    placeholder later filled by Phase X SMT numeric fitting.

    The :tolerance literal counts as one structural slot; the two
    predicate references count as two literals; the approx= head
    counts as one. Total = 4, the upper bound the spec sets.
    """
    preds = _schema_predicates(schema)
    real_preds = [p for p in preds if _return_inner_sort(p[2]) == Keyword("real")]
    cap = per_source_cap()
    out: list[dict[str, Any]] = []
    # Group by binding sort so we only pair predicates over the same domain.
    by_sort: dict[tuple, list[str]] = defaultdict(list)
    for name, arg_sorts, _ret in real_preds:
        by_sort[tuple(arg_sorts)].append(name)
    for sort_key, names in by_sort.items():
        if not sort_key or len(names) < 2:
            continue
        for p1, p2 in itertools.combinations(sorted(names), 2):
            if len(out) >= cap:
                break
            edn = (
                f"(defconstraint :induced/{p1}-approx-{p2}\n"
                f"  :backend :z3\n"
                f"  :assert (approx= (:{p1} ?d) (:{p2} ?d) :tolerance 0.05)\n"
                f"  :on-unsat {{:defect :D-induced-p :severity :advisory\n"
                f'             :message "Popper-typed approx eq: {p1} ≈ {p2}"}})'
            )
            out.append(
                {
                    "id": f"popper-{p1}-{p2}",
                    "canonical_form": canonical_constraint_form(edn),
                    "edn": edn,
                    "cited_atoms": [],
                    "origin": [POPPER],
                    "support": None,
                    "coherence": None,
                    "literal_count": 4,
                    "status": "pending",
                    "rejection_reason": None,
                }
            )
        if len(out) >= cap:
            break
    return out


# ---------------------------------------------------------------------------
# Source 3 — LLM proposer (Phase V) + Stub fallback
# ---------------------------------------------------------------------------


class BudgetTracker:
    """Tracks accumulated LLM spend against an optional cap.

    REQ-INDUCE-056: when accumulated spend exceeds ``limit_usd``, the
    tracker reports ``halted=True`` and subsequent LLM calls SHALL be
    skipped. Horn-body and Popper sources are unaffected because they
    never consult the tracker.
    """

    def __init__(self, *, limit_usd: Optional[float]) -> None:
        self.limit_usd = limit_usd
        self.spent_usd = 0.0
        self.halted = False

    def can_spend(self, amount: float) -> bool:
        if self.limit_usd is None:
            return True
        if self.halted:
            return False
        return self.spent_usd + amount <= self.limit_usd + 1e-9

    def charge(self, amount: float) -> None:
        self.spent_usd += amount
        if self.limit_usd is not None and self.spent_usd >= self.limit_usd:
            self.halted = True


class StubProposer:
    """Deterministic stub LLM proposer for CI.

    Emits a single ``defconstraint`` candidate per cluster, derived
    mechanically from the cluster's predicate name. The per-call cost
    is ``NEUROSYM_INDUCTION_STUB_COST_USD`` (default 0.001) so the
    budget tracker has a concrete number to consume (REQ-INDUCE-056).
    """

    name = "stub"

    def cost_per_call(self) -> float:
        raw = os.environ.get("NEUROSYM_INDUCTION_STUB_COST_USD")
        if raw is None or raw == "":
            return 0.001
        try:
            return float(raw)
        except ValueError:
            return 0.001

    def propose(self, *, cluster: list[dict[str, Any]], schema: dict[str, Any]) -> Optional[dict[str, Any]]:
        if not cluster:
            return None
        pred = cluster[0]["predicate"]
        cited = sorted({a["claim_id"] for a in cluster})
        edn = (
            f"(defconstraint :induced/llm-{pred}\n"
            f"  :backend :z3\n"
            f"  :assert (> (:{pred} ?d) 0)\n"
            f"  :on-unsat {{:defect :D-induced-l :severity :advisory\n"
            f'             :message "LLM-proposed: {pred} > 0"}})'
        )
        return {
            "id": f"llm-{pred}",
            "canonical_form": canonical_constraint_form(edn),
            "edn": edn,
            "cited_atoms": cited,
            "origin": [LLM],
            "support": None,
            "coherence": None,
            "literal_count": 2,
            "status": "pending",
            "rejection_reason": None,
        }


def _candidate_from_edn(edn: str, cluster: list[dict[str, Any]]) -> dict[str, Any]:
    """Wrap a raw EDN string from the Phase V proposer into the uniform
    candidate dict shape documented at the top of this module.

    The proposer (``propose_constraint``) returns only the EDN form; the
    canonical key, cited atoms, and origin tags are derived here so the
    Phase V path produces the same candidate shape as the Horn-body,
    Popper, and Stub sources.
    """
    cited = sorted({a["claim_id"] for a in cluster if a.get("claim_id")})
    return {
        "id": f"llm-{cluster[0]['predicate']}" if cluster else "llm",
        "canonical_form": canonical_constraint_form(edn),
        "edn": edn,
        "cited_atoms": cited,
        "origin": [LLM],
        "support": None,
        "coherence": None,
        "literal_count": 2,
        "status": "pending",
        "rejection_reason": None,
    }


def llm_propose(
    *,
    schema: dict[str, Any],
    cluster: list[dict[str, Any]],
    provider: Any,
    budget: Optional["BudgetTracker"] = None,
) -> list[dict[str, Any]]:
    """REQ-INDUCE-051(c), 056: invoke the LLM proposer for one cluster.

    Phase V's ``propose_constraint`` is used when available; it returns a
    raw EDN string, which is wrapped into the uniform candidate dict via
    ``_candidate_from_edn``. Otherwise the StubProposer's deterministic
    shape is the fallback. The budget tracker is consulted BEFORE each
    call; once exhausted, the source returns [] and downstream Horn-body
    / Popper sources are unaffected.
    """
    cost = provider.cost_per_call() if hasattr(provider, "cost_per_call") else 0.001
    if budget is not None:
        if not budget.can_spend(cost):
            budget.halted = True
            return []
    candidate = None
    if PHASE_V_AVAILABLE and _phase_v_propose is not None:
        try:
            edn = _phase_v_propose(atom_cluster=cluster, schema=schema)
            # The proposer emits a self-disclaiming placeholder when no
            # real LLM / canned candidate is configured (offline CI with
            # no NEUROSYM_STUB_CANDIDATE). Treat that as "proposer not
            # configured" and fall back to the deterministic local stub
            # so the offline default stays grammar-valid.
            if edn and "UNCONFIGURED-STUB" not in edn:
                candidate = _candidate_from_edn(edn, cluster)
        except Exception:
            candidate = None
    if candidate is None:
        candidate = provider.propose(cluster=cluster, schema=schema)
    if budget is not None:
        budget.charge(cost)
    if candidate is None:
        return []
    cap = per_source_cap()
    return [candidate][:cap]


# ---------------------------------------------------------------------------
# Deduplication (REQ-INDUCE-052)
# ---------------------------------------------------------------------------


def _merge_lists(a: Iterable, b: Iterable) -> list:
    """Order-preserving set union."""
    seen: dict = {}
    for item in list(a) + list(b):
        seen[item] = None
    return list(seen.keys())


def dedup(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """REQ-INDUCE-052: collapse alpha-equivalent candidates.

    Two candidates are alpha-equivalent if their canonical S-expression
    forms match after var-name canonicalisation. ``canonical_form`` is
    re-canonicalised here so callers may pass raw EDN forms with
    arbitrary logic-variable names (`?d`, `?x`, `?subject`) and still
    have alpha-equivalent rules collapse correctly. The surviving
    candidate carries the union of origin tags and the union of
    cited_atoms.
    """
    by_key: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for c in candidates:
        key = canonical_constraint_form(c["canonical_form"])
        if key not in by_key:
            new_c = dict(c)
            # Stash the canonicalised key so downstream readers see the
            # alpha-canonical form rather than the source-specific
            # variable naming.
            new_c["canonical_form"] = key
            by_key[key] = new_c
            order.append(key)
            continue
        existing = by_key[key]
        existing["origin"] = _merge_lists(existing.get("origin", []), c.get("origin", []))
        existing["cited_atoms"] = _merge_lists(
            existing.get("cited_atoms", []), c.get("cited_atoms", [])
        )
        # Sum supports when both sources contributed a count.
        s_existing = existing.get("support")
        s_new = c.get("support")
        if s_existing is not None and s_new is not None:
            existing["support"] = s_existing + s_new
        elif s_new is not None:
            existing["support"] = s_new
    return [by_key[k] for k in order]


def dedup_with_rejection_log(
    candidates: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """REQ-INDUCE-055: like ``dedup`` but also returns the rejected
    duplicates with ``rejection_reason = "duplicate"`` so the queue
    can record them for post-mortem analysis."""
    merged = dedup(candidates)
    rejected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for c in candidates:
        key = canonical_constraint_form(c["canonical_form"])
        if key in seen:
            entry = dict(c)
            entry["status"] = "rejected"
            entry["rejection_reason"] = "duplicate"
            rejected.append(entry)
        seen.add(key)
    return merged, rejected


# ---------------------------------------------------------------------------
# Semantic-coherence ranking (REQ-INDUCE-053)
# ---------------------------------------------------------------------------


def coherence_score(candidate: dict[str, Any], sem_index: Any) -> float:
    """Mean pairwise cosine similarity over the candidate's cited atoms.

    A 0- or 1-atom candidate returns 1.0 (the empty pair set is
    maximally coherent by convention; a 1-atom candidate is
    self-coherent).
    """
    atoms = candidate.get("cited_atoms", []) or []
    if len(atoms) < 2:
        return 1.0
    pairs = list(itertools.combinations(atoms, 2))
    sims: list[float] = []
    for a, b in pairs:
        try:
            sims.append(float(sem_index.cosine(a, b)))
        except Exception:
            sims.append(0.0)
    if not sims:
        return 1.0
    return float(statistics.fmean(sims))


def rank_by_semantic_coherence(
    candidates: list[dict[str, Any]],
    sem_index: Any,
) -> list[dict[str, Any]]:
    """REQ-INDUCE-053: order candidates by descending mean pairwise
    cosine over cited atoms. WHERE sem_index is None, the function is a
    no-op that preserves insertion order (graceful degradation when
    Phase Q's SemanticIndex is unavailable).
    """
    if sem_index is None:
        return [dict(c, coherence=c.get("coherence")) for c in candidates]
    scored: list[tuple[int, dict[str, Any]]] = []
    for idx, c in enumerate(candidates):
        sc = coherence_score(c, sem_index)
        copy = dict(c)
        copy["coherence"] = sc
        scored.append((idx, copy))
    # Stable sort: ties broken by original insertion order.
    scored.sort(key=lambda kv: (-kv[1]["coherence"], kv[0]))
    return [c for _idx, c in scored]
