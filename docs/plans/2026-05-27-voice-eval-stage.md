# Voice-Eval Stage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a committed `voice_eval.py` stage that generates N=30 paragraphs of Russell-voice prose via an injected LLM callable and compares them to original Russell using the Russell-Delta scorer and the russellian-style linter battery.

**Architecture:** A single cohesive module in `skills/russellian-style/scripts/` reusing `system_prompt_loader` (generation prompt), `score_russell_delta` (Delta), and the 12 linter modules (battery). Generation is an injected `Callable[[str], str]`; scoring is deterministic and offline. Advisory only.

**Tech Stack:** Python 3.11+, stdlib (`tempfile`, `json`, `argparse`-free arg handling). pytest. The linters require spaCy (already in the skill `.venv`); generation tests need no spaCy.

**Spec:** `openspec/changes/add-voice-eval-stage/` (REQ-VEVAL-001..008), `docs/specs/2026-05-27-voice-eval-stage-design.md`.

---

## File structure

- Create `skills/russellian-style/scripts/voice_eval.py` — generation + evaluation + report + CLI.
- Create `skills/russellian-style/tests/test_voice_eval.py` — TDD across the three functions.
- Create `docs/audits/2026-05-27-voice-eval/` — demo bundle (Task 4).

Run tests from the skill root: `cd skills/russellian-style && .venv/Scripts/python.exe -m pytest tests/<file> -v` (Windows).

---

### Task 1: generation

**Files:**
- Create: `skills/russellian-style/scripts/voice_eval.py`
- Test: `skills/russellian-style/tests/test_voice_eval.py`

- [ ] **Step 1: Write the failing test**

```python
"""Cites REQ-VEVAL-001, REQ-VEVAL-002, REQ-VEVAL-008."""
import pytest
pytestmark = pytest.mark.windows_canary
from scripts.voice_eval import build_generation_prompt, generate_paragraphs, DEFAULT_N


def test_default_paragraph_count_is_30():
    assert DEFAULT_N == 30

def test_prompt_embeds_contract_topic_and_count():
    p = build_generation_prompt("the history of zero", "polemic", 12)
    assert "the history of zero" in p
    assert "12" in p
    assert "# Calibration and planning" in p        # the mode contract is included
    assert "verdict" in p.lower() or "antithesis" in p.lower()   # polemic contract text

def test_generate_paragraphs_calls_llm_with_prompt_and_returns_output():
    captured = {}
    def fake_llm(prompt):
        captured["prompt"] = prompt
        return "GENERATED PROSE"
    out = generate_paragraphs("topic X", mode="technical-exposition", n=5, llm_call=fake_llm)
    assert out == "GENERATED PROSE"
    assert "topic X" in captured["prompt"]
    assert "5" in captured["prompt"]

def test_generate_paragraphs_rejects_unknown_mode():
    with pytest.raises(ValueError):
        generate_paragraphs("t", mode="nope", n=5, llm_call=lambda p: "")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd skills/russellian-style && .venv/Scripts/python.exe -m pytest tests/test_voice_eval.py -v`
Expected: FAIL (module does not exist).

- [ ] **Step 3: Write minimal implementation** (top of `voice_eval.py`)

```python
"""Generate Russell-voice paragraphs and compare them to original Russell.

Advisory eval stage. Generation uses an injected LLM callable (no live calls).
Comparison uses the Russell-Delta scorer and the russellian-style linter battery.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Callable, Optional

from scripts.system_prompt_loader import load as load_prompt, VALID_MODES

DEFAULT_N = 30
DEFAULT_MODE = "technical-exposition"


def build_generation_prompt(topic: str, mode: str, n: int) -> str:
    contract = load_prompt(mode)
    return (
        f"{contract}\n\n"
        f"# Task\n"
        f"Write {n} paragraphs on the following topic, observing the contract above. "
        f"Topic: {topic}\n"
        f"Output only the prose: no headings, no preamble, no numbering."
    )


def generate_paragraphs(topic: str, mode: str = DEFAULT_MODE, n: int = DEFAULT_N,
                        *, llm_call: Callable[[str], str]) -> str:
    if mode not in VALID_MODES:
        raise ValueError(f"unknown mode: {mode!r}; valid: {sorted(VALID_MODES)}")
    return llm_call(build_generation_prompt(topic, mode, n))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd skills/russellian-style && .venv/Scripts/python.exe -m pytest tests/test_voice_eval.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git -C C:\russellian-book-suite add skills/russellian-style/scripts/voice_eval.py skills/russellian-style/tests/test_voice_eval.py
git -C C:\russellian-book-suite commit -m "Add voice-eval generation step"
```

