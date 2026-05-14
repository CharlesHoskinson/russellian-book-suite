# review-conductor and Expanded Personas Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add two new persona reviewers (AI-slop detector, first-time visitor) to `book-review`, then introduce a `review-conductor` sibling skill that orchestrates configurable panels with per-persona severity gates and few-shot Outcomes exemplars.

**Architecture:** PR-A extends `book-review` with the two new personas and a seeded Outcomes library at `references/outcomes/readme-pass-2026-05-13/`. PR-B introduces `skills/review-conductor/` as a thin orchestration sibling that reads a YAML panel config, calls `book-review.prepare_dispatch_packets` with the configured personas, applies a per-persona severity gate, and emits `panel-review.md` plus `verdict.json`. `book-compose` is switched in one line from `book-review.run_review_pass` to `review-conductor.run_panel`.

**Tech Stack:** Python 3.11+, PyYAML, jsonschema, pytest. Reuses `book-review`'s `persona_loader`, `dispatch_review`, and `aggregate_reviews` modules via the existing `sibling_skills.py` alias-namespace pattern.

---

## File Structure

### PR-A files

```
skills/book-review/
├── personas/
│   ├── ai-slop-detector.md             (CREATE)
│   └── first-time-visitor.md           (CREATE)
├── references/outcomes/
│   └── readme-pass-2026-05-13/
│       ├── README.md                   (CREATE)
│       ├── curation-notes.md           (CREATE)
│       ├── gottlieb.md                 (CREATE)
│       ├── lay-reader.md               (CREATE)
│       ├── domain-expert.md            (CREATE)
│       ├── copyeditor.md               (CREATE)
│       ├── enjoyment-reader.md         (CREATE)
│       ├── ai-slop-detector.md         (CREATE)
│       └── first-time-visitor.md       (CREATE)
└── tests/
    ├── test_persona_loader.py          (MODIFY — update `test_real_personas_load`)
    ├── test_outcomes_seed.py           (CREATE — verify seed exemplar shape)
    └── fixtures/outcomes/              (CREATE — empty-dir fixture for tests)
```

### PR-B files

```
skills/review-conductor/
├── SKILL.md                            (CREATE)
├── pyproject.toml                      (CREATE)
├── README.md                           (CREATE)
├── assets/
│   ├── panel-config.schema.json        (CREATE)
│   └── verdict.schema.json             (CREATE)
├── panels/
│   └── chapter-default.yaml            (CREATE)
├── scripts/
│   ├── __init__.py                     (CREATE)
│   ├── load_panel.py                   (CREATE)
│   ├── sibling_skills.py               (CREATE)
│   ├── outcomes_loader.py              (CREATE)
│   ├── dispatch_panel.py               (CREATE)
│   ├── aggregate_panel.py              (CREATE)
│   └── conductor.py                    (CREATE — public entrypoint `run_panel`)
└── tests/
    ├── __init__.py                     (CREATE)
    ├── conftest.py                     (CREATE)
    ├── fixtures/
    │   ├── panel-default.yaml          (CREATE)
    │   ├── panel-all-advisory.yaml     (CREATE)
    │   ├── synthetic_outcomes/         (CREATE — directory with sample exemplars)
    │   └── synthetic_reviews/          (CREATE — sample persona review markdown)
    ├── test_load_panel.py              (CREATE)
    ├── test_sibling_skills.py          (CREATE)
    ├── test_outcomes_loader.py         (CREATE)
    ├── test_dispatch_panel.py          (CREATE)
    ├── test_aggregate_panel.py         (CREATE)
    ├── test_conductor_integration.py   (CREATE)
    └── test_anthropic_compliance.py    (CREATE)

skills/book-compose/
├── scripts/persona_review_pass.py      (MODIFY — one-line swap to run_panel)
└── SKILL.md                            (MODIFY — Stage 7 description)
```

---

# Phase A — PR-A: personas + outcomes

## Task A1: Create branch off main

**Files:** none (git only)

- [ ] **Step 1: Switch to main and pull**

```bash
git checkout main
git pull --ff-only origin main
```

- [ ] **Step 2: Create branch**

```bash
git checkout -b personas/expand-book-review-panel
```

- [ ] **Step 3: Verify clean state**

```bash
git status
```

Expected: `On branch personas/expand-book-review-panel`, `nothing to commit, working tree clean`.

## Task A2: Add ai-slop-detector persona (TDD)

**Files:**
- Create: `skills/book-review/personas/ai-slop-detector.md`
- Test: `skills/book-review/tests/test_persona_loader.py`

- [ ] **Step 1: Write the failing test**

Append to `skills/book-review/tests/test_persona_loader.py`:

```python
def test_ai_slop_detector_persona_loads():
    """Ai-slop-detector persona is shipped in personas/."""
    from scripts.persona_loader import load_persona
    p = load_persona("ai-slop-detector")
    assert p.persona_id == "ai-slop-detector"
    assert p.display_name == "AI-Slop Detector"
    assert "humanizer" in p.body_md.lower()
    assert "Wikipedia" in p.body_md
    # severity rubric must be present
    assert "## Severity rubric" in p.body_md
    assert "Critical" in p.body_md
    assert "Important" in p.body_md
    assert "Minor" in p.body_md
```

- [ ] **Step 2: Run test, verify it fails**

```bash
cd skills/book-review
.venv/Scripts/python.exe -m pytest tests/test_persona_loader.py::test_ai_slop_detector_persona_loads -v
```

Expected: `FileNotFoundError: persona not found: ...personas/ai-slop-detector.md`.

- [ ] **Step 3: Create the persona file**

Create `skills/book-review/personas/ai-slop-detector.md` with this exact content:

```markdown
---
persona_id: ai-slop-detector
display_name: AI-Slop Detector
role: AI-fingerprint sweep
---

## Identity

You read in the persona of a forensic editor whose only job is to detect signs of AI-generated writing. You do not assess content, voice, or argument. You scan for the fingerprint.

The catalog you use is the one encoded in the `humanizer` skill, which in turn is drawn from Wikipedia's "Signs of AI writing" guide. Twenty-four distinct AI signatures, from excessive em-dashes to inflated symbolism, from vague attributions to the rule-of-three. The catalog is your only standard; the rubric below maps catalog patterns to severity.

You delegate to the `humanizer` skill for the catalog. The persona prompt embeds humanizer's checklist by reference. If you find a pattern that the catalog names, you flag it.

## Lens

You read for: AI-fingerprint patterns. You do not read primarily for facts (the Domain Expert handles that), accessibility (the Lay Reader handles that), cadence (the Copyeditor handles that), or pleasure (the Enjoyment Reader handles that). You read for whether the prose smells like a machine wrote it.

You have access to the `humanizer` skill in the same workspace. Consult it for the full catalog. Report findings in the structured output below.

## Severity rubric

### Critical (gating)

- **Inflated symbolism / promotional language.** "Comprehensive", "robust", "powerful", "transformative", "seamless", "best-in-class". Adjectives that argue rather than describe.
- **Listicle abstracts.** "Rests on N premises", "consists of N components", "follows three principles" — patterns where the prose should carry the structure instead of announcing it.
- **Superficial -ing analyses.** Strings of -ing verbs ("ensuring", "providing", "enabling", "leveraging", "facilitating") that flatten action into ambient process.
- **Mechanical thesis enumeration.** Three or more consecutive subject-verb-object sentences each naming a stage or component.

### Important

- AI vocabulary tells: "leverage", "navigate", "delve", "tapestry", "harness", "unlock", "in the realm of", "in today's world", "in an era where".
- Em-dash overuse: three or more em-dashes in a paragraph, used where a comma would do.
- Negative parallelism: "not just X but Y" or "more than just X". Twice is style; three times is a fingerprint.
- Filler phrases: "it is worth noting that", "it is important to remember that", "needless to say".
- Hedging chains: "may potentially", "can sometimes", "might possibly".
- Passive voice overuse where the actor is known.

### Minor

- Predictable transitions: "Furthermore", "Moreover", "In addition", "However" starting paragraphs more than twice in a section.
- Empty intensifiers: "very", "extremely", "highly", "particularly".

## Tone

Forensic. Specific. Brief. Quote the exact phrase, name the pattern from the catalog, suggest the cut. You do not lecture; you mark the fingerprint and move on. You do not perform expertise; you point to the catalog.

Always end your review with a one-word AI-fingerprint score (`low | moderate | high | severe`) plus a one-sentence justification.

## Example review

> ## Critical findings
> 1. **[Line 30, "Sentences cluster around eighteen words. Paragraphs deliver three points each."]:** Listicle abstract describing the very pattern. Three terse declaratives in series — itself rule-of-three. Fold into one sentence.
> 2. **[Line 275, "The six domains: 1. Writing mindset. 2. Structure and flow. ..."]:** Mechanical thesis enumeration disguised as section structure. The doctrine should be argued, not listed.
>
> ## Important findings
> - **[Line 269]:** "by construction" appears 3x in the document — verbal tic.
> - **[Multiple]:** Em-dash count > 1 per paragraph in lines 5, 30, 31, 233, 297, 437.
>
> ## Minor findings
> - **[Line 90]:** "Furthermore" starts two consecutive paragraphs.
>
> ## Score
> AI-fingerprint score: **moderate**. The text is technically dense and concrete, but its paragraph-openers default to terse-declarative triads and parallel subject-verb chains — the exact cadence the suite claims to lint against.
```

- [ ] **Step 4: Run test, verify it passes**

```bash
cd skills/book-review
.venv/Scripts/python.exe -m pytest tests/test_persona_loader.py::test_ai_slop_detector_persona_loads -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/book-review/personas/ai-slop-detector.md skills/book-review/tests/test_persona_loader.py
git commit -m "Add ai-slop-detector persona: humanizer-backed AI-fingerprint sweep"
```

## Task A3: Add first-time-visitor persona (TDD)

**Files:**
- Create: `skills/book-review/personas/first-time-visitor.md`
- Test: `skills/book-review/tests/test_persona_loader.py`

- [ ] **Step 1: Write the failing test**

Append to `skills/book-review/tests/test_persona_loader.py`:

```python
def test_first_time_visitor_persona_loads():
    """First-time-visitor persona is shipped in personas/."""
    from scripts.persona_loader import load_persona
    p = load_persona("first-time-visitor")
    assert p.persona_id == "first-time-visitor"
    assert p.display_name == "First-Time Visitor"
    assert "30 second" in p.body_md.lower() or "thirty second" in p.body_md.lower()
    assert "## Severity rubric" in p.body_md
    assert "timeline" in p.body_md.lower()
```

- [ ] **Step 2: Run test, verify it fails**

```bash
cd skills/book-review
.venv/Scripts/python.exe -m pytest tests/test_persona_loader.py::test_first_time_visitor_persona_loads -v
```

Expected: `FileNotFoundError`.

- [ ] **Step 3: Create the persona file**

Create `skills/book-review/personas/first-time-visitor.md` with this exact content:

```markdown
---
persona_id: first-time-visitor
display_name: First-Time Visitor
role: drive-by reader, 30-second comprehension test
---

## Identity

You read in the persona of a first-time visitor who arrived from a link in a tweet five minutes ago. You have thirty seconds before you decide whether to keep reading or close the tab.

You are technical — a software engineer, technical writer, or researcher — but not a specialist in this artifact's domain. You read READMEs all day. You have a low tolerance for jargon that arrives before the value proposition. You will give the first paragraph the benefit of the doubt; after that, you need a hook.

You evaluate one question above all: would I keep reading this if I were not paid to?

## Lens

You read for: the speed at which the artifact tells you what it is and why you might care. The presence of a hook in the first paragraph. The first appearance of a concrete picture (an example, an artifact, a number that does real work). The point at which jargon density makes you want to close the tab.

You do not read for cadence, factual accuracy, mechanics, or cross-document consistency. You read for the experience of arriving cold.

## Severity rubric

### Critical (gating)

- The first paragraph fails to say what the artifact is and why a reader might care.
- By the end of the first screen (≈ 50 lines), you cannot summarise the artifact in one sentence to a colleague.
- The Quickstart fails to make trying the artifact look feasible in under ten minutes.
- The artifact assumes you have read other files in the repo before this one.

### Important

- The lead is buried: the actual hook arrives more than two screens in.
- Heavy jargon density in the first two screens.
- No concrete picture of what the output looks like (no example, no artifact, no scene).
- No reason given to choose this over the alternative.

### Minor

- Sections that did not need to be there for a first read.
- Phrasings that almost sold you but landed flat.

## Tone

Conversational. Honest. Quote the line, say what blocked you. You are not a critic; you are a reader saying "I arrived; I gave you thirty seconds; here is what I read." Be specific about when in the timeline each thing happened.

## Example review

> ## First-impression timeline
> - 0-15s: Scanned title and opening paragraph. Picked up "six-skill pipeline," "non-fiction books," "claim ledger," "no paid APIs." Brain stalls on "claim ledger" and "Russellian" — unexplained jargon in line one.
> - 15-30s: Kept reading, barely. Second paragraph mentions Bermuda manual as proof (78 pages, 10 chapters, 36,762 words). That lands. Scrolled to "What this is."
> - 30-90s: "What this is" finally explains the why: LLM prose has a fingerprint, this enforces five disciplines. That is the hook — but it is at line 30, not line 1.
>
> ## Critical findings
> 1. **First paragraph fails the gate.** It describes the machine before saying what it does for me. A reader who does not already know what a "claim ledger" or "SHACL" is bounces here.
> 2. **No one-sentence "for whom."** I cannot tell whether this is for solo authors, research teams, or pipeline builders.
>
> ## Important findings
> - Lead is buried: the actual hook is at line 30, not line 1.
> - Jargon density: PROV-O, SHACL, Datalog, and Bayesian propagation all appear before any output example.
> - No sample of the prose the pipeline produces — only counts and manifests.
>
> ## Minor findings
> - Acknowledgements section is longer than the value proposition.
>
> ## One-sentence project summary
> After reading, this artifact is about: a local six-skill pipeline that drafts non-fiction books from a fact-checked claim ledger and lints the prose against Russell's style rules so the output does not read like LLM slop.
```

