# Design: live writer assertion

## Live path

V2 extends the V1 `draft_chapter.draft_chapter` path. The live flow now runs:

1. load the chapter-retrieval bundle through `chapter_bundle`
2. build the V1 scaffold and bounded prompt
3. generate draft prose through the injected `llm_call`
4. split emitted prose into paragraphs and sentences
5. record each emitted sentence with the S2 writer-assertion contract
6. resolve each assertion through the S2 faithfulness + revise/downgrade policy
7. decompose each resolved paragraph into atomic facts
8. block paragraphs with novel-draft-claims and route proposals through book-qa
9. assemble only passing paragraphs into `draft.md`

The contract therefore runs inside the live draft step. It is not a parallel
helper.

## Sentence binding

The binding rule is deterministic and scaffold-derived. The V1 scaffold presents
support claims in bundle order, each paired with one minimal anchor. After
generation, the live path binds emitted sentence N to support claim N and its
anchor. If the generator emits more sentences than support claims, extra
sentences bind to the last support claim. If no anchored support claim exists,
the draft step fails rather than recording an unbound assertion.

This preserves the V1 prompt budget: the generator still receives one bounded
bundle prompt, while the assertion layer gets a stable claim/span binding for
every emitted sentence.

## S2 reuse

`draft_chapter` calls the landed S2 functions directly:

- `record_generated_sentence`
- `resolve_for_publication`
- `decompose_paragraph`
- `record_atomic_facts`
- `evaluate_paragraph_publication`

`writer_assertion.py` remains the contract owner. V2 only wires it onto the live
path and persists the resolved live assertion rows under the chapter draft
directory.

## Injected seams

The model-touching points are injectable:

- `llm_call` for initial draft generation
- `faithfulness_llm_call` for sentence-to-span status
- `revise_call` for revise-from-span
- `decomposer_llm_call` for atomic-fact decomposition

Tests stub all four. The defaults are deterministic offline fallbacks so no live
model or network call is introduced by the implementation.

## Novel-draft-claim routing

Atomic facts are mapped against known scaffold claims by the S2 decomposer. Facts
without an existing claim become `novel-draft-claim` records. A paragraph with a
novel-draft-claim is withheld from `draft.md`; its proposal is routed through the
book-qa `attributed_generation_writeback.write_novel_draft_claim_proposals`
writer, loaded via `sibling_skills`, which appends to
`qa/proposed-transitions.jsonl`. `book-compose` never writes `claims/`.

## Draft artifacts

The live step writes:

- `chapters/drafts/<chapter_id>/draft-prompt.md`
- `chapters/drafts/<chapter_id>/draft-scaffold.json`
- `chapters/drafts/<chapter_id>/writer-assertions.jsonl`
- `chapters/drafts/<chapter_id>/draft-atomic-facts.jsonl` when facts exist
- `chapters/drafts/<chapter_id>/blocked-paragraphs.json`
- `chapters/drafts/<chapter_id>/draft.md`

The only non-`chapters/` write is the book-qa-owned proposal route for
novel-draft-claims.
