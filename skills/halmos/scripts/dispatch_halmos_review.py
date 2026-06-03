"""Assemble the Halmos-reviewer payload and dispatch one subagent (caller-provided dispatcher)."""
from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Callable, Optional

from scripts.build_linkage import build_linkage, _body_paras
from scripts.ids import chapter_n


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8") if p.is_file() else ""


def _contract_purpose(workspace: Path, cid: str) -> str:
    f = workspace / "chapters" / "contracts" / f"{cid}.yaml"
    if not f.is_file():
        return ""
    lines = f.read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(lines):
        m = re.match(r"purpose:\s*(.*)", line)
        if not m:
            continue
        val = m.group(1).strip()
        if not val or re.fullmatch(r"[>|][+\-0-9]*", val):
            block = []
            for nxt in lines[i + 1:]:
                if nxt.strip() and not nxt[:1].isspace():
                    break
                if nxt.strip():
                    block.append(nxt.strip())
            return " ".join(block)[:200]
        return val.strip("'\"")[:200]
    return ""


def _concepts_by_chapter(workspace: Path) -> dict[str, list[dict]]:
    p = workspace / "halmos" / "concepts.jsonl"
    by: dict[str, list[dict]] = {}
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            by.setdefault(r["introduced_in"], []).append(r)
    return by


def build_payload(workspace: Path, chapter_id: str) -> dict:
    workspace = Path(workspace)
    n = chapter_n(chapter_id)
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
            "introduces": [{"concept": c["concept"], "gloss": c["gloss"], "source": c.get("source", "seed")} for c in by.get(pid, [])],
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