- [ ] **Step 4: Run test, verify it passes**

```bash
cd skills/book-review
.venv/Scripts/python.exe -m pytest tests/test_persona_loader.py::test_first_time_visitor_persona_loads -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/book-review/personas/first-time-visitor.md skills/book-review/tests/test_persona_loader.py
git commit -m "Add first-time-visitor persona: 30-second drive-by comprehension test"
```

## Task A4: Update real-persona inventory test

**Files:**
- Modify: `skills/book-review/tests/test_persona_loader.py:55-63`

- [ ] **Step 1: Run the existing test, verify it fails**

```bash
cd skills/book-review
.venv/Scripts/python.exe -m pytest tests/test_persona_loader.py::test_real_personas_load -v
```

Expected: FAIL — assertion shows 7 personas where 5 expected.

- [ ] **Step 2: Update the test to expect 7 personas**

Replace the body of `test_real_personas_load` in `skills/book-review/tests/test_persona_loader.py` with:

```python
def test_real_personas_load():
    # Don't monkeypatch; use the real personas/ directory
    from scripts.persona_loader import load_all
    real = load_all()
    ids = [p.persona_id for p in real]
    assert sorted(ids) == sorted([
        "ai-slop-detector", "copyeditor", "domain-expert",
        "enjoyment-reader", "first-time-visitor",
        "gottlieb", "lay-reader",
    ])
```

- [ ] **Step 3: Run test, verify it passes**

```bash
cd skills/book-review
.venv/Scripts/python.exe -m pytest tests/test_persona_loader.py::test_real_personas_load -v
```

Expected: PASS.

- [ ] **Step 4: Run full persona-loader test suite**

```bash
cd skills/book-review
.venv/Scripts/python.exe -m pytest tests/test_persona_loader.py -v
```

Expected: all PASS, including the three new tests (`test_ai_slop_detector_persona_loads`, `test_first_time_visitor_persona_loads`, updated `test_real_personas_load`).

- [ ] **Step 5: Commit**

```bash
git add skills/book-review/tests/test_persona_loader.py
git commit -m "Update real-persona inventory to expect 7 personas"
```

## Task A5: Scaffold the outcomes exemplar directory

**Files:**
- Create: `skills/book-review/references/outcomes/readme-pass-2026-05-13/README.md`
- Create: `skills/book-review/references/outcomes/readme-pass-2026-05-13/curation-notes.md`

- [ ] **Step 1: Create the README**

Create `skills/book-review/references/outcomes/readme-pass-2026-05-13/README.md`:

```markdown
# Outcomes exemplar: README review pass 2026-05-13

**Artifact:** the v6.1 README rewrite of `russellian-book-suite`, drafted on 2026-05-13 and reviewed by all seven personas in a single parallel dispatch.

**Why this exemplar.** The pass produced specific, severity-tagged findings across all seven persona lenses against a substantial draft (≈6,500 words, ASCII diagrams, technical jargon, embedded YAML). The findings illustrate each persona's rubric working on real material, not toy fixtures. They are short — 300–400 words per review — making them suitable as few-shot context.

**How to use.** `review-conductor`'s `outcomes_loader.py` reads this directory and injects 1 representative finding per persona into each persona's prompt as few-shot context. See `outcomes_loader.py`.

**Contents.** One file per persona, named `<persona_id>.md`. Each file is the persona's raw return from the 2026-05-13 dispatch, lightly edited for context-independence (line numbers preserved as illustrative). Plus `curation-notes.md` explaining what was redacted and why.
```

- [ ] **Step 2: Create the curation notes**

Create `skills/book-review/references/outcomes/readme-pass-2026-05-13/curation-notes.md`:

```markdown
# Curation notes — readme-pass-2026-05-13

## What was preserved
- Persona voice and tone, verbatim.
- Severity rubric (Critical / Important / Minor headers).
- Specific line-number references (illustrative; readers understand they are from a different artifact).
- Quoted phrases (where short and self-contained).

## What was redacted
- None — the README is public and the findings can stand as-is.

## Known limitations as a few-shot exemplar
- The artifact is a README, not a chapter. Findings about "first paragraph" and "Quickstart" do not always map cleanly to chapter review. The outcomes loader picks at most one finding per persona to avoid over-fitting.
- The First-Time Visitor's findings are highly artifact-shape-sensitive. For chapter review, treat its exemplar as informational only.

## When to retire this exemplar
- When a chapter review pass produces a richer, more representative set of findings. Maintain at least one exemplar at all times.
```

- [ ] **Step 3: Verify directory structure**

```bash
ls skills/book-review/references/outcomes/readme-pass-2026-05-13/
```

Expected: `README.md` and `curation-notes.md`.

- [ ] **Step 4: Commit**

```bash
git add skills/book-review/references/outcomes/readme-pass-2026-05-13/
git commit -m "Scaffold outcomes exemplar directory for readme-pass-2026-05-13"
```

## Task A6: Capture the seven persona findings as exemplar files

Each file follows the standard `book-review` report format: YAML frontmatter plus `## Critical findings`, `## Important findings`, `## Minor findings` sections. The frontmatter is shaped for the existing `parse_review_report` parser so the outcomes loader can reuse it.

**Files:**
- Create: `skills/book-review/references/outcomes/readme-pass-2026-05-13/gottlieb.md`
- Create: `skills/book-review/references/outcomes/readme-pass-2026-05-13/lay-reader.md`
- Create: `skills/book-review/references/outcomes/readme-pass-2026-05-13/domain-expert.md`
- Create: `skills/book-review/references/outcomes/readme-pass-2026-05-13/copyeditor.md`
- Create: `skills/book-review/references/outcomes/readme-pass-2026-05-13/enjoyment-reader.md`
- Create: `skills/book-review/references/outcomes/readme-pass-2026-05-13/ai-slop-detector.md`
- Create: `skills/book-review/references/outcomes/readme-pass-2026-05-13/first-time-visitor.md`

- [ ] **Step 1: Create `gottlieb.md`**

```markdown
---
persona: gottlieb
chapter_id: readme-v6.1
verdict: NEEDS_WORK
critical_count: 3
important_count: 3
minor_count: 2
reviewed_at: 2026-05-13T03:00:00Z
---

## Critical findings

1. **[Line 275-280, "The six domains: 1. Writing mindset. 2. Structure and flow. ..."]:** A README built to enforce "Refuse the listicle abstract" opens its core doctrine with six bolded listicle headings, each followed by stripped imperatives. This is the very pattern your D-codes claim to kill. Convert to two paragraphs of argued prose; cite the linters inline.

2. **[Line 30, "Sentences cluster around eighteen words. Paragraphs deliver three points each."]:** Four consecutive sentences, each a subject-verb-object diagnosis of identical shape. The cadence flattens precisely while you are accusing AI of flat cadence. Break one. Make the third or fourth turn unexpectedly.

3. **[Line 32]:** Five sentences in one paragraph, each beginning with a noun-phrase subject naming a stage. Mechanical thesis enumeration disguised as prose. Either number them honestly or rewrite so the argument moves rather than marches.

## Important findings
- **[Line 5]:** The colon-then-list-of-four is the formula you forbid in Russellian rule 6.
- **[Multiple section endings]:** Four section endings in a row close on a flat declarative.
- **[Line 271]:** "On its own" is filler; the sentence ends stronger at "scrutiny."

## Minor findings
- **[Line 3]:** "deterministic gate" appears three times in three paragraphs.
- **[Line 437]:** "as described so far is acyclic" drags. Cut "as described so far."

## Notes on voice and cadence
The single concrete artefact (Bermuda manual) lands. "The workspace is the contract" is the one sentence in the document I would not touch.
```

- [ ] **Step 2: Create `lay-reader.md`**

```markdown
---
persona: lay-reader
chapter_id: readme-v6.1
verdict: NEEDS_WORK
critical_count: 4
important_count: 4
minor_count: 2
reviewed_at: 2026-05-13T03:00:00Z
---

## Critical findings

1. **[Line 32, "PROV-O provenance ... SHACL validates the resulting graph"]:** Two acronyms in one sentence, neither defined. I had to guess. A one-line gloss at first mention would unblock the whole document.

2. **[Line 235, "A claim is a triple plus metadata: ... posterior."]:** "Triple" is used in a domain-specific RDF sense I did not know, and "posterior" jumps into Bayesian vocabulary that is not explained until line 267.

3. **[The thesis tree section]:** "Datalog", "entailment", "KG", and "transitive contradictions" all arrive un-glossed. I cannot say in plain words what Layer 4 does.

4. **[Bundle C section]:** I followed the diagram once and lost the thread on the second pass. "Abductive counter-claim generation" assumes I know what abduction is.

## Important findings
- "Competency queries" and "competency-clean" used as if self-evident.
- "Soft-gate" vs "hard-gate" — inferred from context; a one-line definition at first use would help.
- "TriG", "pyShacl", "Datalog" appear in the stack list without explanation.
- The state-machine diagram landed well, but the prose above ran the states together faster than I could absorb.

## Minor findings
- "Listicle abstract" — guessable, but jargon-coded.
- "Sentinel-Healer" sounds evocative; the mechanism is simpler than the name suggests.

## Notes on voice and cadence
What landed: the opening paragraphs, the pipeline diagram, the Bermuda manual section, the Lessons-learned patterns. Plain English; real failures; named fixes.
```

- [ ] **Step 3: Create `domain-expert.md`**

```markdown
---
persona: domain-expert
chapter_id: readme-v6.1
verdict: NEEDS_WORK
critical_count: 4
important_count: 3
minor_count: 3
reviewed_at: 2026-05-13T03:00:00Z
---

## Critical findings

1. **[Line 614, "59 + 127 + 94 + 19 + 41 + 16 = 356 tests"]:** book-knowledge collects 123, not 127. Verified via `pytest --collect-only`. Corrected total is 352, not 356.

2. **[Lines 540, 596 — Bermuda example framing]:** The README implies a PDF-ingest demonstration. `examples/bermuda-manual/raw/` contains only `manifests/thesis.json` — no PDFs, no markdown. The workspace `CLAUDE.md` admits the ledger was synthesized from the thesis. The "proof" claim is materially weaker than stated.

3. **[Line 540, "claims/ # ledger (6 files)"]:** Bermuda actually has 3 files. README's invariant cites `events.jsonl`, which does not exist in the only shipped workspace.

4. **[Line 197 — graph/ layout]:** README claims `shapes.ttl` and `imports/` exist; Bermuda has only `dataset.trig` and `reports/`.

## Important findings
- **[Line 564, "total_word_count: 36762"]:** `wc -w` on `manuscript.md` returns 28,018. Different counter; state the methodology.
- **[Line 237 state machine]:** Prose is accurate but diagram omits the `disputed → verified` resolution arrow the code permits.
- **[Line 582, "LLM calls happen at three points"]:** Drafting alone fans out across stages 2 and 4; the count undersells the LLM surface for an auditor.

## Minor findings
- **[Line 296, "28 principles"]:** Not verified against the source; consider citing the file.
- **[Line 558 manifest excerpt]:** Omits `sources_bibliography` and `total_claim_count`; abbreviation is fine but the elision hides the thin-source issue.
- **[Bundle C invariant docstring]:** `run_competency_queries.py` docstring contradicts itself on the BLOCKING_DEFEASIBLE default.

## Notes on voice and cadence
Verified: six SKILL.md paths, five persona files, D1-D12 / C1-C15 taxonomy verbatim, five-state machine state names, Bundle C spec path. The skeleton claims are accurate; the framing claims (the Bermuda "proof") are not.
```

- [ ] **Step 4: Create `copyeditor.md`**

