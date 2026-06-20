# HFR v2 — Plan 5 of 5: voice-eval 20×20 Test Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a new `voice-eval` skill that runs the HFR **20×20 acceptance test** — generate 20 prompts × {v1 `triadic-voice`, v2 `triadic-voice-v2`} = 40 passages, gate all 40 through the `russellian-style` **v1** floor, score them on the 8 liveliness signals for per-signal deltas, run a blind order-swapped in-session pairwise judge with win-rate + CIs, monitor formula-drift, emit a pass/fail success report, and ship a blind A/B human-study scaffold with a signal-graduation gate.

**Architecture:** Generation **and** judging are performed **in-session by the running model** (no API, exactly like `triadic-voice`/`triadic-voice-v2`). The skill is therefore a set of **deterministic, unit-tested Python helpers** (prompt set, arm orchestration over injected callables, floor gate, signal deltas, ballot construction, win-rate stats, drift, report, human-study scaffold) plus an **in-session run protocol** in `SKILL.md`. Tests never call a live LLM: generation and judging are injected `Callable`s and stubbed. Cross-skill calls (`liveliness-signals`, `russellian-style`, `triadic-voice-v2`) go through a repo-sibling-first `sibling_skills` bridge mirroring `book-compose`.

**Tech Stack:** Python 3.14, stdlib (`json`/`statistics`/`math`/`collections`), spaCy `en_core_web_sm` (only via the sibling signal scorers; this skill adds no new model dependency). Mirrors `triadic-voice-v2` skill conventions.

**Spec source of truth:** `docs/specs/2026-06-19-hfr-v2-liveliness-design.md` § "Component 5 — Evaluation: the 20×20 final test (`voice-eval`)" and OpenSpec `openspec/changes/add-hfr-v2-liveliness/specs/voice-eval/spec.md` (REQ-VEVAL-009..017).

## Plan set (this is Plan 5 of 5)

1. Corpus Style-Profile (`liveliness-signals` profiler) — written + implemented
2. Floor calibration (`russellian-style` v2 ruleset) — written + implemented
3. Liveliness signals (8 scorers, 3a/3b/3c) — written + implemented
4. Generation v2 (`triadic-voice-v2`) — written + implemented
5. **Evaluation (`voice-eval` 20×20 harness)** ← this plan (depends on 1–4; all four shipped on this branch)

## Global Constraints

- Python `requires-python = ">=3.11"`; the live environment is Python 3.14. (spec)
- The harness is **offline and deterministic** for fixed inputs. Generation and judgment are **injected callables** in code and **the running model** in session — never a live network call inside the skill or its tests. (design § "TDD per repo convention"; REQ-VEVAL-012)
- **No positive signal gates** in this plan; the floor gate uses the **v1** ruleset only. Detector/perplexity reads are advisory and never gate. (REQ-VEVAL-014)
- Cross-skill imports go through `scripts/sibling_skills.py` (repo-sibling-first, then `~/.claude/skills`), mirroring `skills/book-compose/scripts/sibling_skills.py`. The siblings consumed: `liveliness-signals` (signal scoring), `russellian-style` (floor battery + Russell-Delta), `triadic-voice-v2` (v2 brief). Read-only.
- Tests carry `pytestmark = pytest.mark.windows_canary`, cite REQ IDs in the module docstring, and use `tmp_path` for any file I/O. Tests that need spaCy carry the `needs_model` marker and are skip-gated by `conftest.py`. (repo convention)
- No "Co-Authored-By"/AI attribution in commits; terse human-style imperative messages, one problem per commit. (repo CLAUDE.md / AGENTS.md)
- Test invocation: `cd skills/voice-eval && .venv/Scripts/python.exe -m pytest tests/ -q` (a per-skill venv is created in Task 1; on a machine without it, `python -m pytest` after `pip install -e ".[dev]"`).

---

## File Structure

### Created

```
skills/voice-eval/
├── pyproject.toml                      NEW — package + dev extra + pytest config
├── skill_api.py                        NEW — API_VERSION + public re-exports
├── SKILL.md                            NEW — in-session 20×20 run protocol
├── conftest.py                         NEW — spaCy needs_model skip-gate
├── scripts/
│   ├── __init__.py                     NEW
│   ├── sibling_skills.py               NEW — repo-first sibling module loader
│   ├── prompts.py                      NEW — load + validate the 20-prompt set
│   ├── arms.py                         NEW — run_arms: 40 passages via injected callables
│   ├── floor_gate.py                   NEW — equal-grounding v1 floor gate
│   ├── signal_deltas.py                NEW — per-signal mean delta v2−v1, overall + per register
│   ├── ballot.py                       NEW — order-swapped, length-matched pairwise ballots
│   ├── winrate.py                      NEW — verdict aggregation → win-rate + Wilson CI
│   ├── drift.py                        NEW — formula-drift (struct TF-IDF cosine + opening POS + analogy family)
│   ├── detector.py                     NEW — advisory-only detector read (never gates)
│   ├── report.py                       NEW — success-criterion + markdown report
│   └── human_study.py                  NEW — blind A/B scaffold + Fleiss κ + graduation gate
├── assets/
│   └── prompts-20x20.json              NEW — 20 prompts stratified 7/7/6
└── tests/
    ├── __init__.py                     NEW
    ├── test_smoke.py                   NEW
    ├── test_sibling_skills.py          NEW
    ├── test_prompts.py                 NEW
    ├── test_arms.py                    NEW
    ├── test_floor_gate.py              NEW
    ├── test_signal_deltas.py           NEW
    ├── test_ballot.py                  NEW
    ├── test_winrate.py                 NEW
    ├── test_drift.py                   NEW
    ├── test_detector.py                NEW
    ├── test_report.py                  NEW
    └── test_human_study.py             NEW
```

### Modified

```
skills/liveliness-signals/skill_api.py        export score_passage + SIGNAL_NAMES
.github/ci/skills-matrix.json                 register voice-eval (extra=dev, siblings)
openspec/README.md                            register VEVAL slug if absent
docs/plans/2026-06-19-hfr-v2-liveliness-corpus-profile.md   Plan-set pointer: Plan 5 written
openspec/changes/add-hfr-v2-liveliness/tasks.md             tick eval items as planned
```

---

## Task 1: Scaffold the `voice-eval` skill

**Files:**
- Create: `skills/voice-eval/pyproject.toml`
- Create: `skills/voice-eval/skill_api.py`
- Create: `skills/voice-eval/conftest.py`
- Create: `skills/voice-eval/scripts/__init__.py`
- Create: `skills/voice-eval/tests/__init__.py`
- Test: `skills/voice-eval/tests/test_smoke.py`

- [ ] **Step 1: Write the failing smoke test**

```python
# skills/voice-eval/tests/test_smoke.py
"""Cites REQ-VEVAL-009 (skill scaffold)."""
import pytest

pytestmark = pytest.mark.windows_canary


def test_skill_api_version():
    import skill_api
    assert skill_api.API_VERSION == (0, 1)
```

- [ ] **Step 2: Create the package files**

`skills/voice-eval/pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "voice-eval"
version = "0.1.0"
description = "HFR v2 evaluation: the 20x20 comparison harness, formula-drift monitor, and human-study scaffold"
requires-python = ">=3.11"
dependencies = []

[project.optional-dependencies]
dev = ["pytest>=8.0,<10.0"]

[tool.setuptools]
packages = ["scripts"]

[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
    "windows_canary: platform-sensitive test that must run on Windows",
    "needs_model: requires the en_core_web_sm spaCy model",
]
addopts = "-q"
```

`skills/voice-eval/skill_api.py`:

```python
"""Public API surface of voice-eval."""
from __future__ import annotations

from pathlib import Path
import sys

API_VERSION = (0, 1)
_SKILL_ROOT = Path(__file__).resolve().parent
if str(_SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(_SKILL_ROOT))

__all__ = ["API_VERSION"]
```

`skills/voice-eval/conftest.py` (mirrors `liveliness-signals/conftest.py`):

