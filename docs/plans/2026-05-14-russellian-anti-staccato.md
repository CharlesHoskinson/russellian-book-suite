# russellian-style Anti-Staccato Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `lint_ai_staccato` linter with four rules plus a positive-checks block in `style_pass_report`, so the skill detects the AI-staccato patterns the existing eleven linters miss.

**Architecture:** New `scripts/lint_ai_staccato.py` mirrors the existing vitality-tier linters (advisory severity, JSON findings, paragraph-segmented input via `lint_common`). The four rules are independent — each is its own TDD task with isolated fixture. `style_pass_report.generate_report_dict` grows a `positive_checks` block aggregating data already produced by other linters plus one new concession-turn regex pass. Two Bitcoin samples land at `tests/fixtures/before_after/` and double as regression fixtures. No existing linter changes signature, severity, or fixtures.

**Tech Stack:** Python 3.13, spaCy (already a dep via `lint_common`), pytest. The venv at `~/.claude/skills/russellian-style/.venv/` is junction-linked into the repo per the CLAUDE.md convention; invoke via `.venv/Scripts/python.exe -m scripts.<name>` from `skills/russellian-style/`.

**Spec:** `docs/specs/2026-05-14-russellian-anti-staccato-design.md`

---

## File Structure

| Path | Action | Responsibility |
|---|---|---|
| `skills/russellian-style/assets/russellian-rules.json` | modify | Add `ai_staccato` config entry with detection thresholds + abstract-noun stoplist |
| `skills/russellian-style/scripts/lint_ai_staccato.py` | create | Four detection rules; advisory tier; JSON-finding output |
| `skills/russellian-style/scripts/style_pass_report.py` | modify | Include staccato lint in findings; add `positive_checks` block to report dict |
| `skills/russellian-style/references/russellian-style-guide.md` | modify | Reframe hedging stance; add anti-staccato + concession-turn sections |
| `skills/russellian-style/references/before-after-examples.md` | modify | Three new contrast pairs |
| `skills/russellian-style/tests/test_lint_ai_staccato.py` | create | Per-rule positive + negative fixture tests |
| `skills/russellian-style/tests/fixtures/ai_staccato/*.md` | create | Fixtures for each detection rule |
| `skills/russellian-style/tests/fixtures/before_after/bitcoin_staccato.md` | create | Bad 10-paragraph sample |
| `skills/russellian-style/tests/fixtures/before_after/bitcoin_russellian.md` | create | Good 10-paragraph sample |
| `skills/russellian-style/tests/test_bitcoin_samples.py` | create | Regression: bad sample fires; good sample is silent |
| `skills/russellian-style/tests/test_style_pass_report_vitality.py` | modify | Assert positive_checks block present |
| `skills/russellian-style/tests/test_anthropic_compliance.py` | modify | Assert rules.json carries `ai_staccato` entry |
| `docs/research/2026-05-14-russell-style-enhancement.md` | modify | Append anti-staccato fix section + sample link |

---

## Task 1: Add `ai_staccato` config entry to rules.json

**Files:**
- Modify: `skills/russellian-style/assets/russellian-rules.json`

- [ ] **Step 1: Write the failing test**

Open `skills/russellian-style/tests/test_anthropic_compliance.py` and add this test at the bottom:

```python
def test_rules_json_carries_ai_staccato_entry():
    import json
    from pathlib import Path
    rules_path = Path(__file__).resolve().parent.parent / "assets" / "russellian-rules.json"
    rules = json.loads(rules_path.read_text(encoding="utf-8"))
    assert "ai_staccato" in rules, "rules.json must declare the ai_staccato entry"
    cfg = rules["ai_staccato"]
    assert cfg["tier"] == "important"
    assert cfg["severity"] == "advisory"
    det = cfg["detection"]
    for key in (
        "staccato_run_min",
        "staccato_max_sentence_words",
        "staccato_max_sentences_per_paragraph",
        "negation_affirmation_min_paragraphs",
        "this_is_window",
        "this_is_min",
        "abstract_subject_min_run",
        "abstract_subject_stoplist",
    ):
        assert key in det, f"missing detection key: {key}"
    assert "system" in det["abstract_subject_stoplist"]
    assert "protocol" in det["abstract_subject_stoplist"]
```

- [ ] **Step 2: Run test to verify it fails**

```
cd skills/russellian-style
.venv/Scripts/python.exe -m pytest tests/test_anthropic_compliance.py::test_rules_json_carries_ai_staccato_entry -v
```

Expected: FAIL with `assert "ai_staccato" in rules`.

- [ ] **Step 3: Edit rules.json**

Add this entry at the top level of `skills/russellian-style/assets/russellian-rules.json`, before the closing `}`:

```json
,
  "ai_staccato": {
    "id": "ai_staccato",
    "tier": "important",
    "severity": "advisory",
    "detection": {
      "staccato_run_min": 3,
      "staccato_max_sentence_words": 12,
      "staccato_max_sentences_per_paragraph": 3,
      "negation_affirmation_min_paragraphs": 2,
      "this_is_window": 6,
      "this_is_min": 3,
      "abstract_subject_min_run": 4,
      "abstract_subject_stoplist": [
        "system", "protocol", "ledger", "truth", "freedom",
        "pipeline", "result", "process", "thing", "framework",
        "approach", "principle"
      ]
    }
  }
```

(Insert a leading comma after the last existing entry; the rest of the file is unchanged.)

- [ ] **Step 4: Run test to verify it passes**

```
.venv/Scripts/python.exe -m pytest tests/test_anthropic_compliance.py::test_rules_json_carries_ai_staccato_entry -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/russellian-style/assets/russellian-rules.json skills/russellian-style/tests/test_anthropic_compliance.py
git commit -m "russellian-style: add ai_staccato config entry to rules.json"
```

---

## Task 2: `lint_ai_staccato` skeleton + `staccato-paragraph-run` rule

**Files:**
- Create: `skills/russellian-style/scripts/lint_ai_staccato.py`
- Create: `skills/russellian-style/tests/test_lint_ai_staccato.py`
- Create: `skills/russellian-style/tests/fixtures/ai_staccato/staccato_run.md`
- Create: `skills/russellian-style/tests/fixtures/ai_staccato/staccato_run_clean.md`

- [ ] **Step 1: Write the failing test**

Create `skills/russellian-style/tests/test_lint_ai_staccato.py`:

```python
"""lint_ai_staccato: cross-paragraph staccato detection."""
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "ai_staccato"


def test_staccato_paragraph_run_fires():
    from scripts.lint_ai_staccato import lint_ai_staccato
    findings = lint_ai_staccato(FIXTURES / "staccato_run.md")
    runs = [f for f in findings if f["rule"] == "staccato-paragraph-run"]
    assert runs, "expected staccato-paragraph-run to fire"
    f = runs[0]
    assert f["tier"] == "important"
    assert f["severity"] == "advisory"
    assert f["run_length"] >= 3


def test_staccato_paragraph_run_silent_on_varied_prose():
    from scripts.lint_ai_staccato import lint_ai_staccato
    findings = lint_ai_staccato(FIXTURES / "staccato_run_clean.md")
    runs = [f for f in findings if f["rule"] == "staccato-paragraph-run"]
    assert runs == []
```

