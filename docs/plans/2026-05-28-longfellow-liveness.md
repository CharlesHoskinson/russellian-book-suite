# Longfellow × Russell liveness blend — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the russellian-style voice with a Longfellow-inspired liveness blend — drive, rhythm, and argument-anchored image — measured by composing existing instruments plus an order-sensitive nPVI cadence signal, guarded against decoration by a new ornament linter, and validated by a blind reading-council A/B.

**Architecture:** Two existing capabilities are extended (no new capability). `VOICE` gains a `## Liveness` subsection in each mode prompt at a per-mode dial and a new pure-regex `lint_ornament` advisory guard. `VOICE-EVAL` gains a stdlib `liveness` module (nPVI + composite) and wiring in `voice_eval`. A run-once tool in `tools/build-longfellow-corpus/` reaches the network only through scrapling-fetch and emits an index of verified public-domain Longfellow snippets that the prompts cite.

**Tech Stack:** Python 3.11 stdlib (`re`, `statistics`); spaCy 3 only via existing linters (lazy-imported, gated); pytest; scrapling-fetch (dev-time subprocess only). The `[ci]` extra omits the spaCy model, so all new modules and the test files added by this plan must import without it.

**Spec:** `openspec/changes/add-longfellow-liveness/` + `docs/specs/2026-05-27-longfellow-liveness-design.md`.

**Branch / worktree:** Already on `feat/longfellow-liveness` in `~/.config/superpowers/worktrees/russellian-book-suite/feat-longfellow-liveness`, off `origin/main`. The parallel agent's checkout is untouched.

---

## CI / test naming gotcha (read once)

`skills/russellian-style/tests/conftest.py` sets `collect_ignore_glob = ["test_lint_*.py", ...]` when the spaCy model is absent. The CI `[ci]` extra omits the model. Consequence: **a test file named `test_lint_ornament.py` would be silently skipped in CI**, defeating the point of a spaCy-free linter being CI-tested. Name the ornament linter's test file `test_ornament.py` (no `test_lint_` prefix). The same applies to `test_liveness.py` and `test_system_prompt_liveness.py` (neither is `test_lint_*`).

For tests that *do* exercise spaCy-backed linters (i.e., anything calling `voice_eval.evaluate` on real text), keep them in `test_voice_eval.py` and guard with `@pytest.mark.skipif(not _spacy_model_available(), ...)` — the established pattern.

All test files in `skills/russellian-style/tests/` carry `pytestmark = pytest.mark.windows_canary`.

The russellian-style venv is at `skills/russellian-style/.venv/`. POSIX: `.venv/bin/python`; Windows: `.venv\Scripts\python.exe`. The commands below show Windows form; substitute as needed.

---

## File map

| File | New / Mod | Capability | Owner task |
|---|---|---|---|
| `skills/russellian-style/scripts/liveness.py` | new | VOICE-EVAL | Tasks 1, 2 |
| `skills/russellian-style/tests/test_liveness.py` | new | VOICE-EVAL | Tasks 1, 2 |
| `skills/russellian-style/scripts/lint_ornament.py` | new | VOICE | Task 3 |
| `skills/russellian-style/tests/test_ornament.py` | new | VOICE | Task 3 |
| `skills/russellian-style/scripts/voice_eval.py` | mod | VOICE-EVAL | Task 4 |
| `skills/russellian-style/tests/test_voice_eval.py` | mod | VOICE-EVAL | Task 4 |
| `skills/russellian-style/SKILL.md` | mod | VOICE | Task 4 |
| `tools/build-longfellow-corpus/build_longfellow_corpus.py` | new | (tool) | Task 5 |
| `tools/build-longfellow-corpus/test_segment.py` | new | (tool) | Task 5 |
| `tools/build-longfellow-corpus/README.md` | new | (tool) | Task 5 |
| `skills/russellian-style/assets/longfellow-corpus/index.json` | new | VOICE | Task 5 |
| `skills/russellian-style/references/longfellow-liveness-map.md` | new | VOICE | Task 6 |
| `skills/russellian-style/assets/system-prompts/technical-exposition.md` | mod | VOICE | Task 7 |
| `skills/russellian-style/assets/system-prompts/narrative-editorial.md` | mod | VOICE | Task 7 |
| `skills/russellian-style/assets/system-prompts/polemic.md` | mod | VOICE | Task 7 |
| `skills/russellian-style/tests/test_system_prompt_liveness.py` | new | VOICE | Task 7 |
| `docs/audits/2026-05-27-longfellow-liveness-before-after/` | new | (audit) | Task 8 |
| `openspec/changes/add-longfellow-liveness/tasks.md` | new | (OpenSpec) | Task 9 |

Each task is independently committable. Commits are terse, human-style, no AI attribution (CLAUDE.md / repo convention).

---

### Task 1: nPVI cadence signal (`liveness.py`)

REQ-VEVAL-009 (order-sensitive cadence, stdlib, sentence-length floor).

**Files:**
- Create: `skills/russellian-style/scripts/liveness.py`
- Create: `skills/russellian-style/tests/test_liveness.py`

- [ ] **Step 1: Write the failing test**

Create `skills/russellian-style/tests/test_liveness.py`:

```python
"""Cites REQ-VEVAL-009. nPVI is the order-sensitive cadence signal that the Fano
factor cannot supply (Fano is permutation-invariant on sentence lengths)."""
import pytest

pytestmark = pytest.mark.windows_canary

from scripts.liveness import npvi


def test_alternating_lengths_score_higher_than_uniform():
    uniform = " ".join([
        "This sentence carries exactly fourteen words and lands inside the suspect AI band cleanly.",
        "Another sentence of fifteen words again sits inside the same narrow predictable AI band.",
        "Yet another sentence of thirteen words drops squarely inside the AI signature band today.",
    ])
    alternating = " ".join([
        "A short opener arrives first.",
        "A much longer sentence follows, building up clauses, taking its time, reaching across many words before resolving on the final beat.",
        "Short again.",
        "And once more a long sentence stretches itself out, accumulating modifiers and weight, until it lands.",
    ])
    assert npvi(alternating) > npvi(uniform)


def test_single_qualifying_sentence_returns_zero():
    assert npvi("This is one sentence with more than four words.") == 0.0


def test_below_floor_fragments_are_ignored():
    # "Yes." / "No." stuffing must not inflate cadence; the floor (default 4) drops them.
    text = " ".join([
        "Yes.", "No.", "Indeed.",
        "A genuine sentence with comfortably more than four words to clear the floor here.",
        "Another genuine sentence with comfortably more than four words to clear the floor again.",
    ])
    assert npvi(text) == 0.0  # only 2 qualifying sentences of similar length -> low contrast


def test_determinism():
    text = "A short sentence here. A markedly longer one trailing across more words to vary the cadence."
    assert npvi(text) == npvi(text)
```

- [ ] **Step 2: Run the test to verify it fails**

```
cd skills/russellian-style && .venv\Scripts\python.exe -m pytest tests/test_liveness.py -v
```

Expected: `ModuleNotFoundError: No module named 'scripts.liveness'` (or collection error).

- [ ] **Step 3: Write the minimal implementation**

Create `skills/russellian-style/scripts/liveness.py`:

```python
"""Order-sensitive liveness signals (stdlib only; no spaCy, no lint_common).

nPVI (normalized pairwise variability index; Grabe & Low 2002) measures adjacent-
sentence length contrast — the ordering that the Fano factor throws away.

liveness_summary composes nPVI with paragraph-motion variety and concrete-instance
density, minus an ornament penalty. The result is advisory telemetry, not a verdict;
qualitative judgement of improvement belongs to the reading-council A/B.
"""
from __future__ import annotations

import re


DEFAULT_MIN_WORDS = 4  # ignore fragments so "Yes." stuffing cannot inflate cadence


def _qualifying_lengths(text: str, min_words: int) -> list[int]:
    sents = [s for s in re.split(r"[.!?]+", text) if s.strip()]
    lengths = [len(re.findall(r"[A-Za-z']+", s)) for s in sents]
    return [n for n in lengths if n >= min_words]


def npvi(text: str, min_words: int = DEFAULT_MIN_WORDS) -> float:
    """Normalized pairwise variability index of sentence lengths.

    0 means perfectly even; higher means more adjacent-pair contrast. Sentences with
    fewer than ``min_words`` words are dropped so fragment-stuffing cannot inflate the
    score.
    """
    lengths = _qualifying_lengths(text, min_words)
    if len(lengths) < 2:
        return 0.0
    total = 0.0
    pairs = 0
    for a, b in zip(lengths, lengths[1:]):
        denom = (a + b) / 2.0
        if denom > 0:
            total += abs(a - b) / denom
            pairs += 1
    if pairs == 0:
        return 0.0
    return round(100.0 * total / pairs, 2)
```

