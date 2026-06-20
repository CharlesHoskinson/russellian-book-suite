# HFR v2 — Plan 3b of 5: Verb-Energy + Subject-Verb Distance Scorers

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Add two more advisory scorers to `liveliness-signals` — verb-energy (action-bearing density + light-verb-construction flags) and subject→verb distance (Gopen–Swan cognitive load) — both spaCy-dependency based, no external dataset. This brings the advisory suite to 6 of 8 signals.

**Architecture:** Same scorer contract as Plan 3a — `score(sentences_or_doc, register, profile) -> {signal, score, findings}`, advisory, registered in `score.SIGNALS`. These two scorers need token-level dependency/POS info, which the `Sentence` dataclass from Plan 3a does NOT carry, so they consume a spaCy `Doc` via a new `text_util.iter_spacy_sentences(text)` helper that yields spaCy sentence spans (the parser is enabled in `profile_metrics._nlp()`).

**Tech Stack:** Python 3.14, spaCy `en_core_web_sm` (parser + tagger on; ner/lemmatizer off), stdlib. One skill: `liveliness-signals`.

## Plan set (this is Plan 3b of 5)
1. Corpus Style-Profile — DONE
2. Floor calibration — DONE
3a. Signal harness + 4 lexicon-free scorers — DONE
3b. **Verb-energy + subject-verb distance** ← this plan
3c. Brysbaert concrete-anchor + analogy-mapping (embeddings) + feynman delegation + profile augmentation (deferred)
4. Generation v2 (`triadic-voice-v2`)
5. Evaluation (`voice-eval` 20×20 harness)

## Global Constraints
- Python `>=3.11`; live env 3.14. spaCy `>=3.7,<4.0` + `en_core_web_sm`. Use `skills/liveliness-signals/.venv`.
- **Advisory only** (REQ-LIVE-004): scorers never gate; the harness already swallows scorer errors.
- Reuse `profile_metrics._nlp()` — no second model. Without the lemmatizer, match light verbs by an inflected text set, not `.lemma_`.
- Tests carry `pytestmark = pytest.mark.windows_canary`, cite REQ IDs, output pristine; spaCy tests `@pytest.mark.needs_model`. No AI attribution; terse commits.
- `ruff.toml` ignores E402/E731/E701/E702/E741; keep F-rules clean.
- Work from worktree `C:\Users\charl\russellian-book-suite-hfr-v2`; do NOT switch git branches; commit on the current branch.

---

### Task 1: spaCy-sentence helper

**Files:**
- Modify: `skills/liveliness-signals/scripts/text_util.py`
- Modify: `skills/liveliness-signals/tests/test_text_util.py`

**Interfaces:**
- Produces: `iter_spacy_sentences(text) -> list` returning spaCy sentence spans (each carries token `.pos_`, `.dep_`, `.head`, `.children`, `.i`, `.root`). The existing `Sentence`/`iter_sentences` are unchanged.

- [ ] **Step 1: Write the failing test**

```python
# add to skills/liveliness-signals/tests/test_text_util.py
from scripts.text_util import iter_spacy_sentences

@pytest.mark.needs_model
def test_iter_spacy_sentences_exposes_deps():
    sents = iter_spacy_sentences("The careful reader tracks each cue.")
    assert len(sents) == 1
    root = sents[0].root
    assert root.pos_ in ("VERB", "AUX")            # "tracks"
    subs = [t for t in sents[0] if t.dep_ == "nsubj"]
    assert subs and subs[0].text.lower() == "reader"
```

- [ ] **Step 2: Run to confirm it fails**

Run: `cd skills/liveliness-signals && .venv/Scripts/python.exe -m pytest tests/test_text_util.py::test_iter_spacy_sentences_exposes_deps -q`
Expected: FAIL — `ImportError: cannot import name 'iter_spacy_sentences'`.

- [ ] **Step 3: Implement the helper**

```python
# append to skills/liveliness-signals/scripts/text_util.py
def iter_spacy_sentences(text: str) -> list:
    """Yield spaCy sentence spans (parser + tagger on) for dependency scorers."""
    nlp = _nlp()
    return [s for s in nlp(text).sents if any(t.is_alpha for t in s)]
```

- [ ] **Step 4: Run to confirm it passes**

Run: `cd skills/liveliness-signals && .venv/Scripts/python.exe -m pytest tests/test_text_util.py -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add skills/liveliness-signals/scripts/text_util.py skills/liveliness-signals/tests/test_text_util.py
git commit -m "Add spaCy-sentence helper for dependency scorers"
```

---

### Task 2: Verb-energy scorer

**Files:**
- Create: `skills/liveliness-signals/scripts/signal_verb_energy.py`
- Modify: `skills/liveliness-signals/scripts/score.py`
- Test: `skills/liveliness-signals/tests/test_signal_verb_energy.py`

**Interfaces:** `score(sentences, register, profile) -> {"signal":"verb_energy","score":float,"findings":[...]}`. The harness passes the Plan-3a `Sentence` list as `sentences`, which lacks deps; this scorer re-derives a spaCy view from the joined sentence text via `iter_spacy_sentences`. Score = lexical-verb density (VERB tokens / content tokens). Findings = light-verb + event-noun constructions.

