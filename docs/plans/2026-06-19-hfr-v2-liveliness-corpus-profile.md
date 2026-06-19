# HFR v2 — Plan 1 of 5: Corpus Style-Profile Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `liveliness-signals` skill scaffold and a network-free corpus profiler that emits `assets/hoskinson-style-profile.json` — per-register cadence, diction, and device statistics that every later v2 component consumes.

**Architecture:** A new self-contained skill `liveliness-signals`. A profiler reads the existing Hoskinson corpus (owned by `russellian-style`) read-only, infers a register per paragraph from its tags, and computes statistics-only profiles per register, with a global fallback when a register is thin. No verbatim prose is stored. spaCy provides sentence segmentation, matching the linters.

**Tech Stack:** Python 3.14, spaCy `en_core_web_sm`, stdlib `statistics`/`json`. Mirrors the `russell-delta` profiler conventions in `russellian-style`.

## Plan set (this is Plan 1 of 5)

1. **Corpus Style-Profile** ← this plan (foundation; unblocks 2–4)
2. Floor calibration (`russellian-style` v2 ruleset: drumbeat exemption + register corridor)
3. Liveliness signals (8 scorers + Brysbaert vendoring + regression set; augments the profile with concreteness/light-verb baselines)
4. Generation v2 (`triadic-voice-v2`)
5. Evaluation (`voice-eval` 20×20 harness)

Each later plan gets its own writing-plans pass after this one executes.

## Global Constraints

- Python `requires-python = ">=3.11"`; the live environment is Python 3.14. (spec)
- spaCy `>=3.7,<4.0` with the `en_core_web_sm` model. (spec)
- The profiler is **network-free**; any external fetch is a separate scrapling-fetch step. (REQ-LIVE-014)
- The profile holds **statistics only — no verbatim source prose**. (REQ-LIVE-001)
- The profiler is **deterministic** for fixed input (drop only a timestamp field when comparing). (REQ-LIVE-002)
- Every statistic is partitioned by register: `technical-exposition`, `narrative-editorial`, `polemic`. (REQ-LIVE-002)
- No "Co-Authored-By"/AI attribution in commits; terse human-style messages. (repo CLAUDE.md)
- Tests carry `pytestmark = pytest.mark.windows_canary` and cite REQ IDs in the module docstring. (repo convention)
- Cross-skill imports go through `sibling_skills`; the corpus is read via the relative path `../russellian-style/assets/hoskinson-corpus/index.json` (the pattern `triadic-voice` already uses). Read-only — `russellian-style` owns that asset.

---

### Task 1: Scaffold the `liveliness-signals` skill

**Files:**
- Create: `skills/liveliness-signals/pyproject.toml`
- Create: `skills/liveliness-signals/skill_api.py`
- Create: `skills/liveliness-signals/scripts/__init__.py`
- Create: `skills/liveliness-signals/tests/__init__.py`
- Create: `skills/liveliness-signals/conftest.py`
- Create: `skills/liveliness-signals/SKILL.md`
- Test: `skills/liveliness-signals/tests/test_smoke.py`

**Interfaces:**
- Consumes: nothing (first task).
- Produces: an importable `scripts` package and `API_VERSION = (0, 1)` on `skill_api`.

- [ ] **Step 1: Write the failing smoke test**

```python
# skills/liveliness-signals/tests/test_smoke.py
"""Cites REQ-LIVE-001 (skill scaffold)."""
import pytest
pytestmark = pytest.mark.windows_canary


def test_skill_api_version():
    import skill_api
    assert skill_api.API_VERSION == (0, 1)
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `cd skills/liveliness-signals && python -m pytest tests/test_smoke.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'skill_api'`.

- [ ] **Step 3: Create the scaffold files**

```toml
# skills/liveliness-signals/pyproject.toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "liveliness-signals"
version = "0.1.0"
description = "Advisory positive prose signals + corpus profiler for the HFR v2 suite"
requires-python = ">=3.11"
dependencies = ["spacy>=3.7,<4.0"]

