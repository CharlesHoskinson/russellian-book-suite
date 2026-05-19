"""AGM-compliant theory revision for induced BookLogic theories.

This module ships ``revise_theory``, the single entry-point that mutates an
induced theory's provenance sidecar when new evidence reaches a previously
induced rule.

Discipline (per ``docs/specs/2026-05-19-tier6-theory-induction-design.md``
and ``openspec/changes/tier6-agm-revision/``):

* AGM-style contraction: rules are demoted, never silently overwritten.
* Quarantined rules persist in the sidecar with a lower status.
* Status is a deterministic function of entrenchment:

  - ``entrenchment >= 0.7``       -> ``:active``
  - ``0.4 <= entrenchment < 0.7`` -> ``:tentative``
  - ``entrenchment < 0.4``        -> ``:quarantined``

* Entrenchment formula:

      held_out_sat_rate * min(support_doc_count / 10.0, 1.0)

  clamped to ``[0.0, 1.0]``.

Tier 6 implements contract-down only; promote-up is deferred to Tier 7
because it requires the AST-aware semantic-distance metric the design spec
flagged as open research.

REQs implemented: REQ-REVISE-040, 041, 042, 043, 044, 045, 046.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar

# Conditional import for the Phase Y ProvenanceSidecar. When Phase Y has
# not yet merged, fall back to a minimal stub that matches the design
# spec's public surface, so this module is independently testable.
try:  # pragma: no cover - exercised at import time
    from scripts._provenance import ProvenanceSidecar  # type: ignore[no-redef]
except ImportError:  # pragma: no cover - covered when Phase Y lands

    class ProvenanceSidecar:  # type: ignore[no-redef]
        """Minimal stub matching Phase Y's design surface for testing."""

        def __init__(self) -> None:
            self._rules: dict[str, dict[str, Any]] = {}

        def add_rule_provenance(
            self, rule_id: str, prov_dict: dict[str, Any]
        ) -> None:
            self._rules[rule_id] = dict(prov_dict)

        def lookup(self, rule_id: str) -> dict[str, Any] | None:
            return self._rules.get(rule_id)

        def iter_rules(self):
            return iter(self._rules.items())

        def save(self, path: Path) -> None:
            import json
            Path(path).write_text(json.dumps(self._rules))

        def load(self, path: Path) -> None:
            import json
            self._rules = json.loads(Path(path).read_text())


_LOG = logging.getLogger(__name__)

#: Status keywords used in the sidecar; kept as plain strings so they
#: round-trip transparently through the JSON stub and an eventual EDN
#: serializer alike.
STATUS_ACTIVE = ":active"
STATUS_TENTATIVE = ":tentative"
STATUS_QUARANTINED = ":quarantined"

#: Status precedence used to detect contract-down vs forbidden promote-up.
_STATUS_RANK = {
    STATUS_ACTIVE: 2,
    STATUS_TENTATIVE: 1,
    STATUS_QUARANTINED: 0,
}

#: Entrenchment thresholds (REQ-REVISE-042).
THRESHOLD_ACTIVE = 0.7
THRESHOLD_TENTATIVE = 0.4

#: Document-count saturation in the entrenchment formula.
DOC_SATURATION = 10.0


@dataclass
class RevisionReport:
    """Stable shape consumed by ``forge revise`` (Phase AA).

    ``rules_affected`` counts rules whose status TRANSITIONED, not rules
    whose entrenchment merely changed. Per-status counts are the
    post-revision census.
    """

    rules_affected: int = 0
    rules_active: int = 0
    rules_tentative: int = 0
    rules_quarantined: int = 0
    diff_summary: str = ""
    full_quarantine_warning: bool = False

    #: Kebab-case alias map -> snake_case attribute, so callers (and the
    #: Phase Z1.1 micro-test) may index a report with ``report["rules-affected"]``
    #: without forcing the dataclass field names into kebab-case.
    _ALIASES: ClassVar[dict[str, str]] = {
        "rules-affected": "rules_affected",
        "rules-active": "rules_active",
        "rules-tentative": "rules_tentative",
        "rules-quarantined": "rules_quarantined",
        "diff-summary": "diff_summary",
        "full-quarantine-warning": "full_quarantine_warning",
    }

    def __getitem__(self, key: str) -> Any:
        """Allow kebab-case / snake_case indexing into the report."""
        if key in self._ALIASES:
            return getattr(self, self._ALIASES[key])
        if hasattr(self, key) and not key.startswith("_"):
            return getattr(self, key)
        raise KeyError(key)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _status_from_entrenchment(entrenchment: float) -> str:
    """Map a clamped entrenchment value to its status keyword.

    REQ-REVISE-042: deterministic thresholds, no ties.
    """
    if entrenchment >= THRESHOLD_ACTIVE:
        return STATUS_ACTIVE
    if entrenchment >= THRESHOLD_TENTATIVE:
        return STATUS_TENTATIVE
    return STATUS_QUARANTINED


