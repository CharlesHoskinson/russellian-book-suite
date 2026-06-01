"""Build halmos/concepts.jsonl: book concepts with the earliest chapter that introduces them."""
from __future__ import annotations
import json, re
from pathlib import Path

TITLE_CASE = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})\b")
_STOP = {"Multi Agent", "United States", "Open Wallet", "Project Sid", "Verifiable Credentials"}
# Leading words to drop from a matched phrase (a sentence-initial "The Authority Airgap"
# should harvest as "Authority Airgap").
_ARTICLES = {"The", "A", "An", "This", "That", "These", "Those"}


def _norm(t: str) -> str:
    return re.sub(r"\s+", " ", t).strip().lower()


def _slug(t: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", _norm(t)).strip("-")


def _chapter_n(chapter_id: str) -> int:
    m = re.search(r"(\d+)", chapter_id)
    return int(m.group(1)) if m else 0


def harvest_title_case(text: str) -> list[str]:
    """Distinct Title-Case multi-word phrases (leading article dropped), minus stop phrases."""
    seen, out = set(), []
    for m in TITLE_CASE.finditer(text):
        words = m.group(1).split()
        if words and words[0] in _ARTICLES:
            words = words[1:]
        if len(words) < 2:
            continue
        phrase = " ".join(words)
        if phrase in _STOP or phrase in seen:
            continue
        seen.add(phrase)
        out.append(phrase)
    return out


def _load_seed(seed_path: Path) -> list[tuple[str, list[str]]]:
    rows = []
    if seed_path and seed_path.exists():
        for line in seed_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p.strip() for p in line.split("|")]
            rows.append((parts[0], parts[1:]))
    return rows


def _chapter_bodies(workspace: Path) -> list[tuple[str, str]]:
    drafts = workspace / "chapters" / "drafts"
    out = []
    for d in sorted(drafts.glob("ch-*")):
        f = d / "draft.md"
        if f.is_file():
            out.append((d.name, f.read_text(encoding="utf-8")))
    return out


def build_concept_ledger(workspace: Path, seed_path: Path | None = None) -> Path:
    workspace = Path(workspace)
    if seed_path is None:
        seed_path = Path(__file__).resolve().parent.parent / "references" / "seed-concepts.txt"
    bodies = _chapter_bodies(workspace)
    seed = _load_seed(seed_path)

    candidates: dict[str, set[str]] = {}
    for canon, aliases in seed:
        candidates.setdefault(canon, set()).update(aliases)
    counts: dict[str, int] = {}
    for _, body in bodies:
        for phrase in harvest_title_case(body):
            counts[phrase] = counts.get(phrase, 0) + 1
    for phrase, c in counts.items():
        if c >= 2 and phrase not in candidates:
            candidates[phrase] = set()

    records = []
    for canon, aliases in candidates.items():
        forms = [canon] + sorted(aliases)
        norms = [_norm(f) for f in forms]
        intro_cid, gloss = None, ""
        for cid, body in bodies:
            nbody = _norm(body)
            if any(f in nbody for f in norms):
                intro_cid = cid
                for sent in re.split(r"(?<=[.;:]) ", body):
                    if any(f in _norm(sent) for f in norms):
                        gloss = re.sub(r"\s+", " ", sent).strip()[:160]
                        break
                break
        if intro_cid is None:
            continue
        records.append({
            "concept": canon, "slug": _slug(canon), "gloss": gloss,
            "introduced_in": intro_cid, "intro_n": _chapter_n(intro_cid),
            "aliases": sorted(aliases), "source": "device",
        })

    out_dir = workspace / "halmos"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "concepts.jsonl"
    out.write_text("\n".join(json.dumps(r) for r in records) + ("\n" if records else ""), encoding="utf-8")
    return out
