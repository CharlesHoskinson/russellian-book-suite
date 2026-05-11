---
name: book-compose
description: Compile chapter drafts from a validated book workspace. Loads chapter contracts, queries verified claims, generates outline then sections, applies Russellian style, runs release-gate validation, and produces release bundles (Markdown plus optional PDF/EPUB/LaTeX). All processing is local — no external APIs. Use when user says "draft chapter X", "compile chapter from contract", "build release bundle for chapter X", "render chapter to PDF", "build the book release", or "publish the book". Do NOT use for source ingestion (use book-knowledge) or prose-only rewrites (use russellian-style). Also builds book-level releases (manuscript Markdown, React+Tailwind HTML browser, Playwright PDF). Stage 4 includes a multi-persona editorial review (Gottlieb, Lay Reader, Domain Expert, Copyeditor, Enjoyment Reader) via the book-review sibling; chapter releases soft-gate on `persona_critical_count == 0`.
license: MIT
metadata:
  author: charles-hoskinson
  version: 0.1.0
  category: writing
  workspace-aware: true
  invokes: russellian-style
---

# book-compose

You compile validated knowledge into reader-facing chapter drafts and book releases. You read the workspace state read-only; you write only into `chapters/` and `book/releases/`.

## What it owns

- Chapter contracts, outlines, drafts under `chapters/`.
- Release bundles under `chapters/releases/<chapter_id>-<version>/`.
- Book-level releases under `book/releases/<version>/`: manuscript Markdown, HTML, PDF, summary, manifest, bibliography, chapter-bundle copies.
- The release-gate (contract checks, style linters, humanizer, persona aggregation).

## What it does NOT own

- Source ingestion, claim extraction, SHACL validation — `book-knowledge`.
- Sentence-grain prose rewriting — `russellian-style`.
- Persona prompt bodies and aggregation primitives — `book-review`.
- Post-build mechanical/editorial gating — `book-qa`.
- General document Q&A unconnected to a chapter contract.

## Pipeline stages

1. **Contract** — load `chapters/contracts/<chapter_id>.yaml`; scaffold if missing.
2. **Pre-flight gate** — call book-knowledge SHACL + competency queries in-process.
3. **Claim slice** — SPARQL query for verified claims supporting the chapter.
4. **Outline** — section plan with claim assignments; user approval before drafting.
5. **Draft** — per-section: select claims → first pass → `russellian-style` → `humanizer` → write back.
6. **Linters** — `chapter_contract_check.py` enforces hedge / passive / listicle / rhythm / citation / `ai_fingerprint_total == 0`.
7. **Personas** — `persona_review_pass.prepare_packets`; one Task subagent per persona; `aggregate` produces `persona-review.md`; soft-gate `persona_critical_count == 0`.
8. **Chapter bundle** — `build_release_bundle.py` writes draft.md + evidence-summary.md + claims-slice.jsonl + manifest.yaml + optional Pandoc renders.
9. **Book release (explicit only)** — `book_preflight` → `build_book` → React/Tailwind/shadcn injection via `web-artifacts-builder-anthropic` → Playwright PDF.

## Components

- `chapter_contract.py`, `chapter_contract_check.py` — load, validate, check.
- `preflight.py`, `query_chapter_evidence.py`, `evidence_summary.py`, `toc.py`.
- `humanizer_pass.py`, `persona_review_pass.py`, `sibling_skills.py`.
- `build_release_bundle.py`, `diff_drafts.py`.
- `book_preflight.py`, `book_summary.py`, `render_book_html.py`, `print_pdf.py`, `build_book.py`.

## Outputs

- `chapters/drafts/<chapter_id>/{outline.md, draft.md, persona-review.md, style-report.md}`.
- `chapters/releases/<chapter_id>-<version>/{draft.md, evidence-summary.md, claims-slice.jsonl, manifest.yaml, draft.pdf|epub|tex}`.
- `book/releases/<version>/{manuscript.md, manuscript.html (React/Tailwind/shadcn), manuscript.pdf (Playwright), summary.json, book-manifest.yaml, claims-bibliography.jsonl, chapter-bundles/}`.

## Composes with

- `book-knowledge` — pre-flight + claim slice (in-process import).
- `russellian-style` — per-section invocation + linter calls.
- `humanizer` — per-section invocation + assess_draft.
- `book-review` — persona dispatch packets and aggregation.
- `web-artifacts-builder-anthropic` — book HTML browser.
- `book-qa` — runs after `build_book`, before shipping.

## Usage

- "draft chapter ch-NN" — Stages 1–7, write `chapters/drafts/ch-NN/draft.md`.
- "build release bundle for ch-NN v0.3" — Stage 8.
- "build the book release v1.0" — Stage 9 (explicit only; never auto-triggered).

## Tests

Run `.venv\Scripts\python.exe -m pytest tests/` from the skill directory. Coverage: contract loader, preflight wrapper, evidence query, chapter-contract-check linters, humanizer detector, bundle assembly, book-preflight, render_book_html determinism.

## Lessons

See [MEMORY.md](MEMORY.md) for release-surfaced patterns: orphan `[clm-…]` tokens (strip thrice), "Claim ledger:" footnote noise, numeric-name footnote false-strips, CommonMark blank-line after `</section>`, Tailwind preflight flattening headings, contract-driven chapter titles, middle-batch context rot, prompt patterns that work or fail.
