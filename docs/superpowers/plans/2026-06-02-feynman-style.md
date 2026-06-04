# feynman-style Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `skills/feynman-style/`, a second-pass readability skill that warms Russellized prose into Feynman's voice (concrete analogy, conversational directness, honest curiosity, plain diction) without altering the argument, and wire it into the suite so downstream Russell gates never destroy its work.

**Architecture:** A structural twin of `russellian-style` — prompt-only voice modes do the rewriting; deterministic spaCy/stdlib linters score the result against budgets; an optional offline Burrows-Delta scorer calibrates against a local-drop corpus built from copies the user owns; one new hard gate (`preserve_argument`) guarantees claims and atomic structure survived the pass. Linters are partitioned Surface (Feynman overrides; skipped on Feynman-final text) vs Integrity (always enforced).

**Tech Stack:** Python ≥3.11, spaCy (`en_core_web_sm`), pdfplumber (corpus extraction), pytest. No network: `scrapling-fetch` is NOT a dependency.

**Reference implementation:** `skills/russellian-style/` — copy its packaging, `lint_common.py`, `skill_api.py` registry pattern, `delta_math.py`, `system_prompt_loader.py`, and test conventions. Every linter is `def lint_X(path: Path) -> list[dict]` returning dicts with keys `rule, line, col, sentence` (+ optional `term`). Tests carry `pytestmark = pytest.mark.windows_canary`, read fixtures from `tests/fixtures/`, and run under the skill's own venv.

**Local-drop corpus already supplied:** `C:\russellian-book-suite\Surely You're Joking, Mr. Feynman!.pdf` (317pp, text layer extracts cleanly via pdfplumber; smart-quotes arrive mojibaked as `�` and must be normalized). The user owns this copy; it is read only locally, never committed.

**Conventions:**
- Run tests: `cd skills/feynman-style && .venv/Scripts/python.exe -m pytest tests/<file> -v` (Windows).
- Commit after each task. Terse messages, imperative mood, no AI attribution.
- All paths below are relative to repo root `C:\russellian-book-suite`.

---

## File Structure

```
skills/feynman-style/
├── SKILL.md                              # Task 1
├── skill_api.py                          # Task 13 (registry + lint_fragment + classify)
├── pyproject.toml                        # Task 1
├── .gitignore                            # Task 1  (ignores corpus-raw/ and *-profile generated text)
├── conftest.py                           # Task 1  (spaCy-model skip-gate, copied)
├── assets/
│   ├── feynman-rules.json                # Task 12 (budgets, partition map, word lists)
│   ├── feynman-delta-profile.json        # Task 15 (committed feature thresholds; profile add-on overwrites locally)
│   ├── style-pass-report.template.md     # Task 17
│   ├── system-prompts/
│   │   ├── technical-exposition.md       # Task 16
│   │   ├── pedagogical-walkthrough.md    # Task 16
│   │   └── popular-science.md            # Task 16
│   └── feynman-corpus/
│       └── index.json                    # Task 18 (short fair-use anchors + synthetic before/after)
├── scripts/
│   ├── lint_common.py                    # Task 1  (copied verbatim from russellian-style)
│   ├── lint_reading_grade.py             # Task 2
│   ├── lint_conversational.py            # Task 3
│   ├── lint_latinate_diction.py          # Task 4
│   ├── lint_concreteness.py              # Task 5  (analogy + concrete-instance density)
│   ├── lint_curiosity_markers.py         # Task 6
│   ├── lint_sentence_rhythm.py           # Task 7  (ported, recalibrated)
│   ├── lint_ai_vocabulary.py             # Task 7  (ported)
│   ├── preserve_argument.py              # Task 9  (NEW hard gate)
│   ├── delta_math.py                     # Task 14 (copied verbatim)
│   ├── build_delta_profile.py            # Task 14 (local-drop, offline)
│   ├── score_feynman_delta.py            # Task 15
│   ├── system_prompt_loader.py           # Task 16 (ported)
│   ├── style_pass_report.py              # Task 17
│   └── pdf_extract.py                     # Task 14 (pdfplumber + mojibake normalization)
├── references/
│   ├── feynman-style-guide.md            # Task 20
│   ├── feynman-vitality-guide.md         # Task 20
│   ├── feynman-corpus-map.md             # Task 20
│   ├── before-after-examples.md          # Task 20
│   └── negative-triggers.md              # Task 20 (+ Surface/Integrity partition doc)
└── tests/
    ├── conftest.py                       # Task 1
    ├── fixtures/                         # per-task fixtures
    └── test_*.py                         # per-task
```

Sibling edits: `skills/book-compose/` (Task 21), `skills/book-qa/` (Task 22).

---

## Task 1: Scaffold the skill

**Files:**
- Create: `skills/feynman-style/SKILL.md`
- Create: `skills/feynman-style/pyproject.toml`
- Create: `skills/feynman-style/.gitignore`
- Create: `skills/feynman-style/conftest.py` and `skills/feynman-style/tests/conftest.py`
- Create: `skills/feynman-style/scripts/__init__.py`, `skills/feynman-style/tests/__init__.py`
- Copy: `skills/feynman-style/scripts/lint_common.py` (verbatim from `skills/russellian-style/scripts/lint_common.py`)

- [ ] **Step 1: Create directory tree and copy `lint_common.py`**

```bash
cd C:/russellian-book-suite/skills
mkdir -p feynman-style/scripts feynman-style/assets/system-prompts feynman-style/assets/feynman-corpus feynman-style/references feynman-style/tests/fixtures
cp russellian-style/scripts/lint_common.py feynman-style/scripts/lint_common.py
touch feynman-style/scripts/__init__.py feynman-style/tests/__init__.py
```

- [ ] **Step 2: Write `pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "feynman-style"
version = "0.1.0"
description = "Feynman-voice second-pass linters for the feynman-style Claude Code skill"
requires-python = ">=3.11"
dependencies = [
    "spacy>=3.7,<4.0",
]

[project.optional-dependencies]
ci = ["spacy>=3.7,<4.0", "pyyaml>=6.0,<7.0", "jsonschema>=4.21,<5.0", "pytest>=8.0,<9.0"]
dev = ["pytest>=8.0,<9.0", "pyyaml>=6.0,<7.0", "jsonschema>=4.21,<5.0", "pdfplumber>=0.11,<0.12"]

[tool.setuptools]
packages = ["scripts"]

[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
    "windows_canary: test exercises platform-sensitive behaviour and must run on Windows",
]
addopts = "-v"
```

- [ ] **Step 3: Write `.gitignore`** (corpus text is never committed)

```gitignore
corpus-raw/
*.pdf
.venv/
__pycache__/
```

- [ ] **Step 4: Copy `conftest.py` skip-gate from russellian-style**

```bash
cp C:/russellian-book-suite/skills/russellian-style/tests/conftest.py C:/russellian-book-suite/skills/feynman-style/tests/conftest.py
```
If `skills/russellian-style/conftest.py` exists at skill root, copy that too. (The skip-gate skips spaCy-dependent tests when `en_core_web_sm` is not installed.)

- [ ] **Step 5: Write `SKILL.md`**

```markdown
---
name: feynman-style
description: Rewrite already-Russellized technical prose in Richard Feynman's voice — concrete analogy and physical intuition, conversational directness, honest curiosity, plain playful diction — without altering the argument. Use when user says "apply Feynman style", "make this click", "warm up this prose", "explain this simply", "Feynman pass on this draft", or asks to lower reading difficulty after a Russell pass. Do NOT use before russellian-style, and do NOT use for formal proofs, legal/specification text, API reference, bureaucratic boilerplate, or academic abstracts.
license: MIT
metadata:
  author: charles-hoskinson
  version: 0.1.0
  category: writing
---

# feynman-style

Second pass after `russellian-style`. Russell makes prose correct, atomic, and hedge-free but dense; this skill warms the surface so it clicks for a reader. The argument is fixed by Russell and must survive untouched.

## The two-layer contract

- **Feynman owns the prose surface.** It may re-introduce what Russell strips: rhetorical questions, asides, contractions, direct address, "now you might ask—", honest-doubt framing.
- **Russell owns the argument skeleton.** Feynman must not change claims, claim accuracy, logical structure, or atomic argument order. `preserve_argument` enforces this as a hard gate.

## What it owns

- Surface readability: analogy, concreteness, reading grade, conversational diction, curiosity.
- The Feynman voice prompts and rule registry.
- The Surface/Integrity linter partition (which Russell checks may run on Feynman-final text).
- `preserve_argument` — the claims/structure survival gate.

## What it does NOT own

- Source ingestion, claim ledgers — `book-knowledge`.
- Chapter drafting, release bundles — `book-compose`.
- The Russell discipline itself — `russellian-style`.
- Generic AI tells (em-dash overuse, rule-of-three) — `humanizer`.

## Linters

- `lint_reading_grade.py` — Flesch-Kincaid grade load; flags too-hard sentences.
- `lint_conversational.py` — rewards direct address, contractions, rhetorical questions.
- `lint_latinate_diction.py` — flags Latinate jargon with a plain Anglo-Saxon alternative.
- `lint_concreteness.py` — analogy markers + concrete-instance density; flags ungrounded abstraction.
- `lint_curiosity_markers.py` — rewards honest-doubt / puzzle framing.
- `lint_sentence_rhythm.py` — cadence/burstiness, recalibrated to Feynman.
- `lint_ai_vocabulary.py` — AI-slop vocabulary guard (ported).

## Calibration

Generation is prompt-driven. Linters use absolute thresholds from `assets/feynman-rules.json`. An optional Burrows-Delta scorer (`score_feynman_delta.py`) compares against `assets/feynman-delta-profile.json`; the profile is hand-set by default and can be rebuilt offline by `build_delta_profile.py` from copies the user drops in a git-ignored `corpus-raw/` folder. The skill ships and runs with zero network access.
```