- [ ] **Step 2: Create fixtures**

Create `skills/russellian-style/tests/fixtures/ai_staccato/staccato_run.md`:

```markdown
The ledger records claims. It tracks every change.

The graph holds relations. It projects them from claims.

The validator checks shapes. It rejects malformed input.

The report names defects. It links each one to a source.
```

Create `skills/russellian-style/tests/fixtures/ai_staccato/staccato_run_clean.md`:

```markdown
The ledger records claims, but the act of recording is more than a list — every entry brings a date, a source, and a state.

A graph projects relations from those claims, and the projection is where contradictions surface that the prose would otherwise hide.

When the validator runs, it does not merely flag malformed input; it points at the field that failed, the SHACL constraint that named the failure, and the offending line.

The report ties each defect to its source span. A reader can trace a single false claim from the chapter back through the graph to the original paragraph in the source PDF.
```

- [ ] **Step 3: Run test to verify it fails**

```
.venv/Scripts/python.exe -m pytest tests/test_lint_ai_staccato.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.lint_ai_staccato'`.

- [ ] **Step 4: Implement the linter skeleton + first rule**

Create `skills/russellian-style/scripts/lint_ai_staccato.py`:

```python
"""AI-staccato linter.

Detects four cross-paragraph patterns the existing eleven linters miss:
  - staccato-paragraph-run    : runs of short, few-sentence paragraphs
  - negation-affirmation-template : "X is not Y. X is Z." across paragraphs
  - this-is-conclusion-overuse    : repeated "This is ..." conclusions
  - abstract-subject-run          : same abstract noun heading many sentences

All findings emit at advisory severity, important tier; the linter never
gates a build by itself. Promotion to gating is deferred to a follow-up
calibration spec.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .lint_common import load_markdown, load_rules


def _paragraphs(text: str) -> list[tuple[int, str]]:
    """Return (start_line_1indexed, paragraph_text) pairs, skipping code and headings."""
    out: list[tuple[int, str]] = []
    lines = text.splitlines()
    current: list[str] = []
    current_start = 1
    in_fence = False
    for idx, raw in enumerate(lines, start=1):
        if raw.lstrip().startswith("```"):
            in_fence = not in_fence
            if current:
                out.append((current_start, "\n".join(current)))
                current = []
            current_start = idx + 1
            continue
        if in_fence:
            continue
        if raw.strip() == "":
            if current:
                out.append((current_start, "\n".join(current)))
                current = []
            current_start = idx + 1
        else:
            if raw.lstrip().startswith("#"):
                if current:
                    out.append((current_start, "\n".join(current)))
                    current = []
                current_start = idx + 1
                continue
            if not current:
                current_start = idx
            current.append(raw)
    if current:
        out.append((current_start, "\n".join(current)))
    return out