- [ ] **Step 4: Run the test to verify it passes**

```
cd skills/russellian-style && .venv\Scripts\python.exe -m pytest tests/test_liveness.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```
git add skills/russellian-style/scripts/liveness.py skills/russellian-style/tests/test_liveness.py
git commit -m "Add nPVI cadence signal for voice-liveness"
```

---

### Task 2: Liveness composite (`liveness_summary` in `liveness.py`)

REQ-VEVAL-010 (compose existing signals minus ornament penalty; no new burstiness/concrete re-implementation), REQ-VEVAL-012 (telemetry only — no "beats baseline" claim).

**Files:**
- Modify: `skills/russellian-style/scripts/liveness.py` (add `liveness_summary`)
- Modify: `skills/russellian-style/tests/test_liveness.py` (add composite tests)

- [ ] **Step 1: Write the failing tests**

Append to `skills/russellian-style/tests/test_liveness.py`:

```python
from scripts.liveness import liveness_summary


def test_summary_keys_and_advisory_flag():
    s = liveness_summary(npvi_value=60.0, motion_variety=0.5,
                         concrete_per_1000=4.0, ornament_per_1000=0.0)
    assert s["metric"] == "liveness"
    assert s["advisory"] is True
    assert set(s["components"]) == {"cadence", "motion", "concreteness", "ornament_penalty"}
    assert 0.0 <= s["liveness"] <= 1.0


def test_more_ornament_lowers_liveness():
    base = liveness_summary(60.0, 0.5, 4.0, ornament_per_1000=0.0)["liveness"]
    pen = liveness_summary(60.0, 0.5, 4.0, ornament_per_1000=10.0)["liveness"]
    assert pen < base


def test_higher_npvi_raises_cadence_component():
    low = liveness_summary(10.0, 0.5, 4.0, 0.0)["components"]["cadence"]
    high = liveness_summary(80.0, 0.5, 4.0, 0.0)["components"]["cadence"]
    assert high > low


def test_liveness_floored_at_zero():
    s = liveness_summary(0.0, 0.0, 0.0, ornament_per_1000=999.0)
    assert s["liveness"] == 0.0


def test_summary_deterministic():
    args = dict(npvi_value=55.0, motion_variety=0.4, concrete_per_1000=3.0, ornament_per_1000=1.0)
    assert liveness_summary(**args) == liveness_summary(**args)
```

- [ ] **Step 2: Run the tests to verify they fail**

```
cd skills/russellian-style && .venv\Scripts\python.exe -m pytest tests/test_liveness.py -v
```

Expected: 5 new tests fail with `ImportError: cannot import name 'liveness_summary'`.

- [ ] **Step 3: Add `liveness_summary` to `liveness.py`**

Append to `skills/russellian-style/scripts/liveness.py`:

```python
# --- Composite (advisory telemetry; not a verdict) ----------------------------------

# Normalization constants are calibration parameters, not thresholds. nPVI in the
# 50-80 band is "lively" per the prose-rhythm literature (Grabe & Low 2002 applied
# to sentence lengths); 60 is the midpoint. Concrete-density 8/1000 is the upper
# practical band observed in Russell's analytic prose. Ornament penalty caps at 0.5
# so a single decoration finding cannot zero out an otherwise lively passage.
_CADENCE_DENOM = 60.0
_CONCRETE_DENOM = 8.0
_ORNAMENT_DENOM = 10.0
_ORNAMENT_CAP = 0.5


def liveness_summary(npvi_value: float, motion_variety: float,
                     concrete_per_1000: float, ornament_per_1000: float) -> dict:
    """Compose advisory liveness telemetry. Not a verdict.

    Components normalize to roughly 0..1; ornament subtracts. The numbers describe;
    the reading-council A/B judges whether the writing is actually livelier.
    """
    cadence = round(min(max(npvi_value, 0.0) / _CADENCE_DENOM, 1.0), 3)
    motion = round(min(max(motion_variety, 0.0), 1.0), 3)
    concreteness = round(min(max(concrete_per_1000, 0.0) / _CONCRETE_DENOM, 1.0), 3)
    penalty = round(min(max(ornament_per_1000, 0.0) / _ORNAMENT_DENOM, _ORNAMENT_CAP), 3)
    liveness = round(max(0.0, (cadence + motion + concreteness) / 3.0 - penalty), 3)
    return {
        "metric": "liveness",
        "liveness": liveness,
        "components": {
            "cadence": cadence,
            "motion": motion,
            "concreteness": concreteness,
            "ornament_penalty": penalty,
        },
        "advisory": True,
    }
```

- [ ] **Step 4: Run the tests to verify they pass**

```
cd skills/russellian-style && .venv\Scripts\python.exe -m pytest tests/test_liveness.py -v
```

Expected: all 9 tests pass (4 from Task 1 + 5 from Task 2).

- [ ] **Step 5: Commit**

```
git add skills/russellian-style/scripts/liveness.py skills/russellian-style/tests/test_liveness.py
git commit -m "Add liveness composite over nPVI + motion + concreteness minus ornament"
```

---

### Task 3: Ornament linter (`lint_ornament.py`)

REQ-VOICE-013 (markers), REQ-VOICE-014 (no spaCy, no lint_common), REQ-VOICE-015 (advisory).

**Files:**
- Create: `skills/russellian-style/scripts/lint_ornament.py`
- Create: `skills/russellian-style/tests/test_ornament.py`  *(not `test_lint_*` — see CI gotcha)*
- Modify: `skills/russellian-style/SKILL.md` (add to Linters list)

- [ ] **Step 1: Write the failing tests**

Create `skills/russellian-style/tests/test_ornament.py`:

```python
"""Cites REQ-VOICE-013, REQ-VOICE-014, REQ-VOICE-015.

Named test_ornament.py (NOT test_lint_*) so the conftest's spaCy-absent
collect_ignore_glob does not silently skip it in CI.
"""
import pytest

pytestmark = pytest.mark.windows_canary

from pathlib import Path

from scripts.lint_ornament import lint_ornament