- [ ] **Step 1: Write the failing test**

```python
# skills/liveliness-signals/tests/test_signal_verb_energy.py
"""Cites REQ-LIVE-006 (verb-energy: lexical verbs + light-verb-construction flags)."""
import pytest
pytestmark = pytest.mark.windows_canary
from scripts.signal_verb_energy import score_text


@pytest.mark.needs_model
def test_action_prose_scores_higher_than_noun_pile():
    active = "She cuts the deck, breaks the seal, and hands you the card."
    nouny = "The verification of the transaction is a consideration for the formalization."
    assert score_text(active)["score"] > score_text(nouny)["score"]


@pytest.mark.needs_model
def test_light_verb_construction_is_flagged():
    out = score_text("The team will make a proposal about the migration.")
    assert any("make" in f.get("construction", "") for f in out["findings"])
```

- [ ] **Step 2: Run to confirm it fails**

Run: `cd skills/liveliness-signals && .venv/Scripts/python.exe -m pytest tests/test_signal_verb_energy.py -q`
Expected: FAIL — no `scripts.signal_verb_energy`.

- [ ] **Step 3: Implement the scorer**

```python
# skills/liveliness-signals/scripts/signal_verb_energy.py
"""Advisory verb-energy scorer: lexical-verb density + light-verb-construction flags.

Targets light-verb + event-noun constructions (make a proposal), not all
nominalizations (cmp-lg/9503010). Lemmatizer is off, so light verbs are matched
by an inflected text set.
"""
from __future__ import annotations
import re

from scripts.text_util import iter_spacy_sentences

_LIGHT_VERBS = {
    "make", "makes", "made", "making",
    "have", "has", "had", "having",
    "give", "gives", "gave", "giving",
    "take", "takes", "took", "taking",
    "do", "does", "did", "doing",
    "conduct", "conducts", "conducted",
    "perform", "performs", "performed",
    "provide", "provides", "provided",
}
_EVENT_NOUN = re.compile(r"(tion|ment|ance|ence|sion|ity|ing)$")


def score_text(text: str) -> dict:
    spans = iter_spacy_sentences(text)
    content = 0
    lexical_verbs = 0
    findings: list[dict] = []
    for sent in spans:
        for t in sent:
            if t.is_alpha:
                content += 1
                if t.pos_ == "VERB":
                    lexical_verbs += 1
            # light-verb construction: light verb governing an event-noun dobj
            if t.pos_ == "VERB" and t.text.lower() in _LIGHT_VERBS:
                for child in t.children:
                    if child.dep_ == "dobj" and child.pos_ == "NOUN" and _EVENT_NOUN.search(child.text.lower()):
                        findings.append({"construction": f"{t.text.lower()} {child.text.lower()}",
                                        "line": sent.start})
    score = lexical_verbs / content if content else 0.0
    return {"signal": "verb_energy", "score": round(score, 4),
            "lexical_verb_density": round(score, 4), "findings": findings}


def score(sentences, register, profile) -> dict:
    # Harness passes Plan-3a Sentence objects (no deps); re-derive from their text.
    text = " ".join(s.text for s in sentences)
    return score_text(text)
```

- [ ] **Step 4: Register it in `score.py`**

```python
from scripts import signal_verb_energy
SIGNALS.append(("verb_energy", signal_verb_energy.score))
```

- [ ] **Step 5: Run focused + full suite**

Run: `cd skills/liveliness-signals && .venv/Scripts/python.exe -m pytest tests/test_signal_verb_energy.py -q && .venv/Scripts/python.exe -m pytest -q`
Expected: both verb-energy tests pass; full suite green.

- [ ] **Step 6: Commit**

```bash
git add skills/liveliness-signals/scripts/signal_verb_energy.py skills/liveliness-signals/scripts/score.py \
  skills/liveliness-signals/tests/test_signal_verb_energy.py
git commit -m "Add verb-energy scorer (lexical-verb density + light-verb flags)"
```

---

### Task 3: Subject→verb distance scorer + sample assertion

**Files:**
- Create: `skills/liveliness-signals/scripts/signal_sv_distance.py`
- Modify: `skills/liveliness-signals/scripts/score.py`
- Test: `skills/liveliness-signals/tests/test_signal_sv_distance.py`
- Modify: `skills/liveliness-signals/tests/test_device_challenge.py`

**Interfaces:** `score(sentences, register, profile) -> {"signal":"sv_distance","score":float,"findings":[...]}`. For each sentence, distance between the ROOT and its `nsubj`; flag > 7 tokens; score = fraction of subject-bearing sentences whose distance ≤ 7.

- [ ] **Step 1: Write the failing tests**