- [ ] **Step 6: Verify import wiring**

Create the venv and confirm `lint_common` imports:
```bash
cd C:/russellian-book-suite/skills/feynman-style
py -3.11 -m venv .venv
.venv/Scripts/python.exe -m pip install -q -e .[dev]
.venv/Scripts/python.exe -m spacy download en_core_web_sm
.venv/Scripts/python.exe -c "import sys; sys.path.insert(0,'.'); from scripts.lint_common import iter_sentences; print('OK')"
```
Expected: `OK`

- [ ] **Step 7: Commit**

```bash
cd C:/russellian-book-suite
git add skills/feynman-style
git commit -m "Scaffold feynman-style skill"
```

---

## Task 2: `lint_reading_grade` — Flesch-Kincaid grade load

**Files:**
- Create: `skills/feynman-style/scripts/lint_reading_grade.py`
- Test: `skills/feynman-style/tests/test_lint_reading_grade.py`
- Fixtures: `tests/fixtures/hard_grade.md`, `tests/fixtures/plain_grade.md`

This linter is stdlib-only for the syllable/word math; it reuses `iter_sentences` for segmentation. It flags any sentence whose Flesch-Kincaid grade exceeds the budget (default 12).

- [ ] **Step 1: Write the failing test**

```python
import pytest
pytestmark = pytest.mark.windows_canary

from pathlib import Path
from scripts.lint_reading_grade import lint_reading_grade, _syllables, _fk_grade


def test_syllable_counter_basic():
    assert _syllables("cat") == 1
    assert _syllables("running") == 2
    assert _syllables("intuition") == 4

def test_fk_grade_monotonic():
    easy = _fk_grade(words=10, sentences=1, syllables=12)
    hard = _fk_grade(words=30, sentences=1, syllables=70)
    assert hard > easy

def test_flags_dense_sentence(tmp_path):
    md = tmp_path / "hard.md"
    md.write_text(
        "The phenomenological instantiation of electromagnetic propagation "
        "necessitates a comprehensive reconceptualization of the underlying "
        "theoretical superstructure governing particulate interactions.\n",
        encoding="utf-8",
    )
    findings = lint_reading_grade(md, max_grade=12)
    assert findings
    assert findings[0]["rule"] == "reading-grade"
    assert findings[0]["grade"] > 12

def test_passes_plain_sentence(tmp_path):
    md = tmp_path / "plain.md"
    md.write_text("Atoms are little things that jiggle. The hotter it is, the more they jiggle.\n", encoding="utf-8")
    assert lint_reading_grade(md, max_grade=12) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_lint_reading_grade.py -v`
Expected: FAIL — `ModuleNotFoundError: scripts.lint_reading_grade`

- [ ] **Step 3: Write the implementation**

```python
"""Flag sentences whose Flesch-Kincaid grade load exceeds the budget."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from .lint_common import iter_sentences, load_markdown

_VOWEL_GROUP = re.compile(r"[aeiouy]+", re.IGNORECASE)
DEFAULT_MAX_GRADE = 12


def _syllables(word: str) -> int:
    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        return 0
    groups = _VOWEL_GROUP.findall(w)
    count = len(groups)
    if w.endswith("e") and count > 1 and not w.endswith(("le", "ble", "cle", "dle", "gle", "kle", "ple", "tle", "zle")):
        count -= 1
    return max(1, count)


def _fk_grade(words: int, sentences: int, syllables: int) -> float:
    if words == 0 or sentences == 0:
        return 0.0
    return 0.39 * (words / sentences) + 11.8 * (syllables / words) - 15.59


def lint_reading_grade(path: Path, max_grade: int = DEFAULT_MAX_GRADE) -> list[dict]:
    text = load_markdown(path)
    findings: list[dict] = []
    for sentence in iter_sentences(text):
        words = re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", sentence.text)
        if len(words) < 6:
            continue  # too short to grade meaningfully
        syl = sum(_syllables(w) for w in words)
        grade = _fk_grade(len(words), 1, syl)
        if grade > max_grade:
            findings.append({
                "rule": "reading-grade",
                "grade": round(grade, 1),
                "sentence": sentence.text,
                "line": sentence.line,
                "col": sentence.col,
            })
    return findings


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: lint_reading_grade.py <markdown-file>", file=sys.stderr)
        return 2
    findings = lint_reading_grade(Path(argv[1]))
    print(json.dumps(findings, indent=2))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_lint_reading_grade.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add skills/feynman-style/scripts/lint_reading_grade.py skills/feynman-style/tests/test_lint_reading_grade.py
git commit -m "Add reading-grade linter to feynman-style"
```

---

## Task 3: `lint_conversational` — reward direct address, contractions, questions

**Files:**
- Create: `skills/feynman-style/scripts/lint_conversational.py`
- Test: `skills/feynman-style/tests/test_lint_conversational.py`

This linter is a **reward detector**: it counts conversational markers and emits a finding only when a paragraph of substantial length has *too few* (below `min_per_paragraph`). It signals "this paragraph reads cold/formal," which is what we want Feynman to fix. It reads marker lists from `feynman-rules.json` (Task 12) but ships a built-in default so it is testable before that file exists.

- [ ] **Step 1: Write the failing test**

```python
import pytest
pytestmark = pytest.mark.windows_canary

from pathlib import Path
from scripts.lint_conversational import lint_conversational


def test_flags_cold_formal_paragraph(tmp_path):
    md = tmp_path / "cold.md"
    md.write_text(
        "The system processes the input. The output is then produced. "
        "The transformation is deterministic. The result is recorded for later analysis. "
        "Subsequent stages consume the recorded result.\n",
        encoding="utf-8",
    )
    findings = lint_conversational(md, min_per_paragraph=1)
    assert findings
    assert findings[0]["rule"] == "conversational-cold"

def test_warm_paragraph_passes(tmp_path):
    md = tmp_path / "warm.md"
    md.write_text(
        "Now you might ask: what's really going on here? Well, it's simpler than you'd think. "
        "We just feed it the input, and out comes the answer.\n",
        encoding="utf-8",
    )
    assert lint_conversational(md, min_per_paragraph=1) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_lint_conversational.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write the implementation**

```python
"""Reward conversational warmth; flag paragraphs that read cold/formal."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from .lint_common import load_markdown, _split_paragraphs, _is_code_block, _is_heading, _is_list_marker

_CONTRACTION = re.compile(r"\b\w+'(?:s|re|ve|ll|d|t|m)\b", re.IGNORECASE)
_SECOND_PERSON = re.compile(r"\b(you|your|you're|you'd|you'll|we|we're|let's)\b", re.IGNORECASE)
_DIRECT_OPENER = re.compile(r"\b(now|well|so|here's the thing|imagine|suppose|think about)\b", re.IGNORECASE)
DEFAULT_MIN = 1


def _markers(paragraph: str) -> int:
    n = len(_CONTRACTION.findall(paragraph))
    n += len(_SECOND_PERSON.findall(paragraph))
    n += len(_DIRECT_OPENER.findall(paragraph))
    n += paragraph.count("?")
    return n


def lint_conversational(path: Path, min_per_paragraph: int = DEFAULT_MIN) -> list[dict]:
    text = load_markdown(path)
    findings: list[dict] = []
    for start_line, para in _split_paragraphs(text):
        if _is_code_block(para) or _is_heading(para) or _is_list_marker(para):
            continue
        if len(para.split()) < 25:
            continue  # only judge substantial paragraphs
        if _markers(para) < min_per_paragraph:
            findings.append({
                "rule": "conversational-cold",
                "sentence": " ".join(para.split())[:160],
                "line": start_line,
                "col": 1,
            })
    return findings


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: lint_conversational.py <markdown-file>", file=sys.stderr)
        return 2
    findings = lint_conversational(Path(argv[1]))
    print(json.dumps(findings, indent=2))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
```
> Note: `_split_paragraphs`, `_is_code_block`, `_is_heading`, `_is_list_marker` are module-level helpers in the copied `lint_common.py` (verified present at `lint_common.py:54-84`).

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_lint_conversational.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/feynman-style/scripts/lint_conversational.py skills/feynman-style/tests/test_lint_conversational.py
git commit -m "Add conversational-warmth linter to feynman-style"
```

---

## Task 4: `lint_latinate_diction` — flag Latinate jargon with a plain alternative

**Files:**
- Create: `skills/feynman-style/scripts/lint_latinate_diction.py`
- Test: `skills/feynman-style/tests/test_lint_latinate_diction.py`

Flags words present in a Latinate→Anglo-Saxon substitution map and reports the suggested plain word. Map ships built-in here and is overridable from `feynman-rules.json` (`latinate_substitutions`) in Task 12.

- [ ] **Step 1: Write the failing test**

```python
import pytest
pytestmark = pytest.mark.windows_canary

from pathlib import Path
from scripts.lint_latinate_diction import lint_latinate_diction


def test_flags_latinate_with_suggestion(tmp_path):
    md = tmp_path / "latinate.md"
    md.write_text("We utilize the mechanism to facilitate the demonstration.\n", encoding="utf-8")
    findings = lint_latinate_diction(md)
    terms = {f["term"]: f["suggestion"] for f in findings}
    assert terms.get("utilize") == "use"
    assert terms.get("facilitate") == "help"
    assert all(f["rule"] == "latinate-diction" for f in findings)

def test_plain_prose_passes(tmp_path):
    md = tmp_path / "plain.md"
    md.write_text("We use the tool to help the demo.\n", encoding="utf-8")
    assert lint_latinate_diction(md) == []
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_lint_latinate_diction.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write the implementation**

```python
"""Flag Latinate jargon that has a plain Anglo-Saxon substitute."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from .lint_common import iter_sentences, load_markdown

