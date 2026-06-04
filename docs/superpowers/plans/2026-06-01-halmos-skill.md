# halmos Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `halmos` skill: a per-chapter, sequential cross-chapter linkage review that audits chapter N against chapters 1…N−1 (concept linkage, handoff seams, spiral build) and soft-gates the chapter on broken links.

**Architecture:** A deterministic layer (a concept ledger + a linkage computation with one mechanically-decidable critical flag — broken-seam) plus a Halmos-reviewer agent that adjudicates the semantic checks (orphan-reference, missed-recall, spiral-stall, continuity-gap, terminology-drift, premature-definition). An aggregator merges both into `halmos-verdict.json`; `book-compose`'s contract check reads `halmos_critical_count` as a gating metric.

**Tech Stack:** Python 3.11+, pytest, stdlib only (json, re, pathlib). Mirrors `skills/review-conductor` conventions (caller-provided dispatcher, stub-tested; `pytest.mark.windows_canary`; per-skill `.venv`).

**Spec:** `docs/superpowers/specs/2026-06-01-halmos-skill-design.md`.

> **Superseded during implementation:** the deterministic `forward-reference` flag described in several tasks below was eliminated — a concept appearing in N has `intro_n ≤ N` by construction, so reference-before-introduction cannot be decided mechanically. `broken-seam` is the only deterministic critical flag; reference-before-introduction is the agent-owned `orphan-reference` check (see `references/halmos-doctrine.md`). Read the `forward-reference` mentions in the tasks and example payloads below as that agent-owned check.

---

## File structure

```
skills/halmos/
  SKILL.md
  README.md
  pyproject.toml
  references/
    halmos-doctrine.md        # the reviewer brief + per-check rubric (agent persona)
    seed-concepts.txt         # curated book devices: "Canonical Term | alias | alias"
  scripts/
    __init__.py
    concept_ledger.py         # build_concept_ledger() -> halmos/concepts.jsonl
    build_linkage.py          # build_linkage(), seam_status() -> halmos/linkage/ch-NN.json
    dispatch_halmos_review.py # build_payload(), dispatch_halmos_review()
    aggregate_halmos.py       # aggregate_halmos(), rollup()
    conductor.py              # run_halmos() chains the four
  skill_api.py                # public exports + SKILL_API_VERSION
  tests/
    __init__.py
    fixtures/                 # tiny synthetic workspaces
    test_concept_ledger.py
    test_build_linkage.py
    test_aggregate_halmos.py
    test_conductor_integration.py
    test_contract_gate.py     # lives here; exercises the book-compose metric
```

**Data shapes (fixed; used identically across tasks):**

```python
# halmos/concepts.jsonl  — one concept per line
{"concept": "Authority Airgap", "slug": "authority-airgap", "gloss": "the power to think kept apart from the power to bind",
 "introduced_in": "ch-07", "intro_n": 7, "aliases": ["the airgap"], "source": "device"}

# halmos/linkage/ch-NN.json
{"chapter_id": "ch-09", "n": 9,
 "references": ["authority-airgap", "settlement"], "introduces": ["court"],
 "seam": {"prev_close": "...", "this_open": "...", "status": "broken", "overlap": []},
 "flags": [{"check": "broken-seam", "severity": "critical", "concept": None,
            "detail": "ch-08 close and ch-09 open share no salient terms"}]}
# Deterministic flags = {broken-seam} only. orphan/forward-reference are SEMANTIC and the
# agent owns them (it gets each prior chapter's introduced-concepts digest to judge whether
# N leans on something never established). `references`/`introduces` are the inventory the
# agent uses; they are not themselves flags.

# agent findings returned by the dispatcher (validated shape)
{"spiral_coherence": "acceptable",
 "findings": [{"check": "missed-recall", "severity": "important", "prior_chapter": "ch-06",
               "detail": "...", "fix": "..."}],
 "per_prior_chapter": {"ch-08": "standing handed off cleanly"}}

# chapters/drafts/<id>/halmos-verdict.json
{"chapter_id": "ch-09", "halmos_critical_count": 0, "important_count": 2, "minor_count": 1,
 "spiral_coherence": "acceptable", "per_prior_chapter": {...}, "reviews_complete": true}
```

---

### Task 1: Scaffold the skill

**Files:**
- Create: `skills/halmos/pyproject.toml`, `skills/halmos/scripts/__init__.py`, `skills/halmos/tests/__init__.py`, `skills/halmos/references/seed-concepts.txt`

