# neurosym-forge Documentation — Full-Docs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the four documentation artifacts the brief at `docs/handoffs/2026-05-14-neurosym-forge-documentation-brief.md` requires: a concepts overview, an operator runbook, an expanded osmotic-pressure walkthrough, and a README "Verifiers" subsection that replaces the current one-paragraph mention.

**Architecture:** Prose-only delta. All four artifacts get drafted inline by the controller (the user picked "inline drafting + subagent panel review"). Each prose file passes `russellian-style` linters with zero critical findings and a `humanizer` pass before commit. After all four are drafted and lint-clean, the controller dispatches the 7-persona `review-conductor` panel plus a domain-expert subagent focused on the verifier specifics. Gating-persona criticals get addressed before the PR is opened. Plain branch, no worktree.

**Tech Stack:** Markdown only. Lint tooling: russellian-style's eleven linters (6 negative + 5 vitality); humanizer skill's AI-fingerprint catalog. Review tooling: review-conductor's chapter-default panel adapted to the README/docs artifact type.

---

## File structure

### New files

```
docs/
├── concepts/
│   └── neurosym-forge.md                              # NEW (target 150-300 lines)
├── operations/
│   └── neurosym-forge-runbook.md                      # NEW (target 250-400 lines)
```

### Modified files

```
README.md                                              # replace "Verifiers (optional)" section
skills/neurosym-forge/references/worked-examples/osmotic-pressure/README.md  # expand 50 → 100-150 lines
```

---

## Phase A — Source intake

## Task A1: Branch off main + source read

**Files:** none (read-only)

- [ ] **Step 1: Verify clean state + branch**

```bash
git checkout main
git pull --ff-only origin main
git checkout -b docs/neurosym-forge-documentation
git status
```

Expected: `On branch docs/neurosym-forge-documentation`, working tree clean.

- [ ] **Step 2: Batch-read the source materials**

The brief lists twelve sources. Read them in the brief's stated order. Already covered in this session:
- `skills/neurosym-forge/SKILL.md` — covered
- `skills/neurosym-forge/references/worked-examples/osmotic-pressure/README.md` — covered
- Brief itself — covered

Read now (in order):
- `skills/neurosym-forge/references/metta-idioms.md`
- `skills/neurosym-forge/references/atomspace-edn.md`
- `skills/neurosym-forge/references/grounded-atoms.md`
- `skills/neurosym-forge/references/phase-boundaries.md`
- `skills/neurosym-forge/references/rewrite-rule-style.md`
- `docs/specs/2026-05-13-neurosym-forge-design.md`
- `docs/specs/2026-05-14-neurosym-forge-v0.3-mission-design.md`
- `verifiers/bermuda/README.md`
- `docs/operations/2026-05-12-bundle-c-runbook.md` (style pattern; read in full)
- `README.md` § "The seven core skills" and § "Verifiers (optional)" (verify current state of the section being replaced)

- [ ] **Step 3: Record open questions**

If conflicts surface between sources (the brief flags three common cases — terminology drift across the five references, the Bermuda canonical.rs vs v0.3 axioms.rs shim, the `--book-knowledge-bridge` flag history), note them in the relevant deliverable's draft. Do not patch the references; document the canonical position in the concepts doc.

---

## Phase B — Draft the four deliverables

Order matters. The concepts doc establishes canonical terminology that the runbook and the README expansion reuse. The osmotic-pressure walkthrough is independent. The README expansion comes last because it cross-links to the new docs.

## Task B1: Draft `docs/concepts/neurosym-forge.md`

**Files:**
- Create: `docs/concepts/neurosym-forge.md`

Target: ~200 lines. Cross-link to `skills/neurosym-forge/references/*.md` for depth; do not duplicate their content. Use the style of `docs/operations/2026-05-12-bundle-c-runbook.md` for prose discipline — prose-heavy, short paragraphs, concrete examples.

- [ ] **Step 1: Write the file**

Sections (in this order):