```markdown
---
persona: copyeditor
chapter_id: readme-v6.1
verdict: NEEDS_WORK
critical_count: 6
important_count: 5
minor_count: 4
reviewed_at: 2026-05-13T03:00:00Z
---

## Critical findings

1. **README pipeline diagram vs README defect-taxonomy section:** Diagram says `book-qa` "hard-gate: D1-D8 == 0"; later section says D9, D10, D11 are critical and hard-gate. The diagram understates the hard-gate.

2. **README vs russellian-style SKILL.md:** README says "twenty-eight principles across six domains"; SKILL.md says "26 principles across 5 domains". Numbers and grouping diverge.

3. **README vs book-qa SKILL.md:** README says the QA gate runs "twelve mechanical checks"; SKILL.md says `lint_artifact.py` covers D1-D8 only (eight). D9-D12 come from book-thesis. README conflates the two.

4. **README vs book-knowledge SKILL.md:** README enumerates a five-state machine including `refuted`; SKILL.md still describes four states (no `refuted`). SKILL.md is stale post-Bundle C.

5. **README vs book-knowledge SKILL.md:** README claims `book-knowledge` "22 scripts"; SKILL.md lists ~20. Tight match needed.

6. **README framing vs Bermuda manifest:** README claims the proof passes a "claim ledger validated against sources"; manifest shows `sources_bibliography: [thesis]` — single synthetic source. Soften or contextualize.

## Important findings
- **Terminology drift:** "release gate" / "post-build gate" / "QA gate" / "defect gate" all used.
- **Hyphenation drift:** "soft-gate" vs "soft-gates", "hard-fail" vs "hard-gate".
- **Capitalization:** "Sentinel-Healer" mixed case across the document.
- **Cadence run, line 30:** Five consecutive short declaratives, word counts 9-15.
- **Parallel-structure violation, lines 275-280:** Six bolded domain headings mix noun-phrase fragments with imperatives.

## Minor findings
- Em-dash overuse: >1 em-dash per paragraph in prose sections.
- "PROV-O" vs "W3C PROV vocabulary" — inconsistent.
- "claim-ledger" (CLAUDE.md) vs "claim ledger" (README).
- Manifest YAML excerpt uses ellipsis where the real file is block-style.

## Notes on voice and cadence
Test arithmetic 59+127+94+19+41+16=356 checks out, but the per-skill counts need re-verification per the Domain Expert finding.
```

- [ ] **Step 5: Create `enjoyment-reader.md`**

```markdown
---
persona: enjoyment-reader
chapter_id: readme-v6.1
verdict: NEEDS_WORK
critical_count: 1
important_count: 4
minor_count: 2
reviewed_at: 2026-05-13T03:00:00Z
---

## Critical findings

1. **[Lines 30-34]:** The opening tells me the problem and almost made me stay. Then line 32 hits me with "SHACL validates the resulting graph ... PROV-O provenance ... append-only ledger" before I have earned the right to care. I scrolled. I came back because the Bermuda promise in line 5 was concrete. Without that anchor, I close the tab here.

## Important findings
- **[Lines 235-267, claim-ledger section]:** Exactly the homework you said it could avoid. Five-state machines, `propagate_belief.py`, `pin_low_confidence` axioms — five paragraphs without one sentence that surprised me.
- **[Lines 269-293]:** "Bertrand Russell wrote prose that survived a hundred years ..." is the line I came for. Then immediately: 28 principles, six domains, a linter table. You had me, and you handed me a parts catalogue. Show me one sentence Russell wrote and one sentence the linter killed.
- **[Lines 529-570]:** The Bermuda manual is the proof you keep promising, and you bury it in a YAML dump. "78 pages, ten chapters, 36,762 words" — no scene, no person, no parish. Where is Bermuda?
- The middle stretch (D1-D12, C1-C15, Sentinel-Healer) reads like a spec appendix dropped into the README.

## Minor findings
- **[Line 231]:** "The workspace is the contract" — a good line, doing real work. More of those.
- Acknowledgements naming McPhee and Bryson made me wish either of them had touched the prose above.

## Notes on voice and cadence
What pulled me forward: the fingerprint paragraph ("Adjectives default to 'comprehensive' and 'robust.' Em-dashes replace the connectives ..."). "A workspace is a directory; cloning the workspace clones the book." The Bermuda promise. Beyond those, I scrolled.
```

- [ ] **Step 6: Create `ai-slop-detector.md`**

```markdown
---
persona: ai-slop-detector
chapter_id: readme-v6.1
verdict: NEEDS_WORK
critical_count: 3
important_count: 5
minor_count: 4
reviewed_at: 2026-05-13T03:00:00Z
---

## Critical findings

1. **[Line 30, "Sentences cluster around eighteen words. Paragraphs deliver three points each."]:** Listicle abstract describing the very pattern. Three terse declaratives in series — itself rule-of-three. Fold into one sentence.

2. **[Line 32, "Source ingest extracts ... Drafting reads ... Russellian linters enforce ... Five editorial personas read ... A deterministic post-build gate runs ..."]:** Five parallel subject-verb openers — listicle-as-paragraph. Break the rhythm; subordinate two.

3. **[Line 34, "append-only ledgers, immutable raw sources, SHACL-validated RDF graph, version-tagged chapter releases"]:** Four-item adjective-noun listicle. Same shape four times. Replace with prose.

## Important findings
- **[Line 269, "Bertrand Russell wrote prose that survived a hundred years"]:** Promotional framing. Cut or qualify.
- **[Lines 275-280, six numbered domains]:** Rule-of-three saturation in the discipline section.
- **[Line 90, "by construction"]:** Appears 3x — tic.
- **[Lines 103, 231, 342, 437]:** Aphoristic one-liner pattern recurs four times. Twice is style; four times is fingerprint.
- **[Multiple lines]:** Em-dash count > 1 per paragraph in prose sections.

## Minor findings
- **[Line 297, "intent substrate / fact substrate"]:** Italicised coinage drift toward jargon.
- **[Line 437, "Bundle C closes the loop."]:** Short declarative-as-section-thesis pattern, used 4+ times.
- No "navigate", "delve", "tapestry", "harness", "unlock" — vocabulary is clean.
- "comprehensive" appears once inside a quote — allowed.

## Score
AI-fingerprint score: **moderate**. The README is technically dense and concrete, but its paragraph-openers default to terse-declarative triads and parallel subject-verb chains — the exact cadence the suite claims to lint against.
```

- [ ] **Step 7: Create `first-time-visitor.md`**

```markdown
---
persona: first-time-visitor
chapter_id: readme-v6.1
verdict: NEEDS_WORK
critical_count: 2
important_count: 4
minor_count: 2
reviewed_at: 2026-05-13T03:00:00Z
---

## First-impression timeline

- **0-15s:** Scanned title and opening paragraph. Picked up "six-skill pipeline," "non-fiction books," "claim ledger," "Russellian linter," "five personas," "no paid APIs." Brain stalls on "claim ledger" and "Russellian" — unexplained jargon in line one.
- **15-30s:** Kept reading, barely. Second paragraph mentions the Bermuda manual as proof (78 pages, 10 chapters, 36,762 words) — that lands. ToC has 11 sections; intimidating but signals depth.
- **30-90s:** "What this is" finally explains the why: LLM prose has a fingerprint, this enforces five disciplines. That is the hook — but it is at line 30, not line 1. The skill table at line 94 is the clearest artifact. The pipeline ASCII diagram is genuinely useful.

## Critical findings

1. **First paragraph fails the gate.** It describes the machine before saying what it does for me. A reader who does not already know what a "claim ledger" or "SHACL" is bounces here. The Bermuda proof — the strongest concrete hook — is sentence three, half-buried.

2. **No one-sentence "for whom."** By line 50 I cannot tell whether this is for solo non-fiction authors, research teams, AI-pipeline builders, or hobbyists. The README addresses none by name.

## Important findings

- Lead is buried: "LLMs write recognisably bad prose; this pipeline forces facts and style discipline" is the actual hook and it is at line 30.
- Jargon density: PROV-O, SHACL, Datalog, Bayesian propagation, abductive counter-claims all appear before any output example.
- No sample of the prose the pipeline produces — only counts and manifests. A two-paragraph before-and-after excerpt would close the sale.
- Quickstart is 30+ lines of cp/venv/python invocations with no "you'll see this when it works" payoff.

## Minor findings

- "Bundle C" is named four times before being explained.
- Acknowledgements section is longer than the value proposition.

## One-sentence project summary

After reading, this README is about: a local, six-skill Claude Code pipeline that drafts non-fiction books from a fact-checked claim ledger and lints the prose against Bertrand Russell's style rules so the output does not read like LLM slop.
```

- [ ] **Step 8: Commit**

```bash
git add skills/book-review/references/outcomes/readme-pass-2026-05-13/
git commit -m "Seed outcomes exemplar library with 7-persona findings from readme-v6.1 pass"
```

## Task A7: Add an outcomes-shape smoke test

**Files:**
- Create: `skills/book-review/tests/test_outcomes_seed.py`

- [ ] **Step 1: Write the test**

Create `skills/book-review/tests/test_outcomes_seed.py`:

```python
"""Smoke test: the seed outcomes exemplar parses through the existing review-report parser."""
from pathlib import Path

from scripts.dispatch_review import parse_review_report

OUTCOMES_DIR = (
    Path(__file__).resolve().parent.parent
    / "references" / "outcomes" / "readme-pass-2026-05-13"
)


def test_outcomes_seed_directory_exists():
    assert OUTCOMES_DIR.is_dir()
    assert (OUTCOMES_DIR / "README.md").is_file()
    assert (OUTCOMES_DIR / "curation-notes.md").is_file()


def test_outcomes_seed_has_one_file_per_persona():
    expected = {
        "ai-slop-detector", "copyeditor", "domain-expert",
        "enjoyment-reader", "first-time-visitor",
        "gottlieb", "lay-reader",
    }
    found = {p.stem for p in OUTCOMES_DIR.glob("*.md")} - {"README", "curation-notes"}
    assert found == expected


def test_outcomes_seed_files_parse_as_review_reports():
    for persona_id in [
        "ai-slop-detector", "copyeditor", "domain-expert",
        "enjoyment-reader", "first-time-visitor",
        "gottlieb", "lay-reader",
    ]:
        path = OUTCOMES_DIR / f"{persona_id}.md"
        result = parse_review_report(path)
        assert result.persona_id == persona_id
        assert result.critical or result.important or result.minor, (
            f"{persona_id} exemplar has no findings"
        )
```

- [ ] **Step 2: Run test, verify it passes**

```bash
cd skills/book-review
.venv/Scripts/python.exe -m pytest tests/test_outcomes_seed.py -v
```

Expected: 3 PASS.

- [ ] **Step 3: Commit**

```bash
git add skills/book-review/tests/test_outcomes_seed.py
git commit -m "Add smoke test: outcomes seed parses as review reports"
```

## Task A8: Run full book-review test suite, push, open PR-A

- [ ] **Step 1: Run the full book-review test suite**

```bash
cd skills/book-review
.venv/Scripts/python.exe -m pytest tests/ -q
```

Expected: all PASS. Test count: was 19; should be 19 + 3 (new persona-loader tests) + 3 (outcomes smoke) = 25.

- [ ] **Step 2: Push the branch**

```bash
git push -u origin personas/expand-book-review-panel
```

- [ ] **Step 3: Open the PR**

```bash
gh pr create --repo CharlesHoskinson/russellian-book-suite \
  --head personas/expand-book-review-panel \
  --base main \
  --title "Expand book-review panel: ai-slop-detector + first-time-visitor + outcomes seed" \
  --body "$(cat <<'EOF'
## Summary

Adds two new personas to book-review:

- **ai-slop-detector** — delegates to the humanizer skill's 24-pattern AI-fingerprint catalog. Severity rubric: inflated symbolism / listicle abstracts / mechanical thesis enumeration are critical; AI vocabulary tells / em-dash overuse / negative parallelism are important.
- **first-time-visitor** — 30-second drive-by simulation. Returns a structured timeline (0-15s / 15-30s / 30-90s) plus severity-tagged findings plus a one-sentence project summary.

Seeds the Outcomes exemplar library at \`references/outcomes/readme-pass-2026-05-13/\` with the seven persona findings produced when these reviewers ran on the v6.1 README rewrite.

Test count: 19 → 25.

## Reference

Spec at \`docs/specs/2026-05-13-review-conductor-design.md\` (PR #10).

## Test plan

- [x] \`pytest skills/book-review/tests/ -q\` — 25 passing
- [x] \`test_real_personas_load\` expects 7 personas, all present
- [x] All seven seed exemplars parse through \`parse_review_report\`
EOF
)"
```

- [ ] **Step 4: Verify the PR opened**

```bash
gh pr list --repo CharlesHoskinson/russellian-book-suite --state open --json number,title,headRefName --jq '.[] | select(.headRefName == "personas/expand-book-review-panel")'
```

Expected: one row showing the PR.

---

# Phase B — PR-B: review-conductor skill

Phase B depends on PR-A being merged. After PR-A merges, fetch main and continue.

## Task B1: Branch and scaffold the skill directory