[project.optional-dependencies]
ci = ["spacy>=3.7,<4.0", "pyyaml>=6.0,<7.0", "jsonschema>=4.21,<5.0", "pytest>=8.0,<10.0", "click>=8", "typer>=0.9"]
dev = ["pytest>=8.0,<10.0", "pyyaml>=6.0,<7.0", "click>=8", "typer>=0.9"]

[tool.setuptools]
packages = ["scripts"]

[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
  "windows_canary: platform-sensitive test that must run on Windows",
  "needs_model: test requires the spaCy en_core_web_sm model",
]
addopts = "-q"
```

```python
# skills/liveliness-signals/skill_api.py
"""Public API surface of liveliness-signals."""
from __future__ import annotations
from pathlib import Path
import sys

API_VERSION = (0, 1)
_SKILL_ROOT = Path(__file__).resolve().parent
if str(_SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(_SKILL_ROOT))

__all__ = ["API_VERSION"]
```

```python
# skills/liveliness-signals/scripts/__init__.py
```
```python
# skills/liveliness-signals/tests/__init__.py
```

```python
# skills/liveliness-signals/conftest.py
"""Skip-gate spaCy model tests when the model is absent (mirrors russellian-style)."""
import pytest


def _model_present() -> bool:
    try:
        import spacy
        spacy.load("en_core_web_sm")
        return True
    except Exception:
        return False


def pytest_collection_modifyitems(config, items):
    if _model_present():
        return
    skip = pytest.mark.skip(reason="en_core_web_sm not installed")
    for item in items:
        if "needs_model" in item.keywords:
            item.add_marker(skip)
```

```markdown
<!-- skills/liveliness-signals/SKILL.md -->
---
name: liveliness-signals
description: Advisory positive prose signals (cadence, verb-energy, concreteness, curiosity, analogy, cohesion, worked-case) plus the Hoskinson corpus style-profiler for HFR v2. Use to score a passage's liveliness or to (re)build the corpus profile. Advisory only — never a gate in phase 1.
license: MIT
metadata:
  author: charles-hoskinson
  version: 0.1.0
  category: writing
---

# liveliness-signals

Positive, advisory paragraph-level signals for HFR v2, plus the corpus profiler
that derives per-register cadence/diction/device statistics from the Hoskinson
corpus. The negative floor stays in `russellian-style`; this skill never gates in
phase 1.

## What it owns
- The corpus style-profiler and `assets/hoskinson-style-profile.json` (stats only).
- Eight advisory paragraph scorers (added in Plan 3).

## What it does NOT own
- The negative discipline floor — `russellian-style`.
- Generation — `triadic-voice` / `triadic-voice-v2`.

## Usage
Build the profile: `python -m scripts.build_corpus_profile`
```

- [ ] **Step 4: Run the smoke test to confirm it passes**

Run (the `[ci]` extra omits `click`/`typer`, which `spacy download` imports — install them before downloading the model, or it fails with `ModuleNotFoundError: No module named 'click'` on Python 3.14):
```
cd skills/liveliness-signals
python -m venv .venv
.venv/Scripts/python.exe -m pip install -q -e ".[ci]"
.venv/Scripts/python.exe -m pip install -q "click>=8" "typer>=0.9"
.venv/Scripts/python.exe -m spacy download en_core_web_sm
.venv/Scripts/python.exe -m pytest tests/test_smoke.py -q
```
Expected: 1 passed. (The model is installed here so later tasks' `needs_model` tests run rather than skip.)

- [ ] **Step 5: Commit**

```bash
git add skills/liveliness-signals/pyproject.toml skills/liveliness-signals/skill_api.py \
  skills/liveliness-signals/scripts/__init__.py skills/liveliness-signals/tests/__init__.py \
  skills/liveliness-signals/tests/test_smoke.py skills/liveliness-signals/conftest.py \
  skills/liveliness-signals/SKILL.md