---

### Task 2: evaluation (Delta + linter battery)

**Files:**
- Modify: `skills/russellian-style/scripts/voice_eval.py`
- Test: `skills/russellian-style/tests/test_voice_eval.py`

- [ ] **Step 1: Append the failing test**

```python
def test_evaluate_reports_delta_and_linters():
    from scripts.voice_eval import evaluate
    text = "The nineteenth century discovered pure mathematics. " * 80
    rep = evaluate(text)
    g = rep["generated"]
    assert g["russell_delta"]["metric"] == "russell-burrows-delta"
    assert "verdict" in g["russell_delta"]
    assert g["n_words"] > 0
    assert "hedges" in g["linters"] and "passive_voice" in g["linters"]
    # each linter entry carries a raw count and a per-1000-word density
    assert set(g["linters"]["hedges"]) == {"count", "per_1000"}
    assert rep["baseline"] is None

def test_evaluate_with_baseline_reports_side_by_side():
    from scripts.voice_eval import evaluate
    gen = "The argument proceeds by cases. " * 80
    base = "Philosophy is to be studied for the questions themselves. " * 80
    rep = evaluate(gen, russell_baseline_text=base)
    assert rep["baseline"] is not None
    assert rep["baseline"]["russell_delta"]["metric"] == "russell-burrows-delta"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd skills/russellian-style && .venv/Scripts/python.exe -m pytest tests/test_voice_eval.py::test_evaluate_reports_delta_and_linters -v`
Expected: FAIL (`evaluate` not defined).

- [ ] **Step 3: Implement** — append to `voice_eval.py`

```python
from scripts.score_russell_delta import score as _delta_score, load_profile, PROFILE_PATH
from scripts.lint_hedges import lint_hedges
from scripts.lint_passive_voice import lint_passive_voice
from scripts.lint_signal_density import lint_signal_density
from scripts.lint_parallel_structure import lint_parallel_structure
from scripts.lint_listicle_abstract import lint_listicle_abstract
from scripts.lint_sentence_rhythm import lint_sentence_rhythm
from scripts.lint_burstiness import lint_burstiness
from scripts.lint_ai_vocabulary import lint_ai_vocabulary
from scripts.lint_ai_staccato import lint_ai_staccato
from scripts.lint_concrete_instance_density import lint_concrete_instance_density
from scripts.lint_epistemic_precision import lint_epistemic_precision
from scripts.lint_paragraph_motion import lint_paragraph_motion

LINTERS = {
    "hedges": lint_hedges,
    "passive_voice": lint_passive_voice,
    "signal_density": lint_signal_density,
    "parallel_structure": lint_parallel_structure,
    "listicle_abstract": lint_listicle_abstract,
    "sentence_rhythm": lint_sentence_rhythm,
    "burstiness": lint_burstiness,
    "ai_vocabulary": lint_ai_vocabulary,
    "ai_staccato": lint_ai_staccato,
    "concrete_instance_density": lint_concrete_instance_density,
    "epistemic_precision": lint_epistemic_precision,
    "paragraph_motion": lint_paragraph_motion,
}


def _signals(text: str, profile: dict) -> dict:
    delta = _delta_score(text, profile)
    n_words = delta["n_words"]
    fd, name = tempfile.mkstemp(suffix=".md")
    os.close(fd)
    path = Path(name)
    try:
        path.write_text(text, encoding="utf-8")
        linters = {}
        for lname, fn in LINTERS.items():
            count = len(fn(path))
            per_1000 = round(count / n_words * 1000, 3) if n_words else 0.0
            linters[lname] = {"count": count, "per_1000": per_1000}
    finally:
        path.unlink(missing_ok=True)
    return {"russell_delta": delta, "n_words": n_words, "linters": linters}


def evaluate(generated_text: str, russell_baseline_text: Optional[str] = None,
             profile_path: Path = PROFILE_PATH) -> dict:
    profile = load_profile(profile_path)
    report = {"generated": _signals(generated_text, profile), "baseline": None}
    if russell_baseline_text is not None:
        report["baseline"] = _signals(russell_baseline_text, profile)
    return report
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd skills/russellian-style && .venv/Scripts/python.exe -m pytest tests/test_voice_eval.py -v`
Expected: PASS (6 tests). Requires the spaCy venv (the linters import spaCy), as the existing report tests do.