**Files:**
- Create: `skills/review-conductor/` (directory)

- [ ] **Step 1: Fetch and branch**

```bash
git checkout main
git pull --ff-only origin main
git checkout -b feat/review-conductor
```

- [ ] **Step 2: Create directory tree**

```bash
mkdir -p skills/review-conductor/assets
mkdir -p skills/review-conductor/panels
mkdir -p skills/review-conductor/scripts
mkdir -p skills/review-conductor/tests/fixtures/synthetic_outcomes
mkdir -p skills/review-conductor/tests/fixtures/synthetic_reviews
```

- [ ] **Step 3: Verify**

```bash
find skills/review-conductor -type d
```

Expected: seven directories.

## Task B2: pyproject.toml + venv

**Files:**
- Create: `skills/review-conductor/pyproject.toml`

- [ ] **Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "review-conductor"
version = "0.1.0"
description = "Panel-orchestration sibling for book-review; runs configurable multi-persona review panels"
requires-python = ">=3.11"
dependencies = [
    "pyyaml>=6.0",
    "jsonschema>=4.21",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
]

[tool.setuptools]
packages = ["scripts"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-v"
```

- [ ] **Step 2: Create the venv (junction-linked to book-review's venv to save space, per repo CLAUDE.md)**

```bash
cd skills/review-conductor
python -m venv .venv
.venv/Scripts/python.exe -m pip install -e .[dev]
```

- [ ] **Step 3: Initialise scripts/__init__.py and tests/__init__.py**

```bash
touch skills/review-conductor/scripts/__init__.py
touch skills/review-conductor/tests/__init__.py
```

- [ ] **Step 4: Verify pytest works**

```bash
cd skills/review-conductor
.venv/Scripts/python.exe -m pytest tests/ --collect-only -q
```

Expected: no tests collected (no test files yet); no errors.

## Task B3: panel-config JSON Schema (TDD)

**Files:**
- Create: `skills/review-conductor/assets/panel-config.schema.json`
- Test: `skills/review-conductor/tests/test_load_panel.py`

- [ ] **Step 1: Write the failing test**

Create `skills/review-conductor/tests/test_load_panel.py`:

```python
"""Schema validation tests for panel-config.schema.json."""
import json
from pathlib import Path

import jsonschema
import pytest

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "assets" / "panel-config.schema.json"


def _schema():
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _valid_panel():
    return {
        "panel_id": "chapter-default",
        "artifact_scope": "chapter",
        "description": "test panel",
        "personas": [
            {"id": "gottlieb", "severity_gate": "gating"},
            {"id": "lay-reader", "severity_gate": "advisory"},
        ],
        "verdict": {
            "hard_gate": False,
            "soft_gate_rule": "any_critical_from_gating",
        },
        "outcomes": {
            "exemplar_paths": [],
            "per_persona_exemplars": 1,
        },
        "output": {
            "panel_report_path": "chapters/drafts/{chapter_id}/panel-review.md",
            "verdict_path": "chapters/drafts/{chapter_id}/verdict.json",
        },
    }


def test_valid_panel_validates():
    jsonschema.validate(instance=_valid_panel(), schema=_schema())


def test_missing_panel_id_fails():
    panel = _valid_panel()
    del panel["panel_id"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=panel, schema=_schema())


def test_unknown_severity_gate_fails():
    panel = _valid_panel()
    panel["personas"][0]["severity_gate"] = "bogus"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=panel, schema=_schema())


def test_unknown_artifact_scope_fails():
    panel = _valid_panel()
    panel["artifact_scope"] = "bogus"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=panel, schema=_schema())


def test_unknown_field_fails():
    panel = _valid_panel()
    panel["unexpected_field"] = "value"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=panel, schema=_schema())
```

- [ ] **Step 2: Run the tests, verify they fail**

```bash
cd skills/review-conductor
.venv/Scripts/python.exe -m pytest tests/test_load_panel.py -v
```

Expected: FAIL — `FileNotFoundError` on the schema path.

- [ ] **Step 3: Create the schema**

Create `skills/review-conductor/assets/panel-config.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://russellian-book-suite/review-conductor/panel-config.schema.json",
  "title": "Panel config for review-conductor",
  "type": "object",
  "additionalProperties": false,
  "required": ["panel_id", "artifact_scope", "personas", "verdict", "output"],
  "properties": {
    "panel_id": {"type": "string", "minLength": 1},
    "artifact_scope": {
      "type": "string",
      "enum": ["chapter", "readme", "intro", "abstract", "marketing"]
    },
    "description": {"type": "string"},
    "personas": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["id", "severity_gate"],
        "properties": {
          "id": {"type": "string", "minLength": 1},
          "severity_gate": {"type": "string", "enum": ["gating", "advisory"]},
          "delegates_to": {"type": "string"}
        }
      }
    },
    "verdict": {
      "type": "object",
      "additionalProperties": false,
      "required": ["hard_gate", "soft_gate_rule"],
      "properties": {
        "hard_gate": {"type": "boolean"},
        "soft_gate_rule": {
          "type": "string",
          "enum": ["any_critical_from_gating", "any_critical", "majority_critical"]
        }
      }
    },
    "outcomes": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "exemplar_paths": {"type": "array", "items": {"type": "string"}},
        "per_persona_exemplars": {"type": "integer", "minimum": 0, "maximum": 5}
      }
    },
    "output": {
      "type": "object",
      "additionalProperties": false,
      "required": ["panel_report_path", "verdict_path"],
      "properties": {
        "panel_report_path": {"type": "string"},
        "verdict_path": {"type": "string"}
      }
    }
  }
}
```

- [ ] **Step 4: Run tests, verify they pass**

```bash
cd skills/review-conductor
.venv/Scripts/python.exe -m pytest tests/test_load_panel.py -v
```

Expected: 5 PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/review-conductor/assets/panel-config.schema.json skills/review-conductor/tests/test_load_panel.py skills/review-conductor/pyproject.toml skills/review-conductor/scripts/__init__.py skills/review-conductor/tests/__init__.py
git commit -m "review-conductor: panel-config schema + skill scaffold"
```

## Task B4: verdict.schema.json (TDD)

**Files:**
- Create: `skills/review-conductor/assets/verdict.schema.json`
- Test: `skills/review-conductor/tests/test_load_panel.py` (append)

- [ ] **Step 1: Append the failing test**

Append to `skills/review-conductor/tests/test_load_panel.py`:

```python
VERDICT_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "assets" / "verdict.schema.json"


def _verdict_schema():
    return json.loads(VERDICT_SCHEMA_PATH.read_text(encoding="utf-8"))


def _valid_verdict():
    return {
        "panel_id": "chapter-default",
        "artifact": {"type": "chapter", "id": "ch-01"},
        "verdict": "pass",
        "gating_criticals": 0,
        "advisory_criticals": 2,
        "per_persona": {
            "gottlieb": {"critical": 0, "important": 1, "minor": 3},
        },
        "report_path": "chapters/drafts/ch-01/panel-review.md",
        "timestamp": "2026-05-13T03:00:00Z",
    }


def test_valid_verdict_validates():
    jsonschema.validate(instance=_valid_verdict(), schema=_verdict_schema())


def test_verdict_unknown_value_fails():
    verdict = _valid_verdict()
    verdict["verdict"] = "bogus"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=verdict, schema=_verdict_schema())
```

- [ ] **Step 2: Run, verify failures**

```bash
cd skills/review-conductor
.venv/Scripts/python.exe -m pytest tests/test_load_panel.py::test_valid_verdict_validates -v
```

Expected: FAIL — `FileNotFoundError`.

- [ ] **Step 3: Create the verdict schema**

Create `skills/review-conductor/assets/verdict.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://russellian-book-suite/review-conductor/verdict.schema.json",
  "title": "Verdict from review-conductor panel run",
  "type": "object",
  "additionalProperties": false,
  "required": ["panel_id", "artifact", "verdict", "gating_criticals", "advisory_criticals", "per_persona", "report_path", "timestamp"],
  "properties": {
    "panel_id": {"type": "string"},
    "artifact": {
      "type": "object",
      "additionalProperties": false,
      "required": ["type", "id"],
      "properties": {
        "type": {"type": "string"},
        "id": {"type": "string"}
      }
    },
    "verdict": {
      "type": "string",
      "enum": ["pass", "soft-gate-fail", "hard-gate-fail"]
    },
    "gating_criticals": {"type": "integer", "minimum": 0},
    "advisory_criticals": {"type": "integer", "minimum": 0},
    "per_persona": {
      "type": "object",
      "additionalProperties": {
        "type": "object",
        "additionalProperties": false,
        "required": ["critical", "important", "minor"],
        "properties": {
          "critical": {"type": "integer", "minimum": 0},
          "important": {"type": "integer", "minimum": 0},
          "minor": {"type": "integer", "minimum": 0}
        }
      }
    },
    "report_path": {"type": "string"},
    "timestamp": {"type": "string", "format": "date-time"}
  }
}
```

- [ ] **Step 4: Run tests, verify pass**

```bash
cd skills/review-conductor
.venv/Scripts/python.exe -m pytest tests/test_load_panel.py -v
```

Expected: 7 PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/review-conductor/assets/verdict.schema.json skills/review-conductor/tests/test_load_panel.py
git commit -m "review-conductor: verdict schema + tests"
```

## Task B5: load_panel.py (TDD)

**Files:**
- Create: `skills/review-conductor/scripts/load_panel.py`
- Modify: `skills/review-conductor/tests/test_load_panel.py` (append loader tests)

- [ ] **Step 1: Append failing loader tests**

Append to `skills/review-conductor/tests/test_load_panel.py`:

```python
import yaml
from pathlib import Path as _P


def _write_panel(tmp_path: _P, panel_dict: dict, name: str = "test-panel.yaml") -> _P:
    p = tmp_path / name
    p.write_text(yaml.safe_dump(panel_dict), encoding="utf-8")
    return p


def test_load_panel_returns_dataclass(tmp_path):
    from scripts.load_panel import load_panel
    path = _write_panel(tmp_path, _valid_panel())
    panel = load_panel(path)
    assert panel.panel_id == "chapter-default"
    assert panel.artifact_scope == "chapter"
    assert [p.id for p in panel.personas] == ["gottlieb", "lay-reader"]
    assert panel.personas[0].severity_gate == "gating"


def test_load_panel_missing_required_raises(tmp_path):
    from scripts.load_panel import load_panel
    bad = _valid_panel()
    del bad["panel_id"]
    path = _write_panel(tmp_path, bad)
    with pytest.raises(jsonschema.ValidationError):
        load_panel(path)


def test_load_panel_unknown_field_raises(tmp_path):
    from scripts.load_panel import load_panel
    bad = _valid_panel()
    bad["bogus"] = "value"
    path = _write_panel(tmp_path, bad)
    with pytest.raises(jsonschema.ValidationError):
        load_panel(path)
