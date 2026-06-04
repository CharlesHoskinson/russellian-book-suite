# Reading-Council Scoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a craft-grounded reading rubric (enjoyment/flow/style/quality, 1-5) scored by the existing persona council and aggregated (median) into one synthesized `reading-score.json`, with Flesch + burstiness reported alongside; documentation-scoped, advisory.

**Architecture:** A new `review-conductor/scripts/reading_scores.py` (pure stdlib: deterministic anchors, prompt builder, median aggregation with a templated single-voice verdict, thin injected-dispatcher orchestrator), plus a rubric asset, an output schema, a `documentation` panel, and a one-line panel-schema enum addition.

**Tech Stack:** Python 3.11+, stdlib (`re`, `statistics`, `json`). pytest (global). No spaCy, no network, no live LLM.

**Spec:** `openspec/changes/add-reading-council-scoring/` (REQ-READING-001..008), `docs/specs/2026-05-27-reading-council-scoring-design.md`.

Run tests from the skill root: `cd skills/review-conductor && python -m pytest tests/<file> -v`.

---

### Task 1: deterministic anchors

**Files:**
- Create: `skills/review-conductor/scripts/reading_scores.py`
- Test: `skills/review-conductor/tests/test_reading_scores.py`

- [ ] **Step 1: Write the failing test**

```python
"""Cites REQ-READING-006, REQ-READING-008."""
import pytest
from scripts.reading_scores import flesch_reading_ease, burstiness


def test_flesch_easy_text_scores_high():
    assert flesch_reading_ease("The cat sat on the mat.") > 90

def test_flesch_harder_text_scores_lower_than_easy():
    easy = flesch_reading_ease("The cat sat on the mat. The dog ran.")
    hard = flesch_reading_ease("Consequently, the epistemological ramifications necessitate considerable reconsideration.")
    assert hard < easy

def test_flesch_empty_is_zero():
    assert flesch_reading_ease("") == 0.0

def test_burstiness_uniform_is_low():
    assert burstiness("aa bb cc. dd ee ff. gg hh ii.") == 0.0

def test_burstiness_varied_is_high():
    assert burstiness("Short. " + "word " * 30 + ". Tiny.") > 0.4

def test_burstiness_single_sentence_is_zero():
    assert burstiness("just one sentence here") == 0.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd skills/review-conductor && python -m pytest tests/test_reading_scores.py -v`
Expected: FAIL (module does not exist).

- [ ] **Step 3: Write minimal implementation**

```python
"""Reading-council scoring: deterministic anchors, scoring prompt, and median
aggregation into one synthesized reading score. Advisory; no live LLM (the dispatcher
is caller-provided); aggregation and anchors are deterministic and offline.
"""
from __future__ import annotations

import json
import re
import statistics
import sys
from pathlib import Path

_VOWELS = "aeiouy"
DIMENSIONS = ("enjoyment", "flow", "style", "quality")


def _words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z']+", text)


def _sentences(text: str) -> list[str]:
    return [s for s in re.split(r"[.!?]+", text) if s.strip()]


def _syllables(word: str) -> int:
    word = word.lower()
    count, prev_vowel = 0, False
    for ch in word:
        is_vowel = ch in _VOWELS
        if is_vowel and not prev_vowel:
            count += 1
        prev_vowel = is_vowel
    if word.endswith("e") and count > 1:
        count -= 1
    return max(count, 1)


def flesch_reading_ease(text: str) -> float:
    words, sentences = _words(text), _sentences(text)
    if not words or not sentences:
        return 0.0
    syllables = sum(_syllables(w) for w in words)
    words_per_sentence = len(words) / len(sentences)
    syllables_per_word = syllables / len(words)
    return round(206.835 - 1.015 * words_per_sentence - 84.6 * syllables_per_word, 2)


def burstiness(text: str) -> float:
    lengths = [len(_words(s)) for s in _sentences(text)]
    lengths = [n for n in lengths if n > 0]
    if len(lengths) < 2:
        return 0.0
    mean = statistics.mean(lengths)
    if mean == 0:
        return 0.0
    return round(statistics.pstdev(lengths) / mean, 3)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd skills/review-conductor && python -m pytest tests/test_reading_scores.py -v`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git -C C:\russellian-book-suite add skills/review-conductor/scripts/reading_scores.py skills/review-conductor/tests/test_reading_scores.py
