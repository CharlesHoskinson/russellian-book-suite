# Smoke Test — book-compose — 2026-05-09

## Automated verification (passes)

- 33/33 pytest tests pass: 3 sibling_skills + 4 chapter_contract + 3 preflight + 2 query_chapter_evidence + 3 chapter_contract_check + 2 evidence_summary + 2 build_release_bundle + 3 diff_drafts + 4 trigger calibration + 1 integration + 6 anthropic compliance.
- Skill is discoverable in Claude Code: confirmed in session-start skill registry as `book-compose` with the description loaded from SKILL.md.
- Six reference files in `references/` with substantive content (each ≥ 60 lines).
- 8 scripts present and exercising real behavior: sibling_skills.py, chapter_contract.py, preflight.py, query_chapter_evidence.py, chapter_contract_check.py, evidence_summary.py, build_release_bundle.py, diff_drafts.py.
- Asset files present: chapter-contract.schema.json, chapter-contract.template.yaml, release-manifest.schema.json, pandoc/manuscript.tex, pandoc/manuscript.html5, pandoc/citation-style.csl.
- Frontmatter passes Anthropic compliance: kebab-case name (`book-compose`), 717-char description, no XML, includes positive triggers and explicit negative triggers naming `book-knowledge` and `russellian-style` siblings.

## Cross-skill integration verified

book-compose imports both sibling skills' modules in-process via the `sibling_skills.load_*_module` alias-namespace pattern (works around the Python collision between three skills each with a `scripts/` package):

- `preflight.py` calls book-knowledge's `validate_shacl` and `run_competency_queries`.
- `chapter_contract_check.py` calls russellian-style's `lint_hedges`, `lint_passive_voice`, `lint_signal_density`, `lint_parallel_structure`, `iter_sentences`, `load_markdown`.
- `evidence_summary.py` reads book-knowledge's claim ledger via `read_claims`.
- `build_release_bundle.py` invokes book-knowledge's workspace + ledger modules to produce claim slices.

The integration test exercises all 5 stages of the chapter-compose pipeline end-to-end:
1. Stage 1: contract loading (`chapter_contract.load_contract`)
2. Stage 2: preflight (calls book-knowledge validators)
3. Stage 3: evidence query (3 verified claims found via SPARQL)
4. Stage 4: chapter contract check (russellian-style linters in-process)
5. Stage 5: release bundle (Markdown + manifest + evidence-summary + claims-slice)

## Local-only verification

- No HTTP libraries imported. No cloud SDKs. Stack is pyyaml + jsonschema + rdflib + pyshacl + spaCy + Pandoc CLI binary.
- Pandoc invocation degrades gracefully when not on PATH — Markdown output is always produced; PDF/EPUB/LaTeX outputs are skipped silently.

## Live-session triggering tests (pending user validation)

These require a fresh Claude Code session because the running session has the skill discoverable but cannot reliably test trigger behavior from inside the same conversation.

| Test | Prompt | Expected | Status |
|---|---|---|---|
| Positive 1 | "Generate an outline for ch-03 in /tmp/test-book." | book-compose activates | PENDING |
| Positive 2 | "Build the release bundle for chapter 3 version 0.1.0." | book-compose activates, build_release_bundle runs | PENDING |
| Positive 3 | "Render chapter 3 to PDF." | book-compose activates (and Pandoc-derived output is gated on Pandoc availability) | PENDING |
| Negative 1 | "Ingest this PDF into the book." | book-compose does NOT activate (book-knowledge handles ingest) | PENDING |
| Negative 2 | "Rewrite this passage in Russell style." | book-compose does NOT activate (russellian-style) | PENDING |
| Negative 3 | "Audit the knowledge graph." | book-compose does NOT activate (book-knowledge) | PENDING |

## Latency baseline (from automated suite)

- Full pytest suite: 3.84s wall-clock on Windows 11.
- preflight (SHACL + competency queries on small workspace): ~0.7s.
- chapter_contract_check (4 linters via russellian-style): ~3.0s (spaCy POS tag warm-up).
- build_release_bundle (markdown only, no Pandoc): ~0.2s.

## Known issues / deviations from plan

- The plan originally suggested `from scripts.X import` for cross-skill imports; this fails because all three skills (russellian-style, book-knowledge, book-compose) have their own `scripts/` package and Python's import system resolves the first one on path. The implementer added `load_book_knowledge_module(name)` and `load_russellian_style_module(name)` helpers in `sibling_skills.py` that load the sibling modules under aliased namespaces (`_book_knowledge_scripts`, `_russellian_style_scripts`). This is the canonical pattern for any future cross-skill work.
- Pandoc is not installed on this machine. Markdown output works; PDF/EPUB/LaTeX are gated on `pandoc --version` returning successfully. Run `winget install JohnMacFarlane.Pandoc` to enable.
- The shipped `assets/pandoc/citation-style.csl` is a placeholder; replace with chicago-author-date.csl from the citation-style-language repo for production publications.
- 647 `DeprecationWarning`s from rdflib/pyshacl internals during pytest. Functional only.

## Next steps

1. Run the six live-session tests above in a fresh Claude Code window.
2. Update this document with PASS/FAIL for each.
3. Install Pandoc to enable PDF/EPUB/LaTeX rendering.
4. The russellian-book-forge skill family is now complete: russellian-style + book-knowledge + book-compose.
