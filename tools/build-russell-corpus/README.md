# build-russell-corpus

One-shot pipeline that expands the russellian-style Russell corpus from 50 to ~500 entries.

See `docs/specs/2026-05-21-russell-corpus-expansion-design.md` for design.

## Quickstart

```bash
cd tools/build-russell-corpus
python -m venv .venv
.venv/Scripts/pip install -e ".[dev]"     # Windows
.venv/bin/pip install -e ".[dev]"         # POSIX
.venv/bin/python -m pytest tests/ -q
```

Stages (run via `python -m scripts.cli`):

1. `derive_vocabulary` — run once before the first extraction
2. `extract_candidates` — per source, proposes ~100 candidates
3. `sentinel` — deterministic checks
4. `cross_check` — independent LLM rhetorical reader
5. `audit_sample` — operator-facing 5% sample
6. `append_to_index` — writes verified entries to `skills/russellian-style/assets/russell-corpus/index.json`

All stages append-only. State lives under `runs/<batch-id>/`.