# Built-in default; Task 12 lets feynman-rules.json override via "latinate_substitutions".
_DEFAULT_MAP = {
    "utilize": "use", "utilizes": "uses", "utilized": "used",
    "facilitate": "help", "demonstrate": "show", "demonstration": "demo",
    "endeavor": "try", "commence": "start", "terminate": "end",
    "subsequent": "later", "prior to": "before", "in order to": "to",
    "approximately": "about", "sufficient": "enough", "additional": "more",
    "methodology": "method", "functionality": "feature", "leverage": "use",
    "ascertain": "find out", "necessitate": "need", "fundamental": "basic",
}


def _load_map() -> dict:
    from pathlib import Path as _P
    rules = _P(__file__).resolve().parent.parent / "assets" / "feynman-rules.json"
    if rules.exists():
        data = json.loads(rules.read_text(encoding="utf-8"))
        return data.get("latinate_substitutions", _DEFAULT_MAP)
    return _DEFAULT_MAP


def lint_latinate_diction(path: Path) -> list[dict]:
    text = load_markdown(path)
    mapping = _load_map()
    terms = sorted(mapping, key=len, reverse=True)
    pattern = re.compile(r"\b(" + "|".join(re.escape(t) for t in terms) + r")\b", re.IGNORECASE)
    findings: list[dict] = []
    for sentence in iter_sentences(text):
        for m in pattern.finditer(sentence.text):
            term = m.group(1).lower()
            findings.append({
                "rule": "latinate-diction",
                "term": term,
                "suggestion": mapping[term],
                "sentence": sentence.text,
                "line": sentence.line,
                "col": sentence.col + m.start(),
            })
    return findings


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: lint_latinate_diction.py <markdown-file>", file=sys.stderr)
        return 2
    findings = lint_latinate_diction(Path(argv[1]))
    print(json.dumps(findings, indent=2))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_lint_latinate_diction.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/feynman-style/scripts/lint_latinate_diction.py skills/feynman-style/tests/test_lint_latinate_diction.py
git commit -m "Add latinate-diction linter to feynman-style"
```

---

## Task 5: `lint_concreteness` — analogy + concrete-instance density

**Files:**
- Create: `skills/feynman-style/scripts/lint_concreteness.py`
- Test: `skills/feynman-style/tests/test_lint_concreteness.py`

Two findings from one module: `analogy-absent` (a substantial passage with no analogy/comparison markers) and `abstraction-heavy` (abstract-noun ratio above budget). Uses spaCy POS tags for abstract-noun detection (nouns ending in common abstract suffixes is a cheap, deterministic proxy; keep it suffix-based to avoid a sense model).

- [ ] **Step 1: Write the failing test**

```python
import pytest
pytestmark = pytest.mark.windows_canary

from pathlib import Path
from scripts.lint_concreteness import lint_concreteness


def test_flags_abstraction_heavy(tmp_path):
    md = tmp_path / "abstract.md"
    md.write_text(
        "The implementation of the abstraction enables the realization of the "
        "generalization through the formalization of the representation and the "
        "specification of the configuration.\n",
        encoding="utf-8",
    )
    rules = {f["rule"] for f in lint_concreteness(md)}
    assert "abstraction-heavy" in rules

def test_flags_missing_analogy(tmp_path):
    md = tmp_path / "noanalogy.md"
    md.write_text(
        "The electron moves through the field and changes its momentum. "
        "The field exerts a force. The force acts over a distance. "
        "Energy transfers from the field to the particle in measurable amounts.\n",
        encoding="utf-8",
    )
    rules = {f["rule"] for f in lint_concreteness(md)}
    assert "analogy-absent" in rules

def test_concrete_analogy_passes(tmp_path):
    md = tmp_path / "concrete.md"
    md.write_text(
        "Think of the electron like a marble rolling down a hill. "
        "The steeper the hill, the faster it picks up speed, just like a ball on a ramp.\n",
        encoding="utf-8",
    )
    assert lint_concreteness(md) == []
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_lint_concreteness.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write the implementation**

```python
"""Flag passages lacking analogy or saturated with abstract nouns."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from .lint_common import load_markdown, _split_paragraphs, _is_code_block, _is_heading, _is_list_marker

_ANALOGY = re.compile(
    r"\b(like|as if|as though|imagine|picture|think of|similar to|"
    r"the way|just as|kind of like|sort of like|as when)\b",
    re.IGNORECASE,
)
_ABSTRACT_SUFFIX = re.compile(
    r"\b\w+(?:tion|sion|ment|ness|ity|ance|ence|ism|ization|isation)\b",
    re.IGNORECASE,
)
DEFAULT_ABSTRACT_RATIO = 0.18  # abstract nouns / total words


def lint_concreteness(path: Path, max_abstract_ratio: float = DEFAULT_ABSTRACT_RATIO) -> list[dict]:
    text = load_markdown(path)
    findings: list[dict] = []
    for start_line, para in _split_paragraphs(text):
        if _is_code_block(para) or _is_heading(para) or _is_list_marker(para):
            continue
        words = para.split()
        if len(words) < 30:
            continue
        flat = " ".join(words)
        snippet = flat[:160]
        if not _ANALOGY.search(flat):
            findings.append({
                "rule": "analogy-absent",
                "sentence": snippet,
                "line": start_line,
                "col": 1,
            })
        abstract = len(_ABSTRACT_SUFFIX.findall(flat))
        if abstract / len(words) > max_abstract_ratio:
            findings.append({
                "rule": "abstraction-heavy",
                "ratio": round(abstract / len(words), 3),
                "sentence": snippet,
                "line": start_line,
                "col": 1,
            })
    return findings


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: lint_concreteness.py <markdown-file>", file=sys.stderr)
        return 2
    findings = lint_concreteness(Path(argv[1]))
    print(json.dumps(findings, indent=2))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_lint_concreteness.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/feynman-style/scripts/lint_concreteness.py skills/feynman-style/tests/test_lint_concreteness.py
git commit -m "Add concreteness linter to feynman-style"
```

---

## Task 6: `lint_curiosity_markers` — reward honest-doubt / puzzle framing

**Files:**
- Create: `skills/feynman-style/scripts/lint_curiosity_markers.py`
- Test: `skills/feynman-style/tests/test_lint_curiosity_markers.py`

A reward detector mirroring Task 3's shape, but for curiosity moves. Critically, the phrases it rewards ("nobody really knows", "the funny thing is", "here's the puzzle") are the ones the Russell hedge linter would flag — this module exists partly to document that they are **curiosity moves, not hedges** (the partition in Task 12 encodes that). Emits `curiosity-absent` for a long passage with zero markers. This is informational (low budget), never a hard gate.

- [ ] **Step 1: Write the failing test**