1. **The problem** — Two paragraphs. Why scaffold verifiers from a template (each verifier is mostly the same scaffolding around a domain-specific predicate set; the variation is small enough to template). Why ClojureScript and Rust (CLJS owns Phase-2 rewrite orchestration where MeTTa idioms read naturally; Rust owns Phase-3 SMT/Datalog/e-graph where the existing solver ecosystem is mature). Why MeTTa as the conceptual vocabulary (MeTTa's atomspace gives one IR that crosses both languages; the `=` / `:` / `!` / `match` idioms transfer cleanly).

2. **EDN-as-Atomspace IR** — One paragraph stating the choice (JSON-compatible subset of EDN so both CLJS and Rust can parse without custom readers). One paragraph naming the four atom kinds (symbol, variable, grounded, expression) with a one-line example of each. One paragraph on the top-level shape (sorts, rules, grounded modules) and the linter contract (every atom carries `:sort`; no unbound variables). Closing pointer at `skills/neurosym-forge/references/atomspace-edn.md` for the schema.

3. **MeTTa idiom mapping** — One paragraph framing the mapping (MeTTa's seven idioms each translate to a CLJS or Rust construct). A summary table with rows for `=` (rewrite rule), `:` (sort annotation), `!` (evaluation request), `match` (pattern + bindings), `superpose` / `collapse` (multiple results / single result), grounded atoms (Rust `#[napi]` functions), self-reflection (rule introspection in CLJS). Closing pointer at `skills/neurosym-forge/references/metta-idioms.md` for full prose and worked examples.

4. **The axioms hook (v0.3)** — Two paragraphs. First: the contract. `crate::axioms::assert_axioms(&ctx, &solver)` is called once before per-atom tracked assertions; scaffolded projects ship a no-op default; projects override the body to install Z3 hard constraints (the gas constant, conservation laws, range bounds). Second: the Bermuda implementation is the reference. `verifiers/bermuda/src/axioms.rs` installs the population and ferry-capacity bounds; `canonical.rs` predates the hook and gets re-exported via a thin shim in PR-2 of the v0.3 mission.

5. **Composition with book-qa** — One paragraph. D13 is the optional defect class for claim-set unsatisfiability. The verifier emits `verdict.edn` (one atom per claim, plus a global verdict); `verdict_to_qa.py` translates to `qa/verification-defects.json`; `book-qa`'s `lint_artifact.py` reads that file when `qa-config.yaml: enable_verification: true`. The hook is opt-in per workspace.

6. **Where to read next** — Five bullets pointing at the five reference files plus the runbook.

- [ ] **Step 2: Lint the file**

```bash
cd skills/russellian-style
.venv/Scripts/python.exe -m scripts.lint_hedges ../../docs/concepts/neurosym-forge.md
.venv/Scripts/python.exe -m scripts.lint_passive_voice ../../docs/concepts/neurosym-forge.md
.venv/Scripts/python.exe -m scripts.lint_signal_density ../../docs/concepts/neurosym-forge.md
.venv/Scripts/python.exe -m scripts.lint_parallel_structure ../../docs/concepts/neurosym-forge.md
.venv/Scripts/python.exe -m scripts.lint_sentence_rhythm ../../docs/concepts/neurosym-forge.md
.venv/Scripts/python.exe -m scripts.lint_listicle_abstract ../../docs/concepts/neurosym-forge.md
.venv/Scripts/python.exe -m scripts.lint_burstiness ../../docs/concepts/neurosym-forge.md
.venv/Scripts/python.exe -m scripts.lint_ai_vocabulary ../../docs/concepts/neurosym-forge.md
.venv/Scripts/python.exe -m scripts.lint_concrete_instance_density ../../docs/concepts/neurosym-forge.md
.venv/Scripts/python.exe -m scripts.lint_epistemic_precision ../../docs/concepts/neurosym-forge.md
.venv/Scripts/python.exe -m scripts.lint_paragraph_motion ../../docs/concepts/neurosym-forge.md
```

Expected: zero `critical` severity findings on any linter. Quoted anti-examples (where the prose names patterns the linters detect) are exempt by inspection.

- [ ] **Step 3: Triage findings**

If any non-quoted-example critical finding fires, fix the prose and re-lint. The vitality linters land advisory in v1, so their findings do not block; track them but do not iterate to zero on every advisory.

- [ ] **Step 4: Commit**

```bash
git add docs/concepts/neurosym-forge.md
git commit -m "docs/concepts: neurosym-forge conceptual overview"
```

## Task B2: Draft `docs/operations/neurosym-forge-runbook.md`

**Files:**
- Create: `docs/operations/neurosym-forge-runbook.md`

Target: ~320 lines. Pattern off `docs/operations/2026-05-12-bundle-c-runbook.md` — prose-heavy, copy-pasteable commands, expected outputs.

- [ ] **Step 1: Write the file**

Sections (in this order):

1. **Prerequisites** — Python 3.13 + Rust 1.85+ (only for live verification) + Node 22+ (only for the CLJS orchestrator). The skill's `.venv` at `skills/neurosym-forge/.venv/`. Confirm install with `python -m scripts.scaffold_project --help`.

2. **Scaffold a project** — Two recipes. (a) Plain scaffold for a verifier that takes an EDN ledger directly. (b) `--book-knowledge-bridge` scaffold for a verifier that reads a `book-knowledge` workspace's `claims/ledger.jsonl`. For each, show the command, the resulting tree (cljs-orchestrator/, rust-verifier/, rules/, work/, templates/), and where to look for the `axioms.rs` no-op hook.

3. **Ingest a ledger** — Use the bridge `ingest_ledger.py`. Show the predicate-map structure (`{"clm-...": {"predicate": ":population-bound", "args": [...], "kind": ":CONTEXT"}}`). Distinguish `:CONTEXT` (claim becomes a hard constraint in the model) from `:OPAQUE` (claim referenced but not constrained). Expected output: `work/atomspace.edn` populated with one atom per claim plus the predicate registry.

4. **Extract prose** — Two passes. Pass A (regex) for structured ledger entries; Pass B (LLM, opt-in via `--llm-extract`) for free-form prose. Show how to write a predicate pattern in `rules/predicates.edn`. Worked example: extracting an osmotic-pressure equation from a synthetic paper.

5. **Add a sort, rule, or grounded atom** — Three subsections, one per helper. (a) `add_sort` for declaring `:solution`, `:molarity`, etc. (b) `add_rewrite_rule` for typed `=` rules with fixture tests. (c) `add_grounded_atom` for `#[napi]` Rust functions. Each shows the command, what files it touches, and how the checksum linter at `lint_atomspace.py` detects manual edits.

6. **Wire D13 into book-qa** — Where `qa-config.yaml: enable_verification: true` lives in the workspace. Show the data flow: scaffolded project emits `verdict.edn` → `verdict_to_qa.py` translates → `qa/verification-defects.json` → `book-qa` `lint_artifact.py` reads. Expected D13 finding shape on an unsatisfiable claim set.

7. **Run end-to-end against Bermuda** — Two paths. Stubbed: `--stub --stub-verdict sat` for development without Rust/Node. Real: `cargo build --features smt,kg` (skips tectonic). Expected outputs at each step. Time: ~30s stubbed, ~3min real.

8. **Troubleshoot** — Known issues, each with the symptom + fix:
   - Tectonic libpng link failure → use `--features smt,kg` (without `pdf`)
   - `..` in `--out` path → since v0.3, OK as long as resolved path stays under cwd's parent
   - Manual edits to `rules/*.edn` fail the checksum linter → re-run `add_*` helpers instead of hand-editing
   - `--book-knowledge-bridge` not found → ensure `book-knowledge` is installed at `~/.claude/skills/book-knowledge/`

- [ ] **Step 2: Lint**

Same eleven-linter sweep as Task B1, on `docs/operations/neurosym-forge-runbook.md`.

- [ ] **Step 3: Triage + fix**

- [ ] **Step 4: Commit**

```bash
git add docs/operations/neurosym-forge-runbook.md
git commit -m "docs/operations: neurosym-forge operator runbook"
```

## Task B3: Expand osmotic-pressure walkthrough

**Files:**
- Modify: `skills/neurosym-forge/references/worked-examples/osmotic-pressure/README.md`

Current ~70 lines (re-verified in source intake). Target ~120 lines.

- [ ] **Step 1: Read the existing file**

```bash
cat skills/neurosym-forge/references/worked-examples/osmotic-pressure/README.md
```

Preserve the existing scaffold + add-sort + van 't Hoff rule sections. Add new content after them.

- [ ] **Step 2: Add the new sections**

Append (in this order):

1. **Add a grounded atom for the gas constant** — `add_grounded_atom` invocation creating `:R-gas-constant` in `rust-verifier/src/grounded.rs` plus the CLJS bridge stub. Expected diff in the project tree.

2. **Fixture inputs** — A synthetic `raw/osmotic-pressure-paper.txt` (~200 words of paper-style prose stating the three claims). A 3-claim ledger at `work/claims-ledger.jsonl` covering: (a) van 't Hoff factor for NaCl is approximately 2, (b) solution molarity 0.15 mol/L, (c) temperature 310 K. Show the expected `work/atomspace.edn` after ingest.

3. **Run end-to-end (stubbed)** — `npm run build && node cljs-orchestrator/dist/main.js verify work/atomspace.edn work/verdict.edn --stub --stub-verdict sat`. Expected `verdict.edn` contents: one `:sat` atom per claim plus the global `:sat` verdict.

4. **Run end-to-end (real, no PDF)** — `cargo build --features smt,kg` followed by the verify command without `--stub`. Expected: real Z3 returns `:sat` because the three claims are consistent under the van 't Hoff law. Time: ~30s on a recent laptop.

5. **The `:unsat` case** — Doctor the ledger so van 't Hoff factor is 1 (NaCl dissociates into Na⁺ + Cl⁻; i=1 is wrong). Re-run; expected verdict is `:unsat`. Show the unsat core: it cites the doctored claim plus the van 't Hoff rule. This is what the verifier exists to catch.

- [ ] **Step 3: Lint** (same eleven-linter sweep)

- [ ] **Step 4: Commit**

```bash
git add skills/neurosym-forge/references/worked-examples/osmotic-pressure/README.md
git commit -m "neurosym-forge: expand osmotic-pressure worked example with end-to-end walkthrough"
```

## Task B4: README "Verifiers" section replacement

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Locate the current section**

```bash
grep -n "Verifiers (optional)" README.md
```

Expected: one line number. The section is one paragraph (per the brief's note that it's a "one-paragraph mention").

- [ ] **Step 2: Draft the replacement**

Target: 15-25 lines of prose plus the existing verifiers table. Sections inline:

- **What scaffolding produces** — A one-paragraph description of the project tree (cljs-orchestrator/, rust-verifier/, rules/, work/, templates/) and that the `axioms.rs` file ships as a no-op hook the project overrides.
- **The axioms hook in one sentence** — `crate::axioms::assert_axioms(&ctx, &solver)` runs once before per-atom assertions; projects install Z3 hard constraints in the body.
- **The typical workflow** — Five steps in prose, not as a numbered list: scaffold → ingest ledger → extract prose → verify → consume in book-qa.
- **Links** — One paragraph naming the new operator runbook, the new concepts doc, and the existing skill SKILL.md.

- [ ] **Step 3: Replace the section in the README**

Use a single Edit call. Preserve the section heading, the table that follows the prose, and the surrounding cross-references.

- [ ] **Step 4: Lint** (same eleven-linter sweep, on README.md)

- [ ] **Step 5: Commit**

```bash
git add README.md
git commit -m "README: expand Verifiers section with workflow and links to neurosym-forge docs"
```

---

## Phase C — Humanizer pass

## Task C1: Manual humanizer review

**Files:**
- Review: all four new prose files

- [ ] **Step 1: Walk each new file with the humanizer catalog in mind**

Patterns to scan for and fix in place:
- Em-dash overuse (more than ~1 per paragraph)
- Rule-of-three (three parallel clauses or three-item lists used decoratively)
- Banned words: "essentially", "fundamentally", "key insight", "Main theorem:", "Proof strategy:"
- Numbered proof steps in prose
- Excessive bold (every key term bolded)
- AI vocabulary tells: "navigate", "leverage", "delve", "tapestry", "harness", "in the realm of"

Quoted anti-examples and verbatim source citations are exempt.

- [ ] **Step 2: Fix any hits found**

- [ ] **Step 3: Commit any fixes**

```bash
git add docs/concepts/neurosym-forge.md docs/operations/neurosym-forge-runbook.md skills/neurosym-forge/references/worked-examples/osmotic-pressure/README.md README.md
git commit -m "docs: humanizer pass on neurosym-forge documentation"
```

---

## Phase D — Panel review

## Task D1: Dispatch the 7-persona panel + a domain reviewer

**Files:** none (review-only)

- [ ] **Step 1: Push the branch**

```bash
git push -u origin docs/neurosym-forge-documentation
```

- [ ] **Step 2: Dispatch eight reviewers in parallel**

Seven personas from the chapter-default panel (Gottlieb, Lay Reader, Domain Expert, Copyeditor, Enjoyment Reader, AI-Slop Detector, First-Time Visitor) plus one domain-expert sub-agent scoped to the verifier specifics (does the runbook's command surface match the actual scripts; does the concepts doc's axioms-hook description match `verifiers/bermuda/src/axioms.rs`).

Each persona reviews **all four new prose files**, not one file each. Prompt asks for severity-tagged findings under 350 words. Quoted anti-examples and command outputs are exempt.

The verifier-domain sub-agent specifically checks:
- Every `scripts.<name>` command cited in the runbook exists in `skills/neurosym-forge/scripts/`
- Every Cargo feature flag cited (e.g., `--features smt,kg`) is real
- The osmotic-pressure walkthrough's expected verdicts (`:sat` for the clean case, `:unsat` for the doctored case) are physically correct under van 't Hoff
- The D13 wiring description matches `verifiers/bermuda/scripts/verdict_to_qa.py` and `book-qa/scripts/lint_artifact.py`

- [ ] **Step 3: Wait for all eight returns**

## Task D2: Synthesize findings + fix critical gating-persona issues

**Files:** varies by findings

- [ ] **Step 1: Tally findings**

Per-persona table with v1 critical / important / minor counts. Gating personas: Gottlieb, Domain Expert, Copyeditor, AI-Slop Detector. Verdict: pass if zero critical from any gating persona; soft-gate-fail otherwise.

- [ ] **Step 2: Apply critical fixes**

One Edit call per critical finding. Address all gating-persona criticals; advisory criticals fix only if the fix is clear.

- [ ] **Step 3: Re-lint the modified files**

Same eleven-linter sweep on whichever files changed.

- [ ] **Step 4: Commit fixes**

```bash
git commit -am "docs: address panel findings on neurosym-forge documentation"
git push
```

---

## Phase E — PR

## Task E1: Open the PR

- [ ] **Step 1: Verify CI-relevant state**

```bash
cd skills/russellian-style && .venv/Scripts/python.exe -m pytest tests/ -q --tb=no
cd ../book-compose && .venv/Scripts/python.exe -m pytest tests/ -q --tb=no
cd ../book-knowledge && .venv/Scripts/python.exe -m pytest tests/ -q --tb=no
cd ../book-qa && python -m pytest tests/ -q --tb=no
cd ../book-thesis && python -m pytest tests/ -q --tb=no
```

Expected: all green. Documentation-only PR; tests should not regress.

- [ ] **Step 2: Open the PR**

```bash
gh pr create --repo CharlesHoskinson/russellian-book-suite \
  --head docs/neurosym-forge-documentation \
  --base main \
  --title "docs: full neurosym-forge documentation" \
  --body "$(cat <<'EOF'
## Summary

Implements docs/handoffs/2026-05-14-neurosym-forge-documentation-brief.md. Four documentation artifacts that move the neurosym-forge skill from "one-line table entry plus five reference files" to operator-ready.

## Deliverables

1. **`docs/concepts/neurosym-forge.md`** (NEW) — Conceptual overview: the problem, the EDN-as-Atomspace IR, the MeTTa idiom mapping, the v0.3 axioms hook, composition with book-qa via D13. Cross-links to the five skill references for depth.
2. **`docs/operations/neurosym-forge-runbook.md`** (NEW) — Recipe-based operator guide. Prerequisites; scaffold (plain + bridge); ingest a ledger; extract prose; add sort/rule/grounded atom; wire D13; run end-to-end against Bermuda (stubbed + real); troubleshoot the common failures.
3. **Expanded `skills/neurosym-forge/references/worked-examples/osmotic-pressure/README.md`** — Adds grounded-atom recipe, fixture inputs, end-to-end (stubbed + real), and the doctored `:unsat` case showing what the unsat core looks like.
4. **README "Verifiers (optional)" section replacement** — Project tree summary, axioms hook in one sentence, typical workflow, links to the new runbook and concepts doc.

## Style discipline

Every new prose file passes the russellian-style linter sweep (eleven linters) with zero critical findings. Humanizer pass complete. Commits terse, no AI attribution, no Co-Authored-By.

## Panel review

Reviewed by the seven-persona review-conductor panel plus a verifier-domain sub-agent that cross-checked every command surface against `skills/neurosym-forge/scripts/` and the Bermuda implementation. All gating-persona criticals addressed before this PR opened.

## Reference

- Brief: `docs/handoffs/2026-05-14-neurosym-forge-documentation-brief.md`
- Spec: `docs/specs/2026-05-14-neurosym-forge-docs-handoff-design.md` (the spec that drove the brief)
- Plan: `docs/plans/2026-05-14-neurosym-forge-full-documentation.md`

## Test plan

- [x] `pytest` green across russellian-style, book-compose, book-knowledge, book-qa, book-thesis (documentation-only PR; no test regressions possible)
- [x] All four prose files pass russellian-style linters with zero critical findings
- [x] All four prose files pass the humanizer manual sweep
- [x] Verifier-domain reviewer confirmed every cited command and feature flag exists in the codebase
EOF
)"
```

- [ ] **Step 3: Report PR URL**

---

## Self-review

**Spec coverage walkthrough:**

| Brief deliverable | Implementing task |
|---|---|
| `docs/operations/neurosym-forge-runbook.md` | Task B2 |
| `docs/concepts/neurosym-forge.md` | Task B1 |
| README expansion | Task B4 |
| Expanded osmotic-pressure README | Task B3 |
| Style authority (russellian-style + humanizer) | Phase C + the lint step inside each B task |
| Workflow (brainstorm → plan → execution) | This plan covers the plan step; controller executes |
| PR titled `docs: full neurosym-forge documentation` | Task E1 |

All four deliverables have implementing tasks. Lint gates are embedded in each draft task plus a dedicated humanizer pass in Phase C. Panel review is Phase D, mirroring the v5 README review pattern that worked twice in this session.

**Placeholder scan:** No TBD/TODO. Every section's content shape is specified at the bullet level; the actual prose is drafted inline by the controller using the brief's section requirements and the source-material reads.

**Type consistency:** N/A (prose only).

**Risk:** The brief's three flagged open questions (terminology drift across the references; Bermuda canonical.rs vs v0.3 axioms.rs; `--book-knowledge-bridge` history) get surfaced during the Task A1 source read. If any conflict is severe, the controller pauses and asks the user before continuing. The default behavior — canonicalise terminology in the concepts doc, document only the v0.3 contract in the runbook, cover both scaffold variants — is captured in the brief and reflected in Task B1 and B2.

**Effort estimate:** ~2-3 hours for the full execution (source read + drafting + lint + panel + fixes + PR). The brief estimated 1-2 days for a fresh session; this is faster because the controller has the full repo context loaded from the prior session.

---

## Execution Handoff

Plan complete and saved to `docs/plans/2026-05-14-neurosym-forge-full-documentation.md`. Two execution options:

**1. Subagent-Driven (recommended)** — Fresh subagent per task with two-stage review between each.

**2. Inline Execution** — Execute tasks in this session using `superpowers:executing-plans`, with the panel-review checkpoint in Phase D as the main review gate.

The user has already picked **inline drafting + subagent panel review** during brainstorming. Phase A through C draft and lint inline; Phase D is the subagent panel; Phase E opens the PR.
