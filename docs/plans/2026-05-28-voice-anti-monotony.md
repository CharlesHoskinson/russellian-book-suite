# Voice Anti-Monotony Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add three voice-anti-monotony instruments to the `VOICE` capability — two rebuilt deterministic linters (`lint_chassis_uniformity`, `lint_humanity_token_closers`) and one LLM-judge step (`chassis_judge`) — plus a two-donor expansion of the disciplined-lyricism reference (Didion-corrected + McPhee), validated by a preregistered-falsification audit on a snails-v3.1 rewrite.

**Architecture:** Three-instrument stack — cheap deterministic regex (chassis-uniformity + humanity-token-closers) as pre-filter, LLM-judge (chassis_judge) as top-of-stack reader following the reading-council dispatcher pattern. The deterministic linters wire into `voice_eval._linters()`; the LLM-judge stays separate (dispatcher-required), invoked by audits.

**Tech Stack:** Python 3.11 stdlib (`re`, `math`, `collections.Counter`, `statistics`); cross-imports of `classify_paragraph` (from `lint_paragraph_motion`, stdlib) and `strip_quotes` (from `lint_ornament`, after rename); pytest with `windows_canary` marker. No spaCy in any new code or test top-level import.

**Spec:** `openspec/changes/add-voice-anti-monotony/` + `docs/specs/2026-05-28-voice-anti-monotony-design.md`.

**Branch / worktree:** Already on `feat/voice-anti-monotony` in `~/.config/superpowers/worktrees/russellian-book-suite/feat-voice-anti-monotony`, based on `feat/longfellow-liveness`. The parallel agent's checkout (`russell-pass-agentic-civ`) stays untouched.

---

## CI / test naming gotcha (carried from prior iteration)

`skills/russellian-style/tests/conftest.py` sets `collect_ignore_glob = ["test_lint_*.py", ...]` when the spaCy model is absent. The CI `[ci]` extra omits the model. **A test file named `test_lint_chassis_uniformity.py` would silently skip in CI.** Use:

- `test_chassis_uniformity.py` (NOT `test_lint_*`)
- `test_humanity_token_closers.py` (NOT `test_lint_*`)
- `test_chassis_judge.py` (no risk; doesn't match the glob anyway, kept consistent)

All three carry `pytestmark = pytest.mark.windows_canary` so the Windows CI leg (which filters on this marker) actually exercises them.

The russellian-style venv is at `skills/russellian-style/.venv/`. Windows: `.venv\Scripts\python.exe`; POSIX: `.venv/bin/python`. If the worktree's venv is absent (it was in the prior plan), fall back to system `python` — the new code is stdlib-only and runs identically.

---

## Marker-hit vs. fallback (load-bearing for Task 3)

`classify_paragraph` returns one of seven shapes (`SHAPES` at `lint_paragraph_motion.py:13`). The shapes split:

- **MARKER-HIT** (an explicit cue matched): `question_answer`, `concession_turn`, `contrast`, `example_inference`, `definition_by_pressure`
- **FALLBACK** (no cue matched; default by sentence count): `assertion_only` (≤1 sentence), `assertion_justification` (>1 sentence)

Task 3 (`lint_chassis_uniformity`) uses this split: marker-hit dominance counts only the five marker-hit shapes, so a Didion-style sparse-marker essay does NOT trigger false-positive saturation just because most paragraphs land in the `assertion_justification` fallback.

---

## File map

| File | New / Mod | Capability | Owner task |
|---|---|---|---|
| `skills/russellian-style/scripts/lint_ornament.py` | mod (1-line rename + 1 call site) | VOICE | Task 1 |
| `skills/russellian-style/tests/test_ornament.py` | mod (call-site update if any) | VOICE | Task 1 |
| `skills/russellian-style/scripts/lint_humanity_token_closers.py` | new | VOICE | Task 2 |
| `skills/russellian-style/tests/test_humanity_token_closers.py` | new | VOICE | Task 2 |
| `skills/russellian-style/scripts/lint_chassis_uniformity.py` | new | VOICE | Task 3 |
| `skills/russellian-style/tests/test_chassis_uniformity.py` | new | VOICE | Task 3 |
| `skills/russellian-style/scripts/chassis_judge.py` | new | VOICE | Task 4 |
| `skills/russellian-style/tests/test_chassis_judge.py` | new | VOICE | Task 4 |
| `skills/russellian-style/scripts/voice_eval.py` | mod | VOICE | Task 5 |
| `skills/russellian-style/tests/test_voice_eval.py` | mod | VOICE | Task 5 |
| `skills/russellian-style/SKILL.md` | mod (linter list) | VOICE | Task 5 |
| `skills/russellian-style/references/longfellow-liveness-map.md` | mod | VOICE | Task 6 |
| `docs/audits/2026-05-28-snails-v3-vs-v3.1/` | new | (audit) | Task 7 |

Tasks are dependency-ordered: 1 → 2 → 3 → 4 → 5 → 6 → 7. Task 2 needs Task 1 (`strip_quotes`); Task 3 needs Task 2 (closer-density signal reuses humanity-token-closer gate); Task 5 needs Tasks 2 + 3; Tasks 4 and 6 are independent of 1–3 and 5 but ordered after for simplicity.

---

### Task 1: Promote `_strip_quotes` to public `strip_quotes` in `lint_ornament.py`

REQ-VOICE-026. One-line rename + one internal call-site update. Behaviour-preserving.

**Files:**
- Modify: `skills/russellian-style/scripts/lint_ornament.py` (line 93 definition, line 107 call site)
- Verify: `skills/russellian-style/tests/test_ornament.py` (existing 16 tests must still pass)

- [ ] **Step 1: Rename the function definition**

Edit `skills/russellian-style/scripts/lint_ornament.py`. Find line 93:

```python
def _strip_quotes(text: str) -> str:
```

Replace with:

```python
def strip_quotes(text: str) -> str:
```

- [ ] **Step 2: Update the internal call site**

In the same file, find line 107 (inside `lint_ornament`):

```python
    text = _strip_quotes(Path(path).read_text(encoding="utf-8"))
```

Replace with:

```python
    text = strip_quotes(Path(path).read_text(encoding="utf-8"))
```

- [ ] **Step 3: Add a module-docstring note recording the public-helper status**

In the same file, find the docstring lines 6–9:

```python
Quoted spans (double-quoted, curly-quoted, and markdown blockquotes) are removed
before scanning so the linter does not penalize quoting or discussing ornate sources.
The strip is per-line for double/curly quotes (an unmatched opening quote that spans
paragraphs is not detected); markdown blockquote lines (`>`) are dropped wholesale.
```

Insert this sentence as a new line directly after them (before line 10's blank-then-`Each match`):

```
The ``strip_quotes`` helper is exposed publicly so sibling linters (e.g.,
``lint_humanity_token_closers``) reuse it without copy-paste.
```

- [ ] **Step 4: Run the existing ornament tests to confirm behaviour is preserved**

```
cd C:\Users\charl\.config\superpowers\worktrees\russellian-book-suite\feat-voice-anti-monotony\skills\russellian-style
python -m pytest tests/test_ornament.py -v
```

Expected: 16 passed (same as the prior change's final state).

If any test references `_strip_quotes` by name, update the reference (the existing test file at `tests/test_ornament.py` does NOT — it only calls `lint_ornament(path)` — but verify before committing).

- [ ] **Step 5: Commit**

```
git add skills/russellian-style/scripts/lint_ornament.py
git commit -m "Promote strip_quotes to public for sibling-linter reuse"
```

Terse, no AI attribution.

---

### Task 2: `lint_humanity_token_closers`

REQ-VOICE-020 (5-gate behaviour), REQ-VOICE-021 (stdlib-only, advisory).

**Files:**
- Create: `skills/russellian-style/scripts/lint_humanity_token_closers.py`
- Create: `skills/russellian-style/tests/test_humanity_token_closers.py`

- [ ] **Step 1: Write the failing tests**

Create `skills/russellian-style/tests/test_humanity_token_closers.py`:

```python
"""Cites REQ-VOICE-020, REQ-VOICE-021.

Filename is test_humanity_token_closers.py (NOT test_lint_*) so the conftest's
spaCy-absent collect_ignore_glob does not silently skip it in CI.
"""
import pytest

pytestmark = pytest.mark.windows_canary

from pathlib import Path

from scripts.lint_humanity_token_closers import lint_humanity_token_closers


def _write(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "draft.md"
    p.write_text(text, encoding="utf-8")
    return p


# Positive: closers the v3 critique named as chassis aphorisms.
def test_civilisation_closer_flagged(tmp_path):
    # v3 snails essay paragraph 4 closer (paraphrase): humanity-token "we" +
    # token "civilisation", 23 words, no concrete-instance marker, no first-person.
    text = (
        "Gutenberg pulled a sheet of damp paper from the press.\n\n"
        "We have built whole industries on the difficulty of doing what the snail "
        "does without a thought, and we have called the result civilisation."
    )
    findings = lint_humanity_token_closers(_write(tmp_path, text))
    assert len(findings) == 1
    assert findings[0]["rule"] == "humanity-token-closer"
    assert findings[0]["severity"] == "advisory"


def test_men_universal_closer_flagged(tmp_path):
    text = (
        "Consider the question of disputed property lines.\n\n"
        "Men spend their fiercest passions disputing the ownership of ground they did not make."
    )
    findings = lint_humanity_token_closers(_write(tmp_path, text))
    assert len(findings) == 1


def test_nature_universal_closer_flagged(tmp_path):
    text = (
        "The thrush carries the shell to the anvil stone.\n\n"
        "Nature is sparing with most things and spends its ironies freely."
    )
    findings = lint_humanity_token_closers(_write(tmp_path, text))
    assert len(findings) == 1


def test_compact_aphorism_at_word_floor_flagged(tmp_path):
    # 8 words. The first draft's lower bound of 8 misses 8-word closers if we use ≥; use ≥6.
    text = (
        "The contest with the snail is more even than the gardener admits.\n\n"
        "Slowness is, for most of us, a strength."
    )
    findings = lint_humanity_token_closers(_write(tmp_path, text))
    assert len(findings) == 1


def test_long_russell_closer_within_cap_flagged(tmp_path):
    # 27 words. The first draft's 18-word cap missed Russell's characteristic 20-30 word closers.
    text = (
        "The snail keeps no theology and holds no opinion for which it would kill a neighbour.\n\n"
        "I do not offer the snail as a model of every virtue but in one matter "
        "of not being certain past the evidence it improves upon the larger part of mankind."
    )
    findings = lint_humanity_token_closers(_write(tmp_path, text))
    # The closer contains "I" — first-person-singular subtraction disqualifies it.
    # This documents that the rebuilt linter does NOT flag testimony closers.
    assert findings == []


def test_closer_above_28_word_cap_not_flagged(tmp_path):
    # 31 words: above the rebuilt cap. The over-long sweeping closer lands in the
    # burstiness layer, not in this advisory.
    long_closer = (
        "The slowest of creatures is among the best travelled, carried to its empire "
        "asleep on the feet of wading ducks across oceans it could never have known."
    )
    text = "Darwin made the observation.\n\n" + long_closer
    assert len(long_closer.split()) >= 29  # sanity-check the fixture
    findings = lint_humanity_token_closers(_write(tmp_path, text))
    assert findings == []


def test_closer_with_concrete_instance_marker_not_flagged(tmp_path):
    # Capitalised non-initial word ("Bernoulli") = concrete-instance marker.
    text = (
        "The shell records the seasons.\n\n"
        "The geometer Bernoulli earns the spiral by labour and dies."
    )
    findings = lint_humanity_token_closers(_write(tmp_path, text))
    assert findings == []


def test_closer_with_year_not_flagged(tmp_path):
    text = (
        "Mainz was the centre of the new craft.\n\n"
        "By 1452 the press had multiplied book production by orders of magnitude."
    )
    findings = lint_humanity_token_closers(_write(tmp_path, text))
    assert findings == []


def test_closer_with_first_person_singular_not_flagged(tmp_path):
    text = (
        "The reader will perhaps allow a personal note.\n\n"
        "I have known arguments conducted with less attention than the snail gives a leaf."
    )
    findings = lint_humanity_token_closers(_write(tmp_path, text))
    assert findings == []


def test_plain_descriptive_closer_not_flagged(tmp_path):
    text = (
        "Watch the crossing.\n\n"
        "The crossing finished without an audience and without hurry on the wet flagstone."
    )
    findings = lint_humanity_token_closers(_write(tmp_path, text))
    # No humanity token. Should not flag.
    assert findings == []


def test_quoted_closer_excluded(tmp_path):
    # The humanity-token closer lives inside a double-quoted span; strip_quotes
    # removes it before scanning.
    text = 'Russell once said, "We have invented a hundred narcotics against tedium."'
    findings = lint_humanity_token_closers(_write(tmp_path, text))
    assert findings == []


def test_blockquote_closer_excluded(tmp_path):
    text = "Russell once said:\n\n> We have invented a hundred narcotics against tedium.\n"
    findings = lint_humanity_token_closers(_write(tmp_path, text))
    assert findings == []


def test_determinism(tmp_path):
    text = (
        "The snail withdraws.\n\n"
        "We have invented a hundred narcotics against tedium."
    )
    p = _write(tmp_path, text)
    assert lint_humanity_token_closers(p) == lint_humanity_token_closers(p)
```

- [ ] **Step 2: Run the tests to verify they fail**

```
cd C:\Users\charl\.config\superpowers\worktrees\russellian-book-suite\feat-voice-anti-monotony\skills\russellian-style
python -m pytest tests/test_humanity_token_closers.py -v
```

Expected: `ModuleNotFoundError: No module named 'scripts.lint_humanity_token_closers'`.

- [ ] **Step 3: Write the implementation**

Create `skills/russellian-style/scripts/lint_humanity_token_closers.py`:

```python
"""Humanity-token closer linter: flags paragraph closers shaped like aphorisms.

Pure stdlib + re. Cross-imports the public ``strip_quotes`` helper from
``lint_ornament`` (REQ-VOICE-026). Imports nothing from ``lint_common`` (which
loads spaCy at module top) so this module runs under the CI ``[ci]`` extra
without the spaCy English model.

The instrument is named honestly. It measures the density of paragraph-final
sentences that fit the chassis closer shape (8-18-word verdict was the original
spec; the rebuilt range is 6-28 to cover Russell's characteristic 20-30-word
sweeping closers without losing the 8-word "Slowness, well defended, is a kind
of strength" case). Five gates per closer:

  1. Word count in [6, 28].
  2. Contains a humanity-generalising token from the closed list (see ``_HUMANITY``).
  3. Contains no concrete-instance marker (capitalised non-initial word,
     4-digit year, or numeric quantity).
  4. Contains no first-person-singular token (``\\bI\\b`` or ``\\bmy\\b``).
  5. (Implicit: quoted spans are excluded by ``strip_quotes`` before scanning.)

One finding per qualifying closer. Severity advisory; tier advisory; the linter
does not gate. ``voice_eval._signals`` converts ``len(fn(path))`` to per-1000
density. The descriptive threshold for "performs wisdom on a metronome" (the
critique that motivated the linter) is ~6 closers per 1000 words.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from scripts.lint_ornament import strip_quotes


_HUMANITY = (
    "we", "our", "us", "ourselves",
    "mankind", "humanity", "civilisation", "civilization",
    "modern life", "the modern world",
    "most people", "most of us", "the rest of us", "none of us", "each of us",
    "men", "man",
    "nature",
    "no one", "anyone", "everyone",
)
_HUMANITY_RE = re.compile(
    r"(?:^|[\s,;:()\-])(" + "|".join(re.escape(t) for t in _HUMANITY) + r")(?=[\s,.;:!?()\-]|$)",
    re.IGNORECASE,
)

_FIRST_PERSON_SINGULAR = re.compile(r"\b(I|my)\b")
_YEAR = re.compile(r"\b\d{4}\b")
_NUMERIC = re.compile(r"\b\d+\b")
# Proper-noun proxy: capitalised non-initial word. Skip the first word of the
# closer because sentence-initial capitalisation is not a proper-noun signal.
_CAPITALISED_NON_INITIAL = re.compile(r"(?<=\s)[A-Z][a-z]+")

_PARAGRAPH_SPLIT = re.compile(r"\n\s*\n")
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _paragraphs(text: str) -> list[str]:
    return [p.strip() for p in _PARAGRAPH_SPLIT.split(text) if p.strip()]


def _closing_sentence(paragraph: str) -> str:
    """Return the final non-empty sentence of the paragraph, or '' if none."""
    sents = [s.strip() for s in _SENTENCE_SPLIT.split(paragraph.strip()) if s.strip()]
    return sents[-1] if sents else ""


def _is_humanity_token_closer(sentence: str) -> bool:
    if not sentence:
        return False
    words = sentence.split()
    n = len(words)
    if n < 6 or n > 28:
        return False
    if not _HUMANITY_RE.search(sentence):
        return False
    if _FIRST_PERSON_SINGULAR.search(sentence):
        return False
    if _YEAR.search(sentence):
        return False
    if _NUMERIC.search(sentence):
        return False
    if _CAPITALISED_NON_INITIAL.search(sentence):
        return False
    return True


def lint_humanity_token_closers(path: Path) -> list[dict]:
    text = strip_quotes(Path(path).read_text(encoding="utf-8"))
    findings: list[dict] = []
    for i, para in enumerate(_paragraphs(text)):
        closer = _closing_sentence(para)
        if _is_humanity_token_closer(closer):
            findings.append({
                "rule": "humanity-token-closer",
                "paragraph_index": i,
                "closer": closer,
                "tier": "advisory",
                "severity": "advisory",
            })
    return findings


if __name__ == "__main__":
    import sys
    print(json.dumps(lint_humanity_token_closers(Path(sys.argv[1])), indent=2))
```

- [ ] **Step 4: Run the tests to verify they pass**

```
cd C:\Users\charl\.config\superpowers\worktrees\russellian-book-suite\feat-voice-anti-monotony\skills\russellian-style
python -m pytest tests/test_humanity_token_closers.py -v
```

Expected: 13 passed.

If any test fails, fix the regex/gate logic — the tests encode the spec.

- [ ] **Step 5: Commit**

```
git add skills/russellian-style/scripts/lint_humanity_token_closers.py skills/russellian-style/tests/test_humanity_token_closers.py
git commit -m "Add lint_humanity_token_closers: 5-gate advisory regex"
```

---

### Task 3: `lint_chassis_uniformity`

REQ-VOICE-018 (4-signal behaviour), REQ-VOICE-019 (stdlib-only, advisory).

**Files:**
- Create: `skills/russellian-style/scripts/lint_chassis_uniformity.py`
- Create: `skills/russellian-style/tests/test_chassis_uniformity.py`

- [ ] **Step 1: Write the failing tests**

Create `skills/russellian-style/tests/test_chassis_uniformity.py`:

```python
"""Cites REQ-VOICE-018, REQ-VOICE-019.

Filename is test_chassis_uniformity.py (NOT test_lint_*) so the conftest's
spaCy-absent collect_ignore_glob does not silently skip it in CI.
"""
import pytest

pytestmark = pytest.mark.windows_canary

from pathlib import Path

from scripts.lint_chassis_uniformity import lint_chassis_uniformity


def _write(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "draft.md"
    p.write_text(text, encoding="utf-8")
    return p


# Helper: a paragraph that classify_paragraph maps to a particular marker-hit shape.
_QUESTION_PARA = (
    "What is the snail's claim on us? It is the modest claim of a slow life "
    "lived to its own measure without insistence."
)
_CONCESSION_TURN_PARA = (
    "The defender will say the snail is merely slow, but the slowness is the point, "
    "and the point is not concession to weakness but care."
)
_CONTRAST_PARA = (
    "The snail moves at its own pace; however, the gardener moves at the seasons."
)
_EXAMPLE_INFERENCE_PARA = (
    "Consider the radula, with thousands of chitinous teeth. Therefore the snail "
    "is not unarmed, only quiet about its weapon."
)
_DEFINITION_BY_PRESSURE_PARA = (
    "As commonly used, slowness names a fault. Used more carefully, it names "
    "an unhurried attention that arrives at the same place by a steadier road."
)
_FALLBACK_PARA = (
    "The shell records the seasons. Each year adds its line in calcium. "
    "The animal carries a diary it cannot read."
)  # No marker → assertion_justification fallback


def _doc(*paras: str) -> str:
    return "\n\n".join(paras)


def test_three_in_a_row_streak_flags(tmp_path):
    text = _doc(_QUESTION_PARA, _QUESTION_PARA, _QUESTION_PARA, _FALLBACK_PARA)
    findings = lint_chassis_uniformity(_write(tmp_path, text))
    streak = [f for f in findings if f["signal"] == "streak"]
    assert len(streak) >= 1
    assert streak[0]["shape"] == "question_answer"
    assert all(f["severity"] == "advisory" for f in findings)


def test_marker_hit_dominance_flags_in_window(tmp_path):
    # 5-paragraph window; 3 of 5 share a marker-hit shape.
    text = _doc(
        _CONCESSION_TURN_PARA,
        _FALLBACK_PARA,
        _CONCESSION_TURN_PARA,
        _FALLBACK_PARA,
        _CONCESSION_TURN_PARA,
    )
    findings = lint_chassis_uniformity(_write(tmp_path, text))
    marker = [f for f in findings if f["signal"] == "marker_dominance"]
    assert len(marker) >= 1
    assert marker[0]["shape"] == "concession_turn"


def test_fallback_dominance_does_not_trigger_marker_signal(tmp_path):
    # 6 paragraphs of pure-fallback (no markers). The marker-hit dominance signal
    # must NOT fire — that was the first-draft failure mode (false-positive
    # saturation on Didion-style sparse-marker prose).
    text = _doc(*[_FALLBACK_PARA] * 6)
    findings = lint_chassis_uniformity(_write(tmp_path, text))
    marker = [f for f in findings if f["signal"] == "marker_dominance"]
    assert marker == [], (
        f"marker_dominance must not fire on fallback-only prose; got {marker}"
    )
    # But the streak signal IS expected to fire (6 consecutive same-shape paragraphs).
    streak = [f for f in findings if f["signal"] == "streak"]
    assert len(streak) >= 1


def test_varied_marker_hit_paragraphs_do_not_flag(tmp_path):
    text = _doc(
        _QUESTION_PARA,
        _CONCESSION_TURN_PARA,
        _CONTRAST_PARA,
        _EXAMPLE_INFERENCE_PARA,
        _DEFINITION_BY_PRESSURE_PARA,
    )
    findings = lint_chassis_uniformity(_write(tmp_path, text))
    marker = [f for f in findings if f["signal"] == "marker_dominance"]
    streak = [f for f in findings if f["signal"] == "streak"]
    assert marker == []
    assert streak == []


def test_low_entropy_flags(tmp_path):
    # 8 paragraphs, all the same fallback shape → entropy 0 < 1.5.
    text = _doc(*[_FALLBACK_PARA] * 8)
    findings = lint_chassis_uniformity(_write(tmp_path, text))
    entropy = [f for f in findings if f["signal"] == "entropy"]
    assert len(entropy) == 1
    assert entropy[0]["entropy"] == 0.0


def test_high_entropy_does_not_flag(tmp_path):
    # 7 paragraphs spread across all 7 shapes → entropy ≈ log2(7) ≈ 2.81.
    text = _doc(
        _QUESTION_PARA, _CONCESSION_TURN_PARA, _CONTRAST_PARA,
        _EXAMPLE_INFERENCE_PARA, _DEFINITION_BY_PRESSURE_PARA,
        _FALLBACK_PARA, "Single.",
    )
    findings = lint_chassis_uniformity(_write(tmp_path, text))
    entropy = [f for f in findings if f["signal"] == "entropy"]
    assert entropy == []


def test_closer_concentration_flags_at_threshold(tmp_path):
    # 10 paragraphs, 6 with humanity-token closers (60% ≥ 50% threshold, 10 ≥ 8 min).
    closer_p = (
        "Watch the crossing. We have invented a hundred narcotics against tedium."
    )
    plain_p = "The shell records the seasons. Each year adds its line in calcium."
    text = _doc(*([closer_p] * 6 + [plain_p] * 4))
    findings = lint_chassis_uniformity(_write(tmp_path, text))
    closer = [f for f in findings if f["signal"] == "closer_concentration"]
    assert len(closer) == 1
    assert closer[0]["closer_proportion"] >= 0.5


def test_closer_concentration_does_not_flag_below_threshold(tmp_path):
    closer_p = (
        "Watch the crossing. We have invented a hundred narcotics against tedium."
    )
    plain_p = "The shell records the seasons. Each year adds its line in calcium."
    # 10 paragraphs, 3 closers (30% < 50%).
    text = _doc(*([closer_p] * 3 + [plain_p] * 7))
    findings = lint_chassis_uniformity(_write(tmp_path, text))
    closer = [f for f in findings if f["signal"] == "closer_concentration"]
    assert closer == []


def test_short_document_skips_closer_concentration(tmp_path):
    closer_p = (
        "Watch the crossing. We have invented a hundred narcotics against tedium."
    )
    # 5 paragraphs (< 8 minimum) — closer_concentration must not fire even if all 5 are closers.
    text = _doc(*([closer_p] * 5))
    findings = lint_chassis_uniformity(_write(tmp_path, text))
    closer = [f for f in findings if f["signal"] == "closer_concentration"]
    assert closer == []


def test_advisory_severity_only(tmp_path):
    text = _doc(*[_QUESTION_PARA] * 4)
    findings = lint_chassis_uniformity(_write(tmp_path, text))
    assert findings
    assert all(f["severity"] == "advisory" for f in findings)


def test_determinism(tmp_path):
    text = _doc(_QUESTION_PARA, _QUESTION_PARA, _QUESTION_PARA, _FALLBACK_PARA)
    p = _write(tmp_path, text)
    assert lint_chassis_uniformity(p) == lint_chassis_uniformity(p)
```

- [ ] **Step 2: Run the tests to verify they fail**

```
cd C:\Users\charl\.config\superpowers\worktrees\russellian-book-suite\feat-voice-anti-monotony\skills\russellian-style
python -m pytest tests/test_chassis_uniformity.py -v
```

Expected: `ModuleNotFoundError: No module named 'scripts.lint_chassis_uniformity'`.

- [ ] **Step 3: Write the implementation**

Create `skills/russellian-style/scripts/lint_chassis_uniformity.py`:

```python
"""Chassis-uniformity linter: four signals catching paragraph-level monotony.

Pure stdlib + ``re`` + ``math`` + ``collections.Counter``. Reuses
``classify_paragraph`` (stdlib) and ``lint_humanity_token_closers``'s closer-gate
predicate. Imports nothing from ``lint_common`` (which loads spaCy at module top)
so this module runs under the CI ``[ci]`` extra without the spaCy English model.

The first-draft ``lint_shape_variance`` operated on ``classify_paragraph``'s
surface shapes with a single 5-of-6 dominance check. Two QA-pass failure modes
were named: (1) the fact-→-pivot-→-aphorism chassis can wear any of the seven
surface costumes, so single-signal shape dominance misses it; (2)
``classify_paragraph`` falls back to ``assertion_justification`` on any paragraph
without explicit discourse markers, producing false-positive saturation on
sparse-marker prose (e.g., Didion).

The rebuilt linter addresses both with four independent signals, returning the
union. Marker-hit shape dominance ignores the fallback shapes
(``assertion_only``, ``assertion_justification``), eliminating failure mode 2.
The closer-density signal catches chassis monotony even when surface shapes
vary, addressing failure mode 1.

All findings are advisory; tier records internal strength.
"""
from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path

from scripts.lint_paragraph_motion import classify_paragraph
from scripts.lint_humanity_token_closers import (
    _closing_sentence,
    _is_humanity_token_closer,
)


_PARAGRAPH_SPLIT = re.compile(r"\n\s*\n")

# classify_paragraph's seven shapes split into marker-hit (an explicit cue
# matched) and fallback (no cue matched; default by sentence count).
_FALLBACK_SHAPES = frozenset({"assertion_only", "assertion_justification"})
_MARKER_HIT_SHAPES = frozenset({
    "question_answer", "concession_turn", "contrast",
    "example_inference", "definition_by_pressure",
})

# Signal calibration constants.
_WINDOW_SIZE = 5
_WINDOW_DOMINANCE_THRESHOLD = 3  # 3 of 5 = 60%
_STREAK_THRESHOLD = 3            # ≥3 consecutive same shape
_ENTROPY_THRESHOLD = 1.5         # bits; max over 7-shape taxonomy is log2(7) ≈ 2.81
_CLOSER_CONCENTRATION_THRESHOLD = 0.5
_CLOSER_MIN_PARAGRAPHS = 8


def _paragraphs(text: str) -> list[str]:
    return [p.strip() for p in _PARAGRAPH_SPLIT.split(text) if p.strip()]


def _shapes(paragraphs: list[str]) -> list[str]:
    return [classify_paragraph(p) for p in paragraphs]


def _shape_entropy(shapes: list[str]) -> float:
    """Shannon entropy in bits of the shape sequence; 0.0 for empty."""
    if not shapes:
        return 0.0
    counts = Counter(shapes)
    n = len(shapes)
    h = 0.0
    for c in counts.values():
        p = c / n
        h -= p * math.log2(p)
    return h


def _streak_findings(shapes: list[str]) -> list[dict]:
    findings: list[dict] = []
    i = 0
    while i < len(shapes):
        j = i
        while j + 1 < len(shapes) and shapes[j + 1] == shapes[i]:
            j += 1
        run_length = j - i + 1
        if run_length >= _STREAK_THRESHOLD:
            findings.append({
                "rule": "chassis-uniformity",
                "signal": "streak",
                "shape": shapes[i],
                "start_paragraph": i,
                "run_length": run_length,
                "tier": "important" if run_length >= 4 else "advisory",
                "severity": "advisory",
            })
        i = j + 1
    return findings


def _marker_dominance_findings(shapes: list[str]) -> list[dict]:
    findings: list[dict] = []
    if len(shapes) < _WINDOW_SIZE:
        return findings
    seen_windows: set[tuple[int, str]] = set()
    for start in range(len(shapes) - _WINDOW_SIZE + 1):
        window = shapes[start:start + _WINDOW_SIZE]
        for shape, count in Counter(window).items():
            if shape in _FALLBACK_SHAPES:
                continue
            if count >= _WINDOW_DOMINANCE_THRESHOLD:
                key = (start, shape)
                if key in seen_windows:
                    continue
                seen_windows.add(key)
                findings.append({
                    "rule": "chassis-uniformity",
                    "signal": "marker_dominance",
                    "shape": shape,
                    "start_paragraph": start,
                    "window_size": _WINDOW_SIZE,
                    "count_in_window": count,
                    "tier": "important" if count >= 4 else "advisory",
                    "severity": "advisory",
                })
    return findings


def _entropy_finding(shapes: list[str]) -> list[dict]:
    if len(shapes) < _CLOSER_MIN_PARAGRAPHS:
        # Entropy on a very short document is uninformative; suppress.
        return []
    h = _shape_entropy(shapes)
    if h < _ENTROPY_THRESHOLD:
        return [{
            "rule": "chassis-uniformity",
            "signal": "entropy",
            "entropy": round(h, 3),
            "threshold": _ENTROPY_THRESHOLD,
            "n_paragraphs": len(shapes),
            "tier": "important" if h < 1.0 else "advisory",
            "severity": "advisory",
        }]
    return []


def _closer_concentration_finding(paragraphs: list[str]) -> list[dict]:
    if len(paragraphs) < _CLOSER_MIN_PARAGRAPHS:
        return []
    closer_count = sum(
        1 for p in paragraphs
        if _is_humanity_token_closer(_closing_sentence(p))
    )
    proportion = closer_count / len(paragraphs)
    if proportion >= _CLOSER_CONCENTRATION_THRESHOLD:
        return [{
            "rule": "chassis-uniformity",
            "signal": "closer_concentration",
            "closer_proportion": round(proportion, 3),
            "closer_count": closer_count,
            "n_paragraphs": len(paragraphs),
            "tier": "important" if proportion >= 0.7 else "advisory",
            "severity": "advisory",
        }]
    return []


def lint_chassis_uniformity(path: Path) -> list[dict]:
    text = Path(path).read_text(encoding="utf-8")
    paragraphs = _paragraphs(text)
    shapes = _shapes(paragraphs)
    return (
        _streak_findings(shapes)
        + _marker_dominance_findings(shapes)
        + _entropy_finding(shapes)
        + _closer_concentration_finding(paragraphs)
    )


if __name__ == "__main__":
    import sys
    print(json.dumps(lint_chassis_uniformity(Path(sys.argv[1])), indent=2))
```

- [ ] **Step 4: Run the tests to verify they pass**

```
cd C:\Users\charl\.config\superpowers\worktrees\russellian-book-suite\feat-voice-anti-monotony\skills\russellian-style
python -m pytest tests/test_chassis_uniformity.py -v
```

Expected: 11 passed.

If any test fails, fix the linter (NOT the test) — the tests encode the spec.

- [ ] **Step 5: Commit**

```
git add skills/russellian-style/scripts/lint_chassis_uniformity.py skills/russellian-style/tests/test_chassis_uniformity.py
git commit -m "Add lint_chassis_uniformity: 4-signal advisory linter (marker-hit + streak + entropy + closer density)"
```

---

### Task 4: `chassis_judge` (LLM-judge step)

REQ-VOICE-022 (dispatcher pattern + return schema), REQ-VOICE-023 (no live calls + advisory).

**Files:**
- Create: `skills/russellian-style/scripts/chassis_judge.py`
- Create: `skills/russellian-style/tests/test_chassis_judge.py`

- [ ] **Step 1: Write the failing tests**

Create `skills/russellian-style/tests/test_chassis_judge.py`:

```python
"""Cites REQ-VOICE-022, REQ-VOICE-023.

Filename test_chassis_judge.py. No spaCy. All tests use a stubbed dispatcher;
no live LLM call is ever made.
"""
import pytest

pytestmark = pytest.mark.windows_canary

from scripts.chassis_judge import (
    chassis_judge,
    _build_judge_prompt,
    _parse_judge_response,
)


_DOC = (
    "The snail crosses the flagstone.\n\n"
    "The shell records the seasons in calcium.\n\n"
    "We have built whole industries on what the snail does without thought."
)

_FAKE_RESPONSE = """\
PARAGRAPH_MOVES:
1. concrete-scene-opener
2. specific-fact
3. humanity-aphorism

MOVE_TAXONOMY:
- concrete-scene-opener
- specific-fact
- humanity-aphorism

MOST_FREQUENT_MOVE: humanity-aphorism
MOST_FREQUENT_MOVE_FREQUENCY: 0.33
SINGLE_MOVE_SUMMARY: no
UNSYMPATHETIC_CRITIQUE: The essay is too short to monotone, but ends on a generalising verdict.
"""


def test_build_judge_prompt_embeds_document_and_format():
    prompt = _build_judge_prompt(_DOC)
    assert _DOC in prompt
    assert "PARAGRAPH_MOVES:" in prompt
    assert "MOVE_TAXONOMY:" in prompt
    assert "MOST_FREQUENT_MOVE:" in prompt
    assert "MOST_FREQUENT_MOVE_FREQUENCY:" in prompt
    assert "SINGLE_MOVE_SUMMARY:" in prompt
    assert "UNSYMPATHETIC_CRITIQUE:" in prompt


def test_parse_judge_response_extracts_all_fields():
    result = _parse_judge_response(_FAKE_RESPONSE)
    assert result["paragraph_moves"] == [
        "concrete-scene-opener", "specific-fact", "humanity-aphorism",
    ]
    assert set(result["move_taxonomy"]) == {
        "concrete-scene-opener", "specific-fact", "humanity-aphorism",
    }
    assert result["most_frequent_move"] == "humanity-aphorism"
    assert result["most_frequent_move_frequency"] == pytest.approx(0.33)
    assert result["single_move_summary"] is False
    assert "generalising" in result["unsympathetic_critique"]


def test_parse_judge_response_single_move_yes():
    response = _FAKE_RESPONSE.replace("SINGLE_MOVE_SUMMARY: no", "SINGLE_MOVE_SUMMARY: yes")
    result = _parse_judge_response(response)
    assert result["single_move_summary"] is True


def test_chassis_judge_invokes_dispatcher_with_prompt_and_returns_parsed():
    captured = {}

    def fake_dispatcher(prompt: str) -> str:
        captured["prompt"] = prompt
        return _FAKE_RESPONSE

    result = chassis_judge(_DOC, dispatcher=fake_dispatcher)
    assert _DOC in captured["prompt"]
    assert result["metric"] == "chassis-judge"
    assert result["advisory"] is True
    assert result["most_frequent_move"] == "humanity-aphorism"
    assert result["most_frequent_move_frequency"] == pytest.approx(0.33)
    assert isinstance(result["paragraph_moves"], list)
    assert isinstance(result["unsympathetic_critique"], str)


def test_chassis_judge_does_not_call_dispatcher_more_than_once():
    call_count = {"n": 0}

    def fake_dispatcher(prompt: str) -> str:
        call_count["n"] += 1
        return _FAKE_RESPONSE

    chassis_judge(_DOC, dispatcher=fake_dispatcher)
    assert call_count["n"] == 1


def test_chassis_judge_return_keys():
    result = chassis_judge(_DOC, dispatcher=lambda p: _FAKE_RESPONSE)
    assert set(result.keys()) == {
        "metric",
        "paragraph_moves",
        "move_taxonomy",
        "most_frequent_move",
        "most_frequent_move_frequency",
        "single_move_summary",
        "unsympathetic_critique",
        "advisory",
    }
```

- [ ] **Step 2: Run the tests to verify they fail**

```
cd C:\Users\charl\.config\superpowers\worktrees\russellian-book-suite\feat-voice-anti-monotony\skills\russellian-style
python -m pytest tests/test_chassis_judge.py -v
```

Expected: `ModuleNotFoundError: No module named 'scripts.chassis_judge'`.

- [ ] **Step 3: Write the implementation**

Create `skills/russellian-style/scripts/chassis_judge.py`:

```python
"""LLM-judge step: extracts rhetorical-move taxonomy + unsympathetic critique.

The escape from the deterministic-instrument treadmill (REQ-VOICE-022). Single
LLM call per essay, caller-provided dispatcher (mirrors
``skills/review-conductor/scripts/reading_scores.run_reading_council``). The
deterministic linters (chassis_uniformity, humanity_token_closers, etc.) stay as
cheap pre-filters; this judge sits at the top of the stack as a reader-equivalent
that catches the abstraction layer the regex is perpetually one step behind.

This module makes NO live LLM calls. Tests stub the dispatcher. Advisory only;
the judge does not gate.

The judge is NOT auto-wired into ``voice_eval`` — it requires a dispatcher and
the eval is meant to be runnable without one. Audits invoke ``chassis_judge``
directly, alongside ``voice_eval``, the way the prior audit invoked
``reading_scores`` alongside ``voice_eval``.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Callable


_PROMPT_TEMPLATE = """\
You are reading an essay for chassis monotony — the fault where every paragraph
executes the same rhetorical move. A reader catches this when surface shapes
vary but the underlying move repeats (e.g., fact → pivot → aphorism, sixteen
times). Deterministic instruments cannot detect this reliably; you can.

Read the essay below. Then answer in EXACTLY this format, with these headers
and field names, one per line where indicated:

PARAGRAPH_MOVES:
1. <a short noun phrase naming the rhetorical move executed in paragraph 1>
2. <same for paragraph 2>
... (one numbered line per paragraph in the essay)

MOVE_TAXONOMY:
- <each unique move name from above, one per line>

MOST_FREQUENT_MOVE: <the move appearing most often>
MOST_FREQUENT_MOVE_FREQUENCY: <a float between 0.0 and 1.0, the fraction of paragraphs running this move>
SINGLE_MOVE_SUMMARY: <yes or no — can the essay be summarised in a single move-shape?>
UNSYMPATHETIC_CRITIQUE: <one sentence an unsympathetic reader would write about the essay's structural fault>

ESSAY:
{doc_text}
"""


def _build_judge_prompt(doc_text: str) -> str:
    """Pure function. The prompt embeds the document and the response format."""
    return _PROMPT_TEMPLATE.format(doc_text=doc_text)


def _section(response: str, header: str) -> str:
    """Return the lines of the named section, stopping at the next ALL_CAPS header."""
    pattern = re.compile(
        rf"^{re.escape(header)}:\s*\n?(.*?)(?=^[A-Z_]+:|\Z)",
        re.DOTALL | re.MULTILINE,
    )
    m = pattern.search(response)
    return m.group(1).strip() if m else ""


def _scalar(response: str, header: str) -> str:
    """Return the value on the same line as a scalar header (e.g., MOST_FREQUENT_MOVE: foo)."""
    m = re.search(rf"^{re.escape(header)}:\s*(.+)$", response, re.MULTILINE)
    return m.group(1).strip() if m else ""


def _parse_numbered_list(block: str) -> list[str]:
    items: list[str] = []
    for line in block.splitlines():
        m = re.match(r"\s*\d+\.\s+(.*)", line)
        if m:
            items.append(m.group(1).strip())
    return items


def _parse_bulleted_list(block: str) -> list[str]:
    items: list[str] = []
    for line in block.splitlines():
        m = re.match(r"\s*-\s+(.*)", line)
        if m:
            items.append(m.group(1).strip())
    return items


def _parse_judge_response(response: str) -> dict:
    """Pure function. Parses the structured response into the typed dict."""
    paragraph_moves = _parse_numbered_list(_section(response, "PARAGRAPH_MOVES"))
    move_taxonomy = _parse_bulleted_list(_section(response, "MOVE_TAXONOMY"))
    most_frequent = _scalar(response, "MOST_FREQUENT_MOVE")
    freq_raw = _scalar(response, "MOST_FREQUENT_MOVE_FREQUENCY")
    try:
        most_frequent_freq = float(freq_raw) if freq_raw else 0.0
    except ValueError:
        most_frequent_freq = 0.0
    single_raw = _scalar(response, "SINGLE_MOVE_SUMMARY").lower()
    single_move = single_raw.startswith("y")
    critique = _scalar(response, "UNSYMPATHETIC_CRITIQUE")
    return {
        "paragraph_moves": paragraph_moves,
        "move_taxonomy": move_taxonomy,
        "most_frequent_move": most_frequent,
        "most_frequent_move_frequency": most_frequent_freq,
        "single_move_summary": single_move,
        "unsympathetic_critique": critique,
    }


def chassis_judge(doc_text: str, *, dispatcher: Callable[[str], str]) -> dict:
    """Score an essay for chassis monotony via a single LLM call.

    ``dispatcher`` is a caller-provided ``Callable[[str], str]``. The function
    builds the prompt, passes it to the dispatcher exactly once, parses the
    response, and returns the advisory result dict (REQ-VOICE-022 schema).
    """
    prompt = _build_judge_prompt(doc_text)
    response = dispatcher(prompt)
    parsed = _parse_judge_response(response)
    return {
        "metric": "chassis-judge",
        **parsed,
        "advisory": True,
    }


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(
            "usage: chassis_judge.py <doc.md> <response.txt> [out.json]\n"
            "  doc.md       — essay to judge\n"
            "  response.txt — pre-recorded LLM response (audit replay; no live call)\n"
            "  out.json     — optional output path; default stdout",
            file=sys.stderr,
        )
        return 2
    doc_text = Path(argv[1]).read_text(encoding="utf-8")
    response = Path(argv[2]).read_text(encoding="utf-8")
    result = chassis_judge(doc_text, dispatcher=lambda _p: response)
    out = json.dumps(result, indent=2)
    if len(argv) > 3:
        Path(argv[3]).write_text(out + "\n", encoding="utf-8")
        print(f"wrote {argv[3]}")
    else:
        print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
```

- [ ] **Step 4: Run the tests to verify they pass**

```
cd C:\Users\charl\.config\superpowers\worktrees\russellian-book-suite\feat-voice-anti-monotony\skills\russellian-style
python -m pytest tests/test_chassis_judge.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Commit**

```
git add skills/russellian-style/scripts/chassis_judge.py skills/russellian-style/tests/test_chassis_judge.py
git commit -m "Add chassis_judge: LLM-judge step with caller-provided dispatcher"
```

---

### Task 5: Wire the two deterministic linters into `voice_eval`

REQ-VOICE-024 (linters in battery; chassis-judge stays out).

**Files:**
- Modify: `skills/russellian-style/scripts/voice_eval.py`
- Modify: `skills/russellian-style/tests/test_voice_eval.py`
- Modify: `skills/russellian-style/SKILL.md`

- [ ] **Step 1: Write the failing test**

Append to `skills/russellian-style/tests/test_voice_eval.py` (after the existing imports — `_spacy_model_available` and `requires_spacy` already exist in that file):

```python
@requires_spacy
def test_evaluate_emits_chassis_uniformity_and_humanity_token_closers():
    """REQ-VOICE-024: the two new deterministic linters appear in the battery."""
    from scripts.voice_eval import evaluate
    text = (
        "What can we say of the snail? It is the modest claim of a slow life "
        "lived to its own measure without insistence. "
        "The defender will say the snail is merely slow, but the slowness is the point. "
        "Consider the radula, with thousands of teeth. Therefore the snail is not unarmed.\n\n"
        "We have built whole industries on what the snail does without thought.\n\n"
    ) * 4
    rep = evaluate(text)
    linters = rep["generated"]["linters"]
    assert "chassis_uniformity" in linters
    assert "humanity_token_closers" in linters
    # Both report the standard per-1000 density shape.
    for name in ("chassis_uniformity", "humanity_token_closers"):
        assert set(linters[name]) == {"count", "per_1000"}
```

- [ ] **Step 2: Run the test to verify it fails**

```
cd C:\Users\charl\.config\superpowers\worktrees\russellian-book-suite\feat-voice-anti-monotony\skills\russellian-style
python -m pytest tests/test_voice_eval.py::test_evaluate_emits_chassis_uniformity_and_humanity_token_closers -v
```

Expected: fail with `KeyError: 'chassis_uniformity'` (or skip if spaCy model absent — that's the existing `@requires_spacy` pattern).

- [ ] **Step 3: Wire the linters into `voice_eval._linters()`**

Edit `skills/russellian-style/scripts/voice_eval.py`. Find the `_linters()` function. Its import block currently ends with:

```python
    from scripts.lint_paragraph_motion import lint_paragraph_motion
    from scripts.lint_ornament import lint_ornament
```

Replace the import block by adding TWO new import lines (alphabetical placement: `chassis_uniformity` after `burstiness`, `humanity_token_closers` after `hedges`). The full updated import block:

```python
    from scripts.lint_hedges import lint_hedges
    from scripts.lint_passive_voice import lint_passive_voice
    from scripts.lint_signal_density import lint_signal_density
    from scripts.lint_parallel_structure import lint_parallel_structure
    from scripts.lint_listicle_abstract import lint_listicle_abstract
    from scripts.lint_sentence_rhythm import lint_sentence_rhythm
    from scripts.lint_burstiness import lint_burstiness
    from scripts.lint_chassis_uniformity import lint_chassis_uniformity
    from scripts.lint_ai_vocabulary import lint_ai_vocabulary
    from scripts.lint_ai_staccato import lint_ai_staccato
    from scripts.lint_concrete_instance_density import lint_concrete_instance_density
    from scripts.lint_epistemic_precision import lint_epistemic_precision
    from scripts.lint_humanity_token_closers import lint_humanity_token_closers
    from scripts.lint_ornament import lint_ornament
    from scripts.lint_paragraph_motion import lint_paragraph_motion
```

Then update the returned dict. The existing returned dict (after the prior change) has entries through `paragraph_motion`. Replace it with this version that adds the two new entries (placed alphabetically between existing keys):

```python
    return {
        "hedges": lint_hedges,
        "passive_voice": lint_passive_voice,
        "signal_density": lint_signal_density,
        "parallel_structure": lint_parallel_structure,
        "listicle_abstract": lint_listicle_abstract,
        "sentence_rhythm": lint_sentence_rhythm,
        "burstiness": lint_burstiness,
        "chassis_uniformity": lint_chassis_uniformity,
        "ai_vocabulary": lint_ai_vocabulary,
        "ai_staccato": lint_ai_staccato,
        "concrete_instance_density": lint_concrete_instance_density,
        "epistemic_precision": lint_epistemic_precision,
        "humanity_token_closers": lint_humanity_token_closers,
        "ornament": lint_ornament,
        "paragraph_motion": lint_paragraph_motion,
    }
```

(The `chassis_judge` is NOT added — REQ-VOICE-024 requires it stays out of `voice_eval`, like `reading_scores`.)

- [ ] **Step 4: Run the new test and the existing voice_eval suite**

```
cd C:\Users\charl\.config\superpowers\worktrees\russellian-book-suite\feat-voice-anti-monotony\skills\russellian-style
python -m pytest tests/test_voice_eval.py -v
```

Expected: the new test passes (or skips on hosts without the spaCy model); all existing tests still pass.

Also confirm the dependent task suites are still green:

```
python -m pytest tests/test_chassis_uniformity.py tests/test_humanity_token_closers.py tests/test_ornament.py tests/test_liveness.py -v
```

Expected: 11 + 13 + 16 + 9 = 49 passed.

- [ ] **Step 5: Add the two linters to SKILL.md**

Edit `skills/russellian-style/SKILL.md`. In the `## Linters` section (immediately after the existing `- scripts/lint_ornament.py — ...` bullet added by the prior change), insert two new bullets:

```markdown
- `scripts/lint_chassis_uniformity.py` — four-signal advisory linter for paragraph-shape monotony: marker-hit shape dominance over 3-of-5 windows; ≥3-consecutive-shape streaks; low shape-sequence Shannon entropy; high humanity-token-closer concentration. Pure stdlib.
- `scripts/lint_humanity_token_closers.py` — advisory regex linter for paragraph closers fitting the fact-→-moral-aphorism shape (6–28 words; humanity-generalising token; no concrete-instance marker; no first-person singular). Pure stdlib; quote-excluding.
```

- [ ] **Step 6: Commit**

```
git add skills/russellian-style/scripts/voice_eval.py skills/russellian-style/tests/test_voice_eval.py skills/russellian-style/SKILL.md
git commit -m "Wire chassis_uniformity and humanity_token_closers into voice_eval"
```

---

### Task 6: Donor expansion in `longfellow-liveness-map.md`

REQ-VOICE-025 (corrected Didion entry + new McPhee entry, both referenced by named technique only, never quoted).

**Files:**
- Modify: `skills/russellian-style/references/longfellow-liveness-map.md`

- [ ] **Step 1: Locate the existing Didion bullet and replace it**

Open `skills/russellian-style/references/longfellow-liveness-map.md`. Find the "Disciplined-lyricism prose models (referenced by technique, not quoted)" section. The existing entries are Carson, Dillard, Eiseley. The prior iteration's spec mentioned a one-bullet Didion entry to be added; if a Didion bullet already exists in this section, replace it. If it does not yet exist, append after the Eiseley bullet.

Replace the entire "Disciplined-lyricism prose models" section with:

```markdown
## Disciplined-lyricism prose models (referenced by technique, not quoted)

Five prose stylists demonstrate the lively-but-not-purple register the blend targets.
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

- **Joan Didion** (1934–2021; works in copyright through at least 2047 — reference by
  named technique only, never quote). The core Didion move is not the aphorism but
  the aphorism's deferral. She accumulates specific sensory and procedural detail —
  temperatures, brand names, route numbers, furniture — until the reader is carrying
  an argument she has pointedly declined to state. Five translatable moves:
    1. **The diagnostic aphorism that eats itself.** "We tell ourselves stories in
       order to live" (*The White Album*, 1979) is not an inspirational declaration;
       it is a clinical diagnosis Didion spends the essay demonstrating to be
       unstable. The aphorism arrives as thesis; the essay dismantles it. In analytic
       prose: state the generalising claim early, then assemble evidence that
       complicates rather than confirms it; close without re-landing the opening.
    2. **The catalogue as withheld verdict.** In "Some Dreamers of the Golden Dream"
       (*Slouching Towards Bethlehem*, 1968), the affair's mechanics — falsified
       motel registrations, lunch dates, remembered phrases — are listed without
       editorial comment. The accumulation *is* the judgment.
    3. **The landscape that pre-argues.** "Some Dreamers" opens with the San
       Bernardino Valley as "a place where it is routine to misplace the future"
       before any human character appears. The setting states the conclusion in
       displaced form.
    4. **The fragmentary form as argument.** *Slouching*'s title essay uses only two
       explicit transitional markers across forty-four pages. White-space
       segmentation mirrors the "centre cannot hold" argument structurally.
    5. **The physical circumstance as epistemic condition.** "On Morality" is
       written at 119°F in the Enterprise Motel and Trailer Park in Death Valley;
       the physical conditions force the particular. The constraint on knowing
       licenses the observation that follows it.

  *Failure modes* (Didionesque mannerism to avoid): when repetition accumulates
  without variation in force, loop replaces liturgy; when "we" assumes a
  civilisational position the reader has not consented to, detachment becomes
  superiority; when juxtaposition connects nothing discoverable, it becomes surface
  shock. *Canonical texts*: "Slouching Towards Bethlehem" (1968 title essay); "Some
  Dreamers of the Golden Dream" (1968); "Holy Water" (1979); "The White Album"
  (1979 title essay); "On Morality" (1968); "Why I Write" (NYT, 1976). *Critical
  sources*: Als, *NYRB* (Dec 2020); Harrison, "Joan Didion: Only Disconnect"
  (1980); Wilkinson, *We Tell Ourselves Stories* (Liveright, 2025); Bellot,
  *Lit Hub* (2020).

- **John McPhee** (b. 1931; *New Yorker* essays 1965–present; works in copyright —
  reference by named technique only, never quote). McPhee's gift is the
  technical/process essay that makes geology, freight, oranges, or basketball
  coaches read as argument. He counters the Edwardian-familiar-essay register on a
  different axis from Didion: where Didion withholds the verdict, McPhee makes the
  *process* the verdict. Three translatable moves:
    1. **The long sentence as a chain of verbed nouns.** McPhee's signature is a
       cumulative sentence whose engine is a series of concrete verbs, each acting
       on a specific named noun: "The truck shifted, the load settled, the tarp
       belled." The sentence carries information density without ornament.
    2. **The named expert as locus of the technical claim.** Rather than asserting
       a geological or institutional fact in the writer's voice, McPhee credits it
       to a specific named source ("Anita Harris, of the U.S. Geological Survey,
       told me…"). The opposite of the abstract humanity-generalising closer —
       specificity-as-authority.
    3. **The structural conceit borrowed from the subject.** *Annals of the Former
       World* uses geological time as its own structuring principle; *Oranges*
       tells its history in concentric layers like the fruit. The form mirrors the
       content's logic without the form having to be stated.

  *Failure modes*: when the named-expert technique becomes "as X told me" in every
  paragraph, attribution itself becomes a tic; when the technical inventory
  accumulates without ever pivoting, the essay turns into a Wikipedia article with
  a byline. *Canonical texts*: *Oranges* (1967); *Coming into the Country* (1977);
  *Annals of the Former World* (1998); "The Search for Marvin Gardens" (1972);
  "Travels in Georgia" (1973). *Critical sources*: Sims, ed., *The Literary
  Journalists* (1984); Kerrane & Yagoda, eds., *The Art of Fact* (1997); McPhee,
  *Draft No. 4* (2017).

The five-donor balance: Carson, Dillard, Eiseley (anaphoric / image-evolution /
scale-collision; pre-1960 register) + Didion, McPhee (aphorism-as-target /
process-as-argument; post-1950 register). Two post-1950 donors with different
registers shift real corpus weight off the Edwardian-familiar-essay register.
```

- [ ] **Step 2: Verify the file still parses as markdown and the existing anchor catalogue is untouched**

Visually inspect that the file's other sections (intro, "The six techniques", "Anchor catalogue", "The firewall", "Sources") are unchanged.

- [ ] **Step 3: Commit**

```
git add skills/russellian-style/references/longfellow-liveness-map.md
git commit -m "Add Didion (corrected) and McPhee donor entries to liveness map"
```

---

### Task 7: Validation audit bundle with preregistered falsification

REQ-VOICE-027 (two falsification conditions preregistered; outcome recorded honestly).

**Files:**
- Create: `docs/audits/2026-05-28-snails-v3-vs-v3.1/README.md`
- Create: `docs/audits/2026-05-28-snails-v3-vs-v3.1/snails-v3.md` (copy of v3, for reference)
- Create: `docs/audits/2026-05-28-snails-v3-vs-v3.1/snails-v3.1.md`
- Create: `docs/audits/2026-05-28-snails-v3-vs-v3.1/falsification-conditions.md`
- Create: `docs/audits/2026-05-28-snails-v3-vs-v3.1/chassis-judge.json`
- Create: `docs/audits/2026-05-28-snails-v3-vs-v3.1/deterministic-telemetry.json`
- Create: `docs/audits/2026-05-28-snails-v3-vs-v3.1/scores.json`

This task is orchestrator-driven (network-using or human-author work). The subagent flow stops at Task 6; the orchestrator then runs Task 7 directly.

- [ ] **Step 1: Preregister the two falsification conditions (BEFORE writing v3.1)**

Create `docs/audits/2026-05-28-snails-v3-vs-v3.1/falsification-conditions.md` with this content:

```markdown
# Preregistered falsification conditions

These conditions are preregistered BEFORE the v3.1 essay is written. Recorded
here so the eventual audit cannot be reverse-engineered to pass.

The design fails if **either** of these conditions holds in the v3.1 audit:

## Condition 1 — Monotone move-frequency

`chassis_judge.most_frequent_move_frequency` for v3.1 is ≥ 0.50. Half or more
of the paragraphs executing one move-shape is the chassis fault by the LLM-judge's
own taxonomy; if this holds, the design did not break the metronome.

## Condition 2 — Critique names the chassis

`chassis_judge.unsympathetic_critique` for v3.1 contains any of the substrings:
`"chassis"`, `"template"`, `"metronome"`, `"one move"`, `"same move"`,
`"every paragraph"`, OR matches the regex
`r"\b(perform|performing)\b.{0,20}\b(wisdom|insight|moral)\b"`. The LLM-judge
naming the fault in v3.1 is the design's failure regardless of the deterministic
linter numbers.

Either condition triggering means the design did not work. The audit must record
the outcome honestly, including in the failure case. There is no condition under
which "the linter numbers moved" is sufficient to declare success without the
chassis-judge also clearing.

## Honest caveats

Single-author non-blind rewrite. The suite scoring its own output. What the
instruments do and do not measure is disclosed in the README.
```

Commit immediately so the preregistration is timestamped:

```
git add docs/audits/2026-05-28-snails-v3-vs-v3.1/falsification-conditions.md
git commit -m "Preregister falsification conditions for snails-v3.1 audit"
```

- [ ] **Step 2: Save the v3 essay as the audit baseline**

The v3 snails essay produced in the prior session is the input to this audit.
Save it under the audit directory as `snails-v3.md` (the exact text Charles read
when delivering the critique). Where the v3 essay is stored depends on session
state; if it is not in the repo, paste it from the conversation that produced it.

- [ ] **Step 3: Write snails-v3.1**

Apply the design to a rewrite of the snails essay. Concrete requirements:

  - Fix the two factual errors caught in the v3 critique: `Fulvius Lippinus` (not
    `Hirpinus`), per Varro's *Rerum Rusticarum* III.xiv.4. Add the Bernoulli
    stonemason irony — Jacob Bernoulli requested the logarithmic spiral on his
    tomb at the Basel Münster with *eadem mutata resurgo*; the mason carved an
    Archimedean spiral instead.
  - Apply the Didion move (aphorism-as-target, not aphorism-as-payoff): open at
    least one paragraph with a generalising claim and spend the paragraph
    dismantling it rather than landing it.
  - Apply the McPhee move at least once: a long sentence as a chain of verbed
    nouns; or a named-expert credit instead of an abstract closure.
  - Cut the two aphorisms Charles flagged: the "moral certainties have a snail
    at the bottom of them" closer (replace with a plain-descriptive closer or a
    Didion-style refused conclusion); the Polanyi name-drop (drop or earn with a
    real *Great Transformation* reference).
  - At least one paragraph that lets the snail resist its own moral (its
    survival isn't a critique of haste; it's a function of being eaten less than
    rabbits); at least one paragraph that flattens to plain description with no
    verdict; at least one moment where the irony turns on the essayist.

  Write the rewrite to `docs/audits/2026-05-28-snails-v3-vs-v3.1/snails-v3.1.md`.

- [ ] **Step 4: Compute deterministic telemetry on both essays**

Write a small audit script (the prior audit's `audit_telemetry.py` pattern at
`C:\tmp\longfellow\audit_telemetry.py` is the precedent — adapt to load the new
linters). Required output: per-essay `n_words`, `chassis_uniformity` finding
count + signal breakdown, `humanity_token_closers` finding count and per-1000
density, `nPVI`, `burstiness`, `Flesch`, ornament count.

Save to `docs/audits/2026-05-28-snails-v3-vs-v3.1/deterministic-telemetry.json`
with the v3 and v3.1 results side-by-side.

- [ ] **Step 5: Run `chassis_judge` on both essays**

The chassis_judge takes a caller-provided dispatcher; for an audit, the
orchestrator IS the dispatcher (constructs the prompt with `_build_judge_prompt`,
sends to the LLM directly, captures the response, feeds it back). Save the raw
LLM responses to `docs/audits/2026-05-28-snails-v3-vs-v3.1/chassis-judge-v3-response.txt`
and `chassis-judge-v3.1-response.txt`; save the parsed dicts to
`chassis-judge.json` as `{"v3": {...}, "v3.1": {...}}`.

- [ ] **Step 6: Check the two preregistered falsification conditions on v3.1**

Inspect the v3.1 chassis-judge output. Evaluate:

  - Condition 1: is `most_frequent_move_frequency` ≥ 0.50? If yes → DESIGN FAILS.
  - Condition 2: does `unsympathetic_critique` contain any of the listed
    substrings or match the regex? If yes → DESIGN FAILS.

Record the outcome in `scores.json` as either `falsification_outcome: "passed"`
(neither condition fired) or `falsification_outcome: "failed-condition-N"` with
the specific condition number(s). Record honestly even if it's a failure.

- [ ] **Step 7: Score both essays with the reading council**

Same five-persona role-play protocol as the prior audit (see
`docs/audits/2026-05-27-longfellow-liveness-before-after/scores.json` for the
shape). Persona scores → `reading-council-v3-personas.json` /
`reading-council-v3.1-personas.json`. Aggregate via
`skills/review-conductor/scripts/reading_scores.py`. Add the aggregated results
to `scores.json` under `reading_council`.

- [ ] **Step 8: Write the audit README**

Create `docs/audits/2026-05-28-snails-v3-vs-v3.1/README.md` summarising:

  - The topic (snails) and what changed (snails-v3 → snails-v3.1 via the
    `add-voice-anti-monotony` design).
  - Side-by-side table: deterministic telemetry (chassis_uniformity findings,
    humanity_token_closers per_1000, nPVI, burstiness, Flesch, ornament).
  - Side-by-side table: chassis_judge fields (most_frequent_move,
    most_frequent_move_frequency, single_move_summary, unsympathetic_critique).
  - Side-by-side table: reading council (enjoyment, flow, style, quality, overall).
  - **The falsification check**: which conditions fired, which did not, and
    therefore whether the design passed.
  - Honest caveats (same as prior audit): single-author non-blind rewrite,
    suite-scoring-own-output disclosure, what the instruments do and do not
    measure, any composite saturation noted.
  - Quotes the canonical preregistration commit SHA so the audit's pre-/post-
    order is verifiable from git history.

- [ ] **Step 9: Commit**

```
git add docs/audits/2026-05-28-snails-v3-vs-v3.1/
git commit -m "Add snails v3-vs-v3.1 audit with preregistered falsification result"
```

---

## Final verification

After all 7 tasks:

```
cd C:\Users\charl\.config\superpowers\worktrees\russellian-book-suite\feat-voice-anti-monotony\skills\russellian-style
python -m pytest tests/ -q
```

Expected: all tests pass or skip (spaCy-gated tests skip on hosts without the model). New test files (`test_humanity_token_closers.py`, `test_chassis_uniformity.py`, `test_chassis_judge.py`) all run regardless of spaCy.

Then run the finishing-a-development-branch skill to push the branch + open a PR. PR base: `feat/longfellow-liveness` until that branch merges, then rebase onto `main`.