```python
"""Skip-gate spaCy-model tests when the model is absent (mirrors liveliness-signals)."""
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

`skills/voice-eval/scripts/__init__.py` and `skills/voice-eval/tests/__init__.py`: empty files.

- [ ] **Step 3: Create the venv and install**

```bash
cd skills/voice-eval
python -m venv .venv
.venv/Scripts/python.exe -m pip install -q -e ".[dev]"
```

- [ ] **Step 4: Run the smoke test, expect PASS**

Run: `cd skills/voice-eval && .venv/Scripts/python.exe -m pytest tests/test_smoke.py -q`
Expected: `1 passed`.

- [ ] **Step 5: Commit**

```bash
git add skills/voice-eval/pyproject.toml skills/voice-eval/skill_api.py skills/voice-eval/conftest.py skills/voice-eval/scripts/__init__.py skills/voice-eval/tests/__init__.py skills/voice-eval/tests/test_smoke.py
git commit -m "voice-eval: scaffold skill (pyproject, skill_api, conftest, smoke)"
```

---

## Task 2: Sibling bridge + expose `score_passage`

The harness must call three sibling skills. `book-compose/scripts/sibling_skills.py` is the canonical repo-sibling-first loader; we add a trimmed copy. We also re-export `score_passage` and the signal-name list from `liveliness-signals` so the harness has a stable surface.

**Files:**
- Modify: `skills/liveliness-signals/skill_api.py`
- Create: `skills/voice-eval/scripts/sibling_skills.py`
- Test: `skills/voice-eval/tests/test_sibling_skills.py`

- [ ] **Step 1: Export `score_passage` + `SIGNAL_NAMES` from `liveliness-signals`**

Append to `skills/liveliness-signals/skill_api.py` (after the existing `load_profile` export):

```python
def score_passage(text, register="narrative-editorial", profile=None):
    """Score one passage on the 8 liveliness signals. Returns {signal: score_dict}."""
    from scripts.score import score_passage as _sp
    return _sp(text, register=register, profile=profile)


__all__.append("score_passage")

SIGNAL_NAMES = (
    "cadence", "curiosity", "novelty_continuity", "worked_case",
    "verb_energy", "sv_distance", "concrete_anchor", "analogy_mapping",
)
__all__.append("SIGNAL_NAMES")
```

- [ ] **Step 2: Confirm the re-export imports cleanly**

Run: `cd skills/liveliness-signals && .venv/Scripts/python.exe -c "import skill_api; print(sorted(skill_api.__all__))"`
Expected: output includes `'SIGNAL_NAMES'` and `'score_passage'`.

- [ ] **Step 3: Write the failing sibling-bridge test**

```python
# skills/voice-eval/tests/test_sibling_skills.py
"""Cites REQ-VEVAL-011 (signal scoring via sibling) — repo-first resolution."""
import pytest

pytestmark = pytest.mark.windows_canary


def test_resolves_repo_sibling_root(tmp_path, monkeypatch):
    from scripts.sibling_skills import sibling_root, SiblingNotFoundError
    # russellian-style is a repo sibling of voice-eval; resolve must find it.
    root = sibling_root("russellian-style")
    assert (root / "SKILL.md").is_file()


def test_missing_sibling_raises():
    from scripts.sibling_skills import sibling_root, SiblingNotFoundError
    with pytest.raises(SiblingNotFoundError):
        sibling_root("no-such-skill")
```

- [ ] **Step 4: Run the test, expect FAIL**

Run: `cd skills/voice-eval && .venv/Scripts/python.exe -m pytest tests/test_sibling_skills.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.sibling_skills'`.

- [ ] **Step 5: Write `scripts/sibling_skills.py`**

```python
# skills/voice-eval/scripts/sibling_skills.py
"""Locate and load sibling skills (russellian-style, liveliness-signals,
triadic-voice-v2): the in-repo sibling FIRST, then the installed ~/.claude/skills
copy. Sibling modules use absolute ``from scripts.X`` imports that collide with this
skill's own ``scripts`` package, so each load swaps ``sys.path``/``sys.modules`` for
the sibling and restores them after, returning the loaded module.
"""
from __future__ import annotations

import contextlib
import importlib
import os
import sys
from pathlib import Path

_THIS_SKILL = Path(__file__).resolve().parents[1]      # skills/voice-eval
_SKILLS_DIR = _THIS_SKILL.parent                        # skills/


class SiblingNotFoundError(Exception):
    pass


def _installed_root(name: str) -> Path:
    home = Path(os.environ.get("USERPROFILE") or os.path.expanduser("~"))
    return home / ".claude" / "skills" / name


def sibling_root(name: str) -> Path:
    """Repo sibling first, then the installed copy. Must contain SKILL.md."""
    repo = _SKILLS_DIR / name
    if (repo / "SKILL.md").is_file():
        return repo
    installed = _installed_root(name)
    if (installed / "SKILL.md").is_file():
        return installed
    raise SiblingNotFoundError(f"sibling skill not found: {name}")


@contextlib.contextmanager
def _sibling_scripts(root: Path):
    saved = {k: sys.modules.pop(k) for k in list(sys.modules)
             if k == "scripts" or k.startswith("scripts.")}
    saved_path = sys.path[:]
    try:
        sys.path.insert(0, str(root))
        importlib.invalidate_caches()
        yield
    finally:
        for k in list(sys.modules):
            if k == "scripts" or k.startswith("scripts."):
                del sys.modules[k]
        sys.modules.update(saved)
        sys.path[:] = saved_path


def load_module(skill: str, dotted: str):
    """Import ``dotted`` (e.g. 'scripts.score') from sibling ``skill`` and return it.

    The returned module's functions must be called *inside* a ``using(skill)`` block
    when they themselves import sibling ``scripts.*`` at call time. The pure helpers
    we use (score_passage, voice_eval.evaluate, brief.build_generation_brief) bind
    their deps at import, so a plain post-load call is safe — but we re-enter the
    swap on each call via ``call`` for safety.
    """
    root = sibling_root(skill)
    with _sibling_scripts(root):
        return importlib.import_module(dotted)


def call(skill: str, dotted: str, func: str, *args, **kwargs):
    """Import ``skill``'s ``dotted`` module and call ``func`` with the sibling's
    ``scripts`` active for the duration of the call."""
    root = sibling_root(skill)
    with _sibling_scripts(root):
        mod = importlib.import_module(dotted)
        return getattr(mod, func)(*args, **kwargs)
```

- [ ] **Step 6: Run the test, expect PASS**

Run: `cd skills/voice-eval && .venv/Scripts/python.exe -m pytest tests/test_sibling_skills.py -q`
Expected: `2 passed`.

- [ ] **Step 7: Commit**

```bash
git add skills/liveliness-signals/skill_api.py skills/voice-eval/scripts/sibling_skills.py skills/voice-eval/tests/test_sibling_skills.py
git commit -m "voice-eval: repo-first sibling bridge; export score_passage from liveliness-signals"
```

---

## Task 3: Prompt set (20, stratified 7/7/6)

**Files:**
- Create: `skills/voice-eval/assets/prompts-20x20.json`
- Create: `skills/voice-eval/scripts/prompts.py`
- Test: `skills/voice-eval/tests/test_prompts.py`

REQ-VEVAL-009: 20 prompts stratified across the three registers (`technical-exposition`, `narrative-editorial`, `polemic`), split 7/7/6.

- [ ] **Step 1: Write the failing test**

```python
# skills/voice-eval/tests/test_prompts.py
"""Cites REQ-VEVAL-009 (20-prompt stratified set)."""
import pytest

pytestmark = pytest.mark.windows_canary

REGISTERS = {"technical-exposition", "narrative-editorial", "polemic"}


def test_loads_exactly_twenty_unique_prompts():
    from scripts.prompts import load_prompts
    ps = load_prompts()
    assert len(ps) == 20
    ids = [p["id"] for p in ps]
    assert len(set(ids)) == 20
    assert all(p["topic"].strip() for p in ps)


def test_stratified_seven_seven_six():
    from scripts.prompts import load_prompts, register_counts
    counts = register_counts(load_prompts())
    assert counts == {"technical-exposition": 7, "narrative-editorial": 7, "polemic": 6}


def test_validate_rejects_bad_register():
    from scripts.prompts import validate_prompts, PromptSetError
    with pytest.raises(PromptSetError):
        validate_prompts([{"id": "x", "topic": "t", "register": "bogus"}])
```

- [ ] **Step 2: Run, expect FAIL** (`No module named 'scripts.prompts'`).

Run: `cd skills/voice-eval && .venv/Scripts/python.exe -m pytest tests/test_prompts.py -q`

- [ ] **Step 3: Write `assets/prompts-20x20.json`**

Author 20 prompts (7 technical-exposition, 7 narrative-editorial, 6 polemic). Each entry: `{"id", "topic", "register"}`. Use ZK / decentralization / governance topics consistent with the Hoskinson corpus. Exact content:

```json
{
  "version": 1,
  "prompts": [
    {"id": "T01", "topic": "Why a SNARK's verifier stays cheap while its prover does all the work", "register": "technical-exposition"},
    {"id": "T02", "topic": "What a commitment scheme hides and what it binds", "register": "technical-exposition"},
    {"id": "T03", "topic": "How an extended UTXO model carries state without global mutable storage", "register": "technical-exposition"},
    {"id": "T04", "topic": "The role of the Fiat-Shamir transform in making an interactive proof non-interactive", "register": "technical-exposition"},
    {"id": "T05", "topic": "Why finality in a longest-chain protocol is probabilistic, not absolute", "register": "technical-exposition"},
    {"id": "T06", "topic": "What a trusted setup ceremony actually distributes and why one honest party suffices", "register": "technical-exposition"},
    {"id": "T07", "topic": "How recursion lets one proof attest to the verification of another", "register": "technical-exposition"},
    {"id": "N01", "topic": "The first time a cryptographic idea changed how you saw trust", "register": "narrative-editorial"},
    {"id": "N02", "topic": "What a decade of building decentralized systems teaches about patience", "register": "narrative-editorial"},
    {"id": "N03", "topic": "Why the hardest part of governance is not the code", "register": "narrative-editorial"},
    {"id": "N04", "topic": "A small protocol decision whose consequences took years to surface", "register": "narrative-editorial"},
    {"id": "N05", "topic": "What open-source contributors owe each other and what they do not", "register": "narrative-editorial"},
    {"id": "N06", "topic": "The difference between a community and an audience", "register": "narrative-editorial"},
    {"id": "N07", "topic": "Why you keep explaining the same foundational idea in new words", "register": "narrative-editorial"},
    {"id": "P01", "topic": "Why 'just trust the validators' is a failure of nerve, not a design", "register": "polemic"},
    {"id": "P02", "topic": "The case against treating regulation as the enemy of decentralization", "register": "polemic"},
    {"id": "P03", "topic": "Why most tokenomics are astrology with a spreadsheet", "register": "polemic"},
    {"id": "P04", "topic": "The myth that throughput alone measures a blockchain's worth", "register": "polemic"},
    {"id": "P05", "topic": "Why 'move fast and break things' is malpractice for money", "register": "polemic"},
    {"id": "P06", "topic": "The comfortable lie that formal verification is too expensive to bother with", "register": "polemic"}
  ]
}
```

- [ ] **Step 4: Write `scripts/prompts.py`**

```python
# skills/voice-eval/scripts/prompts.py
"""Load and validate the 20-prompt stratified set (REQ-VEVAL-009)."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

_ASSET = Path(__file__).resolve().parents[1] / "assets" / "prompts-20x20.json"

REGISTERS = ("technical-exposition", "narrative-editorial", "polemic")
EXPECTED_COUNTS = {"technical-exposition": 7, "narrative-editorial": 7, "polemic": 6}


class PromptSetError(ValueError):
    pass


def register_counts(prompts: list[dict]) -> dict:
    return dict(Counter(p["register"] for p in prompts))


def validate_prompts(prompts: list[dict]) -> list[dict]:
    if len(prompts) != 20:
        raise PromptSetError(f"expected 20 prompts, got {len(prompts)}")
    ids = [p["id"] for p in prompts]
    if len(set(ids)) != len(ids):
        raise PromptSetError("duplicate prompt ids")
    for p in prompts:
        if p.get("register") not in REGISTERS:
            raise PromptSetError(f"prompt {p.get('id')!r}: bad register {p.get('register')!r}")
        if not str(p.get("topic", "")).strip():
            raise PromptSetError(f"prompt {p.get('id')!r}: empty topic")
    if register_counts(prompts) != EXPECTED_COUNTS:
        raise PromptSetError(f"stratification must be {EXPECTED_COUNTS}, got {register_counts(prompts)}")
    return prompts


def load_prompts(path: Path = _ASSET) -> list[dict]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return validate_prompts(payload["prompts"])
```

- [ ] **Step 5: Run, expect PASS** (`3 passed`). Then commit.

```bash
git add skills/voice-eval/assets/prompts-20x20.json skills/voice-eval/scripts/prompts.py skills/voice-eval/tests/test_prompts.py
git commit -m "voice-eval: 20-prompt stratified set (7/7/6) + loader/validation"
```

---

## Task 4: Generation orchestration (`run_arms`)

The two generation callables are supplied by the in-session protocol (the running model). In tests they are stubs. `run_arms` produces 40 register-tagged passages and is deterministic given deterministic callables.

**Files:**
- Create: `skills/voice-eval/scripts/arms.py`
- Test: `skills/voice-eval/tests/test_arms.py`

REQ-VEVAL-009: one passage per prompt from v1 and v2 → 40 passages.

- [ ] **Step 1: Write the failing test**

```python
# skills/voice-eval/tests/test_arms.py
"""Cites REQ-VEVAL-009 (v1+v2 generation → 40 passages)."""
import pytest

pytestmark = pytest.mark.windows_canary


def _stub(arm):
    # Deterministic generator: echoes arm + prompt id so passages are distinguishable.
    def gen(prompt):
        return f"[{arm}] {prompt['topic']} ({prompt['register']})."
    return gen


def test_run_arms_produces_forty_tagged_passages():
    from scripts.prompts import load_prompts
    from scripts.arms import run_arms
    passages = run_arms(load_prompts(), generate_v1=_stub("v1"), generate_v2=_stub("v2"))
    assert len(passages) == 40
    arms = {p["arm"] for p in passages}
    assert arms == {"v1", "v2"}
    # Every prompt appears once per arm, register carried through.
    pairs = {(p["prompt_id"], p["arm"]) for p in passages}
    assert len(pairs) == 40
    assert all(p["register"] in {"technical-exposition", "narrative-editorial", "polemic"} for p in passages)


def test_run_arms_records_text_and_prompt():
    from scripts.prompts import load_prompts
    from scripts.arms import run_arms
    passages = run_arms(load_prompts()[:1], generate_v1=_stub("v1"), generate_v2=_stub("v2"))
    assert len(passages) == 2
    assert passages[0]["text"].startswith("[v1]")
    assert passages[1]["text"].startswith("[v2]")
```

- [ ] **Step 2: Run, expect FAIL.** Run: `cd skills/voice-eval && .venv/Scripts/python.exe -m pytest tests/test_arms.py -q`

- [ ] **Step 3: Write `scripts/arms.py`**

```python
# skills/voice-eval/scripts/arms.py
"""Run the two generation arms over the prompt set (REQ-VEVAL-009).

Generation is performed in-session by the running model; here it is an injected
``Callable[[dict], str]`` that receives a prompt dict and returns prose. Tests stub it.
"""
from __future__ import annotations

from typing import Callable

Passage = dict
Generator = Callable[[dict], str]


def run_arms(prompts: list[dict], *, generate_v1: Generator, generate_v2: Generator) -> list[Passage]:
    passages: list[Passage] = []
    for arm, gen in (("v1", generate_v1), ("v2", generate_v2)):
        for p in prompts:
            text = gen(p)
            if not isinstance(text, str) or not text.strip():
                raise ValueError(f"empty generation for {p['id']} ({arm})")
            passages.append({
                "prompt_id": p["id"],
                "register": p["register"],
                "arm": arm,
                "text": text,
            })
    return passages
```

- [ ] **Step 4: Run, expect PASS** (`2 passed`). Then commit.

```bash
git add skills/voice-eval/scripts/arms.py skills/voice-eval/tests/test_arms.py
git commit -m "voice-eval: run_arms generates 40 register-tagged passages via injected callables"
```

---

## Task 5: Equal-grounding floor gate (v1 ruleset)

REQ-VEVAL-010: every one of the 40 passages must clear the `russellian-style` **v1** floor; failures are flagged for regeneration so both arms are equally floor-clean. We reuse `russellian-style/scripts/voice_eval.py::evaluate`, which runs the 12-linter battery under the default (v1) ruleset and returns per-linter counts.

**Files:**
- Create: `skills/voice-eval/scripts/floor_gate.py`
- Test: `skills/voice-eval/tests/test_floor_gate.py`

- [ ] **Step 1: Write the failing test** (battery is injected so the test stays offline and spaCy-free)

```python
# skills/voice-eval/tests/test_floor_gate.py
"""Cites REQ-VEVAL-010 (equal-grounding v1 floor gate)."""
import pytest

pytestmark = pytest.mark.windows_canary


def _fake_battery(passing_ids):
    # Returns total floor-violation count: 0 for passing passages, else 3.
    def battery(text, prompt_id, arm):
        return 0 if (prompt_id, arm) in passing_ids else 3
    return battery


def test_gate_flags_failures_for_regeneration():
    from scripts.floor_gate import gate_passages
    passages = [
        {"prompt_id": "T01", "arm": "v1", "register": "technical-exposition", "text": "a"},
        {"prompt_id": "T01", "arm": "v2", "register": "technical-exposition", "text": "b"},
    ]
    passing = {("T01", "v1")}              # v2 fails the floor
    result = gate_passages(passages, battery=_fake_battery(passing))
    assert result["all_clean"] is False
    assert [(f["prompt_id"], f["arm"]) for f in result["failures"]] == [("T01", "v2")]


def test_gate_all_clean_when_zero_violations():
    from scripts.floor_gate import gate_passages
    passages = [{"prompt_id": "T01", "arm": "v1", "register": "technical-exposition", "text": "a"}]
    result = gate_passages(passages, battery=_fake_battery({("T01", "v1")}))
    assert result["all_clean"] is True
    assert result["failures"] == []
```

