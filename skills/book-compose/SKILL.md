---
name: book-compose
description: Compile chapter drafts from a validated book workspace. Loads chapter contracts, queries verified claims, generates outline then sections, applies Russellian style, runs release-gate validation, and produces release bundles (Markdown plus optional PDF/EPUB/LaTeX). All processing is local — no external APIs. Use when user says "draft chapter X", "compile chapter from contract", "build release bundle for chapter X", "render chapter to PDF", "build the book release", or "publish the book". Do NOT use for source ingestion (use book-knowledge) or prose-only rewrites (use russellian-style). Also builds book-level releases (manuscript Markdown, React+Tailwind HTML browser, Playwright PDF). Stage 4 now includes a multi-persona editorial review (Gottlieb, Lay Reader, Domain Expert, Copyeditor, Enjoyment Reader) via the book-review sibling skill; chapter releases soft-gate on `persona_critical_count == 0`.
license: MIT
metadata:
  author: charles-hoskinson
  version: 0.1.0
  category: writing
  workspace-aware: true
  invokes: russellian-style
---

# book-compose

You compile validated knowledge into reader-facing chapter drafts. You read the workspace state read-only; you write only into `chapters/`. You invoke `russellian-style` after each section is drafted.

## Operating doctrine

These rules are non-negotiable.

1. **Never speculate beyond verified claims.** Every cited claim has status=verified.
2. **The chapter contract is the acceptance specification.** Not a suggestion.
3. **A draft is an earned conclusion** derived from verified premises and the chapter contract's stated thesis.
4. **On release-gate failure, surface the remediation queue and stop.** Do not lower the bar.
5. **Every drafted section gets a russellian-style pass before write.**
6. **No external APIs.** All processing is local. Pandoc is a local binary.

## Five-stage workflow

### Stage 1: Contract loading
1. Read `references/chapter-contract-spec.md`.
2. Load `chapters/contracts/<chapter_id>.yaml` via `scripts/chapter_contract.py:load_contract`. Validation errors block the pipeline.
3. If the contract is missing, run `scripts/chapter_contract.py:scaffold_contract(<chapter_id>, <out_path>)` to generate a skeleton. Ask the user to fill required fields.

### Stage 2: Pre-flight gate
1. Read `references/release-bundle-format.md` for the gate semantics.
2. Run `scripts/preflight.py:preflight(workspace)`. The function calls book-knowledge's validate_shacl + run_competency_queries in-process.
3. On failure, write `chapters/drafts/<chapter_id>/blocked.md` with the issues list and stop. Do NOT proceed to outline.

### Stage 3: Outline
1. Read `references/outline-discipline.md`.
2. Run `scripts/query_chapter_evidence.py:query_chapter_evidence(workspace, chapter_id)` to enumerate verified claims available to this chapter.
3. Generate the outline as `chapters/drafts/<chapter_id>/outline.md` with section plan, claim assignments per section, and evidence-density forecast.
4. Ask the user to approve the outline before drafting begins.

### Stage 4: Section drafting and review

1. Read `references/drafting-playbook.md`.
2. For each outline section:
   - Select the verified claims assigned to this section.
   - Write a first draft with code-as-proof discipline.
   - Invoke the `russellian-style` Skill tool — applies the analytic discipline (no hedging, active voice, atomic propositions, no listicle abstract, varied rhythm).
   - Invoke the `humanizer` Skill tool — strips residual AI fingerprints.
   - Write the styled section back. Append the style-pass-report and humanizer-report to a chapter-level report.
3. Concatenate sections into `chapters/drafts/<chapter_id>/draft.md`.
4. Run `scripts/chapter_contract_check.py:check_draft` — verifies russellian + humanizer + listicle + rhythm + citation acceptance metrics.
5. Run persona reviews via `scripts/persona_review_pass.py`:
   - `prepare_packets(workspace, chapter_id)` returns one DispatchPacket per persona (default: gottlieb, lay-reader, domain-expert, copyeditor, enjoyment-reader).
   - For each packet, issue a Task-tool call with `prompt=packet.prompt`. The subagent reads the persona body, reads the chapter prose, and writes its review at `packet.output_path`.
   - After all five subagents complete, call `aggregate(workspace, chapter_id)` to produce `chapters/drafts/<chapter_id>/persona-review.md`.
6. Re-run `chapter_contract_check.py:check_draft`. The contract now includes `persona_critical_count == 0` and `persona_reviews_complete == True`. If those fail, surface the aggregated critical findings and revise the draft (loop back to step 2).

### Stage 5: Release bundle
1. Read `references/release-bundle-format.md`.
2. Run `scripts/build_release_bundle.py:build_release_bundle(workspace, chapter_id, version, formats)`.
3. The bundle lands at `chapters/releases/<chapter_id>-<version>/` with: draft.md, evidence-summary.md, claims-slice.jsonl, manifest.yaml, plus draft.pdf/draft.epub/draft.tex when Pandoc is available.

### Stage 6: Book release (explicit only)

Run only when the user explicitly asks for a book-level release. Book builds never auto-trigger from chapter-bundle builds.

