# HFR v2 — Plan 4 of 5: triadic-voice-v2 Generation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Build the `triadic-voice-v2` skill — the v2 in-session generator. Generation itself is performed by the running model (no API, like v1); v2 adds **deterministic, testable helpers** the protocol and the Plan-5 harness call: a register router, a six-archetype chassis library, a profile-driven target formatter, an anti-copy alarm, and a brief assembler that composes them. The v1 `triadic-voice` skill is left frozen as the 20×20 control.

**Architecture:** Pure-stdlib helpers (no spaCy/model needed — register routing is a keyword heuristic; anti-copy uses word n-grams). The `SKILL.md` is the generation protocol: the model calls `build_generation_brief(topic)`, grounds in the corpus by the brief's exemplar query, writes the passage following the chosen chassis and the numeric targets, then self-checks the draft with `anti_copy`. The profile read is the committed `liveliness-signals` asset.

**Tech Stack:** Python 3.14, stdlib only (`json`, `re`, `collections`). One new skill: `triadic-voice-v2`.

## Plan set (this is Plan 4 of 5)
1–3c. DONE (profile, floor, 8 signals)
4. **triadic-voice-v2 generation** ← this plan
5. Evaluation (`voice-eval` 20×20 harness) — consumes this generator + the 8 signals + the v2 floor

## Global Constraints
- Python `>=3.11`; live env 3.14. Helpers are **stdlib-only** (no spaCy, no model) so the skill is light and the 20×20 harness can call them cheaply.
- **v1 `triadic-voice` is FROZEN** (the 20×20 control). Do not modify `skills/triadic-voice/`. (REQ-TRIAD-007)
- Generation is **in-session, no API/key** — the helpers prepare inputs; the running model writes. (matches v1 doctrine)
- Reads the committed profile at `../liveliness-signals/assets/hoskinson-style-profile.json` (relative to the skill root); reads the corpus at `../russellian-style/assets/hoskinson-corpus/index.json` for anti-copy. Read-only.
- Tests carry `pytestmark = pytest.mark.windows_canary`, cite REQ IDs, output pristine. No AI attribution; terse commits.
- `ruff.toml` ignores E402/E731/E701/E702/E741; keep F-rules clean.
- Work from worktree `C:\Users\charl\russellian-book-suite-hfr-v2`; do NOT switch git branches; commit on the current branch.

---

### Task 1: Scaffold the `triadic-voice-v2` skill

**Files:**
- Create: `skills/triadic-voice-v2/pyproject.toml`, `skill_api.py`, `scripts/__init__.py`, `tests/__init__.py`, `SKILL.md`
- Test: `skills/triadic-voice-v2/tests/test_smoke.py`

- [ ] **Step 1: Write the failing smoke test**

```python
# skills/triadic-voice-v2/tests/test_smoke.py
"""Cites REQ-TRIAD-001 (skill scaffold)."""
import pytest
pytestmark = pytest.mark.windows_canary


def test_skill_api_version():
    import skill_api
    assert skill_api.API_VERSION == (0, 1)
```

- [ ] **Step 2: Run to confirm it fails**

Run: `cd skills/triadic-voice-v2 && python -m pytest tests/test_smoke.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'skill_api'`.

- [ ] **Step 3: Create scaffold files**

```toml
# skills/triadic-voice-v2/pyproject.toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "triadic-voice-v2"
version = "0.1.0"
description = "HFR v2 in-session generator: register router, chassis library, profile targets, anti-copy"
requires-python = ">=3.11"
dependencies = []

[project.optional-dependencies]
dev = ["pytest>=8.0,<10.0"]

[tool.setuptools]
packages = ["scripts"]

[tool.pytest.ini_options]
testpaths = ["tests"]
markers = ["windows_canary: platform-sensitive test that must run on Windows"]
addopts = "-q"
```

