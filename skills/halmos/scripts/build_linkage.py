"""Deterministic cross-chapter linkage for one chapter: references, seam, broken-seam flag."""
from __future__ import annotations
import json, re
from pathlib import Path

from scripts.ids import chapter_n

STOPWORDS = set((
    "a an the of to in on and or but is are was were be been being it its that this these those "
    "for with as by at from into onto out up down over under above below then than so such only "
    "even more most some many any each other else when where which while what who whom whose how "
    "have has had not no nor also about across among against during without within after before "
    "because between through upon would could should might must may can will shall do does did "
    "their there here they them you your our his her she him we us i me my"
).split())


def _norm(t: str) -> str:
    return re.sub(r"\s+", " ", t).strip().lower()


def _content_words(s: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]+", s.lower()) if w not in STOPWORDS and len(w) > 3}


def seam_status(prev_close: str, this_open: str, min_overlap: int = 1) -> tuple[str, list[str]]:
    if not prev_close or not this_open:
        return "unknown", []
    overlap = sorted(_content_words(prev_close) & _content_words(this_open))
    return ("clean" if len(overlap) >= min_overlap else "broken"), overlap


def _load_concepts(workspace: Path) -> list[dict]:
    p = Path(workspace) / "halmos" / "concepts.jsonl"
    if not p.exists():
        return []
    out = []
    for l in p.read_text(encoding="utf-8").splitlines():
        if not l.strip():
            continue
        try:
            out.append(json.loads(l))
        except json.JSONDecodeError:
            continue
    return out


def _body_paras(text: str) -> list[str]:
    return [l.strip() for l in text.splitlines()
            if l.strip() and not l.strip().startswith(("#", "[^"))]


def build_linkage(workspace: Path, chapter_id: str) -> dict:
    workspace = Path(workspace)
    n = chapter_n(chapter_id)
    draft_file = workspace / "chapters" / "drafts" / chapter_id / "draft.md"
    if not draft_file.is_file():
        raise FileNotFoundError(f"no draft to review for {chapter_id}: {draft_file}")
    body = draft_file.read_text(encoding="utf-8")
    nbody = _norm(body)
    concepts = _load_concepts(workspace)

    references, introduces, flags = [], [], []
    for c in concepts:
        forms = [_norm(c["concept"])] + [_norm(a) for a in c.get("aliases", [])]
        if any(f in nbody for f in forms):
            references.append(c["slug"])
        if c["introduced_in"] == chapter_id:
            introduces.append(c["slug"])

    paras = _body_paras(body)
    this_open = paras[0] if paras else ""
    prev_id = f"ch-{n-1:02d}"
    prev_file = workspace / "chapters" / "drafts" / prev_id / "draft.md"
    prev_close = ""
    if prev_file.is_file():
        pp = _body_paras(prev_file.read_text(encoding="utf-8"))
        prev_close = pp[-1] if pp else ""
    status, overlap = seam_status(prev_close, this_open)
    if status == "broken":
        flags.append({"check": "broken-seam", "severity": "critical", "concept": None,
                      "detail": f"{prev_id} close and {chapter_id} open share no salient terms"})

    link = {"chapter_id": chapter_id, "n": n,
            "references": sorted(set(references)), "introduces": sorted(set(introduces)),
            "seam": {"prev_close": prev_close[:300], "this_open": this_open[:300],
                     "status": status, "overlap": overlap},
            "flags": flags}

    out_dir = workspace / "halmos" / "linkage"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{chapter_id}.json").write_text(json.dumps(link, indent=2), encoding="utf-8")
    return link
