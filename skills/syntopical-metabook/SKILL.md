---
name: syntopical-metabook
description: General-purpose knowledge-curation layer for a book/knowledge workspace. Five capabilities — Acquire (grow the source set by citation-graph traversal and ingest via book-knowledge), Synthesize (topic maps, disputed questions, concept reconciliation over the claim ledger), Lens (project a per-chapter view book-compose reads), Gap (score thesis-node coverage and feed uncovered nodes back to acquisition), and Govern (partition rule/claim support by curated schools of thought; render reports, consensus map, adversarial review, induction gate). Use when the user wants to acquire or expand sources, synthesize a cross-source view, project a per-chapter lens, find coverage gaps, or position induced/asserted rules against schools of thought. The skill never touches the network directly (only via scrapling-fetch) and never mutates the canonical workspace (only via book-knowledge); it writes only under syntopical/.
license: MIT
metadata:
  author: charles-hoskinson
  version: 0.3.0
  category: writing
  workspace-aware: true
---

# syntopical-metabook

The world model above the book. Five capabilities over a workspace, each
reachable from the `forge` CLI and exported from `skill_api.py`.

## Capabilities

| Capability | CLI | Playbook |
|---|---|---|
| Acquire | `forge meta acquire` | `references/acquire-playbook.md` |
| Synthesize | `forge meta synthesize` | `references/synthesize-playbook.md` |
| Lens | `forge meta lens` | `references/lens-and-gap-playbook.md` |
| Gap | `forge meta gap` | `references/lens-and-gap-playbook.md` |
| Govern | `forge govern …` | `references/governance-playbook.md` |

The author loop: **Acquire → Synthesize → Gap → (feed back to Acquire) →
Lens → book-compose**, with **Govern** as the quality gate over induced and
asserted rules.

## Boundaries

- Reads: `raw/`, `wiki/`, `claims/`, `graph/`, `chapters/`, `rules/`, `syntopical/schools/`.
- Writes: `syntopical/` only.
- Network: only via `scrapling-fetch`. Never direct HTTP.
- Symbolic reasoning: only via `booklogic_adapter`. Never EDN logic in Python.

## Public surface

`skill_api.py` (`API_VERSION = (0, 3)`) exports:

- Acquire: `expand_seeds`, `rank`, `triage`, `apply_veto`, `download_and_ingest`, `run_acquire`
- Synthesize: `build_topic_map`, `build_disputed_questions`, `build_concept_reconciliation`, `run_synthesize`
- Lens: `project_lens`
- Gap: `build_coverage_report`, `seed_from_gap_report`
- Govern: `build_positions`, `render_per_rule`, `render_consensus_map`, `render_adversarial`, `governance_filter`, `GateDecision`