- [ ] **Step 1: Create `skills/halmos/pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "halmos"
version = "0.1.0"
description = "Sequential cross-chapter linkage review: concept recall, handoff seams, and spiral coherence."
requires-python = ">=3.11"
dependencies = []

[tool.pytest.ini_options]
markers = ["windows_canary: cross-platform deterministic tests"]
```

- [ ] **Step 2: Create empty `skills/halmos/scripts/__init__.py` and `skills/halmos/tests/__init__.py`** (zero bytes).

- [ ] **Step 3: Create `skills/halmos/references/seed-concepts.txt`** (the book's named devices; one per line, `Canonical | alias | alias`). Lines starting `#` are comments.

```
# Curated book devices. Format: Canonical Term | alias | alias
Authority Airgap | the airgap | authority airgap
Bounded Polis | the polis
Sovereign Horizon | the horizon
Logic Monopoly | logic monopoly
Agentic Civilization Scale | the scale | ACS
Settlement | settled transfer
Chorus
Agora
Brake Stack | the brake stack | brakes
Counterparty Risk
```

- [ ] **Step 4: Create the per-skill venv and install pytest**

Run: `cd skills/halmos && python -m venv .venv && .venv/Scripts/python.exe -m pip install -q pytest`
Expected: pytest installs; `.venv/Scripts/python.exe -m pytest --version` prints a version.

- [ ] **Step 5: Commit**

```bash
git add skills/halmos/pyproject.toml skills/halmos/scripts/__init__.py skills/halmos/tests/__init__.py skills/halmos/references/seed-concepts.txt
git commit -m "halmos: scaffold skill (pyproject, seed concepts)"
```

---

### Task 2: Concept ledger

**Files:**
- Create: `skills/halmos/scripts/concept_ledger.py`, `skills/halmos/tests/test_concept_ledger.py`

Responsibility: harvest concepts (seed devices + Title-Case multi-word phrases that recur) from the chapter drafts, write `halmos/concepts.jsonl` with the earliest-introducing chapter.

- [ ] **Step 1: Write the failing test** — `skills/halmos/tests/test_concept_ledger.py`

```python
import pytest
pytestmark = pytest.mark.windows_canary
import json
from pathlib import Path
from scripts.concept_ledger import build_concept_ledger, _norm, harvest_title_case


def _ws(tmp_path: Path, chapters: dict[str, str]) -> Path:
    ws = tmp_path / "ws"
    for cid, body in chapters.items():
        d = ws / "chapters" / "drafts" / cid
        d.mkdir(parents=True)
        (d / "draft.md").write_text(body, encoding="utf-8")
    (ws / "references").mkdir(parents=True, exist_ok=True)
    return ws


def test_harvest_title_case_finds_multiword_devices():
    got = harvest_title_case("The Authority Airgap separates power. The Bounded Polis follows.")
    assert "Authority Airgap" in got
    assert "Bounded Polis" in got


def test_seed_concept_introduced_in_earliest_chapter(tmp_path):
    ws = _ws(tmp_path, {
        "ch-01": "# C1\nIntelligence is not enough.\n",
        "ch-07": "# C7\nCall that separation the Authority Airgap.\n",
        "ch-09": "# C9\nThe airgap also gives a court.\n",
    })
    seed = ws / "references" / "seed-concepts.txt"
    seed.write_text("Authority Airgap | the airgap\n", encoding="utf-8")
    out = build_concept_ledger(ws, seed_path=seed)
    recs = [json.loads(l) for l in out.read_text(encoding="utf-8").splitlines() if l.strip()]
    air = next(r for r in recs if r["slug"] == "authority-airgap")
    assert air["introduced_in"] == "ch-07"   # earliest chapter the term/alias appears
    assert air["intro_n"] == 7
    assert "the airgap" in air["aliases"]


def test_norm_lowercases_and_collapses():
    assert _norm("  The  Airgap ") == "the airgap"
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd skills/halmos && .venv/Scripts/python.exe -m pytest tests/test_concept_ledger.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.concept_ledger'`.

- [ ] **Step 3: Implement `skills/halmos/scripts/concept_ledger.py`**

```python
"""Build halmos/concepts.jsonl: book concepts with the earliest chapter that introduces them."""
from __future__ import annotations
import json, re
from pathlib import Path

TITLE_CASE = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})\b")
# Title-Case phrases that are never book devices (proper nouns, source authors, headings).
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

    # candidate concept -> {aliases}
    candidates: dict[str, set[str]] = {}
    for canon, aliases in seed:
        candidates.setdefault(canon, set()).update(aliases)
    # auto-add Title-Case phrases seen in >=2 chapters (recurring => likely a device)
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
        for cid, body in bodies:           # bodies are in chapter order
            nbody = _norm(body)
            if any(f in nbody for f in norms):
                intro_cid = cid
                # gloss: first sentence in this chapter containing the canonical/alias
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd skills/halmos && .venv/Scripts/python.exe -m pytest tests/test_concept_ledger.py -q`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add skills/halmos/scripts/concept_ledger.py skills/halmos/tests/test_concept_ledger.py
git commit -m "halmos: concept ledger (seed + Title-Case harvest, earliest introduction)"
```

---

### Task 3: Linkage computation (references, seam, forward-reference flag)

**Files:**
- Create: `skills/halmos/scripts/build_linkage.py`, `skills/halmos/tests/test_build_linkage.py`

Responsibility: for chapter N, compute referenced/introduced concepts (the inventory the agent uses), the N−1→N seam status, and the one mechanically-decidable critical flag (`broken-seam`). Writes `halmos/linkage/ch-NN.json`. (orphan/forward-reference are semantic and owned by the agent in Task 4 — see the design note; the deterministic layer cannot decide them, because a concept referenced in N has `intro_n ≤ N` by construction.)

- [ ] **Step 1: Write the failing test** — `skills/halmos/tests/test_build_linkage.py`

```python
import pytest
pytestmark = pytest.mark.windows_canary
import json
from pathlib import Path
from scripts.concept_ledger import build_concept_ledger
from scripts.build_linkage import build_linkage, seam_status, STOPWORDS


def _ws(tmp_path, chapters):
    ws = tmp_path / "ws"
    for cid, body in chapters.items():
        d = ws / "chapters" / "drafts" / cid
        d.mkdir(parents=True)
        (d / "draft.md").write_text(body, encoding="utf-8")
    seed = ws / "references"; seed.mkdir(parents=True, exist_ok=True)
    (seed / "seed-concepts.txt").write_text(
        "Authority Airgap | the airgap\nSettlement\n", encoding="utf-8")
    return ws, seed / "seed-concepts.txt"


def test_seam_status_clean_when_overlap(tmp_path):
    status, overlap = seam_status(
        "the question turns to the Bounded Polis.",
        "The previous chapter left the Bounded Polis question open.")
    assert status == "clean"
    assert "bounded" in overlap or "polis" in overlap


def test_seam_status_broken_when_no_overlap():
    status, overlap = seam_status("a sentence about settlement and value.",
                                  "An unrelated opening about weather and traffic.")
    assert status == "broken"


def test_inventory_and_broken_seam(tmp_path):
    # ch-06 closes on settlement/value/final; ch-07 opens on airgap/separates/power -> no overlap.
    ws, seed = _ws(tmp_path, {
        "ch-06": "# C6\nSettlement makes value real and final.\n",
        "ch-07": "# C7\nCall it the Authority Airgap; it separates power.\n",
    })
    build_concept_ledger(ws, seed_path=seed)
    link = build_linkage(ws, "ch-07")
    # Authority Airgap is introduced in ch-07, so it shows in the inventory
    assert "authority-airgap" in link["references"] or "authority-airgap" in link["introduces"]
    assert link["seam"]["status"] == "broken"
    assert any(f["check"] == "broken-seam" and f["severity"] == "critical" for f in link["flags"])
    p = ws / "halmos" / "linkage" / "ch-07.json"
    assert json.loads(p.read_text(encoding="utf-8"))["chapter_id"] == "ch-07"
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd skills/halmos && .venv/Scripts/python.exe -m pytest tests/test_build_linkage.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.build_linkage'`.

- [ ] **Step 3: Implement `skills/halmos/scripts/build_linkage.py`**

```python
"""Deterministic cross-chapter linkage for one chapter: references, seam, forward-reference flags."""
from __future__ import annotations
import json, re
from pathlib import Path

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


def _chapter_n(cid: str) -> int:
    m = re.search(r"(\d+)", cid)
    return int(m.group(1)) if m else 0


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
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def _body_paras(text: str) -> list[str]:
    return [l.strip() for l in text.splitlines()
            if l.strip() and not l.strip().startswith(("#", "[^"))]


def build_linkage(workspace: Path, chapter_id: str) -> dict:
    workspace = Path(workspace)
    n = _chapter_n(chapter_id)
    body = (workspace / "chapters" / "drafts" / chapter_id / "draft.md").read_text(encoding="utf-8")
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd skills/halmos && .venv/Scripts/python.exe -m pytest tests/test_build_linkage.py -q`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add skills/halmos/scripts/build_linkage.py skills/halmos/tests/test_build_linkage.py
git commit -m "halmos: deterministic linkage (references, seam status, forward-reference flag)"
```

---

### Task 4: The Halmos doctrine reference (agent brief)

**Files:**
- Create: `skills/halmos/references/halmos-doctrine.md`

Responsibility: the reviewer persona/brief the dispatched agent applies. No test (content file); validated by presence in Task 8 SKILL test.

- [ ] **Step 1: Create `skills/halmos/references/halmos-doctrine.md`** with this content:

```markdown
# The Halmos doctrine (reviewer brief)

You review one chapter (N) of a sequentially-drafted book against the chapters already
written (1…N−1). You read in the spirit of Paul Halmos's *How to Write Mathematics* (1970):
exposition advances in a **spiral**, where each new part **recalls and refines** what came
before, so the reader is **always prepared**. Your job is to audit the connective tissue
between N and its predecessors — not the prose line by line (other reviewers do that), and
not logical contradiction (book-thesis does that). You audit **linkage, recall, and flow.**

You receive: chapter N's full text; a priors digest (each prior chapter's title, one-line
thesis, the concepts it introduced with glosses, and its closing paragraph); and a
deterministic linkage record (referenced/introduced concepts, the N−1→N seam, and any
mechanical flags already found). Confirm or extend those flags; you own the judgments below.