def _clamp01(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def _doc_factor(support_doc_count: int) -> float:
    """``min(support_doc_count / 10.0, 1.0)`` per the entrenchment formula."""
    return min(support_doc_count / DOC_SATURATION, 1.0)


def _recover_prior_sat_rate(rule: dict[str, Any]) -> float:
    """Recover the prior held-out-sat-rate for a rule.

    The design spec calls for re-running the 5-fold validation pass from
    Phase X on the diminished support. Phase X is not visible inside this
    module's testable boundary, so the sat-rate is recovered from the
    rule's prior provenance in priority order:

    1. The most-recent ``:prov/validated-by`` entry's ``:sat-rate`` field
       (Phase X writes this).
    2. The implicit sat-rate derived from the current entrenchment and the
       current support-doc count: ``entrenchment / min(docs/10, 1)``.
    3. ``1.0`` as a final defensive fallback (a brand-new rule with no
       history).

    The recovered rate is clamped to ``[0.0, 1.0]``.
    """
    validated_by = rule.get(":prov/validated-by") or []
    for entry in reversed(validated_by):
        if isinstance(entry, dict):
            for key in (":sat-rate", "sat-rate", ":held-out-sat-rate"):
                if key in entry:
                    return _clamp01(float(entry[key]))

    current_entrenchment = rule.get(":prov/entrenchment")
    current_docs = rule.get(":prov/source-documents") or []
    if current_entrenchment is not None and current_docs:
        factor = _doc_factor(len(current_docs))
        if factor > 0.0:
            return _clamp01(float(current_entrenchment) / factor)

    return 1.0


def _diminish_sat_rate(prior_rate: float, atoms_before: int, atoms_lost: int) -> float:
    """Degrade ``prior_rate`` proportional to the atoms removed.

    A contradicting atom that hits a rule removes that atom from the rule's
    support. Without re-running the real Phase X validator inside this
    module, we approximate the validator's response: lose half the
    supporting atoms, lose half the sat-rate contribution. The function is
    monotone-decreasing in ``atoms_lost``; ``atoms_lost == 0`` is a
    no-op; ``atoms_lost == atoms_before`` drives the rate to zero.
    """
    if atoms_before <= 0 or atoms_lost <= 0:
        return _clamp01(prior_rate)
    fraction_lost = atoms_lost / atoms_before
    return _clamp01(prior_rate * (1.0 - fraction_lost))


def _rule_belongs_to_corpus(rule: dict[str, Any], doc_id: str) -> bool:
    """Per-corpus scoping check (REQ-PROV-046 forward compatibility).

    When a rule carries ``:prov/induced-from-corpus`` AND the framework can
    map the doc_id to a corpus, scope retraction to matching rules only.
    The corpus -> doc mapping lives in ``claims.jsonl`` and is not yet
    surfaced through this entry point; absence of the corpus key means
    "apply globally", which is the backward-compatible default for
    single-corpus projects.
    """
    # When the rule doesn't declare a corpus, retraction is global.
    if ":prov/induced-from-corpus" not in rule:
        return True
    # Defensive default: until corpus->doc mapping is wired, treat declared
    # corpora as globally-scoped too. This keeps the function side of the
    # API stable while the Phase AA CLI loads the manifest.
    return True


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def revise_theory(
    induced_path: Path | None,
    prov_path: Path,
    retracted_docs: list[str] | None = None,
    contradicting_atoms: list[str] | None = None,
) -> RevisionReport:
    """Apply an AGM-style contraction to an induced theory's sidecar.

    Parameters
    ----------
    induced_path:
        Path to ``induced-theory.edn`` (the rule text). NOT rewritten by
        this function — only the sidecar mutates. ``None`` is accepted for
        sidecar-only revisions exercised by the micro-tests.
    prov_path:
        Path to ``induced-theory.prov.edn``. Loaded, mutated in place,
        and written back.
    retracted_docs:
        Document identifiers (``"pmid:12345"`` style) whose support should
        be removed from any rule that cites them.
    contradicting_atoms:
        Atom identifiers whose support should be removed from any rule
        that derives from them.

    Returns
    -------
    RevisionReport
        Stable shape per REQ-REVISE-045.

    Notes
    -----
    REQ-REVISE-040 — single entry point.
    REQ-REVISE-041 — contract → re-validate → recompute (Levi identity).
    REQ-REVISE-042 — deterministic status thresholds.
    REQ-REVISE-043 — contract-down only; promote-up deferred to Tier 7.
    REQ-REVISE-044 — full-quarantine warning.
    REQ-REVISE-045 — RevisionReport shape.
    REQ-REVISE-046 — fixture-driven test coverage.
    """
    retracted_set = set(retracted_docs or [])
    contradicting_set = set(contradicting_atoms or [])

    sidecar = ProvenanceSidecar()
    sidecar.load(prov_path)

    diff_entries: list[tuple[str, str, str]] = []
    rules_affected_count = 0
    counts = {STATUS_ACTIVE: 0, STATUS_TENTATIVE: 0, STATUS_QUARANTINED: 0}

    # Sort by rule_id for deterministic diff_summary ordering (REQ-REVISE-045).
    rules = sorted(sidecar.iter_rules(), key=lambda kv: kv[0])

    for rule_id, rule in rules:
        old_status = rule.get(":prov/status", STATUS_ACTIVE)

        # (a) Compute affected sets.
        doc_support = list(rule.get(":prov/source-documents") or [])
        atom_support = list(rule.get(":prov/derived-from-atoms") or [])

        # Per-corpus scoping (defensive; defaults to global).
        applicable_retractions: set[str] = set()
        for doc in retracted_set:
            if _rule_belongs_to_corpus(rule, doc):
                applicable_retractions.add(doc)

        affected_docs = set(doc_support) & applicable_retractions
        affected_atoms = set(atom_support) & contradicting_set

        # (b) Unaffected rule: keep entrenchment + status untouched.
        if not affected_docs and not affected_atoms:
            counts[old_status] = counts.get(old_status, 0) + 1
            continue

        # (c) Contract the support sets.
        new_docs = [d for d in doc_support if d not in affected_docs]
        new_atoms = [a for a in atom_support if a not in affected_atoms]

        atoms_before = len(atom_support)
        atoms_lost = len(affected_atoms)

        # (d) Recompute held-out-sat-rate. We pull prior rate, then
        # diminish proportional to atom loss (a stand-in for Phase X's
        # real validator running on the diminished support).
        prior_rate = _recover_prior_sat_rate(rule)
        new_sat_rate = _diminish_sat_rate(prior_rate, atoms_before, atoms_lost)

        # (e) Recompute entrenchment.
        new_entrenchment = _clamp01(new_sat_rate * _doc_factor(len(new_docs)))

        # Status (REQ-REVISE-042).
        new_status = _status_from_entrenchment(new_entrenchment)

        # REQ-REVISE-043: contract-down only. If the threshold table
        # would promote, clamp back to the prior status.
        if _STATUS_RANK[new_status] > _STATUS_RANK.get(old_status, _STATUS_RANK[STATUS_ACTIVE]):
            new_status = old_status

        # Mutate the rule in place.
        rule[":prov/source-documents"] = new_docs
        rule[":prov/derived-from-atoms"] = new_atoms
        rule[":prov/entrenchment"] = new_entrenchment
        rule[":prov/status"] = new_status

        validated_by = list(rule.get(":prov/validated-by") or [])
        validated_by.append(
            {
                ":pass": ":agm-revision",
                ":sat-rate": new_sat_rate,
                ":retracted-docs": sorted(affected_docs),
                ":contradicting-atoms": sorted(affected_atoms),
                ":prior-status": old_status,
                ":new-status": new_status,
            }
        )
        rule[":prov/validated-by"] = validated_by

        # Persist (the stub's iter_rules returned the same dicts, but be
        # explicit so non-stub sidecars that copy-on-read keep behaving).
        sidecar.add_rule_provenance(rule_id, rule)

        # Tally.
        counts[new_status] = counts.get(new_status, 0) + 1
        if new_status != old_status:
            rules_affected_count += 1
            diff_entries.append((rule_id, old_status, new_status))

    # Persist mutated sidecar.
    sidecar.save(prov_path)

    diff_summary = "; ".join(
        f"{rid}: {old} -> {new}" for rid, old, new in diff_entries
    )

    total_rules = sum(counts.values())
    full_quarantine = (
        total_rules > 0 and counts[STATUS_QUARANTINED] == total_rules
    )

    report = RevisionReport(
        rules_affected=rules_affected_count,
        rules_active=counts[STATUS_ACTIVE],
        rules_tentative=counts[STATUS_TENTATIVE],
        rules_quarantined=counts[STATUS_QUARANTINED],
        diff_summary=diff_summary,
        full_quarantine_warning=full_quarantine,
    )

    if full_quarantine:
        _LOG.warning(
            "agm-revision: full-quarantine — every induced rule (%d) "
            "moved to :quarantined in a single revision; "
            "retracted_docs=%d, contradicting_atoms=%d",
            total_rules,
            len(retracted_set),
            len(contradicting_set),
        )

    return report
