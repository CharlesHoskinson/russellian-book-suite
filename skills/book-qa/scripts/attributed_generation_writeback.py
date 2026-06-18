"""Write attributed-generation proposal records under qa/."""
from __future__ import annotations

import json
from pathlib import Path


def proposed_transitions_path(workspace_root: Path) -> Path:
    return Path(workspace_root) / "qa" / "proposed-transitions.jsonl"


def write_novel_draft_claim_proposals(
    workspace_root: Path, proposals: list[dict]
) -> Path:
    """Append novel-draft-claim proposals for book-knowledge writeback review."""
    out = proposed_transitions_path(workspace_root)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("a", encoding="utf-8", newline="\n") as fh:
        for proposal in proposals:
            record = dict(proposal)
            record.setdefault("kind", "novel_draft_claim")
            record.setdefault("requires", "human-review")
            record.setdefault("auto_apply", False)
            fh.write(json.dumps(record, sort_keys=True) + "\n")
    return out