def _write(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "draft.md"
    p.write_text(text, encoding="utf-8")
    return p


def test_archaic_diction_flagged(tmp_path):
    findings = lint_ornament(_write(tmp_path, "He gazed o'er the lea where 'tis ever still."))
    markers = {f["marker"] for f in findings}
    assert "archaic_diction" in markers
    assert all(f["severity"] == "advisory" for f in findings)


def test_apostrophe_flagged_when_unquoted(tmp_path):
    findings = lint_ornament(_write(tmp_path, "O Reader, attend. The argument proceeds by cases."))
    assert any(f["marker"] == "apostrophe" for f in findings)


def test_apostrophe_inside_quotes_not_flagged(tmp_path):
    findings = lint_ornament(_write(tmp_path, 'He cried, "O Reader, attend!" The argument proceeds.'))
    assert not any(f["marker"] == "apostrophe" for f in findings)


def test_archaism_inside_blockquote_not_flagged(tmp_path):
    text = "Russell wrote plainly. Longfellow did not:\n\n> O'er the lea where 'tis ever still.\n\nThe distinction is the point."
    findings = lint_ornament(_write(tmp_path, text))
    assert not any(f["marker"] == "archaic_diction" for f in findings)


def test_clean_russell_sentence_produces_no_findings(tmp_path):
    text = (
        "Philosophy is to be studied not for definite answers but for the questions themselves. "
        "The argument proceeds by cases. We begin with the table in this room."
    )
    findings = lint_ornament(_write(tmp_path, text))
    assert findings == []


def test_advisory_severity_only(tmp_path):
    text = "O'er the lea, O Reader, the storm raged as if in sympathy with our sorrow."
    findings = lint_ornament(_write(tmp_path, text))
    assert findings, "expect at least one finding"
    assert all(f["severity"] == "advisory" for f in findings)


def test_determinism(tmp_path):
    text = "O'er the lea. O Reader, attend."
    p = _write(tmp_path, text)
    assert lint_ornament(p) == lint_ornament(p)
```

- [ ] **Step 2: Run the tests to verify they fail**

```
cd skills/russellian-style && .venv\Scripts\python.exe -m pytest tests/test_ornament.py -v
```

Expected: `ModuleNotFoundError: No module named 'scripts.lint_ornament'`.

- [ ] **Step 3: Write the minimal implementation**

Create `skills/russellian-style/scripts/lint_ornament.py`:

```python
"""Ornament linter: flags purple-prose markers that distinguish decorative from lively.

Pure stdlib + re. Imports nothing from lint_common (which loads spaCy at module top)
so this module loads and runs under the CI [ci] extra without the spaCy model.

Quoted spans (double-quoted, curly-quoted, and markdown blockquotes) are removed
before scanning so the linter does not penalize quoting or discussing ornate sources.
Severity is advisory; the tier records internal strength for the report only.
"""
from __future__ import annotations

import json
import re
from pathlib import Path


_ARCHAIC = re.compile(
    r"\b(o'er|'tis|'twas|thee|thou|thy|thine|doth|hath|ere|'neath|'gainst|nay)\b",
    re.IGNORECASE,
)

# "O Reader,", "O, Time" at sentence boundaries. Avoids matching the letter O in
# ordinary words by requiring sentence-initial position and a following capital.
_APOSTROPHE = re.compile(r"(?:^|[.!?]\s+)O[, ]+[A-Z][a-z]")

_STRONG_VERBS = ("roared", "shouted", "whispered", "screamed", "blazed", "raced",
                 "sprinted", "glared", "thundered", "bellowed")
_ADVERB_STRONG_VERB = re.compile(
    r"\b\w+ly\s+(" + "|".join(_STRONG_VERBS) + r")\b", re.IGNORECASE
)

_EMOTION_WORDS = ("sorrow", "grief", "despair", "longing", "rapture", "melancholy",
                  "anguish", "yearning", "woe")
# Match the word in subject/object position (bare nominal use), not in compounds.
_EMOTION_RE = re.compile(
    r"(?:^|[\s,;])(" + "|".join(_EMOTION_WORDS) + r")(?=[\s,.;!?])", re.IGNORECASE
)

_EVALUATIVE = ("beautiful", "lovely", "gorgeous", "exquisite", "magnificent",
               "glorious", "radiant", "dazzling", "sublime", "delicate", "tender",
               "wondrous", "ethereal")
_ADJ_STACK = re.compile(
    r"\b(" + "|".join(_EVALUATIVE) + r")\b[,\s]+(?:and\s+)?\b("
    + "|".join(_EVALUATIVE) + r")\b",
    re.IGNORECASE,
)

# "the storm raged, as if in sympathy / protest / grief / sorrow / anger / joy"
_NATURE_MOOD = re.compile(
    r"\bas if (?:in|the)\b[^.!?]{0,40}\b(sympathy|protest|grief|sorrow|anger|joy)\b",
    re.IGNORECASE,
)


def _strip_quotes(text: str) -> str:
    # Drop double-quoted spans, curly-quoted spans, and markdown blockquote lines.
    text = re.sub(r'"[^"\n]*"', " ", text)
    text = re.sub(r"“[^”\n]*”", " ", text)
    text = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith(">"))
    return text


def _tier(marker: str) -> str:
    # "Important" tiers carry to the report; "advisory" stays severity-advisory
    # regardless (REQ-VOICE-015). All vitality linters are advisory in v1.
    if marker in {"archaic_diction", "apostrophe"}:
        return "important"
    return "advisory"


def lint_ornament(path: Path) -> list[dict]:
    raw = Path(path).read_text(encoding="utf-8")
    text = _strip_quotes(raw)
    findings: list[dict] = []

    def _add(marker: str, count: int) -> None:
        if count <= 0:
            return
        findings.append({
            "rule": "ornament",
            "marker": marker,
            "count": count,
            "tier": _tier(marker),
            "severity": "advisory",
        })

    _add("archaic_diction", len(_ARCHAIC.findall(text)))
    _add("apostrophe", len(_APOSTROPHE.findall(text)))
    _add("adverb_amplified_verb", len(_ADVERB_STRONG_VERB.findall(text)))
    _add("abstract_emotion_word", len(_EMOTION_RE.findall(text)))
    _add("adjective_stacking", len(_ADJ_STACK.findall(text)))
    _add("nature_mirrors_mood", len(_NATURE_MOOD.findall(text)))
    return findings


if __name__ == "__main__":
    import sys
    print(json.dumps(lint_ornament(Path(sys.argv[1])), indent=2))
```

- [ ] **Step 4: Run the tests to verify they pass**

```
cd skills/russellian-style && .venv\Scripts\python.exe -m pytest tests/test_ornament.py -v
```

Expected: 7 passed.

- [ ] **Step 5: Add the linter to SKILL.md**

Edit `skills/russellian-style/SKILL.md`. In the `## Linters` section (after the existing `lint_listicle_abstract.py` bullet), append:

```markdown
- `scripts/lint_ornament.py` — purple-prose markers (archaism, apostrophe, adjective stacking, adverb-amplified verbs, abstract emotion words, nature-mirrors-mood); pure-regex, quote-excluding, advisory.
```

- [ ] **Step 6: Commit**

```
git add skills/russellian-style/scripts/lint_ornament.py skills/russellian-style/tests/test_ornament.py skills/russellian-style/SKILL.md
git commit -m "Add lint_ornament: advisory decoration guard, regex-only"
```

---

### Task 4: Wire nPVI, ornament, and liveness composite into `voice_eval`

REQ-VEVAL-009, REQ-VEVAL-010, REQ-VEVAL-011, REQ-VEVAL-012, REQ-VEVAL-013, REQ-VEVAL-014.

**Files:**
- Modify: `skills/russellian-style/scripts/voice_eval.py`
- Modify: `skills/russellian-style/tests/test_voice_eval.py`

- [ ] **Step 1: Write the failing tests**

Append to `skills/russellian-style/tests/test_voice_eval.py` (after the existing imports — note `_spacy_model_available` and `requires_spacy` already exist in that file):

```python
def test_write_report_includes_liveness_telemetry(tmp_path):
    """No-spaCy unit test: write_report renders the liveness section from a hand-built
    report dict. Confirms REQ-VEVAL-010/011/012 surface in the bundle without invoking
    the full linter battery."""
    from scripts.voice_eval import write_report
    report = {
        "meta": {"topic": "x", "mode": "polemic", "n_requested": 3},
        "generated_text": "Sample.",
        "generated": {
            "russell_delta": {"metric": "russell-burrows-delta", "delta": 0.7,
                              "verdict": "within Russell's range",
                              "band": {"p10": 0.6, "p50": 0.7, "p90": 0.8}},
            "n_words": 80,
            "linters": {"ornament": {"count": 0, "per_1000": 0.0}},
            "liveness": {"metric": "liveness", "liveness": 0.55,
                         "components": {"cadence": 0.7, "motion": 0.5,
                                        "concreteness": 0.45, "ornament_penalty": 0.0},
                         "advisory": True},
        },
        "baseline": {
            "russell_delta": {"metric": "russell-burrows-delta", "delta": 0.69,
                              "verdict": "within Russell's range",
                              "band": {"p10": 0.6, "p50": 0.7, "p90": 0.8}},
            "n_words": 80,
            "linters": {"ornament": {"count": 0, "per_1000": 0.0}},
            "liveness": {"metric": "liveness", "liveness": 0.40,
                         "components": {"cadence": 0.45, "motion": 0.4,
                                        "concreteness": 0.35, "ornament_penalty": 0.0},
                         "advisory": True},
        },
    }
    out = tmp_path / "r.md"
    write_report(report, out)
    md = out.read_text(encoding="utf-8")
    assert "## Liveness" in md
    assert "advisory telemetry" in md.lower()
    assert "0.55" in md and "0.40" in md
    # REQ-VEVAL-012: no "beats baseline" claim.
    assert "beats" not in md.lower()


@requires_spacy
def test_evaluate_emits_liveness_block():
    from scripts.voice_eval import evaluate
    text = "Philosophy is studied for the questions. The argument proceeds by cases. " * 30
    rep = evaluate(text)
    lv = rep["generated"]["liveness"]
    assert lv["metric"] == "liveness"
    assert set(lv["components"]) == {"cadence", "motion", "concreteness", "ornament_penalty"}
    assert lv["advisory"] is True
    # ornament linter is now part of the battery
    assert "ornament" in rep["generated"]["linters"]
```

