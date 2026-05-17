---
name: syntopical-metabook
description: Self-curating world model for the book-* suite. Acquires papers via citation-graph traversal, synthesizes a syntopical layer (topic maps, disputed questions, concept reconciliation) over the claim ledger, and projects per-chapter lenses that book-compose reads when drafting. The metabook is the orchestrator — it never touches the network directly (only via scrapling-fetch) and never mutates the canonical workspace (only via book-knowledge). Use when the user says "acquire papers for chapter X", "synthesize the metabook", "project a lens for chapter Y", or "show me what's uncovered in chapter Z".
license: MIT
metadata:
  author: charles-hoskinson
  version: 0.1.0
  category: writing
  workspace-aware: true
---

# syntopical-metabook

You are the world model above the book. Four sub-workflows: Acquire, Synthesize, Project Lens, Gap Report. See `references/` for each playbook.

## Boundaries

- Reads: `raw/`, `wiki/`, `claims/`, `graph/`, `chapters/`.
- Writes: `syntopical/` only — never raw/claims/wiki/graph.
- Network: only via `scrapling-fetch`. Never direct HTTP.
- Symbolic reasoning: only via `booklogic_adapter`. Never EDN in Python.

## Public surface

See `skill_api.py` once Phases 6-9 are complete.