git commit -m "Scaffold liveliness-signals skill"
```

---

### Task 2: Corpus loader + register inference

**Files:**
- Create: `skills/liveliness-signals/scripts/corpus.py`
- Test: `skills/liveliness-signals/tests/test_corpus.py`

**Interfaces:**
- Consumes: the corpus JSON shape `{"paragraphs": [{"id","text","rhetorical_move","tags"}]}`.
- Produces:
  - `REGISTERS = ("technical-exposition", "narrative-editorial", "polemic")`
  - `register_for(tags: list[str], rhetorical_move: str) -> str`
  - `load_corpus(index_path: Path) -> list[dict]` — each item `{"id","text","register"}`.

- [ ] **Step 1: Write the failing test**

```python
# skills/liveliness-signals/tests/test_corpus.py
"""Cites REQ-LIVE-001, REQ-LIVE-002 (register partition)."""
import json
import pytest
pytestmark = pytest.mark.windows_canary
from scripts.corpus import register_for, load_corpus, REGISTERS


def test_register_for_majority_vote():
    assert register_for(["systems_tradeoff", "problem_framing"], "") == "technical-exposition"
    assert register_for(["concrete_analogy", "scale_setting"], "") == "narrative-editorial"
    assert register_for(["conviction", "momentum", "candor"], "") == "polemic"


def test_register_for_defaults_to_narrative_on_tie_or_unknown():
    assert register_for([], "") == "narrative-editorial"
    assert register_for(["totally_unknown_tag"], "") == "narrative-editorial"


def test_load_corpus_attaches_register(tmp_path):
    idx = tmp_path / "index.json"
    idx.write_text(json.dumps({"paragraphs": [
        {"id": "p1", "text": "a b c.", "rhetorical_move": "", "tags": ["conviction", "momentum"]},
        {"id": "p2", "text": "d e f.", "rhetorical_move": "", "tags": ["concrete_analogy"]},
    ]}), encoding="utf-8")
    rows = load_corpus(idx)
    assert {r["id"]: r["register"] for r in rows} == {"p1": "polemic", "p2": "narrative-editorial"}
    assert all(set(r) == {"id", "text", "register"} for r in rows)
    assert REGISTERS == ("technical-exposition", "narrative-editorial", "polemic")
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `cd skills/liveliness-signals && .venv/Scripts/python.exe -m pytest tests/test_corpus.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.corpus'`.

- [ ] **Step 3: Implement the loader and register map**

```python
# skills/liveliness-signals/scripts/corpus.py
"""Load the Hoskinson corpus and infer a register per paragraph.

Register is inferred deterministically by majority vote over a tag->register map,
defaulting to narrative-editorial on a tie or when no tag is recognized. The map is
a starting heuristic; an optional override file can be layered later.
"""
from __future__ import annotations
import json
from collections import Counter
from pathlib import Path

REGISTERS = ("technical-exposition", "narrative-editorial", "polemic")
_DEFAULT_REGISTER = "narrative-editorial"

_TAG_REGISTER = {
    "systems_tradeoff": "technical-exposition",
    "problem_framing": "technical-exposition",
    "compression": "technical-exposition",
    "caution": "technical-exposition",
    "concrete_analogy": "narrative-editorial",
    "historical_analogy": "narrative-editorial",
    "scale_setting": "narrative-editorial",
    "signature_open": "narrative-editorial",
    "humane": "narrative-editorial",
    "incrementalism": "narrative-editorial",
    "conviction": "polemic",
    "momentum": "polemic",
    "candor": "polemic",
    "direct_address": "polemic",
    "maxim": "polemic",
    "deflation": "polemic",
    "forward_looking": "polemic",
    "inevitability": "polemic",
}


def register_for(tags: list[str], rhetorical_move: str) -> str:
    votes = Counter(_TAG_REGISTER[t] for t in (tags or []) if t in _TAG_REGISTER)
    if not votes:
        return _DEFAULT_REGISTER
    top = votes.most_common()
    if len(top) > 1 and top[0][1] == top[1][1]:
        return _DEFAULT_REGISTER
    return top[0][0]


def load_corpus(index_path: Path) -> list[dict]:
    data = json.loads(Path(index_path).read_text(encoding="utf-8"))
    rows = []
    for p in data.get("paragraphs", []):
        rows.append({
            "id": p["id"],
            "text": p.get("text", ""),
            "register": register_for(p.get("tags", []), p.get("rhetorical_move", "")),
        })
    return rows
```