- [ ] **Step 2: Run, expect FAIL.**

- [ ] **Step 3: Write `scripts/floor_gate.py`**

```python
# skills/voice-eval/scripts/floor_gate.py
"""Equal-grounding floor gate (REQ-VEVAL-010): every passage must clear the
russellian-style v1 floor. The battery is injected; ``default_battery`` wires the
real russellian-style 12-linter battery (v1 ruleset) via the sibling bridge.
"""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Callable

Battery = Callable[[str, str, str], int]   # (text, prompt_id, arm) -> violation count


def gate_passages(passages: list[dict], *, battery: Battery) -> dict:
    failures = []
    for p in passages:
        violations = battery(p["text"], p["prompt_id"], p["arm"])
        p["floor_violations"] = violations
        if violations > 0:
            failures.append({"prompt_id": p["prompt_id"], "arm": p["arm"], "violations": violations})
    return {"all_clean": not failures, "failures": failures, "n": len(passages)}


def default_battery(text: str, prompt_id: str, arm: str) -> int:
    """Real v1 floor battery via russellian-style.voice_eval.evaluate.

    evaluate() runs the 12 linters under the default (v1) ruleset and returns
    per-linter {count, per_1000}; the floor is clean iff every count is 0.
    """
    from scripts.sibling_skills import call
    report = call("russellian-style", "scripts.voice_eval", "evaluate", text)
    linters = report["generated"]["linters"]
    return sum(v["count"] for v in linters.values())
```

- [ ] **Step 4: Run, expect PASS** (`2 passed`). Then commit.

```bash
git add skills/voice-eval/scripts/floor_gate.py skills/voice-eval/tests/test_floor_gate.py
git commit -m "voice-eval: equal-grounding v1 floor gate over the 40 passages"
```

---

## Task 6: Per-signal metric deltas

REQ-VEVAL-011: score all 40 on the 8 liveliness signals; report per-signal mean delta v2−v1, overall and per register. Scoring is the injected sibling scorer (`liveliness-signals.score_passage`); the delta math is pure.

**Files:**
- Create: `skills/voice-eval/scripts/signal_deltas.py`
- Test: `skills/voice-eval/tests/test_signal_deltas.py`

- [ ] **Step 1: Write the failing test** (scorer injected; returns `{signal: {"score": x}}`)

```python
# skills/voice-eval/tests/test_signal_deltas.py
"""Cites REQ-VEVAL-011 (per-signal mean deltas, overall + per register)."""
import pytest

pytestmark = pytest.mark.windows_canary

SIGNALS = ("cadence", "verb_energy")


def _scorer(table):
    # table[(prompt_id, arm)] -> {signal: value}
    def score(text, register, prompt_id, arm):
        return {s: {"score": table[(prompt_id, arm)][s]} for s in SIGNALS}
    return score


def test_overall_and_per_register_deltas():
    from scripts.signal_deltas import compute_deltas
    passages = [
        {"prompt_id": "T01", "arm": "v1", "register": "technical-exposition", "text": "a"},
        {"prompt_id": "T01", "arm": "v2", "register": "technical-exposition", "text": "b"},
        {"prompt_id": "P01", "arm": "v1", "register": "polemic", "text": "c"},
        {"prompt_id": "P01", "arm": "v2", "register": "polemic", "text": "d"},
    ]
    table = {
        ("T01", "v1"): {"cadence": 0.4, "verb_energy": 0.2},
        ("T01", "v2"): {"cadence": 0.6, "verb_energy": 0.5},
        ("P01", "v1"): {"cadence": 0.5, "verb_energy": 0.1},
        ("P01", "v2"): {"cadence": 0.5, "verb_energy": 0.4},
    }
    out = compute_deltas(passages, scorer=_scorer(table), signals=SIGNALS)
    # cadence overall delta = mean(0.2, 0.0) = 0.1 ; verb_energy = mean(0.3, 0.3) = 0.3
    assert round(out["overall"]["cadence"], 6) == 0.1
    assert round(out["overall"]["verb_energy"], 6) == 0.3
    assert round(out["per_register"]["technical-exposition"]["cadence"], 6) == 0.2
    assert round(out["per_register"]["polemic"]["cadence"], 6) == 0.0
```

- [ ] **Step 2: Run, expect FAIL.**

- [ ] **Step 3: Write `scripts/signal_deltas.py`**

```python
# skills/voice-eval/scripts/signal_deltas.py
"""Per-signal mean deltas between the v2 and v1 arms (REQ-VEVAL-011).

The scorer is injected; ``default_scorer`` wires liveliness-signals.score_passage.
A delta is computed per prompt (v2 − v1) per signal, then averaged overall and within
each register.
"""
from __future__ import annotations

from collections import defaultdict
from statistics import mean
from typing import Callable

Scorer = Callable[[str, str, str, str], dict]   # (text, register, prompt_id, arm) -> {signal: {"score": float}}


def _index(passages: list[dict], scorer: Scorer, signals) -> dict:
    scores: dict = {}
    for p in passages:
        s = scorer(p["text"], p["register"], p["prompt_id"], p["arm"])
        scores[(p["prompt_id"], p["arm"])] = {sig: float(s[sig].get("score") or 0.0) for sig in signals}
    return scores


def compute_deltas(passages: list[dict], *, scorer: Scorer, signals) -> dict:
    scores = _index(passages, scorer, signals)
    registers = {p["prompt_id"]: p["register"] for p in passages}
    prompt_ids = sorted({p["prompt_id"] for p in passages})

    per_prompt = {}
    for pid in prompt_ids:
        if (pid, "v1") in scores and (pid, "v2") in scores:
            per_prompt[pid] = {sig: scores[(pid, "v2")][sig] - scores[(pid, "v1")][sig] for sig in signals}

    overall = {sig: mean(per_prompt[pid][sig] for pid in per_prompt) for sig in signals}

    by_reg = defaultdict(list)
    for pid, deltas in per_prompt.items():
        by_reg[registers[pid]].append(deltas)
    per_register = {
        reg: {sig: mean(d[sig] for d in rows) for sig in signals}
        for reg, rows in by_reg.items()
    }
    return {"overall": overall, "per_register": per_register, "per_prompt": per_prompt}


def default_scorer(text: str, register: str, prompt_id: str, arm: str) -> dict:
    """Adapt liveliness-signals.score_passage (which nests signals under "signals")
    to the {signal: {"score": float}} contract compute_deltas expects."""
    from scripts.sibling_skills import call
    result = call("liveliness-signals", "scripts.score", "score_passage", text, register)
    return result["signals"]
```

- [ ] **Step 4: Run, expect PASS** (`1 passed`). Then commit.

```bash
git add skills/voice-eval/scripts/signal_deltas.py skills/voice-eval/tests/test_signal_deltas.py
git commit -m "voice-eval: per-signal v2-v1 deltas, overall and per register"
```

---

## Task 7: Blind pairwise ballots (order-swapped, length-matched)

REQ-VEVAL-012 (part 1): build the ballots the in-session judge fills in. For each prompt, two ballots (presentation order swapped). Each ballot hides which arm is A/B, records the length-match status, requires a CoT rationale, and defines the verdict schema (forced-choice keep, "want next sentence more", ordinals momentum/clarity/voice-authority/readability/trustworthiness).

**Files:**
- Create: `skills/voice-eval/scripts/ballot.py`
- Test: `skills/voice-eval/tests/test_ballot.py`

- [ ] **Step 1: Write the failing test**

```python
# skills/voice-eval/tests/test_ballot.py
"""Cites REQ-VEVAL-012 (blind, order-swapped, length-matched pairwise ballots)."""
import pytest

pytestmark = pytest.mark.windows_canary


def _pair(pid):
    return (
        {"prompt_id": pid, "arm": "v1", "register": "polemic", "text": "x " * 50},
        {"prompt_id": pid, "arm": "v2", "register": "polemic", "text": "y " * 50},
    )


def test_two_order_swapped_ballots_per_prompt():
    from scripts.ballot import build_ballots
    v1, v2 = _pair("P01")
    ballots = build_ballots([v1], [v2])
    assert len(ballots) == 2
    # The same pair appears with A/B assignment swapped.
    a_arms = {b["A"]["arm"] for b in ballots}
    assert a_arms == {"v1", "v2"}
    # Blind: the arm label is not leaked into the side payload shown to the judge.
    assert "arm" not in ballots[0]["A"]["shown"]


def test_length_match_flag_and_required_fields():
    from scripts.ballot import build_ballots, VERDICT_FIELDS
    v1, v2 = _pair("P01")
    ballots = build_ballots([v1], [v2])
    b = ballots[0]
    assert b["length_matched"] is True
    assert set(VERDICT_FIELDS) == {
        "keep", "want_next", "momentum", "clarity",
        "voice_authority", "readability", "trustworthiness", "rationale",
    }


def test_length_mismatch_detected():
    from scripts.ballot import build_ballots
    short = {"prompt_id": "P01", "arm": "v1", "register": "polemic", "text": "short"}
    long = {"prompt_id": "P01", "arm": "v2", "register": "polemic", "text": "w " * 200}
    ballots = build_ballots([short], [long])
    assert ballots[0]["length_matched"] is False
```

