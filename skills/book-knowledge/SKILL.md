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

The epistemic compiler for a book workspace. Turns local sources into a typed, provenance-rich, SHACL-validated knowledge base that downstream skills read as ground truth.

## What it owns

- `raw/` — immutable source files and manifests
- `wiki/` — cumulative synthesis pages, append-only log, current-status
- `claims/` — append-only claim ledger and conflict records
- `graph/` — projected RDF dataset, SHACL shapes, validation and query reports

## What it does NOT own

- `chapters/` — written by book-compose; read-only here
- Prose style, persona review, Q&A — delegated to siblings
- Network I/O — this skill never reaches off-machine

## Components

Deterministic helpers in `scripts/`. Invoke via `.venv\Scripts\python.exe -m scripts.<name>`, or import directly.

Workspace and ingest:
- `workspace.py` — `init_workspace`, `find_workspace_root`, `WorkspaceLayout`
- `ingest_pdf.py`, `ingest_markdown.py`, `ingest_common.py` — pdfplumber and markdown-it-py source ingest
- `source_manifest.py` — sha256, doc_id, manifest schema

Claim ledger:
- `claim_validator.py` — schema plus state machine (proposed → verified → disputed → superseded)
- `ledger.py` — append-only claim ledger
- `verify_claim.py` — locator-text cross-check; promotes proposed to verified
- `detect_conflicts.py` — antonym-pair contradiction scan

RDF graph, SHACL, SPARQL:
- `project_graph.py` — ledger to TriG with PROV-O
- `validate_shacl.py` — pyshacl wrapper; writes `graph/reports/shacl-latest.txt`
- `audit_taxonomy.py` — OntoClean role-as-subclass detector
- `run_competency_queries.py` — runs every query in `assets/queries/`

Wiki:
- `wiki_index_regen.py` — rebuilds `wiki/index.md` from page front-matter

Schemas, SHACL shapes, and SPARQL queries ship in `assets/`. Progressive-disclosure docs in `references/`: `ingest-playbook.md`, `wiki-operating-model.md`, `claims-and-provenance.md`, `graph-audit-playbook.md`, `ontology-philosophy.md`, `worked-example.md`.

## Workspace layout

```
<workspace>/
  CLAUDE.md                    # workspace marker
  raw/{pdf,markdown,manifests}/
  wiki/
    index.md  log.md  current-status.md
    sources/  concepts/  entities/  chapters/
  claims/
    ledger.jsonl  conflicts.jsonl  verification/
  graph/
    dataset.trig  shapes.ttl
    imports/  reports/
  chapters/{contracts,drafts,releases}/    # owned by book-compose
  reports/
```

## Composes with

- **russellian-style** — invoked by book-compose on drafted prose; never from here
- **book-compose** — consumes verified claims and SHACL reports to draft chapters
- **book-review** — runs persona passes against drafted chapters
- **book-qa** — final mechanical and editorial gate over built artefacts

## Usage

```bash
.venv\Scripts\python.exe -m scripts.workspace init <workspace>
.venv\Scripts\python.exe -m scripts.ingest_pdf <source.pdf> <workspace>
.venv\Scripts\python.exe -m scripts.verify_claim <workspace>
.venv\Scripts\python.exe -m scripts.project_graph <workspace>
.venv\Scripts\python.exe -m scripts.validate_shacl <workspace>
.venv\Scripts\python.exe -m scripts.run_competency_queries <workspace>
```

Release gate: SHACL conforms, `unsupported_claims` returns zero, `contradiction_scan` returns zero for chapters under release, and each contract meets its `minimum_verified_claims`. On failure, write `graph/reports/release-gate-<run>.md` and stop.

## Tests

```bash
.venv\Scripts\python.exe -m pytest tests/
```

`tests/` covers every script plus integration, Anthropic compliance, and trigger calibration. Smoke results in `tests/smoke-results.md`.