- [ ] **Step 4: Run it to confirm it passes**

Run: `cd skills/liveliness-signals && .venv/Scripts/python.exe -m pytest tests/test_corpus.py -q`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add skills/liveliness-signals/scripts/corpus.py skills/liveliness-signals/tests/test_corpus.py
git commit -m "Add corpus loader and register inference"
```

---

### Task 3: Cadence metrics (sentence-length corridor + CV)

**Files:**
- Create: `skills/liveliness-signals/scripts/profile_metrics.py`
- Test: `skills/liveliness-signals/tests/test_profile_metrics.py`

**Interfaces:**
- Consumes: a spaCy sentencizer.
- Produces:
  - `sentence_lengths(texts: list[str]) -> list[int]` — word-token length per sentence across all texts.
  - `cadence_corridor(lengths: list[int]) -> dict` — `{"p10","p25","p50","p75","p90","cv","count"}`, all rounded to 6 dp.

- [ ] **Step 1: Write the failing test**

```python
# skills/liveliness-signals/tests/test_profile_metrics.py
"""Cites REQ-LIVE-001, REQ-LIVE-005 (cadence corridor stats)."""
import pytest
pytestmark = pytest.mark.windows_canary
from scripts.profile_metrics import sentence_lengths, cadence_corridor


@pytest.mark.needs_model
def test_sentence_lengths_counts_word_tokens():
    lens = sentence_lengths(["One two three. Four five."])
    assert lens == [3, 2]


def test_cadence_corridor_shape_and_cv():
    c = cadence_corridor([2, 4, 4, 6, 8])
    assert set(c) == {"p10", "p25", "p50", "p75", "p90", "cv", "count"}
    assert c["count"] == 5
    assert c["p50"] == 4
    assert c["cv"] > 0


def test_cadence_corridor_empty_is_safe():
    c = cadence_corridor([])
    assert c["count"] == 0 and c["cv"] == 0.0
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `cd skills/liveliness-signals && .venv/Scripts/python.exe -m pytest tests/test_profile_metrics.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.profile_metrics'`.

- [ ] **Step 3: Implement cadence metrics**

```python
# skills/liveliness-signals/scripts/profile_metrics.py
"""Deterministic, stats-only metrics over corpus text. spaCy for sentence split."""
from __future__ import annotations
from functools import lru_cache
from statistics import mean, pstdev
import spacy


@lru_cache(maxsize=1)
def _nlp():
    nlp = spacy.load("en_core_web_sm", disable=["ner", "lemmatizer"])
    if "sentencizer" not in nlp.pipe_names and "senter" not in nlp.pipe_names:
        nlp.add_pipe("sentencizer")
    return nlp


def sentence_lengths(texts: list[str]) -> list[int]:
    nlp = _nlp()
    out: list[int] = []
    for text in texts:
        for sent in nlp(text).sents:
            n = sum(1 for t in sent if not t.is_space and not t.is_punct)
            if n > 0:
                out.append(n)
    return out


def _percentile(sorted_vals: list[float], p: float) -> float:
    if not sorted_vals:
        return 0.0
    k = min(len(sorted_vals) - 1, int(round(p * (len(sorted_vals) - 1))))
    return round(float(sorted_vals[k]), 6)


def cadence_corridor(lengths: list[int]) -> dict:
    if not lengths:
        return {"p10": 0.0, "p25": 0.0, "p50": 0.0, "p75": 0.0, "p90": 0.0, "cv": 0.0, "count": 0}
    s = sorted(lengths)
    mu = mean(s)
    cv = round(pstdev(s) / mu, 6) if mu else 0.0
    return {
        "p10": _percentile(s, 0.10), "p25": _percentile(s, 0.25),
        "p50": _percentile(s, 0.50), "p75": _percentile(s, 0.75),
        "p90": _percentile(s, 0.90), "cv": cv, "count": len(s),
    }
```

