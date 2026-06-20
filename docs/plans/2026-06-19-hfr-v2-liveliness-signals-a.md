# HFR v2 — Plan 3a of 5: Liveliness Signal Harness + Lexicon-Free Scorers

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the advisory liveliness-scoring harness to `liveliness-signals` plus four scorers that need no vendored lexicon — cadence-corridor, curiosity setup-payoff, novelty-continuity, worked-case — and fix the Plan-1 example-marker substring bug. The curiosity scorer fixes the documented "curiosity-absent" false positive on the real sample.

**Architecture:** Each scorer is a small pure function over a passage's spaCy-tokenized sentences, returning an advisory `{signal, score, findings}` dict; `score_passage` runs the registry and emits a JSON report. Nothing gates (REQ-LIVE-004). Scorers reuse `profile_metrics._nlp()` (POS tagger present, lemmatizer/ner disabled) and the committed profile's per-register corridors.

**Tech Stack:** Python 3.14, spaCy `en_core_web_sm`, stdlib. One skill: `liveliness-signals`.

## Plan set (this is Plan 3a of 5)
1. Corpus Style-Profile — DONE
2. Floor calibration — DONE
3a. **Liveliness signal harness + 4 lexicon-free scorers** ← this plan
3b. Brysbaert concreteness + verb-energy + subject-verb distance + analogy + feynman delegation (next)
4. Generation v2 (`triadic-voice-v2`)
5. Evaluation (`voice-eval` 20×20 harness)

## Global Constraints
- Python `>=3.11`; live env 3.14. spaCy `>=3.7,<4.0` + `en_core_web_sm`. Use the existing `skills/liveliness-signals/.venv`.
- **All scorers are advisory** — `score_passage` and the CLI never exit non-zero on a low score; they emit a report. (REQ-LIVE-004)
- Reuse `profile_metrics._nlp()`; do NOT load a second spaCy model. The lemmatizer is disabled, so use lowercased alpha non-stop token text (not `.lemma_`) for content-word sets.
- Tests carry `pytestmark = pytest.mark.windows_canary`, cite REQ IDs, output pristine. spaCy tests carry `@pytest.mark.needs_model`. No AI attribution; terse commits.
- `ruff.toml` ignores E402/E731/E701/E702/E741; keep F-rules clean (no unused imports/vars).
- Work from worktree `C:\Users\charl\russellian-book-suite-hfr-v2`; do NOT switch git branches; commit on the current branch.

---

### Task 1: Sentence helper + scoring harness skeleton

**Files:**
- Create: `skills/liveliness-signals/scripts/text_util.py`
- Create: `skills/liveliness-signals/scripts/score.py`
- Test: `skills/liveliness-signals/tests/test_text_util.py`

**Interfaces:**
- Produces: `Sentence(text, first, content, n_alpha)` dataclass and `iter_sentences(text) -> list[Sentence]` in `text_util`; `score_passage(text, register="narrative-editorial", profile=None) -> dict` and `SIGNALS: list` registry in `score`.

- [ ] **Step 1: Write the failing test**

```python
# skills/liveliness-signals/tests/test_text_util.py
"""Cites REQ-LIVE-003 (sentence helper for scorers)."""
import pytest
pytestmark = pytest.mark.windows_canary
from scripts.text_util import iter_sentences, Sentence


@pytest.mark.needs_model
def test_iter_sentences_basic():
    sents = iter_sentences("The bank holds your money. You trust it.")
    assert len(sents) == 2
    assert isinstance(sents[0], Sentence)
    assert sents[0].first == "the"
    assert "bank" in sents[0].content and "money" in sents[0].content
    assert "the" not in sents[0].content  # stopword excluded
    assert sents[0].n_alpha >= 4
```

- [ ] **Step 2: Run to confirm it fails**

Run: `cd skills/liveliness-signals && .venv/Scripts/python.exe -m pytest tests/test_text_util.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.text_util'`.

- [ ] **Step 3: Implement `text_util`**