- [ ] **Step 2: Run, expect FAIL.**

- [ ] **Step 3: Write `scripts/ballot.py`**

```python
# skills/voice-eval/scripts/ballot.py
"""Blind pairwise ballots for the in-session judge (REQ-VEVAL-012).

For each prompt the v1/v2 pair is presented twice with the A/B order swapped. The
``shown`` payload omits the arm so the judge is blind; ``_decode`` maps a filled
verdict's A/B keep back to the real arm. Length-match within ±15% word count.
"""
from __future__ import annotations

VERDICT_FIELDS = (
    "keep", "want_next", "momentum", "clarity",
    "voice_authority", "readability", "trustworthiness", "rationale",
)
ORDINAL_FIELDS = ("momentum", "clarity", "voice_authority", "readability", "trustworthiness")
_LENGTH_TOL = 0.15


def _words(text: str) -> int:
    return len(text.split())


def _length_matched(a: dict, b: dict) -> bool:
    wa, wb = _words(a["text"]), _words(b["text"])
    if wa == 0 or wb == 0:
        return False
    return abs(wa - wb) / max(wa, wb) <= _LENGTH_TOL


def _side(p: dict) -> dict:
    # Carries the arm internally for decoding, but ``shown`` is what the judge sees.
    return {"arm": p["arm"], "shown": {"prompt_id": p["prompt_id"], "text": p["text"]}}


def build_ballots(v1_passages: list[dict], v2_passages: list[dict]) -> list[dict]:
    by_pid_v1 = {p["prompt_id"]: p for p in v1_passages}
    by_pid_v2 = {p["prompt_id"]: p for p in v2_passages}
    ballots = []
    for pid in sorted(set(by_pid_v1) & set(by_pid_v2)):
        v1, v2 = by_pid_v1[pid], by_pid_v2[pid]
        matched = _length_matched(v1, v2)
        # Order 1: A=v1, B=v2 ; Order 2: A=v2, B=v1 (swap).
        for idx, (a, b) in enumerate(((v1, v2), (v2, v1))):
            ballots.append({
                "prompt_id": pid,
                "register": v1["register"],
                "order": idx,
                "length_matched": matched,
                "requires_rationale": True,
                "A": _side(a),
                "B": _side(b),
                "verdict": None,   # filled in-session with VERDICT_FIELDS
            })
    return ballots


def decode_keep(ballot: dict) -> str:
    """Map a filled ballot's 'keep' ('A'|'B') to the real arm ('v1'|'v2')."""
    choice = ballot["verdict"]["keep"]
    return ballot[choice]["arm"]
```

- [ ] **Step 4: Run, expect PASS** (`3 passed`). Then commit.

```bash
git add skills/voice-eval/scripts/ballot.py skills/voice-eval/tests/test_ballot.py
git commit -m "voice-eval: blind order-swapped length-matched pairwise ballots"
```

---

## Task 8: Win-rate + Wilson confidence interval

REQ-VEVAL-012 (part 2): aggregate filled ballots into a v2 win-rate with a confidence interval. Wilson score interval (deterministic, good for proportions); a swapped pair that disagrees counts as a tie (0.5 each).

**Files:**
- Create: `skills/voice-eval/scripts/winrate.py`
- Test: `skills/voice-eval/tests/test_winrate.py`

- [ ] **Step 1: Write the failing test**

```python
# skills/voice-eval/tests/test_winrate.py
"""Cites REQ-VEVAL-012 (win-rate with confidence interval)."""
import pytest

pytestmark = pytest.mark.windows_canary


def _filled(prompt_id, order, keep_arm, ballots_arms):
    # ballots_arms: which arm is 'A' in this ballot; keep is the letter that selects keep_arm
    keep_letter = "A" if ballots_arms["A"] == keep_arm else "B"
    return {
        "prompt_id": prompt_id, "order": order,
        "A": {"arm": ballots_arms["A"]}, "B": {"arm": ballots_arms["B"]},
        "verdict": {"keep": keep_letter},
    }


def test_winrate_counts_v2_keeps():
    from scripts.winrate import win_rate
    # Two prompts, both orders pick v2 → v2 win-rate 1.0
    ballots = [
        _filled("P01", 0, "v2", {"A": "v1", "B": "v2"}),
        _filled("P01", 1, "v2", {"A": "v2", "B": "v1"}),
        _filled("P02", 0, "v2", {"A": "v1", "B": "v2"}),
        _filled("P02", 1, "v2", {"A": "v2", "B": "v1"}),
    ]
    r = win_rate(ballots, target="v2")
    assert r["wins"] == 4 and r["n"] == 4
    assert r["rate"] == 1.0
    assert 0.0 <= r["ci_low"] <= r["ci_high"] <= 1.0
    assert r["ci_low"] > 0.4   # 4/4 lower Wilson bound well above chance


def test_wilson_interval_known_value():
    from scripts.winrate import wilson_interval
    lo, hi = wilson_interval(8, 10)   # 0.8 of 10
    assert round(lo, 3) == 0.490
    assert round(hi, 3) == 0.943
```

- [ ] **Step 2: Run, expect FAIL.**

- [ ] **Step 3: Write `scripts/winrate.py`**

```python
# skills/voice-eval/scripts/winrate.py
"""Pairwise win-rate with a Wilson score confidence interval (REQ-VEVAL-012)."""
from __future__ import annotations

import math

Z_95 = 1.959963984540054


def wilson_interval(wins: float, n: int, z: float = Z_95) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    phat = wins / n
    denom = 1 + z * z / n
    center = (phat + z * z / (2 * n)) / denom
    margin = (z / denom) * math.sqrt(phat * (1 - phat) / n + z * z / (4 * n * n))
    return (max(0.0, center - margin), min(1.0, center + margin))


def win_rate(ballots: list[dict], *, target: str = "v2") -> dict:
    """Each filled ballot contributes one judgment: 1 if the kept arm == target, else 0.
    (Order-swap duplicates are counted independently, per the design's order-swapped run.)"""
    wins = 0.0
    n = 0
    for b in ballots:
        v = b.get("verdict")
        if not v or "keep" not in v:
            continue
        kept_arm = b[v["keep"]]["arm"]
        wins += 1.0 if kept_arm == target else 0.0
        n += 1
    rate = wins / n if n else 0.0
    lo, hi = wilson_interval(wins, n)
    return {"target": target, "wins": wins, "n": n, "rate": rate, "ci_low": lo, "ci_high": hi}
```

- [ ] **Step 4: Run, expect PASS** (`2 passed`). Then commit.

```bash
git add skills/voice-eval/scripts/winrate.py skills/voice-eval/tests/test_winrate.py
git commit -m "voice-eval: pairwise win-rate with Wilson confidence interval"
```

---

## Task 9: Formula-drift monitor

REQ-VEVAL-013: within each arm's 20 passages, compute TF-IDF cosine over **structure-only** tokens of first and last sentences, plus opening part-of-speech patterns and analogy-family reuse; flag drift above a threshold. "Structure-only" = function words + POS placeholders for content words, so the metric measures *form*, not topic. The spaCy POS read is injected so the core math stays unit-testable offline; `default_struct_tokens` wires the real tagger.

**Files:**
- Create: `skills/voice-eval/scripts/drift.py`
- Test: `skills/voice-eval/tests/test_drift.py`

- [ ] **Step 1: Write the failing test** (inject the structure-tokenizer)

