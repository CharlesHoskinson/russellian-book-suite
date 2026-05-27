# Russellian Voice Calibration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Append a `# Calibration and planning` section to each of the three
russellian-style mode system prompts, adding a silent paragraph-motion planning
directive, mode-matched corpus anchors, and one verified public-domain Russell
touchstone per mode.

**Architecture:** Approach A from the design — inline per-mode edits, no loader change.
`system_prompt_loader.load(mode)` already reads each mode file verbatim into the
composition stage, so appending a section is sufficient. A new parametrized test
enforces the calibration contract across all modes. The corpus, loader, and linters are
untouched.

**Tech Stack:** Python 3.11+, pytest. Markdown prompt files. No new dependencies (the
calibration test reads files through the loader and needs no spaCy).

**Spec:** `openspec/changes/add-voice-calibration-prompts/` (REQ-VOICE-001..007) and
`docs/specs/2026-05-27-russellian-voice-calibration-design.md`.

---

## File structure

- Create: `skills/russellian-style/tests/test_system_prompt_calibration.py`
  — parametrized calibration contract over `VALID_MODES`.
- Modify: `skills/russellian-style/assets/system-prompts/technical-exposition.md`
  — append calibration section.
- Modify: `skills/russellian-style/assets/system-prompts/narrative-editorial.md`
  — append calibration section.
- Modify: `skills/russellian-style/assets/system-prompts/polemic.md`
  — append calibration section.
- Create: `docs/audits/2026-05-27-russellian-voice-calibration/` — validation bundle
  (essays, lint output, readme).

## Verified touchstones (do not alter; verified verbatim during planning)

| Mode | Source + URL | Verbatim excerpt | Corpus row |
|---|---|---|---|
| technical-exposition | The Problems of Philosophy — https://www.gutenberg.org/cache/epub/5827/pg5827-images.html | "Philosophy is to be studied, not for the sake of any definite answers to its questions, since no definite answers can, as a rule, be known to be true, but rather for the sake of the questions themselves." (excerpt; original continues after a semicolon) | problems-010 |
| narrative-editorial | The Analysis of Mind — https://www.gutenberg.org/cache/epub/2529/pg2529-images.html | "[You] put a hungry animal, say a cat, in a cage which has a door that can be opened by lifting a latch; outside the cage you put food. The cat at first dashes all round the cage, making frantic efforts to force a way out." (bracketed capital adjusts the original lower-case "you") | analysis-008 |
| polemic | Free Thought and Official Propaganda — https://www.gutenberg.org/cache/epub/44932/pg44932-images.html | "William James used to preach the 'will to believe.' For my part, I should wish to preach the 'will to doubt.'" | free-001 |

Re-verify with the plain-text editions if needed:

```bash
curl -sL -A "Mozilla/5.0" https://www.gutenberg.org/cache/epub/5827/pg5827.txt | grep -n "for the sake of the questions themselves"
curl -sL -A "Mozilla/5.0" https://www.gutenberg.org/cache/epub/44932/pg44932.txt | grep -n "will to doubt"
curl -sL -A "Mozilla/5.0" https://www.gutenberg.org/cache/epub/2529/pg2529.txt | grep -n "dashes all round the cage"
```

## Environment note

Run tests from the skill root so `scripts` is importable (matches the existing
`test_system_prompt_loader.py`):

```bash
cd skills/russellian-style
.venv/Scripts/python.exe -m pytest tests/ -q          # Windows
.venv/bin/python -m pytest tests/ -q                  # POSIX
```

If the junction-linked `.venv` is missing in a fresh clone:
`python -m venv .venv && .venv/Scripts/pip install -e ".[dev]"`. The calibration test
needs no spaCy; the linters in Task 6 do.

---

### Task 1: Calibration contract test (red)

**Files:**
- Create: `skills/russellian-style/tests/test_system_prompt_calibration.py`

- [ ] **Step 1: Write the failing test**

```python
"""Calibration contract for mode system prompts.

Cites REQ-VOICE-001, REQ-VOICE-002, REQ-VOICE-003, REQ-VOICE-004, REQ-VOICE-007.
"""
import pytest

pytestmark = pytest.mark.windows_canary

from scripts.system_prompt_loader import load, VALID_MODES

MOTION_SEQUENCE = "concession → example → distinction → consequence → turn"


@pytest.mark.parametrize("mode", sorted(VALID_MODES))
def test_REQ_VOICE_001_calibration_heading_present(mode):
    assert "# Calibration and planning" in load(mode)


@pytest.mark.parametrize("mode", sorted(VALID_MODES))
def test_REQ_VOICE_002_planning_motion_sequence_present(mode):
    assert MOTION_SEQUENCE in load(mode)


@pytest.mark.parametrize("mode", sorted(VALID_MODES))
def test_REQ_VOICE_002_plan_is_not_emitted(mode):
    assert "not emit" in load(mode).lower()


@pytest.mark.parametrize("mode", sorted(VALID_MODES))
def test_REQ_VOICE_003_004_attributed_anchor_present(mode):
    text = load(mode)
    assert "russell-corpus-map.md" in text          # mode-matched move anchors
    assert "gutenberg.org" in text                  # touchstone source attribution
    assert "Touchstone" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd skills/russellian-style && .venv/Scripts/python.exe -m pytest tests/test_system_prompt_calibration.py -v`
