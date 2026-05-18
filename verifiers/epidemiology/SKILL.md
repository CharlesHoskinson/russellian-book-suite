---
name: epidemiology
description: Neurosymbolic verifier for Epidemiology Verifier. Use when verifying claim sets in this domain with FOL/SMT/e-graph/Datalog reasoning. Scaffolded by neurosym-forge.
license: MIT
metadata:
  version: 0.1.0
  category: verification
  emits: pdf
---

# Epidemiology Verifier verifier

Runs the four-phase neurosymbolic pipeline against a claim set.

## Usage

- `npm install && npm run build` — first-time setup
- `node cljs-orchestrator/dist/main.js verify work/claims.edn work/verdict.edn` — verify
- `node cljs-orchestrator/dist/main.js typeset work/report.md work/report.pdf` — typeset

## Extension

This project is a scaffold from `neurosym-forge`. Add rules and grounded atoms
via that skill, never by hand-editing `rules/*.edn`.
