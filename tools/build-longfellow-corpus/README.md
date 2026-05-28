# build-longfellow-corpus

Run-once dev tool. Produces `skills/russellian-style/assets/longfellow-corpus/index.json`:
a small set of verified public-domain Longfellow anchor snippets (with source URL,
canto/section locator, technique tag, and prose translation) used by the russellian-style
liveness layer.

Two responsibilities:

- **Offline**, CI-tested: `segment_stanzas` (poetry-aware blank-line segmentation that
  preserves line breaks) and `build_index` (assemble the index from verified inputs).
- **Network**, run by the orchestrator: `fetch_work_markdown(url)` reaches Project
  Gutenberg through scrapling-fetch (the suite's network boundary). Set
  `SCRAPLING_FETCH_ROOT` and `SCRAPLING_FETCH_PYTHON`, then `python build_longfellow_corpus.py
  fetch <url>` writes clean markdown to stdout.

Snippets in `anchors.json` must appear verbatim in the fetched markdown of the cited
source. The skill's `lint_ornament` will flag any prompt that imports archaism, so anchors
are framed as `prose_translation` — borrow cadence and image-logic only.

Run tests with:

    python -m pytest tools/build-longfellow-corpus/test_segment.py -v