- [ ] **Step 5: Commit**

```bash
git -C C:\russellian-book-suite add skills/russellian-style/scripts/voice_eval.py skills/russellian-style/tests/test_voice_eval.py
git -C C:\russellian-book-suite commit -m "Add voice-eval comparison (Delta + linter battery)"
```

---

### Task 3: run, report writer, CLI

**Files:**
- Modify: `skills/russellian-style/scripts/voice_eval.py`
- Test: `skills/russellian-style/tests/test_voice_eval.py`

- [ ] **Step 1: Append the failing test**

```python
def test_run_orchestrates_generation_and_eval():
    from scripts.voice_eval import run
    rep = run("the calculus", mode="technical-exposition", n=4,
              llm_call=lambda prompt: "The calculus was invented twice. " * 80)
    assert rep["meta"]["topic"] == "the calculus"
    assert rep["meta"]["n_requested"] == 4
    assert rep["generated_text"].startswith("The calculus")
    assert rep["generated"]["russell_delta"]["metric"] == "russell-burrows-delta"

def test_write_report_emits_paragraphs_and_table(tmp_path):
    from scripts.voice_eval import run, write_report
    rep = run("x", mode="polemic", n=3, llm_call=lambda p: "An argument with a turn. " * 80)
    out = tmp_path / "report.md"
    write_report(rep, out)
    md = out.read_text(encoding="utf-8")
    assert "russell-burrows-delta" in md
    assert "An argument with a turn." in md      # the generated prose is included
    assert "| linter |" in md                    # the comparison table header
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd skills/russellian-style && .venv/Scripts/python.exe -m pytest tests/test_voice_eval.py::test_run_orchestrates_generation_and_eval -v`
Expected: FAIL (`run` not defined).

- [ ] **Step 3: Implement** — append to `voice_eval.py`

```python
def run(topic: str, mode: str = DEFAULT_MODE, n: int = DEFAULT_N, *,
        llm_call: Callable[[str], str], russell_baseline_path: Optional[str] = None) -> dict:
    text = generate_paragraphs(topic, mode, n, llm_call=llm_call)
    baseline_text = None
    if russell_baseline_path:
        baseline_text = Path(russell_baseline_path).read_text(encoding="utf-8", errors="replace")
    report = evaluate(text, baseline_text)
    report["meta"] = {"topic": topic, "mode": mode, "n_requested": n}
    report["generated_text"] = text
    return report


def _delta_line(sig: dict) -> str:
    d = sig["russell_delta"]
    return f"delta={d['delta']} verdict={d['verdict']} (band p50={d['band']['p50']} p90={d['band']['p90']}) words={sig['n_words']}"


def write_report(report: dict, out_path) -> None:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    meta = report.get("meta", {})
    gen = report["generated"]
    base = report.get("baseline")
    lines = [
        f"# Voice-eval report",
        "",
        f"- topic: {meta.get('topic')}",
        f"- mode: {meta.get('mode')}",
        f"- paragraphs requested: {meta.get('n_requested')}",
        "",
        "## Russell-Delta",
        "",
        f"- generated: {_delta_line(gen)}",
    ]
    if base:
        lines.append(f"- russell baseline: {_delta_line(base)}")
    lines += ["", "## Linter densities (per 1,000 words)", "",
              "| linter | generated | russell baseline |", "|---|---:|---:|"]
    for lname in gen["linters"]:
        g = gen["linters"][lname]["per_1000"]
        b = base["linters"][lname]["per_1000"] if base else "-"
        lines.append(f"| {lname} | {g} | {b} |")
    lines += ["", "## Generated prose", "", report.get("generated_text", "")]
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str]) -> int:
    # CLI evaluates an already-generated markdown file (generation needs an LLM callable,
    # supplied programmatically via run()).
    if len(argv) < 2:
        print("usage: voice_eval.py <generated.md> [russell_baseline.md] [out.md]", file=sys.stderr)
        return 2
    generated = Path(argv[1]).read_text(encoding="utf-8", errors="replace")
    baseline = Path(argv[2]).read_text(encoding="utf-8", errors="replace") if len(argv) > 2 else None
    report = evaluate(generated, baseline)
    report["meta"] = {"topic": "(cli)", "mode": "(cli)", "n_requested": "(cli)"}
    report["generated_text"] = generated
    if len(argv) > 3:
        write_report(report, argv[3])
        print(f"wrote {argv[3]}")
    else:
        print(json.dumps({k: v for k, v in report.items() if k != "generated_text"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd skills/russellian-style && .venv/Scripts/python.exe -m pytest tests/test_voice_eval.py -v`
