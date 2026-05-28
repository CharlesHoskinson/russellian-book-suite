# Russell pass on the agentic-civilizations paper — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Recast `C:\agenticcivthoughts\Agentic_Civilizations_Research_v2.md` in Bertrand Russell's analytic prose in place, strip every epistemic-status tag and AI tell, and pass it through the `russellian-style` linters and corpus-distance scorer.

**Architecture:** First strip the tags and AI scaffolding mechanically. Then rewrite the prose section by section against the russellian-style guide, system prompt, and Russell corpus, carrying certainty-versus-conjecture in the prose. Then drive the negative linters to zero and pull the corpus-distance (Burrows delta) toward the centre of Russell's range. Then regenerate the PDF and commit. All claims, `[n]` citations, the References section, the Agora Scale table, and the nine-section structure are preserved.

**Tech Stack:** the `russellian-style` skill (Python linters + Burrows-delta scorer, run from `C:\russellian-book-suite\skills\russellian-style` with its `.venv\Scripts\python.exe`); `markdown` + `xhtml2pdf` for the PDF.

**Branch:** `russell-pass-agentic-civ` in the suite (spec committed there). The paper rewrite commits land in `C:\agenticcivthoughts` on its `master`. **Commit style in BOTH repos: terse, human, no AI attribution, no Co-Authored-By line.**

---

## Reference commands (used throughout)

Run all skill tools from the skill directory with its venv:

```bash
cd /c/russellian-book-suite/skills/russellian-style
PY=.venv/Scripts/python.exe
PAPER="C:\agenticcivthoughts\Agentic_Civilizations_Research_v2.md"

# Full negative style pass -> writes a report:
$PY -m scripts.style_pass_report "$PAPER" "C:\agenticcivthoughts\style-pass-report.md"

# Corpus distance (lower = closer to Russell; stay within p10..p90, aim toward p50):
$PY -m scripts.score_russell_delta "$PAPER"

# Vitality (run individually; JSON findings):
$PY -m scripts.lint_paragraph_motion "$PAPER"
$PY -m scripts.lint_ai_staccato "$PAPER"
$PY -m scripts.lint_burstiness "$PAPER"
$PY -m scripts.lint_concrete_instance_density "$PAPER"
$PY -m scripts.lint_epistemic_precision "$PAPER"

# Individual negative linters take the file path as the one argument:
$PY -m scripts.lint_hedges "$PAPER"   # also lint_passive_voice, lint_signal_density, lint_parallel_structure, lint_sentence_rhythm, lint_listicle_abstract
```

Baseline (before any work), for reference: style_pass_report total 45 (active-voice 21, no-hedging 15, signal-density 6, listicle-anaphora 1, parallel-structure 1, rhythm-uniform-length 1); Burrows delta 0.785 (band p10 0.621 / p50 0.685 / p90 0.786, "within Russell's range"); paragraph-motion flat_proportion 0.779; staccato clean.

## The Russell rules the rewrite enforces (from `references/russellian-style-guide.md`)

Read `references/russellian-style-guide.md`, `references/russellian-vitality-guide.md`, and the rewrite system prompt `assets/system-prompts/technical-exposition.md` before rewriting. The operative rules:

- State facts, not persuasion; strip superlatives and promotional inflection.
- No vague hedging. Exact uncertainty is welcome ("on the evidence so far, X holds; Y is unresolved"); vague uncertainty ("it seems", "arguably", "somewhat", "may perhaps") is not. Render contrastive "rather than" as "not X but Y".
- Shortest precise word over the Latinate one. Strip adjectives and adverbs; earn each one.
- One claim per sentence; sentence ceiling 30 words; atomize past that. Compound sentences allowed when each clause is under 12 words, shares a subject, and the connective is a true logical operator.
- Active voice, actor explicit.
- No "obviously", "clearly", "of course", "here we will explain", "hope this helps".
- Vary rhythm; avoid four same-shape sentences in a row.
- Use the concession-turn move where prose is a flat run of assertions: state the common view, grant what is true, draw the distinction it hides, state the consequence. (This is what lowers paragraph-motion flat_proportion and the Burrows delta.)
- Keep the certainty/conjecture distinction in words: where the paper now tags `(Speculative)`, write the turn ("Here I leave what is known for what may be guessed"); where it tags `(Grounded)`, state the fact with its `[n]` citation.

