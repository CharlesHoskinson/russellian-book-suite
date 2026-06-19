# Repo design-intelligence KG - design

**Date:** 2026-06-19
**Status:** proposed
**OpenSpec:** `openspec/changes/repo-design-intelligence-kg/`

## Context

The repo has a graphify code map, a Cozo-backed claim graph, OpenSpec design
records, and CI/test metadata. Agents still have to stitch these sources
together manually before they can answer design questions. The missing layer is
a traceability graph that joins code, claims, requirements, tests, CI, and design
decisions with source provenance.

## Architecture

Use the existing homoiconic KG path:

1. Graphify extracts code topology.
2. `project_graphify` loads `code-node` and `code-edge`.
3. New deterministic extractors load design, test, CI, and operator entities.
4. New deterministic linkers create promoted traceability links where evidence
   is exact.
5. Weak or ambiguous matches remain evidence-only.
6. Named queries power agent planning, design review, and audit reports.

## Query surface

The first query pack should answer:

- What changes if this symbol or file changes?
- Why does this abstraction exist?
- Which requirements lack implementation, tests, or CI gates?
- Which high-centrality graphify communities are under-documented or untested?
- Which claims depend on this code?
- Which CI jobs protect this capability?

## Risk controls

- Extractors are read-only and deterministic.
- Every answer cites file and line provenance.
- Weak inferred links are never canonical by default.
- Generated graph artifacts stay out of git.
- The conformance harness fails loudly on backend divergence.

## Success criteria

- Every high-centrality graphify community has a coverage row.
- Every promoted requirement link has deterministic evidence or review evidence.
- Every named query returns source-backed rows.
- Agents can plan a change from graph answers before reading entire subsystems.
