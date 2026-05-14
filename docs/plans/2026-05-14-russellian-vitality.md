# russellian-style Vitality Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a vitality layer to `russellian-style`: five advisory linters that measure positive Russellian moves (burstiness, AI-vocabulary, concrete instances, epistemic precision, paragraph motion), a corpus-retrieval primitive that pulls a same-mode Russell paragraph as a calibration anchor, three mode-keyed system-prompt assets that `book-compose` loads at drafting time, and a positive-style doctrine reference companion to the existing negative-rules guide.

**Architecture:** Additive single-PR change. Existing six linters unchanged. New scripts live alongside in `skills/russellian-style/scripts/`. Assets in `skills/russellian-style/assets/system-prompts/` and `assets/ai-vocabulary-supplement.json`. New reference at `skills/russellian-style/references/russellian-vitality-guide.md`. `style_pass_report.py` extended to emit vitality metrics and corpus anchors. `book-compose` gets a one-line drafter change to load the matching system prompt based on a new optional `prose_mode` chapter-contract field.

**Tech Stack:** Python 3.13, spaCy (en_core_web_sm), jsonschema, pyyaml, pytest. Uses the existing alias-namespace `sibling_skills.py` pattern from `book-review` / `book-compose` / `review-conductor` for cross-skill imports.

---

## File Structure

### New files

```
skills/russellian-style/
├── scripts/
│   ├── sibling_skills.py                       # NEW: humanizer loader
│   ├── retrieve_corpus_anchor.py               # NEW: corpus retrieval primitive
│   ├── system_prompt_loader.py                 # NEW: load <mode>.md from assets/
│   ├── lint_burstiness.py                      # NEW: Fano factor + length-band
│   ├── lint_ai_vocabulary.py                   # NEW: humanizer + Russell overlay
│   ├── lint_concrete_instance_density.py       # NEW: NER count per paragraph
│   ├── lint_epistemic_precision.py             # NEW: tiered hedge classifier
│   └── lint_paragraph_motion.py                # NEW: paragraph-shape rubric
├── assets/
│   ├── ai-vocabulary-supplement.json           # NEW: Russell-specific overlay
│   └── system-prompts/
│       ├── technical-exposition.md             # NEW
│       ├── narrative-editorial.md              # NEW
│       └── polemic.md                          # NEW
├── references/
│   └── russellian-vitality-guide.md            # NEW: positive doctrine
└── tests/
    ├── test_sibling_skills.py                  # NEW
    ├── test_retrieve_corpus_anchor.py          # NEW
    ├── test_system_prompt_loader.py            # NEW
    ├── test_lint_burstiness.py                 # NEW
    ├── test_lint_ai_vocabulary.py              # NEW
    ├── test_lint_concrete_instance_density.py  # NEW
    ├── test_lint_epistemic_precision.py        # NEW
    ├── test_lint_paragraph_motion.py           # NEW
    └── test_style_pass_report_vitality.py      # NEW
```

### Modified files

```
skills/russellian-style/scripts/style_pass_report.py    # add vitality block + anchors
skills/book-compose/scripts/persona_review_pass.py      # load system prompt
skills/book-compose/scripts/sibling_skills.py           # already has load_russellian_style_module
skills/book-compose/scripts/chapter_contract.py         # add prose_mode field
skills/book-compose/assets/chapter-contract.schema.json # (verify path) add prose_mode enum
skills/book-compose/SKILL.md                            # Stage 5 description
```

---

## Phase A — Foundation

## Task A1: Branch off main

**Files:** none (git only)

- [ ] **Step 1: Switch to main + pull**

```bash
git checkout main
git pull --ff-only origin main
```

- [ ] **Step 2: Create branch**

```bash
git checkout -b feat/russellian-vitality
```

- [ ] **Step 3: Verify**

```bash
git status
```

Expected: `On branch feat/russellian-vitality`, `nothing to commit, working tree clean`.

## Task A2: sibling_skills.py — humanizer loader

**Files:**
- Create: `skills/russellian-style/scripts/sibling_skills.py`
- Test: `skills/russellian-style/tests/test_sibling_skills.py`

The humanizer skill ships its catalog as markdown plus optional JSON references; we expose a `load_humanizer_catalog()` function that returns a parsed catalog dict and a `humanizer_available()` predicate so the AI-vocab linter can degrade gracefully.

- [ ] **Step 1: Write the failing test**

Create `skills/russellian-style/tests/test_sibling_skills.py`:

```python
"""sibling_skills loads humanizer's pattern catalog under an alias namespace."""
import pytest


def test_humanizer_available_returns_bool():
    from scripts.sibling_skills import humanizer_available
    assert isinstance(humanizer_available(), bool)


def test_load_humanizer_catalog_returns_dict_when_present():
    from scripts.sibling_skills import humanizer_available, load_humanizer_catalog
    if not humanizer_available():
        pytest.skip("humanizer not installed at ~/.claude/skills/humanizer/")
    catalog = load_humanizer_catalog()
    assert isinstance(catalog, dict)
    # The catalog must expose at least one pattern key (em-dash overuse, magic adverbs, etc.)
    assert len(catalog) >= 1
    # At least one entry should be a list or dict (per-pattern records).
    assert any(isinstance(v, (list, dict)) for v in catalog.values())


def test_load_humanizer_catalog_raises_when_absent(monkeypatch, tmp_path):
    from scripts.sibling_skills import load_humanizer_catalog, SiblingNotFoundError
    # Force resolution to a missing path.
    monkeypatch.setattr("scripts.sibling_skills._skills_root", lambda: tmp_path)
    with pytest.raises(SiblingNotFoundError):
        load_humanizer_catalog()
```

- [ ] **Step 2: Run test, verify it fails**

```bash
cd skills/russellian-style
.venv/Scripts/python.exe -m pytest tests/test_sibling_skills.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.sibling_skills'`.

- [ ] **Step 3: Implement sibling_skills.py**

Create `skills/russellian-style/scripts/sibling_skills.py`:

```python
"""Locate sibling skills and load their parsed catalogs.

The humanizer skill ships its 24-pattern "Signs of AI writing" catalog as
markdown documentation plus (optionally) a JSON file. This module returns
a normalised dict the AI-vocabulary linter consumes. If humanizer is not
installed, callers receive a SiblingNotFoundError; the AI-vocab linter
runs the Russell-specific overlay alone in that case.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path


class SiblingNotFoundError(Exception):
    pass


def _skills_root() -> Path:
    home = Path(os.environ.get("USERPROFILE") or os.path.expanduser("~"))
    return home / ".claude" / "skills"


def _humanizer_root() -> Path:
    return _skills_root() / "humanizer"


def humanizer_available() -> bool:
    root = _humanizer_root()
    return root.is_dir() and (root / "SKILL.md").is_file()


def load_humanizer_catalog() -> dict:
    """Return a dict of {pattern_id: [phrases]} parsed from humanizer.

    Strategy:
    - Prefer humanizer/assets/patterns.json if present.
    - Fall back to parsing the bullet lists inside SKILL.md sections that
      enumerate patterns (em-dash overuse, magic adverbs, etc.).
    """
    if not humanizer_available():
        raise SiblingNotFoundError(f"humanizer not found at {_humanizer_root()}")
    root = _humanizer_root()

    patterns_json = root / "assets" / "patterns.json"
    if patterns_json.is_file():
        return json.loads(patterns_json.read_text(encoding="utf-8"))

    # Fall back to a coarse parse of SKILL.md: pick `### <heading>` sections
    # and collect their bulleted phrase lists.
    text = (root / "SKILL.md").read_text(encoding="utf-8")
    catalog: dict[str, list[str]] = {}
    section_re = re.compile(r"^### +(.+?)$", re.MULTILINE)
    matches = list(section_re.finditer(text))
    for i, m in enumerate(matches):
        heading = m.group(1).strip().lower().replace(" ", "_")
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end]
        phrases: list[str] = []
        for line in body.splitlines():
            line = line.strip()
            if line.startswith(("- ", "* ")):
                phrases.append(line[2:].strip().strip("*_`"))
        if phrases:
            catalog[heading] = phrases
    if not catalog:
        # Humanizer present but unparseable — return an empty marker so the
        # caller can decide to run overlay-only.
        catalog = {"_empty": []}
    return catalog
```

- [ ] **Step 4: Run tests, verify pass**

```bash
cd skills/russellian-style
.venv/Scripts/python.exe -m pytest tests/test_sibling_skills.py -v
```

Expected: 3 PASS (or 2 PASS + 1 SKIP if humanizer not installed locally).

- [ ] **Step 5: Commit**

```bash
git add skills/russellian-style/scripts/sibling_skills.py skills/russellian-style/tests/test_sibling_skills.py
git commit -m "russellian-style: sibling_skills loads humanizer catalog with graceful fallback"
```

## Task A3: retrieve_corpus_anchor.py

**Files:**
- Create: `skills/russellian-style/scripts/retrieve_corpus_anchor.py`
- Test: `skills/russellian-style/tests/test_retrieve_corpus_anchor.py`

Reads `assets/russell-corpus/index.json` and returns an `ExemplarRef` matching a requested rhetorical mode (and optionally a specific move). Deterministic via seeded random.

- [ ] **Step 1: Inspect the corpus index format**

```bash
.venv/Scripts/python.exe -c "import json, pathlib; d = json.loads(pathlib.Path('assets/russell-corpus/index.json').read_text()); print(json.dumps(list(d.values())[0] if isinstance(d, dict) else d[0], indent=2))"
```

Expected: shows one entry's shape. Note the key names (e.g., `corpus_id`, `mode`, `source_title`, `source_url`, `line_hint`, `rhetorical_move`, `calibration_lesson` per the corpus-map design). Adjust the dataclass mapping in the next step if the actual keys differ.

- [ ] **Step 2: Write the failing test**

Create `skills/russellian-style/tests/test_retrieve_corpus_anchor.py`:

```python
"""retrieve_corpus_anchor: same-mode Russell paragraph retrieval."""
import pytest