## Checks and severities

- **orphan-reference (critical):** N leans on a concept or term as if established, but no
  earlier chapter (nor N) introduced it. Confirm the deterministic forward-reference flags
  and add any the index missed.
- **broken-handoff (critical):** N−1's closing promise is not picked up by N's opening, or N
  opens on something N−1 never set up. Use the seam in the linkage record.
- **continuity-gap (critical if a clear skip, else important):** N's argument assumes a step
  the prior chapters never built — a rung skipped in the cumulative argument.
- **missed-recall (important):** N reuses an earlier concept without any recall cue, leaving
  the reader to reconstruct it.
- **spiral-stall (important):** N merely repeats a prior concept verbatim instead of refining
  or extending it; the spiral does not advance.
- **terminology-drift (important):** the same concept is named differently than in the
  chapter that introduced it.
- **premature-definition (minor):** a new concept is defined before it is motivated.

## Output

Return strict JSON:
{
  "spiral_coherence": "tight | acceptable | loose",
  "findings": [{"check": "<one of the above>", "severity": "critical|important|minor",
                "prior_chapter": "ch-NN or null", "detail": "...", "fix": "concrete fix for chapter N"}],
  "per_prior_chapter": {"ch-01": "one clause on how N links to it", ...}
}
Be strict and concrete. A limitation honestly marked as open is not a continuity-gap. The
final message is the JSON, not a human-facing note.
```

- [ ] **Step 2: Commit**

```bash
git add skills/halmos/references/halmos-doctrine.md
git commit -m "halmos: reviewer doctrine brief (spiral exposition, per-check rubric)"
```

---

### Task 5: Dispatch (payload assembly + caller-provided dispatcher)

**Files:**
- Create: `skills/halmos/scripts/dispatch_halmos_review.py`, add a test to `skills/halmos/tests/test_conductor_integration.py` (Task 7 reuses it).

Responsibility: assemble the agent payload (chapter N + priors digest + linkage) and dispatch one reviewer subagent via a caller-provided dispatcher. The dispatcher returns the agent findings dict (stub in tests).

- [ ] **Step 1: Implement `skills/halmos/scripts/dispatch_halmos_review.py`**

```python
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
```

- [ ] **Step 2: Write a payload test** — append to `skills/halmos/tests/test_conductor_integration.py`

```python
import pytest
pytestmark = pytest.mark.windows_canary
import json
from pathlib import Path
from scripts.concept_ledger import build_concept_ledger
from scripts.dispatch_halmos_review import build_payload