```python
# skills/triadic-voice-v2/skill_api.py
"""Public API surface of triadic-voice-v2."""
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
# skills/triadic-voice-v2/scripts/__init__.py
```
```python
# skills/triadic-voice-v2/tests/__init__.py
```

```markdown
<!-- skills/triadic-voice-v2/SKILL.md -->
---
name: triadic-voice-v2
description: HFR v2 generator. Same in-session Russell+Feynman+Hoskinson fusion as triadic-voice, but register-routed, chassis-varied, and profile-target-driven, with an anti-copy self-check. Use when generating v2 passages for the HFR comparison. The running model is the generator; no API key.
license: MIT
metadata:
  author: charles-hoskinson
  version: 0.1.0
  category: writing
---

# triadic-voice-v2

(Protocol assembled in Task 6.) Helpers in `scripts/` prepare a generation brief;
the running model writes the passage and self-checks it.
```

- [ ] **Step 4: Build venv (dev only — stdlib) and run smoke**

Run:
```
cd skills/triadic-voice-v2
python -m venv .venv
.venv/Scripts/python.exe -m pip install -q -e ".[dev]"
.venv/Scripts/python.exe -m pytest tests/test_smoke.py -q
```
Expected: 1 passed. (Do not commit `.venv/`.)

- [ ] **Step 5: Commit**

```bash
git add skills/triadic-voice-v2/pyproject.toml skills/triadic-voice-v2/skill_api.py \
  skills/triadic-voice-v2/scripts/__init__.py skills/triadic-voice-v2/tests/__init__.py \
  skills/triadic-voice-v2/tests/test_smoke.py skills/triadic-voice-v2/SKILL.md
git commit -m "Scaffold triadic-voice-v2 skill"
```

---

### Task 2: Register router

**Files:**
- Create: `skills/triadic-voice-v2/scripts/register_router.py`
- Test: `skills/triadic-voice-v2/tests/test_register_router.py`

**Interfaces:** `route(topic: str) -> str` returning one of `technical-exposition | narrative-editorial | polemic`. Deterministic keyword heuristic; default `narrative-editorial`.

- [ ] **Step 1: Write the failing test**

```python
# skills/triadic-voice-v2/tests/test_register_router.py
"""Cites REQ-TRIAD-001 (register routing)."""
import pytest
pytestmark = pytest.mark.windows_canary
from scripts.register_router import route, REGISTERS


def test_routes_technical():
    assert route("How does the KZG commitment construction work mechanically?") == "technical-exposition"


def test_routes_polemic():
    assert route("Why 'trustless' is a myth everyone repeats and should stop saying") == "polemic"


def test_defaults_to_narrative():
    assert route("Sending the bit, not the dossier: what ZK proofs let you do") == "narrative-editorial"
    assert REGISTERS == ("technical-exposition", "narrative-editorial", "polemic")
```

- [ ] **Step 2: Run to confirm it fails**

Run: `cd skills/triadic-voice-v2 && .venv/Scripts/python.exe -m pytest tests/test_register_router.py -q`
Expected: FAIL — no `scripts.register_router`.

- [ ] **Step 3: Implement**

```python
# skills/triadic-voice-v2/scripts/register_router.py
"""Deterministic keyword router: topic -> register."""
from __future__ import annotations
import re

REGISTERS = ("technical-exposition", "narrative-editorial", "polemic")

_TECHNICAL = re.compile(
    r"\b(how does|how do|mechanic|construct|algorithm|protocol|implement|"
    r"formal|proof|prove|define|definition|architecture|circuit|equation|complexity)\b")
_POLEMIC = re.compile(
    r"\b(myth|wrong|everyone|everybody|stop saying|the truth about|overrated|"
    r"is a lie|debate|versus|vs\.?|critique|hype|should stop|nonsense)\b")


def route(topic: str) -> str:
    low = topic.lower()
    if _POLEMIC.search(low):
        return "polemic"
    if _TECHNICAL.search(low):
        return "technical-exposition"
    return "narrative-editorial"
```