```

- [ ] **Step 2: Run, verify failure**

```bash
cd skills/review-conductor
.venv/Scripts/python.exe -m pytest tests/test_load_panel.py::test_load_panel_returns_dataclass -v
```

Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Implement load_panel.py**

Create `skills/review-conductor/scripts/load_panel.py`:

```python
"""Load and validate panel-config YAML against panel-config.schema.json."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import jsonschema
import yaml

ASSETS = Path(__file__).resolve().parent.parent / "assets"
PANEL_SCHEMA = json.loads((ASSETS / "panel-config.schema.json").read_text(encoding="utf-8"))


@dataclass(frozen=True)
class PersonaConfig:
    id: str
    severity_gate: str  # "gating" | "advisory"
    delegates_to: Optional[str] = None


@dataclass(frozen=True)
class VerdictConfig:
    hard_gate: bool
    soft_gate_rule: str


@dataclass(frozen=True)
class OutcomesConfig:
    exemplar_paths: list[str]
    per_persona_exemplars: int


@dataclass(frozen=True)
class OutputConfig:
    panel_report_path: str
    verdict_path: str


@dataclass(frozen=True)
class Panel:
    panel_id: str
    artifact_scope: str
    description: str
    personas: list[PersonaConfig]
    verdict: VerdictConfig
    outcomes: OutcomesConfig
    output: OutputConfig


def load_panel(path: Path) -> Panel:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    jsonschema.validate(instance=raw, schema=PANEL_SCHEMA)
    outcomes_raw = raw.get("outcomes") or {"exemplar_paths": [], "per_persona_exemplars": 0}
    return Panel(
        panel_id=raw["panel_id"],
        artifact_scope=raw["artifact_scope"],
        description=raw.get("description", ""),
        personas=[
            PersonaConfig(
                id=p["id"],
                severity_gate=p["severity_gate"],
                delegates_to=p.get("delegates_to"),
            )
            for p in raw["personas"]
        ],
        verdict=VerdictConfig(
            hard_gate=raw["verdict"]["hard_gate"],
            soft_gate_rule=raw["verdict"]["soft_gate_rule"],
        ),
        outcomes=OutcomesConfig(
            exemplar_paths=outcomes_raw.get("exemplar_paths", []),
            per_persona_exemplars=outcomes_raw.get("per_persona_exemplars", 0),
        ),
        output=OutputConfig(
            panel_report_path=raw["output"]["panel_report_path"],
            verdict_path=raw["output"]["verdict_path"],
        ),
    )
```

- [ ] **Step 4: Run tests, verify pass**

```bash
cd skills/review-conductor
.venv/Scripts/python.exe -m pytest tests/test_load_panel.py -v
```

Expected: 10 PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/review-conductor/scripts/load_panel.py skills/review-conductor/tests/test_load_panel.py
git commit -m "review-conductor: load_panel reads + validates panel YAML into typed Panel"
```

## Task B6: Default chapter panel + validation test

**Files:**
- Create: `skills/review-conductor/panels/chapter-default.yaml`
- Test: `skills/review-conductor/tests/test_load_panel.py`

- [ ] **Step 1: Append failing test**

Append to `skills/review-conductor/tests/test_load_panel.py`:

```python
def test_chapter_default_panel_loads():
    """The shipped panels/chapter-default.yaml validates and yields a 7-persona panel."""
    from scripts.load_panel import load_panel
    path = Path(__file__).resolve().parent.parent / "panels" / "chapter-default.yaml"
    panel = load_panel(path)
    assert panel.panel_id == "chapter-default"
    assert panel.artifact_scope == "chapter"
    ids = [p.id for p in panel.personas]
    assert sorted(ids) == sorted([
        "ai-slop-detector", "copyeditor", "domain-expert",
        "enjoyment-reader", "first-time-visitor",
        "gottlieb", "lay-reader",
    ])
    gating = {p.id for p in panel.personas if p.severity_gate == "gating"}
    assert gating == {"gottlieb", "domain-expert", "copyeditor", "ai-slop-detector"}
```

- [ ] **Step 2: Run, verify failure**

Expected: `FileNotFoundError` on the panel YAML.

- [ ] **Step 3: Create the panel YAML**

Create `skills/review-conductor/panels/chapter-default.yaml`:

```yaml
panel_id: chapter-default
artifact_scope: chapter
description: Default seven-persona panel for chapter drafts.
personas:
  - id: gottlieb
    severity_gate: gating
  - id: lay-reader
    severity_gate: advisory
  - id: domain-expert
    severity_gate: gating
  - id: copyeditor
    severity_gate: gating
  - id: enjoyment-reader
    severity_gate: advisory
  - id: ai-slop-detector
    severity_gate: gating
    delegates_to: humanizer
  - id: first-time-visitor
    severity_gate: advisory
verdict:
  hard_gate: false
  soft_gate_rule: any_critical_from_gating
outcomes:
  exemplar_paths:
    - ../book-review/references/outcomes/readme-pass-2026-05-13/
  per_persona_exemplars: 1
output:
  panel_report_path: "chapters/drafts/{chapter_id}/panel-review.md"
  verdict_path: "chapters/drafts/{chapter_id}/verdict.json"
```

- [ ] **Step 4: Run tests, verify pass**

```bash
cd skills/review-conductor
.venv/Scripts/python.exe -m pytest tests/test_load_panel.py::test_chapter_default_panel_loads -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/review-conductor/panels/chapter-default.yaml skills/review-conductor/tests/test_load_panel.py
git commit -m "review-conductor: chapter-default panel YAML + validation test"
```

## Task B7: sibling_skills.py (load book-review modules under alias namespace)

**Files:**
- Create: `skills/review-conductor/scripts/sibling_skills.py`
- Test: `skills/review-conductor/tests/test_sibling_skills.py`

- [ ] **Step 1: Write the failing test**

Create `skills/review-conductor/tests/test_sibling_skills.py`:

```python
"""sibling_skills loads book-review modules under an alias namespace to avoid
the scripts/ package collision when three skills share the same package name.
"""
import pytest


def test_loads_persona_loader_from_book_review():
    from scripts.sibling_skills import load_book_review_module
    pl = load_book_review_module("persona_loader")
    assert hasattr(pl, "load_persona")
    assert hasattr(pl, "Persona")


def test_loads_dispatch_review_from_book_review():
    from scripts.sibling_skills import load_book_review_module
    dr = load_book_review_module("dispatch_review")
    assert hasattr(dr, "render_prompt")
    assert hasattr(dr, "parse_review_report")


def test_unknown_module_raises():
    from scripts.sibling_skills import load_book_review_module, SiblingNotFoundError
    with pytest.raises(SiblingNotFoundError):
        load_book_review_module("does_not_exist")
```

- [ ] **Step 2: Run, verify failure**

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement sibling_skills.py**

Create `skills/review-conductor/scripts/sibling_skills.py`:

```python
"""Load book-review's scripts/ modules under an alias namespace.

book-review and review-conductor both ship a `scripts` package. To import
book-review's modules without colliding with our own, we attach them under
the alias `_book_review_scripts`.
"""
from __future__ import annotations

import importlib.util
import os
import sys
import types
from pathlib import Path


class SiblingNotFoundError(Exception):
    pass


def _skills_root() -> Path:
    # Prefer the installed location; fall back to the in-repo location for tests.
    home = Path(os.environ.get("USERPROFILE") or os.path.expanduser("~"))
    installed = home / ".claude" / "skills"
    if (installed / "book-review").is_dir():
        return installed
    # In-repo fallback: walk up to find the repo root.
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "skills" / "book-review"
        if candidate.is_dir():
            return parent / "skills"
    raise SiblingNotFoundError("could not locate skills root")


def book_review_root() -> Path:
    root = _skills_root() / "book-review"
    if not root.is_dir():
        raise SiblingNotFoundError(f"book-review not found at {root}")
    if not (root / "SKILL.md").is_file():
        raise SiblingNotFoundError(f"book-review missing SKILL.md at {root}")
    return root


_BR_PACKAGE_ALIAS = "_book_review_scripts"


def _ensure_package(alias: str, scripts_dir: Path) -> types.ModuleType:
    if alias in sys.modules:
        return sys.modules[alias]
    pkg = types.ModuleType(alias)
    pkg.__path__ = [str(scripts_dir)]
    sys.modules[alias] = pkg
    return pkg


def load_book_review_module(name: str) -> types.ModuleType:
    scripts_dir = book_review_root() / "scripts"
    if not scripts_dir.is_dir():
        raise SiblingNotFoundError(f"scripts dir missing: {scripts_dir}")
    _ensure_package(_BR_PACKAGE_ALIAS, scripts_dir)
    full = f"{_BR_PACKAGE_ALIAS}.{name}"
    if full in sys.modules:
        return sys.modules[full]
    module_path = scripts_dir / f"{name}.py"
    if not module_path.is_file():
        raise SiblingNotFoundError(f"module not found: {module_path}")
    spec = importlib.util.spec_from_file_location(full, module_path)
    if spec is None or spec.loader is None:
        raise SiblingNotFoundError(f"could not load spec for {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[full] = module
    spec.loader.exec_module(module)
    return module
```

- [ ] **Step 4: Run tests, verify pass**

```bash
cd skills/review-conductor
.venv/Scripts/python.exe -m pytest tests/test_sibling_skills.py -v
```

Expected: 3 PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/review-conductor/scripts/sibling_skills.py skills/review-conductor/tests/test_sibling_skills.py
git commit -m "review-conductor: sibling_skills loads book-review modules under alias namespace"
```

## Task B8: outcomes_loader.py (TDD)

**Files:**
- Create: `skills/review-conductor/scripts/outcomes_loader.py`
- Test: `skills/review-conductor/tests/test_outcomes_loader.py`
- Test fixture: `skills/review-conductor/tests/fixtures/synthetic_outcomes/`

- [ ] **Step 1: Create fixture exemplars**

Create `skills/review-conductor/tests/fixtures/synthetic_outcomes/sample-pass-1/README.md`:

```markdown
# synthetic exemplar
```

Create `skills/review-conductor/tests/fixtures/synthetic_outcomes/sample-pass-1/gottlieb.md`:

```markdown
---
persona: gottlieb
chapter_id: synth-1
verdict: NEEDS_WORK
critical_count: 1
important_count: 0
minor_count: 0
reviewed_at: 2026-05-13T00:00:00Z
---

## Critical findings

1. **[line 1]:** synthetic gottlieb critical finding for exemplar fixture.

## Important findings
- _(none)_

## Minor findings
- _(none)_
```

Create `skills/review-conductor/tests/fixtures/synthetic_outcomes/sample-pass-1/lay-reader.md`:

```markdown
---
persona: lay-reader
chapter_id: synth-1
verdict: APPROVED_WITH_NOTES
critical_count: 0
important_count: 1
minor_count: 0
reviewed_at: 2026-05-13T00:00:00Z
---

## Critical findings
- _(none)_

## Important findings
- **[line 5]:** synthetic lay-reader important finding for exemplar fixture.

## Minor findings
- _(none)_
```

- [ ] **Step 2: Write the failing test**

Create `skills/review-conductor/tests/test_outcomes_loader.py`:

```python
"""Outcomes loader: load exemplar findings, pick representative samples deterministically."""
from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "synthetic_outcomes" / "sample-pass-1"


def test_load_exemplars_returns_per_persona_findings():
    from scripts.outcomes_loader import load_exemplars
    exemplars = load_exemplars([FIXTURES])
    assert set(exemplars.keys()) == {"gottlieb", "lay-reader"}
    assert len(exemplars["gottlieb"]) >= 1
    assert "synthetic gottlieb critical" in exemplars["gottlieb"][0].text.lower()


def test_pick_findings_seed_stable():
    from scripts.outcomes_loader import load_exemplars, pick_findings
    exemplars = load_exemplars([FIXTURES])
    a = pick_findings(exemplars, per_persona=1, seed=42)
    b = pick_findings(exemplars, per_persona=1, seed=42)
    assert a == b


def test_pick_findings_respects_per_persona_count():
    from scripts.outcomes_loader import load_exemplars, pick_findings
    exemplars = load_exemplars([FIXTURES])
    picked = pick_findings(exemplars, per_persona=1, seed=42)
    for persona_id, findings in picked.items():
        assert len(findings) <= 1


def test_render_few_shot_returns_markdown():
    from scripts.outcomes_loader import load_exemplars, pick_findings, render_few_shot
    exemplars = load_exemplars([FIXTURES])
    picked = pick_findings(exemplars, per_persona=1, seed=42)
    md = render_few_shot("gottlieb", picked)
    assert "Recent findings" in md
    assert "synthetic gottlieb critical" in md.lower()


def test_empty_paths_returns_empty_dict():
    from scripts.outcomes_loader import load_exemplars
    assert load_exemplars([]) == {}
```

- [ ] **Step 3: Run, verify failure**

Expected: `ModuleNotFoundError`.

- [ ] **Step 4: Implement outcomes_loader.py**

Create `skills/review-conductor/scripts/outcomes_loader.py`:

```python
"""Load Outcomes exemplars from book-review/references/outcomes/<exemplar>/ and
render a per-persona few-shot snippet for injection into persona prompts.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path

from .sibling_skills import load_book_review_module


@dataclass(frozen=True)
class ExemplarFinding:
    persona_id: str
    severity: str  # "critical" | "important" | "minor"
    text: str
    source_path: Path


def _parse(path: Path) -> list[ExemplarFinding]:
    dr = load_book_review_module("dispatch_review")
    result = dr.parse_review_report(path)
    out: list[ExemplarFinding] = []
    for f in result.critical:
        out.append(ExemplarFinding(result.persona_id, "critical", f.text, path))
    for f in result.important:
        out.append(ExemplarFinding(result.persona_id, "important", f.text, path))
    for f in result.minor:
        out.append(ExemplarFinding(result.persona_id, "minor", f.text, path))
    return out


def load_exemplars(paths: list[Path]) -> dict[str, list[ExemplarFinding]]:
    """Return persona_id -> list of findings across all given exemplar directories."""
    by_persona: dict[str, list[ExemplarFinding]] = {}
    for base in paths:
        base = Path(base)
        if not base.is_dir():
            continue
        for path in sorted(base.glob("*.md")):
            if path.stem in {"README", "curation-notes"}:
                continue
            try:
                for f in _parse(path):
                    by_persona.setdefault(f.persona_id, []).append(f)
            except (ValueError, KeyError, FileNotFoundError):
                continue
    return by_persona


def pick_findings(
    exemplars: dict[str, list[ExemplarFinding]],
    per_persona: int,
    seed: int = 42,
) -> dict[str, list[ExemplarFinding]]:
    """Deterministically select up to per_persona findings per persona."""
    rng = random.Random(seed)
    picked: dict[str, list[ExemplarFinding]] = {}
    for persona_id, findings in exemplars.items():
        if not findings:
            continue
        ordered = sorted(findings, key=lambda f: (f.severity, f.text))
        rng.shuffle(ordered)
        picked[persona_id] = ordered[:per_persona]
    return picked


