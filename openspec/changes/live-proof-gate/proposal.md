# Change: live-proof-gate

**Sprint:** V4 of the v0.6 "claim-first prose, live" mission
**Branch:** `plan/v0.6-live-integration` (roadmap); execution branch `feat/live-proof-gate`
**Capability:** `proof-obligations` (extend)
**Roadmap:** `docs/specs/2026-06-18-kg-prose-live-integration-roadmap-design.md`
**Depends on:** V2 `live-writer-assertion` — the writer-assertion contract is what tells the gate which sentence asserts which claim as verified.

## Why

S7 built the proof-obligation gate and the render policy, but neither fires on a real build. The book-qa `gated-sentence-escape` gate reads `qa/gated-sentences.jsonl`, yet nothing emits that file on an actual chapter build; `halmos/proof_gate.py` carries the render policy but has no live caller. The gate is dormant: no rendered sentence is ever checked against its claim's obligation status, so an undischarged verified assertion can reach the prose unchecked.

V4 closes the S7 producer gap end-to-end. The live math/science writer pass emits `qa/gated-sentences.jsonl` from its rendered claims, the S7 book-qa gate fires on real builds, and a build whose final prose asserts an undischarged-unwaived gated claim hard-fails. The S7 machinery stays unchanged; V4 wires its producer and runs its consumer on the live path.

## What

1. The live math/science writer pass (halmos / book-compose) emits a `qa/gated-sentences.jsonl` row per rendered sentence recording the claim it asserts, that claim's obligation status, and the assertion kind.
2. Those emitted rows are the producer the S7 book-qa `gated-sentence-escape` gate reads on a real build.
3. While a claim's obligation is undischarged, the live pass renders it omitted or conjectural — not verified — applying the S7 render policy on the live path.
4. A build whose final prose asserts an undischarged-unwaived gated claim hard-fails the QA gate, end-to-end.
5. A waived obligation renders the claim conjecturally with the waiver noted on the real build.
6. Ownership: halmos/book-compose write only `qa/` and `chapters/`; book-qa owns the gate; book-knowledge owns the obligations; no live external verifier runs on the build's test path — the checker seam stays stubbed.

This is wiring, not new analysis: it reuses the landed S7 obligation entity, gate, and render policy, and routes the live pass's rendered claims into them.

## Scope

- This change ships the live `gated-sentences` producer and the end-to-end gating on a real build.
- It does **not** add the obligation entity, its lifecycle, or the checker seam — those landed in S7 and are reused unchanged.
- It does **not** add the writer-assertion contract — that is V2, on which this change depends.
- It does **not** introduce a live external verifier — the checker seam stays stubbed on the build's test path.

## Requirements

See `specs/proof-obligations/spec.md` (EARS). Summary:

| REQ id | Pattern | One-line |
|---|---|---|
| REQ-PROOF-010 | Event-driven | When the live pass renders a sentence asserting a claim, it emits a `qa/gated-sentences.jsonl` row recording the claim, the obligation status, and the assertion kind |
| REQ-PROOF-011 | Ubiquitous | The emitted gated-sentences are the producer the S7 book-qa gated-sentence-escape gate reads on a real build |
| REQ-PROOF-012 | State-driven | While a claim's obligation is undischarged, the live pass renders it omitted or conjectural and not verified |
| REQ-PROOF-013 | Unwanted | If a build's final prose asserts an undischarged, unwaived gated claim, the QA gate hard-fails that build end-to-end |
| REQ-PROOF-014 | Ubiquitous | The live pass writes only `qa/` and `chapters/`; the gate and obligations stay owned; no live external verifier runs on the test path |
| REQ-PROOF-015 | Optional | Where an obligation is waived, the live pass renders the claim conjecturally with the waiver noted |

## Out of scope

- The obligation entity, lifecycle, and checker seam (S7, landed — reused unchanged).
- The writer-assertion contract and sentence-level faithfulness checks (V2).
- A live external verifier — the checker seam stays stubbed on the build's test path.