- [ ] **Step 4: Run to confirm it passes**

Run: `cd skills/triadic-voice-v2 && .venv/Scripts/python.exe -m pytest tests/test_register_router.py -q`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add skills/triadic-voice-v2/scripts/register_router.py skills/triadic-voice-v2/tests/test_register_router.py
git commit -m "Add register router"
```

---

### Task 3: Chassis library

**Files:**
- Create: `skills/triadic-voice-v2/scripts/chassis.py`
- Test: `skills/triadic-voice-v2/tests/test_chassis.py`

**Interfaces:** `CHASSIS: list[dict]` (6 archetypes, each `{name, beats}`); `select(register: str, rotation: int) -> dict` — deterministic pick favoring register-appropriate archetypes, rotating by `rotation` so consecutive passages differ.

- [ ] **Step 1: Write the failing test**

```python
# skills/triadic-voice-v2/tests/test_chassis.py
"""Cites REQ-TRIAD-002 (six-archetype chassis library, rotated)."""
import pytest
pytestmark = pytest.mark.windows_canary
from scripts.chassis import CHASSIS, select


def test_library_has_six_archetypes():
    assert len(CHASSIS) == 6
    assert all(set(c) >= {"name", "beats"} and len(c["beats"]) >= 3 for c in CHASSIS)


def test_select_is_deterministic_and_rotates():
    a = select("narrative-editorial", 0)
    b = select("narrative-editorial", 1)
    assert a["name"] != b["name"]            # consecutive rotations differ
    assert select("narrative-editorial", 0)["name"] == a["name"]  # deterministic
```

- [ ] **Step 2: Run to confirm it fails**

Run: `cd skills/triadic-voice-v2 && .venv/Scripts/python.exe -m pytest tests/test_chassis.py -q`
Expected: FAIL — no `scripts.chassis`.

- [ ] **Step 3: Implement**

```python
# skills/triadic-voice-v2/scripts/chassis.py
"""The six HFR v2 chassis archetypes and a deterministic rotating selector."""
from __future__ import annotations

CHASSIS = [
    {"name": "objection-decomposition-verdict",
     "beats": ["state a hostile objection plainly", "decompose it into parts", "deliver an exact verdict"],
     "registers": ["polemic", "narrative-editorial"]},
    {"name": "definition-correction-worked-case-consequence",
     "beats": ["correct a wrong definition", "ground it in a worked case", "draw the consequence"],
     "registers": ["technical-exposition", "narrative-editorial"]},
    {"name": "concrete-scene-abstraction-boundary",
     "beats": ["open on a concrete scene", "lift to the abstraction", "name the boundary condition"],
     "registers": ["narrative-editorial", "technical-exposition"]},
    {"name": "false-slogan-causal-account-replacement",
     "beats": ["quote a false slogan", "give the causal account", "state the exact replacement claim"],
     "registers": ["polemic", "narrative-editorial"]},
    {"name": "inverted-funnel",
     "beats": ["Russell open: the unhedged thesis", "Feynman develop: unpack by analogy", "Hoskinson close: candid takeaway"],
     "registers": ["technical-exposition", "polemic"]},
    {"name": "feynman-sandwich",
     "beats": ["Feynman open: drop into a concrete scenario", "Russell core: the exact mechanism", "Feynman close: return to the scene"],
     "registers": ["narrative-editorial", "technical-exposition"]},
]


def select(register: str, rotation: int) -> dict:
    pool = [c for c in CHASSIS if register in c["registers"]] or CHASSIS
    return pool[rotation % len(pool)]
```

- [ ] **Step 4: Run to confirm it passes**

Run: `cd skills/triadic-voice-v2 && .venv/Scripts/python.exe -m pytest tests/test_chassis.py -q`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add skills/triadic-voice-v2/scripts/chassis.py skills/triadic-voice-v2/tests/test_chassis.py
git commit -m "Add six-archetype chassis library with rotating selector"
```