```python
# skills/voice-eval/tests/test_drift.py
"""Cites REQ-VEVAL-013 (formula-drift: struct TF-IDF cosine + opening POS + analogy reuse)."""
import pytest

pytestmark = pytest.mark.windows_canary


def test_identical_structure_flags_high_drift():
    from scripts.drift import arm_drift
    # Three passages that all open and close with the same structural skeleton.
    skeleton = {"first": ["DET", "NOUN", "VERB"], "last": ["PRON", "VERB", "ADJ"], "opening_pos": ("DET", "NOUN", "VERB")}
    passages = [{"prompt_id": f"P0{i}", "arm": "v2", "text": "t",
                 "structure": skeleton, "analogy_family": "bank"} for i in range(3)]
    out = arm_drift(passages, struct_of=lambda p: p["structure"],
                    analogy_of=lambda p: p["analogy_family"], threshold=0.5)
    assert out["flagged"] is True
    assert out["mean_cosine"] > 0.5
    assert out["analogy_reuse_max"] == 3      # 'bank' reused in all three


def test_varied_structure_below_threshold():
    from scripts.drift import arm_drift
    passages = [
        {"prompt_id": "P01", "arm": "v2", "structure": {"first": ["DET", "NOUN"], "last": ["VERB"], "opening_pos": ("DET", "NOUN")}, "analogy_family": "bank"},
        {"prompt_id": "P02", "arm": "v2", "structure": {"first": ["ADV", "VERB", "PRON"], "last": ["NOUN", "NOUN"], "opening_pos": ("ADV", "VERB")}, "analogy_family": "garden"},
        {"prompt_id": "P03", "arm": "v2", "structure": {"first": ["SCONJ", "PRON", "VERB", "ADJ"], "last": ["DET", "ADJ", "NOUN"], "opening_pos": ("SCONJ", "PRON")}, "analogy_family": "river"},
    ]
    out = arm_drift(passages, struct_of=lambda p: p["structure"],
                    analogy_of=lambda p: p["analogy_family"], threshold=0.7)
    assert out["flagged"] is False
    assert out["analogy_reuse_max"] == 1
```

- [ ] **Step 2: Run, expect FAIL.**

- [ ] **Step 3: Write `scripts/drift.py`**

```python
# skills/voice-eval/scripts/drift.py
"""Within-arm formula-drift monitor (REQ-VEVAL-013).

Drift = mean pairwise cosine similarity of structure vectors across an arm's passages.
Each structure vector is a bag of structural tokens: the POS sequences of the first
and last sentences (prefixed so first/last spaces are distinct) plus the opening-POS
n-gram. High mean cosine ⇒ the arm is reusing one skeleton (a formula). Analogy-family
reuse is the max count of any single base-domain family across the arm.
"""
from __future__ import annotations

import math
from collections import Counter
from typing import Callable


def _struct_terms(structure: dict) -> Counter:
    terms = Counter()
    for tok in structure.get("first", []):
        terms[f"first:{tok}"] += 1
    for tok in structure.get("last", []):
        terms[f"last:{tok}"] += 1
    terms[f"open:{'-'.join(structure.get('opening_pos', ()))}"] += 1
    return terms


def _cosine(a: Counter, b: Counter) -> float:
    keys = set(a) | set(b)
    dot = sum(a[k] * b[k] for k in keys)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0


def arm_drift(passages: list[dict], *, struct_of: Callable[[dict], dict],
              analogy_of: Callable[[dict], str], threshold: float = 0.6) -> dict:
    vecs = [_struct_terms(struct_of(p)) for p in passages]
    pairs = [(i, j) for i in range(len(vecs)) for j in range(i + 1, len(vecs))]
    cosines = [_cosine(vecs[i], vecs[j]) for i, j in pairs]
    mean_cos = sum(cosines) / len(cosines) if cosines else 0.0
    fam_counts = Counter(analogy_of(p) for p in passages if analogy_of(p))
    reuse_max = max(fam_counts.values()) if fam_counts else 0
    return {
        "n": len(passages),
        "mean_cosine": mean_cos,
        "analogy_reuse_max": reuse_max,
        "analogy_families": dict(fam_counts),
        "threshold": threshold,
        "flagged": mean_cos > threshold,
    }


def default_struct_tokens(text: str) -> dict:
    """Real structure extractor via spaCy (used in-session, not in unit tests)."""
    import spacy
    nlp = spacy.load("en_core_web_sm")
    doc = nlp(text)
    sents = list(doc.sents)
    if not sents:
        return {"first": [], "last": [], "opening_pos": ()}
    first = [t.pos_ for t in sents[0]]
    last = [t.pos_ for t in sents[-1]]
    return {"first": first, "last": last, "opening_pos": tuple(first[:3])}
```

- [ ] **Step 4: Run, expect PASS** (`2 passed`). Then commit.

```bash
git add skills/voice-eval/scripts/drift.py skills/voice-eval/tests/test_drift.py
git commit -m "voice-eval: within-arm formula-drift monitor (struct cosine + analogy reuse)"
```

---

## Task 10: Detector read — advisory only, never gates

REQ-VEVAL-014: if an AI-detector/perplexity score is computed, it is reported as advisory only and never gates, fails, or blocks any passage.

**Files:**
- Create: `skills/voice-eval/scripts/detector.py`
- Test: `skills/voice-eval/tests/test_detector.py`

- [ ] **Step 1: Write the failing test**

```python
# skills/voice-eval/tests/test_detector.py
"""Cites REQ-VEVAL-014 (detector advisory-only, never gates)."""
import pytest

pytestmark = pytest.mark.windows_canary


def test_detector_report_is_advisory_and_never_blocks():
    from scripts.detector import detector_report
    passages = [{"prompt_id": "P01", "arm": "v2", "text": "x"}]
    rep = detector_report(passages, scorer=lambda text: 0.99)   # "looks AI" — must NOT gate
    assert rep["advisory"] is True
    assert rep["gates"] is False
    assert rep["rows"][0]["score"] == 0.99
    assert "blocked" not in rep and "failures" not in rep


def test_detector_absent_scorer_is_noop():
    from scripts.detector import detector_report
    rep = detector_report([{"prompt_id": "P01", "arm": "v2", "text": "x"}], scorer=None)
    assert rep["advisory"] is True and rep["gates"] is False
    assert rep["rows"] == []
```

- [ ] **Step 2: Run, expect FAIL.**

- [ ] **Step 3: Write `scripts/detector.py`**

```python
# skills/voice-eval/scripts/detector.py
"""Optional AI-detector / perplexity read — advisory only (REQ-VEVAL-014).

Per the design (source-paper correction 3: detectors hit ~0% TPR at 1% FPR and are
trivially evaded), any score here is informational. This module structurally cannot
gate: it returns rows and the constant flags advisory=True, gates=False, and exposes
no pass/fail decision.
"""
from __future__ import annotations

from typing import Callable, Optional


def detector_report(passages: list[dict], *, scorer: Optional[Callable[[str], float]]) -> dict:
    rows = []
    if scorer is not None:
        for p in passages:
            rows.append({"prompt_id": p["prompt_id"], "arm": p["arm"], "score": scorer(p["text"])})
    return {"advisory": True, "gates": False, "rows": rows}
```

- [ ] **Step 4: Run, expect PASS** (`2 passed`). Then commit.

```bash
git add skills/voice-eval/scripts/detector.py skills/voice-eval/tests/test_detector.py
git commit -m "voice-eval: advisory-only detector read that structurally never gates"
```

---

## Task 11: Success criterion + report

REQ-VEVAL-015: report the 20×20 as passing only when the v2 arm (a) stays floor-clean, (b) scores higher than v1 on the positive signals, (c) wins >50% of pairwise judgments, (d) does not score worse on trustworthiness, and (e) shows lower formula drift. Then render a Markdown report.

**Files:**
- Create: `skills/voice-eval/scripts/report.py`
- Test: `skills/voice-eval/tests/test_report.py`

- [ ] **Step 1: Write the failing test**

```python
# skills/voice-eval/tests/test_report.py
"""Cites REQ-VEVAL-015 (success criterion + report)."""
import pytest

pytestmark = pytest.mark.windows_canary


def _good():
    return {
        "floor": {"all_clean": True, "failures": []},
        "deltas": {"overall": {"cadence": 0.2, "verb_energy": 0.1}, "per_register": {}},
        "winrate": {"target": "v2", "rate": 0.65, "n": 40, "ci_low": 0.5, "ci_high": 0.78},
        "trust": {"v2_minus_v1": 0.1},
        "drift": {"v1_mean_cosine": 0.7, "v2_mean_cosine": 0.5},
    }


def test_success_when_all_criteria_met():
    from scripts.report import evaluate_success
    v = evaluate_success(**_good())
    assert v["passed"] is True
    assert all(v["criteria"].values())


def test_fail_when_v2_loses_pairwise():
    from scripts.report import evaluate_success
    g = _good(); g["winrate"]["rate"] = 0.45
    v = evaluate_success(**g)
    assert v["passed"] is False
    assert v["criteria"]["wins_majority"] is False


def test_fail_when_trustworthiness_worse():
    from scripts.report import evaluate_success
    g = _good(); g["trust"]["v2_minus_v1"] = -0.05
    v = evaluate_success(**g)
    assert v["passed"] is False
    assert v["criteria"]["trust_not_worse"] is False


def test_report_renders_markdown(tmp_path):
    from scripts.report import evaluate_success, render_report
    v = evaluate_success(**_good())
    out = tmp_path / "r.md"
    render_report(v, _good(), out)
    text = out.read_text(encoding="utf-8")
    assert "# HFR v2 — 20×20 report" in text
    assert "PASS" in text
```

- [ ] **Step 2: Run, expect FAIL.**

