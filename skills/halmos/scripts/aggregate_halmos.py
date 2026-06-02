"""Merge deterministic + agent findings into halmos-verdict.json and halmos-review.md."""
from __future__ import annotations
import json
from pathlib import Path


def _key(f: dict) -> tuple:
    # Dedup by (check, target). When a finding has no concept and no prior_chapter,
    # fall back to its detail text so two distinct target-less findings of the same
    # check (e.g. two continuity-gaps with prior_chapter=null) are not collapsed.
    return (f.get("check"), f.get("concept") or f.get("prior_chapter") or f.get("detail") or "")


def rollup(linkage: dict, agent_findings: dict) -> dict:
    merged: dict[tuple, dict] = {}
    for f in linkage.get("flags", []):
        merged[_key(f)] = {"check": f["check"], "severity": f["severity"],
                           "concept": f.get("concept"), "prior_chapter": None,
                           "detail": f.get("detail", ""), "fix": "", "source": "deterministic"}
    for f in agent_findings.get("findings", []):
        k = _key(f)
        if k in merged:
            if f.get("fix"):
                merged[k]["fix"] = f["fix"]
            continue
        merged[k] = {"check": f["check"], "severity": f["severity"],
                     "concept": f.get("concept"), "prior_chapter": f.get("prior_chapter"),
                     "detail": f.get("detail", ""), "fix": f.get("fix", ""), "source": "agent"}
    findings = list(merged.values())
    counts = {"critical": 0, "important": 0, "minor": 0}
    for f in findings:
        if f["severity"] in counts:
            counts[f["severity"]] += 1
    return {
        "halmos_critical_count": counts["critical"],
        "important_count": counts["important"],
        "minor_count": counts["minor"],
        "spiral_coherence": agent_findings.get("spiral_coherence", "acceptable"),
        "per_prior_chapter": agent_findings.get("per_prior_chapter", {}),
        "findings": findings,
    }


def aggregate_halmos(workspace: Path, chapter_id: str, agent_findings: dict, linkage: dict) -> Path:
    workspace = Path(workspace)
    merged = rollup(linkage, agent_findings)
    draft_dir = workspace / "chapters" / "drafts" / chapter_id
    verdict = {
        "chapter_id": chapter_id,
        "halmos_critical_count": merged["halmos_critical_count"],
        "important_count": merged["important_count"],
        "minor_count": merged["minor_count"],
        "spiral_coherence": merged["spiral_coherence"],
        "per_prior_chapter": merged["per_prior_chapter"],
        "reviews_complete": True,
    }
    (draft_dir / "halmos-verdict.json").write_text(json.dumps(verdict, indent=2), encoding="utf-8")

    lines = [f"# Halmos linkage review ({chapter_id})", "",
             f"Spiral coherence: **{merged['spiral_coherence']}**. "
             f"Critical {merged['halmos_critical_count']}, important {merged['important_count']}, "
             f"minor {merged['minor_count']}.", "",
             f"Seam: {linkage.get('seam', {}).get('status', 'unknown')} "
             f"(overlap: {', '.join(linkage.get('seam', {}).get('overlap', [])) or 'none'}).", ""]
    if merged["findings"]:
        lines.append("## Findings")
        for f in sorted(merged["findings"], key=lambda x: {"critical": 0, "important": 1, "minor": 2}.get(x["severity"], 3)):
            tgt = f.get("concept") or f.get("prior_chapter") or ""
            lines.append(f"- **[{f['severity']}] {f['check']}** {tgt}: {f['detail']}"
                         + (f"  _Fix:_ {f['fix']}" if f.get("fix") else ""))
        lines.append("")
    if merged["per_prior_chapter"]:
        lines.append("## Linkage to prior chapters")
        for cid in sorted(merged["per_prior_chapter"]):
            lines.append(f"- {cid}: {merged['per_prior_chapter'][cid]}")
        lines.append("")
    (draft_dir / "halmos-review.md").write_text("\n".join(lines), encoding="utf-8")
    return draft_dir / "halmos-verdict.json"
