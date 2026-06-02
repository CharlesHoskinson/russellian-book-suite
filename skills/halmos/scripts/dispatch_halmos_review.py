"""Assemble the Halmos-reviewer payload and dispatch one subagent (caller-provided dispatcher)."""
from __future__ import annotations
import json, re
from pathlib import Path
from typing import Callable, Optional

from scripts.build_linkage import build_linkage, _body_paras, _chapter_n


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8") if p.is_file() else ""


def _contract_purpose(workspace: Path, cid: str) -> str:
    f = workspace / "chapters" / "contracts" / f"{cid}.yaml"
    if not f.is_file():
        return ""
    for line in f.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\s*purpose:\s*(.*)", line)
        if m:
            return m.group(1).strip().strip("'\"")[:200]
    return ""


def _concepts_by_chapter(workspace: Path) -> dict[str, list[dict]]:
    p = workspace / "halmos" / "concepts.jsonl"
    by: dict[str, list[dict]] = {}
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                by.setdefault(r["introduced_in"], []).append(r)
    return by


def build_payload(workspace: Path, chapter_id: str) -> dict:
    workspace = Path(workspace)
    n = _chapter_n(chapter_id)
    draft = _read(workspace / "chapters" / "drafts" / chapter_id / "draft.md")
    linkage = build_linkage(workspace, chapter_id)
    by = _concepts_by_chapter(workspace)
    priors = []
    for i in range(1, n):
        pid = f"ch-{i:02d}"
        body = _read(workspace / "chapters" / "drafts" / pid / "draft.md")
        if not body:
            continue
        paras = _body_paras(body)
        priors.append({
            "chapter_id": pid,
            "thesis": _contract_purpose(workspace, pid),
            "introduces": [{"concept": c["concept"], "gloss": c["gloss"]} for c in by.get(pid, [])],
            "closing": paras[-1][:400] if paras else "",
        })
    return {"chapter_id": chapter_id, "draft": draft, "priors": priors, "linkage": linkage}


def dispatch_halmos_review(workspace: Path, chapter_id: str,
                           dispatcher: Optional[Callable[[dict], dict]] = None) -> dict:
    """Returns the agent findings dict. In production the dispatcher issues a Task-tool
    call running references/halmos-doctrine.md; in tests it returns a canned dict."""
    payload = build_payload(workspace, chapter_id)
    if dispatcher is None:
        raise ValueError("dispatch_halmos_review requires a dispatcher (Task-tool call or stub)")
    findings = dispatcher(payload)
    findings.setdefault("spiral_coherence", "acceptable")
    findings.setdefault("findings", [])
    findings.setdefault("per_prior_chapter", {})
    return findings