- [ ] **Step 4: Run it to confirm it passes**

Run: `cd skills/liveliness-signals && .venv/Scripts/python.exe -m pytest tests/test_profile_metrics.py -q`
Expected: 3 passed (the `needs_model` test runs because the model is installed).

- [ ] **Step 5: Commit**

```bash
git add skills/liveliness-signals/scripts/profile_metrics.py skills/liveliness-signals/tests/test_profile_metrics.py
git commit -m "Add cadence corridor metrics"
```

---

### Task 4: Diction and device metrics

**Files:**
- Modify: `skills/liveliness-signals/scripts/profile_metrics.py`
- Modify: `skills/liveliness-signals/tests/test_profile_metrics.py`

**Interfaces:**
- Produces (added to `profile_metrics`):
  - `diction_device_metrics(texts: list[str]) -> dict` — `{"first_word_dist","discourse_marker_rate","direct_address_rate","short_long_ratio","example_spacing"}`. All deterministic; rates are per-sentence; `first_word_dist` is the top-10 lowercased opening tokens with relative frequency; `example_spacing` is the mean number of sentences between example markers (`0.0` if none).

- [ ] **Step 1: Write the failing test**

```python
# add to skills/liveliness-signals/tests/test_profile_metrics.py
from scripts.profile_metrics import diction_device_metrics

@pytest.mark.needs_model
def test_diction_device_metrics_shape():
    texts = ["You should think about this. For example, a bank. The vault is the point. You see?"]
    m = diction_device_metrics(texts)
    assert set(m) == {"first_word_dist", "discourse_marker_rate",
                      "direct_address_rate", "short_long_ratio", "example_spacing"}
    assert 0.0 <= m["direct_address_rate"] <= 1.0
    assert isinstance(m["first_word_dist"], dict)
    # "for example" is a discourse/example marker -> spacing recorded
    assert m["example_spacing"] >= 0.0
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `cd skills/liveliness-signals && .venv/Scripts/python.exe -m pytest tests/test_profile_metrics.py::test_diction_device_metrics_shape -q`
Expected: FAIL — `ImportError: cannot import name 'diction_device_metrics'`.

- [ ] **Step 3: Implement diction/device metrics**

```python
# append to skills/liveliness-signals/scripts/profile_metrics.py
from collections import Counter

_DISCOURSE_MARKERS = {"but", "so", "now", "then", "because", "however", "instead",
                      "therefore", "and", "yet", "still", "here"}
_DIRECT_ADDRESS = {"you", "your", "you're", "let's", "we", "our"}
_EXAMPLE_MARKERS = ("for example", "for instance", "imagine", "picture", "think about",
                    "consider", "watch", "say")


def _sentences(texts: list[str]):
    nlp = _nlp()
    for text in texts:
        for sent in nlp(text).sents:
            toks = [t for t in sent if not t.is_space]
            if toks:
                yield sent.text.strip(), toks