git -C C:\russellian-book-suite commit -m "Add reading-score deterministic anchors (Flesch, burstiness)"
```

---

### Task 2: scoring prompt + median aggregation + synthesized verdict

**Files:**
- Modify: `skills/review-conductor/scripts/reading_scores.py`
- Test: `skills/review-conductor/tests/test_reading_scores.py`

- [ ] **Step 1: Append the failing test**

```python
def test_build_scoring_prompt_contains_rubric_doc_scale_and_dims():
    from scripts.reading_scores import build_scoring_prompt
    p = build_scoring_prompt("RUBRIC-TEXT-HERE", "DOC-TEXT-HERE")
    assert "RUBRIC-TEXT-HERE" in p and "DOC-TEXT-HERE" in p
    assert "1 to 5" in p
    for dim in ("enjoyment", "flow", "style", "quality"):
        assert dim in p.lower()

def test_aggregate_medians_and_overall():
    from scripts.reading_scores import aggregate_reading_scores
    scores = [
        {"enjoyment": 4, "flow": 3, "style": 4, "quality": 5, "note": "PERSONA-A-SECRET"},
        {"enjoyment": 2, "flow": 3, "style": 4, "quality": 3, "note": "PERSONA-B-SECRET"},
        {"enjoyment": 3, "flow": 4, "style": 2, "quality": 4, "note": "PERSONA-C-SECRET"},
    ]
    rep = aggregate_reading_scores(scores, "The cat sat on the mat. The dog ran fast today.")
    assert rep["enjoyment"] == 3 and rep["flow"] == 3 and rep["style"] == 4 and rep["quality"] == 4
    assert rep["overall"] == round((3 + 3 + 4 + 4) / 4, 2)
    assert set(rep["deterministic"]) == {"flesch", "burstiness"}
    assert isinstance(rep["verdict"], str) and rep["verdict"]

def test_aggregate_does_not_leak_persona_text():
    from scripts.reading_scores import aggregate_reading_scores
    scores = [{"enjoyment": 4, "flow": 4, "style": 4, "quality": 4, "note": "PERSONA-A-SECRET"}]
    rep = aggregate_reading_scores(scores, "A short document with several plain words in it here.")
    assert "PERSONA-A-SECRET" not in json.dumps(rep)

def test_aggregate_empty_raises():
    from scripts.reading_scores import aggregate_reading_scores
    with pytest.raises(ValueError):
        aggregate_reading_scores([], "text")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd skills/review-conductor && python -m pytest tests/test_reading_scores.py -k "prompt or aggregate" -v`
Expected: FAIL (functions not defined).

- [ ] **Step 3: Implement** — append to `reading_scores.py`

```python
def build_scoring_prompt(rubric_text: str, doc_text: str) -> str:
    return (
        f"{rubric_text}\n\n"
        f"# Document to score\n\n{doc_text}\n\n"
        f"# Task\n"
        f"Score the document on each of the four dimensions — enjoyment, flow, style, "
        f"quality — from 1 to 5 against the rubric above, with one line of justification "
        f"per dimension. Return only the four scores and their one-line justifications."
    )


def _band(flesch: float) -> str:
    if flesch >= 70:
        return "very easy"
    if flesch >= 50:
        return "plain"
    return "demanding"


def _synthesize_verdict(medians: dict, overall: float, flesch: float) -> str:
    best = max(DIMENSIONS, key=lambda d: medians[d])
    worst = min(DIMENSIONS, key=lambda d: medians[d])
    return (
        f"Reads at {overall}/5 overall — strongest on {best} ({medians[best]}), "
        f"weakest on {worst} ({medians[worst]}); {_band(flesch)} readability "
        f"(Flesch {flesch})."
    )