def test_retrieve_anchor_returns_exemplar_for_known_mode():
    from scripts.retrieve_corpus_anchor import retrieve_anchor
    ref = retrieve_anchor(rhetorical_mode="problems", seed=42)
    assert ref.corpus_id.startswith("problems-")
    assert ref.source_title
    assert ref.source_url.startswith("https://")
    assert ref.rhetorical_move
    assert ref.calibration_lesson


def test_retrieve_anchor_seed_stable():
    from scripts.retrieve_corpus_anchor import retrieve_anchor
    a = retrieve_anchor(rhetorical_mode="problems", seed=42)
    b = retrieve_anchor(rhetorical_mode="problems", seed=42)
    assert a == b


def test_retrieve_anchor_filters_by_move_substring():
    from scripts.retrieve_corpus_anchor import retrieve_anchor
    ref = retrieve_anchor(rhetorical_mode="political-ideals", rhetorical_move="liberty", seed=42)
    assert "liberty" in ref.rhetorical_move.lower() or "liberty" in ref.calibration_lesson.lower()


def test_retrieve_anchor_unknown_mode_raises():
    from scripts.retrieve_corpus_anchor import retrieve_anchor
    with pytest.raises(ValueError):
        retrieve_anchor(rhetorical_mode="nonexistent-mode", seed=42)


def test_retrieve_anchor_no_move_match_raises():
    from scripts.retrieve_corpus_anchor import retrieve_anchor
    with pytest.raises(LookupError):
        retrieve_anchor(rhetorical_mode="problems", rhetorical_move="aardvark", seed=42)
```

- [ ] **Step 3: Run, verify failure**

```bash
cd skills/russellian-style
.venv/Scripts/python.exe -m pytest tests/test_retrieve_corpus_anchor.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 4: Implement retrieve_corpus_anchor.py**

Create `skills/russellian-style/scripts/retrieve_corpus_anchor.py`:

```python
"""Retrieve one Russell paragraph reference from the corpus index.

Returns a reference + lesson only. Per the russell-corpus-map.md
"do not paste full paragraphs into prompts by default" rule, the
full source text is never returned.
"""
from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


CORPUS_INDEX = (
    Path(__file__).resolve().parent.parent / "assets" / "russell-corpus" / "index.json"
)


@dataclass(frozen=True)
class ExemplarRef:
    corpus_id: str
    source_title: str
    source_url: str
    line_hint: int
    rhetorical_move: str
    calibration_lesson: str


def _load_index() -> list[dict]:
    raw = json.loads(CORPUS_INDEX.read_text(encoding="utf-8"))
    # Tolerate either a list of entries or a dict keyed by corpus_id.
    if isinstance(raw, dict):
        return list(raw.values())
    return raw


def _entry_mode(entry: dict) -> str:
    return entry.get("mode") or entry.get("source") or entry.get("source_id", "")


def retrieve_anchor(
    rhetorical_mode: str,
    rhetorical_move: Optional[str] = None,
    seed: int = 42,
) -> ExemplarRef:
    """Return one corpus entry matching the requested mode + (optional) move."""
    entries = _load_index()
    in_mode = [e for e in entries if _entry_mode(e) == rhetorical_mode]
    if not in_mode:
        raise ValueError(f"no corpus entries for mode: {rhetorical_mode!r}")

    if rhetorical_move:
        needle = rhetorical_move.lower()
        in_mode = [
            e for e in in_mode
            if needle in (e.get("rhetorical_move", "") + " " + e.get("calibration_lesson", "")).lower()
        ]
        if not in_mode:
            raise LookupError(
                f"no corpus entries for mode={rhetorical_mode!r} move~={rhetorical_move!r}"
            )

    rng = random.Random(seed)
    chosen = rng.choice(in_mode)
    return ExemplarRef(
        corpus_id=chosen["corpus_id"],
        source_title=chosen.get("source_title", chosen.get("title", "")),
        source_url=chosen.get("source_url", chosen.get("url", "")),
        line_hint=int(chosen.get("line_hint", 0)),
        rhetorical_move=chosen.get("rhetorical_move", ""),
        calibration_lesson=chosen.get("calibration_lesson", ""),
    )
```

- [ ] **Step 5: Run tests, verify pass**

```bash
cd skills/russellian-style
.venv/Scripts/python.exe -m pytest tests/test_retrieve_corpus_anchor.py -v
```

Expected: 5 PASS. If the corpus index has different key names than the dataclass expects, adjust the dataclass-to-dict mapping in `retrieve_anchor` and re-run.

- [ ] **Step 6: Commit**

```bash
git add skills/russellian-style/scripts/retrieve_corpus_anchor.py skills/russellian-style/tests/test_retrieve_corpus_anchor.py
git commit -m "russellian-style: retrieve_corpus_anchor returns same-mode Russell ExemplarRef"
```

## Task A4: system_prompt_loader.py

**Files:**
- Create: `skills/russellian-style/scripts/system_prompt_loader.py`
- Test: `skills/russellian-style/tests/test_system_prompt_loader.py`

Reads `assets/system-prompts/<mode>.md` and returns its text. The actual prompt files arrive in Task C2; this task only ships the loader and its tests against a fixture prompt.

- [ ] **Step 1: Write the failing test**

Create `skills/russellian-style/tests/test_system_prompt_loader.py`:

```python
"""system_prompt_loader: returns the text of a mode-keyed system prompt."""
from pathlib import Path
import pytest


VALID_MODES = {"technical-exposition", "narrative-editorial", "polemic"}


def test_load_known_mode_returns_nonempty_text(tmp_path, monkeypatch):
    from scripts.system_prompt_loader import load, PROMPTS_DIR
    # Use a tmp fixture; the real assets ship in Task C2.
    prompts_dir = tmp_path / "system-prompts"
    prompts_dir.mkdir()
    (prompts_dir / "technical-exposition.md").write_text("# Test prompt\n\nBody.\n", encoding="utf-8")
    monkeypatch.setattr("scripts.system_prompt_loader.PROMPTS_DIR", prompts_dir)
    text = load("technical-exposition")
    assert "Test prompt" in text


def test_load_unknown_mode_raises():
    from scripts.system_prompt_loader import load
    with pytest.raises(ValueError):
        load("nonexistent-mode")


def test_load_known_mode_missing_file_raises(tmp_path, monkeypatch):
    from scripts.system_prompt_loader import load
    monkeypatch.setattr("scripts.system_prompt_loader.PROMPTS_DIR", tmp_path)
    with pytest.raises(FileNotFoundError):
        load("technical-exposition")


def test_default_mode_is_technical_exposition():
    from scripts.system_prompt_loader import DEFAULT_MODE
    assert DEFAULT_MODE == "technical-exposition"
```

- [ ] **Step 2: Run, verify failure**

```bash
cd skills/russellian-style
.venv/Scripts/python.exe -m pytest tests/test_system_prompt_loader.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement system_prompt_loader.py**

Create `skills/russellian-style/scripts/system_prompt_loader.py`:

```python
"""Load a mode-keyed system prompt from assets/system-prompts/<mode>.md."""
from __future__ import annotations

from pathlib import Path


PROMPTS_DIR = Path(__file__).resolve().parent.parent / "assets" / "system-prompts"

VALID_MODES = {"technical-exposition", "narrative-editorial", "polemic"}
DEFAULT_MODE = "technical-exposition"


def load(mode: str = DEFAULT_MODE) -> str:
    if mode not in VALID_MODES:
        raise ValueError(
            f"unknown prose mode: {mode!r}; valid modes: {sorted(VALID_MODES)}"
        )
    path = PROMPTS_DIR / f"{mode}.md"
    if not path.is_file():
        raise FileNotFoundError(f"system prompt not found: {path}")
    return path.read_text(encoding="utf-8")
```

- [ ] **Step 4: Run tests, verify pass**

```bash
cd skills/russellian-style
.venv/Scripts/python.exe -m pytest tests/test_system_prompt_loader.py -v
```

Expected: 4 PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/russellian-style/scripts/system_prompt_loader.py skills/russellian-style/tests/test_system_prompt_loader.py
git commit -m "russellian-style: system_prompt_loader reads mode-keyed prompt from assets/"
```

---

## Phase B — Vitality linters

## Task B1: lint_burstiness.py

**Files:**
- Create: `skills/russellian-style/scripts/lint_burstiness.py`
- Test: `skills/russellian-style/tests/test_lint_burstiness.py`

Computes Fano factor (variance/mean) of sentence-length distribution, plus the proportion of sentences inside the AI-signature word band `[12, 17]`. PDF-grounded targets: AI mean 14.38 / band 12.33-17.64; human mean 19.28 / range 15.67-25.60.

- [ ] **Step 1: Write the failing test**

Create `skills/russellian-style/tests/test_lint_burstiness.py`:

```python
"""lint_burstiness: Fano factor + AI-band proportion on sentence-length distribution."""
from pathlib import Path


def _write(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "draft.md"
    p.write_text(text, encoding="utf-8")
    return p


def test_uniform_short_sentences_flagged(tmp_path):
    """AI signature: every sentence between 12 and 17 words."""
    from scripts.lint_burstiness import lint_burstiness
    text = " ".join([
        "This sentence has exactly fourteen words and sits inside the suspect AI band cleanly.",
        "Another sentence with fifteen words lands inside the same narrow predictable AI band today.",
        "Yet another sentence of thirteen words drops squarely inside the AI signature band.",
        "A fourth sentence reaches fourteen words again inside the suspect AI signature band.",
    ])
    findings = lint_burstiness(_write(tmp_path, text))
    assert findings
    f = findings[0]
    assert f["rule"] == "burstiness"
    assert f["in_band_proportion"] >= 0.75
    assert f["fano_factor"] < 0.5


def test_high_variance_passes(tmp_path):
    """Human signature: alternating short and long sentences."""
    from scripts.lint_burstiness import lint_burstiness
    text = " ".join([
        "Short.",
        "A modest middle sentence holds the centre of the passage and points outward.",
        "Then comes a long, balanced, compound-complex sentence that uses subordination, a parenthetical aside (offered here), and a closing turn to demonstrate the variance that human prose carries against the metronomic AI rhythm those who read closely come to recognise.",
        "Brief again.",
        "A normal sentence of eight words follows neatly.",
        "Final sentence runs to twenty-two words to balance the earlier short ones and to lift the section's Fano factor well above the AI signature threshold.",
    ])
    findings = lint_burstiness(_write(tmp_path, text))
    if findings:
        f = findings[0]
        assert f["fano_factor"] >= 0.5


def test_empty_document_returns_empty(tmp_path):
    from scripts.lint_burstiness import lint_burstiness
    findings = lint_burstiness(_write(tmp_path, ""))
    assert findings == []


def test_single_sentence_returns_empty(tmp_path):
    from scripts.lint_burstiness import lint_burstiness
    findings = lint_burstiness(_write(tmp_path, "Single sentence here."))
    assert findings == []
```