- [ ] **Step 2: Run the tests to verify they fail**

```
cd skills/russellian-style && .venv\Scripts\python.exe -m pytest tests/test_voice_eval.py::test_write_report_includes_liveness_telemetry tests/test_voice_eval.py::test_evaluate_emits_liveness_block -v
```

Expected: both fail (no `liveness` key; no `## Liveness` section).

- [ ] **Step 3: Update `voice_eval.py`**

Edit `skills/russellian-style/scripts/voice_eval.py`:

**3a.** Add `re` to the stdlib imports near the top, and add the liveness imports below the existing top-level imports. Change:

```python
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Callable, Optional

from scripts.system_prompt_loader import load as load_prompt, VALID_MODES
```

to:

```python
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Callable, Optional

from scripts.system_prompt_loader import load as load_prompt, VALID_MODES
from scripts.liveness import npvi, liveness_summary
```

**3b.** Add `lint_ornament` to the lazy `_linters()` dict. Inside `_linters()`, add the import and dict entry:

```python
    from scripts.lint_ornament import lint_ornament
```

and in the returned dict:

```python
        "ornament": lint_ornament,
```

**3c.** Add the motion-variety helper just above `_signals`:

```python
def _motion_variety(text: str) -> float:
    """Distinct paragraph shapes / total paragraphs, via lint_paragraph_motion's
    stdlib classifier (no spaCy)."""
    from scripts.lint_paragraph_motion import classify_paragraph
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if not paras:
        return 0.0
    shapes = {classify_paragraph(p) for p in paras}
    return round(len(shapes) / len(paras), 3)
```

**3d.** Extend `_signals` to compute and return liveness telemetry. Replace the existing `return {...}` line with:

```python
    motion_variety = _motion_variety(text)
    concrete_per_1000 = linters.get("concrete_instance_density", {}).get("per_1000", 0.0)
    ornament_per_1000 = linters.get("ornament", {}).get("per_1000", 0.0)
    liveness = liveness_summary(npvi(text), motion_variety, concrete_per_1000, ornament_per_1000)
    return {"russell_delta": delta, "n_words": n_words, "linters": linters, "liveness": liveness}
```

**3e.** Add a liveness section to `write_report`. Just above the `lines += ["", "## Linter densities (per 1,000 words)", ...]` line, insert:

```python
    def _liveness_line(sig: dict) -> str:
        lv = sig["liveness"]
        c = lv["components"]
        return (f"liveness={lv['liveness']} (cadence={c['cadence']} motion={c['motion']} "
                f"concreteness={c['concreteness']} ornament_penalty={c['ornament_penalty']})")

    lines += ["", "## Liveness (advisory telemetry — not a verdict)", "",
              f"- generated: {_liveness_line(gen)}"]
    if base:
        lines.append(f"- russell baseline: {_liveness_line(base)}")
```

- [ ] **Step 4: Run the new tests, then the full voice_eval suite**

```
cd skills/russellian-style && .venv\Scripts\python.exe -m pytest tests/test_voice_eval.py -v
```

Expected: all tests pass — the new no-spaCy test passes unconditionally; the new spaCy-gated test passes (or is skipped on CI legs without the model, consistent with the existing `@requires_spacy` tests).

- [ ] **Step 5: Commit**

```
git add skills/russellian-style/scripts/voice_eval.py skills/russellian-style/tests/test_voice_eval.py
git commit -m "Wire ornament linter and liveness composite into voice_eval"
```

---

### Task 5: Longfellow corpus tool + committed index

