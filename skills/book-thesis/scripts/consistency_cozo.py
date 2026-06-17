"""P3.2 — EDN/Cozo D9-D11 consistency pass (REQ-KG-015).

`run_consistency_cozo(workspace)` is the EDN-front/Cozo-back replacement for
`datalog_consistency.run`: it projects the thesis spine (P3.1) + the claim-derived
consistency facts into book-knowledge's Cozo store (via the P3.0 bridge), runs the
recursive CozoScript program ``rules/consistency.cozo`` head by head, and assembles
the SAME ``DefectReport.as_payload()`` the pyDatalog pass emits — proven equal on
the C0.3 goldens and against the live pyDatalog pass.

Parity rests on reuse, not re-implementation: the DefectReport class, the
pair-dedup helper ``_emit_pairs``, the value canonicaliser ``_value_str``, the
ledger reader, the claim-facts.yaml projection, AND the per-rule detail strings all
come from ``datalog_consistency`` unchanged, so only the FACT SOURCE differs (Cozo
rows instead of pyDatalog answers). The fact loader mirrors
``datalog_consistency._assert_claim_facts`` field-for-field (incl. the
``semantic_class`` subject fallback and the ``have_subjects`` gate) so a real
ledger yields the identical defect set.
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from datalog_consistency import (  # noqa: E402  — reuse for exact parity
    DefectReport,
    _emit_pairs,
    _iter_claims,
    _resolve_claims_path,
    _value_str,
    load_claim_facts,
)
from project_thesis_cozo import _book_id, project_thesis  # noqa: E402

RULES = Path(__file__).resolve().parent.parent / "rules" / "consistency.cozo"


def project_consistency_facts(workspace: Path, store, book_id: str | None = None) -> bool:
    """Load the claim-derived consistency facts; return whether any subject exists.

    Mirrors ``datalog_consistency._assert_thesis_facts`` (advancedBy /
    requiresEvidence) and ``._assert_claim_facts`` (claim subject/value/implies/
    supports/conflict), but into the Cozo fact tables instead of pyDatalog. The
    boolean return is the ``have_subjects`` gate the pyDatalog pass uses to suppress
    missing-evidence noise on a ledger with no structured subjects.
    """
    workspace = Path(workspace)
    bid = _book_id(workspace, book_id)
    spec = yaml.safe_load(
        (workspace / "thesis" / f"{bid}.yaml").read_text(encoding="utf-8")
    ) or {}

    chapter_rows: list[dict] = []
    evidence_rows: list[dict] = []
    for sub in spec.get("sub_arguments") or []:
        sid = str(sub["id"]).strip()
        for ch in sub.get("advanced_by_chapters") or []:
            chapter_rows.append(
                {"id": f"{sid}\x1f{ch}", "sub-arg-id": sid, "chapter": str(ch)}
            )
        for ev in sub.get("required_evidence") or []:
            evidence_rows.append(
                {"id": f"{sid}\x1f{ev}", "sub-arg-id": sid, "evidence": str(ev)}
            )

    claim_fact_rows: list[dict] = []
    implies_rows: list[dict] = []
    supports_rows: list[dict] = []
    conflict_rows: list[dict] = []
    have_subjects = False

    claims_path = _resolve_claims_path(workspace)
    if claims_path is not None:
        claim_facts = load_claim_facts(workspace)
        seen: set[str] = set()
        for rec in _iter_claims(claims_path):
            cid = rec.get("claim_id") or rec.get("id")
            if not cid or rec.get("status", "verified") != "verified" or cid in seen:
                continue
            cid = str(cid)
            seen.add(cid)
            proj = claim_facts.get(cid, {})

            fact: dict = {"id": cid}
            # subject: typed projection > inlined subject > semantic_class fallback
            # (identical precedence to _assert_claim_facts).
            subject = proj.get("subject") or rec.get("subject") or rec.get("semantic_class")
            if subject:
                fact["subject"] = str(subject)
                have_subjects = True
            if "value" in proj:
                fact["value"] = _value_str(proj["value"])
            elif "value" in rec:
                fact["value"] = _value_str(rec["value"])
            if "subject" in fact or "value" in fact:
                claim_fact_rows.append(fact)

            for node in rec.get("supports_nodes") or []:
                supports_rows.append(
                    {"id": f"{cid}\x1f{node}", "claim-id": cid, "node": str(node)}
                )
            for tgt in (proj.get("implies") or rec.get("implies") or []):
                implies_rows.append(
                    {"id": f"{cid}\x1f{tgt}", "claim-id": cid, "target-id": str(tgt)}
                )
            for other in rec.get("conflicts_with") or []:
                conflict_rows.append(
                    {"id": f"{cid}\x1f{other}", "claim-id": cid, "other-id": str(other)}
                )

    store.load("sub-arg-chapter", chapter_rows)
    store.load("sub-arg-evidence", evidence_rows)
    store.load("claim-fact", claim_fact_rows)
    store.load("claim-implies", implies_rows)
    store.load("paragraph-supports", supports_rows)
    store.load("claim-conflict", conflict_rows)
    return have_subjects


def _build_store():
    from sibling_skills import book_knowledge_root, load_book_knowledge_module

    cozo_store = load_book_knowledge_module("cozo_store")
    schema = book_knowledge_root() / "assets" / "kg-schema.edn"
    return cozo_store.CozoStore.in_memory(schema_path=schema)


def run_consistency_cozo(workspace, book_id: str | None = None) -> dict:
    """Project + run the Cozo consistency program; return the canonical payload.

    Same shape as ``datalog_consistency.DefectReport.as_payload()`` (summary +
    canonically-sorted defects), so it is byte-comparable to the C0.3 goldens.
    """
    workspace = Path(workspace)
    store = _build_store()
    project_thesis(workspace, store, book_id)
    have_subjects = project_consistency_facts(workspace, store, book_id)
    program = RULES.read_text(encoding="utf-8")

    def q(head: str, cols: list[str]) -> list[tuple]:
        col_str = ", ".join(cols)
        rows = store.query(f"{program}\n?[{col_str}] := {head}[{col_str}]")
        # sorted, mirroring datalog_consistency._collect, so _emit_pairs picks the
        # same first-per-key (a, b) ordering for facts/detail.
        return sorted(tuple(r) for r in rows)

    report = DefectReport()
    for (p,) in q("orphan_paragraph", ["p"]):
        report.orphans.append({"class": "D9", "rule": "orphan_paragraph", "facts": [p],
            "detail": f"paragraph {p!r} does not reach :Thesis through supports edges"})
    direct = _emit_pairs("direct_contradiction", "D10",
        q("direct_contradiction", ["a", "b"]),
        "claims {a!r} and {b!r} assert different values for the same subject",
        report.contradictions, skip=set())
    _emit_pairs("transitive_contradiction", "D10",
        q("transitive_contradiction", ["a", "b"]),
        "claim {a!r} transitively contradicts {b!r}", report.contradictions, skip=direct)
    _emit_pairs("declared_conflict", "D11", q("declared_conflict", ["a", "b"]),
        "ledger declares {a!r} conflicts_with {b!r}", report.invariants, skip=set())
    for (p,) in q("unreachable_supports", ["p"]):
        report.invariants.append({"class": "D11", "rule": "unreachable_supports", "facts": [p],
            "detail": f"{p!r} supports a node that is neither :Thesis nor a SubArgument"})
    for cid, inv in q("invariant_violation", ["c", "i"]):
        report.invariants.append({"class": "D11", "rule": "invariant_violation", "facts": [cid, inv],
            "detail": f"claim {cid!r} violates authored invariant {inv!r}"})
    for (n,) in q("sub_arg_no_chapter", ["n"]):
        report.invariants.append({"class": "D11", "rule": "sub_arg_no_chapter", "facts": [n],
            "detail": f"sub-argument {n!r} is advanced by no chapter"})
    if have_subjects:
        for n, e in q("missing_evidence", ["n", "e"]):
            report.invariants.append({"class": "D11", "rule": "missing_evidence", "facts": [n, e],
                "detail": f"sub-argument {n!r} requires evidence {e!r} that no claim's subject meets"})

    return report.as_payload()


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: consistency_cozo.py <workspace> [book-id]", file=sys.stderr)
        return 2
    book_id = argv[2] if len(argv) > 2 else None
    payload = run_consistency_cozo(Path(argv[1]), book_id)
    s = payload["summary"]
    print(f"cozo consistency: contradictions={s['contradictions']} "
          f"orphans={s['orphans']} invariant_violations={s['invariant_violations']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
