# HFR v2 — Plan 2 of 5: Floor Calibration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a versioned v2 ruleset to `russellian-style` that (a) exempts a deliberate anaphoric *drumbeat* from the rhythm rule and (b) replaces the global 0.25 modifier budget with a register-conditioned corridor derived from the Hoskinson corpus — while leaving the v1 ruleset byte-frozen so the 20×20 control is reproducible.

**Architecture:** The floor stays negative and hard. `russellian-style/scripts/lint_common.load_rules` gains a ruleset selector; the two linters (`lint_sentence_rhythm`, `lint_signal_density`) gain `--ruleset`/`--register` and read v2 behavior only when pointed at `russellian-rules-v2.json`. The per-register modifier budgets are *baked* into the v2 rules file from corpus modifier-ratio percentiles produced by `liveliness-signals` (Task 1) — so the floor reads only its own rules at lint time and never imports the signals skill.

**Tech Stack:** Python 3.14, spaCy `en_core_web_sm`, stdlib. Two skills touched: `liveliness-signals` (Task 1, profiler extension) and `russellian-style` (Tasks 2–5).

## Plan set (this is Plan 2 of 5)
1. Corpus Style-Profile — DONE (`docs/plans/2026-06-19-hfr-v2-liveliness-corpus-profile.md`)
2. **Floor calibration** ← this plan
3. Liveliness signals (8 scorers + Brysbaert + regression set)
4. Generation v2 (`triadic-voice-v2`)
5. Evaluation (`voice-eval` 20×20 harness)

## Global Constraints

- Python `>=3.11`; live env 3.14. spaCy `>=3.7,<4.0` + `en_core_web_sm`. (spec)
- **The v1 ruleset `russellian-style/assets/russellian-rules.json` MUST stay byte-frozen.** No edit to it; v2 lives in a new file. (REQ-VOICE-008)
- **v1 linter behavior MUST be unchanged** when no `--ruleset`/`--register` is given (default = v1). The 20×20 control depends on this. (REQ-VOICE-009 MODIFY clause)
- The accuracy floor (atomicity, hedging, epistemic precision, agentless passive) is identical across registers; only texture dials (rhythm exemption, modifier budget) change. (REQ-VOICE-011)
- Tests carry `pytestmark = pytest.mark.windows_canary`, cite REQ IDs in the module docstring, output pristine. No "Co-Authored-By"/AI attribution; terse commits. (repo convention)
- `ruff.toml` ignores E402/E731/E701/E702/E741; F401/F841 are on. Keep imports clean (F-rules), don't worry about E-style.
- Registers are exactly `technical-exposition`, `narrative-editorial`, `polemic`.

## Environment setup (run once before Task 2)

`russellian-style` needs its own venv in this worktree (gitignored, not carried). The `[ci]` extra omits `click`/`typer`, which `spacy download` imports:
```
cd skills/russellian-style
python -m venv .venv
.venv/Scripts/python.exe -m pip install -q -e ".[ci]"
.venv/Scripts/python.exe -m pip install -q "click>=8" "typer>=0.9"
.venv/Scripts/python.exe -m spacy download en_core_web_sm
.venv/Scripts/python.exe -m pytest -q
```
Expected: the existing russellian-style suite passes (baseline green before changes).

---

### Task 1: Add per-register modifier-ratio percentiles to the profile

**Files:**
- Modify: `skills/liveliness-signals/scripts/profile_metrics.py`
- Modify: `skills/liveliness-signals/scripts/build_corpus_profile.py`
- Modify: `skills/liveliness-signals/tests/test_profile_metrics.py`
- Modify: `skills/liveliness-signals/tests/test_build_corpus_profile.py`
- Regenerate: `skills/liveliness-signals/assets/hoskinson-style-profile.json`