```python
# skills/liveliness-signals/scripts/text_util.py
"""Lightweight sentence view for the liveliness scorers.

Reuses profile_metrics._nlp() (POS tagger on; lemmatizer/ner off), so content
words are lowercased alpha non-stop token TEXT, not lemmas.
"""
from __future__ import annotations
from dataclasses import dataclass

from scripts.profile_metrics import _nlp


@dataclass(frozen=True)
class Sentence:
    text: str
    first: str            # first lowercased alpha token ("" if none)
    content: frozenset    # lowercased alpha non-stop token texts
    n_alpha: int


def iter_sentences(text: str) -> list[Sentence]:
    nlp = _nlp()
    out: list[Sentence] = []
    for sent in nlp(text).sents:
        alpha = [t for t in sent if t.is_alpha]
        if not alpha:
            continue
        first = alpha[0].text.lower()
        content = frozenset(t.text.lower() for t in alpha if not t.is_stop)
        out.append(Sentence(text=sent.text.strip(), first=first,
                            content=content, n_alpha=len(alpha)))
    return out
```

- [ ] **Step 4: Write the failing harness test**

```python
# add to skills/liveliness-signals/tests/test_text_util.py
from scripts.score import score_passage

@pytest.mark.needs_model
def test_score_passage_shape():
    out = score_passage("The bank holds your money. You trust it.", register="narrative-editorial")
    assert out["register"] == "narrative-editorial"
    assert isinstance(out["signals"], dict)   # empty until scorers register
```

- [ ] **Step 5: Run to confirm it fails**

Run: `cd skills/liveliness-signals && .venv/Scripts/python.exe -m pytest tests/test_text_util.py::test_score_passage_shape -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.score'`.

- [ ] **Step 6: Implement the harness skeleton**

```python
# skills/liveliness-signals/scripts/score.py
"""Advisory liveliness scoring harness. Never gates (REQ-LIVE-004)."""
from __future__ import annotations
import json
import sys
from pathlib import Path

from scripts.text_util import iter_sentences

# Each signal is (name, callable(sentences, register, profile) -> dict).
# Scorers are appended in later tasks.
SIGNALS: list = []


def _load_profile_safe(profile):
    if profile is not None:
        return profile
    try:
        import skill_api
        return skill_api.load_profile()
    except Exception:
        return None


def score_passage(text: str, register: str = "narrative-editorial", profile=None) -> dict:
    profile = _load_profile_safe(profile)
    sents = iter_sentences(text)
    signals = {}
    for name, fn in SIGNALS:
        try:
            signals[name] = fn(sents, register, profile)
        except Exception as exc:  # advisory: a scorer error must not break the report
            signals[name] = {"signal": name, "score": None, "error": str(exc)}
    return {"register": register, "n_sentences": len(sents), "signals": signals}


def main(argv: list[str]) -> int:
    args = [a for a in argv[1:] if not a.startswith("--")]
    reg = "narrative-editorial"
    for i, a in enumerate(argv):
        if a == "--register" and i + 1 < len(argv):
            reg = argv[i + 1]
    if not args:
        print("usage: score.py [--register REG] <markdown-file>", file=sys.stderr)
        return 2
    text = Path(args[0]).read_text(encoding="utf-8")
    print(json.dumps(score_passage(text, register=reg), indent=2))
    return 0  # advisory: always 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
```

- [ ] **Step 7: Run both tests**

Run: `cd skills/liveliness-signals && .venv/Scripts/python.exe -m pytest tests/test_text_util.py -q`
Expected: 2 passed.

- [ ] **Step 8: Commit**

```bash
git add skills/liveliness-signals/scripts/text_util.py skills/liveliness-signals/scripts/score.py \
  skills/liveliness-signals/tests/test_text_util.py
git commit -m "Add sentence helper and advisory scoring harness"
```

---

### Task 2: Fix the example-marker substring bug (Plan-1 follow-up)

**Files:**
- Modify: `skills/liveliness-signals/scripts/profile_metrics.py`
- Modify: `skills/liveliness-signals/tests/test_profile_metrics.py`
- Regenerate: `skills/liveliness-signals/assets/hoskinson-style-profile.json`

**Interfaces:** unchanged signatures; `_EXAMPLE_MARKERS` matching becomes word-boundary so `"say"` no longer matches `"essay"`.