- [ ] **Step 3: Write `scripts/report.py`**

```python
# skills/voice-eval/scripts/report.py
"""20×20 success criterion + Markdown report (REQ-VEVAL-015)."""
from __future__ import annotations

from pathlib import Path


def evaluate_success(*, floor: dict, deltas: dict, winrate: dict, trust: dict, drift: dict) -> dict:
    overall = deltas["overall"]
    criteria = {
        "floor_clean": bool(floor["all_clean"]),
        "signals_higher": all(v > 0 for v in overall.values()) and len(overall) > 0,
        "wins_majority": winrate["rate"] > 0.5,
        "trust_not_worse": trust["v2_minus_v1"] >= 0,
        "lower_drift": drift["v2_mean_cosine"] < drift["v1_mean_cosine"],
    }
    return {"passed": all(criteria.values()), "criteria": criteria}


def render_report(verdict: dict, data: dict, out_path) -> None:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    status = "PASS" if verdict["passed"] else "FAIL"
    wr = data["winrate"]
    lines = [
        "# HFR v2 — 20×20 report",
        "",
        f"**Result: {status}**",
        "",
        "## Success criteria",
        "",
        "| criterion | met |",
        "|---|---|",
    ]
    for k, ok in verdict["criteria"].items():
        lines.append(f"| {k} | {'yes' if ok else 'NO'} |")
    lines += [
        "",
        "## Pairwise win-rate (v2)",
        "",
        f"- rate: {wr['rate']:.3f}  (n={wr['n']}, 95% CI {wr['ci_low']:.3f}–{wr['ci_high']:.3f})",
        "",
        "## Per-signal mean delta (v2 − v1)",
        "",
        "| signal | delta |",
        "|---|---:|",
    ]
    for sig, d in data["deltas"]["overall"].items():
        lines.append(f"| {sig} | {d:+.3f} |")
    lines += [
        "",
        "## Formula drift (mean within-arm structural cosine; lower is better)",
        "",
        f"- v1: {data['drift']['v1_mean_cosine']:.3f}",
        f"- v2: {data['drift']['v2_mean_cosine']:.3f}",
        "",
    ]
    if not data["floor"]["all_clean"]:
        lines.append(f"> ⚠ floor failures pending regeneration: {data['floor']['failures']}")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
```

- [ ] **Step 4: Run, expect PASS** (`4 passed`). Then commit.

```bash
git add skills/voice-eval/scripts/report.py skills/voice-eval/tests/test_report.py
git commit -m "voice-eval: 20x20 success criterion + markdown report"
```

---

## Task 12: Human-study scaffold + signal-graduation gate

REQ-VEVAL-016: a blind A/B human-study scaffold — prompt set ≥50–60 items, randomized presentation, a rater rubric covering the targeted dimensions, and inter-rater reliability via Fleiss' κ (Krippendorff's α optional). REQ-VEVAL-017: a signal graduates from advisory to gating only if the study shows a moderate positive Spearman correlation with the targeted dimension whose bootstrap CI excludes zero, and never if it degrades trustworthiness.

**Files:**
- Create: `skills/voice-eval/scripts/human_study.py`
- Test: `skills/voice-eval/tests/test_human_study.py`

- [ ] **Step 1: Write the failing test**

```python
# skills/voice-eval/tests/test_human_study.py
"""Cites REQ-VEVAL-016, REQ-VEVAL-017 (human-study scaffold + graduation gate)."""
import pytest

pytestmark = pytest.mark.windows_canary

RUBRIC_DIMS = ("momentum", "clarity", "voice_authority", "readability", "trustworthiness")


def test_scaffold_min_items_and_randomized_blind():
    from scripts.human_study import build_study
    pairs = [{"prompt_id": f"X{i}", "v1": "a", "v2": "b"} for i in range(60)]
    study = build_study(pairs, seed=7, rubric=RUBRIC_DIMS)
    assert len(study["items"]) >= 50
    # Blind: each item presents A/B with the arm hidden behind a recoverable key.
    assert all(set(it["sides"]) == {"A", "B"} for it in study["items"])
    assert all("arm" not in it["sides"]["A"] for it in study["items"])
    assert set(study["rubric"]) == set(RUBRIC_DIMS)


def test_fleiss_kappa_perfect_agreement():
    from scripts.human_study import fleiss_kappa
    # 3 raters, 2 items, both unanimous → kappa 1.0
    # table[item] = {category: count}
    table = [{"A": 3, "B": 0}, {"A": 0, "B": 3}]
    assert round(fleiss_kappa(table), 6) == 1.0


def test_graduation_denied_without_ci_excluding_zero():
    from scripts.human_study import graduate
    # correlation present but CI straddles zero → denied
    g = graduate(spearman=0.55, ci=(-0.1, 0.8), trust_delta=0.0)
    assert g["graduates"] is False
    assert g["reasons"]["ci_excludes_zero"] is False


def test_graduation_denied_if_trust_degrades():
    from scripts.human_study import graduate
    g = graduate(spearman=0.7, ci=(0.4, 0.85), trust_delta=-0.02)
    assert g["graduates"] is False
    assert g["reasons"]["trust_not_degraded"] is False


def test_graduation_allowed_when_all_conditions_met():
    from scripts.human_study import graduate
    g = graduate(spearman=0.65, ci=(0.3, 0.82), trust_delta=0.01)
    assert g["graduates"] is True
```

- [ ] **Step 2: Run, expect FAIL.**

- [ ] **Step 3: Write `scripts/human_study.py`**

```python
# skills/voice-eval/scripts/human_study.py
"""Blind A/B human-study scaffold + signal-graduation gate (REQ-VEVAL-016/017).

Deterministic given a seed (the randomization uses a seeded ``random.Random``; the
running study is a later activity, but the scaffold and its statistics are built and
tested now). Fleiss' κ measures inter-rater reliability; graduation is gated on a
Spearman correlation whose bootstrap CI excludes zero and a non-negative
trustworthiness delta.
"""
from __future__ import annotations

import random

MIN_ITEMS = 50
GRADUATION_MIN_SPEARMAN = 0.4   # "moderate positive" floor (design § Component 6)


def build_study(pairs: list[dict], *, seed: int, rubric) -> dict:
    if len(pairs) < MIN_ITEMS:
        raise ValueError(f"human study needs >= {MIN_ITEMS} pairs, got {len(pairs)}")
    rng = random.Random(seed)
    items = []
    for pair in pairs:
        a_is_v1 = rng.random() < 0.5
        a_arm, b_arm = ("v1", "v2") if a_is_v1 else ("v2", "v1")
        items.append({
            "prompt_id": pair["prompt_id"],
            "key": {"A": a_arm, "B": b_arm},                 # recoverable mapping (kept by the runner)
            "sides": {"A": {"text": pair[a_arm]}, "B": {"text": pair[b_arm]}},
        })
    rng.shuffle(items)
    return {"items": items, "rubric": tuple(rubric), "min_items": MIN_ITEMS}


def fleiss_kappa(table: list[dict]) -> float:
    """table[item] = {category: n_raters_choosing_it}. All items must share the rater count."""
    categories = sorted({c for row in table for c in row})
    n = sum(table[0].values())
    N = len(table)
    p_j = {c: sum(row.get(c, 0) for row in table) / (N * n) for c in categories}
    P_i = []
    for row in table:
        s = sum(row.get(c, 0) ** 2 for c in categories) - n
        P_i.append(s / (n * (n - 1)))
    P_bar = sum(P_i) / N
    P_e = sum(v * v for v in p_j.values())
    if P_e == 1.0:
        return 1.0
    return (P_bar - P_e) / (1 - P_e)


def graduate(*, spearman: float, ci: tuple[float, float], trust_delta: float) -> dict:
    reasons = {
        "moderate_positive": spearman >= GRADUATION_MIN_SPEARMAN,
        "ci_excludes_zero": ci[0] > 0.0,
        "trust_not_degraded": trust_delta >= 0.0,
    }
    return {"graduates": all(reasons.values()), "reasons": reasons}
```

- [ ] **Step 4: Run, expect PASS** (`5 passed`). Then commit.

```bash
git add skills/voice-eval/scripts/human_study.py skills/voice-eval/tests/test_human_study.py
git commit -m "voice-eval: human-study scaffold (Fleiss kappa) + signal-graduation gate"
```

---

## Task 13: In-session run protocol (`SKILL.md`)

The Python helpers are deterministic; generation and judging are the running model's job. `SKILL.md` is the doctrine that ties them together — it is the human/agent-facing protocol, mirroring `triadic-voice-v2/SKILL.md`.

**Files:**
- Create: `skills/voice-eval/SKILL.md`
- Test: `skills/voice-eval/tests/test_smoke.py` (extend with a doc-contract check)

- [ ] **Step 1: Extend the smoke test with a SKILL.md contract check**

