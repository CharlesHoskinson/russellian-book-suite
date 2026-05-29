"""Layer 4: Datalog consistency pass over the thesis tree and claim ledger.

Reads ``<workspace>/.knowledge/thesis-triples.ttl`` and the verified-claim
ledger at ``<workspace>/claims/ledger.jsonl`` (the canonical book-knowledge
layout), asserts pyDatalog facts, loads the rules in ``rules/consistency.dl``,
and writes derived defects to ``<workspace>/qa/datalog-defects.json``. Defect
classes: D9 paragraph-orphan, D10 (transitive) contradiction, D11
invariant-violation (declared-conflict, unreachable-supports,
missing-evidence, sub-arg-advanced-by-no-chapter, and authored-invariant
violations compiled from thesis `formal:` clauses). D12
(unadvanced-sub-argument = named by no paragraph's supports) is owned by
lint_supports / book-qa, not this pass.
Exit codes: 0 clean, 1 D10/D11 finding (gate fail), 2 CLI error.
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from pyDatalog import pyDatalog
from rdflib import Graph, Namespace, URIRef

NS = Namespace("https://russellian.book/thesis/")
THESIS_URI = URIRef(NS["Thesis"])
RULES_FILE = Path(__file__).resolve().parent.parent / "rules" / "consistency.dl"

# Every predicate and variable referenced by the loader-asserted facts or
# rules/consistency.dl must appear in TERMS.
TERMS = (
    "is_thesis, sub_arg, paragraph, supports, advances, requires_evidence, "
    "claim, claim_subject, claim_value, claim_chapter, conflict_decl, implies, "
    "invariant_pin, invariant_forbid, invariant_violation, "
    "states, reaches_thesis, orphan_paragraph, direct_contradiction, "
    "transitive_contradiction, sub_arg_no_chapter, missing_evidence, "
    "unreachable_supports, declared_conflict, advanced, evidence_met, "
    "P, N, M, S, V, V1, V2, Vok, Vbad, A, B, C, Ch, E, I, Inv, X, Y"
)

# pyDatalog raises if a rule body references a predicate with zero facts. Seed
# each extensional predicate with a sentinel tuple; sentinel rows are filtered
# out before reporting.
SENTINEL = "__nil__"
EXTENSIONAL: tuple[tuple[str, int], ...] = (
    ("is_thesis", 1), ("sub_arg", 1), ("paragraph", 1),
    ("supports", 2), ("advances", 2), ("requires_evidence", 2),
    ("claim", 1), ("claim_subject", 2), ("claim_value", 2),
    ("claim_chapter", 2), ("conflict_decl", 2), ("implies", 2),
    ("invariant_pin", 3), ("invariant_forbid", 3),
)


@dataclass
class DefectReport:
    contradictions: list[dict] = field(default_factory=list)
    orphans: list[dict] = field(default_factory=list)
    invariants: list[dict] = field(default_factory=list)

    def as_payload(self) -> dict[str, Any]:
        defects = self.contradictions + self.orphans + self.invariants
        defects.sort(key=lambda d: (d["class"], d["rule"], json.dumps(d["facts"], sort_keys=True)))
        return {"summary": {"contradictions": len(self.contradictions),
                            "orphans": len(self.orphans),
                            "invariant_violations": len(self.invariants)},
                "defects": defects}

    def gate_failed(self) -> bool:
        return bool(self.contradictions) or bool(self.invariants)


def _local(uri: Any) -> str:
    s = str(uri)
    if s.startswith(str(NS)): return s[len(str(NS)):]
    if "#" in s: return s.rsplit("#", 1)[1]
    return s.rsplit("/", 1)[1] if "/" in s else s


def _resolve_claims_path(workspace: Path) -> Path | None:
    # Canonical book-knowledge layout. Tests and production share this path.
    path = workspace / "claims" / "ledger.jsonl"
    if path.exists() and path.stat().st_size > 0:
        return path
    return None


def _iter_claims(path: Path) -> Iterable[dict[str, Any]]:
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line: yield json.loads(line)


def _value_str(value: Any) -> str:
    """Canonical string form of a claim value, for comparison against
    authored invariant literals (which are strings in the thesis YAML)."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (str, int, float)):
        return str(value)
    return json.dumps(value, sort_keys=True)