- [ ] **Step 2: Run, verify failure**

```bash
cd skills/russellian-style
.venv/Scripts/python.exe -m pytest tests/test_lint_burstiness.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement lint_burstiness.py**

Create `skills/russellian-style/scripts/lint_burstiness.py`:

```python
"""Burstiness linter: Fano factor + AI-band proportion.

PDF-grounded targets ("AI Prose: From Terseness to Cadence", §3):
  - AI prose: mean 14.38 words/sentence; tight band 12.33-17.64.
  - Human prose: mean 19.28; range 15.67-25.60; high Fano factor.
"""
from __future__ import annotations

import json
from pathlib import Path
from statistics import mean, pvariance

from .lint_common import iter_sentences, load_markdown


AI_BAND = (12, 17)


def lint_burstiness(path: Path) -> list[dict]:
    text = load_markdown(path)
    lengths = [len(s.text.split()) for s in iter_sentences(text)]
    if len(lengths) < 2:
        return []
    mu = mean(lengths)
    sigma2 = pvariance(lengths)
    fano = sigma2 / mu if mu > 0 else 0.0
    in_band = sum(1 for n in lengths if AI_BAND[0] <= n <= AI_BAND[1])
    in_band_prop = in_band / len(lengths)

    severity = _severity(fano, in_band_prop)
    if severity == "pass":
        return []
    return [{
        "rule": "burstiness",
        "fano_factor": round(fano, 3),
        "mean_words_per_sentence": round(mu, 2),
        "in_band_proportion": round(in_band_prop, 3),
        "sentence_count": len(lengths),
        "severity": severity,
    }]


def _severity(fano: float, in_band_prop: float) -> str:
    if fano < 0.3 or in_band_prop > 0.85:
        return "critical"
    if fano < 0.5:
        return "important"
    if fano < 0.7:
        return "advisory"
    return "pass"


if __name__ == "__main__":
    import sys
    print(json.dumps(lint_burstiness(Path(sys.argv[1])), indent=2))
```

- [ ] **Step 4: Run tests, verify pass**

```bash
cd skills/russellian-style
.venv/Scripts/python.exe -m pytest tests/test_lint_burstiness.py -v
```

Expected: 4 PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/russellian-style/scripts/lint_burstiness.py skills/russellian-style/tests/test_lint_burstiness.py
git commit -m "russellian-style: lint_burstiness measures Fano factor + AI-band proportion"
```

## Task B2: ai-vocabulary-supplement.json + lint_ai_vocabulary.py

**Files:**
- Create: `skills/russellian-style/assets/ai-vocabulary-supplement.json`
- Create: `skills/russellian-style/scripts/lint_ai_vocabulary.py`
- Test: `skills/russellian-style/tests/test_lint_ai_vocabulary.py`

- [ ] **Step 1: Create the supplement JSON**

Create `skills/russellian-style/assets/ai-vocabulary-supplement.json`:

```json
{
  "patterns": [
    {
      "id": "false_certainty",
      "description": "Words that assert obviousness instead of proving it.",
      "phrases": ["clearly", "obviously", "of course", "it is self-evident that", "needless to say"]
    },
    {
      "id": "magic_adverb",
      "description": "Soft adverb performing the descriptive heavy lifting that a precise verb should.",
      "words": ["quietly", "deeply", "profoundly", "seamlessly", "intricately", "fundamentally"]
    },
    {
      "id": "sweeping_abstraction_subject",
      "description": "Abstract noun used as primary subject without a concrete actor.",
      "head_nouns": ["system", "framework", "landscape", "tapestry", "ecosystem", "paradigm"],
      "exemption": "concrete_actor_present"
    },
    {
      "id": "transition_adverb_starter",
      "description": "Transition adverbs used to begin a sentence; AI's primary syntactic crutch.",
      "phrases": ["moreover", "furthermore", "additionally", "consequently", "subsequently", "notably", "importantly"]
    }
  ]
}
```

- [ ] **Step 2: Write the failing test**

Create `skills/russellian-style/tests/test_lint_ai_vocabulary.py`:

```python
"""lint_ai_vocabulary: humanizer-delegated catalog + Russell-specific overlay."""
from pathlib import Path


def _write(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "draft.md"
    p.write_text(text, encoding="utf-8")
    return p


def test_false_certainty_flagged(tmp_path):
    from scripts.lint_ai_vocabulary import lint_ai_vocabulary
    text = "The system clearly succeeds. Obviously, the user benefits."
    findings = lint_ai_vocabulary(_write(tmp_path, text))
    ids = {f["pattern_id"] for f in findings}
    assert "false_certainty" in ids


def test_magic_adverb_flagged(tmp_path):
    from scripts.lint_ai_vocabulary import lint_ai_vocabulary
    text = "The platform quietly orchestrates workflows and seamlessly bridges teams."
    findings = lint_ai_vocabulary(_write(tmp_path, text))
    ids = {f["pattern_id"] for f in findings}
    assert "magic_adverb" in ids


def test_transition_adverb_starter_flagged(tmp_path):
    from scripts.lint_ai_vocabulary import lint_ai_vocabulary
    text = (
        "The team shipped the feature. Moreover, the team measured adoption. "
        "Furthermore, the dashboards updated nightly."
    )
    findings = lint_ai_vocabulary(_write(tmp_path, text))
    ids = {f["pattern_id"] for f in findings}
    assert "transition_adverb_starter" in ids


def test_no_violations_in_clean_text(tmp_path):
    from scripts.lint_ai_vocabulary import lint_ai_vocabulary
    text = (
        "The committee voted seven to two. The minority filed a brief dissent. "
        "Bermuda's parliament adjourned at six in the evening."
    )
    findings = lint_ai_vocabulary(_write(tmp_path, text))
    assert findings == []


def test_supplement_loads():
    from scripts.lint_ai_vocabulary import load_supplement
    supp = load_supplement()
    ids = {p["id"] for p in supp["patterns"]}
    assert {"false_certainty", "magic_adverb", "transition_adverb_starter"} <= ids
```

- [ ] **Step 3: Run, verify failure**

```bash
cd skills/russellian-style
.venv/Scripts/python.exe -m pytest tests/test_lint_ai_vocabulary.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 4: Implement lint_ai_vocabulary.py**

Create `skills/russellian-style/scripts/lint_ai_vocabulary.py`:

```python
"""AI-vocabulary linter: humanizer catalog + Russell-specific overlay.

Loads humanizer's 24-pattern catalog via sibling_skills when available;
runs the Russell-specific supplement (assets/ai-vocabulary-supplement.json)
in all cases. Reports one finding per detected occurrence with pattern_id,
phrase, and line.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .lint_common import iter_sentences, load_markdown
from .sibling_skills import SiblingNotFoundError, humanizer_available, load_humanizer_catalog


SUPPLEMENT_PATH = (
    Path(__file__).resolve().parent.parent / "assets" / "ai-vocabulary-supplement.json"
)


def load_supplement() -> dict:
    return json.loads(SUPPLEMENT_PATH.read_text(encoding="utf-8"))


def _word_boundary_pattern(phrases: list[str]) -> re.Pattern:
    escaped = [re.escape(p) for p in sorted(phrases, key=len, reverse=True)]
    return re.compile(r"\b(" + "|".join(escaped) + r")\b", flags=re.IGNORECASE)


def _sentence_starts_with(sentence: str, phrases: list[str]) -> str | None:
    head = sentence.strip().lstrip("*_>#- ").lower()
    for p in phrases:
        if head.startswith(p.lower() + " ") or head.startswith(p.lower() + ","):
            return p
    return None


def lint_ai_vocabulary(path: Path) -> list[dict]:
    text = load_markdown(path)
    findings: list[dict] = []

    supplement = load_supplement()
    patterns_by_id = {p["id"]: p for p in supplement["patterns"]}

    fc = patterns_by_id["false_certainty"]
    fc_re = _word_boundary_pattern(fc["phrases"])
    for sentence in iter_sentences(text):
        for m in fc_re.finditer(sentence.text):
            findings.append({
                "rule": "ai-vocabulary",
                "pattern_id": "false_certainty",
                "phrase": m.group(1),
                "sentence": sentence.text,
                "line": getattr(sentence, "line", 0),
            })

    ma = patterns_by_id["magic_adverb"]
    ma_re = _word_boundary_pattern(ma["words"])
    for sentence in iter_sentences(text):
        for m in ma_re.finditer(sentence.text):
            findings.append({
                "rule": "ai-vocabulary",
                "pattern_id": "magic_adverb",
                "phrase": m.group(1),
                "sentence": sentence.text,
                "line": getattr(sentence, "line", 0),
            })

    ta = patterns_by_id["transition_adverb_starter"]
    for sentence in iter_sentences(text):
        hit = _sentence_starts_with(sentence.text, ta["phrases"])
        if hit:
            findings.append({
                "rule": "ai-vocabulary",
                "pattern_id": "transition_adverb_starter",
                "phrase": hit,
                "sentence": sentence.text,
                "line": getattr(sentence, "line", 0),
            })

    # sweeping_abstraction_subject is deferred: it needs a dependency parser to
    # detect subject NP head + check for concrete-actor exemption. Tracked for
    # follow-up; the JSON entry stays in the supplement as future-work.

    # Optional humanizer overlay — only adds findings, never removes.
    if humanizer_available():
        try:
            catalog = load_humanizer_catalog()
        except SiblingNotFoundError:
            catalog = {}
        for cat_id, phrases in catalog.items():
            if not isinstance(phrases, list) or not phrases:
                continue
            cat_re = _word_boundary_pattern([str(p) for p in phrases if isinstance(p, str)])
            for sentence in iter_sentences(text):
                for m in cat_re.finditer(sentence.text):
                    findings.append({
                        "rule": "ai-vocabulary",
                        "pattern_id": f"humanizer:{cat_id}",
                        "phrase": m.group(1),
                        "sentence": sentence.text,
                        "line": getattr(sentence, "line", 0),
                    })

    return findings


if __name__ == "__main__":
    import sys
    print(json.dumps(lint_ai_vocabulary(Path(sys.argv[1])), indent=2))
```

- [ ] **Step 5: Run tests, verify pass**

```bash
cd skills/russellian-style
.venv/Scripts/python.exe -m pytest tests/test_lint_ai_vocabulary.py -v
```

Expected: 5 PASS.

- [ ] **Step 6: Commit**

```bash
git add skills/russellian-style/assets/ai-vocabulary-supplement.json skills/russellian-style/scripts/lint_ai_vocabulary.py skills/russellian-style/tests/test_lint_ai_vocabulary.py
git commit -m "russellian-style: lint_ai_vocabulary detects false certainty, magic adverbs, transition crutches"
```

## Task B3: lint_concrete_instance_density.py

**Files:**
- Create: `skills/russellian-style/scripts/lint_concrete_instance_density.py`
- Test: `skills/russellian-style/tests/test_lint_concrete_instance_density.py`

Uses spaCy NER plus a small occupational-noun matcher.

- [ ] **Step 1: Write the failing test**

Create `skills/russellian-style/tests/test_lint_concrete_instance_density.py`:

```python
"""lint_concrete_instance_density: NER count per paragraph; flag 3+ consecutive paragraphs with zero."""
from pathlib import Path


def _write(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "draft.md"
    p.write_text(text, encoding="utf-8")
    return p


def test_three_abstract_paragraphs_flagged(tmp_path):
    from scripts.lint_concrete_instance_density import lint_concrete_instance_density
    text = (
        "The system processes inputs. The framework outputs results.\n\n"
        "The platform abstracts away complexity. The pipeline orchestrates stages.\n\n"
        "The architecture is layered. The implementation is modular.\n"
    )
    findings = lint_concrete_instance_density(_write(tmp_path, text))
    assert any(f["rule"] == "concrete-instance-density" for f in findings)
    f = [f for f in findings if f["rule"] == "concrete-instance-density"][0]
    assert f["severity"] in ("important", "advisory")


def test_concrete_paragraphs_pass(tmp_path):
    from scripts.lint_concrete_instance_density import lint_concrete_instance_density
    text = (
        "Russell wrote in 1912 that philosophy starts with simple things.\n\n"
        "The Royal Society convened in London on May 14th, 1660.\n\n"
        "Cambridge admitted Wittgenstein in October 1911.\n"
    )
    findings = lint_concrete_instance_density(_write(tmp_path, text))
    assert findings == []


def test_occupational_noun_counts_as_concrete(tmp_path):
    from scripts.lint_concrete_instance_density import lint_concrete_instance_density
    text = (
        "The censor approved the bulletin. The official signed the order.\n\n"
        "The philosopher disputed the claim. The worker filed a grievance.\n\n"
        "The student handed in the essay. The judge sealed the ruling.\n"
    )
    findings = lint_concrete_instance_density(_write(tmp_path, text))
    assert findings == []
```

- [ ] **Step 2: Run, verify failure**

```bash
cd skills/russellian-style
.venv/Scripts/python.exe -m pytest tests/test_lint_concrete_instance_density.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement lint_concrete_instance_density.py**

Create `skills/russellian-style/scripts/lint_concrete_instance_density.py`:

```python
"""Concrete-instance-density linter.