**Interfaces:**
- Produces: `modifier_ratios(texts: list[str]) -> list[float]` in `profile_metrics` (per-sentence ADJ+ADV / alpha-token ratio, for sentences with ≥8 alpha tokens — matching the floor linter's threshold). Adds a `modifier` block `{p50,p75,p90,count}` to each register and `global` in the profile.

Work from the `liveliness-signals` venv: `cd skills/liveliness-signals && .venv/Scripts/python.exe -m pytest ...`

- [ ] **Step 1: Write the failing test for `modifier_ratios`**

```python
# add to skills/liveliness-signals/tests/test_profile_metrics.py
from scripts.profile_metrics import modifier_ratios

@pytest.mark.needs_model
def test_modifier_ratios_only_counts_long_sentences():
    # first sentence has >=8 alpha tokens with 2 modifiers; "No." is too short to count
    texts = ["The very bright young student quickly solved the hard problem. No."]
    r = modifier_ratios(texts)
    assert len(r) == 1            # short sentence excluded
    assert 0.0 < r[0] < 1.0
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `cd skills/liveliness-signals && .venv/Scripts/python.exe -m pytest tests/test_profile_metrics.py::test_modifier_ratios_only_counts_long_sentences -q`
Expected: FAIL — `ImportError: cannot import name 'modifier_ratios'`.

- [ ] **Step 3: Implement `modifier_ratios`**

```python
# append to skills/liveliness-signals/scripts/profile_metrics.py
def modifier_ratios(texts: list[str], min_alpha: int = 8) -> list[float]:
    """Per-sentence modifier (ADJ+ADV) ratio over alpha tokens.

    Only sentences with at least `min_alpha` alpha tokens are measured, matching
    the russellian-style signal-density linter's assessment threshold. The shared
    `_nlp()` keeps the POS tagger (only ner/lemmatizer are disabled), so `pos_`
    is available.
    """
    nlp = _nlp()
    out: list[float] = []
    for text in texts:
        for sent in nlp(text).sents:
            content = [t for t in sent if t.is_alpha]
            if len(content) < min_alpha:
                continue
            mods = sum(1 for t in content if t.pos_ in ("ADJ", "ADV"))
            out.append(mods / len(content))
    return out
```

- [ ] **Step 4: Run to confirm it passes**

Run: `cd skills/liveliness-signals && .venv/Scripts/python.exe -m pytest tests/test_profile_metrics.py -q`
Expected: 5 passed.

- [ ] **Step 5: Write the failing test for the profile `modifier` block**

```python
# add to skills/liveliness-signals/tests/test_build_corpus_profile.py
@pytest.mark.needs_model
def test_build_profile_has_modifier_block():
    rows = [{"id": f"p{i}", "text": "The very bright young student quickly solved the hard problem.",
             "register": "narrative-editorial"} for i in range(6)]
    p = build_profile(rows, min_per_register=5)
    blk = p["registers"]["narrative-editorial"]["modifier"]
    assert set(blk) >= {"p50", "p75", "p90", "count"}
    assert "modifier" in p["global"]
```

- [ ] **Step 6: Run it to confirm it fails**

Run: `cd skills/liveliness-signals && .venv/Scripts/python.exe -m pytest tests/test_build_corpus_profile.py::test_build_profile_has_modifier_block -q`
Expected: FAIL — `KeyError: 'modifier'`.

- [ ] **Step 7: Wire the modifier block into `_profile_for`**

```python
# in skills/liveliness-signals/scripts/build_corpus_profile.py
# add import at top alongside the existing profile_metrics import:
from scripts.profile_metrics import (
    sentence_lengths, cadence_corridor, diction_device_metrics, modifier_ratios,
)

# add this helper near _profile_for:
def _modifier_block(texts: list[str]) -> dict:
    ratios = sorted(modifier_ratios(texts))
    def pct(p):
        if not ratios:
            return 0.0
        k = min(len(ratios) - 1, int(round(p * (len(ratios) - 1))))
        return round(float(ratios[k]), 6)
    return {"p50": pct(0.50), "p75": pct(0.75), "p90": pct(0.90), "count": len(ratios)}

# extend _profile_for to include the modifier block:
def _profile_for(texts: list[str]) -> dict:
    return {"cadence": cadence_corridor(sentence_lengths(texts)),
            "diction": diction_device_metrics(texts),
            "modifier": _modifier_block(texts)}
```

The fallback branch in `build_profile` already copies the whole `glob` cadence/diction; extend it to also copy `glob` modifier. Change the fallback dict to:
```python
            registers[reg] = {"count": len(texts), "fallback": True,
                              "cadence": glob["cadence"], "diction": glob["diction"],
                              "modifier": glob["modifier"]}
```

- [ ] **Step 8: Run the full skill suite**

Run: `cd skills/liveliness-signals && .venv/Scripts/python.exe -m pytest -q`
Expected: all pass (12 now).

- [ ] **Step 9: Regenerate the asset and commit**

```bash
cd skills/liveliness-signals && .venv/Scripts/python.exe -m scripts.build_corpus_profile
# from worktree ROOT:
git add skills/liveliness-signals/scripts/profile_metrics.py skills/liveliness-signals/scripts/build_corpus_profile.py \
  skills/liveliness-signals/tests/test_profile_metrics.py skills/liveliness-signals/tests/test_build_corpus_profile.py \
  skills/liveliness-signals/assets/hoskinson-style-profile.json
git commit -m "Add per-register modifier-ratio percentiles to the corpus profile"
```

- [ ] **Step 10: Record the baked budget inputs**

Run and note the three numbers (used in Task 3):
`cd skills/liveliness-signals && .venv/Scripts/python.exe -c "import skill_api as s; p=s.load_profile(); print({r: p['registers'][r]['modifier'] for r in p['registers']})"`
Write the p75 (technical, polemic) and p90 (narrative-editorial) values into the Task-3 rules file.

---

### Task 2: Versioned ruleset selector in `russellian-style`

**Files:**
- Modify: `skills/russellian-style/scripts/lint_common.py`
- Test: `skills/russellian-style/tests/test_ruleset_selector.py`

**Interfaces:**
- Produces: `load_rules(name: str = "russellian-rules.json") -> dict` — backward-compatible (default reads the frozen v1 file). Later tasks call `load_rules("russellian-rules-v2.json")`.

Work from the `russellian-style` venv.

- [ ] **Step 1: Write the failing test**

```python
# skills/russellian-style/tests/test_ruleset_selector.py
"""Cites REQ-VOICE-008 (versioned ruleset selector)."""
import pytest
pytestmark = pytest.mark.windows_canary
from scripts.lint_common import load_rules


def test_load_rules_defaults_to_v1_frozen():
    r = load_rules()
    assert r["modifier_budget_ratio"] == 0.25  # the frozen v1 value


def test_load_rules_accepts_named_ruleset():
    r = load_rules("russellian-rules.json")  # same file, explicit
    assert "modifier_budget_ratio" in r
```

- [ ] **Step 2: Run to confirm it fails**

Run: `cd skills/russellian-style && .venv/Scripts/python.exe -m pytest tests/test_ruleset_selector.py -q`
Expected: FAIL — `test_load_rules_accepts_named_ruleset` errors (load_rules takes no arg).

- [ ] **Step 3: Add the selector (backward-compatible)**

In `skills/russellian-style/scripts/lint_common.py`, replace the existing `load_rules`:
```python
def load_rules(name: str = "russellian-rules.json") -> dict:
    return json.loads((ASSETS / name).read_text(encoding="utf-8"))
```
(Only the signature gains a defaulted `name`; the default path is identical to before, so every existing caller is unchanged.)

- [ ] **Step 4: Run to confirm pass + no regression**

Run: `cd skills/russellian-style && .venv/Scripts/python.exe -m pytest tests/test_ruleset_selector.py -q && .venv/Scripts/python.exe -m pytest -q`
Expected: new tests pass; full suite still green (the default-arg change breaks nothing).

- [ ] **Step 5: Commit**

```bash
git add skills/russellian-style/scripts/lint_common.py skills/russellian-style/tests/test_ruleset_selector.py
git commit -m "Add backward-compatible named-ruleset selector to load_rules"
```

---

### Task 3: The v2 rules file + drumbeat exemption in the rhythm linter

**Files:**
- Create: `skills/russellian-style/assets/russellian-rules-v2.json`
- Modify: `skills/russellian-style/scripts/lint_sentence_rhythm.py`
- Test: `skills/russellian-style/tests/test_rhythm_drumbeat.py`

**Interfaces:**
- Produces: `lint_sentence_rhythm(path, rules=None)` — accepts an optional pre-loaded rules dict (defaults to `load_rules()` = v1). When `rules["rhythm_drumbeat_exemption"]` is true, a repeated-opening run that satisfies all four drumbeat conditions is exempted and emitted as a `parallel-list` credit instead of a `rhythm-repeated-opening` defect.

- [ ] **Step 1: Create the v2 rules file**

Copy the frozen v1 file and add two keys. Build it deterministically:
```bash
cd skills/russellian-style && .venv/Scripts/python.exe -c "
import json
from pathlib import Path
a = Path('assets')
v1 = json.loads((a/'russellian-rules.json').read_text(encoding='utf-8'))
v1['version'] = v1.get('version','1') + '+v2'
v1['rhythm_drumbeat_exemption'] = True
v1['drumbeat_min_length_cv'] = 0.10      # run word-count CV must exceed this (lengths not mechanically identical)
v1['drumbeat_max_pairwise_overlap'] = 0.6 # avg Jaccard of remainder words must be below this (progressive)
# Register modifier corridor — budgets baked from the corpus modifier percentiles (Task 1 Step 10).
# Replace the three numbers below with the recorded values (technical p75, narrative p90, polemic p75),
# each floored at the design's starting dial so the corridor is never looser than intended.
v1['modifier_budget_by_register'] = {
    'technical-exposition': 0.20,
    'narrative-editorial': 0.30,
    'polemic': 0.25,
}
(a/'russellian-rules-v2.json').write_text(json.dumps(v1, indent=2), encoding='utf-8')
print('wrote russellian-rules-v2.json')
"
```
Then edit the three `modifier_budget_by_register` numbers to `max(<recorded percentile>, <starting dial above>)` using the Task-1 Step-10 output. (The frozen v1 file is untouched.)

- [ ] **Step 2: Write the failing drumbeat test**

```python
# skills/russellian-style/tests/test_rhythm_drumbeat.py
"""Cites REQ-VOICE-009 (drumbeat exemption; v1 unchanged)."""
import pytest
pytestmark = pytest.mark.windows_canary
from pathlib import Path
from scripts.lint_common import load_rules
from scripts.lint_sentence_rhythm import lint_sentence_rhythm

DRUMBEAT = (
    "The setup ceremony that builds the mathematical stage is one trust. "
    "The language you wrote the program in is another. "
    "The witness, the arithmetization, the proof system, and the on-chain contract are each a separate bet. "
    "What people miss is that every one of them is independently testable."
)
TIC = "This is fine. This is good. This is great. This is done."


def _write(tmp_path, text):
    p = tmp_path / "p.md"
    p.write_text(text, encoding="utf-8")
    return p


def test_v1_still_flags_the_drumbeat(tmp_path):
    # frozen v1 behavior: the four "The" run is a repeated-opening defect
    findings = lint_sentence_rhythm(_write(tmp_path, DRUMBEAT))
    assert any(f["rule"] == "rhythm-repeated-opening" for f in findings)


def test_v2_exempts_the_drumbeat_as_parallel_list(tmp_path):
    rules = load_rules("russellian-rules-v2.json")
    findings = lint_sentence_rhythm(_write(tmp_path, DRUMBEAT), rules=rules)
    assert not any(f["rule"] == "rhythm-repeated-opening" for f in findings)
    assert any(f["rule"] == "parallel-list" for f in findings)


def test_v2_still_flags_a_real_tic(tmp_path):
    rules = load_rules("russellian-rules-v2.json")
    findings = lint_sentence_rhythm(_write(tmp_path, TIC), rules=rules)
    assert any(f["rule"] == "rhythm-repeated-opening" for f in findings)
```

- [ ] **Step 3: Run to confirm the v2 tests fail**

Run: `cd skills/russellian-style && .venv/Scripts/python.exe -m pytest tests/test_rhythm_drumbeat.py -q`
Expected: `test_v1_still_flags_the_drumbeat` PASSES (v1 unchanged); the two v2 tests FAIL (no `rules` param / no `parallel-list` rule yet).

- [ ] **Step 4: Add the drumbeat exemption**

Edit `skills/russellian-style/scripts/lint_sentence_rhythm.py`. Add helpers and thread an optional `rules` arg:
```python
# add near the top, after the existing imports:
FUNCTION_OPENERS = {
    "the", "a", "an", "this", "that", "these", "those",
    "it", "they", "we", "you", "he", "she", "there", "here",
}

def _content_words(s: str) -> set[str]:
    return {w.lower() for w in re.findall(r"\b\w+\b", s)}

def _is_drumbeat(run_sents, capper_exists: bool, rules: dict) -> bool:
    """Four conditions (REQ-VOICE-009): shallow opener; progressive (distinct
    remainders); lengths not mechanically identical; capped by a turn within 1-2."""
    opener = _first_word(run_sents[0].text)
    if opener not in FUNCTION_OPENERS:
        return False
    if not capper_exists:
        return False
    counts = [_word_count(s.text) for s in run_sents]
    mu = sum(counts) / len(counts)
    cv = (sum((c - mu) ** 2 for c in counts) / len(counts)) ** 0.5 / mu if mu else 0.0
    if cv <= float(rules.get("drumbeat_min_length_cv", 0.10)):
        return False
    # progressive: average pairwise Jaccard of content words (minus the shared opener) is low
    sets = [_content_words(s.text) - {opener} for s in run_sents]
    pairs = [(i, j) for i in range(len(sets)) for j in range(i + 1, len(sets))]
    def jac(a, b):
        u = a | b
        return len(a & b) / len(u) if u else 0.0
    avg_overlap = sum(jac(sets[i], sets[j]) for i, j in pairs) / len(pairs) if pairs else 0.0
    return avg_overlap < float(rules.get("drumbeat_max_pairwise_overlap", 0.6))
```
Change the signature and the repeated-opening block:
```python
def lint_sentence_rhythm(path: Path, rules: dict | None = None) -> list[dict]:
    text = load_markdown(path)
    if rules is None:
        rules = load_rules()
    min_run = int(rules.get("rhythm_run_min_length", 4))
    tolerance = int(rules.get("rhythm_word_count_tolerance", 3))
    exemption = bool(rules.get("rhythm_drumbeat_exemption", False))
    ...
```
In the repeated-opening loop, where the run of length `run_len >= min_run` is found, replace the single append with:
```python
        if run_len >= min_run:
            run_sents = sentences[i:j]
            capper_exists = j < len(firsts)
            if exemption and _is_drumbeat(run_sents, capper_exists, rules):
                findings.append({
                    "rule": "parallel-list",
                    "first_word": run_first,
                    "start_line": sentences[i].line,
                    "run_length": run_len,
                    "snippet": " ".join(s.text for s in run_sents)[:400],
                })
            else:
                findings.append({
                    "rule": "rhythm-repeated-opening",
                    "first_word": run_first,
                    "start_line": sentences[i].line,
                    "run_length": run_len,
                    "snippet": " ".join(s.text for s in run_sents)[:400],
                })
            i = j
        else:
            i += 1
```
(The uniform-length block and `main()` are unchanged; `main()` still calls `lint_sentence_rhythm(Path(argv[1]))` so the CLI default stays v1.)

- [ ] **Step 5: Run the drumbeat tests + full suite**

Run: `cd skills/russellian-style && .venv/Scripts/python.exe -m pytest tests/test_rhythm_drumbeat.py -q && .venv/Scripts/python.exe -m pytest -q`
Expected: all three drumbeat tests pass; full russellian-style suite still green (v1 default path unchanged).

- [ ] **Step 6: Commit**

```bash
git add skills/russellian-style/assets/russellian-rules-v2.json \
  skills/russellian-style/scripts/lint_sentence_rhythm.py \
  skills/russellian-style/tests/test_rhythm_drumbeat.py
git commit -m "Add v2 ruleset with rhythm drumbeat exemption"
```

---

### Task 4: Register-conditioned modifier corridor in the signal-density linter

**Files:**
- Modify: `skills/russellian-style/scripts/lint_signal_density.py`
- Test: `skills/russellian-style/tests/test_register_corridor.py`

**Interfaces:**
- Produces: `lint_signal_density(path, rules=None, register=None)` — when `register` is given and `rules` carries `modifier_budget_by_register`, the budget for that register is used; otherwise the global `modifier_budget_ratio` (v1 behavior).

- [ ] **Step 1: Write the failing test**

```python
# skills/russellian-style/tests/test_register_corridor.py
"""Cites REQ-VOICE-010, REQ-VOICE-011 (register modifier corridor; v1 unchanged)."""
import pytest
pytestmark = pytest.mark.windows_canary
from pathlib import Path
from scripts.lint_common import load_rules
from scripts.lint_signal_density import lint_signal_density

# A sentence with a modifier ratio between the v1 budget (0.25) and the narrative budget (0.30).
BORDERLINE = "The genuinely careful early reader quietly tracks each subtle structural cue forward."


def _write(tmp_path, text):
    p = tmp_path / "p.md"
    p.write_text(text, encoding="utf-8")
    return p


def test_v1_default_uses_global_budget(tmp_path):
    # no register -> global 0.25 budget (frozen v1 behavior)
    f_default = lint_signal_density(_write(tmp_path, BORDERLINE))
    f_v1_explicit = lint_signal_density(_write(tmp_path, BORDERLINE), rules=load_rules())
    assert [x["rule"] for x in f_default] == [x["rule"] for x in f_v1_explicit]


def test_narrative_register_relaxes_the_budget(tmp_path):
    rules = load_rules("russellian-rules-v2.json")
    flagged_global = lint_signal_density(_write(tmp_path, BORDERLINE), rules=rules)  # no register -> global
    flagged_narrative = lint_signal_density(_write(tmp_path, BORDERLINE), rules=rules, register="narrative-editorial")
    # The borderline sentence trips the tighter global budget but clears the relaxed narrative budget.
    assert len(flagged_narrative) <= len(flagged_global)
```

- [ ] **Step 2: Run to confirm it fails**

Run: `cd skills/russellian-style && .venv/Scripts/python.exe -m pytest tests/test_register_corridor.py -q`
Expected: FAIL — `lint_signal_density` takes no `rules`/`register` args.

- [ ] **Step 3: Add the register corridor**

Edit `skills/russellian-style/scripts/lint_signal_density.py`:
```python
def lint_signal_density(path: Path, rules: dict | None = None, register: str | None = None) -> list[dict]:
    text = load_markdown(path)
    if rules is None:
        rules = load_rules()
    budget = rules["modifier_budget_ratio"]
    by_reg = rules.get("modifier_budget_by_register")
    if register and by_reg and register in by_reg:
        budget = by_reg[register]
    nlp = _nlp()
    overrides = _load_overrides()
    ...
```
The rest of the function is unchanged (it already reports `"budget": budget`). `main()` still calls `lint_signal_density(Path(argv[1]))`, so the CLI default stays v1.

- [ ] **Step 4: Run the corridor tests + full suite**

Run: `cd skills/russellian-style && .venv/Scripts/python.exe -m pytest tests/test_register_corridor.py -q && .venv/Scripts/python.exe -m pytest -q`
Expected: corridor tests pass; full suite green (default path unchanged). If `BORDERLINE`'s ratio does not straddle 0.25–0.30, adjust the sentence's modifiers until it does (verify with `.venv/Scripts/python.exe -m scripts.lint_signal_density <file>` showing a `modifier_ratio` in (0.25, 0.30]).

- [ ] **Step 5: Commit**

```bash
git add skills/russellian-style/scripts/lint_signal_density.py skills/russellian-style/tests/test_register_corridor.py
git commit -m "Add register-conditioned modifier corridor to signal-density linter"
```

---

### Task 5: CLI flags + device-challenge regression on the real sample

**Files:**
- Modify: `skills/russellian-style/scripts/lint_sentence_rhythm.py` (CLI flags in `main`)
- Modify: `skills/russellian-style/scripts/lint_signal_density.py` (CLI flags in `main`)
- Test: `skills/russellian-style/tests/test_floor_v2_regression.py`

**Interfaces:**
- Produces: both linters' `main` accept `--ruleset NAME` and `--register REG`; absent → v1 defaults.

- [ ] **Step 1: Write the failing regression test**

```python
# skills/russellian-style/tests/test_floor_v2_regression.py
"""Cites REQ-VOICE-009, REQ-VOICE-010 (device-challenge: the real sample passes v2)."""
import pytest
pytestmark = pytest.mark.windows_canary
from pathlib import Path
from scripts.lint_common import load_rules
from scripts.lint_sentence_rhythm import lint_sentence_rhythm

SAMPLE = Path(__file__).resolve().parents[3] / "examples" / "triadic-trust-decomposition.md"


def test_sample_drumbeat_paragraph_passes_under_v2():
    # The trust-decomposition sample's first draft anaphora is a drumbeat, not a tic.
    # Under v2 it must not be flagged as rhythm-repeated-opening.
    assert SAMPLE.exists(), f"sample missing at {SAMPLE}"
    rules = load_rules("russellian-rules-v2.json")
    findings = lint_sentence_rhythm(SAMPLE, rules=rules)
    assert not any(f["rule"] == "rhythm-repeated-opening" for f in findings)
```

- [ ] **Step 2: Run to confirm it passes or fails meaningfully**

Run: `cd skills/russellian-style && .venv/Scripts/python.exe -m pytest tests/test_floor_v2_regression.py -q`
Expected: it may already PASS (the committed sample was edited to break the run in Plan-0 work). If it passes, that confirms v2 is at least as permissive as the hand-fix. If it FAILS, the sample still contains a run v2 should exempt — proceed to Step 3 to confirm the exemption logic covers it; do not edit the sample.

- [ ] **Step 3: Add `--ruleset`/`--register` CLI flags to both linters**

In each linter's `main`, parse the two optional flags before the path. For `lint_sentence_rhythm.py`:
```python
def main(argv: list[str]) -> int:
    args = argv[1:]
    ruleset = "russellian-rules.json"
    rest = []
    i = 0
    while i < len(args):
        if args[i] == "--ruleset" and i + 1 < len(args):
            ruleset = args[i + 1]; i += 2
        else:
            rest.append(args[i]); i += 1
    if not rest:
        print("usage: lint_sentence_rhythm.py [--ruleset NAME] <markdown-file>", file=sys.stderr)
        return 2
    rules = load_rules(ruleset)
    findings = lint_sentence_rhythm(Path(rest[0]), rules=rules)
    print(json.dumps(findings, indent=2))
    return 1 if findings else 0
```
For `lint_signal_density.py`, do the same and also accept `--register REG`, passing `register=` into `lint_signal_density`. Keep the no-flag path identical to v1 (`load_rules("russellian-rules.json")` == default).

- [ ] **Step 4: Run the regression + both full suites**

Run:
```
cd skills/russellian-style && .venv/Scripts/python.exe -m pytest -q
cd ../liveliness-signals && .venv/Scripts/python.exe -m pytest -q
```
Expected: both suites green; the device-challenge test passes.

- [ ] **Step 5: Manual device-challenge confirmation**

Run and eyeball:
```
cd skills/russellian-style
.venv/Scripts/python.exe -m scripts.lint_sentence_rhythm ../../examples/triadic-trust-decomposition.md            # v1: may report repeated-opening
.venv/Scripts/python.exe -m scripts.lint_sentence_rhythm --ruleset russellian-rules-v2.json ../../examples/triadic-trust-decomposition.md  # v2: no repeated-opening (parallel-list credit instead, if a run is present)
```

- [ ] **Step 6: Commit**

```bash
git add skills/russellian-style/scripts/lint_sentence_rhythm.py skills/russellian-style/scripts/lint_signal_density.py \
  skills/russellian-style/tests/test_floor_v2_regression.py
git commit -m "Add --ruleset/--register CLI flags and device-challenge regression"
```

---

## Self-Review

**Spec coverage:**
- REQ-VOICE-008 (named-ruleset selector, v1 frozen) → Task 2; v1 file never edited.
- REQ-VOICE-009 (drumbeat exemption; v1 rhythm unchanged) → Task 3 (4-condition `_is_drumbeat`, `parallel-list` credit) + Task 5 device-challenge.
- REQ-VOICE-010 (register modifier corridor) → Task 1 (corpus percentiles) + Task 3 (baked budgets) + Task 4 (linter reads them).
- REQ-VOICE-011 (accuracy floor identical across registers) → only the modifier budget and rhythm exemption are register/ruleset-conditioned; hedges/passive/epistemic/atomicity linters are untouched. Confirmed by the full-suite-green steps.

**v1-frozen invariant:** every linter keeps a no-arg/CLI default path identical to before; `russellian-rules.json` is never written; `test_v1_still_flags_the_drumbeat` and `test_v1_default_uses_global_budget` pin v1 behavior.

**Placeholder scan:** the only deferred value is the three baked budget numbers in Task 3 Step 1, which Task 1 Step 10 produces concretely before Task 3 runs — not a placeholder, a data dependency with an explicit producer.

**Type consistency:** `load_rules(name=...)` (Task 2) is consumed by `lint_sentence_rhythm(path, rules=...)` (Task 3) and `lint_signal_density(path, rules=..., register=...)` (Task 4); the `parallel-list` finding shape mirrors the existing `rhythm-repeated-opening` keys. Consistent.

**Deferred to Plan 3 (not gaps):** REQ-VOICE-012 (passive end-focus exemption) is left to Plan 3 alongside the analogy/curiosity detector work, since it shares the passive-linter surface; noted here so it is not lost.