```python
# skills/liveliness-signals/tests/test_signal_sv_distance.py
"""Cites REQ-LIVE-003 (subject-verb distance; Gopen-Swan cognitive load)."""
import pytest
pytestmark = pytest.mark.windows_canary
from scripts.signal_sv_distance import score_text


@pytest.mark.needs_model
def test_tight_subject_verb_scores_high():
    out = score_text("The reader tracks the cue. You trust the bank.")
    assert out["score"] == 1.0
    assert not out["findings"]


@pytest.mark.needs_model
def test_far_separated_subject_verb_is_flagged():
    text = "The reader, who had spent the entire long and difficult afternoon rereading every footnote, paused."
    out = score_text(text)
    assert any(f["distance"] > 7 for f in out["findings"])
```

- [ ] **Step 2: Run to confirm it fails**

Run: `cd skills/liveliness-signals && .venv/Scripts/python.exe -m pytest tests/test_signal_sv_distance.py -q`
Expected: FAIL — no `scripts.signal_sv_distance`.

- [ ] **Step 3: Implement the scorer**

```python
# skills/liveliness-signals/scripts/signal_sv_distance.py
"""Advisory subject->verb distance scorer (Gopen-Swan cognitive load)."""
from __future__ import annotations

from scripts.text_util import iter_spacy_sentences

_MAX = 7


def score_text(text: str) -> dict:
    spans = iter_spacy_sentences(text)
    findings: list[dict] = []
    ok = 0
    measured = 0
    for sent in spans:
        root = sent.root
        subj = next((c for c in root.children if c.dep_ == "nsubj"), None)
        if subj is None:
            continue
        measured += 1
        dist = abs(root.i - subj.i)
        if dist > _MAX:
            findings.append({"distance": dist, "subject": subj.text, "verb": root.text, "line": sent.start})
        else:
            ok += 1
    score = ok / measured if measured else 0.0
    return {"signal": "sv_distance", "score": round(score, 4), "findings": findings}


def score(sentences, register, profile) -> dict:
    text = " ".join(s.text for s in sentences)
    return score_text(text)
```

- [ ] **Step 4: Register it in `score.py`**

```python
from scripts import signal_sv_distance
SIGNALS.append(("sv_distance", signal_sv_distance.score))
```

- [ ] **Step 5: Extend the device-challenge test (the sample is verb-driven, tightly bound)**

```python
# add to skills/liveliness-signals/tests/test_device_challenge.py
@pytest.mark.needs_model
def test_sample_is_verb_driven_and_tightly_bound():
    out = score_passage(SAMPLE, register="narrative-editorial")
    assert out["signals"]["verb_energy"]["score"] > 0.10      # action-bearing prose
    assert out["signals"]["sv_distance"]["score"] >= 0.5       # mostly tight subject-verb
```

- [ ] **Step 6: Run focused + full suite**

Run: `cd skills/liveliness-signals && .venv/Scripts/python.exe -m pytest tests/test_signal_sv_distance.py tests/test_device_challenge.py -q && .venv/Scripts/python.exe -m pytest -q`
Expected: all pass; full suite green. If the sample thresholds (0.10 / 0.5) are off, measure with `.venv/Scripts/python.exe -c "import skill_api; from scripts.score import score_passage; print(score_passage(open('../../examples/triadic-trust-decomposition.md').read()))"` and set the assert just below the measured values (do not inflate).

- [ ] **Step 7: Commit**

```bash
git add skills/liveliness-signals/scripts/signal_sv_distance.py skills/liveliness-signals/scripts/score.py \
  skills/liveliness-signals/tests/test_signal_sv_distance.py skills/liveliness-signals/tests/test_device_challenge.py
git commit -m "Add subject-verb distance scorer and sample verb/binding assertions"
```

---

## Self-Review

**Spec coverage (Plan 3b portion of REQ-LIVE):**
- REQ-LIVE-006 (verb-energy targets light-verb constructions, not suffix counts) → Task 2; lexical-verb density is the reward, light-verb+event-noun the flag.
- Subject-verb distance (Gopen-Swan; part of REQ-LIVE-003's scorer set) → Task 3.
- Advisory (REQ-LIVE-004) → both registered, harness swallows errors; CLI unaffected.

**Deferred to Plan 3c (not gaps):** REQ-LIVE-007 (Brysbaert concrete-anchor — needs the vendored dataset), REQ-LIVE-009 (analogy-mapping — needs embeddings for a non-keyword detector), the profile light-verb/concreteness augmentation, REQ-VOICE-012 (passive end-focus), and the feynman-style delegation (which needs the analogy/concreteness detectors to redirect to).

**Placeholder scan:** none — every step has runnable code + commands + expected output; the one tunable (the two sample thresholds in Task 3 Step 5) has an explicit measure-then-set procedure.

**Type consistency:** both new scorers expose `score(sentences, register, profile)` + a `score_text(text)` core; `iter_spacy_sentences` returns spaCy spans consumed by both. The harness contract (`{signal, score, findings}`) is preserved.

**Note on the harness re-deriving spaCy:** Tasks 2–3 re-join `Sentence.text` and re-run spaCy for deps rather than threading a Doc through the harness. This is a deliberate v1 simplicity choice (one extra parse per passage, cheap for short passages); Plan 4/5 can optimize by passing a Doc through `score_passage` if profiling shows it matters.