---

## File Structure

- Modify: `C:\agenticcivthoughts\Agentic_Civilizations_Research_v2.md` (the rewrite, in place).
- Create: `C:\agenticcivthoughts\style-pass-report.md` (the style-pass artifact).
- Regenerate: `C:\agenticcivthoughts\Agentic_Civilizations_Research_v2.pdf`.
- Create then delete: `C:\agenticcivthoughts\_build_v2.py` (PDF helper).
- Already committed in the suite: the spec at `docs/specs/2026-05-27-russell-pass-agentic-civilizations-design.md`; this plan at `docs/plans/2026-05-27-russell-pass-agentic-civilizations.md`.

---

### Task 1: Strip the epistemic tags and AI scaffolding

**Files:** Modify `Agentic_Civilizations_Research_v2.md`.

- [ ] **Step 1: Inventory every tag and scaffold token**

Run:
```bash
cd /c/agenticcivthoughts && grep -nE "\(Grounded\)|\(Framework\)|\(Speculative\)|\breported\b|Epistemic status and legend|\| Status \|" Agentic_Civilizations_Research_v2.md
```
Expected: matches for the legend heading + its three bullets + sourcing note (around lines 7 to 15); the Terminology table `Status` column header and its Grounded/Framework cells; the `(Speculative)` demonstrator cells in the Agora Scale table (ACS-4, ACS-5 rows); and inline `(Grounded)/(Framework)/(Speculative)` tokens in sections 1, 3, 4, 5, 6, 7.

- [ ] **Step 2: Delete the "Epistemic status and legend" section**

Remove the entire `## Epistemic status and legend` section (its heading, the three legend bullets, and the sourcing-note paragraph) and the `---` that follows it. Preserve the one substantive caveat it carried by folding it into Section 6 prose during Task 3: the 100-agents-per-human figure rests on a press report (Fortune [21]), not the GTC transcript.

- [ ] **Step 3: Remove the Terminology Status column**

In Section 2, change the table header `| Term | Definition | Status |` and its separator to two columns `| Term | Definition |`, and delete the third cell (Grounded/Framework) from every row. Keep all terms and definitions.

- [ ] **Step 4: Neutralise the Agora Scale table tag cells**

In the Section 3 table, replace the `(Speculative)` demonstrator cell for the ACS-4 (Polis) and ACS-5 (Cosmopolis) rows with `none yet`. Keep the rest of the table verbatim.

- [ ] **Step 5: Strip every remaining inline tag token**

Remove every inline `(Grounded)`, `(Framework)`, `(Speculative)`, and `*reported*`/`reported` status label from the prose and headings. Where deleting the token leaves an ungrammatical sentence, leave the sentence minimally readable for now; Task 2 to 4 will rewrite it and carry the epistemic sense in prose.

- [ ] **Step 6: Verify the strip is complete**

Run:
```bash
cd /c/agenticcivthoughts && grep -nE "\(Grounded\)|\(Framework\)|\(Speculative\)|Epistemic status and legend|\| Status \|" Agentic_Civilizations_Research_v2.md; echo "tags-gone-if-empty"
```
Expected: NO matches before `tags-gone-if-empty`. (A bare word "reported" used as an ordinary verb may remain; only the *status-label* use is removed.)

- [ ] **Step 7: Commit the strip**

```bash
cd /c/agenticcivthoughts && git add Agentic_Civilizations_Research_v2.md && git commit -m "Strip epistemic-status tags and legend from the agentic-civ paper"
```

---

### Task 2: Russell rewrite, sections 1 to 3

**Files:** Modify `Agentic_Civilizations_Research_v2.md` (Section 1 Abstract and thesis, Section 2 Terminology, Section 3 the eras including the "What each era looks and feels like" subsection).

- [ ] **Step 1: Load the rules**