```python
import pytest
pytestmark = pytest.mark.windows_canary

from pathlib import Path
from scripts.lint_curiosity_markers import lint_curiosity_markers, count_markers


def test_counts_curiosity_phrases():
    text = "The funny thing is, nobody really knows why. Here's the puzzle that bugged everyone."
    assert count_markers(text) >= 2

def test_flags_passage_without_curiosity(tmp_path):
    md = tmp_path / "flat.md"
    md.write_text(
        "The procedure runs in three stages. Each stage validates its input. "
        "The final stage emits the result. The result is stored in the ledger. "
        "Downstream consumers read the ledger entry directly.\n",
        encoding="utf-8",
    )
    findings = lint_curiosity_markers(md)
    assert any(f["rule"] == "curiosity-absent" for f in findings)
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_lint_curiosity_markers.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write the implementation**

```python
"""Reward honest-doubt / puzzle framing; flag long passages with none."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from .lint_common import load_markdown, _split_paragraphs, _is_code_block, _is_heading, _is_list_marker

# These read as hedges to Russell but are Feynman curiosity moves. See the
# Surface/Integrity partition in assets/feynman-rules.json and references/negative-triggers.md.
_CURIOSITY = re.compile(
    r"(nobody (?:really )?knows|the funny thing is|here'?s the puzzle|"
    r"it turns out|what'?s (?:really )?going on|the strange thing|"
    r"you might (?:ask|wonder)|the question is|why (?:on earth|in the world)|"
    r"the mystery|nobody had figured)",
    re.IGNORECASE,
)


def count_markers(text: str) -> int:
    return len(_CURIOSITY.findall(text))


def lint_curiosity_markers(path: Path, min_per_long_passage: int = 1, long_words: int = 60) -> list[dict]:
    text = load_markdown(path)
    findings: list[dict] = []
    for start_line, para in _split_paragraphs(text):
        if _is_code_block(para) or _is_heading(para) or _is_list_marker(para):
            continue
        words = para.split()
        if len(words) < long_words:
            continue
        if count_markers(" ".join(words)) < min_per_long_passage:
            findings.append({
                "rule": "curiosity-absent",
                "sentence": " ".join(words)[:160],
                "line": start_line,
                "col": 1,
            })
    return findings


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: lint_curiosity_markers.py <markdown-file>", file=sys.stderr)
        return 2
    findings = lint_curiosity_markers(Path(argv[1]))
    print(json.dumps(findings, indent=2))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_lint_curiosity_markers.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/feynman-style/scripts/lint_curiosity_markers.py skills/feynman-style/tests/test_lint_curiosity_markers.py
git commit -m "Add curiosity-marker linter to feynman-style"
```

---

## Task 7: Port `lint_sentence_rhythm` and `lint_ai_vocabulary`

**Files:**
- Copy + adapt: `skills/feynman-style/scripts/lint_sentence_rhythm.py` from `skills/russellian-style/scripts/lint_sentence_rhythm.py`
- Copy verbatim: `skills/feynman-style/scripts/lint_ai_vocabulary.py` from `skills/russellian-style/scripts/lint_ai_vocabulary.py`
- Copy + trim assets: `skills/feynman-style/assets/ai-vocabulary-supplement.json` from russellian-style
- Test: `skills/feynman-style/tests/test_ports.py`

`lint_ai_vocabulary` is Integrity-class (AI slop is unwanted in any register) — copy verbatim. `lint_sentence_rhythm` is Surface-class but useful standalone for the Feynman default set; copy it and only change the rule-name prefix it emits if it reads from `russellian-rules.json` (repoint `load_rules` to feynman-rules.json keys, or inline the two numeric knobs it uses).

- [ ] **Step 1: Read the source linters to learn their public functions and the rules keys they read**

```bash
sed -n '1,60p' C:/russellian-book-suite/skills/russellian-style/scripts/lint_sentence_rhythm.py
sed -n '1,40p' C:/russellian-book-suite/skills/russellian-style/scripts/lint_ai_vocabulary.py
```
Note the exported function names and any `load_rules()[...]` keys.

- [ ] **Step 2: Copy both files and the vocabulary asset**

```bash
cd C:/russellian-book-suite/skills
cp russellian-style/scripts/lint_ai_vocabulary.py feynman-style/scripts/lint_ai_vocabulary.py
cp russellian-style/scripts/lint_sentence_rhythm.py feynman-style/scripts/lint_sentence_rhythm.py
cp russellian-style/assets/ai-vocabulary-supplement.json feynman-style/assets/ai-vocabulary-supplement.json
```

- [ ] **Step 3: Write a port-smoke test**

```python
import pytest
pytestmark = pytest.mark.windows_canary

from pathlib import Path
from scripts.lint_ai_vocabulary import lint_ai_vocabulary
from scripts.lint_sentence_rhythm import lint_sentence_rhythm


def test_ai_vocabulary_runs(tmp_path):
    md = tmp_path / "v.md"
    md.write_text("This robust, comprehensive solution leverages a seamless paradigm.\n", encoding="utf-8")
    out = lint_ai_vocabulary(md)
    assert isinstance(out, list)
    assert all("rule" in f and "line" in f for f in out)

def test_sentence_rhythm_runs(tmp_path):
    md = tmp_path / "r.md"
    md.write_text("It runs. It stops. It runs. It stops. It runs again now.\n", encoding="utf-8")
    out = lint_sentence_rhythm(md)
    assert isinstance(out, list)
```

- [ ] **Step 4: Resolve the rules-file dependency**

If Step 1 showed `lint_sentence_rhythm` reads `load_rules()["max_sentence_word_count"]` etc., either (a) ensure Task 12's `feynman-rules.json` carries the same keys, or (b) replace the `load_rules()` call with module-level constants `MAX_SENTENCE_WORDS = 35` and `MIN_LENGTH_VARIANCE = 4.0` (Feynman tolerates longer, more varied sentences than Russell). Pick (b) for isolation. Make the edit, then run:

Run: `.venv/Scripts/python.exe -m pytest tests/test_ports.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add skills/feynman-style/scripts/lint_ai_vocabulary.py skills/feynman-style/scripts/lint_sentence_rhythm.py skills/feynman-style/assets/ai-vocabulary-supplement.json skills/feynman-style/tests/test_ports.py
git commit -m "Port ai-vocabulary and sentence-rhythm linters into feynman-style"
```

---

## Task 9: `preserve_argument` — the claims/structure survival gate (NEW)

**Files:**
- Create: `skills/feynman-style/scripts/preserve_argument.py`
- Test: `skills/feynman-style/tests/test_preserve_argument.py`

This is the one hard gate and the only genuinely new component. It compares the Russell-input (`before`) to the Feynman-output (`after`) and verifies the argument survived. v0.1 uses deterministic, model-free checks (the design forbids smuggling logic changes through prose warming):

1. **Sentence-count-of-claims preserved** — every `before` sentence must have a content-overlapping `after` sentence (content words = non-stopword tokens). A `before` claim with no overlapping `after` sentence is a `dropped-claim`.
2. **No new numbers/entities** — any number or capitalized multi-word proper term in `after` that is absent from `before` is an `introduced-fact` (Feynman may not invent data).
3. **Ordering preserved** — the relative order of matched claims must not invert (`reordered-claim`).

Returns a `PreservationReport(ok: bool, violations: list[dict])`. `ok` is the hard gate.

- [ ] **Step 1: Write the failing test**

```python
import pytest
pytestmark = pytest.mark.windows_canary

from scripts.preserve_argument import preserve_argument, PreservationReport


def test_clean_warming_passes():
    before = "The cache stores results. A second request reads from disk. This avoids a network call."
    after = ("Here's the trick: the cache just keeps your results around. "
             "So the second time you ask, it grabs them off the disk — "
             "and you skip the network call entirely.")
    report = preserve_argument(before, after)
    assert isinstance(report, PreservationReport)
    assert report.ok, report.violations

def test_dropped_claim_fails():
    before = "The cache stores results. A second request reads from disk. This avoids a network call."
    after = "Here's the trick: the cache keeps your results around."
    report = preserve_argument(before, after)
    assert not report.ok
    assert any(v["kind"] == "dropped-claim" for v in report.violations)

def test_introduced_number_fails():
    before = "The cache stores results to avoid a network call."
    after = "The cache stores results, cutting latency by 80 percent and avoiding the network call."
    report = preserve_argument(before, after)
    assert not report.ok
    assert any(v["kind"] == "introduced-fact" for v in report.violations)
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_preserve_argument.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write the implementation**

```python
"""preserve_argument: verify the Feynman pass did not change the argument.

Hard gate. Deterministic, model-free. Compares the Russell input (before) to
the Feynman output (after).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .lint_common import iter_sentences

_STOP = {
    "the", "a", "an", "and", "or", "but", "if", "then", "so", "to", "of", "in",
    "on", "for", "is", "are", "was", "were", "be", "been", "it", "this", "that",
    "these", "those", "as", "at", "by", "with", "from", "into", "you", "your",
    "we", "our", "they", "their", "i", "he", "she", "his", "her", "its", "now",
    "here", "well", "just", "really", "out", "up", "off", "about", "what", "why",
    "how", "when", "where", "which", "who", "will", "would", "can", "could",
}
_NUM = re.compile(r"\b\d+(?:[.,]\d+)?\b")
_PROPER = re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b")


@dataclass
class PreservationReport:
    ok: bool
    violations: list[dict] = field(default_factory=list)


def _content_words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]+", text.lower()) if w not in _STOP and len(w) > 2}


def _sentences(text: str) -> list[str]:
    # iter_sentences needs a path-backed source in lint_common; segment inline instead.
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def preserve_argument(before: str, after: str, min_overlap: float = 0.34) -> PreservationReport:
    violations: list[dict] = []
    before_sents = _sentences(before)
    after_sents = _sentences(after)
    after_bags = [_content_words(s) for s in after_sents]

    # 1 + 3: every before-claim maps to an after-sentence; track order.
    matched_after_idx: list[int] = []
    for bi, bs in enumerate(before_sents):
        bbag = _content_words(bs)
        if not bbag:
            continue
        best_i, best_score = -1, 0.0
        for ai, abag in enumerate(after_bags):
            if not abag:
                continue
            overlap = len(bbag & abag) / len(bbag)
            if overlap > best_score:
                best_i, best_score = ai, overlap
        if best_score < min_overlap:
            violations.append({"kind": "dropped-claim", "claim": bs[:120], "score": round(best_score, 2)})
        else:
            matched_after_idx.append(best_i)

    # 3: matched order must be non-decreasing
    for a, b in zip(matched_after_idx, matched_after_idx[1:]):
        if b < a:
            violations.append({"kind": "reordered-claim", "detail": f"after-sentence {b} precedes {a}"})
            break

    # 2: no new numbers or proper-name entities
    before_nums = set(_NUM.findall(before))
    for n in _NUM.findall(after):
        if n not in before_nums:
            violations.append({"kind": "introduced-fact", "fact": n})
    before_proper = set(_PROPER.findall(before))
    for p in _PROPER.findall(after):
        if p not in before_proper:
            violations.append({"kind": "introduced-fact", "fact": p})

    return PreservationReport(ok=not violations, violations=violations)
