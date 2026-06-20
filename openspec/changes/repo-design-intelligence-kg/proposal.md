# Change: repo-design-intelligence-kg

## Why

The repo already has three partial graphs: graphify's code graph,
book-knowledge's claim graph, and OpenSpec/docs as a human-readable design
record. They are valuable separately, but an agent still has to infer design
intent, test coverage, CI gates, and claim provenance by reading many files.

The goal is a design-intelligence knowledge graph: a source-backed graph an agent
can query to improve design, utility, testing, and documentation without relying
on broad keyword sweeps or unsupported summaries.

## What

- Extend the homoiconic KG model with design, test, CI, and traceability
  entities.
- Add an evidence-first link policy for code-to-claim, requirement-to-code,
  requirement-to-test, and design-to-implementation links.
- Define deterministic extraction passes for OpenSpec requirements, design docs,
  tests, CI workflows, and graphify code nodes.
- Define a query pack that lets agents ask impact, coverage, stale-doc, and
  design-rationale questions with source citations.
- Produce a graphify-backed design audit report that maps live code communities
  to requirements, tests, CI gates, claims, and open design risks.

## Out of scope

- Replacing graphify.
- Committing generated `graphify-out/` artifacts.
- Letting model-inferred links become canonical without deterministic evidence
  or review.
- Changing the production book pipeline before the graph has conformance tests.