Read `C:\russellian-book-suite\skills\russellian-style\references\russellian-style-guide.md`, `references\russellian-vitality-guide.md`, and `assets\system-prompts\technical-exposition.md`. Optionally retrieve an anchoring Russell passage for a hard paragraph:
```bash
cd /c/russellian-book-suite/skills/russellian-style && .venv/Scripts/python.exe -m scripts.retrieve_corpus_anchor "the difference between what is known and what is guessed"
```

- [ ] **Step 2: Rewrite Section 1 (Abstract and thesis)**

Recast every sentence in Russell's voice. State the governing axiom in the first paragraph (the substrate thesis: a crowd of agents becomes a civilization only when a shared layer lets them prove identity, remember, transact without leaking strategy, and agree on state). Keep the four thesis claims and their `[n]` citations, but as full declarative sentences, not bold-labelled list items; if a numbered list survives, each item is a complete claim, not an abstract-noun stub (rule 27). Carry the conjectural status of the 100-agents forecast in prose ("Huang projects, and I have only the press report of it, ...").

- [ ] **Step 3: Rewrite Section 2 (Terminology)**

Tighten each definition to the shortest precise form. Active voice. Define the term before any clause that uses another defined term. The two-column table stays.

- [ ] **Step 4: Rewrite Section 3 (the eras)**

Rewrite the prose around the Agora Scale table: the two-lenses paragraph, the hard-transitions paragraph, the early-versus-mature paragraph, and the six "looks and feels like" blocks. Keep the table and the `[n]` citations. For the forward rungs (Polis, Cosmopolis), mark the turn from knowledge to conjecture in prose rather than with a tag. Apply the concession-turn move to at least the Agora and Polis blocks so they are not flat assertion runs.

- [ ] **Step 5: Lint sections 1 to 3 and check drift**

Run the full pass and the delta:
```bash
cd /c/russellian-book-suite/skills/russellian-style && PY=.venv/Scripts/python.exe && PAPER="C:\agenticcivthoughts\Agentic_Civilizations_Research_v2.md"
$PY -m scripts.style_pass_report "$PAPER" "C:\agenticcivthoughts\style-pass-report.md" 2>&1 | tail -3
$PY -m scripts.score_russell_delta "$PAPER"
```
Expected: total findings falling toward zero versus the 45 baseline; delta moving below 0.785 toward 0.685; verdict stays "within Russell's range". Fix any active-voice / hedging finding that lands in sections 1 to 3 before continuing.

- [ ] **Step 6: Commit**

```bash
cd /c/agenticcivthoughts && git add Agentic_Civilizations_Research_v2.md && git commit -m "Russell pass: sections 1 to 3"
```

---

### Task 3: Russell rewrite, sections 4 to 6

**Files:** Modify `Agentic_Civilizations_Research_v2.md` (Section 4 Capabilities, Section 5 Midnight City, Section 6 OpenClaw and Nvidia).

- [ ] **Step 1: Rewrite Section 4 (Capabilities)**

Recast the prose around the capability table; keep the table and `[n]` citations. The sentence "The capabilities compose ..." becomes a clean derivation: state what each capability is, then that they interlock on shared identifiers.

- [ ] **Step 2: Rewrite Section 5 (Midnight City)**

Recast the four bold-led paragraphs. Keep the quoted strings exactly as quoted (e.g., "holds a real crypto wallet", "a row in a database", "nothing is on rails") with their `[n]` citations; quotations are empirical evidence and are not rewritten. The bold lead-ins ("The disclosure modes are an instrument", etc.) may stay as paragraph topic sentences if each reads as a claim, not a label. Fold the "honest limits" content in as Russell's plain statement of what the demonstration does not yet prove.

- [ ] **Step 3: Rewrite Section 6 (OpenClaw and Nvidia)**

Recast the three paragraphs. Keep every quoted phrase and `[n]` citation. Place the press-report caveat for the 100-to-1 figure here in prose if it was not already placed in Section 1.

- [ ] **Step 4: Lint sections 4 to 6 and check drift**

