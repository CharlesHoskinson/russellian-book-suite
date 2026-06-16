# Triadic voice: Russell × Feynman × Hoskinson exemplar layer

Status: draft
Owner: russellian-style

## Problem

`russellian-style` calibrates a single voice — Bertrand Russell's analytic style — through three mechanisms: a style guide, a 50-paragraph Russell exemplar corpus (`assets/russell-corpus/index.json`), and deterministic linters for hedging, passive voice, signal density, parallel structure, rhythm, and listicle abstraction.

A single exemplar voice is a narrow target. Russell supplies rigor and atomic sentences but little warmth and no momentum. The goal is a richer writing target that fuses three voices: Russell's analytic discipline, Richard Feynman's intuition-first exposition (concrete analogy, "let me show you why," narrative warmth), and Charles Hoskinson's candor, forward momentum, direct address, and domain authority.

Voice and tone transfer through exemplars at generation time, not through deterministic rules. A linter can reject a hedge; it cannot encode Feynman's analogy or Hoskinson's cadence. So the fusion is built as an exemplar layer — two new corpora beside the existing Russell corpus, plus one synthesized fusion guide — while the existing linters stay in place as a discipline floor that all three voices must clear.

The Hoskinson corpus must be built from source. His spoken voice lives in years of YouTube uploads at `@charleshoskinsoncrypto` and is not available as text. This spec describes a resumable ingestion pipeline that discovers and samples those videos, pulls their captions, cleans them to exemplar passages, tags them with rhetorical metadata, and emits a corpus in the existing schema.

## Goals

- Add `skills/russellian-style/assets/hoskinson-corpus/index.json`, built from a stratified sample of `@charleshoskinsoncrypto` videos, with cleaned exemplar text stored inline.
- Add `skills/russellian-style/assets/feynman-corpus/index.json` as source pointers plus paraphrased style metadata only — no verbatim Feynman text.
- Add `skills/russellian-style/references/triadic-voice-guide.md`: one synthesized guide describing each voice's contribution, when each dominates, and how the discipline linters still apply.
- Add a resumable ingestion tool `tools/build-voice-corpus/` that produces the Hoskinson corpus end to end.
- All outbound discovery traffic routes through `scrapling-fetch`. Caption retrieval is the single, documented exception (yt-dlp), scoped strictly to caption tracks.
- No new linters; the existing `russellian-style` linters and skill API do not change.

## Non-goals

- No full-archive ingest. v1 samples ~150–300 videos; the manifest is structured to permit later expansion.
- No weighted "voice-blend" configuration. The fusion guide describes the blend in prose; numeric weighting is a later change if warranted.
- No new or relaxed linters. Feynman's warmth and Hoskinson's cadence are admitted through exemplars, not by loosening discipline checks.
- No browser/StealthyFetcher path. Channel discovery uses scrapling's basic HTTP Fetcher; browser binaries are not required.
- No change to `retrieve_corpus_anchor.py` retrieval behavior beyond reading the two new corpora.

## Voice contract (the fusion)

| Voice | Supplies | Copyright posture |
|---|---|---|
| Russell | analytic rigor, logical atomism, declarative active voice, no hedging | public domain (unchanged) |
| Feynman | concrete analogy, intuition before formalism, narrative warmth, first-person curiosity | copyrighted → pointers + paraphrased metadata only |
| Hoskinson | candor, forward momentum, direct address, domain authority | user's own content → inline text permitted |

The discipline floor is invariant: warmth and momentum are admitted, but hedging, passive voice, modifier bloat, and rhythm defects are still flagged by the existing linters.

## Where it lives

A resumable ingestion tool under `tools/build-voice-corpus/` with its own `.venv` and `pyproject.toml`, matching the convention that `tools/` holds synthesis and tagging utilities. It mirrors `tools/build-russell-corpus/`.

```
tools/build-voice-corpus/
├── pyproject.toml
├── scripts/
│   ├── discover.py          # scrapling-fetch → channel video list
│   ├── sample.py            # deterministic stratified sampler
│   ├── fetch_captions.py    # yt-dlp → VTT (prefer human subs, fall back to auto)
│   ├── clean.py             # VTT → de-timestamped, de-duped, sentence-segmented text
│   ├── style_tag.py         # LLM tagger → rhetorical_move + tags
│   ├── append_to_index.py   # emit/append hoskinson-corpus/index.json
│   ├── manifest.py          # resumable per-video state
│   └── corpus_io.py
├── assets/
│   ├── extractor-prompt.md  # style-tag prompt (mirrors build-russell-corpus)
│   ├── stock-fragments.yaml # intro/outro/ASR boilerplate to strip
│   └── feynman-sources.yaml # pointer allow-list for the Feynman corpus
└── tests/
    ├── test_sample.py            # determinism under fixed seed
    ├── test_clean.py             # VTT fixtures → expected passages
    ├── test_append_to_index.py   # schema validation
    ├── test_manifest.py          # resume skips completed stages
    └── fixtures/
        ├── sample.vtt
        ├── auto_sub.vtt
        └── channel_list.json
```

## Pipeline

Five stages, each driven off a per-video manifest so reruns skip completed work.

