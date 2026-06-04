"""Build syntopical/positions.edn from schools + ledger + prov sidecar.

Reads:
  <workspace>/syntopical/schools/*.edn
  <workspace>/syntopical/governance-config.edn      (auto-created if absent)
  <workspace>/knowledge/claims/ledger.jsonl
  <workspace>/rules/booklogic/induced-theory.prov.edn
  <workspace>/rules/constraints.edn                 (compiled, preferred)
  <workspace>/rules/booklogic/constraints.edn        (source fallback)

Writes:
  <workspace>/syntopical/positions.edn
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from ._schools import load_schools_dir
from ._config import load_or_create_config
from ._stance import derive_stance, RuleEvidence
from ._positions_io import Position, write_positions
from ._constraints import load_constraints


def _claim_doc_index(ledger_path: Path) -> dict[str, list[str]]:
    """claim_id -> list of doc_ids (last-wins on state transitions)."""
    out: dict[str, list[str]] = {}
    if not ledger_path.exists():
        return out
    for line in ledger_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if r.get("status") != "verified":
            continue
        out[r["claim_id"]] = [s["doc_id"] for s in r.get("source_spans", [])]
    return out


def _load_prov_sidecar(path: Path) -> dict[str, dict]:
    """Tolerant reader for induced-theory.prov.edn -- pulls out per-rule
    :prov/derived-from-atoms, :prov/source-documents,
    :prov/contradiction-atoms only."""
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    rules: dict[str, dict] = {}
    rule_re = re.compile(r'"([^"]+)"\s*\{(.*?)\}\}', re.DOTALL)
    for m in rule_re.finditer(text):
        rule_id, body = m.group(1), m.group(2)
        atoms = re.search(r":prov/derived-from-atoms\s*\[([^\]]*)\]", body)
        docs = re.search(r":prov/source-documents\s*\[([^\]]*)\]", body)
        contras = re.search(r":prov/contradiction-atoms\s*\[([^\]]*)\]", body)
        rules[rule_id] = {
            "atoms": _str_vec(atoms.group(1)) if atoms else [],
            "docs":  _str_vec(docs.group(1))  if docs  else [],
            "contras": _str_vec(contras.group(1)) if contras else [],
        }
    return rules


def _str_vec(s: str) -> list[str]:
    return [m.strip('"') for m in re.findall(r'"[^"]*"', s)]


def _emit_rows(rule_id, source, evidence, schools, config, induction_prov):
    rows = []
    for school in schools:
        stance = derive_stance(school, evidence, config)
        declared = (rule_id in school.canonical_asserts
                    or rule_id in school.canonical_rejects)
        rows.append(Position(
            rule_id=rule_id,
            rule_form="",
            source=source,
            school=school.slug,
            stance=stance,
            supporting_atoms=list(evidence.supporting_atoms),
            supporting_docs=list(evidence.supporting_docs),
            contradicting_atoms=list(evidence.contradicting_atoms),
            contradicting_docs=list(evidence.contradicting_docs),
            declared_by_charter=declared,
            induction_prov=induction_prov,
        ))
    return rows


def build_positions(workspace: Path, generated_at: str | None = None) -> Path:
    workspace = Path(workspace).resolve()
    syntopical = workspace / "syntopical"

    config = load_or_create_config(syntopical / "governance-config.edn")
    schools = load_schools_dir(syntopical / "schools")

    claim_docs = _claim_doc_index(workspace / "knowledge" / "claims" / "ledger.jsonl")
    prov = _load_prov_sidecar(workspace / "rules" / "booklogic" / "induced-theory.prov.edn")

    if generated_at is None:
        generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    constraints_path = workspace / "rules" / "constraints.edn"
    if not constraints_path.exists():
        constraints_path = workspace / "rules" / "booklogic" / "constraints.edn"
    constraints = load_constraints(constraints_path)

    positions: list[Position] = []
    for rule_id, prov_data in prov.items():
        supporting_docs = list(dict.fromkeys(prov_data["docs"]))
        contradicting_docs = list(dict.fromkeys(
            [d for atom in prov_data["contras"] for d in claim_docs.get(atom, [])]
        ))
        evidence = RuleEvidence(
            rule_id=rule_id,
            supporting_docs=supporting_docs,
            contradicting_docs=contradicting_docs,
            supporting_atoms=list(prov_data["atoms"]),
            contradicting_atoms=list(prov_data["contras"]),
        )
        positions += _emit_rows(
            rule_id, "induced", evidence, schools, config,
            f"induced-theory.prov.edn#{rule_id}")

    for cid, cdata in constraints.items():
        track = cdata.get("track")
        track_claim = track.lstrip(":") if track else None
        if track_claim and track_claim in claim_docs:
            supporting_atoms = [track_claim]
            supporting_docs = list(dict.fromkeys(claim_docs[track_claim]))
        else:
            supporting_atoms = []
            supporting_docs = []
        evidence = RuleEvidence(
            rule_id=cid,
            supporting_docs=supporting_docs,
            contradicting_docs=[],
            supporting_atoms=supporting_atoms,
            contradicting_atoms=[],
        )
        positions += _emit_rows(
            cid, "defconstraint", evidence, schools, config,
            f"constraints.edn#{cid}")

    out_path = syntopical / "positions.edn"
    write_positions(out_path, positions, generated_at=generated_at)
    return out_path


def _main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        prog="python -m scripts.governance.build_positions",
        description="Build syntopical/positions.edn from schools + ledger + prov sidecar.",
    )
    ap.add_argument("workspace", type=Path)
    args = ap.parse_args(argv)
    out = build_positions(args.workspace)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