```bash
cd /c/russellian-book-suite/skills/russellian-style && PY=.venv/Scripts/python.exe && PAPER="C:\agenticcivthoughts\Agentic_Civilizations_Research_v2.md"
$PY -m scripts.style_pass_report "$PAPER" "C:\agenticcivthoughts\style-pass-report.md" 2>&1 | tail -3
$PY -m scripts.score_russell_delta "$PAPER"
```
Expected: findings continuing to fall; delta continuing toward 0.685, within range. Fix section 4 to 6 findings before continuing.

- [ ] **Step 5: Commit**

```bash
cd /c/agenticcivthoughts && git add Agentic_Civilizations_Research_v2.md && git commit -m "Russell pass: sections 4 to 6"
```

---

### Task 4: Russell rewrite, sections 7 to 9

**Files:** Modify `Agentic_Civilizations_Research_v2.md` (Section 7 failure modes, Section 8 convergent accountability, Section 9 goals).

- [ ] **Step 1: Rewrite Section 7 (Emergent behaviors and failure modes)**

Recast the prose; keep the quoted FASA vocabulary ("prompt injection-driven Remote Code Execution (RCE), sequential tool attack chains, context amnesia, and supply chain contamination") and `[n]` citations verbatim. The closing "principle" paragraph is a strong Russell unit already in spirit; tighten it.

- [ ] **Step 2: Rewrite Section 8 (Convergent accountability)**

The five-item bullet list must have parallel grammatical openings (rule 19): make every bullet open the same way (each names a system, then states what boundary it places, in the same grammatical shape). Keep the `[n]` citations.

- [ ] **Step 3: Rewrite Section 9 (Goals)**

Recast the goals prose. State the teleological position ("bounded civic autonomy, not immediate autopoiesis") as an earned conclusion. Keep the `[n]` citations and the Polis/Cosmopolis distinction, the latter carried in prose, not a tag.

- [ ] **Step 4: Lint sections 7 to 9 and check drift**

```bash
cd /c/russellian-book-suite/skills/russellian-style && PY=.venv/Scripts/python.exe && PAPER="C:\agenticcivthoughts\Agentic_Civilizations_Research_v2.md"
$PY -m scripts.style_pass_report "$PAPER" "C:\agenticcivthoughts\style-pass-report.md" 2>&1 | tail -3
$PY -m scripts.score_russell_delta "$PAPER"
```
Expected: findings near zero; delta within range and below baseline. Fix section 7 to 9 findings before continuing.

- [ ] **Step 5: Commit**

```bash
cd /c/agenticcivthoughts && git add Agentic_Civilizations_Research_v2.md && git commit -m "Russell pass: sections 7 to 9"
```

---

### Task 5: Drive the negative linters to zero

**Files:** Modify `Agentic_Civilizations_Research_v2.md`.

- [ ] **Step 1: Run the full negative pass**

```bash
cd /c/russellian-book-suite/skills/russellian-style && PY=.venv/Scripts/python.exe && PAPER="C:\agenticcivthoughts\Agentic_Civilizations_Research_v2.md"
$PY -m scripts.style_pass_report "$PAPER" "C:\agenticcivthoughts\style-pass-report.md"
head -20 "C:\agenticcivthoughts\style-pass-report.md"
```
Expected: a "Summary by rule" table. Target: zero findings for active-voice, no-hedging, parallel-structure, listicle-anaphora, rhythm-uniform-length. signal-density should be zero or a small residual only where cutting the modifier would lose a load-bearing fact.

- [ ] **Step 2: Fix each remaining finding**

For each finding the report lists by line: rewrite that sentence. Contrastive "rather than" becomes "not X but Y". Passive becomes active. Over-budget sentences atomize. The one listicle-anaphora and parallel-structure finding are addressed by the Section 8 bullet rewrite and the Section 1 thesis rewrite; confirm they cleared.

- [ ] **Step 3: Re-run until clean**

Re-run Step 1. Expected: total findings 0, or a documented signal-density residual of at most 2 with a one-line justification in the commit message. No active-voice, no-hedging, parallel, listicle, or rhythm findings remain.

- [ ] **Step 4: Commit**

```bash
cd /c/agenticcivthoughts && git add Agentic_Civilizations_Research_v2.md && git commit -m "Russell pass: clear negative linters"
```

---

### Task 6: Vitality and corpus distance

**Files:** Modify `Agentic_Civilizations_Research_v2.md`.