- [ ] **Step 1: Write the failing test**

```python
# add to skills/liveliness-signals/tests/test_profile_metrics.py
import re as _re_unused  # noqa: F401  (kept only if needed; remove if unused)

@pytest.mark.needs_model
def test_example_marker_is_word_boundary():
    from scripts.profile_metrics import diction_device_metrics
    # "essay" contains "say" but is NOT an example marker; no marker, no spacing pair
    m = diction_device_metrics(["I wrote an essay about trust. It was long enough to matter here."])
    assert m["example_spacing"] == 0.0
```

- [ ] **Step 2: Run to confirm it fails**

Run: `cd skills/liveliness-signals && .venv/Scripts/python.exe -m pytest tests/test_profile_metrics.py::test_example_marker_is_word_boundary -q`
Expected: FAIL — substring match counts "say" inside "essay", producing a marker.

- [ ] **Step 3: Make the marker match word-boundary**

In `skills/liveliness-signals/scripts/profile_metrics.py`, add `import re` at the top, then replace the example-marker detection. Change:
```python
        low = sent_text.lower()
        if any(m in low for m in _EXAMPLE_MARKERS):
            example_positions.append(i)
```
to:
```python
        low = sent_text.lower()
        if _EXAMPLE_RE.search(low):
            example_positions.append(i)
```
and define the compiled pattern next to `_EXAMPLE_MARKERS`:
```python
_EXAMPLE_RE = re.compile(r"\b(" + "|".join(re.escape(m) for m in _EXAMPLE_MARKERS) + r")\b")
```

- [ ] **Step 4: Run the focused + full suite**

Run: `cd skills/liveliness-signals && .venv/Scripts/python.exe -m pytest -q`
Expected: all pass (the new test + existing).

- [ ] **Step 5: Regenerate the asset and commit**

```bash
cd skills/liveliness-signals && .venv/Scripts/python.exe -m scripts.build_corpus_profile
git add skills/liveliness-signals/scripts/profile_metrics.py skills/liveliness-signals/tests/test_profile_metrics.py \
  skills/liveliness-signals/assets/hoskinson-style-profile.json
git commit -m "Fix example-marker matching to word-boundary; regenerate profile"
```

---

### Task 3: Cadence-corridor scorer

**Files:**
- Create: `skills/liveliness-signals/scripts/signal_cadence.py`
- Modify: `skills/liveliness-signals/scripts/score.py` (register the signal)
- Test: `skills/liveliness-signals/tests/test_signal_cadence.py`

**Interfaces:** `score(sentences, register, profile) -> {"signal":"cadence","score":float,"findings":[...]}`. Rewards rhythmic variety near the register's corpus CV; flags metronomic (too uniform) and erratic (too spiky).

- [ ] **Step 1: Write the failing test**

```python
# skills/liveliness-signals/tests/test_signal_cadence.py
"""Cites REQ-LIVE-005 (cadence corridor, two-sided)."""
import pytest
pytestmark = pytest.mark.windows_canary
from scripts.text_util import iter_sentences
from scripts.signal_cadence import score

PROFILE = {"registers": {"narrative-editorial": {"cadence": {"cv": 0.5}}}}


@pytest.mark.needs_model
def test_metronomic_is_flagged():
    # five sentences of identical length -> cv ~ 0 -> metronomic
    text = " ".join(["The grey cat sat there quietly."] * 5)
    out = score(iter_sentences(text), "narrative-editorial", PROFILE)
    assert out["signal"] == "cadence"
    assert any(f["flag"] == "metronomic" for f in out["findings"])


@pytest.mark.needs_model
def test_varied_passage_scores_positive():
    text = ("No. " "The setup ceremony that builds the whole mathematical stage is the first trust you make. "
            "You check it. " "Then the language, the witness, and the proof all add their own separate bets.")
    out = score(iter_sentences(text), "narrative-editorial", PROFILE)
    assert out["score"] > 0.0
    assert not any(f["flag"] == "metronomic" for f in out["findings"])
```

- [ ] **Step 2: Run to confirm it fails**

Run: `cd skills/liveliness-signals && .venv/Scripts/python.exe -m pytest tests/test_signal_cadence.py -q`
Expected: FAIL — no `scripts.signal_cadence`.