def _ws(tmp_path):
    ws = tmp_path / "ws"
    data = {
        "ch-01": "# C1\nIntelligence is not civilization.\n",
        "ch-02": "# C2\nThe previous chapter said intelligence is not civilization; institutions follow.\n",
    }
    for cid, body in data.items():
        d = ws / "chapters" / "drafts" / cid
        d.mkdir(parents=True)
        (d / "draft.md").write_text(body, encoding="utf-8")
    refs = ws / "references"; refs.mkdir(parents=True, exist_ok=True)
    (refs / "seed-concepts.txt").write_text("Institutions\n", encoding="utf-8")
    build_concept_ledger(ws, seed_path=refs / "seed-concepts.txt")
    return ws


def test_build_payload_includes_priors_digest(tmp_path):
    ws = _ws(tmp_path)
    p = build_payload(ws, "ch-02")
    assert p["chapter_id"] == "ch-02"
    assert [x["chapter_id"] for x in p["priors"]] == ["ch-01"]
    assert "draft" in p and "linkage" in p
```

- [ ] **Step 3: Run tests to verify they pass**

Run: `cd skills/halmos && .venv/Scripts/python.exe -m pytest tests/test_conductor_integration.py::test_build_payload_includes_priors_digest -q`
Expected: 1 passed.

- [ ] **Step 4: Commit**

```bash
git add skills/halmos/scripts/dispatch_halmos_review.py skills/halmos/tests/test_conductor_integration.py
git commit -m "halmos: payload assembly + caller-provided dispatcher"
```

---

### Task 6: Aggregate into verdict + report

**Files:**
- Create: `skills/halmos/scripts/aggregate_halmos.py`, `skills/halmos/tests/test_aggregate_halmos.py`

Responsibility: merge deterministic flags with agent findings (dedup by (check, concept/seam)); write `chapters/drafts/<id>/halmos-verdict.json` and `halmos-review.md`; compute `halmos_critical_count`.

- [ ] **Step 1: Write the failing test** — `skills/halmos/tests/test_aggregate_halmos.py`

```python
import pytest
pytestmark = pytest.mark.windows_canary
import json
from pathlib import Path
from scripts.aggregate_halmos import aggregate_halmos, rollup


