# Change: kg-code-claim-autolink

**Sprint:** S6 of the v0.5 KG-for-prose mission
**Branch:** `plan/kg-prose-roadmap` (roadmap); execution branch `feat/kg-code-claim-autolink`
**Capability:** `homoiconic-kg` (extend)
**Roadmap:** `docs/specs/2026-06-17-kg-prose-enhancement-roadmap-design.md`
**Depends on:** the current graphify code-graph ingestion only (the landed `homoiconic-kg` P4 fusion). Measured by S0 (`kg-prose-eval`). No upstream sprint.

## Why

The `code-claim-link` entity already exists in `kg-schema.edn`, and the code graph — `code-node`, `code-edge`, and the graphify-derived communities — is already joined into the store by the homoiconic-kg P4 fusion. But the links themselves are wholly explicit: every `code-claim-link` row is hand-authored. Nothing derives a link from the code graph it sits beside, so the writer's software descriptions rest on whatever a human happened to wire up.

The brief's move #7 derives links from deterministic evidence first — filenames, exact symbols, import/call edges — and stores that evidence, leaving learned ranking as a strictly second stage. Structural retrieval over the code graph reduces project-specific hallucination about the suite's own software, because a claim about a function is anchored to the `code-node` that actually defines it rather than to a paraphrase.

## What

1. Replace the wholly-explicit `code-claim-link` with a **derived** relation whose supporting evidence is stored in a new `link-evidence` relation (fields: `kind`, `score`, `witness`, `provenance`).
2. Stage-one deterministic signals only: a claim's `source.file` matches a `code-node` module path (`kind=file-path`); a mention resolves to a symbol present in `code-node` reached by a CONTAINS/USES trail (`kind=exact-symbol`).
3. Only deterministic (or thresholded-and-reviewed) links become canonical; ambiguous candidates are stored as evidence, never silently promoted. Learned ranking is deferred to S9.

## Scope

- This change ships the `link-evidence` relation (added to `kg-schema.edn`), the deterministic stage-one linker, and the canonical-promotion rule.
- It does **not** ship learned ranking via embeddings/GNN link-prediction (S9) — stage one is deterministic only; the learned candidate ranker that consumes `link-evidence` is a later sprint.
- It does **not** recompute the graphify code graph; S6 reads the existing `code-node`/`code-edge`/community relations, it does not re-ingest them.

## Requirements

See `specs/homoiconic-kg/spec.md` (EARS). Summary:

| REQ id | Pattern | One-line |
|---|---|---|
| REQ-KG-026 | Ubiquitous | The schema declares a `link-evidence` relation with `kind`, `score`, `witness`, `provenance` |
| REQ-KG-027 | Event-driven | When a claim's `source.file` matches a `code-node` module path, a `file-path` link is materialized with its evidence |
| REQ-KG-028 | Event-driven | When a mention resolves to a `code-node` symbol via a CONTAINS/USES trail, an `exact-symbol` link is materialized |
| REQ-KG-029 | Ubiquitous | Only deterministic or thresholded-reviewed links become canonical; lower-confidence candidates stay as `link-evidence` |
| REQ-KG-030 | Ubiquitous | The linker is deterministic over a snapshot (result-set-equal, golden-able) |
| REQ-KG-031 | Unwanted | If a mention is ambiguous, candidates are stored as evidence and none is promoted without the S9 decision |

## Out of scope

- Learned code↔claim ranking (TransE/RotatE/GNN link-prediction as a candidate ranker) — S9.
- Recomputing the graphify code graph (`code-node`/`code-edge`/community ingestion).
- The chapter-bundle's consumption of code links (S1, REQ-CHAP-007) — S6 produces the links; the bundle merely surfaces whatever is canonical.