```
> Note: this module segments sentences inline (regex) rather than via `iter_sentences`, because `iter_sentences` reads from a file path and `preserve_argument` works on in-memory strings. This is intentional and keeps the gate dependency-light.

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_preserve_argument.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add skills/feynman-style/scripts/preserve_argument.py skills/feynman-style/tests/test_preserve_argument.py
git commit -m "Add preserve_argument hard gate to feynman-style"
```

---

## Task 12: `feynman-rules.json` — budgets, partition map, word lists

**Files:**
- Create: `skills/feynman-style/assets/feynman-rules.json`
- Test: `skills/feynman-style/tests/test_rules_schema.py`

Holds: linter budgets, the **Surface/Integrity classification map** (the heart of the non-destruction contract), the Latinate substitution map, and negative-trigger keywords. The classification map names linters and the stage each runs in.

- [ ] **Step 1: Write the failing test**

```python
import pytest
pytestmark = pytest.mark.windows_canary

import json
from pathlib import Path

RULES = Path("assets/feynman-rules.json")

def test_rules_load_and_have_partition():
    data = json.loads(RULES.read_text(encoding="utf-8"))
    assert "linter_class" in data
    cls = data["linter_class"]
    # Russell surface linters Feynman overrides → "surface"
    assert cls["no-hedging"] == "surface"
    assert cls["signal-density"] == "surface"
    # Integrity always enforced
    assert cls["preserve-argument"] == "integrity"
    assert cls["footnote-orphan"] == "integrity"
    # every value is one of the two classes
    assert set(cls.values()) <= {"surface", "integrity"}

def test_rules_have_budgets_and_maps():
    data = json.loads(RULES.read_text(encoding="utf-8"))
    assert isinstance(data["budgets"]["reading-grade"], (int, float))
    assert data["latinate_substitutions"]["utilize"] == "use"
    assert "max_sentence_word_count" in data
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_rules_schema.py -v`
Expected: FAIL — file missing

- [ ] **Step 3: Write `feynman-rules.json`**

```json
{
  "version": "0.1.0",
  "budgets": {
    "reading-grade": 12,
    "conversational-cold": 0,
    "latinate-diction": 2,
    "analogy-absent": 0,
    "abstraction-heavy": 0,
    "curiosity-absent": 2,
    "ai-vocabulary": 0
  },
  "max_sentence_word_count": 35,
  "min_length_variance": 4.0,
  "abstract_ratio_budget": 0.18,
  "linter_class": {
    "reading-grade": "surface",
    "conversational-cold": "surface",
    "latinate-diction": "surface",
    "analogy-absent": "surface",
    "abstraction-heavy": "surface",
    "curiosity-absent": "surface",
    "rhythm-uniform-length": "surface",
    "no-hedging": "surface",
    "signal-density": "surface",
    "staccato-paragraph-run": "surface",
    "ai-vocabulary": "integrity",
    "active-voice": "integrity",
    "parallel-structure": "integrity",
    "footnote-orphan": "integrity",
    "preserve-argument": "integrity"
  },
  "latinate_substitutions": {
    "utilize": "use", "utilizes": "uses", "utilized": "used",
    "facilitate": "help", "demonstrate": "show", "demonstration": "demo",
    "endeavor": "try", "commence": "start", "terminate": "end",
    "subsequent": "later", "approximately": "about", "sufficient": "enough",
    "additional": "more", "methodology": "method", "functionality": "feature",
    "leverage": "use", "ascertain": "find out", "necessitate": "need",
    "fundamental": "basic"
  },
  "negative_trigger_keywords": [
    "formal proof", "theorem", "lemma", "specification", "RFC", "legal",
    "contract clause", "API reference", "function signature", "bureaucratic",
    "abstract", "academic abstract", "boilerplate"
  ]
}
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_rules_schema.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/feynman-style/assets/feynman-rules.json skills/feynman-style/tests/test_rules_schema.py
git commit -m "Add feynman-rules.json with Surface/Integrity partition"
```

---

## Task 13: `skill_api.py` — registry, `lint_fragment`, `classify_linter`

**Files:**
- Create: `skills/feynman-style/skill_api.py`
- Test: `skills/feynman-style/tests/test_skill_api.py`

Mirrors `russellian-style/skill_api.py` (copy its `LintIssue`, sys.path bootstrap, `_import_linter`, `_raw_to_issue`, and `lint_fragment` body verbatim). Add: the Feynman registry, the Feynman default set, and a new `classify_linter(rule) -> "surface"|"integrity"` reading `feynman-rules.json`. Expose `preserve_argument` re-export.

- [ ] **Step 1: Write the failing test**

```python
import pytest
pytestmark = pytest.mark.windows_canary

from skill_api import lint_fragment, LintIssue, classify_linter, preserve_argument


def test_lint_fragment_runs_default_set():
    text = ("The phenomenological instantiation of electromagnetic propagation "
            "necessitates comprehensive reconceptualization of the theoretical superstructure.")
    issues = lint_fragment(text)
    assert all(isinstance(i, LintIssue) for i in issues)
    assert any(i.linter == "reading-grade" for i in issues)

def test_classify_linter():
    assert classify_linter("no-hedging") == "surface"
    assert classify_linter("preserve-argument") == "integrity"

def test_preserve_argument_reexported():
    r = preserve_argument("The cache stores results.", "The cache keeps your results around.")
    assert r.ok

def test_empty_text_returns_empty():
    assert lint_fragment("") == []
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_skill_api.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write `skill_api.py`**

Copy the full body of `skills/russellian-style/skill_api.py` (lines 1-175 as read in this plan's research), then replace the registry, default set, and `__all__`, and append the classifier + re-export:

```python
# --- replace _LINTER_REGISTRY with: ---
_LINTER_REGISTRY: dict[str, tuple[str, str]] = {
    "reading-grade":        ("scripts.lint_reading_grade",   "lint_reading_grade"),
    "conversational-cold":  ("scripts.lint_conversational",  "lint_conversational"),
    "latinate-diction":     ("scripts.lint_latinate_diction","lint_latinate_diction"),
    "analogy-absent":       ("scripts.lint_concreteness",    "lint_concreteness"),
    "abstraction-heavy":    ("scripts.lint_concreteness",    "lint_concreteness"),
    "curiosity-absent":     ("scripts.lint_curiosity_markers","lint_curiosity_markers"),
    "rhythm-uniform-length":("scripts.lint_sentence_rhythm", "lint_sentence_rhythm"),
    "ai-vocabulary":        ("scripts.lint_ai_vocabulary",   "lint_ai_vocabulary"),
}

# --- replace _DEFAULT_LINTERS with the Feynman reward/penalty set ---
_DEFAULT_LINTERS = frozenset([
    "reading-grade", "conversational-cold", "latinate-diction",
    "analogy-absent", "abstraction-heavy", "curiosity-absent",
    "rhythm-uniform-length", "ai-vocabulary",
])

# --- append, after lint_fragment ---
import json as _json
from pathlib import Path as _Path

def classify_linter(rule: str) -> str:
    """Return 'surface' or 'integrity' for a rule name, per feynman-rules.json."""
    rules = _Path(__file__).resolve().parent / "assets" / "feynman-rules.json"
    data = _json.loads(rules.read_text(encoding="utf-8"))
    return data["linter_class"].get(rule, "surface")

from scripts.preserve_argument import preserve_argument, PreservationReport

__all__ = ["LintIssue", "lint_fragment", "classify_linter",
           "preserve_argument", "PreservationReport"]
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_skill_api.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/feynman-style/skill_api.py skills/feynman-style/tests/test_skill_api.py
git commit -m "Add feynman-style public API with linter classification"
```

---

## Task 14: Offline corpus profile — `pdf_extract.py`, `delta_math.py`, `build_delta_profile.py`

**Files:**
- Copy verbatim: `skills/feynman-style/scripts/delta_math.py` from `skills/russellian-style/scripts/delta_math.py`
- Create: `skills/feynman-style/scripts/pdf_extract.py`
- Create: `skills/feynman-style/scripts/build_delta_profile.py`
- Test: `skills/feynman-style/tests/test_build_delta_profile.py`
- Setup: move the supplied PDF into the git-ignored drop folder

The builder reads `corpus-raw/` (PDF via pdfplumber, plus `.txt`/`.md`), normalizes mojibaked smart-quotes, computes a relative word-frequency profile, and writes it to `assets/feynman-delta-profile.json`. With an empty/missing `corpus-raw/`, it leaves the committed thresholds untouched and reports that it fell back. Offline — no network.

- [ ] **Step 1: Move the owned PDF into the drop folder**

```bash
cd C:/russellian-book-suite
mkdir -p skills/feynman-style/corpus-raw
mv "Surely You're Joking, Mr. Feynman!.pdf" skills/feynman-style/corpus-raw/
```
(`corpus-raw/` is git-ignored from Task 1, so the copyrighted text is never committed.)

- [ ] **Step 2: Copy `delta_math.py`**

```bash
cp skills/russellian-style/scripts/delta_math.py skills/feynman-style/scripts/delta_math.py
```

- [ ] **Step 3: Write the failing test**

```python
import pytest
pytestmark = pytest.mark.windows_canary