---

### Task 4: Profile-target formatter

**Files:**
- Create: `skills/triadic-voice-v2/scripts/profile_targets.py`
- Test: `skills/triadic-voice-v2/tests/test_profile_targets.py`

**Interfaces:** `load_profile() -> dict` (reads the committed liveliness-signals asset); `targets(register: str, profile: dict) -> dict` returning `{sentence_len_band:(p10,p90), cadence_cv, discourse_marker_rate, direct_address_rate, example_spacing, modifier_budget}`; `as_prompt(t: dict) -> str` a one-paragraph injectable spec.

- [ ] **Step 1: Write the failing test**

```python
# skills/triadic-voice-v2/tests/test_profile_targets.py
"""Cites REQ-TRIAD-003 (profile-driven statistical targets)."""
import pytest
pytestmark = pytest.mark.windows_canary
from scripts.profile_targets import targets, as_prompt

PROFILE = {"registers": {"narrative-editorial": {
    "cadence": {"p10": 4.0, "p90": 28.0, "cv": 0.55},
    "diction": {"discourse_marker_rate": 0.2, "direct_address_rate": 0.3, "example_spacing": 3.0},
    "modifier": {"p90": 0.24}}}}


def test_targets_shape_and_values():
    t = targets("narrative-editorial", PROFILE)
    assert t["sentence_len_band"] == (4.0, 28.0)
    assert t["cadence_cv"] == 0.55
    assert 0.0 <= t["modifier_budget"] <= 1.0


def test_as_prompt_is_injectable_text():
    s = as_prompt(targets("narrative-editorial", PROFILE))
    assert "sentence length" in s.lower() and "4" in s and "28" in s
```

- [ ] **Step 2: Run to confirm it fails**

Run: `cd skills/triadic-voice-v2 && .venv/Scripts/python.exe -m pytest tests/test_profile_targets.py -q`
Expected: FAIL — no `scripts.profile_targets`.

- [ ] **Step 3: Implement**

```python
# skills/triadic-voice-v2/scripts/profile_targets.py
"""Format per-register corpus statistics into prompt-injectable generation targets."""
from __future__ import annotations
import json
from pathlib import Path

_PROFILE = Path(__file__).resolve().parent.parent.parent / "liveliness-signals" / "assets" / "hoskinson-style-profile.json"


def load_profile() -> dict:
    return json.loads(_PROFILE.read_text(encoding="utf-8"))


def targets(register: str, profile: dict) -> dict:
    reg = profile["registers"][register]
    cad, dic = reg["cadence"], reg["diction"]
    mod = reg.get("modifier", {})
    return {
        "sentence_len_band": (cad["p10"], cad["p90"]),
        "cadence_cv": cad["cv"],
        "discourse_marker_rate": dic["discourse_marker_rate"],
        "direct_address_rate": dic["direct_address_rate"],
        "example_spacing": dic["example_spacing"],
        "modifier_budget": mod.get("p90", 0.25),
    }


def as_prompt(t: dict) -> str:
    lo, hi = t["sentence_len_band"]
    return (
        f"Cadence target: vary sentence length mostly between {lo:.0f} and {hi:.0f} words "
        f"(coefficient of variation near {t['cadence_cv']:.2f} — alternate short punches with longer unpacking). "
        f"Address the reader directly about {t['direct_address_rate']*100:.0f}% of sentences; "
        f"open roughly 1 sentence in {max(1, round(1/ max(t['discourse_marker_rate'],1e-6))) if t['discourse_marker_rate'] else 0} "
        f"with a discourse marker. Land a concrete example about every {t['example_spacing']:.0f} sentences. "
        f"Keep the modifier (adjective+adverb) ratio at or below {t['modifier_budget']:.2f}."
    )
```

- [ ] **Step 4: Run to confirm it passes**

