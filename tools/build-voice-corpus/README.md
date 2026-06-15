# build-voice-corpus

Resumable pipeline that turns `@charleshoskinsoncrypto` YouTube videos into the
Hoskinson exemplar corpus used by `russellian-style`.

Stages: discover (scrapling-fetch) -> sample (deterministic stratified) ->
fetch_captions (yt-dlp) -> clean (VTT) -> style_tag (LLM) -> append_to_index.
Each network/LLM boundary is an injected callable; the unit suite runs offline.

## Setup

    py -3.14 -m venv .venv
    .venv/Scripts/python.exe -m pip install -e ".[test]"

## Test

    .venv/Scripts/python.exe -m pytest

## Run (live)

    .venv/Scripts/python.exe -m scripts.cli --workdir <dir> --index ../../skills/russellian-style/assets/hoskinson-corpus/index.json --target 200

`llm_call` must be wired to a model client in `main()` before a live run.
yt-dlp is the only network call outside scrapling-fetch, scoped to caption tracks.

## Generate (live)

Once a corpus exists, generate voice text grounded in it (needs ANTHROPIC_API_KEY):

    .venv/Scripts/python.exe -m scripts.generate --topic "why formal verification belongs at the base layer" --mode triadic

`--mode hoskinson` for pure Hoskinson voice, `--mode triadic` (default) for the Russell x Feynman x
Hoskinson fusion. `--model` overrides the model (default claude-opus-4-8). Generation is an injected
llm_call; the unit tests run offline with a stub.

## Copyright

Hoskinson transcripts are the channel owner's own content (stored inline). The
Feynman corpus stores pointers and paraphrased metadata only - no verbatim text.