def _sentences(para: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", para.strip()) if s.strip()]


def _staccato_paragraph_run(paragraphs: list[tuple[int, str]], cfg: dict) -> list[dict]:
    """Flag runs of N+ consecutive short-sentence paragraphs."""
    min_run = cfg["staccato_run_min"]
    max_words = cfg["staccato_max_sentence_words"]
    max_sents = cfg["staccato_max_sentences_per_paragraph"]
    findings: list[dict] = []
    run_start: int | None = None
    run_length = 0
    run_start_line = 0
    for start_line, text in paragraphs:
        sents = _sentences(text)
        is_staccato = (
            2 <= len(sents) <= max_sents
            and all(len(s.split()) <= max_words for s in sents)
        )
        if is_staccato:
            if run_start is None:
                run_start = start_line
                run_start_line = start_line
                run_length = 1
            else:
                run_length += 1
        else:
            if run_start is not None and run_length >= min_run:
                findings.append({
                    "rule": "staccato-paragraph-run",
                    "tier": "important",
                    "severity": "advisory",
                    "line": run_start_line,
                    "run_length": run_length,
                    "message": (
                        f"{run_length} consecutive paragraphs of 2-3 short sentences "
                        f"(<= {max_words} words each). Break the rhythm with a longer "
                        "concession or example paragraph."
                    ),
                })
            run_start = None
            run_length = 0
    if run_start is not None and run_length >= min_run:
        findings.append({
            "rule": "staccato-paragraph-run",
            "tier": "important",
            "severity": "advisory",
            "line": run_start_line,
            "run_length": run_length,
            "message": (
                f"{run_length} consecutive paragraphs of 2-3 short sentences "
                f"(<= {max_words} words each). Break the rhythm with a longer "
                "concession or example paragraph."
            ),
        })
    return findings


def lint_ai_staccato(path: Path) -> list[dict]:
    text = load_markdown(path)
    paras = _paragraphs(text)
    cfg = load_rules()["ai_staccato"]["detection"]
    findings: list[dict] = []
    findings.extend(_staccato_paragraph_run(paras, cfg))
    return findings


if __name__ == "__main__":
    import sys
    print(json.dumps(lint_ai_staccato(Path(sys.argv[1])), indent=2))
```

- [ ] **Step 5: Run test to verify it passes**

```
.venv/Scripts/python.exe -m pytest tests/test_lint_ai_staccato.py -v
```

Expected: PASS — both `test_staccato_paragraph_run_fires` and `test_staccato_paragraph_run_silent_on_varied_prose`.

- [ ] **Step 6: Commit**

```bash
git add skills/russellian-style/scripts/lint_ai_staccato.py \
        skills/russellian-style/tests/test_lint_ai_staccato.py \
        skills/russellian-style/tests/fixtures/ai_staccato/staccato_run.md \
        skills/russellian-style/tests/fixtures/ai_staccato/staccato_run_clean.md
git commit -m "russellian-style: lint_ai_staccato skeleton + staccato-paragraph-run rule"
```

---

## Task 3: `negation-affirmation-template` rule

**Files:**
- Modify: `skills/russellian-style/scripts/lint_ai_staccato.py`
- Modify: `skills/russellian-style/tests/test_lint_ai_staccato.py`
- Create: `skills/russellian-style/tests/fixtures/ai_staccato/negation_affirmation.md`
- Create: `skills/russellian-style/tests/fixtures/ai_staccato/negation_affirmation_clean.md`

- [ ] **Step 1: Write the failing test**

Append to `skills/russellian-style/tests/test_lint_ai_staccato.py`:

```python
def test_negation_affirmation_template_fires():
    from scripts.lint_ai_staccato import lint_ai_staccato
    findings = lint_ai_staccato(FIXTURES / "negation_affirmation.md")
    hits = [f for f in findings if f["rule"] == "negation-affirmation-template"]
    assert hits, "expected negation-affirmation-template to fire"
    assert hits[0]["match_count"] >= 2


def test_negation_affirmation_template_silent_on_clean():
    from scripts.lint_ai_staccato import lint_ai_staccato
    findings = lint_ai_staccato(FIXTURES / "negation_affirmation_clean.md")
    hits = [f for f in findings if f["rule"] == "negation-affirmation-template"]
    assert hits == []
```

- [ ] **Step 2: Create fixtures**

`skills/russellian-style/tests/fixtures/ai_staccato/negation_affirmation.md`:

```markdown
The cost is not borne by the firm. It is borne by the worker.

The system is not failing slowly. It is failing all at once.

A regulator is not a friend of the public. It is a friend of the regulated.
```

`skills/russellian-style/tests/fixtures/ai_staccato/negation_affirmation_clean.md`:

```markdown
The cost falls on the worker, and the firm collects the rest. To call this an oversight is too generous.

The system fails, and the failure shows itself in patches: a queue that grows, a refund that does not arrive, a complaint that no one will read.

A regulator may begin in good faith, but the work itself — meetings with the regulated, dinners, second careers — turns the office over. Friendship outlasts the term.
```

- [ ] **Step 3: Run test to verify it fails**

```
.venv/Scripts/python.exe -m pytest tests/test_lint_ai_staccato.py::test_negation_affirmation_template_fires -v
```

Expected: FAIL — the rule does not yet exist.

- [ ] **Step 4: Implement the rule**

Append to `skills/russellian-style/scripts/lint_ai_staccato.py` (before the bottom `if __name__` block):

```python
_NEG_AFFIRM_RE = re.compile(
    r"\b(\w[\w\s'’-]{0,40}?)\s+(?:is|are|was|were)\s+not\s+[^.!?]+?[.!?]\s+"
    r"(?:\1|It|It is|These|They|Those|This)\s+(?:is|are|was|were)\s+",
    re.IGNORECASE,
)


def _negation_affirmation_template(paragraphs: list[tuple[int, str]], cfg: dict) -> list[dict]:
    """Flag the 'X is not Y. X is Z.' (or variants) template across paragraphs."""
    min_paras = cfg["negation_affirmation_min_paragraphs"]
    hits: list[int] = []
    for start_line, text in paragraphs:
        if _NEG_AFFIRM_RE.search(text):
            hits.append(start_line)
    if len(hits) < min_paras:
        return []
    return [{
        "rule": "negation-affirmation-template",
        "tier": "important",
        "severity": "advisory",
        "line": hits[0],
        "match_count": len(hits),
        "match_lines": hits,
        "message": (
            f"'X is not Y. X is Z.' template matches across {len(hits)} paragraphs. "
            "Vary the rhetorical shape — try a concession, a distinction, or a "
            "consequence-carrying turn."
        ),
    }]
```

Then update `lint_ai_staccato` to call the new rule:

```python
def lint_ai_staccato(path: Path) -> list[dict]:
    text = load_markdown(path)
    paras = _paragraphs(text)
    cfg = load_rules()["ai_staccato"]["detection"]
    findings: list[dict] = []
    findings.extend(_staccato_paragraph_run(paras, cfg))
    findings.extend(_negation_affirmation_template(paras, cfg))
    return findings
```

- [ ] **Step 5: Run test to verify it passes**

```
.venv/Scripts/python.exe -m pytest tests/test_lint_ai_staccato.py -v
```

Expected: PASS — all four tests so far.

- [ ] **Step 6: Commit**

```bash
git add skills/russellian-style/scripts/lint_ai_staccato.py \
        skills/russellian-style/tests/test_lint_ai_staccato.py \
        skills/russellian-style/tests/fixtures/ai_staccato/negation_affirmation.md \
        skills/russellian-style/tests/fixtures/ai_staccato/negation_affirmation_clean.md
git commit -m "russellian-style: ai_staccato negation-affirmation-template rule"
```

---

## Task 4: `this-is-conclusion-overuse` rule

**Files:**
- Modify: `skills/russellian-style/scripts/lint_ai_staccato.py`
- Modify: `skills/russellian-style/tests/test_lint_ai_staccato.py`
- Create: `skills/russellian-style/tests/fixtures/ai_staccato/this_is_stacking.md`
- Create: `skills/russellian-style/tests/fixtures/ai_staccato/this_is_stacking_clean.md`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_lint_ai_staccato.py`:

```python
def test_this_is_conclusion_overuse_fires():
    from scripts.lint_ai_staccato import lint_ai_staccato
    findings = lint_ai_staccato(FIXTURES / "this_is_stacking.md")
    hits = [f for f in findings if f["rule"] == "this-is-conclusion-overuse"]
    assert hits, "expected this-is-conclusion-overuse to fire"
    assert hits[0]["match_count"] >= 3


def test_this_is_conclusion_overuse_silent_on_clean():
    from scripts.lint_ai_staccato import lint_ai_staccato
    findings = lint_ai_staccato(FIXTURES / "this_is_stacking_clean.md")
    hits = [f for f in findings if f["rule"] == "this-is-conclusion-overuse"]
    assert hits == []
```

- [ ] **Step 2: Create fixtures**

`tests/fixtures/ai_staccato/this_is_stacking.md`:

```markdown
Speculators bought the asset hoping the price would climb. This is not investment in any sober sense.

Many buyers had no use for the asset beyond its resale. This is a market for hope, not value.

The protocol does not endorse this behaviour. It is a system, not a sermon.

Holders complained when the price fell. This is the predictable end of every speculative wave.
```

`tests/fixtures/ai_staccato/this_is_stacking_clean.md`:

```markdown
Speculators bought the asset hoping the price would climb. Their hope was not investment in any sober sense, but a wager on the next buyer's optimism.

Many buyers had no use for the asset beyond resale. The market they joined was one of hope rather than value, and the distinction matters because hope is a poor anchor for a long-term holding.

The protocol does not endorse this behaviour, nor does it forbid it. A protocol is a set of rules, not a sermon, and the rules say nothing about the wisdom of those who follow them.

When the price fell, the holders complained — predictably, and at the worst possible time for their resale plans. Every speculative wave ends this way, and the explanation is older than markets.
```

- [ ] **Step 3: Run test to verify it fails**

```
.venv/Scripts/python.exe -m pytest tests/test_lint_ai_staccato.py::test_this_is_conclusion_overuse_fires -v
```

Expected: FAIL.

- [ ] **Step 4: Implement the rule**

Append to `scripts/lint_ai_staccato.py`:

```python
_THIS_IS_RE = re.compile(r"^\s*(?:This|It|These|Those)\s+(?:is|are|was|were)\b", re.IGNORECASE)


def _this_is_conclusion_overuse(paragraphs: list[tuple[int, str]], cfg: dict) -> list[dict]:
    """Flag windows where many paragraphs end on a 'This is ...' / 'It is ...' sentence."""
    window = cfg["this_is_window"]
    min_hits = cfg["this_is_min"]
    matches: list[int] = []
    for start_line, text in paragraphs:
        sents = _sentences(text)
        if not sents:
            continue
        last = sents[-1]
        if _THIS_IS_RE.match(last):
            matches.append(start_line)
    if not matches:
        return []
    findings: list[dict] = []
    seen_window = False
    for i in range(len(matches)):
        # Count matches whose paragraph indices fall within `window` paragraphs.
        run = [m for m in matches[i:] if _paragraph_distance(matches[i], m, paragraphs) < window]
        if len(run) >= min_hits and not seen_window:
            findings.append({
                "rule": "this-is-conclusion-overuse",
                "tier": "important",
                "severity": "advisory",
                "line": run[0],
                "match_count": len(run),
                "match_lines": run,
                "message": (
                    f"{len(run)} paragraphs in a {window}-paragraph window end "
                    "on a 'This is …' / 'It is …' conclusion. Replace with a "
                    "consequence-carrying sentence."
                ),
            })
            seen_window = True
            break
    return findings


def _paragraph_distance(line_a: int, line_b: int, paragraphs: list[tuple[int, str]]) -> int:
    """Number of paragraphs between two paragraphs identified by their start lines."""
    idx_a = next((i for i, (l, _) in enumerate(paragraphs) if l == line_a), -1)
    idx_b = next((i for i, (l, _) in enumerate(paragraphs) if l == line_b), -1)
    if idx_a < 0 or idx_b < 0:
        return 99999
    return abs(idx_b - idx_a)
```

Update `lint_ai_staccato` to call the new rule:

```python
def lint_ai_staccato(path: Path) -> list[dict]:
    text = load_markdown(path)
    paras = _paragraphs(text)
    cfg = load_rules()["ai_staccato"]["detection"]
    findings: list[dict] = []
    findings.extend(_staccato_paragraph_run(paras, cfg))
    findings.extend(_negation_affirmation_template(paras, cfg))
    findings.extend(_this_is_conclusion_overuse(paras, cfg))
    return findings
```

- [ ] **Step 5: Run test to verify it passes**

```
.venv/Scripts/python.exe -m pytest tests/test_lint_ai_staccato.py -v
```

Expected: PASS — six tests.

- [ ] **Step 6: Commit**

```bash
git add skills/russellian-style/scripts/lint_ai_staccato.py \
        skills/russellian-style/tests/test_lint_ai_staccato.py \
        skills/russellian-style/tests/fixtures/ai_staccato/this_is_stacking.md \
        skills/russellian-style/tests/fixtures/ai_staccato/this_is_stacking_clean.md
git commit -m "russellian-style: ai_staccato this-is-conclusion-overuse rule"
```

---

## Task 5: `abstract-subject-run` rule

**Files:**
- Modify: `skills/russellian-style/scripts/lint_ai_staccato.py`
- Modify: `skills/russellian-style/tests/test_lint_ai_staccato.py`
- Create: `skills/russellian-style/tests/fixtures/ai_staccato/abstract_subject_run.md`
- Create: `skills/russellian-style/tests/fixtures/ai_staccato/abstract_subject_run_clean.md`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_lint_ai_staccato.py`:

```python
def test_abstract_subject_run_fires():
    from scripts.lint_ai_staccato import lint_ai_staccato
    findings = lint_ai_staccato(FIXTURES / "abstract_subject_run.md")
    hits = [f for f in findings if f["rule"] == "abstract-subject-run"]
    assert hits, "expected abstract-subject-run to fire"
    assert hits[0]["subject"] in {"system", "protocol", "ledger"}
    assert hits[0]["run_length"] >= 4


def test_abstract_subject_run_silent_on_varied_subjects():
    from scripts.lint_ai_staccato import lint_ai_staccato
    findings = lint_ai_staccato(FIXTURES / "abstract_subject_run_clean.md")
    hits = [f for f in findings if f["rule"] == "abstract-subject-run"]
    assert hits == []
```

- [ ] **Step 2: Create fixtures**

`tests/fixtures/ai_staccato/abstract_subject_run.md`:

```markdown
The system records claims as data. The system projects those claims onto a graph. The system validates the graph against a SHACL shape. The system blocks the release when validation fails.
```

`tests/fixtures/ai_staccato/abstract_subject_run_clean.md`:

```markdown
The author records claims as data; the system she works through projects each one onto a graph. A validator runs the SHACL pass, and the censor blocks the release if a constraint fails. The reader benefits because the chapter cannot ship with a quietly broken citation.
```

- [ ] **Step 3: Run test to verify it fails**

```
.venv/Scripts/python.exe -m pytest tests/test_lint_ai_staccato.py::test_abstract_subject_run_fires -v
```

Expected: FAIL.

- [ ] **Step 4: Implement the rule**

Append to `scripts/lint_ai_staccato.py`. The rule uses spaCy's parser to identify the `nsubj` of each sentence:

```python
from functools import lru_cache


@lru_cache(maxsize=1)
def _nlp_parser():
    import spacy
    return spacy.load("en_core_web_sm", disable=["ner", "lemmatizer"])


def _subject_lemma(sentence_doc) -> str | None:
    for token in sentence_doc:
        if token.dep_ == "nsubj":
            return token.lower_
    return None


def _abstract_subject_run(paragraphs: list[tuple[int, str]], cfg: dict) -> list[dict]:
    """Flag runs of N+ consecutive sentences whose nsubj is the same stoplist noun."""
    stoplist = {w.lower() for w in cfg["abstract_subject_stoplist"]}
    min_run = cfg["abstract_subject_min_run"]
    nlp = _nlp_parser()
    findings: list[dict] = []
    for start_line, text in paragraphs:
        doc = nlp(text)
        sents = list(doc.sents)
        if len(sents) < min_run:
            continue
        run_subj: str | None = None
        run_len = 0
        run_start_idx = 0
        for idx, sent in enumerate(sents):
            subj = _subject_lemma(sent)
            if subj is not None and subj in stoplist:
                if subj == run_subj:
                    run_len += 1
                else:
                    if run_subj is not None and run_len >= min_run:
                        findings.append(_abstract_run_finding(
                            run_subj, run_len, start_line, sents[run_start_idx]
                        ))
                    run_subj = subj
                    run_len = 1
                    run_start_idx = idx
            else:
                if run_subj is not None and run_len >= min_run:
                    findings.append(_abstract_run_finding(
                        run_subj, run_len, start_line, sents[run_start_idx]
                    ))
                run_subj = None
                run_len = 0
        if run_subj is not None and run_len >= min_run:
            findings.append(_abstract_run_finding(
                run_subj, run_len, start_line, sents[run_start_idx]
            ))
    return findings


def _abstract_run_finding(subject: str, run_length: int, para_start_line: int, first_sent) -> dict:
    return {
        "rule": "abstract-subject-run",
        "tier": "important",
        "severity": "advisory",
        "line": para_start_line,
        "subject": subject,
        "run_length": run_length,
        "message": (
            f"{run_length} consecutive sentences share the same abstract subject "
            f"'{subject}'. Vary the agent — particular subjects (an author, a censor, "
            "the worker, the philosopher) keep prose alive."
        ),
    }
```

Update `lint_ai_staccato`:

```python
def lint_ai_staccato(path: Path) -> list[dict]:
    text = load_markdown(path)
    paras = _paragraphs(text)
    cfg = load_rules()["ai_staccato"]["detection"]
    findings: list[dict] = []
    findings.extend(_staccato_paragraph_run(paras, cfg))
    findings.extend(_negation_affirmation_template(paras, cfg))
    findings.extend(_this_is_conclusion_overuse(paras, cfg))
    findings.extend(_abstract_subject_run(paras, cfg))
    return findings
```

- [ ] **Step 5: Run test to verify it passes**

```
.venv/Scripts/python.exe -m pytest tests/test_lint_ai_staccato.py -v
```

Expected: PASS — eight tests.

- [ ] **Step 6: Commit**

```bash
git add skills/russellian-style/scripts/lint_ai_staccato.py \
        skills/russellian-style/tests/test_lint_ai_staccato.py \
        skills/russellian-style/tests/fixtures/ai_staccato/abstract_subject_run.md \
        skills/russellian-style/tests/fixtures/ai_staccato/abstract_subject_run_clean.md
git commit -m "russellian-style: ai_staccato abstract-subject-run rule"
```

---

## Task 6: `style_pass_report` integration + positive_checks block

**Files:**
- Modify: `skills/russellian-style/scripts/style_pass_report.py`
- Modify: `skills/russellian-style/tests/test_style_pass_report_vitality.py`

- [ ] **Step 1: Write the failing test**

Open `tests/test_style_pass_report_vitality.py` and append:

```python
def test_report_dict_has_positive_checks_block(tmp_path):
    from scripts.style_pass_report import generate_report_dict
    sample = tmp_path / "draft.md"
    sample.write_text(
        "The ledger records claims, but the act of recording is more than a list — every "
        "entry carries a date, a source, and a state.\n\n"
        "A graph projects relations from those claims, and the projection is where "
        "contradictions surface that the prose would otherwise hide.\n",
        encoding="utf-8",
    )
    report = generate_report_dict(sample)
    assert "positive_checks" in report
    pc = report["positive_checks"]
    for key in (
        "sentence_length_fano",
        "paragraph_shape_diversity",
        "concession_turn_count",
        "concrete_instance_count",
        "template_repetition_rate",
    ):
        assert key in pc, f"missing positive check: {key}"
    assert pc["concession_turn_count"] >= 1


def test_report_dict_includes_ai_staccato_findings(tmp_path):
    from scripts.style_pass_report import generate_report_dict
    sample = tmp_path / "staccato.md"
    sample.write_text(
        "The ledger records claims. It tracks every change.\n\n"
        "The graph holds relations. It projects them from claims.\n\n"
        "The validator checks shapes. It rejects malformed input.\n\n"
        "The report names defects. It links each one to a source.\n",
        encoding="utf-8",
    )
    report = generate_report_dict(sample)
    finds = [f for f in report["findings"]
             if f.get("finding", {}).get("rule") == "staccato-paragraph-run"]
    assert finds, "expected ai_staccato findings to appear in report dict"
```

- [ ] **Step 2: Run test to verify it fails**

```
.venv/Scripts/python.exe -m pytest tests/test_style_pass_report_vitality.py::test_report_dict_has_positive_checks_block -v
```

Expected: FAIL — `positive_checks` not in report.

- [ ] **Step 3: Modify `style_pass_report.py`**

Add the import at the top of the file with the other linter imports:

```python
from .lint_ai_staccato import lint_ai_staccato
```

Add the concession-turn regex constant near the top of the file (after the imports, before functions):

```python
_CONCESSION_TURN_RE = re.compile(
    r"\b(But|However|Yet|Still|Nevertheless|Even so|It is true that)\b",
)
```

Add `import re` to the top of the file if absent.

Define the new helpers below `_passive_voice_ratio`:

```python
def _sentence_length_fano(path: Path) -> float:
    from statistics import mean, pvariance
    text = load_markdown(path)
    lengths = [len(s.text.split()) for s in iter_sentences(text)]
    if len(lengths) < 2:
        return 0.0
    mu = mean(lengths)
    if mu == 0:
        return 0.0
    return round(pvariance(lengths) / mu, 3)


def _paragraph_shape_diversity(motion_findings: list[dict], paragraphs_in_text: int) -> float:
    """Shannon entropy of the paragraph_motion shape distribution, normalised by log(n_shapes)."""
    import math
    from .lint_paragraph_motion import SHAPES, classify_paragraph
    # If motion didn't return a finding, the rubric was still computed for our purposes.
    # Re-run classification: paragraph_motion only returns when flat > 0.7.
    return 0.0  # populated by _positive_checks via direct rubric


def _positive_checks(source_path: Path, motion_finds: list[dict], concrete_finds: list[dict],
                     staccato_finds: list[dict]) -> dict:
    import math
    from .lint_paragraph_motion import classify_paragraph
    text = load_markdown(source_path)
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    shapes = [classify_paragraph(p) for p in paras] if paras else []
    if shapes:
        counts: dict[str, int] = {}
        for s in shapes:
            counts[s] = counts.get(s, 0) + 1
        total = len(shapes)
        entropy = 0.0
        for k in counts.values():
            p = k / total
            entropy -= p * math.log2(p)
        max_entropy = math.log2(len(counts)) if len(counts) > 1 else 1.0
        diversity = round(entropy / max_entropy, 3) if max_entropy > 0 else 0.0
    else:
        diversity = 0.0
    concession = sum(len(_CONCESSION_TURN_RE.findall(p)) for p in paras)
    rep_rate = 0.0
    para_count = max(len(paras), 1)
    for f in staccato_finds:
        if f.get("rule") == "negation-affirmation-template":
            rep_rate = round(f.get("match_count", 0) / para_count, 3)
            break
    return {
        "sentence_length_fano": _sentence_length_fano(source_path),
        "paragraph_shape_diversity": diversity,
        "concession_turn_count": concession,
        "concrete_instance_count": _concrete_instance_count(text),
        "template_repetition_rate": rep_rate,
    }


def _concrete_instance_count(text: str) -> int:
    """Reuse the concrete-instance-density NER pass for an absolute count."""
    from .lint_common import _nlp_sentencizer  # type: ignore[attr-defined]
    nlp = _nlp_sentencizer()
    doc = nlp(text)
    return sum(1 for ent in doc.ents if ent.label_ in {"PERSON", "ORG", "GPE", "DATE", "MONEY", "ORDINAL"})
```

Inside `generate_report_dict`, replace the existing `findings` aggregation with one that also includes the staccato lint, and add `positive_checks` to the returned dict.

Find the block:

```python
    for f in burst + ai_vocab + concrete + episteme + motion:
        findings.append({"section": "vitality", "finding": f})
```

Replace with:

```python
    staccato = lint_ai_staccato(source_path)
    for f in burst + ai_vocab + concrete + episteme + motion + staccato:
        findings.append({"section": "vitality", "finding": f})
```

And in the return dict, add the `positive_checks` key:

```python
    return {
        "path": str(source_path),
        "negative_metrics": negative_metrics,
        "vitality_metrics": vitality_metrics,
        "positive_checks": _positive_checks(source_path, motion, concrete, staccato),
        "findings": findings,
        "corpus_anchors": corpus_anchors,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```
.venv/Scripts/python.exe -m pytest tests/test_style_pass_report_vitality.py -v
.venv/Scripts/python.exe -m pytest tests/test_style_pass_report.py -v
```

Expected: PASS for both new tests, plus all existing report tests still pass (no regression).

- [ ] **Step 5: Commit**

```bash
git add skills/russellian-style/scripts/style_pass_report.py \
        skills/russellian-style/tests/test_style_pass_report_vitality.py
git commit -m "russellian-style: style_pass_report aggregates ai_staccato + positive_checks block"
```

---

## Task 7: Revise `russellian-style-guide.md`

**Files:**
- Modify: `skills/russellian-style/references/russellian-style-guide.md`

- [ ] **Step 1: Reframe the hedging section**

Open `skills/russellian-style/references/russellian-style-guide.md`. Locate the heading or paragraph that says `no hedging`. Reframe it as `no vague hedging; exact uncertainty permitted`. Add this paragraph immediately after the reframed section:

```markdown
The skill does not forbid uncertainty. It forbids the *vague* uncertainty
that hides the limits of a claim. "It seems to me that …" is vague.
"On the evidence so far, X holds; the cases of Y are unresolved." is
exact uncertainty and is welcome.
```

- [ ] **Step 2: Add the "Anti-staccato" section**

Append this section near the end of the file (before any final references / see-also block):

```markdown
## Anti-staccato

Mechanical clarity passes the negative linters and still produces
prose that reads as a wall of compact assertions. The trap is most
visible in the negation-affirmation template:

**Bad** — passes all six negative linters; fails
`staccato-paragraph-run` and `this-is-conclusion-overuse`:

> Speculation has obscured the philosophy. Many men bought Bitcoin not
> because they desired sound money, but because they desired more
> dollars. This is not a contradiction in the protocol. It is a
> contradiction in the buyer.

**Good** — passes both:

> Those who call Bitcoin a mere speculation have seized upon a real
> defect and mistaken it for the whole subject. It is true that many
> men bought it in the hope of selling it to a more excited neighbour.
> But this tells us more about men than about the protocol. A system
> may be philosophically interesting even when most of its admirers
> understand it badly.

The good version keeps every clarity gain — no hedge, active voice,
modest modifier load — and adds the moves the bad version lacks:
concession ("real defect"), distinction (men vs. protocol), and a
sentence that turns the argument rather than concluding it.
```

- [ ] **Step 3: Add the "Concession-turn structure" section**

Append after the Anti-staccato section:

```markdown
## Concession-turn structure

Russell's working unit is not the sentence but the move. The most
common move has four steps:

1. State the common view (often the reader's prejudice).
2. Grant the part of it that is true.
3. Draw the distinction the common view conceals.
4. State the consequence that follows from the distinction.

The four steps need not occupy four sentences. Two short ones can
carry the whole move if the concession and the distinction are
compressed.

Example:

> The defender of the official secret will say that disclosure aids
> the enemy. He is right when the secret is technical and the enemy
> is technical. He is wrong, and dangerously so, when the secret is
> embarrassing and the enemy is the voter.

Three sentences, four moves: common view (sentence 1), partial grant
(sentence 2), distinction (sentence 3), consequence (sentence 3's
second clause). The paragraph earns its last sentence.
```

- [ ] **Step 4: Commit**

```bash
git add skills/russellian-style/references/russellian-style-guide.md
git commit -m "russellian-style: reframe hedging; add anti-staccato + concession-turn sections"
```

---

## Task 8: Add three contrast pairs to `before-after-examples.md`

**Files:**
- Modify: `skills/russellian-style/references/before-after-examples.md`

- [ ] **Step 1: Append the three pairs**

Append to `skills/russellian-style/references/before-after-examples.md`:

```markdown
---

## Anti-staccato contrast pairs

### Pair 1 — Bitcoin staccato → Russellian

**Bad** (linter-clean; AI-staccato):

> Speculation has obscured the philosophy. Many men bought Bitcoin not
> because they desired sound money, but because they desired more
> dollars. This is not a contradiction in the protocol. It is a
> contradiction in the buyer.

**Good** (analytic with motion):

> Those who call Bitcoin a mere speculation have seized upon a real
> defect and mistaken it for the whole subject. It is true that many
> men bought it in the hope of selling it to a more excited neighbour.
> But this tells us more about men than about the protocol. A system
> may be philosophically interesting even when most of its admirers
> understand it badly.

What changed: concession ("real defect"); distinction (men vs.
protocol); turn ("A system may be …").

### Pair 2 — Abstract-noun-subject overuse → Particular agents

**Bad** (subject `system` heads four consecutive sentences):

> The system records claims as data. The system projects those claims
> onto a graph. The system validates the graph against a SHACL shape.
> The system blocks the release when validation fails.

**Good** (particular agents):

> The author records claims as data; the system she works through
> projects each one onto a graph. A validator runs the SHACL pass, and
> the censor — for that is what a SHACL gate is — blocks the release
> when a constraint fails. The reader benefits because the chapter
> cannot ship with a quietly broken citation.

What changed: particular subjects (the author, the validator, the
censor, the reader); cadence variety; one sentence carries a
parenthetical aside that an abstract-subject run cannot.

### Pair 3 — "This is …" stacking → Consequence-carrying turn

**Bad** (three paragraph-final "This is …" / "It is …" sentences):

> Speculators bought the asset hoping the price would climb. This is
> not investment in any sober sense.
>
> Many buyers had no use for the asset beyond resale. This is a market
> for hope, not value.
>
> The protocol does not endorse this behaviour. It is a system, not a
> sermon.

**Good** (consequences that earn their last sentence):

> Speculators bought the asset hoping the price would climb. Their
> hope was not investment in any sober sense, but a wager on the next
> buyer's optimism.
>
> Many buyers had no use for the asset beyond resale. The market they
> joined was one of hope rather than value, and the distinction
> matters because hope is a poor anchor for a long-term holding.
>
> The protocol does not endorse this behaviour, nor does it forbid
> it. A protocol is a set of rules, not a sermon, and the rules say
> nothing about the wisdom of those who follow them.

What changed: each paragraph ends on a consequence ("a wager on the
next buyer's optimism", "a poor anchor for a long-term holding",
"the rules say nothing about the wisdom of those who follow them")
rather than a "This is …" identity claim. The paragraphs now depend
on each other; reordering them would lose the build.
```

- [ ] **Step 2: Commit**

```bash
git add skills/russellian-style/references/before-after-examples.md
git commit -m "russellian-style: three anti-staccato contrast pairs in before-after-examples"
```

---

## Task 9: Bitcoin regression samples + regression test

**Files:**
- Create: `skills/russellian-style/tests/fixtures/before_after/bitcoin_staccato.md`
- Create: `skills/russellian-style/tests/fixtures/before_after/bitcoin_russellian.md`
- Create: `skills/russellian-style/tests/test_bitcoin_samples.py`

- [ ] **Step 1: Write the failing test**

Create `skills/russellian-style/tests/test_bitcoin_samples.py`:

```python
"""Regression: the bad Bitcoin sample fires the new lint; the good one is silent."""
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "before_after"


def test_bitcoin_staccato_fires_expected_rules():
    from scripts.lint_ai_staccato import lint_ai_staccato
    findings = lint_ai_staccato(FIXTURES / "bitcoin_staccato.md")
    rules = {f["rule"] for f in findings}
    assert "staccato-paragraph-run" in rules
    assert "negation-affirmation-template" in rules
    assert "this-is-conclusion-overuse" in rules


def test_bitcoin_russellian_silent_under_ai_staccato():
    from scripts.lint_ai_staccato import lint_ai_staccato
    findings = lint_ai_staccato(FIXTURES / "bitcoin_russellian.md")
    assert findings == [], f"expected no findings; got {findings}"


def test_bitcoin_russellian_silent_under_negative_linters():
    """Sanity check: the good sample passes all six negative linters too."""
    from scripts.lint_hedges import lint_hedges
    from scripts.lint_passive_voice import lint_passive_voice
    from scripts.lint_signal_density import lint_signal_density
    from scripts.lint_parallel_structure import lint_parallel_structure
    from scripts.lint_sentence_rhythm import lint_sentence_rhythm
    from scripts.lint_listicle_abstract import lint_listicle_abstract
    sample = FIXTURES / "bitcoin_russellian.md"
    findings = (
        lint_hedges(sample)
        + lint_passive_voice(sample)
        + lint_signal_density(sample)
        + lint_parallel_structure(sample)
        + lint_sentence_rhythm(sample)
        + lint_listicle_abstract(sample)
    )
    # The negative-linter suite is strict; the good sample is allowed at most
    # two findings (typically a passive flagged inside a quoted concession).
    assert len(findings) <= 2, f"too many negative findings: {findings}"
```

- [ ] **Step 2: Create the bad sample**

Create `skills/russellian-style/tests/fixtures/before_after/bitcoin_staccato.md`:

```markdown
Bitcoin emerged as a response to inflation. It promised a money outside the state's reach.

The protocol fixed a supply schedule. It made monetary policy a public number.

Critics called Bitcoin a bubble. They were right and wrong at once.

Speculation has obscured the philosophy. Many men bought Bitcoin because they desired more dollars. This is not a contradiction in the protocol. It is a contradiction in the buyer.

The protocol does not endorse speculation. It is a system, not a sermon.

Holders complained when the price fell. This is the predictable end of every speculative wave.

The ledger records each transaction. It cannot be amended.

The network confirms each block in turn. It does so without permission.

The miner takes the fee. It does so because the protocol pays it.

The user keeps the keys. It is the only condition of ownership.
```

- [ ] **Step 3: Create the good sample**

Create `skills/russellian-style/tests/fixtures/before_after/bitcoin_russellian.md`:

```markdown
Bitcoin came into the world as a response to inflation, which is to say as a response to a thousand small thefts by governments that wished to spend more than they collected. To call this a small response is to misread the scale of the original injury.

The protocol's supply schedule is a public number, and a public number is a kind of constitution. Where a central bank may revise its target by a vote of seven men, Bitcoin's schedule answers only to a fork — and a fork demands the open consent of those who follow the chain.

Critics call Bitcoin a bubble, and at the worst moments of its history they have been right. Yet the same critic who calls a thing a bubble in 2014 and again in 2018 and again in 2022 is no longer making a market diagnosis. He is making a habit.

Those who call Bitcoin a mere speculation have seized upon a real defect and mistaken it for the whole subject. It is true that many men bought it in the hope of selling it to a more excited neighbour. But this tells us more about men than about the protocol. A system may be philosophically interesting even when most of its admirers understand it badly.

The protocol's authors did not promise a moral economy. They promised an arithmetic one. The reader who arrives looking for a sermon will find only a difficulty-adjusted target, an open ledger, and a cryptographic signature scheme that does not care what the user spends his coins on.

A protocol of this kind has a peculiar relation to its users. It enforces no policy on them and depends on none of their virtues. The Athenian assembly demanded both arguments and good citizens; the Bitcoin network demands neither, asking only that the miner submit a block whose hash matches the threshold.

The ledger records every transaction, and once a transaction has six confirmations no central authority can take it back. A bank reconciles its books at night; the chain reconciles itself every ten minutes, and the reconciliation is the work that the network does instead of issuing orders.

This is not an argument that Bitcoin solves political problems. The ordinary tax inspector, the schoolteacher in Lagos, and the pensioner in Naples each have problems that no monetary protocol can reach. The argument is narrower: Bitcoin solves one part of one problem, and the part it solves is the part where the state has historically been the worst offender.

Holders complain when the price falls, and they are entitled to their disappointment. But a holder who treats price as truth has already conceded to the speculator's frame; the case for the protocol does not stand or fall on the next quarter's chart, any more than the case for double-entry bookkeeping stood or fell on Florentine wool prices in 1378.

The user keeps the keys, and the keys are the only condition of ownership the protocol recognises. A keyless owner is no owner. This places a burden on the user that no banking customer has carried in three centuries, and the burden is the cost of the freedom — a cost that some will gladly pay and that others, honestly examining their habits, would do better to refuse.
```

- [ ] **Step 4: Run tests to verify pass**

```
.venv/Scripts/python.exe -m pytest tests/test_bitcoin_samples.py -v
```

Expected: PASS — all three tests. If `test_bitcoin_russellian_silent_under_negative_linters` fails because the sample triggers some passive or hedge, tune the sample (the goal is human prose that passes the negative bar, not a regex submission).

- [ ] **Step 5: Commit**

```bash
git add skills/russellian-style/tests/fixtures/before_after/bitcoin_staccato.md \
        skills/russellian-style/tests/fixtures/before_after/bitcoin_russellian.md \
        skills/russellian-style/tests/test_bitcoin_samples.py
git commit -m "russellian-style: Bitcoin staccato vs Russellian regression fixtures"
```

---

## Task 10: Research-doc appendix

**Files:**
- Modify: `docs/research/2026-05-14-russell-style-enhancement.md`

- [ ] **Step 1: Append the dated section**

Append to `docs/research/2026-05-14-russell-style-enhancement.md`:

```markdown
---

## Anti-staccato fix (2026-05-14)

The vitality layer (Phase B, commit `a3cb36c`) shipped five advisory
linters: burstiness, ai-vocabulary, concrete-instance density,
epistemic precision, paragraph motion. Field testing against a fresh
Bitcoin prose attempt reproduced the original failure: the output
passed all six negative linters and most of the vitality block, yet
still read as a wall of compact assertion + compact justification
pairs. The vitality linters caught flat_proportion ≥ 0.93 on
paragraph motion — the signal was right, but the advisory severity and
the lack of named patterns gave the operator no concrete redirection.

The new `lint_ai_staccato` linter names four patterns the existing
suite missed:

1. **staccato-paragraph-run** — runs of three or more paragraphs
   whose sentences are all twelve words or fewer.
2. **negation-affirmation-template** — repeated `X is not Y. X is Z.`
   shapes across paragraphs.
3. **this-is-conclusion-overuse** — three or more paragraph-final
   sentences starting with `This is …` / `It is …` in a six-paragraph
   window.
4. **abstract-subject-run** — four or more consecutive sentences
   sharing the same abstract-noun grammatical subject from a short
   stoplist (`system`, `protocol`, `ledger`, `truth`, `freedom`, etc.).

`style_pass_report` now emits a positive-checks block alongside the
existing negative_metrics and vitality_metrics:
`sentence_length_fano`, `paragraph_shape_diversity`,
`concession_turn_count`, `concrete_instance_count`,
`template_repetition_rate`. All five are informational; no new gate.

### Bitcoin comparison

Two 10-paragraph samples land at
`skills/russellian-style/tests/fixtures/before_after/`:

- `bitcoin_staccato.md` — the failing pattern. Fires
  `staccato-paragraph-run` (≥ 1 run), `negation-affirmation-template`
  (≥ 2 hits), and `this-is-conclusion-overuse` (≥ 3 hits in window).
- `bitcoin_russellian.md` — the same factual content recast with
  concessions, distinctions, particular agents (the schoolteacher in
  Lagos, the pensioner in Naples, the Athenian assembly), and
  consequence-carrying paragraph ends. Silent under all four new
  rules and ≤ 2 findings under the six negative linters.

The paragraph-by-paragraph difference is mostly the four moves that
the negative linters cannot enforce: concession before judgement
(paragraphs 1, 3, 4), particular agents in place of `the system`
(paragraphs 5, 6, 8), consequences that earn the last sentence
(paragraphs 2, 4, 7, 9), and one paragraph (10) that does the rare
Russellian move of stating the cost a free choice imposes on the one
who makes it.

### Calibration note

The new linter is advisory in v1, matching the research-doc guidance
that gating should follow calibration against at least three corpus
sources and one real chapter. The Bitcoin good-sample is the seed
target. A future spec can promote `negation-affirmation-template` to
gating once it has been run against three corpus chapters without
false positives.
```

- [ ] **Step 2: Commit**

```bash
git add docs/research/2026-05-14-russell-style-enhancement.md
git commit -m "docs: research-doc appendix for anti-staccato fix"
```

---

## Final verification

- [ ] **Run the full skill test suite**

```
cd skills/russellian-style
.venv/Scripts/python.exe -m pytest tests/ -q
```

Expected: every test passes. No regressions in the existing eleven-linter suite or the report tests.

- [ ] **Smoke-test against the corpus map**

```
cd skills/russellian-style
.venv/Scripts/python.exe -m scripts.lint_ai_staccato references/russell-corpus-map.md
```

Expected: no findings (the corpus map is a metadata file, not prose).

- [ ] **Smoke-test against the bad Bitcoin sample**

```
.venv/Scripts/python.exe -m scripts.lint_ai_staccato tests/fixtures/before_after/bitcoin_staccato.md
```

Expected: JSON output naming `staccato-paragraph-run`,
`negation-affirmation-template`, and `this-is-conclusion-overuse`.

- [ ] **Smoke-test against the good Bitcoin sample**

```
.venv/Scripts/python.exe -m scripts.lint_ai_staccato tests/fixtures/before_after/bitcoin_russellian.md
```

Expected: `[]`.

- [ ] **Open the PR**

```bash
git push -u origin feat/russellian-anti-staccato
gh pr create --base main \
  --title "russellian-style: anti-staccato lint + positive-checks block" \
  --body "$(cat <<'EOF'
Adds the missing pattern detector the existing eleven linters cannot reach: a `lint_ai_staccato` linter with four rules (`staccato-paragraph-run`, `negation-affirmation-template`, `this-is-conclusion-overuse`, `abstract-subject-run`) plus a positive-checks block in `style_pass_report` covering cadence variety, paragraph-shape diversity, concession turns, concrete instances, and template repetition rate. All advisory; no new gate.

Two 10-paragraph Bitcoin fixtures (bad + good) at `tests/fixtures/before_after/` double as regression tests. The good sample reads as Russell; the bad sample reproduces the AI-staccato pattern verbatim.

Spec: `docs/specs/2026-05-14-russellian-anti-staccato-design.md`.

## Test plan
- [ ] `pytest tests/` under `skills/russellian-style/` passes
- [ ] `lint_ai_staccato` fires on the bad Bitcoin sample, silent on the good
- [ ] `style_pass_report.generate_report_dict` returns a `positive_checks` block
EOF
)"
```

---

## Self-review

**Spec coverage:**
- §1 New linter `lint_ai_staccato.py` with four rules → Tasks 2, 3, 4, 5 (one per rule). ✓
- §2 `style_pass_report` integration + positive_checks → Task 6. ✓
- §3 Style guide revisions → Task 7. ✓
- §4 Before/after examples → Task 8. ✓
- §5 Rules.json entry → Task 1. ✓
- §6 Tests → embedded throughout each task; final pass in Final Verification. ✓
- §7 Bitcoin samples + regression test → Task 9. ✓
- §8 Research-doc appendix → Task 10. ✓

**Placeholder scan:** No TBD, TODO, "implement later" markers. Every code step shows complete code. Every command is exact.

**Type consistency:** `lint_ai_staccato(path: Path) -> list[dict]` is consistent across tasks 2-5. The four rule helpers (`_staccato_paragraph_run`, `_negation_affirmation_template`, `_this_is_conclusion_overuse`, `_abstract_subject_run`) all take `(paragraphs, cfg)` and return `list[dict]` with the same shape. Findings carry `rule`, `tier`, `severity`, `line`, and rule-specific extras — consistent with the existing vitality linters.

**Cross-task dependencies:** Task 1 must land before Task 2 because the linter reads `rules.json`. Tasks 2-5 stack on each other within `lint_ai_staccato.py`. Task 6 depends on Task 2-5. Tasks 7-10 are independent of each other and can run in any order after Task 6.