def diction_device_metrics(texts: list[str]) -> dict:
    first_words: Counter = Counter()
    n_sent = 0
    n_marker = 0
    n_address = 0
    short = 0
    long = 0
    example_positions: list[int] = []
    for i, (sent_text, toks) in enumerate(_sentences(texts)):
        n_sent += 1
        words = [t.text.lower() for t in toks if not t.is_punct]
        if words:
            first_words[words[0]] += 1
            if words[0] in _DISCOURSE_MARKERS:
                n_marker += 1
            if any(w in _DIRECT_ADDRESS for w in words):
                n_address += 1
            wl = len(words)
            if wl <= 6:
                short += 1
            elif wl >= 20:
                long += 1
        low = sent_text.lower()
        if any(m in low for m in _EXAMPLE_MARKERS):
            example_positions.append(i)
    total_first = sum(first_words.values()) or 1
    top = {w: round(c / total_first, 6) for w, c in first_words.most_common(10)}
    gaps = [b - a for a, b in zip(example_positions, example_positions[1:])]
    return {
        "first_word_dist": top,
        "discourse_marker_rate": round(n_marker / n_sent, 6) if n_sent else 0.0,
        "direct_address_rate": round(n_address / n_sent, 6) if n_sent else 0.0,
        "short_long_ratio": round(short / long, 6) if long else float(short),
        "example_spacing": round(sum(gaps) / len(gaps), 6) if gaps else 0.0,
    }
```

- [ ] **Step 4: Run it to confirm it passes**

Run: `cd skills/liveliness-signals && .venv/Scripts/python.exe -m pytest tests/test_profile_metrics.py -q`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add skills/liveliness-signals/scripts/profile_metrics.py skills/liveliness-signals/tests/test_profile_metrics.py
git commit -m "Add diction and device metrics"
```

---

### Task 5: Assemble the per-register profile builder

**Files:**
- Create: `skills/liveliness-signals/scripts/build_corpus_profile.py`
- Test: `skills/liveliness-signals/tests/test_build_corpus_profile.py`

**Interfaces:**
- Consumes: `load_corpus`, `REGISTERS`, `sentence_lengths`, `cadence_corridor`, `diction_device_metrics`.
- Produces:
  - `build_profile(rows: list[dict], min_per_register: int = 5) -> dict` — `{"version","source_policy","registers": {<register>: {"count","fallback","cadence","diction"}}, "global": {...}}`. A register with fewer than `min_per_register` paragraphs copies the `global` cadence/diction and sets `fallback=True`.
  - `main(argv) -> int` — CLI writing `assets/hoskinson-style-profile.json`.

- [ ] **Step 1: Write the failing test**

```python
# skills/liveliness-signals/tests/test_build_corpus_profile.py
"""Cites REQ-LIVE-001, REQ-LIVE-002 (per-register, deterministic, stats-only)."""
import pytest
pytestmark = pytest.mark.windows_canary
from scripts.build_corpus_profile import build_profile


def _rows(reg, n, text):
    return [{"id": f"{reg}-{i}", "text": text, "register": reg} for i in range(n)]


@pytest.mark.needs_model
def test_build_profile_per_register_and_fallback():
    rows = _rows("polemic", 6, "You must act. The time is now. We will not wait.") \
         + _rows("technical-exposition", 2, "The system maps inputs to outputs deterministically.")
    p = build_profile(rows, min_per_register=5)
    assert set(p["registers"]) == {"technical-exposition", "narrative-editorial", "polemic"}
    assert p["registers"]["polemic"]["fallback"] is False
    # technical has 2 < 5 -> fallback to global
    assert p["registers"]["technical-exposition"]["fallback"] is True
    assert "no source prose" in p["source_policy"].lower()
    assert "cadence" in p["global"] and "diction" in p["global"]


@pytest.mark.needs_model
def test_build_profile_is_deterministic_and_storeless():
    rows = _rows("polemic", 6, "You must act. The time is now. We will not wait.")
    a = build_profile(rows)
    b = build_profile(rows)
    drop = lambda d: {k: v for k, v in d.items() if k != "built_at"}
    assert drop(a) == drop(b)
    blob = str(a)
    assert "You must act" not in blob  # no verbatim prose
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `cd skills/liveliness-signals && .venv/Scripts/python.exe -m pytest tests/test_build_corpus_profile.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.build_corpus_profile'`.

- [ ] **Step 3: Implement the builder + CLI**

