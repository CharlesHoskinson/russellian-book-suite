# Design: live chapter bundle input

## Live draft seam

`book-compose` had a documented chapter-drafting stage, but no tracked module that
implemented the live chapter-draft step. The only executable paths were the flat
`query_chapter_evidence.py` selector, release-bundle assembly, and book-level
assembly. V1 makes the live draft seam explicit in
`skills/book-compose/scripts/draft_chapter.py`.

The new `draft_chapter.draft_chapter(workspace, chapter_id, llm_call=...)` path is
the compose-owned chapter draft step. It writes the draft artifacts under
`chapters/drafts/<chapter_id>/` and is the path tested by
`test_live_chapter_bundle_input.py`. It does not call `query_chapter_evidence`;
that flat selector remains available for older tooling and release summaries but
is no longer the drafting scaffold.

## Bundle access

The draft step obtains its scaffold by calling
`chapter_bundle.build_chapter_bundle_input(workspace, chapter_id)`. That serializer
already loads `book-knowledge`'s `project_chapter_bundle` through
`sibling_skills`, validates the S1 bundle payload, and returns the payload plus the
bundle's prompt scaffold. V1 does not reimplement bundle projection or reshape the
S1 payload.

Bundle access is read-only over the ledger. `draft_chapter` reads the bundle and
writes only:

- `chapters/drafts/<chapter_id>/draft-prompt.md`
- `chapters/drafts/<chapter_id>/draft-scaffold.json`
- `chapters/drafts/<chapter_id>/draft.md`

## Scaffold shape

`build_bundle_scaffold(bundle)` converts the S1 bundle into the bounded writer
scaffold:

- `thesis-cue`: the bundle `prompt_scaffold`
- `dominant-communities`: copied from the bundle for a single top-community cue
- `support-claims`: load-bearing claims in bundle order, each paired with its
  minimal source-span anchor
- `caveats`: unresolved rebuttals copied from the bundle
- `flags`: bundle flags, including unanchored load-bearing claims

Load-bearing claims with no matching minimal anchor, or with the S1
`unanchored-load-bearing` flag, are withheld from `support-claims`. They are
surfaced under `flags` and are not presented as assertable support.

## Prompt construction

`render_drafting_prompt(scaffold)` is deterministic and testable without
generation. It renders:

- the thesis cue from the bundle prompt scaffold
- one dominant-community cue
- ordered support claims, each as claim id plus source-span anchor
- a caveat line per open rebuttal
- a flag line for unanchored load-bearing claims

The prompt carries only load-bearing, in-scope context instead of dumping the
entire bundle. This keeps the prompt within the v0.6 budget discipline while
preserving the claim-first, citation-first structure.

## Generation seam

`draft_chapter` requires an injected `llm_call` callable. Tests stub it and assert
against the deterministic prompt. No live model is invoked by the implementation
or tests.