1. Read `references/book-release-format.md` and `references/web-app-design.md`.
2. Run `scripts/book_preflight.py:book_preflight(workspace, chapter_versions)`. On failure, surface the issues list and stop.
3. Run `scripts/build_book.py:build_book(workspace, version, chapter_versions, book_title, book_id)`. This produces:
   - `book/releases/<version>/manuscript.md` — concatenated source of truth
   - `book/releases/<version>/manuscript.html` — deterministic skeleton with inlined book payload
   - `book/releases/<version>/summary.json` — chapter abstracts + section headings + word counts
   - `book/releases/<version>/book-manifest.yaml` — schema-validated metadata
   - `book/releases/<version>/claims-bibliography.jsonl` — verified claims for the book scope
   - `book/releases/<version>/chapter-bundles/<chapter-id>-<version>/` — copy of each chapter release
4. Invoke the `web-artifacts-builder-anthropic` Skill tool, passing the summary.json and the manuscript.md text. Instruct the skill to render a React+Tailwind+shadcn book browser into the BOOK_APP_INSERTION_POINT marker in `manuscript.html`. Required components: TOC sidebar, reader pane, executive summary card, per-chapter abstracts, source bibliography, search bar, theme toggle. Print-CSS rules per `references/web-app-design.md`.
5. If Playwright + Chromium are installed, `build_book` automatically renders manuscript.html to manuscript.pdf via `print_pdf.py`. Otherwise the PDF step is skipped silently.

## Russellian-style integration contract

Two enforcement points:
1. **Per-section invocation** during Stage 4 — the skill rewrites prose deterministically.
2. **Acceptance-test fields** in the chapter contract (`hedge_count == 0`, `passive_voice_ratio < 0.05`) verified in Stage 4 by `chapter_contract_check.py`, which calls russellian-style's linters in-process via `sibling_skills.load_russellian_style_module`.

A draft fails release if hedge density or passive-voice ratio exceeds threshold.

Workspace-level overrides: an optional `<workspace>/style-overrides.json` is exposed to russellian-style via the `RUSSELLIAN_OVERRIDES` env var. `chapter_contract_check.py` discovers the workspace root by walking up from the draft until it finds a directory containing `CLAUDE.md`, then sets the env var if `style-overrides.json` exists. The path constant is `sibling_skills.workspace_style_overrides_path(workspace)`.

## Humanizer integration contract

Two enforcement points, mirroring russellian-style:
1. **Per-section invocation** during Stage 4 — Claude invokes the `humanizer` Skill tool after russellian-style on each section to remove residual AI fingerprints.
2. **Acceptance-test fields** in the chapter contract (`ai_fingerprint_total == 0`) verified in Stage 4 by `chapter_contract_check.py`, which calls `humanizer_pass.assess_draft` in-process. The deterministic detector covers AI vocabulary words, filler phrases, and inflated symbolism. The `em_dash_count` metric is informational; it does not contribute to `ai_fingerprint_total`.

A draft fails release if `ai_fingerprint_total > 0`.

## References (progressive disclosure)

Load these only when the corresponding stage requires them.

- `references/chapter-contract-spec.md` — YAML schema and three example contracts
- `references/outline-discipline.md` — axiomatic outline rules, sideways-drift detection
- `references/drafting-playbook.md` — section workflow, code-as-proof, citation density
- `references/release-bundle-format.md` — bundle layout and reproducibility
- `references/pandoc-templates.md` — template selection and per-book overrides
- `references/worked-example.md` — end-to-end walkthrough

## Scripts

Deterministic helpers in `scripts/`. Invoke via `.venv\Scripts\python.exe -m scripts.<name>` from the skill directory, OR import their public functions directly.

- `scripts/sibling_skills.py` — locates russellian-style and book-knowledge; provides `load_*_module` helpers
- `scripts/chapter_contract.py` — load_contract, scaffold_contract, validate_contract
- `scripts/preflight.py` — preflight (calls book-knowledge validators in-process)
- `scripts/query_chapter_evidence.py` — SPARQL query for verified claims supporting a chapter
- `scripts/chapter_contract_check.py` — check_draft (calls russellian-style linters + humanizer_pass in-process)
- `scripts/humanizer_pass.py` — assess_draft (deterministic AI-fingerprint detector)
- `scripts/persona_review_pass.py` — wrapper around the book-review sibling skill: prepare dispatch packets and aggregate persona reviews.
- `scripts/toc.py` — build_toc, lookup_chapter (workspace-wide chapter index)
- `scripts/evidence_summary.py` — per-chapter cited-claims summary
- `scripts/build_release_bundle.py` — assembles the release bundle, wraps Pandoc
- `scripts/diff_drafts.py` — compare two draft versions

Book-level (explicit invocation):
- `scripts/book_preflight.py` — verify chapter releases + SHACL before building the book
- `scripts/book_summary.py` — collect per-chapter data + assemble the React-app payload
- `scripts/render_book_html.py` — write the deterministic HTML skeleton with inlined payload
- `scripts/print_pdf.py` — Playwright headless Chromium prints HTML to PDF
- `scripts/build_book.py` — orchestrator

## Local-only guarantee

This skill never makes outbound network calls. All processing happens locally via:
- pyyaml (YAML loading)
- jsonschema (schema validation)
- rdflib + pyshacl (graph queries via book-knowledge sibling)
- spaCy (POS tagging via russellian-style sibling)
- Pandoc CLI binary (local subprocess)

No HTTP libraries imported. No cloud SDKs. The conversational reasoning happens in Claude itself.