Run: `cd skills/triadic-voice-v2 && .venv/Scripts/python.exe -m pytest tests/test_profile_targets.py -q`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add skills/triadic-voice-v2/scripts/profile_targets.py skills/triadic-voice-v2/tests/test_profile_targets.py
git commit -m "Add profile-driven target formatter"
```

---

### Task 5: Anti-copy alarm

**Files:**
- Create: `skills/triadic-voice-v2/scripts/anti_copy.py`
- Test: `skills/triadic-voice-v2/tests/test_anti_copy.py`

**Interfaces:** `word_ngrams(text, n=4) -> set[tuple]`; `check(draft: str, corpus_texts: list[str], taboo: list[str] = ()) -> dict` returning `{"shared_ngrams":[...], "taboo_hits":[...], "alarm": bool}`. Alarm fires if any shared 4-gram with the corpus or any taboo phrase appears.

- [ ] **Step 1: Write the failing test**

```python
# skills/triadic-voice-v2/tests/test_anti_copy.py
"""Cites REQ-TRIAD-006 (anti-copy n-gram + taboo alarm)."""
import pytest
pytestmark = pytest.mark.windows_canary
from scripts.anti_copy import check, word_ngrams


def test_verbatim_run_trips_alarm():
    corpus = ["you have to learn how to walk before you can run in this space"]
    draft = "Remember, you have to learn how to walk before you can run, always."
    out = check(draft, corpus)
    assert out["alarm"] is True
    assert out["shared_ngrams"]


def test_original_prose_is_clean():
    corpus = ["a totally unrelated sentence about farming and weather patterns here"]
    draft = "Zero-knowledge proofs decompose one trust into seven testable bets."
    out = check(draft, corpus, taboo=["send the bit not the dossier"])
    assert out["alarm"] is False
    assert not out["shared_ngrams"] and not out["taboo_hits"]
```

- [ ] **Step 2: Run to confirm it fails**

Run: `cd skills/triadic-voice-v2 && .venv/Scripts/python.exe -m pytest tests/test_anti_copy.py -q`
Expected: FAIL — no `scripts.anti_copy`.

- [ ] **Step 3: Implement**

```python
# skills/triadic-voice-v2/scripts/anti_copy.py
"""Anti-copy alarm: flag verbatim n-gram overlap with the corpus + taboo phrases."""
from __future__ import annotations
import re

_WORD = re.compile(r"[a-z0-9']+")


def _tokens(text: str) -> list[str]:
    return _WORD.findall(text.lower())


def word_ngrams(text: str, n: int = 4) -> set:
    toks = _tokens(text)
    return {tuple(toks[i:i + n]) for i in range(len(toks) - n + 1)}


def check(draft: str, corpus_texts: list[str], taboo: list[str] = ()) -> dict:
    draft_grams = word_ngrams(draft, 4)
    corpus_grams: set = set()
    for t in corpus_texts:
        corpus_grams |= word_ngrams(t, 4)
    shared = sorted(" ".join(g) for g in (draft_grams & corpus_grams))
    low = draft.lower()
    taboo_hits = [p for p in taboo if p.lower() in low]
    return {"shared_ngrams": shared, "taboo_hits": taboo_hits,
            "alarm": bool(shared or taboo_hits)}
```

- [ ] **Step 4: Run to confirm it passes**

Run: `cd skills/triadic-voice-v2 && .venv/Scripts/python.exe -m pytest tests/test_anti_copy.py -q`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add skills/triadic-voice-v2/scripts/anti_copy.py skills/triadic-voice-v2/tests/test_anti_copy.py
git commit -m "Add anti-copy n-gram and taboo alarm"
```

---

### Task 6: Brief assembler + the v2 generation protocol (SKILL.md)

**Files:**
- Create: `skills/triadic-voice-v2/scripts/brief.py`
- Modify: `skills/triadic-voice-v2/skill_api.py` (export `build_generation_brief`)
- Overwrite: `skills/triadic-voice-v2/SKILL.md` (the full protocol)
- Test: `skills/triadic-voice-v2/tests/test_brief.py`