def test_rollup_dedupes_and_counts():
    linkage = {"flags": [{"check": "forward-reference", "severity": "critical", "concept": "bounded-polis", "detail": "x"}]}
    agent = {"spiral_coherence": "loose", "findings": [
        {"check": "forward-reference", "severity": "critical", "prior_chapter": None, "concept": "bounded-polis", "detail": "dup"},
        {"check": "missed-recall", "severity": "important", "prior_chapter": "ch-06", "detail": "y", "fix": "recall it"},
    ], "per_prior_chapter": {}}
    merged = rollup(linkage, agent)
    assert merged["halmos_critical_count"] == 1     # the duplicate forward-reference collapses
    assert merged["important_count"] == 1
    assert merged["spiral_coherence"] == "loose"


def test_aggregate_writes_verdict_and_report(tmp_path):
    ws = tmp_path / "ws"
    (ws / "chapters" / "drafts" / "ch-09").mkdir(parents=True)
    (ws / "chapters" / "drafts" / "ch-09" / "draft.md").write_text("# C9\n", encoding="utf-8")
    linkage = {"chapter_id": "ch-09", "flags": [], "seam": {"status": "clean", "overlap": ["x"]}}
    agent = {"spiral_coherence": "tight", "findings": [], "per_prior_chapter": {"ch-08": "clean handoff"}}
    out = aggregate_halmos(ws, "ch-09", agent, linkage)
    v = json.loads((ws / "chapters" / "drafts" / "ch-09" / "halmos-verdict.json").read_text(encoding="utf-8"))
    assert v["halmos_critical_count"] == 0 and v["reviews_complete"] is True
    assert (ws / "chapters" / "drafts" / "ch-09" / "halmos-review.md").exists()
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd skills/halmos && .venv/Scripts/python.exe -m pytest tests/test_aggregate_halmos.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.aggregate_halmos'`.

- [ ] **Step 3: Implement `skills/halmos/scripts/aggregate_halmos.py`**

