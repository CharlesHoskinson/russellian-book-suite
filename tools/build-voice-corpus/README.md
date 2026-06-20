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

## Generate

In a Claude session this is a SKILL, not an API call — the running model reads the corpus + the
triadic-voice guide and writes the passage directly. No API key, no `anthropic` package. See
`skills/triadic-voice/SKILL.md`.

To assemble the corpus-grounded prompt without any model call (e.g. to hand to a session):

    .venv/Scripts/python.exe -m scripts.generate --topic "why formal verification belongs at the base layer" --mode triadic

That prints the prompt (`--llm print`, the default). `--mode hoskinson` for pure Hoskinson voice.

For an unattended/headless run that calls the model itself, install the optional API extra and set a
key:

    .venv/Scripts/python.exe -m pip install -e ".[api]"
    set ANTHROPIC_API_KEY=...    # PowerShell: $env:ANTHROPIC_API_KEY="..."
    .venv/Scripts/python.exe -m scripts.generate --topic "..." --mode triadic --llm anthropic

## Copyright

Hoskinson transcripts are the channel owner's own content (stored inline). The
Feynman corpus stores pointers and paraphrased metadata only - no verbatim text.