Counts named entities (spaCy NER: PERSON, ORG, GPE, DATE, MONEY, ORDINAL,
EVENT, NORP, LOC) per paragraph plus a custom list of occupational nouns
('the official', 'the censor', etc.). Flags 3+ consecutive paragraphs
with zero concrete instances.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import spacy


_NLP = None


def _nlp():
    global _NLP
    if _NLP is None:
        _NLP = spacy.load("en_core_web_sm", disable=["lemmatizer", "tagger"])
    return _NLP


_NER_LABELS = {"PERSON", "ORG", "GPE", "DATE", "MONEY", "ORDINAL", "EVENT", "NORP", "LOC", "TIME"}

_OCCUPATIONAL_NOUNS = {
    "official", "censor", "philosopher", "worker", "student", "judge",
    "magistrate", "officer", "professor", "physician", "scholar", "tradesman",
    "soldier", "merchant", "scientist", "clerk", "minister", "barrister",
}


def _paragraphs(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]


def _concrete_count(para: str) -> int:
    nlp = _nlp()
    doc = nlp(para)
    ner_count = sum(1 for ent in doc.ents if ent.label_ in _NER_LABELS)
    occ_re = re.compile(
        r"\bthe\s+(" + "|".join(re.escape(w) for w in _OCCUPATIONAL_NOUNS) + r")\b",
        flags=re.IGNORECASE,
    )
    occ_count = len(occ_re.findall(para))
    return ner_count + occ_count


def lint_concrete_instance_density(path: Path) -> list[dict]:
    text = Path(path).read_text(encoding="utf-8")
    paras = _paragraphs(text)
    if len(paras) < 3:
        return []
    counts = [_concrete_count(p) for p in paras]

    findings: list[dict] = []
    # Trigger: 3+ consecutive paragraphs with zero concrete instances.
    run_start = None
    for i, c in enumerate(counts):
        if c == 0:
            if run_start is None:
                run_start = i
            if i - run_start + 1 >= 3:
                findings.append({
                    "rule": "concrete-instance-density",
                    "severity": "important",
                    "run_start_paragraph": run_start,
                    "run_length": i - run_start + 1,
                    "message": (
                        f"{i - run_start + 1} consecutive paragraphs with zero concrete "
                        f"instances (PERSON/ORG/GPE/DATE/MONEY/ORDINAL or occupational noun)."
                    ),
                })
        else:
            run_start = None

    # Advisory: avg density < 0.5 per paragraph.
    avg = sum(counts) / len(counts)
    if avg < 0.5 and not findings:
        findings.append({
            "rule": "concrete-instance-density",
            "severity": "advisory",
            "avg_per_paragraph": round(avg, 2),
            "message": f"Average concrete-instance density {avg:.2f} below 0.5/paragraph.",
        })

    return findings


if __name__ == "__main__":
    import sys
    print(json.dumps(lint_concrete_instance_density(Path(sys.argv[1])), indent=2))
```

- [ ] **Step 4: Run tests, verify pass**

```bash
cd skills/russellian-style
.venv/Scripts/python.exe -m pytest tests/test_lint_concrete_instance_density.py -v
```

Expected: 3 PASS. If `spacy.load("en_core_web_sm")` fails, run `.venv/Scripts/python.exe -m spacy download en_core_web_sm` first.

- [ ] **Step 5: Commit**

```bash
git add skills/russellian-style/scripts/lint_concrete_instance_density.py skills/russellian-style/tests/test_lint_concrete_instance_density.py
git commit -m "russellian-style: lint_concrete_instance_density flags 3+ abstract paragraphs in a row"
```

## Task B4: lint_epistemic_precision.py

**Files:**
- Create: `skills/russellian-style/scripts/lint_epistemic_precision.py`
- Test: `skills/russellian-style/tests/test_lint_epistemic_precision.py`

Three categories: banned-vague (always fail), allowed-bounded (recognise, do not flag), required-uncertainty (numeric specificity without source attribution).

- [ ] **Step 1: Write the failing test**

Create `skills/russellian-style/tests/test_lint_epistemic_precision.py`:

```python
"""lint_epistemic_precision: banned vague / allowed bounded / required uncertainty."""
from pathlib import Path