- [ ] **Step 3: Implement the scorer**

```python
# skills/liveliness-signals/scripts/signal_cadence.py
"""Advisory cadence-corridor scorer: rewards rhythmic variety vs the register CV."""
from __future__ import annotations
from statistics import mean, pstdev


def score(sentences, register, profile) -> dict:
    lengths = [s.n_alpha for s in sentences if s.n_alpha > 0]
    findings: list[dict] = []
    if len(lengths) < 3:
        return {"signal": "cadence", "score": 0.0, "findings": findings}
    mu = mean(lengths)
    cv = pstdev(lengths) / mu if mu else 0.0
    corpus_cv = 0.5
    try:
        corpus_cv = float(profile["registers"][register]["cadence"]["cv"]) or 0.5
    except Exception:
        pass
    if cv < 0.5 * corpus_cv:
        findings.append({"flag": "metronomic", "passage_cv": round(cv, 4), "corpus_cv": round(corpus_cv, 4)})
    elif cv > 2.0 * corpus_cv:
        findings.append({"flag": "erratic", "passage_cv": round(cv, 4), "corpus_cv": round(corpus_cv, 4)})
    # reward peaks at parity with corpus cv, decays away from it
    ratio = cv / corpus_cv if corpus_cv else 0.0
    sc = max(0.0, 1.0 - abs(1.0 - min(ratio, 2.0)))
    return {"signal": "cadence", "score": round(sc, 4), "findings": findings,
            "passage_cv": round(cv, 4), "corpus_cv": round(corpus_cv, 4)}
```

- [ ] **Step 4: Register it in `score.py`**

In `skills/liveliness-signals/scripts/score.py`, after `SIGNALS: list = []`, append registration at import time:
```python
from scripts import signal_cadence
SIGNALS.append(("cadence", signal_cadence.score))
```

- [ ] **Step 5: Run focused + full suite**

Run: `cd skills/liveliness-signals && .venv/Scripts/python.exe -m pytest tests/test_signal_cadence.py tests/test_text_util.py -q`
Expected: all pass (the harness test now shows a `cadence` signal).

- [ ] **Step 6: Commit**

```bash
git add skills/liveliness-signals/scripts/signal_cadence.py skills/liveliness-signals/scripts/score.py \
  skills/liveliness-signals/tests/test_signal_cadence.py
git commit -m "Add cadence-corridor scorer"
```

---

### Task 4: Curiosity setup-payoff scorer (fixes the false positive)

**Files:**
- Create: `skills/liveliness-signals/scripts/signal_curiosity.py`
- Modify: `skills/liveliness-signals/scripts/score.py`
- Test: `skills/liveliness-signals/tests/test_signal_curiosity.py`

**Interfaces:** `score(sentences, register, profile) -> {"signal":"curiosity","score":float,"findings":[...]}`. A setup is a gap-opening cue (or an interrogative); a payoff is a following declarative within 1–2 sentences. Counts pairs, not keywords.