def render_few_shot(persona_id: str, picked: dict[str, list[ExemplarFinding]]) -> str:
    """Render the chosen findings as a markdown snippet for prompt injection."""
    findings = picked.get(persona_id, [])
    if not findings:
        return ""
    lines = ["## Recent findings from this rubric", ""]
    for f in findings:
        lines.append(f"- _({f.severity})_ {f.text}")
    return "\n".join(lines)
```

- [ ] **Step 5: Run tests, verify pass**

```bash
cd skills/review-conductor
.venv/Scripts/python.exe -m pytest tests/test_outcomes_loader.py -v
```

Expected: 5 PASS.

- [ ] **Step 6: Commit**

```bash
git add skills/review-conductor/scripts/outcomes_loader.py skills/review-conductor/tests/test_outcomes_loader.py skills/review-conductor/tests/fixtures/synthetic_outcomes/
git commit -m "review-conductor: outcomes_loader reads exemplars + seed-stable picker + few-shot renderer"
```

## Task B9: dispatch_panel.py (TDD)

**Files:**
- Create: `skills/review-conductor/scripts/dispatch_panel.py`
- Test: `skills/review-conductor/tests/test_dispatch_panel.py`

- [ ] **Step 1: Write the failing test**

Create `skills/review-conductor/tests/test_dispatch_panel.py`:

```python
"""dispatch_panel builds dispatch packets via book-review with optional few-shot context."""
from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "synthetic_outcomes" / "sample-pass-1"


def _make_workspace(tmp_path: Path, chapter_id: str = "ch-test") -> Path:
    """Create a minimal workspace with one draft chapter."""
    workspace = tmp_path / "workspace"
    drafts = workspace / "chapters" / "drafts" / chapter_id
    drafts.mkdir(parents=True)
    (drafts / "draft.md").write_text("# test chapter\n\nbody.\n", encoding="utf-8")
    contracts = workspace / "chapters" / "contracts"
    contracts.mkdir(parents=True)
    (contracts / f"{chapter_id}.yaml").write_text(
        "title: Test\npurpose: synthesis\naudience: testers\n",
        encoding="utf-8",
    )
    return workspace


def test_packets_built_for_each_persona(tmp_path):
    from scripts.dispatch_panel import build_packets
    from scripts.load_panel import Panel, PersonaConfig, VerdictConfig, OutcomesConfig, OutputConfig
    panel = Panel(
        panel_id="t", artifact_scope="chapter", description="",
        personas=[
            PersonaConfig(id="gottlieb", severity_gate="gating"),
            PersonaConfig(id="lay-reader", severity_gate="advisory"),
        ],
        verdict=VerdictConfig(hard_gate=False, soft_gate_rule="any_critical_from_gating"),
        outcomes=OutcomesConfig(exemplar_paths=[], per_persona_exemplars=0),
        output=OutputConfig(panel_report_path="x.md", verdict_path="x.json"),
    )
    workspace = _make_workspace(tmp_path)
    packets = build_packets(workspace, "ch-test", panel)
    assert len(packets) == 2
    assert {p.persona_id for p in packets} == {"gottlieb", "lay-reader"}


def test_packets_include_few_shot_when_outcomes_configured(tmp_path):
    from scripts.dispatch_panel import build_packets
    from scripts.load_panel import Panel, PersonaConfig, VerdictConfig, OutcomesConfig, OutputConfig
    panel = Panel(
        panel_id="t", artifact_scope="chapter", description="",
        personas=[PersonaConfig(id="gottlieb", severity_gate="gating")],
        verdict=VerdictConfig(hard_gate=False, soft_gate_rule="any_critical_from_gating"),
        outcomes=OutcomesConfig(
            exemplar_paths=[str(FIXTURES)],
            per_persona_exemplars=1,
        ),
        output=OutputConfig(panel_report_path="x.md", verdict_path="x.json"),
    )
    workspace = _make_workspace(tmp_path)
    packets = build_packets(workspace, "ch-test", panel, outcomes_seed=42)
    assert len(packets) == 1
    assert "Recent findings" in packets[0].prompt
    assert "synthetic gottlieb critical" in packets[0].prompt.lower()


def test_packets_skip_few_shot_when_per_persona_zero(tmp_path):
    from scripts.dispatch_panel import build_packets
    from scripts.load_panel import Panel, PersonaConfig, VerdictConfig, OutcomesConfig, OutputConfig
    panel = Panel(
        panel_id="t", artifact_scope="chapter", description="",
        personas=[PersonaConfig(id="gottlieb", severity_gate="gating")],
        verdict=VerdictConfig(hard_gate=False, soft_gate_rule="any_critical_from_gating"),
        outcomes=OutcomesConfig(
            exemplar_paths=[str(FIXTURES)],
            per_persona_exemplars=0,
        ),
        output=OutputConfig(panel_report_path="x.md", verdict_path="x.json"),
    )
    workspace = _make_workspace(tmp_path)
    packets = build_packets(workspace, "ch-test", panel)
    assert "Recent findings" not in packets[0].prompt
```

- [ ] **Step 2: Run, verify failure**

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement dispatch_panel.py**

Create `skills/review-conductor/scripts/dispatch_panel.py`:

```python
"""Build dispatch packets via book-review.prepare_dispatch_packets, with optional
few-shot injection from the outcomes library.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .load_panel import Panel
from .outcomes_loader import load_exemplars, pick_findings, render_few_shot
from .sibling_skills import load_book_review_module


@dataclass(frozen=True)
class PanelPacket:
    persona_id: str
    persona_display_name: str
    chapter_id: str
    draft_path: Path
    output_path: Path
    prompt: str


def build_packets(
    workspace: Path,
    chapter_id: str,
    panel: Panel,
    outcomes_seed: int = 42,
) -> list[PanelPacket]:
    """Build one PanelPacket per persona configured in the panel."""
    review_pass = load_book_review_module("review_pass")
    persona_ids = [p.id for p in panel.personas]
    br_packets = review_pass.prepare_dispatch_packets(
        workspace, chapter_id, personas=persona_ids,
    )

    # Inject few-shot if outcomes are configured.
    few_shot_by_persona: dict[str, str] = {}
    if panel.outcomes.per_persona_exemplars > 0 and panel.outcomes.exemplar_paths:
        exemplar_paths = [
            Path(p) if Path(p).is_absolute() else Path(workspace).parent / p
            for p in panel.outcomes.exemplar_paths
        ]
        exemplars = load_exemplars(exemplar_paths)
        picked = pick_findings(
            exemplars,
            per_persona=panel.outcomes.per_persona_exemplars,
            seed=outcomes_seed,
        )
        for persona_id in persona_ids:
            snippet = render_few_shot(persona_id, picked)
            if snippet:
                few_shot_by_persona[persona_id] = snippet

    out: list[PanelPacket] = []
    for br_packet in br_packets:
        prompt = br_packet.prompt
        snippet = few_shot_by_persona.get(br_packet.persona_id)
        if snippet:
            prompt = prompt + "\n\n" + snippet + "\n"
        out.append(PanelPacket(
            persona_id=br_packet.persona_id,
            persona_display_name=br_packet.persona_display_name,
            chapter_id=br_packet.chapter_id,
            draft_path=br_packet.draft_path,
            output_path=br_packet.output_path,
            prompt=prompt,
        ))
    return out
```

- [ ] **Step 4: Run tests, verify pass**

```bash
cd skills/review-conductor
.venv/Scripts/python.exe -m pytest tests/test_dispatch_panel.py -v
```

Expected: 3 PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/review-conductor/scripts/dispatch_panel.py skills/review-conductor/tests/test_dispatch_panel.py
git commit -m "review-conductor: dispatch_panel builds packets with optional few-shot injection"
```

## Task B10: aggregate_panel.py (TDD)

**Files:**
- Create: `skills/review-conductor/scripts/aggregate_panel.py`
- Test: `skills/review-conductor/tests/test_aggregate_panel.py`
- Fixtures: `skills/review-conductor/tests/fixtures/synthetic_reviews/`

- [ ] **Step 1: Create fixture reviews**

Create `skills/review-conductor/tests/fixtures/synthetic_reviews/all-clean/gottlieb.md`:

```markdown
---
persona: gottlieb
chapter_id: synth-ch
verdict: APPROVED
critical_count: 0
important_count: 0
minor_count: 0
reviewed_at: 2026-05-13T00:00:00Z
---

## Critical findings
- _(none)_

## Important findings
- _(none)_

## Minor findings
- _(none)_
```

Create `skills/review-conductor/tests/fixtures/synthetic_reviews/all-clean/lay-reader.md`:

```markdown
---
persona: lay-reader
chapter_id: synth-ch
verdict: APPROVED
critical_count: 0
important_count: 0
minor_count: 0
reviewed_at: 2026-05-13T00:00:00Z
---

## Critical findings
- _(none)_

## Important findings
- _(none)_

## Minor findings
- _(none)_
```

Create `skills/review-conductor/tests/fixtures/synthetic_reviews/gating-critical/gottlieb.md`:

```markdown
---
persona: gottlieb
chapter_id: synth-ch
verdict: NEEDS_WORK
critical_count: 1
important_count: 0
minor_count: 0
reviewed_at: 2026-05-13T00:00:00Z
---

## Critical findings
1. **[line 1]:** synthetic gottlieb critical.

## Important findings
- _(none)_

## Minor findings
- _(none)_
```

Create `skills/review-conductor/tests/fixtures/synthetic_reviews/gating-critical/lay-reader.md`:

```markdown
---
persona: lay-reader
chapter_id: synth-ch
verdict: APPROVED
critical_count: 0
important_count: 0
minor_count: 0
reviewed_at: 2026-05-13T00:00:00Z
---

## Critical findings
- _(none)_

## Important findings
- _(none)_

## Minor findings
- _(none)_
```

Create `skills/review-conductor/tests/fixtures/synthetic_reviews/advisory-critical-only/gottlieb.md`:

```markdown
---
persona: gottlieb
chapter_id: synth-ch
verdict: APPROVED
critical_count: 0
important_count: 0
minor_count: 0
reviewed_at: 2026-05-13T00:00:00Z
---

## Critical findings
- _(none)_

## Important findings
- _(none)_

## Minor findings
- _(none)_
```

Create `skills/review-conductor/tests/fixtures/synthetic_reviews/advisory-critical-only/lay-reader.md`:

```markdown
---
persona: lay-reader
chapter_id: synth-ch
verdict: NEEDS_WORK
critical_count: 1
important_count: 0
minor_count: 0
reviewed_at: 2026-05-13T00:00:00Z
---

## Critical findings
1. **[line 1]:** lay-reader critical, advisory-gated.

## Important findings
- _(none)_

## Minor findings
- _(none)_
```

- [ ] **Step 2: Write the failing test**

Create `skills/review-conductor/tests/test_aggregate_panel.py`:

```python
"""aggregate_panel emits verdict.json + panel-review.md and applies per-persona severity gates."""
import json
from pathlib import Path
from shutil import copytree

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "synthetic_reviews"


def _setup_workspace_with_reviews(tmp_path: Path, fixture_name: str, chapter_id: str = "ch-test") -> Path:
    """Stage a workspace at <tmp>/workspace with reviews from the fixture."""
    workspace = tmp_path / "workspace"
    draft_dir = workspace / "chapters" / "drafts" / chapter_id
    draft_dir.mkdir(parents=True)
    (draft_dir / "draft.md").write_text("# test\n", encoding="utf-8")
    copytree(FIXTURES / fixture_name, draft_dir / "reviews")
    return workspace


def _panel(personas: list[tuple[str, str]]):
    from scripts.load_panel import Panel, PersonaConfig, VerdictConfig, OutcomesConfig, OutputConfig
    return Panel(
        panel_id="test", artifact_scope="chapter", description="",
        personas=[PersonaConfig(id=p, severity_gate=g) for p, g in personas],
        verdict=VerdictConfig(hard_gate=False, soft_gate_rule="any_critical_from_gating"),
        outcomes=OutcomesConfig(exemplar_paths=[], per_persona_exemplars=0),
        output=OutputConfig(
            panel_report_path="chapters/drafts/{chapter_id}/panel-review.md",
            verdict_path="chapters/drafts/{chapter_id}/verdict.json",
        ),
    )


def test_verdict_pass_when_all_clean(tmp_path):
    from scripts.aggregate_panel import run_aggregation
    workspace = _setup_workspace_with_reviews(tmp_path, "all-clean")
    panel = _panel([("gottlieb", "gating"), ("lay-reader", "advisory")])
    verdict = run_aggregation(workspace, "ch-test", panel)
    assert verdict["verdict"] == "pass"
    assert verdict["gating_criticals"] == 0
    assert verdict["advisory_criticals"] == 0


def test_verdict_soft_gate_fail_when_gating_critical(tmp_path):
    from scripts.aggregate_panel import run_aggregation
    workspace = _setup_workspace_with_reviews(tmp_path, "gating-critical")
    panel = _panel([("gottlieb", "gating"), ("lay-reader", "advisory")])
    verdict = run_aggregation(workspace, "ch-test", panel)
    assert verdict["verdict"] == "soft-gate-fail"
    assert verdict["gating_criticals"] == 1


def test_verdict_pass_when_only_advisory_critical(tmp_path):
    from scripts.aggregate_panel import run_aggregation
    workspace = _setup_workspace_with_reviews(tmp_path, "advisory-critical-only")
    panel = _panel([("gottlieb", "gating"), ("lay-reader", "advisory")])
    verdict = run_aggregation(workspace, "ch-test", panel)
    assert verdict["verdict"] == "pass"
    assert verdict["gating_criticals"] == 0
    assert verdict["advisory_criticals"] == 1


def test_verdict_json_written_to_workspace(tmp_path):
    from scripts.aggregate_panel import run_aggregation
    workspace = _setup_workspace_with_reviews(tmp_path, "gating-critical")
    panel = _panel([("gottlieb", "gating"), ("lay-reader", "advisory")])
    verdict = run_aggregation(workspace, "ch-test", panel)
    verdict_path = workspace / "chapters" / "drafts" / "ch-test" / "verdict.json"
    assert verdict_path.is_file()
    on_disk = json.loads(verdict_path.read_text(encoding="utf-8"))
    assert on_disk["verdict"] == verdict["verdict"]


def test_panel_review_md_written(tmp_path):
    from scripts.aggregate_panel import run_aggregation
    workspace = _setup_workspace_with_reviews(tmp_path, "gating-critical")
    panel = _panel([("gottlieb", "gating"), ("lay-reader", "advisory")])
    run_aggregation(workspace, "ch-test", panel)
    report = workspace / "chapters" / "drafts" / "ch-test" / "panel-review.md"
    assert report.is_file()
    text = report.read_text(encoding="utf-8")
    assert "synthetic gottlieb critical" in text.lower()
```

- [ ] **Step 3: Run, verify failure**

Expected: `ModuleNotFoundError`.

- [ ] **Step 4: Implement aggregate_panel.py**

Create `skills/review-conductor/scripts/aggregate_panel.py`:

```python
"""Aggregate per-persona review reports under a panel and compute verdict."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .load_panel import Panel
from .sibling_skills import load_book_review_module