```python
"""Merge deterministic + agent findings into halmos-verdict.json and halmos-review.md."""
from __future__ import annotations
import json
from pathlib import Path


def _key(f: dict) -> tuple:
    return (f.get("check"), f.get("concept") or f.get("prior_chapter") or "")


def rollup(linkage: dict, agent_findings: dict) -> dict:
    merged: dict[tuple, dict] = {}
    for f in linkage.get("flags", []):
        merged[_key(f)] = {"check": f["check"], "severity": f["severity"],
                           "concept": f.get("concept"), "prior_chapter": None,
                           "detail": f.get("detail", ""), "fix": "", "source": "deterministic"}
    for f in agent_findings.get("findings", []):
        k = _key(f)
        if k in merged:                      # deterministic flag confirmed by the agent; keep det., attach fix
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd skills/halmos && .venv/Scripts/python.exe -m pytest tests/test_aggregate_halmos.py -q`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add skills/halmos/scripts/aggregate_halmos.py skills/halmos/tests/test_aggregate_halmos.py
git commit -m "halmos: aggregate deterministic + agent findings into verdict and report"
```

---

### Task 7: Conductor (chain) + stub-dispatcher integration test

**Files:**
- Create: `skills/halmos/scripts/conductor.py`; extend `skills/halmos/tests/test_conductor_integration.py`

Responsibility: `run_halmos` runs concept ledger → linkage → dispatch → aggregate, returning the verdict dict.

- [ ] **Step 1: Implement `skills/halmos/scripts/conductor.py`**

```python
"""Public entrypoint: run_halmos(workspace, chapter_id, dispatcher) -> verdict dict."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Callable, Optional

from scripts.concept_ledger import build_concept_ledger
from scripts.build_linkage import build_linkage
from scripts.dispatch_halmos_review import dispatch_halmos_review
from scripts.aggregate_halmos import aggregate_halmos


def run_halmos(workspace: Path, chapter_id: str,
               dispatcher: Optional[Callable[[dict], dict]] = None,
               seed_path: Optional[Path] = None) -> dict:
    workspace = Path(workspace)
    build_concept_ledger(workspace, seed_path=seed_path)
    linkage = build_linkage(workspace, chapter_id)
    agent_findings = dispatch_halmos_review(workspace, chapter_id, dispatcher=dispatcher)
    verdict_path = aggregate_halmos(workspace, chapter_id, agent_findings, linkage)
    return json.loads(verdict_path.read_text(encoding="utf-8"))
```

- [ ] **Step 2: Add the integration test** — append to `skills/halmos/tests/test_conductor_integration.py`

```python
def test_run_halmos_gates_on_broken_seam(tmp_path):
    ws = tmp_path / "ws2"
    data = {  # ch-06 close and ch-07 open share no salient term -> broken seam (critical)
        "ch-06": "# C6\nSettlement makes value real and final.\n",
        "ch-07": "# C7\nCall it the Authority Airgap; it separates power.\n",
    }
    for cid, body in data.items():
        d = ws / "chapters" / "drafts" / cid; d.mkdir(parents=True)
        (d / "draft.md").write_text(body, encoding="utf-8")
    refs = ws / "references"; refs.mkdir(parents=True, exist_ok=True)
    (refs / "seed-concepts.txt").write_text(
        "Authority Airgap | the airgap\nSettlement\n", encoding="utf-8")

    def stub(payload):  # the agent adds nothing new here
        return {"spiral_coherence": "acceptable", "findings": [], "per_prior_chapter": {}}

    verdict = run_halmos(ws, "ch-07", dispatcher=stub, seed_path=refs / "seed-concepts.txt")
    assert verdict["halmos_critical_count"] == 1     # the deterministic broken-seam flag
    assert verdict["reviews_complete"] is True
```

- [ ] **Step 3: Run the whole suite**

Run: `cd skills/halmos && .venv/Scripts/python.exe -m pytest tests/ -q`
Expected: all green — 10 passed (concept_ledger 3, build_linkage 3, aggregate 2, conductor_integration 2).

- [ ] **Step 4: Commit**

```bash
git add skills/halmos/scripts/conductor.py skills/halmos/tests/test_conductor_integration.py
git commit -m "halmos: conductor chains ledger->linkage->dispatch->aggregate; integration test"
```

---

### Task 8: Public API + SKILL.md + README

**Files:**
- Create: `skills/halmos/skill_api.py`, `skills/halmos/SKILL.md`, `skills/halmos/README.md`

- [ ] **Step 1: Implement `skills/halmos/skill_api.py`**

```python
"""halmos public surface."""
SKILL_API_VERSION = "0.1.0"
from scripts.concept_ledger import build_concept_ledger
from scripts.build_linkage import build_linkage, seam_status
from scripts.dispatch_halmos_review import build_payload, dispatch_halmos_review
from scripts.aggregate_halmos import aggregate_halmos, rollup
from scripts.conductor import run_halmos

__all__ = ["SKILL_API_VERSION", "build_concept_ledger", "build_linkage", "seam_status",
           "build_payload", "dispatch_halmos_review", "aggregate_halmos", "rollup", "run_halmos"]
```

- [ ] **Step 2: Create `skills/halmos/SKILL.md`** with frontmatter and usage:

```markdown
---
name: halmos
description: Sequential cross-chapter linkage review. Use when drafting chapter N to audit how it recalls, reuses, and builds on chapters 1..N-1 — concept linkage, handoff seams, and spiral coherence in Paul Halmos's sense. Emits halmos-review.md + halmos-verdict.json and soft-gates the chapter via halmos_critical_count == 0. Do NOT use for logical entailment (book-thesis) or persona review (review-conductor).
license: MIT
metadata:
  author: charles-hoskinson
  version: 0.1.0
  category: writing
  workspace-aware: true
---

# halmos

Named for Paul Halmos, whose *How to Write Mathematics* prescribes the spiral method:
each new part recalls and refines what came before, so the reader is always prepared.
`halmos` enforces that spiral across chapters.

## Public surface (`skill_api.py`)
- `run_halmos(workspace, chapter_id, dispatcher)` — the entrypoint; chains the four below.
- `build_concept_ledger(workspace)` — `halmos/concepts.jsonl`.
- `build_linkage(workspace, chapter_id)` — `halmos/linkage/ch-NN.json` (references, seam, forward-reference flags).
- `dispatch_halmos_review(workspace, chapter_id, dispatcher)` — Halmos-reviewer subagent.
- `aggregate_halmos(...)` — `chapters/drafts/<id>/{halmos-review.md, halmos-verdict.json}`.

The `dispatcher` is caller-provided: in production it issues a Task-tool call running
`references/halmos-doctrine.md`; in tests it returns a canned findings dict.

## Gate
Add `- halmos_critical_count == 0` to a chapter contract's `acceptance_tests`. `book-compose`'s
`chapter_contract_check` reads `chapters/drafts/<id>/halmos-verdict.json`.

## Boundaries
Reads chapters/drafts, contracts, claims, thesis. Writes halmos/ and the two per-chapter
files only. No network.
```

- [ ] **Step 3: Create `skills/halmos/README.md`** (short: one paragraph + the data shapes from this plan).

- [ ] **Step 4: Run the full suite once more**

Run: `cd skills/halmos && .venv/Scripts/python.exe -m pytest tests/ -q`
Expected: all green.

- [ ] **Step 5: Commit**

```bash
git add skills/halmos/skill_api.py skills/halmos/SKILL.md skills/halmos/README.md
git commit -m "halmos: public API, SKILL.md, README"
```

---

### Task 9: Contract gate in book-compose

**Files:**
- Modify: `skills/book-compose/scripts/chapter_contract_check.py`
- Create: `skills/book-compose/tests/test_halmos_gate.py`

Responsibility: add a `halmos_critical_count` metric to `_compute_metrics`, read from the chapter's `halmos-verdict.json` (mtime ≥ draft mtime), so contracts can gate on it.

- [ ] **Step 1: Write the failing test** — `skills/book-compose/tests/test_halmos_gate.py`

```python
import pytest
pytestmark = pytest.mark.windows_canary
import json, time
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.chapter_contract_check import _compute_metrics


def _draft(tmp_path, verdict: dict | None):
    d = tmp_path / "chapters" / "drafts" / "ch-09"
    d.mkdir(parents=True)
    dp = d / "draft.md"; dp.write_text("# C9\nbody\n", encoding="utf-8")
    if verdict is not None:
        time.sleep(0.01)
        (d / "halmos-verdict.json").write_text(json.dumps(verdict), encoding="utf-8")
    return dp


def test_halmos_metric_reads_verdict(tmp_path):
    dp = _draft(tmp_path, {"halmos_critical_count": 0, "reviews_complete": True})
    m = _compute_metrics(dp)
    assert m["halmos_critical_count"] == 0


def test_halmos_metric_absent_is_failing_sentinel(tmp_path):
    dp = _draft(tmp_path, None)
    m = _compute_metrics(dp)
    assert m["halmos_critical_count"] == 999   # absent/stale -> gate cannot pass
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd skills/book-compose && .venv/Scripts/python.exe -m pytest tests/test_halmos_gate.py -q`
Expected: FAIL (`KeyError: 'halmos_critical_count'`).

- [ ] **Step 3: Add the reader to `chapter_contract_check.py`.** Add this helper near the other `_read_*` helpers:

```python
def _read_halmos_critical(draft_path: Path) -> int:
    """halmos_critical_count from the chapter's halmos-verdict.json. Absent/stale -> 999
    (a sentinel that cannot satisfy `== 0`), mirroring the persona-not-run behavior."""
    verdict = draft_path.parent / "halmos-verdict.json"
    if not verdict.is_file() or verdict.stat().st_mtime < draft_path.stat().st_mtime:
        return 999
    try:
        data = json.loads(verdict.read_text(encoding="utf-8"))
        return int(data.get("halmos_critical_count", 999))
    except (ValueError, OSError):
        return 999
```

Then, inside `_compute_metrics(draft_path)`, add to the returned metrics dict:

```python
        "halmos_critical_count": _read_halmos_critical(draft_path),
```

(Confirm `json` is already imported at the top of the file; it is, per the existing
`_read_verdict_counts`. The metric is now available to `_evaluate_test`, which already
parses `<metric> == <int>` expressions generically.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd skills/book-compose && .venv/Scripts/python.exe -m pytest tests/test_halmos_gate.py -q`
Expected: 2 passed.

- [ ] **Step 5: Run the full book-compose suite to confirm no regression**

Run: `cd skills/book-compose && .venv/Scripts/python.exe -m pytest tests/ -q`
Expected: all green (the new metric is additive; existing acceptance tests that don't mention `halmos_critical_count` are unaffected).

- [ ] **Step 6: Commit**

```bash
git add skills/book-compose/scripts/chapter_contract_check.py skills/book-compose/tests/test_halmos_gate.py
git commit -m "book-compose: read halmos_critical_count as a gating contract metric"
```

---

## Self-review

**Spec coverage:** concept ledger reusing claim ledger + device extractor (Task 2 — devices implemented; claim-ledger reuse is available via the same `chapters/drafts` read and can be extended, the seed list covers the curated devices); deterministic linkage + the two critical flags (Task 3); doctrine brief (Task 4); dispatch + priors digest (Task 5); aggregate + verdict (Task 6); conductor (Task 7); public API + SKILL (Task 8); contract gate (Task 9). The `orphan-reference`, `terminology-drift`, `missed-recall`, `spiral-stall`, `continuity-gap`, `premature-definition` checks are owned by the agent (Task 4 doctrine) and surfaced through aggregate (Task 6); the deterministic layer owns `broken-seam` only. Forward/orphan-reference cannot be decided deterministically because a concept referenced in chapter N has `intro_n ≤ N` by construction, so the agent (which receives each prior chapter's introduced-concepts digest) owns that judgment. The `references`/`introduces` inventory feeds the agent.

**Placeholder scan:** every step has concrete code, exact paths, and exact commands. No TBDs.

**Type/signature consistency:** `build_concept_ledger(workspace, seed_path=None) -> Path`; `build_linkage(workspace, chapter_id) -> dict` (also writes file); `seam_status(prev, this, min_overlap=1) -> (str, list)`; `dispatch_halmos_review(workspace, chapter_id, dispatcher=None) -> dict`; `build_payload(workspace, chapter_id) -> dict`; `aggregate_halmos(workspace, chapter_id, agent_findings, linkage) -> Path`; `rollup(linkage, agent_findings) -> dict`; `run_halmos(workspace, chapter_id, dispatcher=None, seed_path=None) -> dict`. The verdict key `halmos_critical_count` is identical in aggregate (Task 6), the gate reader (Task 9), and the SKILL doc (Task 8). `_body_paras` and `_chapter_n` are defined once in `build_linkage` and imported by `dispatch_halmos_review`.

**Note for the implementer:** the spec mentions optionally reusing `book-knowledge.ledger` via the sibling loader to enrich concepts with verified claims. This plan reads `chapters/drafts` directly and uses the seed list for devices, which is self-contained and sufficient for v0.1; a follow-up can add claim-backed concepts by reading `claims/ledger.jsonl` in `concept_ledger.py` (latest status per `claim_id`, `verified`, mapping `supports_chapters` → concept provenance) without changing any signature.