def _assert_thesis_facts(graph: Graph) -> None:
    for s, _p, _o in graph.triples((None, NS["statement"], None)):
        if s == THESIS_URI:
            pyDatalog.assert_fact("is_thesis", _local(s))
    for s, _p, _o in graph.triples((None, None, NS["SubArgument"])):
        pyDatalog.assert_fact("sub_arg", _local(s))
    for s, _p, o in graph.triples((None, NS["supports"], None)):
        pyDatalog.assert_fact("supports", _local(s), _local(o))
    # advancedBy points from sub-arg to chapter; advances(Ch, N) is the inverse.
    for s, _p, o in graph.triples((None, NS["advancedBy"], None)):
        pyDatalog.assert_fact("advances", _local(o), _local(s))
    for s, _p, o in graph.triples((None, NS["requiresEvidence"], None)):
        pyDatalog.assert_fact("requires_evidence", _local(s), _local(o))
    # Authored invariants, compiled by compile_thesis into (subject, value)
    # pairs. invariant_pin(Inv, Subject, Value): a claim about Subject MUST
    # equal Value. invariant_forbid(Inv, Subject, Value): it must NOT equal it.
    for s, _p, subject in graph.triples((None, NS["invariantSubject"], None)):
        inv = _local(s)
        for _s, _p2, val in graph.triples((s, NS["invariantPinnedValue"], None)):
            pyDatalog.assert_fact("invariant_pin", inv, str(subject), str(val))
        for _s, _p2, val in graph.triples((s, NS["invariantForbiddenValue"], None)):
            pyDatalog.assert_fact("invariant_forbid", inv, str(subject), str(val))


def _assert_claim_facts(records: Iterable[dict[str, Any]]) -> bool:
    """Assert claim-derived facts. Returns True if any ``claim_subject`` fact
    was asserted (i.e. the ledger carries structured subject data)."""
    seen: set[str] = set()
    any_subject = False
    for rec in records:
        cid = rec.get("claim_id") or rec.get("id")
        if not cid or rec.get("status", "verified") != "verified" or cid in seen:
            continue
        seen.add(cid)
        pyDatalog.assert_fact("claim", cid)
        # Only claims that actually carry a supports edge participate in the
        # orphan/reachability check. A bare ledger record (the real schema has
        # no supports_nodes field) is not a manuscript paragraph and must not
        # be flagged as an orphan — that would flood D9 with false positives.
        supports_nodes = rec.get("supports_nodes")
        if supports_nodes:
            pyDatalog.assert_fact("paragraph", cid)
            _multi_assert("supports", cid, supports_nodes)
        if (subject := rec.get("subject") or rec.get("semantic_class")):
            pyDatalog.assert_fact("claim_subject", cid, str(subject))
            any_subject = True
        if "value" in rec:
            # Stringify so values compare cleanly against invariant literals
            # (which are authored as strings in the thesis YAML).
            pyDatalog.assert_fact("claim_value", cid, _value_str(rec["value"]))
        _multi_assert("claim_chapter", cid, rec.get("supports_chapters"))
        _multi_assert("conflict_decl", cid, rec.get("conflicts_with"))
        _multi_assert("implies", cid, rec.get("implies"))
    return any_subject


def _multi_assert(pred: str, cid: str, values: Any) -> None:
    for v in values or []:
        pyDatalog.assert_fact(pred, cid, str(v))


def _collect(predicate: str, arity: int) -> list[tuple]:
    args = ", ".join(f"X{i}" for i in range(arity))
    pyDatalog.create_terms(args)
    out = pyDatalog.ask(f"{predicate}({args})")
    if out is None:
        return []
    return sorted(row for row in out.answers if SENTINEL not in row)