REQ-VOICE-012 (verbatim+attributed for public-domain Longfellow only). The tool reaches the network only through scrapling-fetch (the suite's network boundary). Building the index is run-once; CI tests only the offline pieces.

**Files:**
- Create: `tools/build-longfellow-corpus/__init__.py` (empty)
- Create: `tools/build-longfellow-corpus/build_longfellow_corpus.py`
- Create: `tools/build-longfellow-corpus/test_segment.py`
- Create: `tools/build-longfellow-corpus/README.md`
- Create: `skills/russellian-style/assets/longfellow-corpus/index.json` (committed artifact)

- [ ] **Step 1: Write the failing offline segmentation test**

Create `tools/build-longfellow-corpus/__init__.py` (empty file):

```
```

Create `tools/build-longfellow-corpus/test_segment.py`:

```python
"""Offline tests for the poetry-aware segmentation. No network.

The actual scrapling-driven build is run-once by the orchestrator and not exercised
in CI (network-using; the suite's network boundary is scrapling-fetch).
"""
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

from build_longfellow_corpus import segment_stanzas, build_index


VERSE = """\
Should you ask me, whence these stories?
Whence these legends and traditions,
With the odors of the forest,
With the dew and damp of meadows?

Dark behind it rose the forest,
Rose the black and gloomy pine-trees,
Rose the firs with cones upon them;
Bright before it beat the water,
Beat the clear and sunny water,
Beat the shining Big-Sea-Water.

(single line block ignored)
"""


def test_segment_returns_only_multiline_stanzas():
    stanzas = segment_stanzas(VERSE, min_lines=2)
    assert len(stanzas) == 2
    assert stanzas[0].startswith("Should you ask me")
    assert "single line" not in stanzas[1]


def test_segment_preserves_line_breaks():
    stanzas = segment_stanzas(VERSE, min_lines=2)
    assert "\n" in stanzas[0]
    assert stanzas[0].count("\n") == 3  # 4 lines, 3 line breaks


def test_segment_drops_heading_blocks():
    text = "# Chapter I\n\nDark behind it rose the forest,\nBright before it beat the water,\n"
    stanzas = segment_stanzas(text)
    assert all(not s.startswith("#") for s in stanzas)
    assert len(stanzas) == 1


def test_build_index_shape():
    sources = {
        "hiawatha": {"title": "The Song of Hiawatha",
                     "url": "https://www.gutenberg.org/ebooks/19",
                     "copyright_status": "public_domain_us"},
    }
    anchors = [{
        "id": "hiawatha-antithesis",
        "source": "hiawatha",
        "locator": "Hiawatha's Childhood",
        "snippet": "Dark behind it rose the forest, / Bright before it beat the water",
        "technique": "antithetical spatial parallelism",
        "prose_translation": "two sentences with mirrored skeletons holding contrasting claims",
        "tags": ["cadence", "antithesis"],
    }]
    idx = build_index(sources, anchors, version="0.1.0")
    assert idx["version"] == "0.1.0"
    assert idx["donor"].startswith("Henry Wadsworth Longfellow")
    assert "copyright_policy" in idx
    assert idx["sources"] == sources
    assert idx["anchors"] == anchors
```

- [ ] **Step 2: Run the segmentation test to verify it fails**

```
cd /c/Users/charl/.config/superpowers/worktrees/russellian-book-suite/feat-longfellow-liveness && /c/russellian-book-suite/skills/russellian-style/.venv/Scripts/python.exe -m pytest tools/build-longfellow-corpus/test_segment.py -v
```

(Use any python with stdlib; the tests are stdlib-only.) Expected: `ModuleNotFoundError: No module named 'build_longfellow_corpus'`.

- [ ] **Step 3: Implement the tool**

Create `tools/build-longfellow-corpus/build_longfellow_corpus.py`:

```python
"""Build a study corpus of public-domain Longfellow stanzas with verified snippets.

Two responsibilities:

1. Pure, stdlib-only: poetry-aware segmentation (`segment_stanzas`) and index
   assembly (`build_index`). Offline and CI-testable.

2. Network: `fetch_work_markdown(url)` reaches scrapling-fetch by subprocess (the
   suite's network boundary, per scrapling-fetch/SKILL.md). Run-once by the
   orchestrator; not exercised in CI.

The committed artifact is `skills/russellian-style/assets/longfellow-corpus/index.json`.
Tests assert the schema of that artifact; the network step is performed manually.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path


COPYRIGHT_POLICY = (
    "Public-domain (US) source. Short verified verse snippets are stored for anchor "
    "use; cite the source URL and locator (canto, line group) in any report. "
    "Borrow cadence and image-logic only — never meter, rhyme, archaism, or sentiment."
)


def segment_stanzas(markdown: str, min_lines: int = 2) -> list[str]:
    """Split verse markdown into stanzas, preserving line breaks within each.

    A stanza is a blank-line-separated block of at least ``min_lines`` non-empty lines
    that does not begin with a markdown heading. Whitespace inside each line is
    preserved so meter is visible.
    """
    stanzas: list[str] = []
    for block in re.split(r"\n\s*\n", markdown):
        lines = [l for l in block.splitlines() if l.strip()]
        if len(lines) < min_lines:
            continue
        if lines[0].lstrip().startswith("#"):
            continue
        stanzas.append("\n".join(l.strip() for l in lines))
    return stanzas


def build_index(sources: dict, anchors: list, version: str = "0.1.0") -> dict:
    """Assemble the index.json content from verified sources and curated anchors."""
    return {
        "version": version,
        "donor": "Henry Wadsworth Longfellow (public domain)",
        "copyright_policy": COPYRIGHT_POLICY,
        "sources": sources,
        "anchors": anchors,
    }


# --- Network entry point (run-once by orchestrator; not part of CI) ----------------

def fetch_work_markdown(url: str, *,
                        scrapling_root: str | None = None,
                        scrapling_python: str | None = None) -> str:
    """Fetch a Gutenberg work through scrapling-fetch and return clean markdown.

    Requires scrapling-fetch installed in a venv. The orchestrator passes either both
    arguments or sets env vars ``SCRAPLING_FETCH_ROOT`` (the skill's directory) and
    ``SCRAPLING_FETCH_PYTHON`` (its venv python).
    """
    scrapling_root = scrapling_root or os.environ.get("SCRAPLING_FETCH_ROOT")
    scrapling_python = scrapling_python or os.environ.get("SCRAPLING_FETCH_PYTHON")
    if not scrapling_root or not scrapling_python:
        raise RuntimeError(
            "Provide scrapling_root / scrapling_python (or env vars "
            "SCRAPLING_FETCH_ROOT / SCRAPLING_FETCH_PYTHON)."
        )
    snippet = (
        "import sys; from scripts.fetch import fetch; "
        "from scripts.extract import html_to_markdown; "
        "page = fetch(sys.argv[1], mode='plain'); "
        "sys.stdout.write(html_to_markdown(page.html, sys.argv[1]))"
    )
    result = subprocess.run(
        [scrapling_python, "-c", snippet, url],
        cwd=scrapling_root, check=True, capture_output=True, text=True,
    )
    return result.stdout


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[1] not in ("fetch", "build"):
        print("usage: build_longfellow_corpus.py fetch <url> > work.md\n"
              "       build_longfellow_corpus.py build <sources.json> <anchors.json> <out.json>",
              file=sys.stderr)
        return 2
    if argv[1] == "fetch":
        sys.stdout.write(fetch_work_markdown(argv[2]))
        return 0
    sources = json.loads(Path(argv[2]).read_text(encoding="utf-8"))
    anchors = json.loads(Path(argv[3]).read_text(encoding="utf-8"))
    idx = build_index(sources, anchors)
    Path(argv[4]).write_text(json.dumps(idx, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {argv[4]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
```

- [ ] **Step 4: Run the offline tests to verify they pass**

```
cd /c/Users/charl/.config/superpowers/worktrees/russellian-book-suite/feat-longfellow-liveness && /c/russellian-book-suite/skills/russellian-style/.venv/Scripts/python.exe -m pytest tools/build-longfellow-corpus/test_segment.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Run the tool to fetch and curate the index (orchestrator step, network)**

This is the network step. From the worktree root, with scrapling-fetch available:

```
$env:SCRAPLING_FETCH_ROOT="C:\russellian-book-suite\skills\scrapling-fetch"
$env:SCRAPLING_FETCH_PYTHON="C:\russellian-book-suite\skills\scrapling-fetch\.venv\Scripts\python.exe"
.venv\Scripts\python.exe tools\build-longfellow-corpus\build_longfellow_corpus.py fetch https://www.gutenberg.org/cache/epub/19/pg19-images.html > C:\tmp\hiawatha.md
.venv\Scripts\python.exe tools\build-longfellow-corpus\build_longfellow_corpus.py fetch https://www.gutenberg.org/cache/epub/2039/pg2039-images.html > C:\tmp\evangeline.md
```

(Add `tales-of-a-wayside-inn` Gutenberg #1365 and `miles-standish` #6608 likewise.) Then inspect with `segment_stanzas` to select the four-to-eight anchors below, verifying each snippet appears verbatim in the fetched markdown.

- [ ] **Step 6: Write the curated `sources.json` and `anchors.json` and build the index**

Each anchor's `snippet` must appear verbatim in the corresponding fetched markdown (verified by the orchestrator before committing).

Create `C:\tmp\longfellow-sources.json`:

```json
{
  "hiawatha": {
    "title": "The Song of Hiawatha",
    "url": "https://www.gutenberg.org/cache/epub/19/pg19-images.html",
    "copyright_status": "public_domain_us"
  },
  "evangeline": {
    "title": "Evangeline: A Tale of Acadie",
    "url": "https://www.gutenberg.org/cache/epub/2039/pg2039-images.html",
    "copyright_status": "public_domain_us"
  },
  "wayside-inn": {
    "title": "Tales of a Wayside Inn",
    "url": "https://www.gutenberg.org/cache/epub/1365/pg1365-images.html",
    "copyright_status": "public_domain_us"
  },
  "miles-standish": {
    "title": "The Courtship of Miles Standish",
    "url": "https://www.gutenberg.org/cache/epub/6608/pg6608-images.html",
    "copyright_status": "public_domain_us"
  }
}
```

Create `C:\tmp\longfellow-anchors.json` with the following structure (verify each `snippet` against the fetched markdown before committing):

```json
[
  {
    "id": "hiawatha-antithesis",
    "source": "hiawatha",
    "locator": "Introduction / Hiawatha's Childhood",
    "snippet": "Dark behind it rose the forest, / Rose the black and gloomy pine-trees, / Rose the firs with cones upon them; / Bright before it beat the water, / Beat the clear and sunny water, / Beat the shining Big-Sea-Water.",
    "technique": "antithetical spatial parallelism with verb repetition",
    "prose_translation": "Two sentences with mirrored skeletons hold contrasting claims; the verb is repeated to mark the pulse; drop the meter and the rhyme.",
    "tags": ["cadence", "antithesis", "parallelism"]
  },
  {
    "id": "hiawatha-catalog",
    "source": "hiawatha",
    "locator": "Hiawatha's Childhood",
    "snippet": "Saw the wild rice, Mahnomonee, / Saw the blueberry, Meenahga, / And the strawberry, Odahmin",
    "technique": "specific-named enumeration with polysyndeton",
    "prose_translation": "When listing items that support a claim, name them exactly — proper names, technical names, exact quantities — and use repeated 'and' to make the weight of the list felt.",
    "tags": ["concreteness", "enumeration"]
  },
  {
    "id": "hiawatha-anaphora",
    "source": "hiawatha",
    "locator": "Introduction",
    "snippet": "Should you ask me, whence these stories? / Whence these legends and traditions",
    "technique": "rhetorical-question opening with anaphora",
    "prose_translation": "Open a section with the question you are about to resolve, in the reader's voice; repeat the wh-word once to mark the structure.",
    "tags": ["momentum", "anaphora"]
  },
  {
    "id": "evangeline-primeval",
    "source": "evangeline",
    "locator": "Prologue",
    "snippet": "This is the forest primeval. The murmuring pines and the hemlocks",
    "technique": "deictic anchor — name the scene, then particularize",
    "prose_translation": "State the claim concretely in the first sentence; in the second, name the two specific instances that make it visible.",
    "tags": ["concreteness", "knot-and-resolution"]
  }
]
```

Then build the index:

```
.venv\Scripts\python.exe tools\build-longfellow-corpus\build_longfellow_corpus.py build C:\tmp\longfellow-sources.json C:\tmp\longfellow-anchors.json skills\russellian-style\assets\longfellow-corpus\index.json
```

- [ ] **Step 7: Write the tool README**

Create `tools/build-longfellow-corpus/README.md`:

```markdown
# build-longfellow-corpus

Run-once dev tool. Produces `skills/russellian-style/assets/longfellow-corpus/index.json`:
a small set of verified public-domain Longfellow anchor snippets (with source URL,
canto/section locator, technique tag, and prose translation) used by the russellian-style
liveness layer.

Two responsibilities:

- **Offline**, CI-tested: `segment_stanzas` (poetry-aware blank-line segmentation that
  preserves line breaks) and `build_index` (assemble the index from verified inputs).
- **Network**, run by the orchestrator: `fetch_work_markdown(url)` reaches Project
  Gutenberg through scrapling-fetch (the suite's network boundary). Set
  `SCRAPLING_FETCH_ROOT` and `SCRAPLING_FETCH_PYTHON`, then `python build_longfellow_corpus.py
  fetch <url>` writes clean markdown to stdout.

Snippets in `anchors.json` must appear verbatim in the fetched markdown of the cited
source. The skill's `lint_ornament` will flag any prompt that imports archaism, so anchors
are framed as `prose_translation` — borrow cadence and image-logic only.

Run tests with:

    python -m pytest tools/build-longfellow-corpus/test_segment.py -v
```

- [ ] **Step 8: Commit**

```
git add tools/build-longfellow-corpus/ skills/russellian-style/assets/longfellow-corpus/index.json
git commit -m "Add Longfellow study corpus and run-once builder via scrapling-fetch"
```

---

### Task 6: `references/longfellow-liveness-map.md`

REQ-VOICE-009, REQ-VOICE-011, REQ-VOICE-012. Mirrors `russell-corpus-map.md` in role: a positive guide of prose-translatable techniques + the firewall.

**Files:**
- Create: `skills/russellian-style/references/longfellow-liveness-map.md`

- [ ] **Step 1: Write the file**

Create with this content (the anchor IDs must match Task 5's `index.json`):

```markdown
# Longfellow Liveness Map

This guide names the prose-translatable techniques the liveness layer borrows from
Longfellow and a small tradition of poetic-but-disciplined prose (Carson, Dillard,
Eiseley). It mirrors `russell-corpus-map.md` in role: the positive moves the linters
cannot reward and the writer should reach for.

Anchor snippets are stored in `assets/longfellow-corpus/index.json` (public-domain,
verbatim, attributed). In-copyright prose models are referenced by named technique
only and never quoted.

The firewall: borrow cadence and image-logic only. Never the meter, rhyme, archaism,
or sentiment.

## The six techniques

### 1. Sentence-length percussion (Le Guin)

After a cluster of medium or long sentences, a short sentence — fewer than eight words
— marks arrival. The short sentence is amplified by what surrounds it; never produce
four consecutive sentences of similar length.

### 2. Cumulative, base-clause-first sentence (Christensen)

State the main claim first. Then add one to three free modifiers, each more specific
than the one before. Forward motion, not suspension. Default to cumulative; reserve
periodic (claim-last) for deliberate climactic weight.

### 3. Knot-and-resolution cadence (Stevenson)

At least once per substantive paragraph, build a sentence whose early clauses create a
tension and whose final clause resolves it — on the narrower, more specific term, not
a grand generalization. Subtle sound concordance is welcome; metrical regularity is not.

### 4. Anaphora tied to the argued term

When developing a concept across three or more consecutive sentences, open two of them
with the same word or phrase — the term under argument, not an atmospheric word. The
repetition marks stages of an argument; never decoration.

### 5. Specific-named catalog with chosen syndeton

When listing instances that support a claim, name them exactly: proper names, technical
names, exact quantities, dates. Three exact items outweigh six vague categories. End the
list with asyndeton (no final conjunction) for compression, or polysyndeton (and... and)
when you want the reader to feel the weight rather than the speed of accumulation.

### 6. Concrete anchor per abstraction (Strunk & White, Rule 16)

After each abstract claim, add one sentence that names the smallest specific physical
thing that instantiates it. Choose for precision, not beauty. One concrete detail,
exactly chosen, outweighs three atmospheric adjectives.

## Anchor catalogue

| ID | Technique | Prose translation |
| --- | --- | --- |
| `hiawatha-antithesis` | antithetical spatial parallelism | Two sentences with mirrored skeletons hold contrasting claims; the verb is repeated to mark the pulse. |
| `hiawatha-catalog` | specific-named enumeration with polysyndeton | Name the items exactly and let repeated "and" make the weight of the list felt. |
| `hiawatha-anaphora` | rhetorical-question opening with anaphora | Open with the question you are about to resolve, in the reader's voice; repeat the wh-word once to mark the structure. |
| `evangeline-primeval` | deictic anchor — name then particularize | State the claim concretely first; name the two specific instances that make it visible in the next sentence. |

## Disciplined-lyricism prose models (referenced by technique, not quoted)

Three prose stylists demonstrate the lively-but-not-purple register the blend targets.
Use their techniques; do not quote them.

- **Rachel Carson** — anaphoric accumulation with epistemic progression (a repeated
  modal "would" building to "should"); parataxis as register shift; point-of-view
  ("as the gulls saw") grounding elevated prose in a biological specific.
- **Annie Dillard** — recurring concrete image that evolves semantically across an
  essay, doing argumentative work by accumulating contradictions; phonemic patterning
  (alliteration / assonance) that enacts the claim rather than ornaments it.
- **Loren Eiseley** — scale-collision: a human-scale physical particular juxtaposed
  with a geological or cosmological claim in one sentence, the collision doing the
  emotional work.

## The firewall (what each liveness anchor must not import)

Stop and rewrite if the prose has acquired any of:

- Two evaluative adjectives modifying the same noun.
- An adverb attached to a verb that already contains the adverb's meaning.
- An emotion word applied directly without a concrete vehicle for it.
- Any apostrophe — to the reader, to a personified abstraction, to nature.
- A word chosen because it is grander than the plain alternative.
- A clause where nature's condition mirrors the argument's emotional register.
- Metrical regularity audible when the sentence is read aloud.
- An image whose argumentative function cannot be stated in one sentence.

These are what `lint_ornament` flags, advisory in v1.

## Sources

In-repo:
- Russell vitality companion: `references/russellian-vitality-guide.md`.
- Russell corpus anchors: `references/russell-corpus-map.md`.

External:
- Le Guin, *Steering the Craft* (sentence-length percussion).
- Christensen, *Generative Rhetoric of the Sentence* (cumulative construction).
- Stevenson, *On Some Technical Elements of Style in Literature* (knot-and-resolution).
- Strunk & White, *The Elements of Style*, Rule 16 (concreteness).
- Grabe & Low (2002), normalized Pairwise Variability Index (nPVI).
```

- [ ] **Step 2: Commit**

```
git add skills/russellian-style/references/longfellow-liveness-map.md
git commit -m "Add Longfellow liveness map: techniques, anchors, firewall"
```

---

### Task 7: Add `## Liveness` to each mode prompt + contract test

REQ-VOICE-008 (subsection presence), REQ-VOICE-009 (gradable directives), REQ-VOICE-010 (per-mode intensity), REQ-VOICE-011 (anchor + firewall), REQ-VOICE-012 (Longfellow verbatim+attributed; prose models technique-only), REQ-VOICE-017 (contract test).

**Files:**
- Modify: `skills/russellian-style/assets/system-prompts/technical-exposition.md`
- Modify: `skills/russellian-style/assets/system-prompts/narrative-editorial.md`
- Modify: `skills/russellian-style/assets/system-prompts/polemic.md`
- Create: `skills/russellian-style/tests/test_system_prompt_liveness.py`

- [ ] **Step 1: Write the failing contract test**

Create `skills/russellian-style/tests/test_system_prompt_liveness.py` (NOT `test_lint_*`, so it runs in CI):

```python
"""Cites REQ-VOICE-008 through REQ-VOICE-012, REQ-VOICE-017.

Each mode prompt's # Calibration and planning section must contain a ## Liveness
subsection at the declared intensity for that mode, with at least one anchor
referencing a longfellow-corpus snippet ID, and the firewall stated.
"""
import json
import pytest
from pathlib import Path

pytestmark = pytest.mark.windows_canary

from scripts.system_prompt_loader import load, VALID_MODES, PROMPTS_DIR


MODE_DIAL = {
    "technical-exposition": "low",
    "narrative-editorial": "high",
    "polemic": "medium",
}

CORPUS_INDEX = (PROMPTS_DIR.parent / "longfellow-corpus" / "index.json")


def _anchor_ids() -> set[str]:
    idx = json.loads(CORPUS_INDEX.read_text(encoding="utf-8"))
    return {a["id"] for a in idx["anchors"]}


@pytest.mark.parametrize("mode", sorted(VALID_MODES))
def test_each_mode_has_liveness_subsection_at_declared_dial(mode):
    text = load(mode)
    assert "## Liveness" in text, f"{mode} missing ## Liveness subsection"
    dial = MODE_DIAL[mode]
    # Intensity declared in plain prose: "Intensity: low" / "Intensity: high" / "Intensity: medium"
    assert f"Intensity: {dial}" in text, f"{mode} ## Liveness section must declare 'Intensity: {dial}'"


@pytest.mark.parametrize("mode", sorted(VALID_MODES))
def test_each_mode_cites_a_longfellow_corpus_anchor(mode):
    text = load(mode)
    ids = _anchor_ids()
    assert any(aid in text for aid in ids), (
        f"{mode} ## Liveness section must reference at least one anchor ID from "
        f"longfellow-corpus/index.json"
    )


@pytest.mark.parametrize("mode", sorted(VALID_MODES))
def test_each_mode_states_the_firewall(mode):
    text = load(mode)
    assert "never meter" in text.lower(), (
        f"{mode} ## Liveness section must state the firewall (e.g., "
        f"'borrow cadence and image-logic only, never meter, rhyme, archaism, or sentiment')"
    )
```

- [ ] **Step 2: Run the test to verify it fails**

```
cd skills/russellian-style && .venv\Scripts\python.exe -m pytest tests/test_system_prompt_liveness.py -v
```

Expected: 9 parametrized cases (3 modes × 3 assertions) fail with "missing ## Liveness subsection".

- [ ] **Step 3: Append `## Liveness` to `technical-exposition.md`**

Append the following block to the end of `skills/russellian-style/assets/system-prompts/technical-exposition.md` (it already ends with the existing `# Calibration and planning` bullet list; add the subsection below it on a new line):

```markdown

## Liveness

- Intensity: low. Technical-exposition stays austere; liveness is light support, not the leading move.
- Sentence-length percussion: vary length every five or six sentences. At least one short sentence per page lands a verdict.
- Concrete anchor per abstraction: after each abstract claim, add one sentence naming the smallest specific physical thing that instantiates it. Choose for precision, never beauty.
- Cumulative construction: state the claim first, then add at most one free modifier zooming to a more specific case.
- No anaphora is required; do not use rhetorical-question openers (this mode bans them already).

Anchor (`evangeline-primeval`, public-domain Longfellow, *Evangeline*, Prologue): "This is the forest primeval. The murmuring pines and the hemlocks." Borrow the technique — state the claim concretely in one sentence, then name the two specific instances that make it visible in the next — never the meter, rhyme, archaism, or sentiment.

Firewall: borrow cadence and image-logic only, never meter, rhyme, archaism, or sentiment. The ornament linter flags decoration; treat its findings as a rewrite signal, not noise.
```

- [ ] **Step 4: Append `## Liveness` to `narrative-editorial.md`**

Append to `skills/russellian-style/assets/system-prompts/narrative-editorial.md` (after the existing `# Calibration and planning` block):

```markdown

## Liveness

- Intensity: high. This is the mode built for scenes and human pace; the liveness layer leads.
- Sentence-length percussion: vary length every two or three sentences. A four-word verdict can land in the middle of a paragraph after a thirty-word build-up.
- Cumulative construction: open with the claim or scene, then add two or three free modifiers, each zooming to a more specific sensory detail.
- Knot-and-resolution: at least once per substantive paragraph, set up a tension in the early clauses and resolve it on the narrower term at the end.
- Anaphora tied to the argued term: open two or three consecutive sentences with the same word or phrase — the term under examination, not an atmospheric word.
- Concrete anchor per claim: one specific physical thing per abstraction. Three exact items outweigh six vague categories.

Anchors (public-domain Longfellow, *The Song of Hiawatha*):
- `hiawatha-antithesis` ("Dark behind it rose the forest, ... Bright before it beat the water"). Borrow the technique: two sentences with mirrored skeletons hold contrasting claims; repeat the verb to mark the pulse. Drop the trochaic meter and the rhyme.
- `hiawatha-anaphora` ("Should you ask me, whence these stories? / Whence these legends and traditions"). Borrow the technique: open a section with the question you are about to resolve, in the reader's voice; repeat the wh-word once to mark the structure. Drop the verse meter and any apostrophe.

Disciplined-lyricism models (referenced, never quoted): Carson's anaphoric accumulation with epistemic progression; Dillard's recurring concrete image evolving across an essay; Eiseley's scale-collision in one sentence.

Firewall: borrow cadence and image-logic only, never meter, rhyme, archaism, or sentiment. No apostrophe ("O Reader"), no "o'er / 'tis / thee / thou", no bare emotion words ("sorrow", "grief"), no nature-mirrors-mood. The ornament linter enforces these as an advisory rewrite signal.
```

- [ ] **Step 5: Append `## Liveness` to `polemic.md`**

Append to `skills/russellian-style/assets/system-prompts/polemic.md` (after the existing `# Calibration and planning` block):

```markdown

## Liveness

- Intensity: medium. Polemic earns momentum through antithesis; the liveness layer adds drive and one specific scene without softening the argument.
- Sentence-length percussion: vary length every three or four sentences. A four-word verdict landing inside a long paragraph is already in the mode's mandates; the liveness layer reinforces it.
- Cumulative construction: state the claim first, then one or two free modifiers that zoom from the principle to a specific instance.
- Knot-and-resolution: at least one sentence per substantive paragraph that sets up a tension and resolves it on the sharper, narrower term.
- Anaphora tied to the argued term: at least one anaphoric pair per section — the repeated phrase is what is under argument, not a flourish.
- Specific-named instance per claim: name the official, the institution, the date; do not abstract them into "the system" or "the platform".

Anchor (`hiawatha-catalog`, public-domain Longfellow, *The Song of Hiawatha*, Hiawatha's Childhood): "Saw the wild rice, Mahnomonee, / Saw the blueberry, Meenahga, / And the strawberry, Odahmin". Borrow the technique: name items exactly and use repeated "and" to make the weight of the list felt, or end on asyndeton (no final "and") for compression. Drop the meter and the proper nouns of place.

Firewall: borrow cadence and image-logic only, never meter, rhyme, archaism, or sentiment. The polemic mode is especially vulnerable to imported outrage — keep the verdict cold, let the antithesis carry the heat. The ornament linter flags decorative slippage.
```

- [ ] **Step 6: Run the contract test to verify it passes**

```
cd skills/russellian-style && .venv\Scripts\python.exe -m pytest tests/test_system_prompt_liveness.py -v
```

Expected: 9 passed.

- [ ] **Step 7: Run the full skill test suite to catch any regression**

```
cd skills/russellian-style && .venv\Scripts\python.exe -m pytest tests/ -q
```

Expected: all tests pass or skip (spaCy-gated). No new failures.

- [ ] **Step 8: Commit**

```
git add skills/russellian-style/assets/system-prompts/ skills/russellian-style/tests/test_system_prompt_liveness.py
git commit -m "Add per-mode liveness layer with Longfellow anchors and firewall"
```

---

### Task 8: Validation audit bundle (the success gate)

The success gate is not a number. It is a blind reading-council A/B: take a real topic, generate one baseline passage (current prompts) and one blended passage (new prompts), score both with the reading council, and write the comparison up like the snails bundle.

**Files:**
- Create: `docs/audits/2026-05-27-longfellow-liveness-before-after/README.md`
- Create: `docs/audits/2026-05-27-longfellow-liveness-before-after/baseline.md`
- Create: `docs/audits/2026-05-27-longfellow-liveness-before-after/blended.md`
- Create: `docs/audits/2026-05-27-longfellow-liveness-before-after/scores.json`

- [ ] **Step 1: Pick a topic and generate two passages**

Pick a substantive, non-trivial topic that exercises argument-anchored image — e.g., "the rise and limits of formal verification in distributed systems" or another in the user's domain. Generate 15–20 paragraphs twice:

1. **Baseline** — use the prompts at `origin/main` (no liveness layer). Save to `baseline.md`.
2. **Blended** — use the prompts on `feat/longfellow-liveness` after Task 7. Save to `blended.md`.

Both passages must (a) discuss the same topic, (b) be of similar length (within ±10% words), and (c) be saved verbatim as Markdown.

- [ ] **Step 2: Run `voice_eval` on each passage**

```
cd skills/russellian-style
.venv\Scripts\python.exe -m scripts.voice_eval <abs path to baseline.md> > <abs path to baseline-voice-eval.json>
.venv\Scripts\python.exe -m scripts.voice_eval <abs path to blended.md>  > <abs path to blended-voice-eval.json>
```

Record `russell_delta`, the `liveness` block, and the `ornament` linter count for each.

- [ ] **Step 3: Score each passage with the reading council**

The reading-council aggregator (`skills/review-conductor/scripts/reading_scores.py`) takes a document and a JSON array of per-persona scores. The orchestrator role-plays the five reading-council personas defined in `skills/review-conductor/personas/` (or equivalent), reads each passage **blind to condition**, and writes a per-passage `persona-scores.json` containing one object per persona — each with keys `enjoyment`, `flow`, `style`, `quality` (integers 1–5):

```json
[
  {"enjoyment": 4, "flow": 4, "style": 4, "quality": 4},
  {"enjoyment": 3, "flow": 4, "style": 4, "quality": 4},
  {"enjoyment": 4, "flow": 3, "style": 3, "quality": 4},
  {"enjoyment": 3, "flow": 4, "style": 4, "quality": 3},
  {"enjoyment": 4, "flow": 4, "style": 4, "quality": 4}
]
```

Aggregate:

```
cd skills/review-conductor
.venv\Scripts\python.exe -m scripts.reading_scores <abs path to baseline.md> <abs path to baseline-persona-scores.json> <abs path to baseline-council.json>
.venv\Scripts\python.exe -m scripts.reading_scores <abs path to blended.md>  <abs path to blended-persona-scores.json>  <abs path to blended-council.json>
```

Each `*-council.json` carries the four median dimensions, `overall`, `deterministic.flesch`, `deterministic.burstiness`, and `verdict`.

- [ ] **Step 4: Write `scores.json`**

Schema:

```json
{
  "topic": "<topic>",
  "baseline": {
    "reading_council": {"enjoyment": 0.0, "flow": 0.0, "style": 0.0, "quality": 0.0,
                        "overall": 0.0, "deterministic": {"flesch": 0.0, "burstiness": 0.0},
                        "verdict": "<verdict>"},
    "voice_eval": {"liveness": 0.0, "components": {"cadence": 0.0, "motion": 0.0,
                   "concreteness": 0.0, "ornament_penalty": 0.0},
                   "russell_delta": {"delta": 0.0, "verdict": "<verdict>"}}
  },
  "blended": { "<same shape>" }
}
```

- [ ] **Step 5: Write `README.md`**

Mirror the snails audit (`docs/audits/2026-05-27-snails-before-after/README.md`): table of reading-council and deterministic numbers side by side; a short "Reading" section that names the trade. The success criterion is **flow and enjoyment rise without quality falling**. Do not use the words "radically" or "beats". If the trade is the wrong shape (quality fell), say so — the audit is honest, not vindication.

Template:

```markdown
# Longfellow × Russell liveness blend: before / after — measured by the suite

Date: 2026-05-27

Two passages on the same topic (<topic>). `baseline` uses the prompts at `origin/main`;
`blended` uses the prompts on `feat/longfellow-liveness` (the `## Liveness` layer per mode,
anchored in `assets/longfellow-corpus/index.json`).

The success gate for this change is **the reading council, not a deterministic score**:
flow and enjoyment must rise without quality falling. The voice_eval telemetry is
descriptive.

## Result

| metric | baseline | blended | reads as |
|---|---|---|---|
| Enjoyment | <n> | <n> | <up/down/flat> |
| Flow | <n> | <n> | <up/down/flat> |
| Style | <n> | <n> | <up/down/flat> |
| Quality | <n> | <n> | <up/down/flat> |
| Overall | <n> | <n> | <up/down/flat> |
| Flesch | <n> | <n> | <plain/etc> |
| burstiness | <n> | <n> | <up/down/flat> |
| liveness (telemetry) | <n> | <n> | <descriptive> |
| ornament penalty | <n> | <n> | <descriptive> |

## Reading

<two paragraphs naming the trade honestly: what improved, what cost was paid, whether
the change earned the gate (flow + enjoyment up, quality at least flat).>

Passages: `baseline.md`, `blended.md`. Scores: `scores.json`.
```

- [ ] **Step 6: Commit**

```
git add docs/audits/2026-05-27-longfellow-liveness-before-after/
git commit -m "Add Longfellow liveness before/after audit bundle"
```

---

### Task 9: OpenSpec `tasks.md` (REQ → task map)

OpenSpec convention: every change carries a `tasks.md` mapping each task line to its REQ IDs (`openspec/README.md`).

**Files:**
- Create: `openspec/changes/add-longfellow-liveness/tasks.md`

- [ ] **Step 1: Write the file**

Create `openspec/changes/add-longfellow-liveness/tasks.md`:

```markdown
# Tasks — add-longfellow-liveness

Each line cites the REQ IDs it satisfies. Implementation plan:
`docs/plans/2026-05-28-longfellow-liveness.md`.

1. **nPVI cadence signal** (`scripts/liveness.py:npvi`, `tests/test_liveness.py`) — REQ-VEVAL-009, REQ-VEVAL-013.
2. **Liveness composite** (`scripts/liveness.py:liveness_summary`, `tests/test_liveness.py`) — REQ-VEVAL-010, REQ-VEVAL-013, REQ-VEVAL-014.
3. **Ornament linter** (`scripts/lint_ornament.py`, `tests/test_ornament.py`, `SKILL.md`) — REQ-VOICE-013, REQ-VOICE-014, REQ-VOICE-015.
4. **voice_eval wiring** (`scripts/voice_eval.py`, `tests/test_voice_eval.py`) — REQ-VEVAL-009, REQ-VEVAL-010, REQ-VEVAL-011, REQ-VEVAL-012, REQ-VEVAL-013, REQ-VEVAL-014.
5. **Longfellow corpus + builder** (`tools/build-longfellow-corpus/`, `assets/longfellow-corpus/index.json`) — REQ-VOICE-012.
6. **Liveness map** (`references/longfellow-liveness-map.md`) — REQ-VOICE-009, REQ-VOICE-011, REQ-VOICE-012.
7. **Per-mode `## Liveness` + contract test** (`assets/system-prompts/*.md`, `tests/test_system_prompt_liveness.py`) — REQ-VOICE-008, REQ-VOICE-009, REQ-VOICE-010, REQ-VOICE-011, REQ-VOICE-012, REQ-VOICE-017.
8. **Validation audit bundle** (`docs/audits/2026-05-27-longfellow-liveness-before-after/`) — validates the change against the success gate (reading-council A/B).

Out of scope, asserted unchanged by REQ-VOICE-016: `system_prompt_loader.py`,
`VALID_MODES`, `DEFAULT_MODE`, `assets/russell-corpus/index.json`,
`references/russell-corpus-map.md`, the Russell-Delta scorer.
```

- [ ] **Step 2: Commit**

```
git add openspec/changes/add-longfellow-liveness/tasks.md
git commit -m "Add OpenSpec tasks.md for add-longfellow-liveness"
```

---

## Final verification

After all tasks, run the full russellian-style suite and the offline corpus-tool tests:

```
cd skills/russellian-style && .venv\Scripts\python.exe -m pytest tests/ -q
cd ../../tools/build-longfellow-corpus && /c/russellian-book-suite/skills/russellian-style/.venv/Scripts/python.exe -m pytest test_segment.py -q
```

Expected: all green or appropriately skipped (spaCy-gated tests skip in CI; the new
`test_liveness.py`, `test_ornament.py`, and `test_system_prompt_liveness.py` all run
regardless because they import no spaCy).

Then run the finishing-a-development-branch skill to push the branch + open a PR
against `main` (squash-merge, no AI attribution).
