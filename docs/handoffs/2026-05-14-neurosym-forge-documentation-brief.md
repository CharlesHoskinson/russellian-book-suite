# Brief — neurosym-forge documentation

Date: 2026-05-14
Audience: a Claude Code session writing the docs

## Mission

Produce four documentation artifacts that make `neurosym-forge` operator-ready. The skill is on main at v0.3 but has no operator runbook, no concepts overview, and only a one-paragraph mention in the repo README. Engineers who want to scaffold their own verifier projects have no end-to-end walkthrough.

## Context

`neurosym-forge` is the skill that scaffolds ClojureScript + Rust neurosymbolic verifier projects. It lives at `skills/neurosym-forge/`. v0.3 (merged at SHA `10b1a2b`) adds an `axioms.rs` hook contract, makes `tectonic` an optional Cargo feature, relaxes the `--out` policy, and implements a real Z3 walk in the scaffolded `smt.rs`. The first consumer is `verifiers/bermuda/`, a verifier scoped to the Bermuda book at `examples/bermuda-manual/`.

Relevant PRs: #14 (v0.1 scaffolder + tests), #18 (Bermuda integration + book-qa D13), #21 (v0.3 hardening).

## Sources to read before writing

Read these in this order:

1. `skills/neurosym-forge/SKILL.md` — public skill spec
2. `skills/neurosym-forge/references/metta-idioms.md` — the MeTTa mapping (the conceptual heart)
3. `skills/neurosym-forge/references/atomspace-edn.md` — the IR
4. `skills/neurosym-forge/references/grounded-atoms.md` — the v0.3 axioms hook
5. `skills/neurosym-forge/references/phase-boundaries.md` — what crosses Claude / CLJS / Rust boundaries
6. `skills/neurosym-forge/references/rewrite-rule-style.md` — rule conventions
7. `skills/neurosym-forge/references/worked-examples/osmotic-pressure/README.md` — the worked example
8. `docs/specs/2026-05-13-neurosym-forge-design.md` — v0.1 design
9. `docs/specs/2026-05-14-neurosym-forge-v0.3-mission-design.md` — v0.3 umbrella
10. `verifiers/bermuda/README.md` — what a scaffolded project looks like end-to-end
11. `docs/operations/2026-05-12-bundle-c-runbook.md` — style and length pattern to follow for the runbook
12. `README.md` § "The seven core skills (plus one optional)" and § "Verifiers (optional)" — current README state

## Deliverables

Four artifacts. Each has a target path and the sections it must contain.

### 1. `docs/operations/neurosym-forge-runbook.md` (NEW)

Recipe-based operator guide. Pattern off `docs/operations/2026-05-12-bundle-c-runbook.md` — prose-heavy, copy-pasteable commands, expected outputs. Target length 250-400 lines.

Sections:

- **Prerequisites.** Python 3.13, Rust 1.85+ (only for live verification), Node 22+ (only for the CLJS orchestrator). The skill venv at `skills/neurosym-forge/.venv/`.
- **Scaffold a project.** The `scaffold_project` command with `--book-knowledge-bridge` and without. What the output tree contains. The `axioms.rs` no-op hook.
- **Ingest a ledger.** The bridge `ingest_ledger.py`, predicate maps, the `:CONTEXT` vs `:OPAQUE` distinction.
- **Extract prose.** Pass A (regex) and Pass B (LLM, opt-in). How to write a predicate pattern.
- **Add a sort, rule, or grounded atom.** The three `add_*` helpers. How checksums work. When to use each.
- **Wire D13 into book-qa.** The `qa-config.yaml: enable_verification: true` flag. How `verdict_to_qa.py` produces the file `lint_artifact.py` reads.
- **Run end-to-end against Bermuda.** The stubbed path (`--stub --stub-verdict sat`) and the real path (cargo build with `--features smt,kg` to skip tectonic).
- **Troubleshoot.** Known issues: tectonic libpng failure (use feature flags); `..` in `--out` (since v0.3 OK if resolved path stays under cwd's parent); manual edits to `rules/*.edn` flagged by checksum linter.

### 2. `docs/concepts/neurosym-forge.md` (NEW directory + file)

Conceptual overview, ~150-300 lines. Cross-link to the skill's `references/*.md` for depth; do not duplicate their content.

Sections:

- **The problem.** Two paragraphs. Why scaffold verifiers from a template; why ClojureScript and Rust; why MeTTa as the conceptual vocabulary.
- **EDN-as-Atomspace IR.** The four atom kinds (symbol, variable, grounded, expression) and the top-level shape. Why a JSON-compatible subset of EDN. Link to `atomspace-edn.md` for the schema.
- **MeTTa idiom mapping.** A summary table covering `=`, `:`, `!`, `match`, `superpose`/`collapse`, grounded atoms, self-reflection. Brief; the full table lives in `metta-idioms.md`.
- **The axioms hook (v0.3).** The contract: `crate::axioms::assert_axioms(&ctx, &solver)` is called once before per-atom tracked assertions. Projects override the body. The Bermuda implementation is the reference.
- **Composition with book-qa.** D13 reads `qa/verification-defects.json`. The verifier's verdict.edn gets translated by `verdict_to_qa.py`. The hook is opt-in per workspace via `qa-config.yaml`.

### 3. README expansion

Modify `README.md` only. Find the existing one-paragraph "Verifiers (optional)" section and replace it with a longer subsection.

The replacement covers:

- What scaffolding produces (project tree summary)
- The axioms hook in one sentence
- The typical workflow (scaffold → ingest ledger → extract prose → verify → consume in book-qa)
- Links to the new runbook and concepts doc, plus the existing skill SKILL.md

Keep concise — the deep prose belongs in the dedicated docs (no duplication). Aim for 15-25 lines of prose plus the existing verifiers table.

### 4. Enhanced `skills/neurosym-forge/references/worked-examples/osmotic-pressure/README.md`

Expand the existing file. Currently ~50 lines, target ~100-150.

Add:

- A complete walkthrough: scaffold, add predicates, add the van 't Hoff rule, add a grounded atom for the gas constant, run end-to-end (stubbed), expected output
- The fixture inputs (osmotic-pressure-paper.txt as a synthetic source; the 3-claim ledger)
- The expected `:sat` verdict and what it confirms
- A second walkthrough showing the `:unsat` case (doctored i=1) and what's in the unsat core

## Style authority

Use the existing repo skill family. Run these against every new prose file:

- **russellian-style linters.** From the skill root:

  ```
  cd skills/russellian-style
  .venv/Scripts/python.exe -m scripts.lint_hedges <file>
  .venv/Scripts/python.exe -m scripts.lint_passive_voice <file>
  .venv/Scripts/python.exe -m scripts.lint_signal_density <file>
  .venv/Scripts/python.exe -m scripts.lint_parallel_structure <file>
  .venv/Scripts/python.exe -m scripts.lint_sentence_rhythm <file>
  .venv/Scripts/python.exe -m scripts.lint_listicle_abstract <file>
  ```

  Critical findings on any linter block merge.

- **humanizer skill.** Apply the AI-fingerprint catalog: no em-dash overuse (more than ~1 per paragraph), no rule-of-three, no "key insight" / "essentially" / "fundamentally" / "Main theorem:" / "Proof strategy:", no numbered proof steps, no excessive bold.

- **Repo conventions.** Terse human commits, no AI attribution, no Co-Authored-By, no "Generated with Claude Code", no smileys or emoji, one problem per commit.

## Workflow

Use the superpowers stack the rest of this repo uses:

1. Read this brief end-to-end.
2. Invoke `superpowers:brainstorming` to confirm scope with the user. They have already pre-approved the four deliverables and the style authority; the brainstorm is for any open questions you surface while reading sources.
3. Invoke `superpowers:writing-plans` to produce a TDD-shaped plan. No Python tests, but each prose artifact gets a lint-pass checkpoint as its acceptance test.
4. Invoke `superpowers:subagent-driven-development` to execute. Dispatch one subagent per deliverable (4 total), plus subagents for the lint-pass checkpoints.
5. Open a single PR titled `docs: full neurosym-forge documentation`.

Use git worktrees for parallel agent edits. Create one off `origin/main` with a branch like `docs/neurosym-forge-documentation`.

## Acceptance criteria

- All four deliverables produced and committed
- Each new prose file passes russellian-style linters with zero critical findings
- Humanizer pass shows no critical findings on any new prose file
- Commits follow repo conventions (terse, no AI attribution, no Co-Authored-By)
- PR CI green: the existing lint-workflow + book-qa + book-thesis test jobs do not regress
- PR body lists the four deliverables and links to the spec at `docs/specs/2026-05-14-neurosym-forge-docs-handoff-design.md`

## Out of scope

- New skill features
- Changes to existing skills' SKILL.md beyond cross-linking
- Rewriting `skills/neurosym-forge/references/*.md` (those are reference detail; the new concepts doc summarises and links)
- Anything from PR-2 or PR-3 of the v0.3 mission (Bermuda real run, predicate expansion, osmotic-pressure scaffold)
- Touching `verifiers/bermuda/` content beyond linking
- Changes to the test suite
- Anything in `tools/`

## Open questions you might surface

If you find conflicts between sources or gaps in the existing content, raise them in the brainstorming session before writing. Common cases:

- The five `references/*.md` files were written across PR #14, PR #18, and PR #21 by different subagents and may have subtle terminology drift. The new concepts doc is the place to canonicalise terminology.
- The Bermuda `canonical.rs` predates the v0.3 `axioms.rs` hook; the v0.3 plan introduces a thin re-export shim. PR-2 lands this. The runbook should describe the v0.3 contract; do not document the Bermuda-specific shim as a general pattern.
- The `--book-knowledge-bridge` flag was removed in v0.1's QA pass, re-added in v0.2 (PR #18), and is the canonical way to scaffold a workspace-aware verifier. The runbook covers both with-flag and without-flag scaffolds.

## When you finish

Open the PR, paste the verdict counts (lint passes, line counts per deliverable), and close out. The next mission picks up at PR-2 of the v0.3 umbrella.