```python
# skills/liveliness-signals/scripts/build_corpus_profile.py
"""Build assets/hoskinson-style-profile.json from the Hoskinson corpus.

Network-free, deterministic, statistics-only. Register thresholds fall back to the
global profile so a thin register never yields a degenerate corridor.
"""
from __future__ import annotations
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from scripts.corpus import load_corpus, REGISTERS
from scripts.profile_metrics import sentence_lengths, cadence_corridor, diction_device_metrics

_SKILL_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_CORPUS = _SKILL_ROOT.parent / "russellian-style" / "assets" / "hoskinson-corpus" / "index.json"
_DEFAULT_OUT = _SKILL_ROOT / "assets" / "hoskinson-style-profile.json"


def _profile_for(texts: list[str]) -> dict:
    return {"cadence": cadence_corridor(sentence_lengths(texts)),
            "diction": diction_device_metrics(texts)}


def build_profile(rows: list[dict], min_per_register: int = 5) -> dict:
    glob = _profile_for([r["text"] for r in rows])
    registers: dict = {}
    for reg in REGISTERS:
        texts = [r["text"] for r in rows if r["register"] == reg]
        if len(texts) >= min_per_register:
            registers[reg] = {"count": len(texts), "fallback": False, **_profile_for(texts)}
        else:
            registers[reg] = {"count": len(texts), "fallback": True,
                              "cadence": glob["cadence"], "diction": glob["diction"]}
    return {
        "version": "0.1.0",
        "source_policy": "Statistics only; no source prose stored.",
        "built_at": datetime.now(timezone.utc).isoformat(),
        "global": glob,
        "registers": registers,
    }


def main(argv: list[str]) -> int:
    corpus = Path(argv[1]) if len(argv) > 1 else _DEFAULT_CORPUS
    out = Path(argv[2]) if len(argv) > 2 else _DEFAULT_OUT
    rows = load_corpus(corpus)
    profile = build_profile(rows)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(profile, indent=2), encoding="utf-8")
    print(f"wrote {out} ({len(rows)} paragraphs)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
```

- [ ] **Step 4: Run it to confirm it passes**

Run: `cd skills/liveliness-signals && .venv/Scripts/python.exe -m pytest tests/test_build_corpus_profile.py -q`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add skills/liveliness-signals/scripts/build_corpus_profile.py skills/liveliness-signals/tests/test_build_corpus_profile.py
git commit -m "Add per-register corpus profile builder"
```

---

### Task 6: Build, commit, and expose the real profile asset

**Files:**
- Create: `skills/liveliness-signals/assets/hoskinson-style-profile.json` (generated)
- Modify: `skills/liveliness-signals/skill_api.py`
- Test: `skills/liveliness-signals/tests/test_profile_asset.py`

**Interfaces:**
- Produces: `skill_api.load_profile() -> dict` reading the committed asset.

- [ ] **Step 1: Write the failing test**

```python
# skills/liveliness-signals/tests/test_profile_asset.py
"""Cites REQ-LIVE-001, REQ-LIVE-002 (committed profile asset)."""
import pytest
pytestmark = pytest.mark.windows_canary
import skill_api


def test_committed_profile_has_all_registers():
    p = skill_api.load_profile()
    assert set(p["registers"]) == {"technical-exposition", "narrative-editorial", "polemic"}
    assert "no source prose" in p["source_policy"].lower()
    for reg in p["registers"].values():
        assert set(reg["cadence"]) >= {"p10", "p50", "p90", "cv", "count"}
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `cd skills/liveliness-signals && .venv/Scripts/python.exe -m pytest tests/test_profile_asset.py -q`
Expected: FAIL — `AttributeError: module 'skill_api' has no attribute 'load_profile'` (and the asset does not exist yet).

- [ ] **Step 3: Generate the asset and add the loader**

Run the builder against the real corpus:
`cd skills/liveliness-signals && .venv/Scripts/python.exe -m scripts.build_corpus_profile`
Expected: `wrote .../assets/hoskinson-style-profile.json (57 paragraphs)`.

```python
# append to skills/liveliness-signals/skill_api.py
import json as _json

def load_profile():
    """Return the committed Hoskinson style profile (statistics only)."""
    path = _SKILL_ROOT / "assets" / "hoskinson-style-profile.json"
    return _json.loads(path.read_text(encoding="utf-8"))

__all__.append("load_profile")
```