def aggregate_reading_scores(persona_scores: list[dict], text: str) -> dict:
    if not persona_scores:
        raise ValueError("need at least one persona score")
    medians = {d: round(statistics.median([s[d] for s in persona_scores]), 2) for d in DIMENSIONS}
    overall = round(statistics.mean([medians[d] for d in DIMENSIONS]), 2)
    flesch = flesch_reading_ease(text)
    burst = burstiness(text)
    return {
        **medians,
        "overall": overall,
        "deterministic": {"flesch": flesch, "burstiness": burst},
        "verdict": _synthesize_verdict(medians, overall, flesch),
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd skills/review-conductor && python -m pytest tests/test_reading_scores.py -v`
Expected: PASS (10 tests).

- [ ] **Step 5: Commit**

```bash
git -C C:\russellian-book-suite add skills/review-conductor/scripts/reading_scores.py skills/review-conductor/tests/test_reading_scores.py
git -C C:\russellian-book-suite commit -m "Add reading-score prompt and synthesized median aggregation"
```

---

### Task 3: rubric asset, output schema, documentation panel

**Files:**
- Create: `skills/review-conductor/assets/reading-rubric.md`
- Create: `skills/review-conductor/assets/reading-score.schema.json`
- Create: `skills/review-conductor/panels/documentation.yaml`
- Modify: `skills/review-conductor/assets/panel-config.schema.json` (add "documentation" to the `artifact_scope` enum)
- Test: `skills/review-conductor/tests/test_reading_scores.py`

- [ ] **Step 1: Append the failing test**

```python
def test_documentation_panel_loads_with_documentation_scope():
    from scripts.load_panel import load_panel
    panel = load_panel(Path(__file__).resolve().parent.parent / "panels" / "documentation.yaml")
    assert panel["artifact_scope"] == "documentation"
    ids = [p["id"] for p in panel["personas"]]
    assert "enjoyment-reader" in ids

def test_reading_rubric_names_four_dimensions():
    rubric = (Path(__file__).resolve().parent.parent / "assets" / "reading-rubric.md").read_text(encoding="utf-8")
    for dim in ("Enjoyment", "Flow", "Style", "Quality"):
        assert dim in rubric
```

(If `load_panel` exposes a different function name, adjust the import to match `scripts/load_panel.py`.)

- [ ] **Step 2: Run test to verify it fails**

Run: `cd skills/review-conductor && python -m pytest tests/test_reading_scores.py -k "documentation_panel or rubric" -v`
Expected: FAIL (files do not exist / schema rejects "documentation").

- [ ] **Step 3a: Add "documentation" to the panel-config schema enum**

In `assets/panel-config.schema.json`, change the `artifact_scope` enum from
`["chapter", "readme", "intro", "abstract", "marketing"]` to
`["chapter", "readme", "intro", "abstract", "marketing", "documentation"]`.

- [ ] **Step 3b: Create `assets/reading-rubric.md`**

```markdown
# Reading rubric

Score each dimension from 1 (poor) to 5 (excellent), with one line of justification.

## Enjoyment
Absorption and the pull to keep reading. Narrative Transportation: does it hold
attention, stir any affect, and put concrete pictures in the mind? Sol Stein's test:
"the best reading experiences defy interruption." 5 = could not put it down; 3 = read on
without resistance; 1 = abandoned early.

## Flow
Momentum from sentence to sentence and paragraph to paragraph. Clean transitions; the
paragraph as a unit of thought (Strunk-White); varied rhythm. 5 = never snags; 1 =
constant stalls and rereads.

## Style
Vigour and economy. "Make every word tell"; prefer the specific, definite, concrete
(Strunk-White); the particular distinguishing detail over the cliché (Stein); a present,
consistent voice. 5 = vivid and economical; 1 = flat, padded, or generic.

## Quality
Clarity, structure, accuracy, and earning its length. 5 = nothing to cut, nothing
unclear; 1 = confused, bloated, or wrong.
```

- [ ] **Step 3c: Create `assets/reading-score.schema.json`**

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "reading-score",
  "type": "object",
  "required": ["enjoyment", "flow", "style", "quality", "overall", "deterministic", "verdict"],
  "properties": {
    "enjoyment": {"type": "number", "minimum": 1, "maximum": 5},
    "flow": {"type": "number", "minimum": 1, "maximum": 5},
    "style": {"type": "number", "minimum": 1, "maximum": 5},
    "quality": {"type": "number", "minimum": 1, "maximum": 5},
    "overall": {"type": "number", "minimum": 1, "maximum": 5},
    "deterministic": {
      "type": "object",
      "required": ["flesch", "burstiness"],
      "properties": {"flesch": {"type": "number"}, "burstiness": {"type": "number"}}
    },
    "verdict": {"type": "string", "minLength": 1}
  },
  "additionalProperties": false
}
```

- [ ] **Step 3d: Create `panels/documentation.yaml`**

```yaml
panel_id: documentation
artifact_scope: documentation
description: Reading-council scoring of documentation prose (advisory).
personas:
  - id: enjoyment-reader
    severity_gate: advisory
  - id: gottlieb
    severity_gate: advisory
  - id: lay-reader
    severity_gate: advisory
  - id: first-time-visitor
    severity_gate: advisory
verdict:
  hard_gate: false
  soft_gate_rule: any_critical_from_gating
outcomes:
  exemplar_paths:
    - ../book-review/references/outcomes/readme-pass-2026-05-13/
  per_persona_exemplars: 1
output:
  panel_report_path: "reports/reading/{artifact_id}-reading.md"
  verdict_path: "reports/reading/{artifact_id}-reading-score.json"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd skills/review-conductor && python -m pytest tests/test_reading_scores.py -v`
Expected: PASS. (If `load_panel`'s validator rejects the panel for another required field, align `documentation.yaml` to `chapter-default.yaml`'s shape.)

- [ ] **Step 5: Commit**

```bash
git -C C:\russellian-book-suite add skills/review-conductor/assets/reading-rubric.md skills/review-conductor/assets/reading-score.schema.json skills/review-conductor/panels/documentation.yaml skills/review-conductor/assets/panel-config.schema.json skills/review-conductor/tests/test_reading_scores.py
git -C C:\russellian-book-suite commit -m "Add reading rubric, score schema, and documentation panel"
```

---

### Task 4: orchestrator + regression

**Files:**
- Modify: `skills/review-conductor/scripts/reading_scores.py`
- Test: `skills/review-conductor/tests/test_reading_scores.py`

- [ ] **Step 1: Append the failing test**

```python
def test_run_reading_council_with_stub_dispatcher():
    from scripts.reading_scores import run_reading_council
    def stub_dispatcher(prompt, personas):
        # one score dict per persona; notes must not leak into output
        return [{"enjoyment": 4, "flow": 4, "style": 3, "quality": 4, "note": f"{p}-note"}
                for p in personas]
    rep = run_reading_council(
        "A short readable document. It has two plain sentences here for scoring.",
        dispatcher=stub_dispatcher,
        rubric_text="RUBRIC",
        personas=["enjoyment-reader", "gottlieb", "lay-reader", "first-time-visitor"],
    )
    assert rep["style"] == 3 and rep["enjoyment"] == 4
    assert "note" not in rep and "enjoyment-reader-note" not in json.dumps(rep)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd skills/review-conductor && python -m pytest tests/test_reading_scores.py -k run_reading_council -v`
Expected: FAIL (`run_reading_council` not defined).

- [ ] **Step 3: Implement** — append to `reading_scores.py`

```python
def run_reading_council(doc_text: str, *, dispatcher, rubric_text: str,
                        personas: list[str]) -> dict:
    """Score a document with the injected council dispatcher and synthesize one score.

    `dispatcher(prompt, personas) -> list[dict]` returns one score dict per persona
    (keys: enjoyment, flow, style, quality; an optional `note` is ignored in the output).
    No live LLM call happens here; the dispatcher is caller-provided.
    """
    prompt = build_scoring_prompt(rubric_text, doc_text)
    persona_scores = dispatcher(prompt, personas)
    return aggregate_reading_scores(persona_scores, doc_text)


def write_reading_report(report: dict, out_path) -> None:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")


def main(argv: list[str]) -> int:
    # CLI scores a document from a JSON file of per-persona scores (offline; the council
    # dispatch happens upstream). Usage: reading_scores.py <doc.md> <persona-scores.json> [out.json]
    if len(argv) < 3:
        print("usage: reading_scores.py <doc.md> <persona-scores.json> [out.json]", file=sys.stderr)
        return 2
    text = Path(argv[1]).read_text(encoding="utf-8", errors="replace")
    scores = json.loads(Path(argv[2]).read_text(encoding="utf-8"))
    report = aggregate_reading_scores(scores, text)
    if len(argv) > 3:
        write_reading_report(report, argv[3])
        print(f"wrote {argv[3]}")
    else:
        print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
```

- [ ] **Step 4: Run tests; then the full review-conductor suite**

Run: `cd skills/review-conductor && python -m pytest tests/test_reading_scores.py -v` (expect all pass)
Then: `cd skills/review-conductor && python -m pytest tests/ -q` (expect no regressions in the existing suite).

- [ ] **Step 5: Commit**

```bash
git -C C:\russellian-book-suite add skills/review-conductor/scripts/reading_scores.py skills/review-conductor/tests/test_reading_scores.py
git -C C:\russellian-book-suite commit -m "Add reading-council orchestrator, report writer, and CLI"
```

---

### Task 5: demo — score the README

**Files:**
- Create: `docs/audits/2026-05-27-reading-council/README-reading-score.json`
- Create: `docs/audits/2026-05-27-reading-council/README.md`

- [ ] **Step 1: Score the repo README via a foreground council**

The implementing agent acts as the four-persona council (enjoyment-reader, gottlieb,
lay-reader, first-time-visitor): read `C:\russellian-book-suite\README.md` (or its
Introduction section) and assign each persona honest 1-5 scores on the four dimensions
against `assets/reading-rubric.md`. Save the per-persona scores to a temp JSON, then:

```bash
cd /c/russellian-book-suite/skills/review-conductor
python -m scripts.reading_scores ../../README.md <temp-persona-scores.json> \
  ../../docs/audits/2026-05-27-reading-council/README-reading-score.json
```

Confirm the JSON has the four dimension scores, overall, deterministic anchors (the
real Flesch + burstiness of the README), and a synthesized one-line verdict with no
per-persona text.

- [ ] **Step 2: Write the bundle README and commit**

`README.md` states what was scored, the enjoyment/flow/style/quality numbers, the
deterministic anchors, and an honest one-paragraph read of where the documentation is
lively vs. stale.

```bash
git -C C:\russellian-book-suite add docs/audits/2026-05-27-reading-council/
git -C C:\russellian-book-suite commit -m "Add reading-council README scoring demo"
```

---

## Self-review (completed during planning)

- **Spec coverage:** REQ-READING-001 (rubric asset, Task 3); 002 (documentation panel + scope enum, Task 3); 003 (build_scoring_prompt, Task 2); 004 (aggregate medians + overall + reading-score, Task 2); 005 (synthesized verdict, no leakage — Task 2 tests); 006 (Flesch + burstiness alongside, Task 1 + Task 2); 007 (advisory — no gate/raise on scores anywhere); 008 (injected dispatcher, deterministic/offline — Tasks 1/2/4). All mapped.
- **Placeholder scan:** none — full module/asset/panel code and commands given.
- **Type/name consistency:** `flesch_reading_ease`, `burstiness`, `build_scoring_prompt`, `aggregate_reading_scores`, `run_reading_council`, `DIMENSIONS`, and the output keys (`enjoyment/flow/style/quality/overall/deterministic/verdict`) are consistent across tasks.

## Not in scope

- Recurring all-docs staleness sweep (make target / scheduled trigger); a book-compose gate; golden-set calibration tuning; wiring the live council dispatcher (the dispatch happens upstream; the CLI consumes per-persona scores).
- Pushing / opening a PR.