Expected: FAIL — all parametrizations fail the assertions (no calibration section in the
files yet).

(No commit yet; the section is added in Tasks 2-4, committed together in Task 5.)

---

### Task 2: Calibration section — technical-exposition

**Files:**
- Modify: `skills/russellian-style/assets/system-prompts/technical-exposition.md`

- [ ] **Step 1: Append the section to the end of the file**

```markdown

# Calibration and planning

- Before drafting, map the paragraph's motion: concession → example → distinction → consequence → turn. Decide where the turn lands. This plan is private; do not emit it — only the prose ships.
- Mode anchors (see `references/russell-corpus-map.md`): define an abstraction through an ordinary case before naming it (problems-001); raise the counterexample before stating the conclusion (problems-002); classify the alternatives before evaluating them (external-007); end on a reversal that changes the reader's valuation (problems-010).
- Dry understatement, not exclamation: let a weak or absurd view show through exact statement. The precision does the work emphasis would spoil.
- Touchstone. Flat: "Philosophy raises many important and multifaceted questions worth considering." Russell, turning uncertainty into value (The Problems of Philosophy, https://www.gutenberg.org/cache/epub/5827/pg5827-images.html): "Philosophy is to be studied, not for the sake of any definite answers to its questions, since no definite answers can, as a rule, be known to be true, but rather for the sake of the questions themselves." Copy the motion and the register, never the words.
```

- [ ] **Step 2: Run the calibration test for this mode**

Run: `cd skills/russellian-style && .venv/Scripts/python.exe -m pytest tests/test_system_prompt_calibration.py -v -k technical-exposition`
Expected: PASS for the four `technical-exposition` parametrizations.

---

### Task 3: Calibration section — narrative-editorial

**Files:**
- Modify: `skills/russellian-style/assets/system-prompts/narrative-editorial.md`

- [ ] **Step 1: Append the section to the end of the file**

```markdown

# Calibration and planning

- Before drafting a scene, map its motion: concession → example → distinction → consequence → turn. Decide which concrete detail carries the turn. This plan is private; do not emit it — only the prose ships.
- Mode anchors (see `references/russell-corpus-map.md`): ground an abstraction in a vivid empirical sequence with a real actor (analysis-008); put a mistaken view into a recognizable human figure rather than an abstraction (problems-007).
- Dry understatement, not exclamation: let the absurd show through precise description. Do not name the feeling; describe the action and let the reader infer it.
- Touchstone. Flat: "Researchers conducted experiments that demonstrated how animals gradually acquire learned behaviours over time." Russell, grounding learning in a scene (The Analysis of Mind, https://www.gutenberg.org/cache/epub/2529/pg2529-images.html): "[You] put a hungry animal, say a cat, in a cage which has a door that can be opened by lifting a latch; outside the cage you put food. The cat at first dashes all round the cage, making frantic efforts to force a way out." Copy the concreteness and pacing, never the words.
```

- [ ] **Step 2: Run the calibration test for this mode**

Run: `cd skills/russellian-style && .venv/Scripts/python.exe -m pytest tests/test_system_prompt_calibration.py -v -k narrative-editorial`
Expected: PASS for the four `narrative-editorial` parametrizations.

---

### Task 4: Calibration section — polemic

**Files:**
- Modify: `skills/russellian-style/assets/system-prompts/polemic.md`

- [ ] **Step 1: Append the section to the end of the file**

(polemic already mandates dry irony, so no extra understatement line.)

```markdown

# Calibration and planning

- Before drafting, map the argument's motion: concession → example → distinction → consequence → turn. Decide where the closing verdict reverses the opener. This plan is private; do not emit it — only the prose ships.
- Mode anchors (see `references/russell-corpus-map.md`): build the section around a memorable reversal that sets belief against rational doubt (free-001); personify the prevailing view as a human figure (problems-007); ground the charge in a named figure or institution (free-005); state both sides of a principle in the same paragraph before choosing (political-006).
- Touchstone. Flat: "It is important to note that one should stay open-minded and avoid believing things without sufficient evidence." Russell, compressing the reversal into an antithesis (Free Thought and Official Propaganda, https://www.gutenberg.org/cache/epub/44932/pg44932-images.html): "William James used to preach the 'will to believe.' For my part, I should wish to preach the 'will to doubt.'" Copy the antithesis and the compression, never the words.
```

- [ ] **Step 2: Run the calibration test for this mode**

Run: `cd skills/russellian-style && .venv/Scripts/python.exe -m pytest tests/test_system_prompt_calibration.py -v -k polemic`
Expected: PASS for the four `polemic` parametrizations.