def _emit_pairs(rule: str, cls: str, pairs: Iterable[tuple], detail_fmt: str,
                bucket: list[dict], skip: set) -> set:
    """Append pair-defects to bucket, deduped by sorted (a, b)."""
    added: set = set()
    for a, b in pairs:
        key = tuple(sorted([str(a), str(b)]))
        if key in skip or key in added: continue
        added.add(key)
        bucket.append({"class": cls, "rule": rule, "facts": [a, b],
                       "detail": detail_fmt.format(a=a, b=b)})
    return added


def run(workspace: Path) -> DefectReport:
    workspace = workspace.resolve()
    ttl_path = workspace / ".knowledge" / "thesis-triples.ttl"
    if not ttl_path.exists():
        raise FileNotFoundError(f"missing thesis triples: {ttl_path}")

    pyDatalog.clear()
    pyDatalog.create_terms(TERMS)
    for name, arity in EXTENSIONAL:
        pyDatalog.assert_fact(name, *([SENTINEL] * arity))

    graph = Graph()
    graph.parse(ttl_path, format="turtle")
    _assert_thesis_facts(graph)

    have_subjects = False
    claims_path = _resolve_claims_path(workspace)
    if claims_path is not None:
        have_subjects = _assert_claim_facts(_iter_claims(claims_path))

    pyDatalog.load(RULES_FILE.read_text(encoding="utf-8"))

    report = DefectReport()
    for (p,) in _collect("orphan_paragraph", 1):
        report.orphans.append({"class": "D9", "rule": "orphan_paragraph", "facts": [p],
            "detail": f"paragraph {p!r} does not reach :Thesis through supports edges"})
    direct = _emit_pairs("direct_contradiction", "D10",
        _collect("direct_contradiction", 2),
        "claims {a!r} and {b!r} assert different values for the same subject",
        report.contradictions, skip=set())
    _emit_pairs("transitive_contradiction", "D10",
        _collect("transitive_contradiction", 2),
        "claim {a!r} transitively contradicts {b!r}", report.contradictions, skip=direct)
    _emit_pairs("declared_conflict", "D11", _collect("declared_conflict", 2),
        "ledger declares {a!r} conflicts_with {b!r}", report.invariants, skip=set())
    for (p,) in _collect("unreachable_supports", 1):
        report.invariants.append({"class": "D11", "rule": "unreachable_supports", "facts": [p],
            "detail": f"{p!r} supports a node that is neither :Thesis nor a SubArgument"})
    for cid, inv in _collect("invariant_violation", 2):
        report.invariants.append({"class": "D11", "rule": "invariant_violation", "facts": [cid, inv],
            "detail": f"claim {cid!r} violates authored invariant {inv!r}"})
    # NB: this is the chapter-coverage invariant, NOT book-qa's D12
    # ("unadvanced-sub-argument" = named by no paragraph's supports, computed by
    # lint_supports from qa/supports-defects.json). Distinct class + rule name
    # so the two are never conflated.
    for (n,) in _collect("sub_arg_no_chapter", 1):
        report.invariants.append({"class": "D11", "rule": "sub_arg_no_chapter", "facts": [n],
            "detail": f"sub-argument {n!r} is advanced by no chapter"})
    # Evidence-slot satisfaction is only meaningful when the ledger carries
    # structured claim subjects to match against required-evidence slots. With
    # no subjects asserted, every slot is trivially "unmet"; reporting that
    # would flood D11 with false positives on a real ledger, so skip it.
    if have_subjects:
        for n, e in _collect("missing_evidence", 2):
            report.invariants.append({"class": "D11", "rule": "missing_evidence", "facts": [n, e],
                "detail": f"sub-argument {n!r} requires evidence {e!r} that no claim's subject meets"})

    out = workspace / "qa" / "datalog-defects.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report.as_payload(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: datalog_consistency.py <workspace>", file=sys.stderr)
        return 2
    try:
        report = run(Path(argv[1]))
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    s = report.as_payload()["summary"]
    print(f"datalog consistency: contradictions={s['contradictions']} "
          f"orphans={s['orphans']} invariant_violations={s['invariant_violations']}")
    return 1 if report.gate_failed() else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
