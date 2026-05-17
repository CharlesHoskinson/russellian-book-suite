"""Apply the booklogic post-rank symbolic veto (REQ-VETO-1/2).

When triage marks a candidate as auto-approve, call booklogic to verify it is
reachable from the chapter's thesis tree. Demote unreachable candidates to
manual-review with a `booklogic-veto` annotation that includes the rule-trace.
Bypass entirely if SYNTOPICAL_NO_BOOKLOGIC=1.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
from types import SimpleNamespace
from scripts.acquire.triage import TriageResult
from scripts.booklogic_adapter import reachable_from_thesis as _reachable_from_thesis, BooklogicError

def apply_veto(tr: TriageResult, thesis_tree, candidate_lookup: dict,
               manifest_path: Path) -> TriageResult:
    if os.environ.get("SYNTOPICAL_NO_BOOKLOGIC") == "1":
        _append_warning(manifest_path, {
            "kind": "booklogic-veto-skipped",
            "candidate_ids": [c.id for c in tr.auto_approve],
            "reason": "env",
        })
        return tr

    demoted: list = []
    for c in list(tr.auto_approve):
        cand_obj = candidate_lookup.get(c.id)
        if cand_obj is None:
            # No candidate metadata available — skip veto, keep approval.
            continue
        # Adapter expects an object with .id / .extracted_concepts / .embedding_score
        cand = SimpleNamespace(**cand_obj) if isinstance(cand_obj, dict) else cand_obj
        try:
            v = _reachable_from_thesis(cand, thesis_tree)
        except BooklogicError as e:
            # Veto skip on adapter failure — log to manifest and keep the candidate.
            _append_warning(manifest_path, {
                "kind": "booklogic-veto-skipped",
                "candidate_ids": [c.id],
                "reason": f"booklogic-error: {e}",
            })
            continue
        if not v.reachable:
            tr.auto_approve.remove(c)
            tr.manual_review.append(c)
            ann = f"booklogic-veto rule-trace={v.rule_trace}"
            tr.notes.setdefault(c.id, []).append(ann)
            demoted.append(c.id)
    return tr

def _append_warning(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")