**Interfaces:** `build_generation_brief(topic: str, rotation: int = 0, profile: dict|None = None) -> dict` returning `{topic, register, chassis, targets, targets_prompt, exemplar_query}`. The in-session model reads this brief, grounds in the corpus exemplars matching `exemplar_query`, writes the passage, then runs `anti_copy.check` on its draft.

- [ ] **Step 1: Write the failing test**

```python
# skills/triadic-voice-v2/tests/test_brief.py
"""Cites REQ-TRIAD-004, REQ-TRIAD-005 (brief composes router+chassis+targets)."""
import pytest
pytestmark = pytest.mark.windows_canary
from scripts.brief import build_generation_brief

PROFILE = {"registers": {"narrative-editorial": {
    "cadence": {"p10": 4.0, "p90": 28.0, "cv": 0.55},
    "diction": {"discourse_marker_rate": 0.2, "direct_address_rate": 0.3, "example_spacing": 3.0},
    "modifier": {"p90": 0.24}}}}


def test_brief_composes_all_parts():
    b = build_generation_brief("Sending the bit, not the dossier", rotation=0, profile=PROFILE)
    assert b["register"] == "narrative-editorial"
    assert set(b["chassis"]) >= {"name", "beats"}
    assert b["targets"]["sentence_len_band"] == (4.0, 28.0)
    assert "cadence target" in b["targets_prompt"].lower()
    assert b["exemplar_query"]["register"] == "narrative-editorial"
```

- [ ] **Step 2: Run to confirm it fails**

Run: `cd skills/triadic-voice-v2 && .venv/Scripts/python.exe -m pytest tests/test_brief.py -q`
Expected: FAIL — no `scripts.brief`.

- [ ] **Step 3: Implement the assembler**

```python
# skills/triadic-voice-v2/scripts/brief.py
"""Compose register + chassis + profile targets into one generation brief."""
from __future__ import annotations

from scripts.register_router import route
from scripts.chassis import select
from scripts.profile_targets import targets, as_prompt, load_profile


def build_generation_brief(topic: str, rotation: int = 0, profile=None) -> dict:
    if profile is None:
        profile = load_profile()
    register = route(topic)
    chassis = select(register, rotation)
    t = targets(register, profile)
    return {
        "topic": topic,
        "register": register,
        "chassis": chassis,
        "targets": t,
        "targets_prompt": as_prompt(t),
        "exemplar_query": {"register": register, "move": chassis["name"]},
    }
```

- [ ] **Step 4: Export it + run the test**

Append to `skills/triadic-voice-v2/skill_api.py`:
```python
from scripts.brief import build_generation_brief  # noqa: E402
__all__.append("build_generation_brief")
```
Run: `cd skills/triadic-voice-v2 && .venv/Scripts/python.exe -m pytest tests/test_brief.py -q`
Expected: 1 passed.

- [ ] **Step 5: Write the full SKILL.md protocol**

Overwrite `skills/triadic-voice-v2/SKILL.md` with the generation protocol (front matter unchanged; body below):