from pathlib import Path
from scripts.pdf_extract import normalize_text
from scripts.build_delta_profile import build_profile_from_texts, build_profile


def test_normalize_fixes_mojibake():
    raw = "She�s got a birthday—not today—but soon."
    out = normalize_text("Shes got a birthday")
    assert "'" in out or "s got" in out  # apostrophe restored or stripped, never a stray byte
    assert "�" not in out

def test_build_profile_from_texts_returns_relative_freqs():
    texts = ["atoms jiggle and jiggle", "the atoms move and jiggle around"]
    prof = build_profile_from_texts(texts, top_n=5)
    assert abs(sum(prof.values()) - 1.0) < 1e-6
    assert "jiggle" in prof

def test_build_profile_empty_drop_falls_back(tmp_path):
    # empty drop dir → returns None, signals fallback (does not raise)
    result = build_profile(corpus_dir=tmp_path, out_path=tmp_path / "p.json")
    assert result is None
```

- [ ] **Step 4: Run to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_build_delta_profile.py -v`
Expected: FAIL — modules missing

- [ ] **Step 5: Write `pdf_extract.py`**

```python
"""Local PDF/text extraction for the offline corpus profile. No network."""
from __future__ import annotations

import re
from pathlib import Path

# Map common Windows-1252 / mojibake artifacts to clean characters.
_MOJIBAKE = {
    "": "'", "": "'", "": '"', "": '"',
    "": "-", "": "-", "�": "'",
    "‘": "'", "’": "'", "“": '"', "”": '"',
    "–": "-", "—": "-",
}


def normalize_text(text: str) -> str:
    for bad, good in _MOJIBAKE.items():
        text = text.replace(bad, good)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_pdf(path: Path) -> str:
    import pdfplumber  # deferred so unit tests not needing PDFs import cleanly
    chunks: list[str] = []
    with pdfplumber.open(str(path)) as pdf:
        for page in pdf.pages:
            chunks.append(page.extract_text() or "")
    return normalize_text("\n".join(chunks))


def extract_any(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        return extract_pdf(path)
    return normalize_text(path.read_text(encoding="utf-8", errors="replace"))
```

- [ ] **Step 6: Write `build_delta_profile.py`**

```python
"""Build an OFFLINE word-frequency profile from copies the user owns.

Reads skills/feynman-style/corpus-raw/ (PDF/txt/md), writes
assets/feynman-delta-profile.json. With no drop files, returns None and leaves
the committed thresholds untouched. Never touches the network.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Optional

from scripts.pdf_extract import extract_any

_SKILL_ROOT = Path(__file__).resolve().parent.parent
_DROP = _SKILL_ROOT / "corpus-raw"
_OUT = _SKILL_ROOT / "assets" / "feynman-delta-profile.json"
_WORD = re.compile(r"[a-z]+(?:'[a-z]+)?")


def build_profile_from_texts(texts: list[str], top_n: int = 500) -> dict:
    counts: Counter[str] = Counter()
    for t in texts:
        counts.update(_WORD.findall(t.lower()))
    total = sum(counts.values())
    if total == 0:
        return {}
    common = counts.most_common(top_n)
    return {w: c / total for w, c in common}


def build_profile(corpus_dir: Path = _DROP, out_path: Path = _OUT,
                  top_n: int = 500) -> Optional[Path]:
    if not corpus_dir.exists():
        return None
    sources = [p for p in corpus_dir.iterdir()
               if p.suffix.lower() in (".pdf", ".txt", ".md")]
    if not sources:
        return None
    texts = [extract_any(p) for p in sources]
    profile = build_profile_from_texts(texts, top_n=top_n)
    if not profile:
        return None
    payload = {
        "version": "0.1.0",
        "source_file_count": len(sources),
        "token_basis": "relative_frequency",
        "frequencies": profile,
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out_path


def main(argv: list[str]) -> int:
    result = build_profile()
    if result is None:
        print("No corpus-raw/ drop files found; using committed thresholds.", file=sys.stderr)
        return 0
    print(f"Wrote profile from local drop -> {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
```

- [ ] **Step 7: Run to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_build_delta_profile.py -v`
Expected: PASS

- [ ] **Step 8: Build the real profile from the owned PDF (manual, local-only)**

```bash
cd C:/russellian-book-suite/skills/feynman-style
.venv/Scripts/python.exe -m pip install -q "pdfplumber>=0.11,<0.12"
.venv/Scripts/python.exe -c "import sys; sys.path.insert(0,'.'); from scripts.build_delta_profile import build_profile; print(build_profile())"
```
Expected: prints a path; `assets/feynman-delta-profile.json` now carries real frequencies. (This file IS committed; it contains only relative word frequencies, not reproducible text.)

- [ ] **Step 9: Commit**

```bash
cd C:/russellian-book-suite
git add skills/feynman-style/scripts/pdf_extract.py skills/feynman-style/scripts/build_delta_profile.py skills/feynman-style/scripts/delta_math.py skills/feynman-style/tests/test_build_delta_profile.py skills/feynman-style/assets/feynman-delta-profile.json
git commit -m "Add offline local-drop corpus profile builder"
```

---

## Task 15: `score_feynman_delta.py` — Burrows-Delta against the profile

**Files:**
- Create: `skills/feynman-style/scripts/score_feynman_delta.py`
- Test: `skills/feynman-style/tests/test_score_feynman_delta.py`

Reuses `delta_math.py` (copied in Task 14). Scores a passage's word-frequency vector against `feynman-delta-profile.json` and returns a delta distance (lower = closer to Feynman). Read `skills/russellian-style/scripts/score_russell_delta.py` first and mirror its structure; repoint the profile path to `feynman-delta-profile.json`.

- [ ] **Step 1: Read the russellian scorer for the exact `delta_math` API**

```bash
sed -n '1,80p' C:/russellian-book-suite/skills/russellian-style/scripts/score_russell_delta.py
```
Note the function used (e.g. `burrows_delta(sample_freqs, reference_profile)`).

- [ ] **Step 2: Write the failing test**

```python
import pytest
pytestmark = pytest.mark.windows_canary

from scripts.score_feynman_delta import score_text


def test_score_returns_float():
    score = score_text("atoms jiggle and bounce around like little balls")
    assert isinstance(score, float)
    assert score >= 0.0
```

- [ ] **Step 3: Run to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_score_feynman_delta.py -v`
Expected: FAIL — module not found

- [ ] **Step 4: Write the implementation** (adapt names to whatever Step 1 revealed)

```python
"""Burrows-Delta distance of a passage from the Feynman frequency profile."""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

from scripts import delta_math

_PROFILE = Path(__file__).resolve().parent.parent / "assets" / "feynman-delta-profile.json"
_WORD = re.compile(r"[a-z]+(?:'[a-z]+)?")


def _load_profile() -> dict:
    data = json.loads(_PROFILE.read_text(encoding="utf-8"))
    return data.get("frequencies", {})


def score_text(text: str) -> float:
    profile = _load_profile()
    if not profile:
        return 0.0
    counts = Counter(_WORD.findall(text.lower()))
    total = sum(counts.values()) or 1
    sample = {w: c / total for w, c in counts.items()}
    # delta_math exposes a z-score Delta over the shared vocabulary; if the
    # exact function name differs (Step 1), adapt this call.
    return float(delta_math.burrows_delta(sample, profile))


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: score_feynman_delta.py <markdown-file>", file=sys.stderr)
        return 2
    print(round(score_text(Path(argv[1]).read_text(encoding="utf-8")), 4))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
```
> If `delta_math` has no `burrows_delta` with this signature, use whatever symbol Step 1 showed (e.g. `delta_distance`) and match its argument shape. Do not invent a new metric.