Expected: PASS (8 tests).

- [ ] **Step 5: Commit**

```bash
git -C C:\russellian-book-suite add skills/russellian-style/scripts/voice_eval.py skills/russellian-style/tests/test_voice_eval.py
git -C C:\russellian-book-suite commit -m "Add voice-eval run, report writer, and CLI"
```

---

### Task 4: regression + demo bundle

**Files:**
- Create: `docs/audits/2026-05-27-voice-eval/generated.md`
- Create: `docs/audits/2026-05-27-voice-eval/report.md`
- Create: `docs/audits/2026-05-27-voice-eval/README.md`

- [ ] **Step 1: Full russellian-style suite (regression)**

Run: `cd skills/russellian-style && .venv/Scripts/python.exe -m pytest tests/ -q`
Expected: PASS (all prior tests + `test_voice_eval.py`). No regressions.

- [ ] **Step 2: Produce 30 paragraphs (foreground session as the LLM)**

The implementing agent (or a foreground Claude session) writes 30 paragraphs on a chosen
topic following the `technical-exposition` (or `polemic`) contract, and saves them to
`docs/audits/2026-05-27-voice-eval/generated.md`. This is the `llm_call` output; the prose
must observe the mode contract (silent motion plan, atomic sentences, concrete instances,
no banned vocabulary) and must be original.

- [ ] **Step 3: Compare against a genuine Russell excerpt and write the report**

Use a real Russell excerpt as the baseline (e.g. the Mysticism essay at
`C:\Users\charl\AppData\Local\Temp\compare\real-russell-math.md`, or any source file in
`C:\Users\charl\AppData\Local\Temp\russell_delta_src\`). Run:

```bash
cd /c/russellian-book-suite/skills/russellian-style
.venv/Scripts/python.exe -m scripts.voice_eval \
  ../../docs/audits/2026-05-27-voice-eval/generated.md \
  "C:\Users\charl\AppData\Local\Temp\compare\real-russell-math.md" \
  ../../docs/audits/2026-05-27-voice-eval/report.md
```

Confirm `report.md` shows the generated Delta/verdict, the Russell baseline Delta/verdict,
and the side-by-side linter density table.

- [ ] **Step 4: Write the bundle README and commit**

`README.md` states the topic, mode, the generated and baseline Delta/verdict, and an
honest one-paragraph read of how close the generated prose came to Russell.

```bash
git -C C:\russellian-book-suite add docs/audits/2026-05-27-voice-eval/
git -C C:\russellian-book-suite commit -m "Add voice-eval demo bundle"
```

---

## Self-review (completed during planning)

- **Spec coverage:** REQ-VEVAL-001 (build_generation_prompt + generate_paragraphs, Task 1); 002 (injected llm_call, no live calls — Tasks 1/2/3 use fakes; Task 1 test); 003 (evaluate: Delta + 12 linters, Task 2); 004 (baseline branch, Task 2); 005 (determinism + offline — scoring is deterministic, no network; asserted implicitly via fixed-input tests); 006 (advisory — no raise/gate anywhere); 007 (write_report bundle, Task 3); 008 (DEFAULT_N == 30, Task 1). All mapped.
- **Placeholder scan:** none — full module code and commands given.
- **Type/name consistency:** `build_generation_prompt`, `generate_paragraphs`, `evaluate`, `_signals`, `run`, `write_report`, `LINTERS`, `DEFAULT_N` consistent across tasks; report keys (`generated`, `baseline`, `meta`, `generated_text`, `russell_delta`, `linters`, `n_words`) consistent between `evaluate`/`run`/`write_report`.

## Not in scope

- Contrastive Delta (Russell vs. other authors); budget-linter recalibration; the rubric judge.
- Wiring a live LLM into the CLI (generation is programmatic via `run()` with an injected callable); pushing / opening a PR.