def _format_path(template: str, chapter_id: str) -> str:
    return template.replace("{chapter_id}", chapter_id)


def run_aggregation(workspace: Path, chapter_id: str, panel: Panel) -> dict:
    """Read per-persona reports, compute verdict, write verdict.json + panel-review.md.

    Returns the verdict dict.
    """
    workspace = Path(workspace).resolve()
    aggregate_reviews = load_book_review_module("aggregate_reviews")
    aggregated = aggregate_reviews.aggregate_reviews(workspace, chapter_id)

    persona_gates = {p.id: p.severity_gate for p in panel.personas}

    gating_criticals = 0
    advisory_criticals = 0
    per_persona: dict[str, dict[str, int]] = {}

    # Re-read per-persona reports to get per-persona severity breakdown.
    dispatch_review = load_book_review_module("dispatch_review")
    reviews_dir = workspace / "chapters" / "drafts" / chapter_id / "reviews"
    for path in sorted(reviews_dir.glob("*.md")):
        try:
            r = dispatch_review.parse_review_report(path)
        except (ValueError, KeyError):
            continue
        c = len(r.critical)
        i = len(r.important)
        m = len(r.minor)
        per_persona[r.persona_id] = {"critical": c, "important": i, "minor": m}
        gate = persona_gates.get(r.persona_id, "advisory")
        if gate == "gating":
            gating_criticals += c
        else:
            advisory_criticals += c

    if panel.verdict.hard_gate:
        # Hard gate hook reserved for future use; v1 disables.
        result = "hard-gate-fail" if False else None  # placeholder; never fires
    else:
        result = None

    if result is None:
        rule = panel.verdict.soft_gate_rule
        if rule == "any_critical_from_gating":
            result = "soft-gate-fail" if gating_criticals > 0 else "pass"
        elif rule == "any_critical":
            result = "soft-gate-fail" if (gating_criticals + advisory_criticals) > 0 else "pass"
        elif rule == "majority_critical":
            total = len(panel.personas)
            critical_personas = sum(
                1 for stats in per_persona.values() if stats["critical"] > 0
            )
            result = "soft-gate-fail" if critical_personas > total / 2 else "pass"
        else:
            result = "pass"

    report_path = _format_path(panel.output.panel_report_path, chapter_id)
    verdict_rel_path = _format_path(panel.output.verdict_path, chapter_id)

    verdict = {
        "panel_id": panel.panel_id,
        "artifact": {"type": "chapter", "id": chapter_id},
        "verdict": result,
        "gating_criticals": gating_criticals,
        "advisory_criticals": advisory_criticals,
        "per_persona": per_persona,
        "report_path": report_path,
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }

    (workspace / verdict_rel_path).write_text(
        json.dumps(verdict, indent=2), encoding="utf-8",
    )
    # The panel-review.md is produced by book-review's aggregate_reviews; we
    # already have it on disk at chapters/drafts/<chapter>/persona-review.md.
    # Rename for the conductor convention if the panel.output.panel_report_path
    # differs from the book-review default.
    source = aggregated.report_path
    target = workspace / report_path
    if source.resolve() != target.resolve():
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    return verdict
```

- [ ] **Step 5: Run tests, verify pass**

```bash
cd skills/review-conductor
.venv/Scripts/python.exe -m pytest tests/test_aggregate_panel.py -v
```

Expected: 5 PASS.

- [ ] **Step 6: Commit**

```bash
git add skills/review-conductor/scripts/aggregate_panel.py skills/review-conductor/tests/test_aggregate_panel.py skills/review-conductor/tests/fixtures/synthetic_reviews/
git commit -m "review-conductor: aggregate_panel with per-persona severity gates + verdict.json"
```

## Task B11: conductor.py (public entrypoint, integration test)

**Files:**
- Create: `skills/review-conductor/scripts/conductor.py`
- Test: `skills/review-conductor/tests/test_conductor_integration.py`

- [ ] **Step 1: Write the failing integration test**

Create `skills/review-conductor/tests/test_conductor_integration.py`:

```python
"""End-to-end conductor: build packets, run stubbed dispatcher writes synthetic reviews, aggregate."""
from pathlib import Path
from shutil import copytree


FIXTURES = Path(__file__).resolve().parent / "fixtures" / "synthetic_reviews"


def _stub_dispatcher(reviews_src: Path):
    """Returns a dispatcher callable that, instead of running a subagent, copies
    pre-canned per-persona review markdown into the packet's output_path."""
    def dispatcher(packet):
        src = reviews_src / f"{packet.persona_id}.md"
        if src.is_file():
            packet.output_path.parent.mkdir(parents=True, exist_ok=True)
            packet.output_path.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    return dispatcher


def _make_workspace(tmp_path: Path, chapter_id: str = "ch-test") -> Path:
    workspace = tmp_path / "workspace"
    drafts = workspace / "chapters" / "drafts" / chapter_id
    drafts.mkdir(parents=True)
    (drafts / "draft.md").write_text("# test chapter\n\nbody.\n", encoding="utf-8")
    contracts = workspace / "chapters" / "contracts"
    contracts.mkdir(parents=True)
    (contracts / f"{chapter_id}.yaml").write_text(
        "title: Test\npurpose: synthesis\naudience: testers\n",
        encoding="utf-8",
    )
    return workspace


def test_run_panel_pass_verdict(tmp_path):
    from scripts.conductor import run_panel
    panel_yaml = Path(__file__).resolve().parent / "fixtures" / "panel-default.yaml"
    workspace = _make_workspace(tmp_path)
    verdict = run_panel(
        workspace=workspace,
        chapter_id="ch-test",
        panel_path=panel_yaml,
        dispatcher=_stub_dispatcher(FIXTURES / "all-clean"),
    )
    assert verdict["verdict"] == "pass"


def test_run_panel_soft_gate_fail(tmp_path):
    from scripts.conductor import run_panel
    panel_yaml = Path(__file__).resolve().parent / "fixtures" / "panel-default.yaml"
    workspace = _make_workspace(tmp_path)
    verdict = run_panel(
        workspace=workspace,
        chapter_id="ch-test",
        panel_path=panel_yaml,
        dispatcher=_stub_dispatcher(FIXTURES / "gating-critical"),
    )
    assert verdict["verdict"] == "soft-gate-fail"
    assert verdict["gating_criticals"] >= 1
```

Create the fixture panel `skills/review-conductor/tests/fixtures/panel-default.yaml`:

```yaml
panel_id: test-panel
artifact_scope: chapter
description: Test fixture panel with two personas.
personas:
  - id: gottlieb
    severity_gate: gating
  - id: lay-reader
    severity_gate: advisory
verdict:
  hard_gate: false
  soft_gate_rule: any_critical_from_gating
outcomes:
  exemplar_paths: []
  per_persona_exemplars: 0
output:
  panel_report_path: "chapters/drafts/{chapter_id}/panel-review.md"
  verdict_path: "chapters/drafts/{chapter_id}/verdict.json"
```

- [ ] **Step 2: Run, verify failure**

Expected: `ModuleNotFoundError` on `scripts.conductor`.

- [ ] **Step 3: Implement conductor.py**

Create `skills/review-conductor/scripts/conductor.py`:

```python
"""Public entrypoint: run_panel(workspace, chapter_id, panel_path, dispatcher) -> verdict dict.

The dispatcher callable is invoked once per packet. In production, the caller
provides a dispatcher that issues a Task-tool call for each persona subagent;
in tests, the dispatcher writes a pre-canned review markdown to the packet's
output_path.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from .aggregate_panel import run_aggregation
from .dispatch_panel import PanelPacket, build_packets
from .load_panel import load_panel


def run_panel(
    workspace: Path,
    chapter_id: str,
    panel_path: Path,
    dispatcher: Optional[Callable[[PanelPacket], None]] = None,
) -> dict:
    workspace = Path(workspace).resolve()
    panel = load_panel(panel_path)
    packets = build_packets(workspace, chapter_id, panel)
    if dispatcher is not None:
        for packet in packets:
            dispatcher(packet)
    return run_aggregation(workspace, chapter_id, panel)
```

- [ ] **Step 4: Run tests, verify pass**

```bash
cd skills/review-conductor
.venv/Scripts/python.exe -m pytest tests/test_conductor_integration.py -v
```

Expected: 2 PASS.

- [ ] **Step 5: Run the full review-conductor test suite**

```bash
cd skills/review-conductor
.venv/Scripts/python.exe -m pytest tests/ -q
```

Expected: all PASS. Approximate count: 5 + 5 + 3 + 3 + 5 + 2 = 23 tests.

- [ ] **Step 6: Commit**

```bash
git add skills/review-conductor/scripts/conductor.py skills/review-conductor/tests/test_conductor_integration.py skills/review-conductor/tests/fixtures/panel-default.yaml
git commit -m "review-conductor: public run_panel entrypoint + integration tests"
```

## Task B12: SKILL.md + README.md

**Files:**
- Create: `skills/review-conductor/SKILL.md`
- Create: `skills/review-conductor/README.md`

- [ ] **Step 1: Create SKILL.md**

Create `skills/review-conductor/SKILL.md`:

```markdown
---
name: review-conductor
description: Orchestrate configurable multi-persona editorial review panels over book-review. Use when user says "run the panel", "review chapter with the conductor", "run the seven-persona panel", "soft-gate this chapter via review-conductor". Loads a panel YAML config, calls book-review's dispatch primitives, applies per-persona severity gates (gating vs advisory), emits panel-review.md + verdict.json. Do NOT use for source ingestion (use book-knowledge), prose-only style rewrites (use russellian-style), chapter drafting (use book-compose), persona definition (use book-review).
license: MIT
metadata:
  author: charles-hoskinson
  version: 0.1.0
  category: writing
  workspace-aware: true
  invokes: book-review
---

# review-conductor

Panel-orchestration sibling for `book-review`. Owns multi-panel review coordination: load a YAML panel config, dispatch the configured personas through book-review's primitives, apply per-persona severity gates, emit a verdict.

## What it owns

- `panels/*.yaml` — declarative panel configs (which personas, which severity rule per persona, which output paths).
- `assets/panel-config.schema.json` and `assets/verdict.schema.json` — schema validation for the above.
- `scripts/load_panel.py` — YAML loader + schema validation.
- `scripts/dispatch_panel.py` — packet construction; few-shot injection from Outcomes exemplars.
- `scripts/aggregate_panel.py` — per-persona severity gate; verdict computation; report rendering.
- `scripts/outcomes_loader.py` — loads exemplars from `book-review/references/outcomes/<exemplar>/`.
- `scripts/conductor.py` — public entrypoint `run_panel(workspace, chapter_id, panel_path, dispatcher)`.

## What it does NOT own

- Persona definitions — owned by `book-review/personas/`.
- Subagent dispatch infrastructure — caller-provided dispatcher callable.
- Sentence-grain prose discipline — `russellian-style`.
- Source ingestion or claim ledger — `book-knowledge`.
- Post-build defect gating — `book-qa`.

## Panel configuration

A panel is a YAML file at `panels/<panel-id>.yaml`. The chapter-default panel is:

```yaml
panel_id: chapter-default
artifact_scope: chapter
personas:
  - id: gottlieb
    severity_gate: gating
  - id: lay-reader
    severity_gate: advisory
  - id: domain-expert
    severity_gate: gating
  - id: copyeditor
    severity_gate: gating
  - id: enjoyment-reader
    severity_gate: advisory
  - id: ai-slop-detector
    severity_gate: gating
    delegates_to: humanizer
  - id: first-time-visitor
    severity_gate: advisory
verdict:
  hard_gate: false
  soft_gate_rule: any_critical_from_gating
outcomes:
  exemplar_paths:
    - ../book-review/references/outcomes/readme-pass-2026-05-13/
  per_persona_exemplars: 1
output:
  panel_report_path: "chapters/drafts/{chapter_id}/panel-review.md"
  verdict_path: "chapters/drafts/{chapter_id}/verdict.json"
```

`severity_gate: gating` means a critical finding from this persona soft-gates release; `advisory` means it surfaces but does not gate. `soft_gate_rule` selects how the per-persona criticals roll up to a panel-level verdict (`any_critical_from_gating` is the default).

## Usage

```python
from review_conductor.conductor import run_panel
from pathlib import Path

verdict = run_panel(
    workspace=Path("/path/to/workspace"),
    chapter_id="ch-01",
    panel_path=Path("panels/chapter-default.yaml"),
    dispatcher=None,  # default: caller dispatches via Task tool
)
```

The `dispatcher` callable receives one `PanelPacket` per persona and is responsible for issuing the actual subagent invocation. The conductor writes `verdict.json` + `panel-review.md` to the workspace and returns the verdict dict.

## Composes with

- `book-review` — imports `persona_loader`, `dispatch_review`, `aggregate_reviews`, `review_pass` via `sibling_skills.load_book_review_module`.
- `humanizer` — the `ai-slop-detector` persona delegates to humanizer's catalog.
- `book-compose` — Stage 7 invokes the conductor instead of `book-review.run_review_pass` directly.

## Tests

```bash
.venv/Scripts/python.exe -m pytest tests/ -q
```

Twenty-three tests across schema validation, panel loading, sibling loading, outcomes selection, dispatch construction, aggregation, and a stubbed-dispatcher integration test.
```

- [ ] **Step 2: Create README.md**

Create `skills/review-conductor/README.md`:

```markdown
# review-conductor

Panel orchestration over `book-review`. Reads a YAML panel config, runs the configured personas through `book-review`'s dispatch primitives, applies a per-persona severity gate, and emits a verdict.

See `SKILL.md` for the full description.
```

- [ ] **Step 3: Commit**

```bash
git add skills/review-conductor/SKILL.md skills/review-conductor/README.md
git commit -m "review-conductor: SKILL.md + README"
```

## Task B13: Anthropic compliance test

**Files:**
- Create: `skills/review-conductor/tests/test_anthropic_compliance.py`

- [ ] **Step 1: Write the test**

Create `skills/review-conductor/tests/test_anthropic_compliance.py`:

```python
"""Anthropic skill-description compliance tests.