- [ ] **Step 1: Measure vitality and distance**

```bash
cd /c/russellian-book-suite/skills/russellian-style && PY=.venv/Scripts/python.exe && PAPER="C:\agenticcivthoughts\Agentic_Civilizations_Research_v2.md"
$PY -m scripts.score_russell_delta "$PAPER"
$PY -m scripts.lint_paragraph_motion "$PAPER" | head -12
$PY -m scripts.lint_ai_staccato "$PAPER"
$PY -m scripts.lint_burstiness "$PAPER" | head -8
$PY -m scripts.lint_concrete_instance_density "$PAPER" | head -8
$PY -m scripts.lint_epistemic_precision "$PAPER" | head -8
```

- [ ] **Step 2: Add motion where prose is flat**

If `paragraph-motion` flat_proportion is above 0.55, find the flattest paragraphs (assertion-only runs) and apply the concession-turn move: common view, partial grant, distinction, consequence. Keep `lint_ai_staccato` empty (do not over-correct into a wall of short sentences). Vary sentence length per the burstiness reading.

- [ ] **Step 3: Re-score**

Re-run Step 1. Expected: Burrows delta within p10..p90 and at or below ~0.70 (moved down from 0.785 baseline, toward the p50 of 0.685), `reliable: true`; flat_proportion below 0.55; staccato empty; epistemic-precision and concrete-instance findings resolved or justified.

- [ ] **Step 4: Confirm the negative linters are still clean**

```bash
cd /c/russellian-book-suite/skills/russellian-style && .venv/Scripts/python.exe -m scripts.style_pass_report "C:\agenticcivthoughts\Agentic_Civilizations_Research_v2.md" "C:\agenticcivthoughts\style-pass-report.md" 2>&1 | tail -3
```
Expected: still zero (the motion edits did not reintroduce hedges or passive voice).

- [ ] **Step 5: Commit**

```bash
cd /c/agenticcivthoughts && git add Agentic_Civilizations_Research_v2.md style-pass-report.md && git commit -m "Russell pass: lift paragraph motion and corpus distance"
```

---

### Task 7: Final gates, PDF, and finish

**Files:** Modify `Agentic_Civilizations_Research_v2.md`; create/delete `_build_v2.py`; regenerate the PDF.

- [ ] **Step 1: Final strip re-verify and dash gate**

```bash
cd /c/agenticcivthoughts && grep -nE "\(Grounded\)|\(Framework\)|\(Speculative\)|Epistemic status and legend|\| Status \|" Agentic_Civilizations_Research_v2.md; echo "tags-clear-if-empty"; echo -n "dashes (want 0): "; grep -c "—\|–" Agentic_Civilizations_Research_v2.md
```
Expected: no tag matches; dash count 0.

- [ ] **Step 2: Humanizer pass**

Apply the humanizer skill for residual AI tells (em/en dashes, rule-of-three, AI vocabulary, curly quotes). The russellian-style skill explicitly defers generic AI-writing tells to humanizer. Fix any hit; re-run the dash gate.

- [ ] **Step 3: Regenerate the PDF and verify glyph-clean**

Create `C:\agenticcivthoughts\_build_v2.py`:

```python
import sys, markdown
from xhtml2pdf import pisa
SRC = r"C:\agenticcivthoughts\Agentic_Civilizations_Research_v2.md"
DST = r"C:\agenticcivthoughts\Agentic_Civilizations_Research_v2.pdf"
CSS = """
@page { size: A4 portrait; margin: 1.8cm; }
body { font-family: Helvetica, Arial, sans-serif; font-size: 10pt; line-height: 1.4; color: #111; }
h1 { font-size: 20pt; margin-bottom: 2pt; }
h2 { font-size: 14pt; margin-top: 14pt; border-bottom: 1px solid #999; padding-bottom: 2pt; }
h3 { font-size: 12pt; margin-top: 10pt; }
p, li { font-size: 10pt; }
table { border-collapse: collapse; width: 100%; margin: 6pt 0; }
th, td { border: 1px solid #999; padding: 3pt 4pt; font-size: 8pt; text-align: left; vertical-align: top; word-wrap: break-word; }
th { background-color: #ececec; font-weight: bold; }
code { font-family: Courier, monospace; font-size: 8.5pt; }
"""
body = markdown.markdown(open(SRC, encoding="utf-8").read(), extensions=["tables"])
html = f"<html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{body}</body></html>"
with open(DST, "wb") as fh:
    err = pisa.CreatePDF(html, dest=fh, encoding="utf-8").err
sys.exit(1 if err else 0)
```

