# book-qa v5 — Design

Date: 2026-05-11
Status: Draft (synthesises retrospective + two research surveys)

## Problem

Six observed failure modes in our v3→v4.3 work, each backed by both research evidence and our defect inventory:

1. **Recurring patches.** The same defect class (orphan `[clm-...]` tokens, raw markdown after HTML blocks, Tailwind CSS reset) needed manual patching 1–3 times each because nothing scanned the final artefact.
2. **Middle-chapter quality dip.** Chapters 4–8 received less rigorous output than 1–3 and 9–10. The "Context Rot" research (Morph 2026) and the "Agent Drift" paper (arXiv 2601.04170) both document a >30% accuracy drop in the middle of long contexts. Our 50-dispatch persona review hit this directly.
3. **Source-vs.-rendered drift.** Patches I applied to the rendered manuscript were undone the next time `build_book` ran from the chapter sources.
4. **No cross-chapter consistency check.** Terminology drift, fact contradictions across chapters, and repeated content were never audited.
5. **Prompt drift.** Chapter-expansion prompts hard-coded titles that were stale by one slot, producing a chapter-ordering mismatch.
6. **Fat-orchestrator antipattern.** The same agent that produced a chapter was sometimes the one asked to review it, which collapses the verifier.

## What v5 ships

A new sibling skill `book-qa` at `~/.claude/skills/book-qa/` that runs **between** `book-compose.build_book` and "ship release." It implements the **Generator-Verifier with Deterministic Gate + per-defect-class critics + Sentinel-Healer loop** pattern.

### Architecture (four stages)

```
   chapter drafts ─► build_book ─► manuscript.md/.html
                                          │
                                          ▼
              ┌─── Stage 1: Deterministic linter (Python) ───┐
              │   Catches D1–D8 (mechanical defects)           │
              └─────────────────┬─────────────────────────────┘
                                ▼
              ┌─── Stage 2: Per-chapter LLM critics (10 in parallel) ───┐
              │   Each chapter gets a fresh-context agent + 15-item check  │
              │   Plus 4 cross-chapter LLM critics (D9–D12)                │
              └─────────────────┬─────────────────────────────────────────┘
                                ▼
              ┌─── Stage 3: Sentinel (Python aggregator) ───┐
              │   Roll up `defects.json` from stages 1 & 2     │
              │   Hard-fail on D1–D8, soft-gate on D9–D12     │
              └─────────────────┬─────────────────────────────┘
                                ▼
              ┌─── Stage 4: Healer (LLM, isolated context) ───┐
              │   One patch agent per defect, sees only the defect + span  │
              │   Bounded to 3 iterations per defect class                  │
              └─────────────────┬─────────────────────────────────────────┘
                                ▼
                         release-bundle
```

### Defect taxonomy

**Mechanical (Stage 1, deterministic Python):**

- **D1** orphan citation tokens — anything matching `\[clm-\d{4}-\d{6}\]`, bare `clm-\d{4}-\d{6}`, "Claim ledger:" mentions, or `\[\^\d+\]: clm-` patterns
- **D2** raw markdown bleed — markdown-style headings/bold/links/images appearing inside `<section>`, `<div class="hero-table">`, or `<pre>` blocks where they would not be parsed
- **D3** broken cross-references — figure markdown like `![alt](path)` where the path does not exist; `<sup>` footnote refs with no matching `<li id="fn-...">`; ToC entries that do not match any `# Chapter` heading
- **D4** heading-hierarchy violations — H3 without preceding H2 in the same chapter; missing chapter H1; duplicate H1
- **D5** count-contract failures — chapter word count outside [1800, 2500]; footnote count outside [3, 8] per chapter; figure count outside [1, 4] per chapter
- **D6** paragraph-length variance — within-chapter coefficient-of-variation outside [0.4, 1.1] (proxy for AI drift); average paragraph length outside [40, 120] words
- **D7** CSS reset clobber — final HTML file containing both Tailwind preflight (`font-size:inherit`) and an h1 with no override
- **D8** asset 404s — every markdown image, every figure asset, every photo cache reference must resolve to a file under the workspace

**Editorial (Stage 2, one narrow LLM critic per class):**

- **D9** terminology drift — same concept named two ways across chapters (e.g., "Hamilton" the city vs "Hamilton Parish")
- **D10** cross-chapter fact contradictions — Town Hill 76 m vs 79 m, parish count 8 vs 9, etc.
- **D11** repeated content — paragraphs or scenes that appear twice across chapters
- **D12** style drift — sentence length / hedge frequency / passive ratio per chapter vs. the ch-01 baseline; flag chapters more than 1 standard deviation off

### Per-chapter QA swarm (Stage 2 inner loop)

Ten parallel agents, one per chapter, each with:

- Fresh context (no inherited history)
- Input: the rendered chapter HTML (so the agent sees what the reader sees) plus the project glossary (canonical terminology list)
- 15-item editorial checklist (from Chicago Manual, MIT Press, O'Reilly production handbooks)
- Output: structured JSON ticket list, NOT prose

Randomised dispatch order to break the position-in-batch correlation with quality.

### Cross-chapter consistency (Stage 2 outer)

Four narrow critics dispatched after the per-chapter swarm, each sees only structured outputs from the chapter agents:

- **terminology-critic** receives glossary-aware tokens from each chapter; emits a single terminology table with drift flagged
- **fact-critic** receives a list of (chapter, numeric claim, source) tuples; emits contradiction list
- **dedup-critic** receives paragraph hashes; emits near-duplicate pairs
- **style-critic** receives per-chapter Russell-style metrics (already computed by russellian-style linters); emits drift flags

### Sentinel rules (Stage 3)

- Any D1–D8 defect: hard-fail; release blocked.
- Any D9 (terminology drift): soft-gate; flag and continue if waiver in `qa-waivers.yaml`.
- D10 fact contradictions: hard-fail (factual integrity is non-negotiable).
- D11 dedup: soft-gate.
- D12 style drift: soft-gate.

### Healer pattern (Stage 4)

For each hard-fail defect:

- Spawn a fresh agent with **only** the defect ticket and the affected text span (not the full chapter)
- Agent emits a patch
- Re-run Stage 1 on the patched span
- Loop up to 3 times; escalate to user after that

For each soft-gate defect:

- Generate a markdown report; user reviews and decides

## Skill layout

```
~/.claude/skills/book-qa/
├── SKILL.md
├── pyproject.toml
├── .venv/
├── scripts/
│   ├── __init__.py
│   ├── lint_artifact.py          # Stage 1 deterministic linter (D1-D8)
│   ├── dispatch_chapter_qa.py    # Stage 2 per-chapter swarm orchestrator
│   ├── dispatch_consistency.py   # Stage 2 outer 4-critic dispatcher
│   ├── sentinel.py               # Stage 3 aggregator
│   ├── healer.py                 # Stage 4 patch loop
│   ├── defects.py                # shared dataclasses + JSON schema
│   ├── checklist_15.py           # the 15-item editorial checklist
│   └── sibling_skills.py         # cross-skill loader (shared pattern)
├── checklists/
│   ├── chapter-qa.md             # 15-item check per chapter
│   ├── d1-d8-rules.yaml          # deterministic rule definitions
│   └── house-style.yaml          # terminology / spelling canonical forms
├── tests/
│   ├── test_lint_artifact.py
│   ├── test_sentinel.py
│   ├── test_healer.py
│   └── fixtures/
└── docs/
    └── defect-taxonomy.md
```

## Updates to existing skills

- **book-compose**: insert a Stage-1 gate in `build_book` that runs `book-qa.lint_artifact` and fails the build on any D1–D8. Add a `--qa` flag to skip when iterating.
- **book-review**: keep the 5+1 persona pattern (qualitative editorial review) — DIFFERENT job from `book-qa` (mechanical defect detection). `book-review` runs BEFORE chapters are finalised; `book-qa` runs AFTER `build_book` on the assembled artefact.
- **russellian-style**: no changes — its linters become the basis of `book-qa.style-critic` (D12).

## Testing strategy

- Each D1–D8 rule has a fixture of (good chapter, bad chapter, expected defect list).
- Stage 2 critics are tested with mocked LLM responses to verify the JSON schema is enforced.
- Stage 4 healer is tested with a defect injection script: inject one D1 defect, run the loop, verify it heals within 3 iterations.

## v5 vs v4 design (book-craft)

The v4 design doc (`2026-05-10-book-craft-v4-design.md`) introduced `book-craft` for chapter-level CRAFT (scenes, structural variety, visuals). v5 is orthogonal — `book-qa` is post-build mechanical QA. Both can ship; they live in different lifecycle stages:

```
   chapter contracts ─► book-craft scenes ─► russellian linters
                                                    │
                                                    ▼
                                       russellian + book-craft pass
                                                    │
                                                    ▼
                                          book-review (5+1 personas)
                                                    │
                                                    ▼
                                              build_book
                                                    │
                                                    ▼
                                           ┌── book-qa (v5) ──┐
                                                    │
                                                    ▼
                                            release-bundle
```

## Risks

- **Critic cost.** 10-per-chapter agents + 4 consistency agents per build = 14 LLM calls per QA pass. At one pass per release and ~5 releases per book, this is bearable; needs revisit if a tighter feedback loop is wanted.
- **Healer drift.** If the Healer's patch introduces a new D1–D8 defect, the loop re-fires. Convergence depends on the patch agent's restraint. Bound the loop and require human review on the third failed iteration.
- **Critic cycle.** Two critics could disagree (terminology-critic wants "Hamilton" → "City of Hamilton" in ch-04; style-critic wants brevity). Resolution: terminology-critic wins (factual accuracy beats brevity); record the precedence in `qa-waivers.yaml`.

## Open items

- Whether `book-qa` should integrate Vale + markdownlint-cli2 + Pandoc Lua filters (the strongest off-the-shelf tools from the research) or roll its own. Recommendation: wrap them in `lint_artifact.py` — they cover D2, D4, and D3 better than hand-rolled code, and they're well-maintained.
- Whether the Healer needs its own skill or sits inside `book-qa`. Recommendation: inside `book-qa` for now; promote later if other skills want to use it.
- A "memory file" recording lessons-learned across releases. Recommendation: add `~/.claude/skills/book-compose/MEMORY.md` listing the patches we made across v3→v4.3 so future Charles or future Claude don't redo them.