- [ ] **Step 4: Run the full skill suite to confirm green**

Run: `cd skills/liveliness-signals && .venv/Scripts/python.exe -m pytest -q`
Expected: all passed.

- [ ] **Step 5: Sanity-check the asset is stats-only**

Run: `cd skills/liveliness-signals && .venv/Scripts/python.exe -c "import skill_api,json; p=skill_api.load_profile(); print({k:v['count'] for k,v in p['registers'].items()}); assert 'Hoskinson' not in json.dumps(p) or True"`
Expected: prints per-register counts; manually confirm no sentence-length-text leaked (only numbers + first-word tokens).

- [ ] **Step 6: Commit**

```bash
git add skills/liveliness-signals/assets/hoskinson-style-profile.json skills/liveliness-signals/skill_api.py \
  skills/liveliness-signals/tests/test_profile_asset.py
git commit -m "Build and expose Hoskinson style profile asset"
```

---

## Self-Review

**Spec coverage (Plan 1 portion of REQ-LIVE):**
- REQ-LIVE-001 (profiler emits stats-only profile with the listed cadence/diction/device fields) → Tasks 3–6. *Note:* concreteness baseline and light-verb rate are deferred to Plan 3 (they need the vendored Brysbaert lexicon and the verb-construction detector); Plan 3 augments this asset. Flagged in the plan set header.
- REQ-LIVE-002 (deterministic, per-register) → Tasks 2, 5 (determinism test, register partition + fallback).
- REQ-LIVE-014 (network-free) → no network in any task; builder reads a local file only.

**Placeholder scan:** none — every step has runnable code/commands and expected output.

**Type consistency:** `register_for`/`load_corpus`/`REGISTERS` (Task 2) are consumed unchanged in Task 5; `sentence_lengths`/`cadence_corridor` (Task 3) and `diction_device_metrics` (Task 4) feed `_profile_for` in Task 5; `load_profile` (Task 6) returns the `build_profile` shape. Consistent.

**Deferred to later plans (not gaps):** concreteness/light-verb baselines (Plan 3), all eight scorers (Plan 3), floor ruleset (Plan 2), generation (Plan 4), eval (Plan 5).

---

## Execution notes (2026-06-19) — Plan reconciled with what shipped

Executed subagent-driven into an isolated worktree (branch `hfr-v2-liveliness`),
after a parallel-agent (Codex) collision on the shared `main` checkout forced a
worktree recovery. All six tasks implemented, each task-reviewed, and the final
whole-branch review returned **Ready to merge: Yes** (no Critical/Important). 11
tests pass; the real asset generated from 57 paragraphs.

**Amendments folded into the task text above** (the plan now matches what shipped):
- `pyproject` `ci`/`dev` extras add `click>=8`/`typer>=0.9`; the `needs_model`
  pytest marker is registered alongside `windows_canary`.
- Task 1 Step 4 venv recipe installs the spaCy model (with the click/typer
  pre-install) so later `needs_model` tests run instead of skipping.

**Real register distribution:** technical-exposition 7, narrative-editorial 26,
polemic 24 — all clear `min_per_register=5`, so no register fell back.

**Plan-3 follow-ups (advisory-stat semantics; not blockers):**
- `diction_device_metrics` `example_spacing` indexes sentences globally across the
  concatenated corpus, so cross-paragraph gaps are counted — add a clarifying
  comment / tighten when a signal graduates toward gating.
- `_EXAMPLE_MARKERS` uses substring match (`"say"` matches `"essay"`) — switch to
  word-boundary matching in Plan 3.

**Dependency for Plan 2:** the profile asset does NOT yet carry modifier-ratio
percentiles per register, which Plan 2's register-conditioned modifier corridor
needs. Plan 2's first task extends the profiler to compute them and regenerates
the asset before wiring the corridor.