1. **Discover.** `scrapling-fetch` enumerates `@charleshoskinsoncrypto` uploads. Output: `{video_id, title, published, duration, format_hint}` rows. Rate-limited, cached, offline-mode honored. Failures map to the existing typed `scrapling-fetch` errors.

2. **Stratify and sample.** Deterministic (fixed-seed) selection of ~150–300 videos across `year × format (AMA / whiteboard / keynote / short) × length bucket`. `format` is inferred from title/duration heuristics. The same seed yields the same sample across reruns. The sampler logs the per-stratum counts; nothing is silently dropped.

3. **Fetch captions.** `yt-dlp` pulls each video's caption track, preferring human-uploaded subtitles and falling back to auto-generated. Output: one VTT per video. yt-dlp is the only network call outside `scrapling-fetch`; it is documented as a scoped exception in `scrapling-fetch`'s doctrine note. Videos with no captions, age-gated, or removed are recorded `skipped` with a reason — not fatal.

4. **Clean.** VTT → plain text: strip timestamps and cue tags, de-duplicate the rolling-window repetition that auto-subs produce, segment into sentences, and remove stock intro/outro and ASR boilerplate listed in `stock-fragments.yaml`. Output: candidate exemplar passages keyed by `video_id` + `t_start`.

5. **Style-tag.** An LLM reader tags representative passages with a `rhetorical_move` string and `tags`, reusing the `extractor-prompt.md` pattern. Tagged passages are appended to `hoskinson-corpus/index.json`. No live LLM in tests; the tagger takes an injected `llm_call` callable.

## Data schemas

Hoskinson corpus entry (inline text — his own content):

```json
{
  "id": "hoskinson-AMA-2024-03-12-007",
  "video_id": "abc123",
  "t_start": "00:14:22",
  "text": "Look, the thing people miss about governance is ...",
  "rhetorical_move": "reframes critique as a systems-design tradeoff",
  "tags": ["candor", "direct_address"]
}
```

Feynman corpus entry (pointer + paraphrased metadata only — copyrighted):

```json
{
  "id": "feynman-flp-I-22-003",
  "source": "feynman-lectures",
  "locator": "Vol I, Ch 22, §22-3",
  "url": "https://www.feynmanlectures.caltech.edu/I_22.html",
  "rhetorical_move": "builds intuition with a concrete analogy before the formal statement",
  "tags": ["analogy_first", "intuition_before_formalism"]
}
```

Both index files carry the existing top-level envelope (`version`, `*_count`, `copyright_policy`, `sources`, entry array), matching `russell-corpus/index.json`.

Feynman seed sources (`feynman-sources.yaml`, pointers only): Feynman Lectures on Physics (online edition); *Surely You're Joking* / *What Do You Care What Other People Think?*; *QED: The Strange Theory of Light and Matter* / *Lectures on Computation*.

## Copyright posture

- **Russell** — public domain (Project Gutenberg). Unchanged.
- **Hoskinson** — the user's own spoken content; cleaned exemplar text is stored inline.
- **Feynman** — copyrighted. The corpus stores source pointers (volume/chapter/section or URL) and paraphrased style metadata only. No verbatim Feynman text enters the repo. `feynman-sources.yaml` is the allow-list of permitted pointer sources, mirroring `pd-allow-list.yaml`.

## Error handling and robustness

- **Resumable manifest.** Per-video state machine: `discovered → sampled → fetched → cleaned → tagged`, plus terminal `skipped(reason)`. Reruns advance only incomplete videos.
- **Non-fatal caption gaps.** Missing/age-gated/removed captions record `skipped`; the run continues.
- **Rate limiting and caching** on discovery (via `scrapling-fetch`); yt-dlp throttled between videos.
- **Offline mode** (`SCRAPLING_OFFLINE=1`) honored for discovery; cached channel list reused.
- **Deterministic sampling** so a rerun reproduces the same corpus unless the seed or sample size changes.

## Testing

TDD per suite convention; no live network and no live LLM in tests.

- `test_sample.py` — fixed seed yields identical sample; per-stratum counts logged.
- `test_clean.py` — `sample.vtt` and `auto_sub.vtt` fixtures clean to expected passages; rolling-window dedup verified.
- `test_append_to_index.py` — emitted index validates against the corpus JSON schema; inline-text and pointer-only entries both accepted.
- `test_manifest.py` — a half-complete manifest resumes without re-fetching completed videos.
- Discovery and caption stages take injected `scrapling_fetch` / `yt_dlp` callables, stubbed in tests.

## Dependencies

- `tools/build-voice-corpus/` adds `yt-dlp` to its own `.venv`. `scrapling-fetch` is reused as-is (basic Fetcher; the `[fetchers]` extra is required on Python 3.14 — its 0.4.8 core metadata omits curl_cffi/playwright/browserforge).
- No new runtime dependency for `russellian-style`; it reads two more JSON files.

## Open questions

- Sample size within the 150–300 band, and exact stratum weights, are tuned during the first discovery run once channel volume per year is known.
- Whether the Feynman corpus is populated by hand from the allow-list or via a guarded extractor like `build-russell-corpus`'s cross-check stage. v1 assumes hand-curation against `feynman-sources.yaml`, since the set is small and copyright-sensitive.