---

### Task 5: Full suite green + commit

**Files:** none new.

- [ ] **Step 1: Run the calibration test across all modes**

Run: `cd skills/russellian-style && .venv/Scripts/python.exe -m pytest tests/test_system_prompt_calibration.py -v`
Expected: PASS — all 12 parametrizations.

- [ ] **Step 2: Run the full russellian-style suite (regression guard)**

Run: `cd skills/russellian-style && .venv/Scripts/python.exe -m pytest tests/ -q`
Expected: PASS — including the existing `test_system_prompt_loader.py` (REQ-VOICE-006:
the loader is unchanged).

- [ ] **Step 3: Confirm scope guard (REQ-VOICE-006)**

Run: `cd /c/russellian-book-suite && git status --short`
Expected: only the test file and the three `system-prompts/*.md` files are modified.
`system_prompt_loader.py`, `assets/russell-corpus/index.json`,
`references/russell-corpus-map.md`, and the linter scripts must NOT appear.

- [ ] **Step 4: Commit**

```bash
cd /c/russellian-book-suite
git add skills/russellian-style/tests/test_system_prompt_calibration.py \
        skills/russellian-style/assets/system-prompts/technical-exposition.md \
        skills/russellian-style/assets/system-prompts/narrative-editorial.md \
        skills/russellian-style/assets/system-prompts/polemic.md
git commit -m "Add voice calibration to russellian-style mode prompts"
```

---

### Task 6: Validation bundle

**Files:**
- Create: `docs/audits/2026-05-27-russellian-voice-calibration/baseline-polemic.md`
- Create: `docs/audits/2026-05-27-russellian-voice-calibration/candidate-polemic.md`
- Create: `docs/audits/2026-05-27-russellian-voice-calibration/lint-results.md`
- Create: `docs/audits/2026-05-27-russellian-voice-calibration/README.md`

- [ ] **Step 1: Draft two 600-word essays titled "On the Absurdities of Artificial Intelligences Governing Human Passions"**

`baseline-polemic.md`: drafted following the pre-change `polemic.md` (the version before
Task 4). `candidate-polemic.md`: drafted following the revised `polemic.md`, applying
the silent motion plan and the anchors. Both essays are original prose; neither reuses
the touchstone wording.

- [ ] **Step 2: Lint both essays with the full linter set**

```bash
cd skills/russellian-style
for f in ../../docs/audits/2026-05-27-russellian-voice-calibration/baseline-polemic.md \
         ../../docs/audits/2026-05-27-russellian-voice-calibration/candidate-polemic.md; do
  echo "### $f"
  for L in lint_hedges lint_passive_voice lint_signal_density lint_sentence_rhythm \
           lint_listicle_abstract lint_parallel_structure lint_paragraph_motion \
           lint_ai_vocabulary lint_ai_staccato lint_burstiness \
           lint_concrete_instance_density lint_epistemic_precision; do
    echo "-- $L"; .venv/Scripts/python.exe scripts/$L.py "$f"
  done
done
```

Each linter prints JSON findings and exits 1 when it finds any, 0 when clean.

- [ ] **Step 3: Record results and assert acceptance**

Write `lint-results.md` with the per-linter finding counts for both essays. Acceptance
(REQ-VOICE: validation): the candidate essay has no more total findings than the
baseline on any linter, and the candidate shows non-empty `lint_paragraph_motion`
improvement or parity. If the candidate regresses on any linter, revise
`candidate-polemic.md` (not the linter) and re-run.

- [ ] **Step 4: Write the bundle README and commit**

`README.md` summarises what was tested, the prompt version under test, and the verdict.

```bash
cd /c/russellian-book-suite
git add docs/audits/2026-05-27-russellian-voice-calibration/
git commit -m "Add validation bundle for voice calibration prompts"
```

---

## Self-review (completed during planning)

- **Spec coverage:** REQ-VOICE-001 (Task 2-4 heading + Task 1 test); 002 (motion
  sequence + not-emit, Task 1 test + Tasks 2-4); 003 (mode anchors, Tasks 2-4, asserted
  via corpus-map reference in Task 1); 004 (touchstone + attribution, Tasks 2-4 + Task 1
  assertion); 005 (verbatim quotes — verified during planning, table above); 006 (scope
  guard, Task 5 Step 3); 007 (parametrized test, Task 1). All requirements map to tasks.
- **Placeholder scan:** none — all prompt text and commands are literal.
- **Type/name consistency:** the test references `load` and `VALID_MODES` exactly as
  exported by `system_prompt_loader.py`; the heading string `# Calibration and planning`
  and `MOTION_SEQUENCE` match the appended sections character-for-character.

## Not in scope

- Corpus expansion (`tools/build-russell-corpus`).
- Corpus-driven prompt assembly at load time (revisit at ~500 corpus entries).
- Opening the PR / running CI — operator's decision; this plan does not push.