```markdown
# triadic-voice-v2

The v2 HFR generator. Same fused Russell+Feynman+Hoskinson voice and same in-session
doctrine as `triadic-voice` (the running model writes; no API key), but generation is
register-routed, chassis-varied, profile-target-driven, and anti-copy-checked. The v1
`triadic-voice` skill is unchanged and remains the comparison control.

## How to generate (in-session)

1. **Build the brief.** Call `build_generation_brief(topic, rotation)` (from `skill_api`).
   It returns the `register`, a `chassis` (beat plan), numeric `targets` + an injectable
   `targets_prompt`, and an `exemplar_query`. `rotation` increments per passage so the
   chassis varies across a batch.
2. **Ground in the real voice.** Read 6–10 Hoskinson corpus entries matching the
   `exemplar_query` (register + rhetorical move) and the fusion guide
   `../russellian-style/references/triadic-voice-guide.md`. Study cadence; never copy wording.
3. **Plan, then adapt, beat by beat.** Write the passage following the chassis `beats` in
   order. After each beat, check it against the `targets_prompt` (cadence band, direct
   address, example spacing, modifier budget) and the discipline floor; revise the beat
   before moving on. This is the plan-then-adapt loop — not one-shot.
4. **Self-check copying.** Run `anti_copy.check(draft, corpus_texts, taboo)` on the finished
   draft. If `alarm` is true, rewrite the flagged spans — never ship a verbatim corpus run.
5. **Clear the floor.** The passage must pass the `russellian-style` v2 floor for its
   register (`--ruleset russellian-rules-v2.json --register <register>`). Liveliness signals
   are advisory, not gates.

## What v2 changes vs v1
Register routing (technical/narrative/polemic dials), a rotating six-archetype chassis
(not the fixed open-Hoskinson/develop-Feynman/close-Russell), corpus-derived numeric
targets injected into the write, and an explicit anti-copy gate.

## Helpers
`scripts/register_router.py`, `scripts/chassis.py`, `scripts/profile_targets.py`,
`scripts/anti_copy.py`, `scripts/brief.py`. All stdlib, deterministic, unit-tested.
```

- [ ] **Step 6: Run the full skill suite + a manual brief smoke**

Run:
```
cd skills/triadic-voice-v2 && .venv/Scripts/python.exe -m pytest -q
.venv/Scripts/python.exe -c "import skill_api; b=skill_api.build_generation_brief('Why \\'trustless\\' is a myth', 0); print(b['register'], b['chassis']['name']); print(b['targets_prompt'][:120])"
```
Expected: all tests pass; the smoke prints `polemic`, a chassis name, and a targets sentence (this confirms the brief composes against the real committed profile).

- [ ] **Step 7: Commit**

```bash
git add skills/triadic-voice-v2/scripts/brief.py skills/triadic-voice-v2/skill_api.py \
  skills/triadic-voice-v2/SKILL.md skills/triadic-voice-v2/tests/test_brief.py
git commit -m "Add brief assembler and v2 generation protocol"
```

---

## Self-Review

**Spec coverage (REQ-TRIAD):**
- REQ-TRIAD-001 (register router) → Task 2; brief uses it (Task 6).
- REQ-TRIAD-002 (six-archetype chassis, rotated) → Task 3.
- REQ-TRIAD-003 (profile-driven targets injected) → Task 4; `targets_prompt` is the injectable form.
- REQ-TRIAD-004 (retrieval by register+move tuple) → Task 6 `exemplar_query`; the protocol step 2 consumes it. (Full embedding retrieval is out of scope; the tuple query over the existing corpus tags is the v1 mechanism.)
- REQ-TRIAD-005 (per-beat plan-then-adapt) → SKILL.md step 3 (protocol; the model executes it in-session).
- REQ-TRIAD-006 (anti-copy alarm) → Task 5; the protocol step 4 runs it.
- REQ-TRIAD-007 (v1 frozen) → `skills/triadic-voice/` never touched; Global Constraints pin it.

**Note on testability:** the deterministic helpers (router, chassis, targets, anti-copy, brief) are unit-tested; the generation itself is in-session prose the model produces by following SKILL.md — verified structurally by the brief smoke (Task 6 Step 6) and substantively by the Plan-5 20×20 (where v2 output is scored and judged against v1).

**Deferred to Plan 5 / follow-on:** embedding-based exemplar retrieval; the actual 20 v2 generations (Plan 5 drives them); feynman-style delegation.

**Placeholder scan:** none — every step has runnable code + commands + expected output.

**Type consistency:** `route`→`select`→`targets`/`as_prompt` are composed by `build_generation_brief`; `anti_copy.check` is independent and called by the protocol. The brief dict shape is fixed and consumed by Plan 5's harness.