Run and verify:
```bash
cd /c/agenticcivthoughts && python _build_v2.py; echo "exit=$?"; rm -f _build_v2.py; python -c "
from pypdf import PdfReader
r=PdfReader(r'C:\agenticcivthoughts\Agentic_Civilizations_Research_v2.pdf')
t=''.join((p.extract_text() or '') for p in r.pages)
print('pages', len(r.pages))
for c,n in [('■','box'),('�','repl'),('—','emdash'),('–','endash')]: print(n, t.count(c))
print('Agora Scale:', 'Agora Scale' in t, '| no tag word Grounded:', t.count('(Grounded)'))
" 2>&1 | grep -v "wrong pointing"
```
Expected: `exit=0`; box/repl/emdash/endash all 0; `(Grounded)` count 0.

- [ ] **Step 4: Commit the PDF and report**

```bash
cd /c/agenticcivthoughts && git add Agentic_Civilizations_Research_v2.pdf style-pass-report.md && git commit -m "Russell pass: regenerate PDF and style-pass report"
```

- [ ] **Step 5: Commit the plan in the suite**

```bash
cd /c/russellian-book-suite && git add docs/plans/2026-05-27-russell-pass-agentic-civilizations.md && git commit -m "Add plan: Russell pass on the agentic-civilizations paper"
```

- [ ] **Step 6: Final review and finish**

Dispatch one read-only reviewer over the whole rewritten paper: confirm it reads in Russell's voice end to end, no epistemic tags survive, every claim and `[n]` citation is intact, and the speculative sections are marked as conjecture in prose. Apply any fix, recommit. Then invoke `superpowers:finishing-a-development-branch` for the suite branch `russell-pass-agentic-civ` (the suite holds only the spec and plan; the paper rewrite is committed directly on `C:\agenticcivthoughts` master). Do not push.

---

## Self-Review

**Spec coverage:**
- Rewrite in place, full Russell voice -> Tasks 2, 3, 4.
- Strip every tag + the legend section + Status column + (Speculative) cells -> Task 1; re-verified Task 7 Step 1.
- Keep claims, [n] citations, References, Agora Scale table, nine-section structure -> stated in every rewrite task; verified Task 7.
- Carry epistemics in prose -> Task 2 Step 2/4, Task 3 Step 3, Task 4 Step 3.
- Six negative linters meet budget + emit style-pass-report.md -> Task 5; report path used throughout.
- Vitality / corpus distance (the "compliant but lifeless" guard) -> Task 6.
- Humanizer-clean, zero dashes -> Task 7 Step 1/2.
- PDF glyph-clean -> Task 7 Step 3.
- Terse, no-AI-attribution commits in both repos -> every commit command omits Co-Authored-By; stated in the header.
- Spec + plan in the suite docs -> spec committed in brainstorming; plan committed Task 7 Step 5.

**Placeholder scan:** No "TBD"/"TODO". The rewrite tasks give rules, the system prompt, per-section targets, and exact lint commands rather than pre-writing every Russell sentence, which is correct for a prose-rewrite plan (the sentences are the work; the gates are deterministic). Budgets are concrete: negative findings 0 (signal-density residual at most 2 with justification); delta within p10..p90 and at or below ~0.70; flat_proportion below 0.55; staccato empty.

**Name consistency:** `$PY`, `$PAPER`, the linter module names (`scripts.style_pass_report`, `scripts.score_russell_delta`, `scripts.lint_paragraph_motion`, etc.), the report path `C:\agenticcivthoughts\style-pass-report.md`, and the `_build_v2.py` helper are used identically across tasks. The strip-verify grep pattern is identical in Task 1 Step 6 and Task 7 Step 1.
