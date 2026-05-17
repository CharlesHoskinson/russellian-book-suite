"""Read QA tickets, propose ledger transitions; write to claims/ and qa/ reports."""
from __future__ import annotations

import json
from pathlib import Path

from .booklogic_remedies import load_remedies, match_remedies_against_verdict
from .transition_rules import map_ticket_to_proposed_transition, map_remedy_proposal_to_transition


def _read_verdict(workspace_root: Path) -> dict | None:
    """Locate a verdict.edn under the workspace; parse if present."""
    candidates = [
        workspace_root / "verifier-work" / "verdict.edn",
        workspace_root / "work" / "verdict.edn",
        workspace_root / "verdict.edn",
    ]
    for p in candidates:
        if p.exists():
            edn_mod = _get_edn_reader()
            Keyword  = edn_mod.Keyword
            read_edn = edn_mod.read_edn
            payload = read_edn(p.read_text(encoding="utf-8"))
            return {
                "verdict":        _kw_name(payload.get(Keyword("verdict")), Keyword),
                "core":           payload.get(Keyword("core"), []),
                "low_confidence": payload.get(Keyword("low-confidence"), []),
            }
    return None


def _get_edn_reader():
    """Lazy-load the neurosym-forge EDN reader (same strategy as booklogic_remedies)."""
    import importlib.util, sys as _sys
    _mod_name = "_nf_edn_reader"
    if _mod_name in _sys.modules:
        return _sys.modules[_mod_name]
    _reader_path = (
        Path(__file__).resolve().parents[3]
        / "skills" / "neurosym-forge" / "scripts" / "_edn_reader.py"
    )
    spec = importlib.util.spec_from_file_location(_mod_name, _reader_path)
    mod  = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    _sys.modules[_mod_name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _kw_name(v, Keyword):
    if isinstance(v, Keyword):
        return v.name
    return v


def _load_booklogic_remedy_proposals(workspace_root: Path) -> list[dict]:
    """Match `rules/remedies.edn` against any present verdict.edn."""
    remedies_path = workspace_root / "rules" / "remedies.edn"
    remedies = load_remedies(remedies_path)
    if not remedies:
        return []
    verdict = _read_verdict(workspace_root)
    if verdict is None:
        return []
    return match_remedies_against_verdict(remedies, verdict)


def _defect_to_ticket(defect: dict, index: int) -> dict | None:
    """Translate a row from ``qa/defects.json`` into a writeback ticket.

    Only defects that carry a ``claim_id`` are candidates for writeback;
    everything else (mechanical D1-D8 manuscript hygiene, etc.) is skipped
    here and surfaces via Sentinel/Healer instead. The ``class`` is
    preserved verbatim so ``transition_rules`` can dispatch on its
    existing synonym sets (notably ``D11`` -> ``unsupported_claim``).
    """
    if not isinstance(defect, dict):
        return None
    claim_id = defect.get("claim_id")
    if not claim_id:
        return None
    cls = defect.get("class") or defect.get("class_") or "D?"
    tid = defect.get("id") or f"defect-{cls}-{index:04d}"
    return {
        "id": tid,
        "class": cls,
        "claim_id": claim_id,
        "claim_current_status": defect.get("claim_current_status"),
        "severity": defect.get("severity", "important"),
    }


def _load_tickets(qa_dir: Path) -> list[dict]:
    tickets: list[dict] = []
    # Legacy fixture filenames retained for backwards-compatible test fixtures
    # and any external pipeline still emitting them. Production currently writes
    # neither file; the new defects.json source below is the canonical input.
    for name in ("lint-findings.json", "swarm-findings.json"):
        p = qa_dir / name
        if not p.exists():
            continue
        payload = json.loads(p.read_text(encoding="utf-8"))
        tickets.extend(payload.get("tickets", []))
    # Canonical Stage-1 source: defects.json emitted by lint_artifact.py.
    # Only defects bound to a claim_id become writeback tickets; the rest are
    # filtered out by _defect_to_ticket.
    defects_path = qa_dir / "defects.json"
    if defects_path.exists():
        payload = json.loads(defects_path.read_text(encoding="utf-8"))
        for i, d in enumerate(payload.get("defects", [])):
            t = _defect_to_ticket(d, i)
            if t is not None:
                tickets.append(t)
    return tickets


def propose_writeback(workspace_root: Path, version: str) -> Path:
    """Emit proposed ledger transitions from current QA findings.

    The output file `claims/proposed-transitions.jsonl` is OVERWRITTEN on each
    call — it is a per-build scratch artifact, not an accumulating log.
    Consumers (`apply_writeback.py`) must process it before the next sentinel
    run, or earlier proposals are lost.
    """
    qa_dir = workspace_root / "qa"
    claims_dir = workspace_root / "claims"
    claims_dir.mkdir(parents=True, exist_ok=True)
    tickets = _load_tickets(qa_dir)
    # BookLogic remedy proposals (REQ-QA-PIPE-010).
    remedy_proposals = _load_booklogic_remedy_proposals(workspace_root)
    proposed: list[dict] = []
    for t in tickets:
        m = map_ticket_to_proposed_transition(t)
        if m is not None:
            m["severity"] = t.get("severity", "important")
            proposed.append(m)
    # Merge remedy-driven proposals (REQ-QA-PIPE-011).
    for rp in remedy_proposals:
        m = map_remedy_proposal_to_transition(rp)
        if m is None:
            continue
        m["severity"] = rp.get("severity", "important")
        proposed.append(m)
    out_jsonl = claims_dir / "proposed-transitions.jsonl"
    # Intentional truncate-and-write: per-build scratch, consumed by apply_writeback.
    with out_jsonl.open("w", encoding="utf-8") as fh:
        for p in proposed:
            # Preserve existing schema; add booklogic-driven fields with defaults.
            p.setdefault("requires", "auto-apply")
            p.setdefault("auto_apply", True)
            fh.write(json.dumps(p, sort_keys=True) + "\n")
    md_lines = [f"# Ledger writeback proposals — {version}", "",
                f"Total: {len(proposed)} proposed transition(s).", ""]
    md_lines.append("| kind | target | from→to / new_status | ticket | severity |")
    md_lines.append("|---|---|---|---|---|")
    for p in proposed:
        if p["kind"] == "claim":
            from_ = p.get("from", "?")
            md_lines.append(f"| claim | {p['claim_id']} | {from_}→{p['to']} | {p['cause_ticket_id']} | {p['severity']} |")
        else:
            md_lines.append(f"| counter_claim | {p['counter_claim_id']} | →{p['new_status']} | {p['cause_ticket_id']} | {p['severity']} |")
    out_md = qa_dir / f"ledger-writeback-{version}.md"
    out_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return out_md
