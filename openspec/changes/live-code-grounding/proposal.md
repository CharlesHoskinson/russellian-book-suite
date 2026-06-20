# Change: live-code-grounding

**Sprint:** V5 of the v0.6 "claim-first prose, live" mission
**Branch:** `plan/v0.6-live-integration` (roadmap); execution branch `feat/live-code-grounding`
**Capability:** `claim-first-drafting` (extend)
**Roadmap:** `docs/specs/2026-06-18-kg-prose-live-integration-roadmap-design.md`
**Depends on:** V1 `live-chapter-bundle-input` (the scaffold). Consumes the landed S6 deterministic `code-claim-link` relation.

## Why

S6 derives deterministic canonical `code-claim-link` rows — a claim bound to a code symbol by file path plus exact symbol, with ambiguous candidates kept evidence-only — but the writer never sees them: they are not surfaced into the V1 drafting scaffold. A software chapter therefore drafts software descriptions with no view of the actual code graph, exactly the invented-API risk the deterministic linker was built to remove.

V5 surfaces the canonical links for software chapters. Once the scaffold pairs a load-bearing claim with its linked code symbol or module, the writer grounds the software description in the code graph rather than in recall. Only canonical (deterministic, unambiguous) links are shown; ambiguous evidence-only candidates stay invisible, so the scaffold never offers a false anchor. This is wiring, not new analysis: it reads the landed S6 links and routes the canonical subset into the existing scaffold.

## What

1. For a software chapter, the scaffold surfaces the canonical `code-claim-link` rows for its claims so the writer grounds software descriptions in the code graph.
2. Only canonical (deterministic, unambiguous) links are surfaced; ambiguous/evidence-only candidates are not shown.
3. A load-bearing claim with a canonical link is paired with its linked code symbol or module in the scaffold.
4. The grounding is read-only over the code graph + ledger and deterministic over a snapshot.
5. A claim with only evidence-only (ambiguous) links gets no code grounding — no false anchor.
6. A non-software chapter (no code links) omits the code-grounding section rather than emitting an empty required block.

Ownership: book-compose consumes the landed S6 links via `sibling_skills`; the access is read-only over the code graph and the ledger.

## Scope

- This change ships the code-grounding section of the V1 scaffold.
- It does **not** add the deterministic linker itself (S6, landed), learned code↔claim ranking (S9), the bundle scaffold (V1), or the warning surface (V3).
- It does not recompute or modify the S6 `code-claim-link` relation.

## Requirements

See `specs/claim-first-drafting/spec.md` (EARS). Summary:

| REQ id | Pattern | One-line |
|---|---|---|
| REQ-DRAFT-013 | Optional | Where a chapter describes software, the scaffold surfaces the canonical code-claim-links for its claims so the writer grounds software descriptions in the code graph |
| REQ-DRAFT-014 | Ubiquitous | Only canonical (deterministic, unambiguous) code-claim-links are surfaced; ambiguous evidence-only candidates are not shown |
| REQ-DRAFT-015 | Event-driven | When a load-bearing claim has a canonical code-claim-link, the scaffold pairs the claim with its linked code symbol or module |
| REQ-DRAFT-016 | Ubiquitous | The code grounding is read-only over the code graph and ledger, and deterministic over a snapshot |
| REQ-DRAFT-017 | Unwanted | If a claim has only evidence-only (ambiguous) links, the scaffold surfaces no code grounding for it |
| REQ-DRAFT-018 | Ubiquitous | A non-software chapter with no code links omits the code-grounding section rather than emitting an empty required block |

## Out of scope

- The deterministic code↔claim linker (S6, already landed).
- Learned code↔claim ranking (S9).
- The bundle-driven scaffold itself (V1) and the grounded/contradiction/confidence warning surface (V3).
- Any change to the S6 `code-claim-link` relation or to its precision/recall computation.