Append to `skills/voice-eval/tests/test_smoke.py`:

```python
def test_skill_md_documents_the_protocol():
    from pathlib import Path
    text = (Path(__file__).resolve().parents[1] / "SKILL.md").read_text(encoding="utf-8")
    for anchor in ("20×20", "in-session", "blind", "order", "floor", "win-rate"):
        assert anchor in text, f"SKILL.md must mention {anchor!r}"
```

- [ ] **Step 2: Run, expect FAIL** (SKILL.md missing).

- [ ] **Step 3: Write `skills/voice-eval/SKILL.md`**

````markdown
---
name: voice-eval
description: HFR v2 evaluation. Runs the 20×20 comparison between triadic-voice (v1) and triadic-voice-v2 (v2): generate in-session, gate on the russellian-style v1 floor, score the 8 liveliness signals, judge blind pairwise, monitor formula-drift, and report pass/fail. Use to decide whether v2 beats v1. The running model generates and judges; no API key.
license: MIT
metadata:
  author: charles-hoskinson
  version: 0.1.0
  category: writing
---

# voice-eval

The HFR v2 acceptance test. Deterministic Python helpers do the bookkeeping and
statistics; **the running model does the generation and the judging in-session** (no
API key), exactly like `triadic-voice`/`triadic-voice-v2`. v1 is the frozen control.

## How to run the 20×20 (in-session)

1. **Load prompts.** `load_prompts()` → 20 prompts stratified 7/7/6.
2. **Generate both arms.** For each prompt, write one v1 passage (follow
   `triadic-voice/SKILL.md`) and one v2 passage (follow `triadic-voice-v2/SKILL.md`,
   using `build_generation_brief(topic, rotation)`). Feed these as the `generate_v1` /
   `generate_v2` callables to `run_arms(...)` → 40 passages.
3. **Gate on the v1 floor.** `gate_passages(passages, battery=default_battery)`. Any
   passage with violations is **regenerated** before scoring, so both arms are equally
   floor-clean (REQ-VEVAL-010).
4. **Signal deltas.** `compute_deltas(passages, scorer=default_scorer, signals=SIGNAL_NAMES)`
   → per-signal mean delta v2−v1, overall and per register (REQ-VEVAL-011).
5. **Blind pairwise judge.** `build_ballots(v1_passages, v2_passages)` → 40 ballots
   (each pair judged in both orders, length-matched). For each ballot, judge blind:
   read A and B, give a chain-of-thought rationale, then fill the verdict
   (`keep`, `want_next`, and ordinal `momentum/clarity/voice_authority/readability/
   trustworthiness`). Never look at the arm labels. Aggregate with
   `win_rate(filled_ballots, target="v2")` (REQ-VEVAL-012).
6. **Formula-drift.** Within each arm, `arm_drift(passages, struct_of=…, analogy_of=…)`
   using `default_struct_tokens` for the POS skeletons (REQ-VEVAL-013).
7. **(Optional) detector** — advisory only, never gates (REQ-VEVAL-014).
8. **Report.** `evaluate_success(...)` then `render_report(...)`. v2 passes only when it
   is floor-clean, scores higher on the positive signals, wins >50% pairwise,
   trustworthiness is not worse, and drift is lower (REQ-VEVAL-015).

## Human study (later run)
`build_study(pairs, seed, rubric)` builds the ≥50–60-item blind A/B scaffold;
`fleiss_kappa(...)` measures inter-rater reliability; `graduate(...)` is the gate that
promotes a signal from advisory to gating only on a moderate positive Spearman
correlation whose CI excludes zero, never degrading trustworthiness (REQ-VEVAL-016/017).

## Helpers
`scripts/prompts.py`, `arms.py`, `floor_gate.py`, `signal_deltas.py`, `ballot.py`,
`winrate.py`, `drift.py`, `detector.py`, `report.py`, `human_study.py`,
`sibling_skills.py`. All deterministic and unit-tested; siblings loaded repo-first.
````

- [ ] **Step 4: Run the full skill suite, expect PASS**

Run: `cd skills/voice-eval && .venv/Scripts/python.exe -m pytest tests/ -q`
Expected: all tests pass (the `default_*` sibling-wired paths are exercised in-session, not in unit tests).

- [ ] **Step 5: Commit**

```bash
git add skills/voice-eval/SKILL.md skills/voice-eval/tests/test_smoke.py
git commit -m "voice-eval: in-session 20x20 run protocol (SKILL.md)"
```

---

## Task 14: Wiring & housekeeping

**Files:**
- Modify: `.github/ci/skills-matrix.json`
- Modify: `openspec/README.md`
- Modify: `docs/plans/2026-06-19-hfr-v2-liveliness-corpus-profile.md`
- Modify: `openspec/changes/add-hfr-v2-liveliness/tasks.md`

- [ ] **Step 1: Register `voice-eval` in the CI skills matrix**

Add to the `"skills"` array in `.github/ci/skills-matrix.json` (siblings are symlinked so the bridge resolves them in CI):

```json
    {
      "skill": "voice-eval",
      "extra": "dev",
      "siblings": ["russellian-style", "liveliness-signals", "triadic-voice-v2"]
    },
```

- [ ] **Step 2: Register the `VEVAL` slug in `openspec/README.md`** (only if not already present — `add-voice-eval-stage` may have added it). Confirm with:

Run: `grep -n "VEVAL" openspec/README.md`
If absent, add `VEVAL` to the REQ-prefix registry table next to the other voice slugs (`LIVE`, `TRIAD`, `VOICE`).

- [ ] **Step 3: Update the Plan-set pointer**

In `docs/plans/2026-06-19-hfr-v2-liveliness-corpus-profile.md`, change the Plan-set line for item 5 from a future-tense pointer to:

```markdown
5. Evaluation (`voice-eval` 20×20 harness) — **written** (`docs/plans/2026-06-19-hfr-v2-voice-eval.md`)
```

- [ ] **Step 4: Tick the eval items in the OpenSpec task tracker**

In `openspec/changes/add-hfr-v2-liveliness/tasks.md`, mark the four `## Evaluation (voice-eval)` checkboxes as planned/this-plan (leave them `[ ]` for execution, but the harness tasks now have a concrete plan; no content change required if you prefer to tick them only after execution). Add one line under that section:

```markdown
- Plan: docs/plans/2026-06-19-hfr-v2-voice-eval.md (Tasks 1–14)
```

- [ ] **Step 5: Run the full skill suite + ruff**

```bash
cd skills/voice-eval
.venv/Scripts/python.exe -m pytest tests/ -q
.venv/Scripts/python.exe -m ruff check . 2>/dev/null || python -m ruff check skills/voice-eval
```
Expected: all tests pass; ruff clean.

- [ ] **Step 6: Confirm no regression in the touched sibling**

```bash
cd skills/liveliness-signals && .venv/Scripts/python.exe -m pytest tests/ -q
```
Expected: still green (the `score_passage`/`SIGNAL_NAMES` export is additive).

- [ ] **Step 7: Commit**

```bash
git add .github/ci/skills-matrix.json openspec/README.md docs/plans/2026-06-19-hfr-v2-liveliness-corpus-profile.md openspec/changes/add-hfr-v2-liveliness/tasks.md
git commit -m "voice-eval: register skill in CI matrix; update plan-set pointer + tasks"
```

---

## Definition of Done

- `skills/voice-eval/` exists with all 11 scripts, `SKILL.md`, and a green test suite (each helper unit-tested offline; sibling-wired `default_*` paths used only in-session).
- All of REQ-VEVAL-009..017 are covered (see map below).
- `liveliness-signals` exports `score_passage` + `SIGNAL_NAMES`; its suite still green.
- `voice-eval` is registered in `.github/ci/skills-matrix.json`; Plan-set pointer and OpenSpec tasks updated.
- The actual 20×20 *run* (generate + judge in-session, record deltas/win-rate/drift in the change notes) is a **follow-on execution activity**, not part of building the harness.

## Requirement coverage map

| REQ | Task |
|---|---|
| REQ-VEVAL-009 (20×20 harness, 40 passages) | Tasks 3, 4 |
| REQ-VEVAL-010 (equal-grounding v1 floor gate) | Task 5 |
| REQ-VEVAL-011 (per-signal metric deltas) | Task 6 |
| REQ-VEVAL-012 (blind order-swapped pairwise + win-rate) | Tasks 7, 8 |
| REQ-VEVAL-013 (formula-drift monitor) | Task 9 |
| REQ-VEVAL-014 (detector never gates) | Task 10 |
| REQ-VEVAL-015 (success-criterion report) | Task 11 |
| REQ-VEVAL-016 (human-study scaffold) | Task 12 |
| REQ-VEVAL-017 (signal-graduation gate) | Task 12 |
| In-session protocol / wiring | Tasks 13, 14 |