- [ ] **Step 1: Write the failing test (asserts on the real sample's curiosity)**

```python
# skills/liveliness-signals/tests/test_signal_curiosity.py
"""Cites REQ-LIVE-008 (setup-payoff, not keywords). Fixes the curiosity-absent false positive."""
import pytest
pytestmark = pytest.mark.windows_canary
from scripts.text_util import iter_sentences
from scripts.signal_curiosity import score

# The motivating sample text that the old keyword detector wrongly called "curiosity-absent".
SAMPLE = ("Here's why that matters. Think about what you do when a bank tells you your balance is correct. "
          "You trust the bank. What people miss is that every one of them is independently testable.")


@pytest.mark.needs_model
def test_sample_curiosity_is_detected():
    out = score(iter_sentences(SAMPLE), "narrative-editorial", None)
    assert out["signal"] == "curiosity"
    assert out["score"] > 0.0
    assert len(out["findings"]) >= 1


@pytest.mark.needs_model
def test_flat_definition_has_no_curiosity():
    out = score(iter_sentences("A commitment scheme hides a value. It binds the value. It opens later."), "technical-exposition", None)
    assert out["score"] == 0.0
```

- [ ] **Step 2: Run to confirm it fails**

Run: `cd skills/liveliness-signals && .venv/Scripts/python.exe -m pytest tests/test_signal_curiosity.py -q`
Expected: FAIL — no `scripts.signal_curiosity`.

- [ ] **Step 3: Implement the scorer**

```python
# skills/liveliness-signals/scripts/signal_curiosity.py
"""Advisory curiosity scorer: setup-payoff pairs, not literal keywords."""
from __future__ import annotations
import re

_SETUP_RE = re.compile(
    r"\b(here'?s why|here is why|what people miss|what most people miss|"
    r"watch what|the question is|the thing is|the part people miss|"
    r"why does|why is|how does|how is)\b")


def _is_setup(sent) -> bool:
    low = sent.text.lower()
    return bool(_SETUP_RE.search(low)) or sent.text.rstrip().endswith("?")


def _is_payoff(sent) -> bool:
    # a payoff is a non-interrogative declarative that carries content
    return (not sent.text.rstrip().endswith("?")) and sent.n_alpha >= 4


def score(sentences, register, profile) -> dict:
    findings: list[dict] = []
    n = len(sentences)
    total_alpha = sum(s.n_alpha for s in sentences) or 1
    for i, s in enumerate(sentences):
        if not _is_setup(s):
            continue
        if any(_is_payoff(sentences[j]) for j in range(i + 1, min(i + 3, n))):
            findings.append({"setup_line": i, "setup": s.text[:80]})
    # density: pairs per ~200 alpha tokens, capped at 1.0
    density = len(findings) / (total_alpha / 200.0)
    return {"signal": "curiosity", "score": round(min(density, 1.0), 4), "findings": findings}
```

- [ ] **Step 4: Register it in `score.py`**

```python
from scripts import signal_curiosity
SIGNALS.append(("curiosity", signal_curiosity.score))
```

- [ ] **Step 5: Run focused + full suite**

Run: `cd skills/liveliness-signals && .venv/Scripts/python.exe -m pytest tests/test_signal_curiosity.py -q && .venv/Scripts/python.exe -m pytest -q`
Expected: both curiosity tests pass; full suite green.

- [ ] **Step 6: Commit**

```bash
git add skills/liveliness-signals/scripts/signal_curiosity.py skills/liveliness-signals/scripts/score.py \
  skills/liveliness-signals/tests/test_signal_curiosity.py
git commit -m "Add curiosity setup-payoff scorer (fixes curiosity-absent false positive)"
```

---

### Task 5: Novelty-continuity scorer (anti-gaming coherence)

**Files:**
- Create: `skills/liveliness-signals/scripts/signal_novelty.py`
- Modify: `skills/liveliness-signals/scripts/score.py`
- Test: `skills/liveliness-signals/tests/test_signal_novelty.py`

**Interfaces:** `score(sentences, register, profile) -> {"signal":"novelty_continuity","score":float,"findings":[...]}`. Adjacent-sentence content-word Jaccard; rewards a corridor (neither near-0 jump-cut nor near-1 restatement); flags both extremes. This is the coherence check a disconnected punchline fails.

- [ ] **Step 1: Write the failing test**

```python
# skills/liveliness-signals/tests/test_signal_novelty.py
"""Cites REQ-LIVE-010 (novelty-continuity corridor; anti-gaming coherence)."""
import pytest
pytestmark = pytest.mark.windows_canary
from scripts.text_util import iter_sentences
from scripts.signal_novelty import score


@pytest.mark.needs_model
def test_restatement_is_flagged():
    text = "The proof hides the secret value. The proof hides the secret value entirely."
    out = score(iter_sentences(text), "narrative-editorial", None)
    assert any(f["flag"] == "restatement" for f in out["findings"])


@pytest.mark.needs_model
def test_disconnected_punchline_is_flagged_as_jump_cut():
    text = "The setup ceremony builds the mathematical stage carefully. Bananas ripen fastest in warm rooms."
    out = score(iter_sentences(text), "narrative-editorial", None)
    assert any(f["flag"] == "jump_cut" for f in out["findings"])
```

- [ ] **Step 2: Run to confirm it fails**

Run: `cd skills/liveliness-signals && .venv/Scripts/python.exe -m pytest tests/test_signal_novelty.py -q`
Expected: FAIL — no `scripts.signal_novelty`.

- [ ] **Step 3: Implement the scorer**

```python
# skills/liveliness-signals/scripts/signal_novelty.py
"""Advisory novelty-continuity scorer: adjacent-sentence content overlap corridor."""
from __future__ import annotations

_LOW = 0.05    # below -> jump cut
_HIGH = 0.6    # above -> restatement


def _jaccard(a: frozenset, b: frozenset) -> float:
    u = a | b
    return len(a & b) / len(u) if u else 0.0


def score(sentences, register, profile) -> dict:
    findings: list[dict] = []
    if len(sentences) < 2:
        return {"signal": "novelty_continuity", "score": 0.0, "findings": findings}
    in_band = 0
    pairs = 0
    for a, b in zip(sentences, sentences[1:]):
        pairs += 1
        j = _jaccard(a.content, b.content)
        if j <= _LOW:
            findings.append({"flag": "jump_cut", "pair_start": sentences.index(a), "jaccard": round(j, 3)})
        elif j >= _HIGH:
            findings.append({"flag": "restatement", "pair_start": sentences.index(a), "jaccard": round(j, 3)})
        else:
            in_band += 1
    return {"signal": "novelty_continuity", "score": round(in_band / pairs, 4) if pairs else 0.0,
            "findings": findings}
```

- [ ] **Step 4: Register it in `score.py`**

```python
from scripts import signal_novelty
SIGNALS.append(("novelty_continuity", signal_novelty.score))
```

- [ ] **Step 5: Run focused + full suite**

Run: `cd skills/liveliness-signals && .venv/Scripts/python.exe -m pytest tests/test_signal_novelty.py -q && .venv/Scripts/python.exe -m pytest -q`
Expected: both tests pass; full suite green.

- [ ] **Step 6: Commit**

```bash
git add skills/liveliness-signals/scripts/signal_novelty.py skills/liveliness-signals/scripts/score.py \
  skills/liveliness-signals/tests/test_signal_novelty.py
git commit -m "Add novelty-continuity scorer (anti-gaming coherence corridor)"
```

---

### Task 6: Worked-case presence scorer + device-challenge regression

**Files:**
- Create: `skills/liveliness-signals/scripts/signal_worked_case.py`
- Modify: `skills/liveliness-signals/scripts/score.py`
- Test: `skills/liveliness-signals/tests/test_signal_worked_case.py`
- Test: `skills/liveliness-signals/tests/test_device_challenge.py`

**Interfaces:** `score(sentences, register, profile) -> {"signal":"worked_case","score":float,"findings":[...]}`. Detects a worked-example / contrast / counterexample frame via word-boundary cues. The device-challenge test confirms the real sample registers curiosity AND worked-case — not "absent".

- [ ] **Step 1: Write the failing tests**

```python
# skills/liveliness-signals/tests/test_signal_worked_case.py
"""Cites REQ-LIVE-011 (worked-case presence)."""
import pytest
pytestmark = pytest.mark.windows_canary
from scripts.text_util import iter_sentences
from scripts.signal_worked_case import score


@pytest.mark.needs_model
def test_worked_example_detected():
    out = score(iter_sentences("Trust is abstract. Think about a bank: you never see the vault, yet you rely on it."), "narrative-editorial", None)
    assert out["score"] == 1.0
    assert out["findings"]


@pytest.mark.needs_model
def test_bare_definition_has_no_worked_case():
    out = score(iter_sentences("A nullifier is a unique tag. It prevents double spends."), "technical-exposition", None)
    assert out["score"] == 0.0
```

```python
# skills/liveliness-signals/tests/test_device_challenge.py
"""Cites REQ-LIVE-013 (device-challenge set: the sample is not 'absent')."""
import pytest
pytestmark = pytest.mark.windows_canary
from scripts.score import score_passage

SAMPLE = ("Here's why that matters. Think about what you do when a bank tells you your balance is correct. "
          "You trust the bank: one trust, one black box. What people miss is that every part is independently testable.")


@pytest.mark.needs_model
def test_sample_registers_curiosity_and_worked_case():
    out = score_passage(SAMPLE, register="narrative-editorial")
    assert out["signals"]["curiosity"]["score"] > 0.0      # not curiosity-absent
    assert out["signals"]["worked_case"]["score"] == 1.0   # bank worked example present
```

- [ ] **Step 2: Run to confirm they fail**

Run: `cd skills/liveliness-signals && .venv/Scripts/python.exe -m pytest tests/test_signal_worked_case.py tests/test_device_challenge.py -q`
Expected: FAIL — no `scripts.signal_worked_case` (and the device test errors on the missing `worked_case` signal).

- [ ] **Step 3: Implement the scorer**

```python
# skills/liveliness-signals/scripts/signal_worked_case.py
"""Advisory worked-case scorer: a worked example / contrast / counterexample frame."""
from __future__ import annotations
import re

_CUES = ("for example", "for instance", "think about", "think of", "consider",
         "suppose", "imagine", "picture", "take the case", "say you",
         "unlike", "whereas", "instead of", "rather than", "as if")
_CUE_RE = re.compile(r"\b(" + "|".join(re.escape(c) for c in _CUES) + r")\b")


def score(sentences, register, profile) -> dict:
    findings: list[dict] = []
    for i, s in enumerate(sentences):
        m = _CUE_RE.search(s.text.lower())
        if m:
            findings.append({"line": i, "cue": m.group(1)})
    return {"signal": "worked_case", "score": 1.0 if findings else 0.0, "findings": findings}
```

- [ ] **Step 4: Register it in `score.py`**

```python
from scripts import signal_worked_case
SIGNALS.append(("worked_case", signal_worked_case.score))
```

- [ ] **Step 5: Run focused + full suite**

Run: `cd skills/liveliness-signals && .venv/Scripts/python.exe -m pytest tests/test_signal_worked_case.py tests/test_device_challenge.py -q && .venv/Scripts/python.exe -m pytest -q`
Expected: all pass; full suite green.

- [ ] **Step 6: Commit**

```bash
git add skills/liveliness-signals/scripts/signal_worked_case.py skills/liveliness-signals/scripts/score.py \
  skills/liveliness-signals/tests/test_signal_worked_case.py skills/liveliness-signals/tests/test_device_challenge.py
git commit -m "Add worked-case scorer and device-challenge regression"
```

---

## Self-Review

**Spec coverage (Plan 3a portion of REQ-LIVE):**
- REQ-LIVE-003 (scorers emit paragraph-level score + JSON) → Tasks 1,3,4,5,6.
- REQ-LIVE-004 (advisory; never gates) → `score_passage`/CLI always return 0; per-scorer errors are swallowed into the report.
- REQ-LIVE-005 (cadence corridor, two-sided) → Task 3.
- REQ-LIVE-008 (curiosity setup-payoff, not keywords) → Task 4, asserted on the real sample.
- REQ-LIVE-010 (novelty-continuity corridor; coherence) → Task 5.
- REQ-LIVE-011 (worked-case) → Task 6.
- REQ-LIVE-013 (device-challenge: sample not "absent") → Task 6 device test (curiosity + worked-case both register on the sample).
- Plan-1 follow-up (example-marker word-boundary) → Task 2.

**Deferred to Plan 3b (not gaps):** REQ-LIVE-006 (verb-energy / light-verb constructions), REQ-LIVE-007 (concrete-anchor / Brysbaert), REQ-LIVE-009 (analogy-mapping), subject-verb distance, the concreteness/light-verb profile augmentation, the feynman-style delegation, and REQ-LIVE-012 (passive end-focus exemption). These need the vendored Brysbaert lexicon and/or the feynman surface.

**Placeholder scan:** none — every step has runnable code + commands + expected output.

**Type consistency:** every scorer exposes `score(sentences, register, profile) -> dict` with a `signal`/`score`/`findings` shape; `score.py` registers them uniformly; `iter_sentences`→`Sentence(text,first,content,n_alpha)` is consumed unchanged by all four scorers.
