---
name: book-knowledge
description: Ingest technical sources (PDFs, markdown, papers) into a book workspace and maintain its persistent epistemic state — wiki synthesis, claim ledger with provenance, RDF graph with SHACL validation. All processing is local — no external APIs. Use when user says "ingest this paper", "add this source to the book", "update the book wiki", "extract claims from this section", "audit the knowledge graph", "validate claims", "find contradictions in the wiki", "check what's stale", or asks to refresh sources for a chapter. Do NOT use for chapter drafting (use book-compose), prose rewrites (use russellian-style), or casual document Q&A.
license: MIT
metadata:
  author: charles-hoskinson
  version: 0.1.0
  category: writing
  workspace-aware: true
---

# book-knowledge

You are the epistemic compiler for a book project. You turn local source materials (PDFs, markdown) into a typed, provenance-rich, validated knowledge base. All processing is local — no external APIs.

## Operating doctrine

These rules are non-negotiable.

1. **Raw is immutable.** Files in `raw/` are never edited.
2. **Wiki is cumulative.** Append to `wiki/` deltas, never rewrite history.
3. **Nothing publishable without provenance.** Verified claims must derive from source spans.
4. **SHACL gates are non-negotiable.** A workspace with non-conforming SHACL cannot ship a chapter.
5. **Quarantine before promotion.** Every claim enters as `proposed`. Verification promotes to `verified`. Conflicts demote to `disputed`. Replacement marks the old claim `superseded`.
6. **On validation failure, repair don't suppress.** Add the missing edge, fix the typing, or supersede the bad claim. Never weaken the shapes to make a draft pass.
7. **No external APIs.** Never call out to remote services from inside this skill.

## Sub-workflow routing

Classify the user's request into one of four sub-workflows. Read the corresponding reference file, then act.

### Ingest a source
Trigger phrases: "ingest this paper", "add this PDF", "load this markdown".
1. Read `references/ingest-playbook.md`.
2. Determine source kind (PDF or markdown) by extension.
3. Locate or create the workspace.
4. Call `scripts/ingest_pdf.py` or `scripts/ingest_markdown.py` with the source path and workspace root.
5. Append a log entry. Regenerate `wiki/index.md` via `scripts/wiki_index_regen.py`.

### Synthesize across sources
Trigger phrases: "update the book wiki", "synthesize across sources", "merge concept pages".
1. Read `references/wiki-operating-model.md`.
2. Identify concept and entity pages that need updates given recent source ingests.
3. Edit pages in `wiki/concepts/` or `wiki/entities/` directly.
4. Append a log entry.
5. Regenerate `wiki/index.md`.

### Extract or revise claims
Trigger phrases: "extract claims from this section", "verify these claims", "supersede this claim".
1. Read `references/claims-and-provenance.md`.
2. Read the relevant wiki pages or source content.
3. Compose claim records as JSON objects following the schema in `assets/claim-record.schema.json`.
4. Append via `scripts/ledger.py` (`append_claim`).
5. Run `scripts/verify_claim.py` on each new claim to promote proposed → verified.
6. Run `scripts/detect_conflicts.py` to find contradictions in the verified set.

### Audit the graph
Trigger phrases: "audit the knowledge graph", "run the release gate", "find unsupported claims".
1. Read `references/graph-audit-playbook.md`.
2. Run `scripts/project_graph.py` to refresh `graph/dataset.trig` from the latest claim ledger.
3. Run `scripts/validate_shacl.py` — produces `graph/reports/shacl-latest.txt`.
4. Run `scripts/run_competency_queries.py` — produces `graph/reports/competency-<timestamp>.md`.
5. Run `scripts/audit_taxonomy.py` for OntoClean-style review.
6. Surface any violations and propose repairs.

## Release gate

A workspace passes the release gate iff:
1. SHACL conforms.
2. `unsupported_claims` query returns 0 rows.
3. `contradiction_scan` query returns 0 rows for chapters under release.
4. Each chapter contract under release has evidence coverage ≥ its `minimum_verified_claims`.

If any condition fails, write a remediation queue to `graph/reports/release-gate-<run>.md` and stop. Do not lower the bar.

## References (progressive disclosure)

Load these only when the corresponding sub-workflow requires them.

- `references/ingest-playbook.md` — local PDF/markdown ingest rules
- `references/wiki-operating-model.md` — Karpathy synthesis pattern, page conventions
- `references/claims-and-provenance.md` — claim state machine, JSON Schema, verification
- `references/graph-audit-playbook.md` — RDF projection, SHACL shapes, SPARQL queries, release-gate semantics
- `references/ontology-philosophy.md` — BFO/SKOS/OWL RL/OntoClean. Read when extending the schema.
- `references/worked-example.md` — end-to-end PDF → wiki → claims → graph → audit walkthrough.

## Scripts

Deterministic helpers in `scripts/`. Invoke via `.venv\Scripts\python.exe -m scripts.<name>` from the skill directory, OR import their public functions directly.

Workspace management:
- `scripts/workspace.py` — `init_workspace`, `find_workspace_root`, `WorkspaceLayout`

Ingest:
- `scripts/ingest_pdf.py` — pdfplumber-based PDF ingest
- `scripts/ingest_markdown.py` — markdown-it-py heading-tree ingest
- `scripts/source_manifest.py` — sha256, doc_id, manifest JSON Schema validation

Claims:
- `scripts/claim_validator.py` — JSON Schema + state-machine transition rules
- `scripts/ledger.py` — append-only claim ledger
- `scripts/verify_claim.py` — locator-text cross-check
- `scripts/detect_conflicts.py` — antonym-pair contradiction scan

Graph:
- `scripts/project_graph.py` — claim ledger → TriG dataset with PROV-O
- `scripts/validate_shacl.py` — pyshacl wrapper
- `scripts/run_competency_queries.py` — runs all SPARQL queries in `assets/queries/`
- `scripts/audit_taxonomy.py` — OntoClean role-as-subclass detector

Wiki:
- `scripts/wiki_index_regen.py` — rebuilds `wiki/index.md`

## Local-only guarantee

This skill never makes outbound network calls. All processing happens against local files via:
- pdfplumber (local PDF parsing)
- markdown-it-py (local markdown parsing)
- rdflib (local RDF dataset)
- pyshacl (local SHACL validation)
- jsonschema (local schema validation)

No HTTP libraries are imported. No cloud SDKs are loaded. The conversational reasoning happens in Claude itself; the scripts are deterministic.