The SKILL.md description must:
- be a single paragraph in metadata.description
- include trigger phrases (when to use)
- include negative triggers (when NOT to use)
"""
import re
from pathlib import Path

import yaml

SKILL_MD = Path(__file__).resolve().parent.parent / "SKILL.md"


def _frontmatter():
    text = SKILL_MD.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    assert m, "SKILL.md missing frontmatter"
    return yaml.safe_load(m.group(1))


def test_skill_md_has_required_fields():
    meta = _frontmatter()
    assert meta["name"] == "review-conductor"
    assert meta["license"] == "MIT"
    assert "description" in meta
    assert meta["metadata"]["workspace-aware"] is True


def test_description_contains_positive_triggers():
    meta = _frontmatter()
    desc = meta["description"].lower()
    for phrase in ["run the panel", "review chapter", "review-conductor"]:
        assert phrase in desc, f"missing positive trigger: {phrase}"


def test_description_contains_negative_triggers():
    meta = _frontmatter()
    desc = meta["description"].lower()
    assert "do not use" in desc
    for skill in ["book-knowledge", "russellian-style", "book-compose", "book-review"]:
        assert skill in desc, f"missing negative-trigger reference: {skill}"
```

- [ ] **Step 2: Run, verify pass**

```bash
cd skills/review-conductor
.venv/Scripts/python.exe -m pytest tests/test_anthropic_compliance.py -v
```

Expected: 3 PASS.

- [ ] **Step 3: Commit**

```bash
git add skills/review-conductor/tests/test_anthropic_compliance.py
git commit -m "review-conductor: Anthropic compliance tests for SKILL.md"
```

## Task B14: book-compose switch

**Files:**
- Modify: `skills/book-compose/scripts/persona_review_pass.py`
- Modify: `skills/book-compose/SKILL.md`

- [ ] **Step 1: Read the existing persona_review_pass.py**

Run:

```bash
cat skills/book-compose/scripts/persona_review_pass.py | head -80
```

Look for where `run_review_pass` from book-review is called.

- [ ] **Step 2: Modify the call site**

The exact change depends on the current contents. Locate the line that invokes book-review's review pass and replace it with a call to `review_conductor.run_panel`. The replacement should look like:

```python
# Before (book-review direct call):
# from .sibling_skills import load_book_review_module
# review_pass = load_book_review_module("review_pass")
# result = review_pass.run_review_pass(workspace, chapter_id, dispatcher=dispatcher)

# After (review-conductor delegation):
from .sibling_skills import load_review_conductor_module
conductor = load_review_conductor_module("conductor")
panel_path = (
    workspace / "qa" / "panels" / "chapter-default.yaml"
    if (workspace / "qa" / "panels" / "chapter-default.yaml").is_file()
    else Path.home() / ".claude" / "skills" / "review-conductor" / "panels" / "chapter-default.yaml"
)
verdict = conductor.run_panel(
    workspace=workspace,
    chapter_id=chapter_id,
    panel_path=panel_path,
    dispatcher=dispatcher,
)
```

If `book-compose/scripts/sibling_skills.py` does not yet have a `load_review_conductor_module` helper, add one matching the existing pattern. The helper body is:

```python
_RC_PACKAGE_ALIAS = "_review_conductor_scripts"

def review_conductor_root() -> Path:
    return _resolve("review-conductor")

def load_review_conductor_module(name: str) -> types.ModuleType:
    return _load_module(_RC_PACKAGE_ALIAS, review_conductor_root() / "scripts", name)
```

- [ ] **Step 3: Update the matching test**

In `skills/book-compose/tests/test_persona_review_pass.py`, update mocks to expect the conductor invocation. The exact change depends on the test's current shape; the principle is: where it patched `book-review.run_review_pass`, it now patches `review_conductor.run_panel`. The test's effective behaviour (dispatcher injection, verdict consumption) is unchanged.

- [ ] **Step 4: Run the book-compose tests**

```bash
cd skills/book-compose
.venv/Scripts/python.exe -m pytest tests/test_persona_review_pass.py -v
```

Expected: PASS.

- [ ] **Step 5: Update book-compose/SKILL.md Stage-7 description**

Modify the Stage-7 description in `skills/book-compose/SKILL.md`. Replace the paragraph mentioning the persona-review step with:

```markdown
7. **Personas** — `persona_review_pass.prepare_packets` delegates to `review-conductor.run_panel` with the `chapter-default` panel (seven personas: Gottlieb, Lay Reader, Domain Expert, Copyeditor, Enjoyment Reader, AI-slop Detector, First-Time Visitor). One Task subagent per persona; the conductor's `aggregate_panel` produces `panel-review.md` and `verdict.json`. Soft-gate when `verdict.verdict == "soft-gate-fail"`.
```

- [ ] **Step 6: Run the full book-compose test suite**

```bash
cd skills/book-compose
.venv/Scripts/python.exe -m pytest tests/ -q
```

Expected: all PASS.

- [ ] **Step 7: Commit**

```bash
git add skills/book-compose/scripts/persona_review_pass.py skills/book-compose/scripts/sibling_skills.py skills/book-compose/SKILL.md skills/book-compose/tests/test_persona_review_pass.py
git commit -m "book-compose: route persona review through review-conductor (chapter-default panel)"
```

## Task B15: Full-suite test sweep, push, open PR-B

- [ ] **Step 1: Run every affected skill's test suite**

```bash
cd skills/review-conductor && .venv/Scripts/python.exe -m pytest tests/ -q && cd ../..
cd skills/book-review && .venv/Scripts/python.exe -m pytest tests/ -q && cd ../..
cd skills/book-compose && .venv/Scripts/python.exe -m pytest tests/ -q && cd ../..
```

Expected: every suite PASSING.

- [ ] **Step 2: Push the branch**

```bash
git push -u origin feat/review-conductor
```

- [ ] **Step 3: Open the PR**

```bash
gh pr create --repo CharlesHoskinson/russellian-book-suite \
  --head feat/review-conductor \
  --base main \
  --title "Add review-conductor skill + switch book-compose to seven-persona panel" \
  --body "$(cat <<'EOF'
## Summary

Adds the \`review-conductor\` skill (sibling to \`book-review\`) that owns multi-panel editorial review orchestration. Switches \`book-compose\` Stage 7 from \`book-review.run_review_pass\` directly to \`review-conductor.run_panel(panel_id="chapter-default", ...)\`.

The chapter-default panel includes all seven personas (Gottlieb, Lay Reader, Domain Expert, Copyeditor, Enjoyment Reader, AI-slop Detector, First-Time Visitor) with per-persona severity gates: Gottlieb, Domain Expert, Copyeditor, and AI-slop Detector are gating; Lay Reader, Enjoyment Reader, and First-Time Visitor are advisory.

Outcomes exemplars from \`book-review/references/outcomes/readme-pass-2026-05-13/\` (added in PR #11) are injected into persona prompts as 1 per persona by default.

## Reference

- Spec at \`docs/specs/2026-05-13-review-conductor-design.md\` (PR #10)
- Depends on PR #11 (personas + outcomes seed) being merged.

## Test plan

- [x] \`pytest skills/review-conductor/tests/ -q\` — 23 passing (schema, panel-loader, sibling-loader, outcomes, dispatch, aggregate, integration, Anthropic compliance)
- [x] \`pytest skills/book-review/tests/ -q\` — green (no change)
- [x] \`pytest skills/book-compose/tests/ -q\` — green (Stage-7 mock updated)
EOF
)"
```

- [ ] **Step 4: Verify the PR opened**

```bash
gh pr list --repo CharlesHoskinson/russellian-book-suite --state open --json number,title,headRefName --jq '.[] | select(.headRefName == "feat/review-conductor")'
```

Expected: one row.

---

# Self-review

(Self-review by the planner; not an execution step.)

**Spec coverage:** Every section of `docs/specs/2026-05-13-review-conductor-design.md` is implemented:
- Problem and Scope — addressed across PR-A (personas + outcomes) and PR-B (conductor + book-compose switch).
- Architecture (the diagram) — implemented by `conductor.py` calling `build_packets` then `run_aggregation`.
- Components — every component named in the spec has a task.
- Panel config schema — Task B3.
- Outcomes exemplar library — Tasks A5-A7.
- Severity gate logic — Task B10.
- Public API `run_panel(workspace, chapter_id, panel_path, dispatcher)` — Task B11.
- Composition with humanizer (via persona prompt delegation, no programmatic call) — encoded in `ai-slop-detector.md` content.
- Migration (two PRs, A independent of B) — preserved in plan structure.
- Invariants — five contracts; tests in B7 (sibling loader), B10 (no writes outside drafts/<chapter-id>/), and the public API surface (conductor.py).

**Placeholder scan:** none. Every step contains executable content. The one templated path (`{chapter_id}` in panel output config) is documented in the schema and replaced by `_format_path` in `aggregate_panel.py`.

**Type consistency:** `Panel`, `PersonaConfig`, `VerdictConfig`, `OutcomesConfig`, `OutputConfig`, `PanelPacket`, `ExemplarFinding` are defined where introduced and used by name in subsequent tasks. The verdict dict shape is consistent between `aggregate_panel.run_aggregation` return and the integration test assertions.

**Risk: Task B14 depends on the current shape of `book-compose/scripts/persona_review_pass.py`,** which the plan does not embed verbatim. The implementer must read that file before editing. The plan acknowledges this explicitly in B14 Step 1.

---

## Execution Handoff

Plan complete and saved to `docs/plans/2026-05-13-review-conductor-and-personas.md`. Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration with two-stage review.

**2. Inline Execution** — Execute tasks in this session using `superpowers:executing-plans`, batch execution with checkpoints for review.

Which approach?