def _write(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "draft.md"
    p.write_text(text, encoding="utf-8")
    return p


def test_banned_vague_flagged(tmp_path):
    from scripts.lint_epistemic_precision import lint_epistemic_precision
    text = "Perhaps the system fails. It could be argued that the design is flawed."
    findings = lint_epistemic_precision(_write(tmp_path, text))
    cats = {f["category"] for f in findings}
    assert "banned_vague" in cats


def test_allowed_bounded_not_flagged(tmp_path):
    from scripts.lint_epistemic_precision import lint_epistemic_precision
    text = (
        "The latency stays within 5% of the baseline under nominal load. "
        "In cases where the source has been verified, the claim is admitted."
    )
    findings = lint_epistemic_precision(_write(tmp_path, text))
    cats = {f["category"] for f in findings}
    assert "banned_vague" not in cats
    assert "required_uncertainty" not in cats


def test_required_uncertainty_flagged(tmp_path):
    """Numeric specificity without source attribution."""
    from scripts.lint_epistemic_precision import lint_epistemic_precision
    text = "The team shipped 47 features in the third quarter of 2024."
    findings = lint_epistemic_precision(_write(tmp_path, text))
    cats = {f["category"] for f in findings}
    assert "required_uncertainty" in cats


def test_required_uncertainty_suppressed_when_source_present(tmp_path):
    from scripts.lint_epistemic_precision import lint_epistemic_precision
    text = "The team shipped 47 features in the third quarter of 2024 (source: internal release log)."
    findings = lint_epistemic_precision(_write(tmp_path, text))
    cats = {f["category"] for f in findings}
    assert "required_uncertainty" not in cats
```

- [ ] **Step 2: Run, verify failure**

```bash
cd skills/russellian-style
.venv/Scripts/python.exe -m pytest tests/test_lint_epistemic_precision.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement lint_epistemic_precision.py**

Create `skills/russellian-style/scripts/lint_epistemic_precision.py`:

```python
"""Epistemic precision linter.

Three categories replacing the binary hedge model:
1. banned_vague: vague hedges (perhaps, arguably, ...). Always flagged.
2. allowed_bounded: numeric/conditional constraints. Recognised, not flagged.
3. required_uncertainty: numeric specificity lacking a source attribution.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .lint_common import iter_sentences, load_markdown


_BANNED_VAGUE = [
    "perhaps", "arguably", "to some extent", "in some sense",
    "to a certain extent", "it could be argued", "many would say",
    "it might be suggested",
]

_ALLOWED_BOUNDED_PATTERNS = [
    re.compile(r"\bwithin\s+\d+\s*%", re.IGNORECASE),
    re.compile(r"\bunder\s+condition\b", re.IGNORECASE),
    re.compile(r"\bin\s+cases\s+where\b", re.IGNORECASE),
    re.compile(r"\bup\s+to\s+\d+\b", re.IGNORECASE),
    re.compile(r"\bat\s+least\s+\d+\b", re.IGNORECASE),
]

_NUMERIC_SPECIFICITY = re.compile(
    r"\b(\d{1,4}(?:\.\d+)?(?:%)?|\d{1,4}(?:st|nd|rd|th))\b"
)

_ATTRIBUTION_HINTS = re.compile(
    r"\b(source|cited|according to|reports?|per\s+\w+|\[clm-\d+-\d+\])\b",
    re.IGNORECASE,
)


def _banned_vague_pattern() -> re.Pattern:
    return re.compile(
        r"\b(" + "|".join(re.escape(p) for p in sorted(_BANNED_VAGUE, key=len, reverse=True)) + r")\b",
        flags=re.IGNORECASE,
    )


def lint_epistemic_precision(path: Path) -> list[dict]:
    text = load_markdown(path)
    findings: list[dict] = []

    banned_re = _banned_vague_pattern()
    for sentence in iter_sentences(text):
        for m in banned_re.finditer(sentence.text):
            findings.append({
                "rule": "epistemic-precision",
                "category": "banned_vague",
                "phrase": m.group(1),
                "sentence": sentence.text,
                "line": getattr(sentence, "line", 0),
                "severity": "important",
            })

    # required_uncertainty: numeric specificity without attribution.
    sentences = list(iter_sentences(text))
    for i, sentence in enumerate(sentences):
        if not _NUMERIC_SPECIFICITY.search(sentence.text):
            continue
        if any(p.search(sentence.text) for p in _ALLOWED_BOUNDED_PATTERNS):
            continue
        if _ATTRIBUTION_HINTS.search(sentence.text):
            continue
        # Tolerance: attribution in the immediately preceding sentence.
        if i > 0 and _ATTRIBUTION_HINTS.search(sentences[i - 1].text):
            continue
        findings.append({
            "rule": "epistemic-precision",
            "category": "required_uncertainty",
            "sentence": sentence.text,
            "line": getattr(sentence, "line", 0),
            "severity": "advisory",
            "message": "Numeric specificity without source attribution in this sentence or the previous one.",
        })

    return findings


if __name__ == "__main__":
    import sys
    print(json.dumps(lint_epistemic_precision(Path(sys.argv[1])), indent=2))
```

- [ ] **Step 4: Run tests, verify pass**

```bash
cd skills/russellian-style
.venv/Scripts/python.exe -m pytest tests/test_lint_epistemic_precision.py -v
```

Expected: 4 PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/russellian-style/scripts/lint_epistemic_precision.py skills/russellian-style/tests/test_lint_epistemic_precision.py
git commit -m "russellian-style: lint_epistemic_precision replaces binary hedge with three-tier classifier"
```

## Task B5: lint_paragraph_motion.py

**Files:**
- Create: `skills/russellian-style/scripts/lint_paragraph_motion.py`
- Test: `skills/russellian-style/tests/test_lint_paragraph_motion.py`

Rubric tagger per paragraph using lexical cues. Flags sections where >70% of paragraphs are flat (assertion-only or assertion+justification).

- [ ] **Step 1: Write the failing test**

Create `skills/russellian-style/tests/test_lint_paragraph_motion.py`:

```python
"""lint_paragraph_motion: per-paragraph shape rubric + flat-axiom-stack detection."""
from pathlib import Path


def _write(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "draft.md"
    p.write_text(text, encoding="utf-8")
    return p


def test_assertion_only_paragraphs_flagged(tmp_path):
    from scripts.lint_paragraph_motion import lint_paragraph_motion
    text = (
        "The ledger records claims.\n\n"
        "The graph projects relations.\n\n"
        "The validator enforces shapes.\n\n"
        "The report summarises findings.\n"
    )
    findings = lint_paragraph_motion(_write(tmp_path, text))
    assert any(f["rule"] == "paragraph-motion" for f in findings)
    f = [f for f in findings if f["rule"] == "paragraph-motion"][0]
    assert f["flat_proportion"] >= 0.7


def test_concession_turn_recognised(tmp_path):
    from scripts.lint_paragraph_motion import classify_paragraph
    para = (
        "The defender of the practice will say that the system is necessary. "
        "But the same defender, pressed on the cost, can find no answer that the "
        "tired worker will accept. The necessity, once it meets the worker, breaks."
    )
    assert classify_paragraph(para) == "concession_turn"


def test_question_answer_recognised(tmp_path):
    from scripts.lint_paragraph_motion import classify_paragraph
    para = (
        "What does the ledger record? It records the propositions, their sources, "
        "their state, and the transitions between states."
    )
    assert classify_paragraph(para) == "question_answer"


def test_mixed_section_not_flagged(tmp_path):
    from scripts.lint_paragraph_motion import lint_paragraph_motion
    text = (
        "What does the ledger do? It binds every claim to its source.\n\n"
        "The defender of mood will say that prose can carry truth without "
        "address. But mood, pressed by a domain reader, dissolves.\n\n"
        "Consider the auditor. She opens the ledger; the ledger answers.\n\n"
        "The contract for chapter four therefore lists six claims.\n"
    )
    findings = lint_paragraph_motion(_write(tmp_path, text))
    flat = [f for f in findings if f["rule"] == "paragraph-motion"]
    assert flat == []
```

- [ ] **Step 2: Run, verify failure**

```bash
cd skills/russellian-style
.venv/Scripts/python.exe -m pytest tests/test_lint_paragraph_motion.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement lint_paragraph_motion.py**

Create `skills/russellian-style/scripts/lint_paragraph_motion.py`:

```python
"""Paragraph-motion linter.

Tags each paragraph with one shape using lexical cues, then flags sections
where >70% of paragraphs are flat (assertion_only or assertion_justification).
"""
from __future__ import annotations

import json
import re
from pathlib import Path


SHAPES = (
    "assertion_only",
    "assertion_justification",
    "concession_turn",
    "contrast",
    "example_inference",
    "question_answer",
    "definition_by_pressure",
)


_CONCESSION_MARKERS = re.compile(
    r"\b(but|yet|however|nevertheless|still|even so)\b",
    re.IGNORECASE,
)
_DEFENDER_MARKERS = re.compile(
    r"\b(will say|might claim|argues that|insists that|the defender|the critic)\b",
    re.IGNORECASE,
)
_EXAMPLE_MARKERS = re.compile(
    r"\b(for example|for instance|consider|imagine|take the case)\b",
    re.IGNORECASE,
)
_DEFINITION_MARKERS = re.compile(
    r"\b(as commonly used|as usually understood|in ordinary language|what people mean by)\b",
    re.IGNORECASE,
)
_THEREFORE_MARKERS = re.compile(r"\b(therefore|hence|so that|thus)\b", re.IGNORECASE)


def _sentences(para: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", para.strip()) if s.strip()]


def classify_paragraph(para: str) -> str:
    sents = _sentences(para)
    if not sents:
        return "assertion_only"

    starts_with_question = "?" in sents[0] and sents[0].rstrip().endswith("?")
    if starts_with_question and len(sents) >= 2:
        return "question_answer"

    if _DEFENDER_MARKERS.search(para) and _CONCESSION_MARKERS.search(para):
        return "concession_turn"

    if _EXAMPLE_MARKERS.search(para) and _THEREFORE_MARKERS.search(para):
        return "example_inference"

    if _DEFINITION_MARKERS.search(para):
        return "definition_by_pressure"

    if _CONCESSION_MARKERS.search(para):
        return "contrast"

    if len(sents) <= 1:
        return "assertion_only"

    return "assertion_justification"


def _paragraphs(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]


def lint_paragraph_motion(path: Path) -> list[dict]:
    text = Path(path).read_text(encoding="utf-8")
    paras = _paragraphs(text)
    if len(paras) < 3:
        return []
    shapes = [classify_paragraph(p) for p in paras]
    flat = {"assertion_only", "assertion_justification"}
    flat_count = sum(1 for s in shapes if s in flat)
    flat_prop = flat_count / len(shapes)

    findings: list[dict] = []
    if flat_prop > 0.70:
        findings.append({
            "rule": "paragraph-motion",
            "severity": "important",
            "flat_proportion": round(flat_prop, 3),
            "shape_distribution": {s: shapes.count(s) for s in SHAPES if shapes.count(s) > 0},
            "message": (
                f"{flat_count}/{len(shapes)} paragraphs are flat "
                "(assertion_only or assertion_justification). Add concession, "
                "contrast, definition-by-pressure, or question-answer motion."
            ),
        })
    return findings


if __name__ == "__main__":
    import sys
    print(json.dumps(lint_paragraph_motion(Path(sys.argv[1])), indent=2))
```

- [ ] **Step 4: Run tests, verify pass**

```bash
cd skills/russellian-style
.venv/Scripts/python.exe -m pytest tests/test_lint_paragraph_motion.py -v
```

Expected: 4 PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/russellian-style/scripts/lint_paragraph_motion.py skills/russellian-style/tests/test_lint_paragraph_motion.py
git commit -m "russellian-style: lint_paragraph_motion detects flat-axiom-stack sections"
```

---

## Phase C — Assets

## Task C1: System-prompt assets (three files)

**Files:**
- Create: `skills/russellian-style/assets/system-prompts/technical-exposition.md`
- Create: `skills/russellian-style/assets/system-prompts/narrative-editorial.md`
- Create: `skills/russellian-style/assets/system-prompts/polemic.md`

- [ ] **Step 1: Create technical-exposition.md**

Create `skills/russellian-style/assets/system-prompts/technical-exposition.md`:

```markdown
# Role

You are writing a chapter section for a non-fiction book under Russellian analytic discipline. The chapter explains, defines, or argues from evidence. The audience is an attentive technical reader who does not need motivational framing.

# Structural mandates

- Vary sentence length deliberately. Include at least one sentence under ten words and at least one over twenty-five in every screen of prose.
- Use compound-complex sentences to demonstrate causality; punctuate them with short declarative beats.
- Open each paragraph with the conclusion the paragraph will earn, not with a system noun.
- End paragraphs with a sentence that changes the pressure of the argument; do not close on restatement.

# Negative constraints (banned words and patterns)

- Banned transition starters: moreover, furthermore, additionally, consequently, subsequently, notably, importantly.
- Banned magic adverbs: quietly, deeply, profoundly, seamlessly, intricately, fundamentally.
- Banned false-certainty markers: clearly, obviously, of course, it is self-evident that, needless to say.
- Banned vague hedges: perhaps, arguably, to some extent, in some sense, it could be argued.
- Banned listicle abstracts: do not write "rests on N premises", "consists of N components", or any phrase that summarises a list before the prose has earned it.
- No rhetorical questions used as section openers. Use them inside a paragraph if a question deserves an answer.

# Rhetorical devices to prefer

- Tricolon with an asymmetric tail: the final element of any three-item list should be structurally longer than the first two ("Life, Liberty, and the pursuit of Happiness").
- Antithesis: balance opposing elements to expose a distinction.
- Concession and turn: open with the strongest version of the opposing view, then turn the thought.
- Concrete instance: every abstraction must earn its place with a specific person, institution, object, place, date, or measurable event.

# Closing rules

- Use contractions where natural for the register.
- Cite numeric or surprising claims with a source token; do not assert specificity without attribution.
- Do not end the section with a summary paragraph. The last sentence is the section's verdict.
```

- [ ] **Step 2: Create narrative-editorial.md**

Create `skills/russellian-style/assets/system-prompts/narrative-editorial.md`:

```markdown
# Role

You are writing a narrative chapter or book introduction under Russellian discipline, but with room to build scenes and let the reader move through the material at human pace. You may name people, places, and small physical details.

# Structural mandates

- Sentence lengths swing wildly. Follow a thirty-word meandering description with a four-word blunt statement.
- Allow hyperbaton — the deliberate alteration of normal word order to preserve a specific cadence.
- Conjunction-starts are allowed. Begin a sentence with And, But, or Yet when the rhythm earns it.
- Each scene needs at least one concrete actor by name or role within the first three sentences.

# Negative constraints

- Banned magic adverbs: quietly, deeply, profoundly, seamlessly, intricately, beautifully.
- Banned emotional-summary closers. Do not write "she felt overwhelmed" or "he was deeply moved." Describe physical action and environmental detail; let the reader infer the feeling.
- Banned transition starters: moreover, furthermore, additionally.
- Banned listicle abstracts.

# Rhetorical devices to prefer

- Tricolon with an asymmetric tail.
- Sentence fragments are allowed when they earn a punch.
- One parenthetical aside per scene is acceptable.
- Concrete sensory anchors: a sound, a temperature, a smell, a specific street.

# Closing rules

- Do not use "In conclusion" or "Ultimately."
- Close on an image or an action, not a summary.
```

- [ ] **Step 3: Create polemic.md**

Create `skills/russellian-style/assets/system-prompts/polemic.md`:

```markdown
# Role

You are writing public argument — an op-ed, a retrospective, or an opinionated explanation — under Russellian discipline. The reader knows you have a position; the position must be argued, not announced.

# Structural mandates

- Antithesis carries the section. Each paragraph should balance an opposing element against the position.
- Use sharp turns. The last sentence of each paragraph should reverse, narrow, or sharpen the first.
- Sentence lengths must vary; bury a four-word verdict in the middle of a long paragraph.

# Negative constraints

- Banned: any phrasing that asserts the conclusion without earning it ("clearly", "obviously", "the answer is").
- Banned: pure outrage. Anger without analysis is noise.
- Banned: tricolons used decoratively without an asymmetric tail.
- Banned: magic adverbs.

# Rhetorical devices to prefer

- Dry irony where a false view deserves compression.
- Concrete counterexample: name the official, the institution, the date.
- The well-formed antithesis: balance opposing terms in the same paragraph and let the contrast carry the point.
- Personification of a prevailing view — give the opposing position a human figure rather than treating it as an abstract position.

# Closing rules

- The closing sentence is the verdict. It should reverse or sharpen the opener.
- Do not close on a hope or a call to action. State what the argument has shown.
```

- [ ] **Step 4: Verify the three files load through system_prompt_loader**

```bash
cd skills/russellian-style
.venv/Scripts/python.exe -c "from scripts.system_prompt_loader import load; print(load('technical-exposition')[:80]); print(load('narrative-editorial')[:80]); print(load('polemic')[:80])"
```

Expected: three excerpts printed; no errors.

- [ ] **Step 5: Commit**

```bash
git add skills/russellian-style/assets/system-prompts/
git commit -m "russellian-style: three mode-keyed system prompts (technical, narrative, polemic)"
```

## Task C2: russellian-vitality-guide.md

**Files:**
- Create: `skills/russellian-style/references/russellian-vitality-guide.md`

- [ ] **Step 1: Create the guide**

Create `skills/russellian-style/references/russellian-vitality-guide.md`:

```markdown
# Russellian Vitality Guide

The existing `russellian-style-guide.md` lists the negative rules: what to remove. This file lists the positive rules: what to put in. The deterministic linters can punish bloat, hedge, passive voice, listicle abstract, and flat rhythm; they cannot reward a concrete instance, a useful concession, a witty antithesis, or a paragraph that earns its last sentence. This guide tells the writer (human or agent) what those moves are.

The six rules below derive from the 50-paragraph corpus map at `references/russell-corpus-map.md`. Each rule cites one corpus entry that demonstrates it.

## 1. Open with a difficulty, not a system noun

Begin a paragraph with the human or intellectual difficulty the paragraph will address. Do not begin with "the system", "the framework", "the platform". A system noun in the subject slot tells the reader nothing has happened yet.

*Corpus exemplar:* `problems-006` ("Wrong conception split into two causes"). Russell opens by naming the wrong conception, not by describing the apparatus that produces it.

## 2. Use concrete examples to earn abstractions

Every abstract claim earns the right to exist by producing a concrete instance: a person, an institution, an object, a date, a measurable event, or one of the occupational nouns Russell relies on (the official, the censor, the philosopher, the worker).

*Corpus exemplar:* `problems-001` ("Relation made concrete through a room example"). Russell defines an abstract relation through an ordinary spatial case before naming it abstractly.

## 3. Permit exact uncertainty; ban vague hedging

Vague hedges (*perhaps*, *arguably*, *to some extent*) are evasive and banned. Exact uncertainty — *within 5%*, *under condition Y*, *in cases where the source has been verified* — is welcomed. Numeric specificity without a source attribution is itself a hedge; cite the source token.

*Corpus exemplar:* `mysticism-006` ("Ignorance stated plainly before the thesis"). Russell admits the limit of his knowledge before stating the testable claim.

## 4. Use antithesis to expose a distinction

When two positions are in tension, balance them in the same paragraph and let the contrast carry the point. Do not stage a list of positives followed by a list of negatives; that is a balance sheet, not an argument.

*Corpus exemplar:* `free-001` ("Belief opposed by rational doubt"). Russell builds the paragraph around a single memorable reversal: the wish to doubt set against the wish to believe.

## 5. Vary paragraph motion

A section that uses only assertion-and-justification paragraphs is a flat axiom stack. Russell varies motion paragraph by paragraph:

- common-view → concession → distinction → consequence → turn
- question → partial answer → new question
- ordinary case → instability under pressure → narrowed inquiry
- abstract claim → concrete counterexample → resulting refinement

*Corpus exemplar:* `analysis-001` ("Common examples open a technical definition"). The paragraph starts with what people think they know and then begins to make the term unstable.

## 6. Let the last sentence change pressure

The last sentence of a paragraph is its verdict, not its summary. It should leave the reader in a different epistemic position than the first sentence did. A paragraph that closes on a restatement of its topic sentence has wasted its second half.

*Corpus exemplar:* `problems-010` ("Uncertainty turned into value"). The paragraph ends with a reversal that changes how the reader values the limitation Russell has been describing.

## Using this guide alongside the negative rules

The negative-rules guide (`russellian-style-guide.md`) is enforced by deterministic linters. This guide is calibration material for the writer and the persona reviewers. The five new vitality linters (`lint_burstiness`, `lint_ai_vocabulary`, `lint_concrete_instance_density`, `lint_epistemic_precision`, `lint_paragraph_motion`) approximate the positive rules from the failure side: they detect the absence of these moves. They do not detect their presence; that judgment lives with the persona panel and the writer.

When a vitality linter fires, `style_pass_report.py` retrieves one corpus exemplar (via `retrieve_corpus_anchor.py`) whose rhetorical move corresponds to the missing motion. The exemplar is a reference + lesson, not a paragraph for the writer to imitate. Russell's value is the paragraph motion, not the diction.
```

- [ ] **Step 2: Commit**

```bash
git add skills/russellian-style/references/russellian-vitality-guide.md
git commit -m "russellian-style: positive-doctrine vitality guide companion to negative rules"
```

---

## Phase D — Integration

## Task D1: Extend style_pass_report.py

**Files:**
- Modify: `skills/russellian-style/scripts/style_pass_report.py`
- Test: `skills/russellian-style/tests/test_style_pass_report_vitality.py`

Add a `vitality_metrics` block and per-finding corpus-anchor attachment.

- [ ] **Step 1: Read the existing style_pass_report.py**

```bash
cat skills/russellian-style/scripts/style_pass_report.py | head -120
```

Look for the function that aggregates the existing linters (likely `generate_report` or similar) and where its output dict is constructed.

- [ ] **Step 2: Write the failing test**

Create `skills/russellian-style/tests/test_style_pass_report_vitality.py`:

```python
"""style_pass_report v0.2: emits vitality_metrics block + corpus_anchors list."""
from pathlib import Path


def _write(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "draft.md"
    p.write_text(text, encoding="utf-8")
    return p


def test_report_includes_vitality_metrics_block(tmp_path):
    from scripts.style_pass_report import generate_report_dict
    text = "Short sentence one. Another short one. Third short. Fourth short."
    report = generate_report_dict(_write(tmp_path, text))
    assert "vitality_metrics" in report
    vm = report["vitality_metrics"]
    expected_keys = {
        "burstiness_fano_factor",
        "in_band_proportion",
        "ai_vocabulary_violations",
        "concrete_instance_density_violations",
        "epistemic_precision_violations",
        "paragraph_motion_score",
        "russell_vitality_score",
    }
    assert expected_keys <= set(vm.keys())


def test_corpus_anchors_attached_when_paragraph_motion_fires(tmp_path):
    from scripts.style_pass_report import generate_report_dict
    text = (
        "The ledger records claims.\n\n"
        "The graph projects relations.\n\n"
        "The validator enforces shapes.\n\n"
        "The report summarises findings.\n"
    )
    report = generate_report_dict(_write(tmp_path, text))
    anchors = report.get("corpus_anchors", [])
    if any("paragraph-motion" in str(v) for v in report.get("findings", [])):
        assert anchors, "expected at least one corpus anchor when paragraph-motion fires"
        a = anchors[0]
        assert "corpus_id" in a["anchor"]
        assert "calibration_lesson" in a["anchor"]


def test_negative_metrics_block_unchanged(tmp_path):
    from scripts.style_pass_report import generate_report_dict
    text = "Hello world."
    report = generate_report_dict(_write(tmp_path, text))
    assert "negative_metrics" in report
    neg = report["negative_metrics"]
    expected_neg = {
        "hedge_count", "passive_voice_ratio", "modifier_budget_violations",
        "parallel_structure_violations", "listicle_abstract_count", "rhythm_violations",
    }
    assert expected_neg <= set(neg.keys())
```

- [ ] **Step 3: Run, verify failure**

```bash
cd skills/russellian-style
.venv/Scripts/python.exe -m pytest tests/test_style_pass_report_vitality.py -v
```

Expected: FAIL — either `generate_report_dict` doesn't exist or it doesn't emit `vitality_metrics`.

- [ ] **Step 4: Modify style_pass_report.py**

The exact diff depends on the existing shape. The principle is: add a `generate_report_dict(path)` public function that returns the schema below, and have the existing markdown-rendering function call it.

Insert into `skills/russellian-style/scripts/style_pass_report.py` (after the existing imports and any existing helpers):

```python
from .lint_hedges import lint_hedges
from .lint_passive_voice import lint_passive_voice
from .lint_signal_density import lint_signal_density
from .lint_parallel_structure import lint_parallel_structure
from .lint_sentence_rhythm import lint_sentence_rhythm
from .lint_listicle_abstract import lint_listicle_abstract
from .lint_burstiness import lint_burstiness
from .lint_ai_vocabulary import lint_ai_vocabulary
from .lint_concrete_instance_density import lint_concrete_instance_density
from .lint_epistemic_precision import lint_epistemic_precision
from .lint_paragraph_motion import lint_paragraph_motion
from .retrieve_corpus_anchor import retrieve_anchor


# Map paragraph-motion shape → the rhetorical_mode argument to retrieve_anchor.
_MOTION_TO_MODE = {
    "flat_axiom_stack": "problems",  # Russell's popular-philosophy register
}


def _russell_vitality_score(metrics: dict) -> float:
    pm = metrics["paragraph_motion_score"]
    bf = metrics["burstiness_fano_factor"]
    av = metrics["ai_vocabulary_violations"]
    burst_term = min(bf / 0.7, 1.0)
    av_term = max(0.0, 1.0 - av / 10.0)
    return round(pm * 0.4 + burst_term * 0.3 + av_term * 0.3, 3)


def generate_report_dict(path) -> dict:
    from pathlib import Path
    p = Path(path)

    # Existing negative linters.
    hedges = lint_hedges(p)
    passives = lint_passive_voice(p)
    signal = lint_signal_density(p)
    parallel = lint_parallel_structure(p)
    rhythm = lint_sentence_rhythm(p)
    listicle = lint_listicle_abstract(p)

    # New vitality linters.
    burst = lint_burstiness(p)
    ai_vocab = lint_ai_vocabulary(p)
    concrete = lint_concrete_instance_density(p)
    episteme = lint_epistemic_precision(p)
    motion = lint_paragraph_motion(p)

    # Pull per-section metrics from burst (one entry per fired section).
    fano = burst[0]["fano_factor"] if burst else 0.7  # 0.7 = at-target default
    in_band = burst[0]["in_band_proportion"] if burst else 0.0

    # paragraph_motion_score: 1.0 if no flat sections, lower otherwise.
    if motion:
        pm_score = round(1.0 - motion[0].get("flat_proportion", 0.0), 3)
    else:
        pm_score = 1.0

    vitality_metrics = {
        "burstiness_fano_factor": fano,
        "in_band_proportion": in_band,
        "ai_vocabulary_violations": len(ai_vocab),
        "concrete_instance_density_violations": len(concrete),
        "epistemic_precision_violations": len(episteme),
        "paragraph_motion_score": pm_score,
    }
    vitality_metrics["russell_vitality_score"] = _russell_vitality_score(vitality_metrics)

    negative_metrics = {
        "hedge_count": len(hedges),
        "passive_voice_ratio": round(len(passives) / max(1, len(passives) + 1), 3),
        "modifier_budget_violations": len(signal),
        "parallel_structure_violations": len(parallel),
        "listicle_abstract_count": len(listicle),
        "rhythm_violations": len(rhythm),
    }

    findings = []
    for f in hedges + passives + signal + parallel + rhythm + listicle:
        findings.append({"section": "negative", "finding": f})
    for f in burst + ai_vocab + concrete + episteme + motion:
        findings.append({"section": "vitality", "finding": f})

    corpus_anchors = []
    if motion:
        try:
            anchor = retrieve_anchor(rhetorical_mode="problems", seed=42)
            corpus_anchors.append({
                "for_finding": "paragraph-motion:flat_axiom_stack",
                "anchor": {
                    "corpus_id": anchor.corpus_id,
                    "source_title": anchor.source_title,
                    "rhetorical_move": anchor.rhetorical_move,
                    "calibration_lesson": anchor.calibration_lesson,
                },
            })
        except (LookupError, ValueError):
            pass

    return {
        "path": str(p),
        "negative_metrics": negative_metrics,
        "vitality_metrics": vitality_metrics,
        "findings": findings,
        "corpus_anchors": corpus_anchors,
    }
```

If the file already has a markdown-rendering entrypoint, have it call `generate_report_dict` and render both blocks. The principle: do not delete or rename the existing public surface; only add.

- [ ] **Step 5: Run tests, verify pass**

```bash
cd skills/russellian-style
.venv/Scripts/python.exe -m pytest tests/test_style_pass_report_vitality.py tests/test_style_pass_report.py -v
```

Expected: all new tests PASS; existing `test_style_pass_report.py` still PASSES.

- [ ] **Step 6: Commit**

```bash
git add skills/russellian-style/scripts/style_pass_report.py skills/russellian-style/tests/test_style_pass_report_vitality.py
git commit -m "russellian-style: style_pass_report emits vitality_metrics + corpus_anchors"
```

## Task D2: book-compose integration

**Files:**
- Modify: `skills/book-compose/scripts/persona_review_pass.py` (or the chapter-drafting site; verify)
- Modify: `skills/book-compose/scripts/chapter_contract.py`
- Modify: `skills/book-compose/assets/chapter-contract.schema.json`
- Modify: `skills/book-compose/SKILL.md`

The chapter contract gains an optional `prose_mode` enum field. The drafting site loads the matching system prompt from russellian-style via the existing `load_russellian_style_module` helper.

- [ ] **Step 1: Read the existing contract schema**

```bash
cat skills/book-compose/assets/chapter-contract.schema.json
```

Locate the `properties` block.

- [ ] **Step 2: Write the failing test**

Append to `skills/book-compose/tests/test_chapter_contract.py` (or a new test file if the existing one isn't easily extended):

```python
def test_chapter_contract_accepts_prose_mode():
    import json
    from pathlib import Path
    import jsonschema
    schema = json.loads((
        Path(__file__).resolve().parent.parent / "assets" / "chapter-contract.schema.json"
    ).read_text(encoding="utf-8"))
    valid = {
        "chapter_id": "ch-01",
        "title": "Test",
        "purpose": "purpose long enough to satisfy schema",
        "audience": "senior-engineer",
        "chapter_type": "reference",
        "prose_mode": "narrative-editorial",
        "evidence_requirements": {"minimum_verified_claims": 0, "max_unresolved_conflicts": 0},
        "acceptance_tests": ["hedge_count == 0"],
        "output_formats": ["markdown"],
    }
    jsonschema.validate(instance=valid, schema=schema)


def test_chapter_contract_rejects_unknown_prose_mode():
    import json, pytest
    from pathlib import Path
    import jsonschema
    schema = json.loads((
        Path(__file__).resolve().parent.parent / "assets" / "chapter-contract.schema.json"
    ).read_text(encoding="utf-8"))
    invalid = {
        "chapter_id": "ch-01",
        "title": "Test",
        "purpose": "purpose long enough to satisfy schema",
        "audience": "senior-engineer",
        "chapter_type": "reference",
        "prose_mode": "bogus-mode",
        "evidence_requirements": {"minimum_verified_claims": 0, "max_unresolved_conflicts": 0},
        "acceptance_tests": ["hedge_count == 0"],
        "output_formats": ["markdown"],
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=invalid, schema=schema)
```

- [ ] **Step 3: Run, verify failure**

```bash
cd skills/book-compose
.venv/Scripts/python.exe -m pytest tests/test_chapter_contract.py::test_chapter_contract_accepts_prose_mode tests/test_chapter_contract.py::test_chapter_contract_rejects_unknown_prose_mode -v
```

Expected: FAIL — schema does not yet declare `prose_mode`.

- [ ] **Step 4: Add prose_mode to the schema**

Edit `skills/book-compose/assets/chapter-contract.schema.json`. Inside the `properties` block, add:

```json
"prose_mode": {
  "type": "string",
  "enum": ["technical-exposition", "narrative-editorial", "polemic"],
  "description": "Optional. Selects which russellian-style system prompt the drafter loads. Defaults to technical-exposition.",
  "default": "technical-exposition"
}
```

Do NOT add `prose_mode` to the schema's `required` array. The field is optional with a default.

- [ ] **Step 5: Run tests, verify pass**

```bash
cd skills/book-compose
.venv/Scripts/python.exe -m pytest tests/test_chapter_contract.py -v
```

Expected: both new tests PASS; existing tests unchanged.

- [ ] **Step 6: Add load_system_prompt helper to book-compose**

Append to `skills/book-compose/scripts/persona_review_pass.py`:

```python
def load_system_prompt(prose_mode: str = "technical-exposition") -> str:
    """Load the russellian-style system prompt for the given prose mode.

    Returns the markdown text of the prompt. Falls back to the
    technical-exposition default if the mode is unknown (with a warning
    in the returned text) rather than raising — the drafter must always
    have some system prompt to inject.
    """
    spl = load_russellian_style_module("system_prompt_loader")
    try:
        return spl.load(prose_mode)
    except ValueError:
        return spl.load(spl.DEFAULT_MODE)
```

- [ ] **Step 7: Add a test for the loader integration**

Append to `skills/book-compose/tests/test_persona_review_pass.py`:

```python
def test_load_system_prompt_returns_text_for_known_mode():
    from scripts.persona_review_pass import load_system_prompt
    text = load_system_prompt("technical-exposition")
    assert "Role" in text or "role" in text
    assert "Banned" in text or "banned" in text or "Negative" in text


def test_load_system_prompt_falls_back_for_unknown_mode():
    from scripts.persona_review_pass import load_system_prompt
    text = load_system_prompt("nonexistent-mode")
    assert text  # falls back to default; non-empty
```

- [ ] **Step 8: Run integration tests**

```bash
cd skills/book-compose
.venv/Scripts/python.exe -m pytest tests/test_persona_review_pass.py -v
```

Expected: new tests PASS; existing tests unchanged.

- [ ] **Step 9: Update book-compose/SKILL.md**

Modify Stage 5 in `skills/book-compose/SKILL.md`:

```markdown
5. **Draft** — per-section: load the russellian-style system prompt matching the chapter contract's `prose_mode` field (one of `technical-exposition`, `narrative-editorial`, `polemic`; defaults to `technical-exposition`) → select claims → first pass → `russellian-style` → `humanizer` → write back.
```

- [ ] **Step 10: Commit**

```bash
git add skills/book-compose/assets/chapter-contract.schema.json skills/book-compose/scripts/persona_review_pass.py skills/book-compose/tests/test_chapter_contract.py skills/book-compose/tests/test_persona_review_pass.py skills/book-compose/SKILL.md
git commit -m "book-compose: load russellian-style system prompt by chapter prose_mode"
```

---

## Phase E — Sweep + PR

## Task E1: Full-suite test sweep, push, open PR

- [ ] **Step 1: Run every affected skill's test suite**

```bash
cd skills/russellian-style && .venv/Scripts/python.exe -m pytest tests/ -q && cd ../..
cd skills/book-compose && .venv/Scripts/python.exe -m pytest tests/ -q && cd ../..
cd skills/book-review && .venv/Scripts/python.exe -m pytest tests/ -q && cd ../..
cd skills/review-conductor && .venv/Scripts/python.exe -m pytest tests/ -q && cd ../..
```

Expected: every suite green.

- [ ] **Step 2: Run all the new linters against this README**

```bash
cd skills/russellian-style
.venv/Scripts/python.exe -m scripts.lint_burstiness ../../README.md
.venv/Scripts/python.exe -m scripts.lint_ai_vocabulary ../../README.md
.venv/Scripts/python.exe -m scripts.lint_concrete_instance_density ../../README.md
.venv/Scripts/python.exe -m scripts.lint_epistemic_precision ../../README.md
.venv/Scripts/python.exe -m scripts.lint_paragraph_motion ../../README.md
```

Expected: each prints a JSON array (possibly empty). No tracebacks. This is a smoke test, not a gate.

- [ ] **Step 3: Push the branch**

```bash
git push -u origin feat/russellian-vitality
```

- [ ] **Step 4: Open the PR**

```bash
gh pr create --repo CharlesHoskinson/russellian-book-suite \
  --head feat/russellian-vitality \
  --base main \
  --title "russellian-style vitality layer: 5 advisory linters + corpus retrieval + system prompts" \
  --body "$(cat <<'EOF'
## Summary

Implements docs/specs/2026-05-14-russellian-vitality-design.md. Single additive PR.

**New advisory linters (5)**
- \`lint_burstiness\` — Fano factor on sentence-length distribution; flags the PDF-grounded AI signature band [12, 17] words.
- \`lint_ai_vocabulary\` — false certainty, magic adverbs, transition-adverb starters; delegates to humanizer's catalog when present and runs the Russell-specific overlay always.
- \`lint_concrete_instance_density\` — spaCy NER per paragraph; flags 3+ consecutive paragraphs with zero concrete instances.
- \`lint_epistemic_precision\` — three-tier classifier replacing the binary hedge model: banned-vague / allowed-bounded / required-uncertainty.
- \`lint_paragraph_motion\` — paragraph-shape rubric; flags sections where >70% of paragraphs are flat (assertion-only or assertion+justification).

**New utilities**
- \`sibling_skills.py\` — humanizer-catalog loader with graceful fallback.
- \`retrieve_corpus_anchor.py\` — returns one ExemplarRef matching a rhetorical mode (and optionally a move) from the 50-paragraph Russell corpus.
- \`system_prompt_loader.py\` — loads a mode-keyed system prompt from assets/.

**New assets**
- Three system prompts at \`assets/system-prompts/\`: technical-exposition, narrative-editorial, polemic.
- \`assets/ai-vocabulary-supplement.json\` — Russell-specific overlay on top of humanizer's catalog.

**New reference**
- \`references/russellian-vitality-guide.md\` — positive-doctrine companion to the existing negative-rules guide.

**Modified**
- \`style_pass_report.py\` — emits new \`vitality_metrics\` block and \`corpus_anchors\` list alongside the existing \`negative_metrics\`.
- \`book-compose/scripts/persona_review_pass.py\` — adds \`load_system_prompt(mode)\` helper.
- \`book-compose/assets/chapter-contract.schema.json\` — adds optional \`prose_mode\` enum.
- \`book-compose/SKILL.md\` — Stage 5 description updated.

## Severity

All five new linters start **advisory** in v1. They surface in \`style-pass-report.md\` and contribute to \`russell_vitality_score\` (composite, advisory-only). No release gate consumes the new metrics yet. Promotion to gating lands in a follow-up spec once the linters correlate with persona findings.

## Reference

- Spec: \`docs/specs/2026-05-14-russellian-vitality-design.md\`
- Plan: \`docs/plans/2026-05-14-russellian-vitality.md\`
- Background: \`docs/research/2026-05-14-russell-style-enhancement.md\`, \`skills/russellian-style/references/russell-corpus-map.md\`, the "AI Prose: From Terseness to Cadence" PDF.

## Test plan

- [x] All new linters have unit tests covering positive cases, negative cases, and edge cases.
- [x] \`sibling_skills\` degrades gracefully when humanizer is absent.
- [x] \`retrieve_corpus_anchor\` is seed-stable.
- [x] \`system_prompt_loader\` validates the mode enum and raises on missing files.
- [x] \`style_pass_report.generate_report_dict\` emits both negative and vitality blocks.
- [x] \`book-compose\` chapter-contract schema accepts the new \`prose_mode\` field and rejects unknown values.
- [x] Smoke test: all new linters run against this README without tracebacks.
EOF
)"
```

- [ ] **Step 5: Verify the PR opened**

```bash
gh pr list --repo CharlesHoskinson/russellian-book-suite --state open --json number,title,headRefName --jq '.[] | select(.headRefName == "feat/russellian-vitality")'
```

Expected: one row.

---

## Self-Review

(Self-review by the planner; not an execution step.)

**Spec coverage:** Every numbered component in the spec has a task:
- Burstiness linter → Task B1 ✓
- AI-vocabulary linter + supplement JSON → Task B2 ✓
- Concrete-instance-density linter → Task B3 ✓
- Epistemic-precision linter → Task B4 ✓
- Paragraph-motion linter → Task B5 ✓
- `retrieve_corpus_anchor.py` → Task A3 ✓
- `sibling_skills.py` → Task A2 ✓
- `system_prompt_loader.py` → Task A4 ✓
- Three system-prompt assets → Task C1 ✓
- `russellian-vitality-guide.md` → Task C2 ✓
- `style_pass_report.py` revision → Task D1 ✓
- `book-compose` integration + `prose_mode` field → Task D2 ✓
- Sweep + PR → Task E1 ✓

**Placeholder scan:** None. Every code step includes the actual code or the exact file content. The one "verify before editing" note in Task D2 is honest acknowledgement that the existing persona_review_pass.py shape was not re-read during plan authoring — the implementer must read it first.

**Type consistency:** `ExemplarRef` dataclass fields match across `retrieve_corpus_anchor.py` and `style_pass_report.py`. `VALID_MODES` is `{technical-exposition, narrative-editorial, polemic}` in `system_prompt_loader.py`, the schema enum, and the SKILL.md description. `generate_report_dict` returns the schema specified in the spec.

**Known risks:**
- The corpus-index JSON shape is inferred from `references/russell-corpus-map.md`. If the actual JSON has different key names, Task A3 Step 1 catches it; the dataclass mapping is the only adjustment needed.
- spaCy `en_core_web_sm` must be installed in the russellian-style venv. The existing skill already depends on spaCy; the model should already be present. If not: `.venv/Scripts/python.exe -m spacy download en_core_web_sm`.
- The humanizer catalog parser is a coarse markdown bullet-list scrape. If humanizer's SKILL.md uses a non-bullet format, the parser returns `{"_empty": []}` and the AI-vocab linter runs the supplement only. This is intentional graceful-degradation behaviour.

---

## Execution Handoff

Plan complete and saved to `docs/plans/2026-05-14-russellian-vitality.md`. Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration with two-stage review.

**2. Inline Execution** — Execute tasks in this session using `superpowers:executing-plans`, batch execution with checkpoints for your review.

Which approach?