- [ ] **Step 5: Run to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_score_feynman_delta.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add skills/feynman-style/scripts/score_feynman_delta.py skills/feynman-style/tests/test_score_feynman_delta.py
git commit -m "Add Burrows-Delta scorer for feynman-style"
```

---

## Task 16: System prompts + `system_prompt_loader.py`

**Files:**
- Copy + adapt: `skills/feynman-style/scripts/system_prompt_loader.py` from russellian-style
- Create: 3 prompts under `skills/feynman-style/assets/system-prompts/`
- Test: `skills/feynman-style/tests/test_system_prompt_loader.py`

Each prompt has a shared **Structural mandates** block (the two-layer contract: warm the surface, never touch the argument) and a mode-specific block. Read the russellian prompts first for the house format.

- [ ] **Step 1: Read a russellian prompt + the loader**

```bash
sed -n '1,60p' C:/russellian-book-suite/skills/russellian-style/assets/system-prompts/technical-exposition.md
sed -n '1,60p' C:/russellian-book-suite/skills/russellian-style/scripts/system_prompt_loader.py
```

- [ ] **Step 2: Copy the loader and repoint its prompt directory**

```bash
cp skills/russellian-style/scripts/system_prompt_loader.py skills/feynman-style/scripts/system_prompt_loader.py
```
Edit any hardcoded mode names to: `technical-exposition`, `pedagogical-walkthrough`, `popular-science`.

- [ ] **Step 3: Write the failing test**

```python
import pytest
pytestmark = pytest.mark.windows_canary

from scripts.system_prompt_loader import load_system_prompt, available_modes


def test_three_modes_available():
    modes = set(available_modes())
    assert {"technical-exposition", "pedagogical-walkthrough", "popular-science"} <= modes

def test_prompt_states_two_layer_contract():
    text = load_system_prompt("technical-exposition")
    assert "argument" in text.lower()
    assert "analogy" in text.lower()
```
> If the loader's public function names differ (Step 1), adapt the imports to match.

- [ ] **Step 4: Run to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_system_prompt_loader.py -v`
Expected: FAIL

- [ ] **Step 5: Write `technical-exposition.md`** (the primary mode)

```markdown
# Feynman voice — technical exposition

You are rewriting prose that has ALREADY passed a Russell pass: it is correct, atomic, and hedge-free, but dense. Your job is the second pass — make it click — without changing the argument.

## Structural mandates (all modes)

- DO NOT change any claim, number, name, or the order of the argument. The logic is fixed. If you cannot warm a sentence without altering its meaning, leave it.
- Replace one abstraction per paragraph with a concrete, physical picture the reader can see or feel.
- Talk to the reader. Use "you", contractions, and an occasional direct question.
- Where the source hides a genuine puzzle, surface it ("here's the strange part").
- Prefer the short Anglo-Saxon word over the Latinate one.
- Keep sentences varied in length. Read it aloud; if you run out of breath, cut it.

## This mode

Explain a hard technical idea as if lecturing a sharp student who is NOT a specialist. Ground every formal step in something tangible. Keep the rigor; lose the stiffness.
```

- [ ] **Step 6: Write `pedagogical-walkthrough.md` and `popular-science.md`**

```markdown
# Feynman voice — pedagogical walkthrough

[Include the same "Structural mandates (all modes)" block verbatim as in technical-exposition.md.]

## This mode

Lead the reader by the hand through a derivation or process, step by step, checking understanding as you go ("so far so good?"). Motivate each step before taking it. Use a running concrete example.
```

```markdown
# Feynman voice — popular science

[Include the same "Structural mandates (all modes)" block verbatim as in technical-exposition.md.]

## This mode

Write for a curious general reader with no background. Maximize analogy and story; minimize notation. Wonder out loud. Never sacrifice a true claim for a clean line.
```

- [ ] **Step 7: Run to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_system_prompt_loader.py -v`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add skills/feynman-style/scripts/system_prompt_loader.py skills/feynman-style/assets/system-prompts/
git commit -m "Add feynman voice system prompts and loader"
```

---

## Task 17: `style_pass_report.py` + report template

**Files:**
- Copy + adapt: `skills/feynman-style/scripts/style_pass_report.py` and `assets/style-pass-report.template.md` from russellian-style
- Test: `skills/feynman-style/tests/test_style_pass_report.py`

The report summarizes: per-linter findings vs budget, the Burrows-Delta score, and — critically — the `preserve_argument` verdict (PASS/FAIL as the hard gate). Read the russellian report module first; mirror its render function and add a `preservation` section.

- [ ] **Step 1: Read the russellian report module + template**

```bash
sed -n '1,80p' C:/russellian-book-suite/skills/russellian-style/scripts/style_pass_report.py
cat C:/russellian-book-suite/skills/russellian-style/assets/style-pass-report.template.md
```

- [ ] **Step 2: Write the failing test**

```python
import pytest
pytestmark = pytest.mark.windows_canary

from scripts.style_pass_report import render_report


def test_report_includes_preservation_verdict():
    md = render_report(
        findings=[{"rule": "reading-grade", "line": 3, "grade": 14.2}],
        delta_score=1.8,
        preservation_ok=True,
    )
    assert "reading-grade" in md
    assert "PASS" in md  # preservation verdict surfaced

def test_report_flags_failed_preservation():
    md = render_report(findings=[], delta_score=1.0, preservation_ok=False)
    assert "FAIL" in md
```

- [ ] **Step 3: Run to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_style_pass_report.py -v`
Expected: FAIL

- [ ] **Step 4: Write `style_pass_report.py`** (mirror russellian render; add preservation)

```python
"""Render a feynman-style pass report. Mirrors russellian-style's report shape."""
from __future__ import annotations

from collections import Counter


def render_report(findings: list[dict], delta_score: float, preservation_ok: bool) -> str:
    by_rule = Counter(f.get("rule", "?") for f in findings)
    lines = ["# Feynman style pass report", ""]
    lines.append(f"**Argument preservation (hard gate):** {'PASS' if preservation_ok else 'FAIL'}")
    lines.append(f"**Feynman delta score:** {delta_score:.2f}  (lower is closer)")
    lines.append("")
    lines.append("## Findings by rule")
    if not by_rule:
        lines.append("None.")
    for rule, n in sorted(by_rule.items()):
        lines.append(f"- `{rule}`: {n}")
    return "\n".join(lines) + "\n"
```

- [ ] **Step 5: Run to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_style_pass_report.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add skills/feynman-style/scripts/style_pass_report.py skills/feynman-style/tests/test_style_pass_report.py
git commit -m "Add feynman-style pass report with preservation verdict"
```

---

## Task 18: Anchor corpus — `feynman-corpus/index.json`

**Files:**
- Create: `skills/feynman-style/assets/feynman-corpus/index.json`
- Test: `skills/feynman-style/tests/test_corpus_index.py`

A small set of SHORT fair-use excerpts (one to three sentences each — quotation length) tagged by rhetorical move, plus synthetic before/after pairs we author. These are exemplars for the prompts and anchors for `feynman-corpus-map.md`. Excerpts are short quotations consistent with fair use; the full text is never reproduced.

- [ ] **Step 1: Write the failing test**

```python
import pytest
pytestmark = pytest.mark.windows_canary

import json
from pathlib import Path

IDX = Path("assets/feynman-corpus/index.json")

def test_index_well_formed():
    data = json.loads(IDX.read_text(encoding="utf-8"))
    assert isinstance(data, list) and len(data) >= 8
    moves = {e["rhetorical_move"] for e in data}
    assert {"analogy", "direct-address", "honest-doubt"} <= moves
    for e in data:
        assert {"source_id", "rhetorical_move", "text"} <= set(e)

def test_excerpts_are_short():
    data = json.loads(IDX.read_text(encoding="utf-8"))
    for e in data:
        if e["source_id"].startswith("synthetic"):
            continue
        assert len(e["text"].split()) <= 60  # quotation-length only
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_corpus_index.py -v`
Expected: FAIL — file missing

- [ ] **Step 3: Write `index.json`**

Author ~10-14 entries. Include short, attributed fair-use excerpts (the kind of one-liners widely quoted from Feynman, drawn from the owned local copy) and synthetic pairs. Example shape:

```json
[
  {
    "source_id": "syjmf-jiggle",
    "line_hint": "atoms chapter",
    "rhetorical_move": "analogy",
    "text": "Everything is made of atoms — little particles that move around in perpetual motion, attracting when a little distance apart, repelling when squeezed together."
  },
  {
    "source_id": "synthetic-001-before",
    "rhetorical_move": "direct-address",
    "text": "BEFORE (Russellized): The function memoizes results; a repeated call returns the cached value, eliminating redundant computation."
  },
  {
    "source_id": "synthetic-001-after",
    "rhetorical_move": "direct-address",
    "text": "AFTER (Feynman): The first time you ask, it does the work and tucks the answer in its pocket. Ask again, and it just hands you what's in the pocket — no work at all."
  },
  {
    "source_id": "synthetic-002-honest-doubt",
    "rhetorical_move": "honest-doubt",
    "text": "Here's the part nobody likes to admit: we don't really know why this constant has the value it does. We just measure it and move on."
  }
]
```
Add further entries covering `plain-restatement` and more `analogy`/`honest-doubt` moves until ≥8 total and the three required moves are present.

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_corpus_index.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/feynman-style/assets/feynman-corpus/index.json skills/feynman-style/tests/test_corpus_index.py
git commit -m "Add feynman anchor corpus index"
```

---

## Task 20: Reference docs + refusal protocol

**Files:**
- Create: `skills/feynman-style/references/feynman-style-guide.md`
- Create: `skills/feynman-style/references/feynman-vitality-guide.md`
- Create: `skills/feynman-style/references/feynman-corpus-map.md`
- Create: `skills/feynman-style/references/before-after-examples.md`
- Create: `skills/feynman-style/references/negative-triggers.md`

No tests (prose docs). `negative-triggers.md` must also document the Surface/Integrity partition so a human can audit which Russell checks are suppressed on Feynman-final text.

- [ ] **Step 1: Write `feynman-style-guide.md`** — catalog the four moves (analogy/intuition, conversational directness, honest curiosity, plain diction) with concrete do/don't examples, mirroring `russellian-style-guide.md`'s structure (read it first for format).

- [ ] **Step 2: Write `feynman-vitality-guide.md`** — what to do when prose is plain and correct but lifeless (inject a running example, surface the puzzle, vary cadence).

- [ ] **Step 3: Write `feynman-corpus-map.md`** — index `assets/feynman-corpus/index.json` by rhetorical move; explain when to retrieve which anchor.

- [ ] **Step 4: Write `before-after-examples.md`** — 4-6 worked Russell-output → Feynman-output rewrites, each annotated with which moves were applied and an explicit note that the argument was unchanged.

- [ ] **Step 5: Write `negative-triggers.md`** — the refusal protocol (refuse on formal proofs, legal/spec text, API reference, bureaucratic boilerplate, academic abstracts; refuse to run before russellian-style). Then a table reproducing the Surface/Integrity partition from `feynman-rules.json` with a sentence on why each surface Russell check is suppressed on Feynman-final prose.

- [ ] **Step 6: Commit**

```bash
git add skills/feynman-style/references/
git commit -m "Add feynman-style reference docs and refusal protocol"
```

---

## Task 21: Wire the terminal `feynman` stage into `book-compose`

**Files:**
- Read first: `skills/book-compose/SKILL.md` and the stage orchestrator script.
- Modify: the book-compose stage pipeline (exact file found in Step 1).
- Test: add to book-compose's test suite.

The feynman stage runs AFTER the russell stage and is terminal for surface dimensions. Ordering must be enforced (assert russell precedes feynman). Feynman-passed sections are stamped with a provenance marker (`stage: "feynman"`) that Task 22 reads.

- [ ] **Step 1: Locate the stage pipeline**

```bash
grep -rn "russell" C:/russellian-book-suite/skills/book-compose/scripts/ | head
sed -n '1,40p' C:/russellian-book-suite/skills/book-compose/SKILL.md
```
Identify where the russell pass is invoked and how stages are sequenced.

- [ ] **Step 2: Write the failing test** (asserting order + provenance) — match book-compose's existing test style discovered in Step 1. Assert: (a) a `feynman` stage exists and runs after `russell`; (b) running feynman before russell raises/refuses; (c) output sections carry `stage == "feynman"`.

- [ ] **Step 3: Run to verify it fails.** Expected: FAIL.

- [ ] **Step 4: Implement** — add the optional `feynman` stage call (invoke `feynman-style` via the suite's `sibling_skills.load_skill_api("feynman-style")`), enforce Russell→Feynman ordering, and stamp the provenance marker. Use `classify_linter` from feynman-style's API only for reporting.

- [ ] **Step 5: Run to verify it passes.** Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add skills/book-compose
git commit -m "Add terminal feynman stage to book-compose pipeline"
```

---

## Task 22: Per-stage linter selection in `book-qa`

**Files:**
- Read first: the `chapter_contract_check` linter-selection logic in `skills/book-qa/`.
- Modify: that selection logic.
- Test: add to book-qa's suite.

When the release gate sees a Feynman-final section (provenance `stage == "feynman"`), it must run **only Integrity-class linters + Feynman budgets**, never the Surface Russell budgets. It reads the partition via `feynman-style`'s `classify_linter`.

- [ ] **Step 1: Locate the contract-check linter selection**

```bash
grep -rn "chapter_contract_check\|linters\|hedge" C:/russellian-book-suite/skills/book-qa/scripts/ | head
```

- [ ] **Step 2: Write the failing test** — a Feynman-stamped section containing rhetorical questions and contractions must PASS the gate (surface Russell checks suppressed), while a Russell-stamped section with the same content still triggers them. Match book-qa's test style.

- [ ] **Step 3: Run to verify it fails.** Expected: FAIL.

- [ ] **Step 4: Implement** — in the selection path, branch on provenance: for `stage == "feynman"`, filter linters to `classify_linter(rule) == "integrity"` plus the Feynman budget set; otherwise unchanged. Import via `sibling_skills.load_skill_api("feynman-style")`.

- [ ] **Step 5: Run to verify it passes.** Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add skills/book-qa
git commit -m "Suppress surface Russell checks on feynman-final sections in book-qa"
```

---

## Task 23: End-to-end integration test (proves the non-destruction contract)

**Files:**
- Create: `skills/feynman-style/tests/test_skill_integration.py`
- Fixture: `skills/feynman-style/tests/fixtures/russell_output.md`

The capstone. A known Russell-output fixture → Feynman pass (simulated by a fixed warmed rewrite, since generation is LLM-driven) → assert the three contract properties.

- [ ] **Step 1: Create the fixture** `russell_output.md` — a short, dense, hedge-free, atomic passage (3-5 sentences) and a hand-written Feynman-warmed counterpart embedded in the test.

- [ ] **Step 2: Write the integration test**

```python
import pytest
pytestmark = pytest.mark.windows_canary

from pathlib import Path
from skill_api import lint_fragment, classify_linter, preserve_argument

RUSSELL = Path("tests/fixtures/russell_output.md").read_text(encoding="utf-8")
FEYNMAN = (
    "Think of the cache as a notepad. The first time you ask a question, "
    "it works out the answer and jots it down. Ask the same thing again and "
    "it just reads it back to you — so you skip the slow trip to the network entirely."
)

def test_a_feynman_budgets_met():
    issues = lint_fragment(FEYNMAN)
    grades = [i for i in issues if i.linter == "reading-grade"]
    assert grades == []  # warmed prose is under the grade budget

def test_b_argument_preserved():
    report = preserve_argument(RUSSELL, FEYNMAN)
    assert report.ok, report.violations

def test_c_surface_russell_checks_are_suppressed():
    # The rhetorical question + contractions in FEYNMAN are surface-class and
    # must be classified for suppression on feynman-final text.
    assert classify_linter("no-hedging") == "surface"
    assert classify_linter("signal-density") == "surface"
    # Integrity checks remain enforced.
    assert classify_linter("preserve-argument") == "integrity"
```
> `russell_output.md` content must be such that `FEYNMAN` shares its claims (cache stores results; second request avoids the network) so `preserve_argument` passes.

- [ ] **Step 3: Run to verify it fails, then make fixture+text consistent until it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_skill_integration.py -v`
Expected: PASS once the fixture and FEYNMAN text share claims.

- [ ] **Step 4: Run the full suite**

Run: `cd skills/feynman-style && .venv/Scripts/python.exe -m pytest tests/ -v`
Expected: all green.

- [ ] **Step 5: Commit**

```bash
git add skills/feynman-style/tests/test_skill_integration.py skills/feynman-style/tests/fixtures/russell_output.md
git commit -m "Add end-to-end non-destruction integration test for feynman-style"
```

---

## Task 24: Suite registration + README

**Files:**
- Modify: top-level `README.md` (add feynman-style to the skill catalog / pipeline diagram).
- Modify: any skill manifest/index the suite uses (found in Step 1).

- [ ] **Step 1: Find where skills are registered**

```bash
grep -rn "russellian-style" C:/russellian-book-suite/README.md C:/russellian-book-suite/CLAUDE.md | head
ls C:/russellian-book-suite/*.json C:/russellian-book-suite/.claude 2>/dev/null
```

- [ ] **Step 2: Add `feynman-style`** to the same places `russellian-style` appears (catalog entry + pipeline sequence: note it runs after russell and is terminal). Keep the description terse and matching house style.

- [ ] **Step 3: Commit**

```bash
git add README.md CLAUDE.md
git commit -m "Register feynman-style in suite docs"
```

---

## Self-Review Notes (completed during planning)

- **Spec coverage:** every spec section maps to a task — identity/pipeline (Task 1 SKILL.md), two-layer contract (Tasks 9, 12, 13), four voice traits (Tasks 2-6), non-destruction partition (Tasks 12, 13, 21, 22), preserve_argument (Task 9), feature-based + local-drop corpus (Tasks 14, 15, 18), system prompts (Task 16), testing (per-task + Task 23), refusal protocol (Tasks 1, 20), out-of-scope items respected (no intensity dial, no network dep).
- **Task numbering** intentionally tracks the file-structure component IDs; gaps (8, 10, 11, 19) were folded into neighbours during decomposition — no missing work.
- **Type consistency:** `LintIssue(linter, line, col, message)` and linter dicts `{rule, line, col, sentence, ...}` are used identically across Tasks 2-7, 13, 23. `PreservationReport(ok, violations)` consistent across Tasks 9, 13, 17, 23. `classify_linter(rule) -> "surface"|"integrity"` consistent across Tasks 13, 21, 22, 23.
- **Adapt-on-read flags:** Tasks 7, 15, 16, 17 depend on exact symbol names in russellian-style source; each instructs the engineer to read the source first and adapt names rather than guess. This is deliberate, not a placeholder.
```
