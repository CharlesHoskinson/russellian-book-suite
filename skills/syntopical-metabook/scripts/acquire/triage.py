"""Partition scored candidates into auto-approve / manual-review / reject buckets
per REQ-ACQ-3 and write the triage file."""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from scripts.acquire.rank_candidates import ScoredCandidate

@dataclass
class TriageConfig:
    t_high: float = 0.75
    t_low: float = 0.55
    max_auto_per_run: int = 25

@dataclass
class TriageResult:
    run_id: str
    auto_approve: list[ScoredCandidate] = field(default_factory=list)
    manual_review: list[ScoredCandidate] = field(default_factory=list)
    reject: list[ScoredCandidate] = field(default_factory=list)
    notes: dict[str, list[str]] = field(default_factory=dict)  # candidate_id -> annotations

def triage(scored: list[ScoredCandidate], cfg: TriageConfig,
           workspace_root: Path, run_id: str) -> TriageResult:
    res = TriageResult(run_id=run_id)
    # Sort descending by score so cap applies to top-N
    ranked = sorted(scored, key=lambda c: -c.score)
    auto_quota = cfg.max_auto_per_run
    for c in ranked:
        if c.score >= cfg.t_high and len(res.auto_approve) < auto_quota:
            res.auto_approve.append(c)
        elif c.score >= cfg.t_high:
            res.manual_review.append(c)  # over the cap
        elif c.score >= cfg.t_low:
            res.manual_review.append(c)
        else:
            res.reject.append(c)
    _write_triage_file(res, workspace_root, cfg)
    return res

def _write_triage_file(res: TriageResult, workspace_root: Path, cfg: TriageConfig) -> None:
    d = workspace_root / "syntopical" / "acquisition"
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"triage-{res.run_id}.md"
    lines = [
        f"# Triage Run {res.run_id}",
        "",
        f"Thresholds: T_high={cfg.t_high}, T_low={cfg.t_low}, max_auto_per_run={cfg.max_auto_per_run}",
        "",
        "## auto-approve",
        "",
    ]
    for c in res.auto_approve:
        ann = " ".join(res.notes.get(c.id, []))
        lines.append(f"- [x] {c.id} (score={c.score:.3f}){' — ' + ann if ann else ''}")
    lines += ["", "## manual-review", ""]
    for c in res.manual_review:
        ann = " ".join(res.notes.get(c.id, []))
        lines.append(f"- [ ] {c.id} (score={c.score:.3f}){' — ' + ann if ann else ''}")
    lines += ["", "## reject", ""]
    for c in res.reject:
        lines.append(f"- {c.id} (score={c.score:.3f})")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
