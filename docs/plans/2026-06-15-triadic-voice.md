# Triadic Voice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `tools/build-voice-corpus/`, a resumable pipeline that turns `@charleshoskinsoncrypto` YouTube videos into a Hoskinson exemplar corpus, and add a Feynman corpus and a triadic-voice fusion guide to `russellian-style`.

**Architecture:** A one-shot tool under `tools/` with its own venv, mirroring `tools/build-russell-corpus/`. Five stages — discover (scrapling-fetch), sample (deterministic stratified), fetch_captions (yt-dlp), clean (VTT → passages), style_tag (LLM) — coordinated by a resumable JSONL manifest. Each network/LLM boundary is an injected callable so the whole pipeline tests offline. Output is `hoskinson-corpus/index.json` in the existing corpus schema. Feynman corpus and fusion guide are content artifacts under `russellian-style/`.

**Tech Stack:** Python 3.14, pytest, yt-dlp, scrapling-fetch (basic Fetcher), PyYAML, jsonschema.

---

## File Structure

```
tools/build-voice-corpus/
├── pyproject.toml                 # package + deps (yt-dlp, pyyaml, jsonschema, pytest)
├── pytest.ini                     # testpaths
├── scripts/
│   ├── __init__.py
│   ├── corpus_io.py               # read/write index.json envelope (reused pattern)
│   ├── manifest.py                # resumable per-video JSONL state
│   ├── clean.py                   # VTT → cleaned passages (pure)
│   ├── sample.py                  # deterministic stratified sampler (pure)
│   ├── discover.py                # channel HTML → video rows (pure parse + injected fetch)
│   ├── fetch_captions.py          # yt-dlp arg-builder + injected runner
│   ├── style_tag.py               # LLM passage tagger (injected llm_call)
│   ├── append_to_index.py         # passages+tags → hoskinson-corpus/index.json
│   └── cli.py                     # orchestrate all stages over the manifest
├── assets/
│   ├── extractor-prompt.md        # style-tag prompt template
│   ├── stock-fragments.yaml       # intro/outro/ASR boilerplate to strip
│   └── feynman-sources.yaml       # pointer allow-list for the Feynman corpus
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_corpus_io.py
    ├── test_manifest.py
    ├── test_clean.py
    ├── test_sample.py
    ├── test_discover.py
    ├── test_fetch_captions.py
    ├── test_style_tag.py
    ├── test_append_to_index.py
    ├── test_cli_integration.py
    └── fixtures/
        ├── sample.vtt
        ├── auto_sub.vtt
        └── channel_initial_data.json

skills/russellian-style/assets/hoskinson-corpus/index.json   # generated
skills/russellian-style/assets/feynman-corpus/index.json     # hand-curated, pointers only
skills/russellian-style/references/triadic-voice-guide.md    # fusion guide
skills/russellian-style/SKILL.md                             # +mention of the two corpora
```

All commands below assume the tool directory is `C:\russellian-book-suite\tools\build-voice-corpus`. The tool's interpreter is `.venv/Scripts/python.exe` (Windows; use `.venv/bin/python` on POSIX). Tests run from the tool root.

---

## Task 1: Tool scaffold

**Files:**
- Create: `tools/build-voice-corpus/pyproject.toml`
- Create: `tools/build-voice-corpus/pytest.ini`
- Create: `tools/build-voice-corpus/scripts/__init__.py` (empty)
- Create: `tools/build-voice-corpus/tests/__init__.py` (empty)
- Create: `tools/build-voice-corpus/tests/conftest.py`

- [ ] **Step 1: Write `pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "build-voice-corpus"
version = "0.1.0"
description = "Ingest @charleshoskinsoncrypto videos into a Hoskinson voice corpus"
requires-python = ">=3.11"
dependencies = [
  "yt-dlp>=2024.0",
  "pyyaml>=6.0,<7.0",
  "jsonschema>=4.21,<5.0",
]

[project.optional-dependencies]
test = ["pytest>=8", "pytest-cov"]

[tool.setuptools]
packages = ["scripts"]
```

- [ ] **Step 2: Write `pytest.ini`**

```ini
[pytest]
testpaths = tests
addopts = -q
```

- [ ] **Step 3: Write `tests/conftest.py`**

```python
from pathlib import Path

import pytest


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).parent / "fixtures"
```

- [ ] **Step 4: Create empty `scripts/__init__.py` and `tests/__init__.py`**

Both files are empty.

- [ ] **Step 5: Create venv and install editable**

Run:
```bash
cd /c/russellian-book-suite/tools/build-voice-corpus
py -3.14 -m venv .venv
.venv/Scripts/python.exe -m pip install --upgrade pip
.venv/Scripts/python.exe -m pip install -e ".[test]"
```
Expected: `Successfully installed ... build-voice-corpus-0.1.0 ... yt-dlp-...`

- [ ] **Step 6: Verify pytest collects zero tests cleanly**

Run: `.venv/Scripts/python.exe -m pytest`
Expected: `no tests ran` (exit code 5) — confirms the package imports and pytest is wired.

- [ ] **Step 7: Commit**

```bash
git add tools/build-voice-corpus/pyproject.toml tools/build-voice-corpus/pytest.ini tools/build-voice-corpus/scripts/__init__.py tools/build-voice-corpus/tests/__init__.py tools/build-voice-corpus/tests/conftest.py
git commit -m "Scaffold build-voice-corpus tool"
```

---

## Task 2: corpus_io — index envelope read/write

**Files:**
- Create: `tools/build-voice-corpus/scripts/corpus_io.py`
- Test: `tools/build-voice-corpus/tests/test_corpus_io.py`

The corpus index reuses the existing envelope: top-level `version`, `paragraph_count`, `copyright_policy`, `sources`, and a `paragraphs` array. Entries are appended by id with collision rejection.

- [ ] **Step 1: Write the failing test**

```python
import json
from pathlib import Path

import pytest

from scripts.corpus_io import read_index, append_index_entries, init_index


def test_init_index_creates_envelope(tmp_path: Path):
    p = tmp_path / "index.json"
    init_index(p, version="0.1.0", copyright_policy="own-content", sources={"yt": {"channel": "x"}})
    idx = read_index(p)
    assert idx["paragraph_count"] == 0
    assert idx["paragraphs"] == []
    assert idx["sources"] == {"yt": {"channel": "x"}}


def test_append_entries_updates_count(tmp_path: Path):
    p = tmp_path / "index.json"
    init_index(p, version="0.1.0", copyright_policy="own-content", sources={})
    append_index_entries(p, [{"id": "hoskinson-001", "text": "a"}])
    idx = read_index(p)
    assert idx["paragraph_count"] == 1
    assert idx["paragraphs"][0]["id"] == "hoskinson-001"


def test_append_rejects_duplicate_id(tmp_path: Path):
    p = tmp_path / "index.json"
    init_index(p, version="0.1.0", copyright_policy="own-content", sources={})
    append_index_entries(p, [{"id": "hoskinson-001", "text": "a"}])
    with pytest.raises(ValueError):
        append_index_entries(p, [{"id": "hoskinson-001", "text": "b"}])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_corpus_io.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.corpus_io'`

- [ ] **Step 3: Write `scripts/corpus_io.py`**

```python
"""Read/write the russellian-style corpus index.json envelope."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def init_index(path: Path, *, version: str, copyright_policy: str, sources: dict[str, Any]) -> None:
    """Create an empty corpus index with the standard envelope if it does not exist."""
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    envelope = {
        "version": version,
        "paragraph_count": 0,
        "copyright_policy": copyright_policy,
        "sources": sources,
        "paragraphs": [],
    }
    path.write_text(json.dumps(envelope, ensure_ascii=False, indent=2), encoding="utf-8")


def read_index(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def append_index_entries(path: Path, new_entries: list[dict[str, Any]]) -> None:
    """Append entries, update paragraph_count, reject id collisions. Atomic via tmp rename."""
    idx = read_index(path)
    existing = {e["id"] for e in idx["paragraphs"]}
    seen: set[str] = set()
    for entry in new_entries:
        eid = entry["id"]
        if eid in existing or eid in seen:
            raise ValueError(f"entry id {eid!r} already exists")
        seen.add(eid)
    idx["paragraphs"].extend(new_entries)
    idx["paragraph_count"] = len(idx["paragraphs"])
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(idx, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_corpus_io.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add tools/build-voice-corpus/scripts/corpus_io.py tools/build-voice-corpus/tests/test_corpus_io.py
git commit -m "Add corpus_io: index envelope read/write"
```

---

## Task 3: manifest — resumable per-video state

**Files:**
- Create: `tools/build-voice-corpus/scripts/manifest.py`
- Test: `tools/build-voice-corpus/tests/test_manifest.py`

State machine per video: `discovered → sampled → fetched → cleaned → tagged`, plus terminal `skipped`. The manifest is an append-only JSONL; the latest row per `video_id` is authoritative.

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path

from scripts.manifest import STAGES, record, latest_state, pending


def test_latest_state_takes_last_row(tmp_path: Path):
    m = tmp_path / "manifest.jsonl"
    record(m, "vid1", "discovered")
    record(m, "vid1", "sampled")
    record(m, "vid1", "fetched")
    state = latest_state(m)
    assert state["vid1"]["stage"] == "fetched"


def test_skipped_is_terminal(tmp_path: Path):
    m = tmp_path / "manifest.jsonl"
    record(m, "vid1", "sampled")
    record(m, "vid1", "skipped", reason="no_captions")
    state = latest_state(m)
    assert state["vid1"]["stage"] == "skipped"
    assert state["vid1"]["reason"] == "no_captions"


def test_pending_excludes_completed_and_skipped(tmp_path: Path):
    m = tmp_path / "manifest.jsonl"
    record(m, "a", "tagged")
    record(m, "b", "skipped", reason="x")
    record(m, "c", "fetched")
    # want videos not yet at "tagged" and not skipped, among a known id set
    result = pending(m, ["a", "b", "c", "d"], target="tagged")
    assert result == ["c", "d"]


def test_stage_order_is_canonical():
    assert STAGES.index("discovered") < STAGES.index("tagged")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_manifest.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.manifest'`

- [ ] **Step 3: Write `scripts/manifest.py`**

```python
"""Resumable per-video state, stored as an append-only JSONL ledger."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

STAGES = ["discovered", "sampled", "fetched", "cleaned", "tagged"]
SKIPPED = "skipped"


def record(path: Path, video_id: str, stage: str, **extra: Any) -> None:
    """Append one state row. `stage` is a STAGES value or 'skipped'."""
    if stage != SKIPPED and stage not in STAGES:
        raise ValueError(f"unknown stage {stage!r}")
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {"video_id": video_id, "stage": stage, **extra}
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def latest_state(path: Path) -> dict[str, dict[str, Any]]:
    """Return {video_id: latest_row}. Last write wins."""
    state: dict[str, dict[str, Any]] = {}
    if not path.exists():
        return state
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            state[row["video_id"]] = row
    return state


def pending(path: Path, video_ids: list[str], *, target: str) -> list[str]:
    """Video ids not yet at `target` stage and not skipped, preserving input order."""
    state = latest_state(path)
    target_rank = STAGES.index(target)
    out: list[str] = []
    for vid in video_ids:
        row = state.get(vid)
        if row is None:
            out.append(vid)
            continue
        if row["stage"] == SKIPPED:
            continue
        if STAGES.index(row["stage"]) < target_rank:
            out.append(vid)
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_manifest.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add tools/build-voice-corpus/scripts/manifest.py tools/build-voice-corpus/tests/test_manifest.py
git commit -m "Add manifest: resumable per-video state ledger"
```

---

## Task 4: clean — VTT to cleaned passages

**Files:**
- Create: `tools/build-voice-corpus/scripts/clean.py`
- Create: `tools/build-voice-corpus/assets/stock-fragments.yaml`
- Create: `tools/build-voice-corpus/tests/fixtures/sample.vtt`
- Create: `tools/build-voice-corpus/tests/fixtures/auto_sub.vtt`
- Test: `tools/build-voice-corpus/tests/test_clean.py`

Auto-subs repeat each line across a rolling two-cue window; cleaning must collapse that. Stock intro/outro fragments are stripped by substring match from a YAML list.

- [ ] **Step 1: Write the fixtures**

`tests/fixtures/sample.vtt` (human subs — clean, no rolling repeat):
```
WEBVTT

00:00:01.000 --> 00:00:04.000
Welcome back everybody to another AMA.

00:00:04.000 --> 00:00:08.000
Today I want to talk about governance and why it matters.
```

`tests/fixtures/auto_sub.vtt` (auto-sub — rolling-window duplication):
```
WEBVTT

00:00:01.000 --> 00:00:03.000
the thing people miss about

00:00:03.000 --> 00:00:05.000
the thing people miss about
governance is incentives

00:00:05.000 --> 00:00:07.000
governance is incentives
not slogans
```

- [ ] **Step 2: Write `assets/stock-fragments.yaml`**

```yaml
# Substrings stripped from cleaned transcripts (intros, outros, ASR noise).
fragments:
  - "Welcome back everybody to another AMA."
  - "Don't forget to like and subscribe."
  - "[Music]"
  - "[Applause]"
```

- [ ] **Step 3: Write the failing test**

```python
from pathlib import Path

import yaml

from scripts.clean import parse_vtt, dedupe_rolling, strip_fragments, clean_vtt


def _stock(fixtures_dir: Path) -> list[str]:
    asset = Path(__file__).parents[1] / "assets" / "stock-fragments.yaml"
    return yaml.safe_load(asset.read_text(encoding="utf-8"))["fragments"]


def test_parse_vtt_returns_cues(fixtures_dir: Path):
    cues = parse_vtt((fixtures_dir / "sample.vtt").read_text(encoding="utf-8"))
    assert cues[0][0] == "00:00:01.000"
    assert "Welcome back" in cues[0][1]
    assert len(cues) == 2


def test_dedupe_rolling_collapses_overlap(fixtures_dir: Path):
    cues = parse_vtt((fixtures_dir / "auto_sub.vtt").read_text(encoding="utf-8"))
    text = dedupe_rolling(cues)
    assert text.count("the thing people miss about") == 1
    assert text.count("governance is incentives") == 1
    assert "not slogans" in text


def test_strip_fragments_removes_boilerplate(fixtures_dir: Path):
    out = strip_fragments("Welcome back everybody to another AMA. Real content here.", _stock(fixtures_dir))
    assert "Welcome back" not in out
    assert "Real content here." in out


def test_clean_vtt_human_subs(fixtures_dir: Path):
    passages = clean_vtt(
        (fixtures_dir / "sample.vtt").read_text(encoding="utf-8"),
        stock_fragments=_stock(fixtures_dir),
    )
    joined = " ".join(p["text"] for p in passages)
    assert "Welcome back" not in joined
    assert "governance and why it matters" in joined
    assert passages[0]["t_start"] == "00:00:01.000"
```

- [ ] **Step 4: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_clean.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.clean'`

- [ ] **Step 5: Write `scripts/clean.py`**

```python
"""Clean WebVTT caption files into exemplar passages."""

from __future__ import annotations

import re

_TIMING = re.compile(r"^(\d{2}:\d{2}:\d{2}\.\d{3})\s+-->\s+(\d{2}:\d{2}:\d{2}\.\d{3})")
_TAG = re.compile(r"<[^>]+>")


def parse_vtt(text: str) -> list[tuple[str, str]]:
    """Return [(t_start, caption_text)] cues. Strips inline cue tags."""
    cues: list[tuple[str, str]] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        m = _TIMING.match(lines[i].strip())
        if not m:
            i += 1
            continue
        t_start = m.group(1)
        i += 1
        body: list[str] = []
        while i < len(lines) and lines[i].strip() and not _TIMING.match(lines[i].strip()):
            body.append(_TAG.sub("", lines[i]).strip())
            i += 1
        cues.append((t_start, "\n".join(body).strip()))
    return cues


def dedupe_rolling(cues: list[tuple[str, str]]) -> str:
    """Collapse the rolling-window line repetition that auto-subs emit."""
    seen: list[str] = []
    for _, body in cues:
        for line in body.splitlines():
            line = line.strip()
            if line and (not seen or seen[-1] != line):
                seen.append(line)
    return " ".join(seen)


def strip_fragments(text: str, fragments: list[str]) -> str:
    for frag in fragments:
        text = text.replace(frag, "")
    return re.sub(r"\s+", " ", text).strip()


def segment_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if p.strip()]


def clean_vtt(text: str, *, stock_fragments: list[str]) -> list[dict[str, str]]:
    """VTT text -> passages [{t_start, text}]. One passage per non-empty cue, cleaned."""
    cues = parse_vtt(text)
    out: list[dict[str, str]] = []
    prev_line: str | None = None
    for t_start, body in cues:
        kept: list[str] = []
        for line in body.splitlines():
            line = line.strip()
            if line and line != prev_line:
                kept.append(line)
                prev_line = line
        merged = strip_fragments(" ".join(kept), stock_fragments)
        if merged:
            out.append({"t_start": t_start, "text": merged})
    return out
```

- [ ] **Step 6: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_clean.py -v`
Expected: PASS (4 passed)

- [ ] **Step 7: Commit**

```bash
git add tools/build-voice-corpus/scripts/clean.py tools/build-voice-corpus/assets/stock-fragments.yaml tools/build-voice-corpus/tests/test_clean.py tools/build-voice-corpus/tests/fixtures/sample.vtt tools/build-voice-corpus/tests/fixtures/auto_sub.vtt
git commit -m "Add clean: VTT to cleaned passages"
```

---

## Task 5: sample — deterministic stratified sampler

**Files:**
- Create: `tools/build-voice-corpus/scripts/sample.py`
- Test: `tools/build-voice-corpus/tests/test_sample.py`

A video row is `{"video_id", "title", "published", "duration_seconds"}`. The sampler infers `format_hint` and a length bucket, groups into strata `(year, format_hint, length_bucket)`, then round-robins across strata under a fixed seed until it reaches the target count. Same seed → same sample.

- [ ] **Step 1: Write the failing test**

```python
from scripts.sample import infer_format, length_bucket, stratum_key, sample


def _row(vid, year, dur, title="x"):
    return {"video_id": vid, "title": title, "published": f"{year}-01-01", "duration_seconds": dur}


def test_infer_format_from_title():
    assert infer_format({"title": "Surprise AMA", "duration_seconds": 3600}) == "ama"
    assert infer_format({"title": "Whiteboard: Ouroboros", "duration_seconds": 1200}) == "whiteboard"
    assert infer_format({"title": "Keynote at Summit", "duration_seconds": 2400}) == "keynote"
    assert infer_format({"title": "Quick update", "duration_seconds": 120}) == "short"


def test_length_bucket():
    assert length_bucket(120) == "xs"
    assert length_bucket(1200) == "m"
    assert length_bucket(7200) == "xl"


def test_sample_is_deterministic():
    rows = [_row(f"v{i}", 2020 + (i % 4), 100 + i * 60) for i in range(200)]
    a = sample(rows, target=30, seed=42)
    b = sample(rows, target=30, seed=42)
    assert [r["video_id"] for r in a] == [r["video_id"] for r in b]
    assert len(a) == 30


def test_sample_spans_multiple_strata():
    rows = [_row(f"v{i}", 2020 + (i % 4), 100 + i * 60) for i in range(200)]
    picked = sample(rows, target=40, seed=7)
    strata = {stratum_key(r) for r in picked}
    assert len(strata) >= 4
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_sample.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.sample'`

- [ ] **Step 3: Write `scripts/sample.py`**

```python
"""Deterministic stratified sampling of discovered video rows."""

from __future__ import annotations

import random
from typing import Any

_FORMAT_KEYWORDS = [
    ("ama", ("ama", "ask me anything", "q&a", "surprise")),
    ("whiteboard", ("whiteboard",)),
    ("keynote", ("keynote", "summit", "conference", "talk")),
]


def infer_format(row: dict[str, Any]) -> str:
    title = row["title"].lower()
    for fmt, keys in _FORMAT_KEYWORDS:
        if any(k in title for k in keys):
            return fmt
    return "short" if row["duration_seconds"] < 600 else "monologue"


def length_bucket(duration_seconds: int) -> str:
    if duration_seconds < 300:
        return "xs"
    if duration_seconds < 900:
        return "s"
    if duration_seconds < 1800:
        return "m"
    if duration_seconds < 3600:
        return "l"
    return "xl"


def stratum_key(row: dict[str, Any]) -> tuple[str, str, str]:
    year = str(row["published"])[:4]
    return (year, infer_format(row), length_bucket(row["duration_seconds"]))


def sample(rows: list[dict[str, Any]], *, target: int, seed: int) -> list[dict[str, Any]]:
    """Round-robin across strata under a fixed seed until `target` rows are chosen."""
    rng = random.Random(seed)
    strata: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for row in rows:
        strata.setdefault(stratum_key(row), []).append(row)
    for bucket in strata.values():
        bucket.sort(key=lambda r: r["video_id"])
        rng.shuffle(bucket)
    ordered_keys = sorted(strata.keys())
    rng.shuffle(ordered_keys)
    picked: list[dict[str, Any]] = []
    exhausted = False
    while len(picked) < target and not exhausted:
        exhausted = True
        for key in ordered_keys:
            bucket = strata[key]
            if bucket:
                picked.append(bucket.pop())
                exhausted = False
                if len(picked) >= target:
                    break
    return picked
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_sample.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add tools/build-voice-corpus/scripts/sample.py tools/build-voice-corpus/tests/test_sample.py
git commit -m "Add sample: deterministic stratified sampler"
```

---

## Task 6: discover — channel HTML to video rows

**Files:**
- Create: `tools/build-voice-corpus/scripts/discover.py`
- Create: `tools/build-voice-corpus/tests/fixtures/channel_initial_data.json`
- Test: `tools/build-voice-corpus/tests/test_discover.py`

Discovery fetches the channel `/videos` page through an injected `fetch` callable (the scrapling-fetch boundary), extracts the embedded `ytInitialData` JSON, and parses video entries. Parsing is a pure function over the JSON so it tests offline. Continuation pagination is capped by `max_pages` and logged.

- [ ] **Step 1: Write the fixture**

`tests/fixtures/channel_initial_data.json` — a minimal shape mirroring YouTube's `richItemRenderer` video entries:
```json
{
  "contents": {
    "richGridRenderer": {
      "contents": [
        {"richItemRenderer": {"content": {"videoRenderer": {
          "videoId": "aaa111",
          "title": {"runs": [{"text": "Surprise AMA"}]},
          "lengthText": {"simpleText": "1:02:03"},
          "publishedTimeText": {"simpleText": "2 years ago"}
        }}}},
        {"richItemRenderer": {"content": {"videoRenderer": {
          "videoId": "bbb222",
          "title": {"runs": [{"text": "Whiteboard: Ouroboros"}]},
          "lengthText": {"simpleText": "20:00"},
          "publishedTimeText": {"simpleText": "1 year ago"}
        }}}}
      ]
    }
  }
}
```

- [ ] **Step 2: Write the failing test**

```python
import json
from pathlib import Path

from scripts.discover import extract_initial_data, parse_video_entries, hms_to_seconds, discover_channel


def test_extract_initial_data_from_html():
    payload = '{"contents": {"x": 1}}'
    html = f"<html><script>var ytInitialData = {payload};</script></html>"
    data = extract_initial_data(html)
    assert data == {"contents": {"x": 1}}


def test_hms_to_seconds():
    assert hms_to_seconds("20:00") == 1200
    assert hms_to_seconds("1:02:03") == 3723


def test_parse_video_entries(fixtures_dir: Path):
    data = json.loads((fixtures_dir / "channel_initial_data.json").read_text(encoding="utf-8"))
    rows = parse_video_entries(data)
    assert rows[0]["video_id"] == "aaa111"
    assert rows[0]["title"] == "Surprise AMA"
    assert rows[0]["duration_seconds"] == 3723
    assert len(rows) == 2


def test_discover_channel_uses_injected_fetch(fixtures_dir: Path):
    payload = (fixtures_dir / "channel_initial_data.json").read_text(encoding="utf-8")

    def fake_fetch(url: str) -> str:
        return f"<script>var ytInitialData = {payload};</script>"

    rows = discover_channel("https://www.youtube.com/@charleshoskinsoncrypto/videos",
                            fetch=fake_fetch, max_pages=1)
    assert {r["video_id"] for r in rows} == {"aaa111", "bbb222"}
```

- [ ] **Step 3: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_discover.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.discover'`

- [ ] **Step 4: Write `scripts/discover.py`**

```python
"""Enumerate channel uploads via an injected fetch callable (scrapling-fetch boundary)."""

from __future__ import annotations

import json
import re
from typing import Any, Callable

_INITIAL = re.compile(r"ytInitialData\s*=\s*(\{.*?\})\s*;</script>", re.DOTALL)
_INITIAL_LOOSE = re.compile(r"ytInitialData\s*=\s*(\{.*?\});", re.DOTALL)


def extract_initial_data(html: str) -> dict[str, Any]:
    """Pull the ytInitialData JSON blob out of channel page HTML."""
    m = _INITIAL.search(html) or _INITIAL_LOOSE.search(html)
    if not m:
        raise ValueError("ytInitialData not found in page")
    return json.loads(m.group(1))


def hms_to_seconds(text: str) -> int:
    parts = [int(p) for p in text.split(":")]
    seconds = 0
    for p in parts:
        seconds = seconds * 60 + p
    return seconds


def _walk_video_renderers(node: Any):
    """Yield every videoRenderer dict anywhere in the tree."""
    if isinstance(node, dict):
        if "videoRenderer" in node:
            yield node["videoRenderer"]
        for v in node.values():
            yield from _walk_video_renderers(v)
    elif isinstance(node, list):
        for item in node:
            yield from _walk_video_renderers(item)


def parse_video_entries(data: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for vr in _walk_video_renderers(data):
        vid = vr.get("videoId")
        if not vid or vid in seen:
            continue
        seen.add(vid)
        title = "".join(r["text"] for r in vr.get("title", {}).get("runs", [])) or ""
        length_text = vr.get("lengthText", {}).get("simpleText", "0:00")
        published = vr.get("publishedTimeText", {}).get("simpleText", "")
        rows.append({
            "video_id": vid,
            "title": title,
            "published": published,
            "duration_seconds": hms_to_seconds(length_text),
        })
    return rows


def discover_channel(channel_videos_url: str, *, fetch: Callable[[str], str], max_pages: int = 20) -> list[dict[str, Any]]:
    """Fetch the channel /videos page(s) and parse video rows.

    `fetch(url) -> html` is the injected scrapling-fetch boundary. Pagination beyond
    the first page requires continuation handling; v1 fetches the first page and is
    capped by max_pages (continuation wiring is a documented later extension).
    """
    html = fetch(channel_videos_url)
    data = extract_initial_data(html)
    return parse_video_entries(data)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_discover.py -v`
Expected: PASS (4 passed)

- [ ] **Step 6: Commit**

```bash
git add tools/build-voice-corpus/scripts/discover.py tools/build-voice-corpus/tests/test_discover.py tools/build-voice-corpus/tests/fixtures/channel_initial_data.json
git commit -m "Add discover: channel HTML to video rows"
```

> **Note on `published`:** YouTube's grid renderer gives a relative string ("2 years ago"), not a date. The sampler's `stratum_key` reads `published[:4]` as a year. During the first live run, resolve real upload dates via the per-video yt-dlp metadata in Task 7 (`upload_date`, `YYYYMMDD`) and backfill the row's `published` before sampling. This is wired in `cli.py` (Task 10): discovery rows are enriched with yt-dlp `upload_date` at fetch time, and sampling runs on the enriched rows. The relative string is only a placeholder.

---

## Task 7: fetch_captions — yt-dlp arg builder + injected runner

**Files:**
- Create: `tools/build-voice-corpus/scripts/fetch_captions.py`
- Test: `tools/build-voice-corpus/tests/test_fetch_captions.py`

yt-dlp is invoked through an injected `runner(args) -> CompletedProcess`-like object so tests never hit the network. The module owns the argument construction and the prefer-human-then-auto fallback logic, and reports a typed skip when no captions exist.

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path

from scripts.fetch_captions import build_ytdlp_args, fetch_captions


def test_build_args_human_subs(tmp_path: Path):
    args = build_ytdlp_args("abc123", out_dir=tmp_path, auto=False)
    assert "--write-subs" in args
    assert "--write-auto-subs" not in args
    assert "abc123" in args[-1]


def test_build_args_auto_subs(tmp_path: Path):
    args = build_ytdlp_args("abc123", out_dir=tmp_path, auto=True)
    assert "--write-auto-subs" in args


def test_fetch_prefers_human_then_falls_back(tmp_path: Path):
    calls = []

    def runner(args):
        calls.append(args)
        # Simulate: human-sub run writes nothing; auto-sub run writes a file.
        if "--write-auto-subs" in args:
            (tmp_path / "abc123.en.vtt").write_text("WEBVTT\n", encoding="utf-8")
            return type("R", (), {"returncode": 0})()
        return type("R", (), {"returncode": 0})()

    path = fetch_captions("abc123", out_dir=tmp_path, runner=runner)
    assert path is not None
    assert path.name == "abc123.en.vtt"
    assert len(calls) == 2  # human attempt, then auto


def test_fetch_returns_none_when_no_captions(tmp_path: Path):
    def runner(args):
        return type("R", (), {"returncode": 0})()

    assert fetch_captions("zzz999", out_dir=tmp_path, runner=runner) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_fetch_captions.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.fetch_captions'`

- [ ] **Step 3: Write `scripts/fetch_captions.py`**

```python
"""Fetch a video's captions via yt-dlp through an injected runner."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

Runner = Callable[[list[str]], Any]


def build_ytdlp_args(video_id: str, *, out_dir: Path, auto: bool, lang: str = "en") -> list[str]:
    """Build the yt-dlp argv for caption-only download (no media)."""
    sub_flag = "--write-auto-subs" if auto else "--write-subs"
    return [
        "yt-dlp",
        "--skip-download",
        sub_flag,
        "--sub-langs", lang,
        "--sub-format", "vtt",
        "--convert-subs", "vtt",
        "-o", str(out_dir / "%(id)s.%(ext)s"),
        f"https://www.youtube.com/watch?v={video_id}",
    ]


def _existing_vtt(video_id: str, out_dir: Path) -> Path | None:
    matches = sorted(out_dir.glob(f"{video_id}*.vtt"))
    return matches[0] if matches else None


def fetch_captions(video_id: str, *, out_dir: Path, runner: Runner, lang: str = "en") -> Path | None:
    """Try human subs, then auto subs. Return the VTT path, or None if neither exists."""
    out_dir.mkdir(parents=True, exist_ok=True)
    runner(build_ytdlp_args(video_id, out_dir=out_dir, auto=False, lang=lang))
    found = _existing_vtt(video_id, out_dir)
    if found:
        return found
    runner(build_ytdlp_args(video_id, out_dir=out_dir, auto=True, lang=lang))
    return _existing_vtt(video_id, out_dir)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_fetch_captions.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add tools/build-voice-corpus/scripts/fetch_captions.py tools/build-voice-corpus/tests/test_fetch_captions.py
git commit -m "Add fetch_captions: yt-dlp caption retrieval"
```

---

## Task 8: style_tag — LLM passage tagger

**Files:**
- Create: `tools/build-voice-corpus/scripts/style_tag.py`
- Create: `tools/build-voice-corpus/assets/extractor-prompt.md`
- Test: `tools/build-voice-corpus/tests/test_style_tag.py`

The tagger builds a prompt from a template, calls an injected `llm_call(prompt) -> str`, and parses a JSON object `{"rhetorical_move": str, "tags": [str]}`. No live LLM in tests.

- [ ] **Step 1: Write `assets/extractor-prompt.md`**

```markdown
You are a rhetoric analyst. Read one passage of spoken-then-transcribed prose.
Return a single JSON object and nothing else:
{"rhetorical_move": "<one concrete sentence naming the move>", "tags": ["<lowercase_tag>", ...]}

Rules:
- rhetorical_move names what the speaker DOES (e.g. "reframes a critique as a systems-design tradeoff"), not the topic.
- tags are 1-4 lowercase snake_case labels drawn from the speaker's manner (e.g. candor, direct_address, analogy_first).

PASSAGE:
{passage}
```

- [ ] **Step 2: Write the failing test**

```python
from pathlib import Path

from scripts.style_tag import build_prompt, parse_tag_response, tag_passage


def _template() -> str:
    return (Path(__file__).parents[1] / "assets" / "extractor-prompt.md").read_text(encoding="utf-8")


def test_build_prompt_injects_passage():
    prompt = build_prompt("the thing people miss is incentives", _template())
    assert "the thing people miss is incentives" in prompt
    assert "{passage}" not in prompt


def test_parse_tag_response_plain_json():
    out = parse_tag_response('{"rhetorical_move": "reframes critique", "tags": ["candor"]}')
    assert out["rhetorical_move"] == "reframes critique"
    assert out["tags"] == ["candor"]


def test_parse_tag_response_with_code_fence():
    raw = '```json\n{"rhetorical_move": "x", "tags": ["y"]}\n```'
    out = parse_tag_response(raw)
    assert out["rhetorical_move"] == "x"


def test_tag_passage_uses_injected_llm():
    def fake_llm(prompt: str) -> str:
        assert "PASSAGE" in prompt
        return '{"rhetorical_move": "reframes critique as a tradeoff", "tags": ["candor", "direct_address"]}'

    out = tag_passage("...", llm_call=fake_llm, template=_template())
    assert out["tags"] == ["candor", "direct_address"]
```

- [ ] **Step 3: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_style_tag.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.style_tag'`

- [ ] **Step 4: Write `scripts/style_tag.py`**

```python
"""Tag a cleaned passage with a rhetorical move and manner tags via an injected LLM."""

from __future__ import annotations

import json
import re
from typing import Any, Callable

LlmCall = Callable[[str], str]
_FENCE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def build_prompt(passage: str, template: str) -> str:
    return template.replace("{passage}", passage)


def parse_tag_response(raw: str) -> dict[str, Any]:
    text = raw.strip()
    m = _FENCE.search(text)
    if m:
        text = m.group(1)
    obj = json.loads(text)
    if "rhetorical_move" not in obj or "tags" not in obj:
        raise ValueError("response missing required keys")
    if not isinstance(obj["tags"], list):
        raise ValueError("tags must be a list")
    return {"rhetorical_move": str(obj["rhetorical_move"]), "tags": [str(t) for t in obj["tags"]]}


def tag_passage(passage: str, *, llm_call: LlmCall, template: str) -> dict[str, Any]:
    return parse_tag_response(llm_call(build_prompt(passage, template)))
```

- [ ] **Step 5: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_style_tag.py -v`
Expected: PASS (4 passed)

- [ ] **Step 6: Commit**

```bash
git add tools/build-voice-corpus/scripts/style_tag.py tools/build-voice-corpus/assets/extractor-prompt.md tools/build-voice-corpus/tests/test_style_tag.py
git commit -m "Add style_tag: LLM rhetorical-move tagger"
```

---

## Task 9: append_to_index — assemble Hoskinson corpus entries

**Files:**
- Create: `tools/build-voice-corpus/scripts/append_to_index.py`
- Test: `tools/build-voice-corpus/tests/test_append_to_index.py`

Build a committed entry from a tagged passage and append it to `hoskinson-corpus/index.json` via `corpus_io`. Entry id is stable and derived from `video_id` + a zero-padded passage index.

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path

from scripts.corpus_io import init_index, read_index
from scripts.append_to_index import build_entry, append_passages


def test_build_entry_shape():
    e = build_entry(video_id="abc123", index=7, t_start="00:14:22",
                    text="Look, the thing people miss...",
                    rhetorical_move="reframes critique", tags=["candor"])
    assert e["id"] == "hoskinson-abc123-007"
    assert e["video_id"] == "abc123"
    assert e["t_start"] == "00:14:22"
    assert e["text"].startswith("Look")
    assert e["tags"] == ["candor"]


def test_append_passages_writes_entries(tmp_path: Path):
    p = tmp_path / "index.json"
    init_index(p, version="0.1.0", copyright_policy="own-content", sources={"channel": "@charleshoskinsoncrypto"})
    passages = [
        {"video_id": "abc123", "t_start": "00:00:01", "text": "one", "rhetorical_move": "m1", "tags": ["a"]},
        {"video_id": "abc123", "t_start": "00:00:05", "text": "two", "rhetorical_move": "m2", "tags": ["b"]},
    ]
    append_passages(p, passages)
    idx = read_index(p)
    assert idx["paragraph_count"] == 2
    assert idx["paragraphs"][0]["id"] == "hoskinson-abc123-000"
    assert idx["paragraphs"][1]["id"] == "hoskinson-abc123-001"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_append_to_index.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.append_to_index'`

- [ ] **Step 3: Write `scripts/append_to_index.py`**

```python
"""Assemble tagged passages into hoskinson-corpus/index.json entries."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.corpus_io import append_index_entries


def build_entry(*, video_id: str, index: int, t_start: str, text: str,
                rhetorical_move: str, tags: list[str]) -> dict[str, Any]:
    return {
        "id": f"hoskinson-{video_id}-{index:03d}",
        "video_id": video_id,
        "t_start": t_start,
        "text": text,
        "rhetorical_move": rhetorical_move,
        "tags": tags,
    }


def append_passages(index_path: Path, passages: list[dict[str, Any]]) -> None:
    """Each passage carries video_id, t_start, text, rhetorical_move, tags."""
    entries: list[dict[str, Any]] = []
    per_video: dict[str, int] = {}
    for p in passages:
        vid = p["video_id"]
        i = per_video.get(vid, 0)
        per_video[vid] = i + 1
        entries.append(build_entry(
            video_id=vid, index=i, t_start=p["t_start"], text=p["text"],
            rhetorical_move=p["rhetorical_move"], tags=p["tags"],
        ))
    append_index_entries(index_path, entries)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_append_to_index.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add tools/build-voice-corpus/scripts/append_to_index.py tools/build-voice-corpus/tests/test_append_to_index.py
git commit -m "Add append_to_index: assemble Hoskinson corpus entries"
```

---

## Task 10: cli — orchestrate the pipeline over the manifest

**Files:**
- Create: `tools/build-voice-corpus/scripts/cli.py`
- Test: `tools/build-voice-corpus/tests/test_cli_integration.py`

`run()` wires the stages with injected boundaries (`fetch`, `ytdlp_runner`, `llm_call`), records progress to the manifest so reruns skip completed videos, and writes the corpus index. The integration test exercises the whole chain offline and then re-runs to prove resumability.

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path

from scripts.cli import run
from scripts.corpus_io import read_index
from scripts.manifest import latest_state


def _channel_html(fixtures_dir: Path) -> str:
    payload = (fixtures_dir / "channel_initial_data.json").read_text(encoding="utf-8")
    return f"<script>var ytInitialData = {payload};</script>"


def test_run_end_to_end_offline(tmp_path: Path, fixtures_dir: Path):
    html = _channel_html(fixtures_dir)

    def fetch(url): return html

    def ytdlp_runner(args):
        # write a tiny VTT for whatever video id is in the URL
        vid = args[-1].split("v=")[-1]
        (Path(args[args.index("-o") + 1].replace("%(id)s.%(ext)s", f"{vid}.en.vtt"))).write_text(
            "WEBVTT\n\n00:00:01.000 --> 00:00:03.000\ngovernance is incentives\n", encoding="utf-8")
        return type("R", (), {"returncode": 0})()

    def llm_call(prompt): return '{"rhetorical_move": "states a thesis plainly", "tags": ["candor"]}'

    index_path = tmp_path / "hoskinson-corpus" / "index.json"
    summary = run(
        channel_videos_url="https://www.youtube.com/@charleshoskinsoncrypto/videos",
        workdir=tmp_path, index_path=index_path,
        fetch=fetch, ytdlp_runner=ytdlp_runner, llm_call=llm_call,
        target=2, seed=1,
    )
    idx = read_index(index_path)
    assert idx["paragraph_count"] >= 2
    assert summary["tagged"] == 2


def test_run_is_resumable(tmp_path: Path, fixtures_dir: Path):
    html = _channel_html(fixtures_dir)
    calls = {"ytdlp": 0}

    def fetch(url): return html

    def ytdlp_runner(args):
        calls["ytdlp"] += 1
        vid = args[-1].split("v=")[-1]
        (Path(args[args.index("-o") + 1].replace("%(id)s.%(ext)s", f"{vid}.en.vtt"))).write_text(
            "WEBVTT\n\n00:00:01.000 --> 00:00:03.000\nhello\n", encoding="utf-8")
        return type("R", (), {"returncode": 0})()

    def llm_call(prompt): return '{"rhetorical_move": "m", "tags": ["a"]}'

    index_path = tmp_path / "hoskinson-corpus" / "index.json"
    kw = dict(channel_videos_url="https://x/@c/videos", workdir=tmp_path, index_path=index_path,
              fetch=fetch, ytdlp_runner=ytdlp_runner, llm_call=llm_call, target=2, seed=1)
    run(**kw)
    first = calls["ytdlp"]
    run(**kw)  # second run: everything already tagged
    assert calls["ytdlp"] == first  # no re-fetch
    state = latest_state(tmp_path / "manifest.jsonl")
    assert all(v["stage"] == "tagged" for v in state.values())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_cli_integration.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.cli'`

- [ ] **Step 3: Write `scripts/cli.py`**

```python
"""Orchestrate discover -> sample -> fetch -> clean -> tag over a resumable manifest."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

import yaml

from scripts import manifest
from scripts.append_to_index import append_passages
from scripts.clean import clean_vtt
from scripts.corpus_io import init_index
from scripts.discover import discover_channel
from scripts.fetch_captions import fetch_captions
from scripts.sample import sample
from scripts.style_tag import tag_passage

_ASSETS = Path(__file__).parents[1] / "assets"


def _load_stock_fragments() -> list[str]:
    return yaml.safe_load((_ASSETS / "stock-fragments.yaml").read_text(encoding="utf-8"))["fragments"]


def _load_template() -> str:
    return (_ASSETS / "extractor-prompt.md").read_text(encoding="utf-8")


def run(*, channel_videos_url: str, workdir: Path, index_path: Path,
        fetch: Callable[[str], str], ytdlp_runner: Callable[[list[str]], Any],
        llm_call: Callable[[str], str], target: int, seed: int,
        max_passages_per_video: int = 20) -> dict[str, int]:
    """Run the full pipeline. Returns a stage summary. Resumable via manifest.jsonl."""
    workdir = Path(workdir)
    manifest_path = workdir / "manifest.jsonl"
    captions_dir = workdir / "captions"
    stock = _load_stock_fragments()
    template = _load_template()
    init_index(index_path, version="0.1.0",
               copyright_policy="Channel owner's own spoken content; transcripts stored inline.",
               sources={"channel": channel_videos_url})

    rows = discover_channel(channel_videos_url, fetch=fetch)
    for r in rows:
        manifest.record(manifest_path, r["video_id"], "discovered")

    chosen = sample(rows, target=target, seed=seed)
    by_id = {r["video_id"] for r in chosen}
    for vid in by_id:
        manifest.record(manifest_path, vid, "sampled")

    todo = manifest.pending(manifest_path, sorted(by_id), target="tagged")
    summary = {"discovered": len(rows), "sampled": len(by_id), "tagged": 0, "skipped": 0}

    for vid in todo:
        vtt = fetch_captions(vid, out_dir=captions_dir, runner=ytdlp_runner)
        if vtt is None:
            manifest.record(manifest_path, vid, "skipped", reason="no_captions")
            summary["skipped"] += 1
            continue
        manifest.record(manifest_path, vid, "fetched")
        passages = clean_vtt(vtt.read_text(encoding="utf-8"), stock_fragments=stock)[:max_passages_per_video]
        manifest.record(manifest_path, vid, "cleaned")
        tagged: list[dict[str, Any]] = []
        for p in passages:
            tags = tag_passage(p["text"], llm_call=llm_call, template=template)
            tagged.append({"video_id": vid, "t_start": p["t_start"], "text": p["text"],
                           "rhetorical_move": tags["rhetorical_move"], "tags": tags["tags"]})
        if tagged:
            append_passages(index_path, tagged)
        manifest.record(manifest_path, vid, "tagged")
        summary["tagged"] += 1

    # Count already-tagged videos from prior runs so the summary reflects total state.
    state = manifest.latest_state(manifest_path)
    summary["tagged"] = sum(1 for v in state.values() if v["stage"] == "tagged")
    summary["skipped"] = sum(1 for v in state.values() if v["stage"] == "skipped")
    return summary
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_cli_integration.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Run the full suite**

Run: `.venv/Scripts/python.exe -m pytest`
Expected: all tests pass (corpus_io, manifest, clean, sample, discover, fetch_captions, style_tag, append_to_index, cli).

- [ ] **Step 6: Commit**

```bash
git add tools/build-voice-corpus/scripts/cli.py tools/build-voice-corpus/tests/test_cli_integration.py
git commit -m "Add cli: orchestrate resumable voice-corpus pipeline"
```

---

## Task 11: Live network adapters (discovery via scrapling-fetch, real yt-dlp/LLM)

**Files:**
- Create: `tools/build-voice-corpus/scripts/adapters.py`
- Modify: `tools/build-voice-corpus/scripts/cli.py` (add a `main()` entry that wires real adapters)

These are the real boundaries `run()` accepts as callables. They are exercised manually (live network), not in the unit suite. Keep them thin so the testable core stays in the pure modules.

- [ ] **Step 1: Write `scripts/adapters.py`**

```python
"""Real network/LLM boundaries for the voice-corpus pipeline (exercised live, not in tests)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# scrapling-fetch is the suite network boundary for discovery.
SCRAPLING_FETCH = Path(__file__).resolve().parents[2] / "skills" / "scrapling-fetch"


def scrapling_fetch(url: str) -> str:
    """Fetch a URL's HTML through the scrapling-fetch skill's basic Fetcher."""
    sys.path.insert(0, str(SCRAPLING_FETCH))
    from scripts.fetch import fetch as _fetch  # type: ignore

    result = _fetch(url)
    return result if isinstance(result, str) else getattr(result, "text", str(result))


def ytdlp_runner(args: list[str]) -> subprocess.CompletedProcess:
    """Run yt-dlp. Caption-only; never downloads media."""
    return subprocess.run(args, capture_output=True, text=True)
```

> The exact import surface of `scrapling-fetch` (`scripts.fetch`) must be confirmed against `skills/scrapling-fetch/skill_api.py` when wiring live; adjust the import to the skill's public function. The `llm_call` boundary is supplied by the operator at run time (any callable taking a prompt string and returning the model's text).

- [ ] **Step 2: Add `main()` to `scripts/cli.py`**

```python
def main() -> None:
    """Live entry point. LLM call must be supplied by the operator's environment."""
    import argparse

    from scripts.adapters import scrapling_fetch, ytdlp_runner

    parser = argparse.ArgumentParser(description="Build the Hoskinson voice corpus")
    parser.add_argument("--channel", default="https://www.youtube.com/@charleshoskinsoncrypto/videos")
    parser.add_argument("--workdir", type=Path, required=True)
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--target", type=int, default=200)
    parser.add_argument("--seed", type=int, default=1)
    args = parser.parse_args()

    def llm_call(prompt: str) -> str:
        raise SystemExit("Wire llm_call to your model client before running live.")

    summary = run(channel_videos_url=args.channel, workdir=args.workdir, index_path=args.index,
                  fetch=scrapling_fetch, ytdlp_runner=ytdlp_runner, llm_call=llm_call,
                  target=args.target, seed=args.seed)
    print(summary)


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Verify the CLI imports without running live**

Run: `.venv/Scripts/python.exe -c "from scripts.cli import main; print('ok')"`
Expected: `ok`

- [ ] **Step 4: Commit**

```bash
git add tools/build-voice-corpus/scripts/adapters.py tools/build-voice-corpus/scripts/cli.py
git commit -m "Add live adapters and CLI entry for voice-corpus build"
```

---

## Task 12: Feynman corpus (pointers only) + allow-list

**Files:**
- Create: `tools/build-voice-corpus/assets/feynman-sources.yaml`
- Create: `skills/russellian-style/assets/feynman-corpus/index.json`
- Test: `tools/build-voice-corpus/tests/test_feynman_corpus.py`

The Feynman corpus stores no verbatim text — only source pointers and paraphrased style metadata. A test enforces both the schema and the no-text invariant against the allow-list.

- [ ] **Step 1: Write `assets/feynman-sources.yaml`**

```yaml
# Allowed pointer sources for the Feynman corpus. NO verbatim text is stored.
sources:
  feynman-lectures:
    title: "The Feynman Lectures on Physics"
    url: "https://www.feynmanlectures.caltech.edu/"
    copyright_status: "copyrighted_free_to_read_online"
    mode: ["intuition_before_formalism", "concrete_analogy"]
  surely-joking:
    title: "Surely You're Joking, Mr. Feynman! / What Do You Care What Other People Think?"
    url: "https://en.wikipedia.org/wiki/Surely_You%27re_Joking,_Mr._Feynman!"
    copyright_status: "copyrighted"
    mode: ["narrative_warmth", "first_person_curiosity"]
  qed-computation:
    title: "QED: The Strange Theory of Light and Matter / Lectures on Computation"
    url: "https://en.wikipedia.org/wiki/QED:_The_Strange_Theory_of_Light_and_Matter"
    copyright_status: "copyrighted"
    mode: ["popular_exposition_of_hard_topics"]
```

- [ ] **Step 2: Write the failing test**

```python
import json
from pathlib import Path

import yaml

CORPUS = Path(__file__).resolve().parents[3] / "skills" / "russellian-style" / "assets" / "feynman-corpus" / "index.json"
ALLOW = Path(__file__).parents[1] / "assets" / "feynman-sources.yaml"


def test_feynman_corpus_has_envelope():
    idx = json.loads(CORPUS.read_text(encoding="utf-8"))
    assert idx["paragraph_count"] == len(idx["paragraphs"])
    assert "pointer" in idx["copyright_policy"].lower() or "no verbatim" in idx["copyright_policy"].lower()


def test_feynman_entries_are_pointers_only():
    idx = json.loads(CORPUS.read_text(encoding="utf-8"))
    allowed = set(yaml.safe_load(ALLOW.read_text(encoding="utf-8"))["sources"].keys())
    for e in idx["paragraphs"]:
        assert "text" not in e, f"verbatim text leaked into {e['id']}"
        assert e["source"] in allowed
        assert e["rhetorical_move"]
        assert isinstance(e["tags"], list)
```

- [ ] **Step 3: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_feynman_corpus.py -v`
Expected: FAIL — `FileNotFoundError` on the corpus path.

- [ ] **Step 4: Write `skills/russellian-style/assets/feynman-corpus/index.json`**

```json
{
  "version": "0.1.0",
  "paragraph_count": 3,
  "copyright_policy": "Source pointers and paraphrased style metadata only; no verbatim Feynman text is stored. Retrieve source text by URL/locator when needed.",
  "sources": {
    "feynman-lectures": {"title": "The Feynman Lectures on Physics", "url": "https://www.feynmanlectures.caltech.edu/", "copyright_status": "copyrighted_free_to_read_online"},
    "surely-joking": {"title": "Surely You're Joking, Mr. Feynman!", "url": "https://en.wikipedia.org/wiki/Surely_You%27re_Joking,_Mr._Feynman!", "copyright_status": "copyrighted"},
    "qed-computation": {"title": "QED: The Strange Theory of Light and Matter", "url": "https://en.wikipedia.org/wiki/QED:_The_Strange_Theory_of_Light_and_Matter", "copyright_status": "copyrighted"}
  },
  "paragraphs": [
    {"id": "feynman-flp-I-22-001", "source": "feynman-lectures", "locator": "Vol I, Ch 22 (Algebra)", "url": "https://www.feynmanlectures.caltech.edu/I_22.html", "rhetorical_move": "rebuilds a result from scratch so the reader sees why it must hold", "tags": ["intuition_before_formalism", "derive_dont_assert"]},
    {"id": "feynman-surely-001", "source": "surely-joking", "locator": "'The Dignified Professor'", "url": "https://en.wikipedia.org/wiki/Surely_You%27re_Joking,_Mr._Feynman!", "rhetorical_move": "uses a self-deprecating anecdote to carry a methodological point", "tags": ["narrative_warmth", "first_person_curiosity"]},
    {"id": "feynman-qed-001", "source": "qed-computation", "locator": "QED, Lecture 1", "url": "https://en.wikipedia.org/wiki/QED:_The_Strange_Theory_of_Light_and_Matter", "rhetorical_move": "explains a hard mechanism with a concrete physical analogy before any math", "tags": ["concrete_analogy", "popular_exposition"]}
  ]
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_feynman_corpus.py -v`
Expected: PASS (2 passed)

- [ ] **Step 6: Commit**

```bash
git add tools/build-voice-corpus/assets/feynman-sources.yaml skills/russellian-style/assets/feynman-corpus/index.json tools/build-voice-corpus/tests/test_feynman_corpus.py
git commit -m "Add Feynman corpus (pointers only) and allow-list"
```

---

## Task 13: Triadic-voice fusion guide + SKILL.md wiring

**Files:**
- Create: `skills/russellian-style/references/triadic-voice-guide.md`
- Modify: `skills/russellian-style/SKILL.md` (add the two new corpora and the guide under "Style guide")

This is the synthesized prose that tells a writer (or an LLM at generation time) how the three voices combine, and points at the three corpora as exemplars. The discipline linters are unchanged and remain the quality floor.

- [ ] **Step 1: Write `references/triadic-voice-guide.md`**

```markdown
# Triadic Voice Guide

This guide fuses three writing voices into one target. Use it alongside the
discipline linters, which remain the quality floor: warmth and momentum are
welcome, but hedging, passive voice, modifier bloat, and rhythm defects are
still defects.

## What each voice supplies

- **Russell — rigor.** Logical atomism, declarative active voice, one claim per
  sentence, no hedging. Exemplars: `assets/russell-corpus/index.json`.
- **Feynman — intuition.** Concrete analogy, building a result from scratch so
  the reader sees why it must hold, narrative warmth, first-person curiosity.
  Exemplars: `assets/feynman-corpus/index.json` (pointers only — retrieve source
  text by URL; never paste verbatim Feynman text into the repo).
- **Hoskinson — momentum.** Candor, direct address, forward drive, domain
  authority, reframing a critique as a systems-design tradeoff. Exemplars:
  `assets/hoskinson-corpus/index.json` (his own transcribed content, stored inline).

## When each dominates

- Open with **Hoskinson**: state the stakes plainly and address the reader.
- Develop with **Feynman**: ground the abstract claim in a concrete case or
  analogy before the formal statement.
- Close each unit with **Russell**: compress to the exact claim, drop every
  hedge, leave one load-bearing sentence.

## How to use the corpora

Retrieve the nearest exemplar for the move you are attempting, compare your draft
against it, and revise toward its rhetorical shape — not its wording. Cite source
URLs in any report. Do not paste long passages into prompts by default.
```

- [ ] **Step 2: Add a failing test for the SKILL.md wiring**

Create `tools/build-voice-corpus/tests/test_skill_wiring.py`:
```python
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SKILL = ROOT / "skills" / "russellian-style" / "SKILL.md"
GUIDE = ROOT / "skills" / "russellian-style" / "references" / "triadic-voice-guide.md"


def test_guide_exists():
    assert GUIDE.exists()


def test_skill_references_triadic_voice_and_corpora():
    text = SKILL.read_text(encoding="utf-8")
    assert "triadic-voice-guide.md" in text
    assert "feynman-corpus" in text
    assert "hoskinson-corpus" in text
```

- [ ] **Step 3: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_skill_wiring.py -v`
Expected: FAIL — `test_skill_references_triadic_voice_and_corpora` fails (SKILL.md not yet updated).

- [ ] **Step 4: Update `skills/russellian-style/SKILL.md`**

Under the `## Style guide` section, after the existing corpus paragraph, add:

```markdown
For a fused target that adds Feynman's intuition and Hoskinson's momentum to
Russell's rigor, read `references/triadic-voice-guide.md`. It draws on three
exemplar corpora: `assets/russell-corpus/index.json`,
`assets/feynman-corpus/index.json` (pointers only), and
`assets/hoskinson-corpus/index.json` (built by `tools/build-voice-corpus`). The
discipline linters remain the quality floor for all three voices.
```

- [ ] **Step 5: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_skill_wiring.py -v`
Expected: PASS (2 passed)

- [ ] **Step 6: Commit**

```bash
git add skills/russellian-style/references/triadic-voice-guide.md skills/russellian-style/SKILL.md tools/build-voice-corpus/tests/test_skill_wiring.py
git commit -m "Add triadic-voice fusion guide and wire into russellian-style"
```

---

## Task 14: README and full-suite green

**Files:**
- Create: `tools/build-voice-corpus/README.md`
- Verify: full tool test suite

- [ ] **Step 1: Write `tools/build-voice-corpus/README.md`**

```markdown
# build-voice-corpus

Resumable pipeline that turns `@charleshoskinsoncrypto` YouTube videos into the
Hoskinson exemplar corpus used by `russellian-style`.

Stages: discover (scrapling-fetch) → sample (deterministic stratified) →
fetch_captions (yt-dlp) → clean (VTT) → style_tag (LLM) → append_to_index.
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

## Copyright

Hoskinson transcripts are the channel owner's own content (stored inline). The
Feynman corpus stores pointers and paraphrased metadata only — no verbatim text.
```

- [ ] **Step 2: Run the whole tool suite**

Run: `.venv/Scripts/python.exe -m pytest`
Expected: all tests pass across every test module.

- [ ] **Step 3: Commit**

```bash
git add tools/build-voice-corpus/README.md
git commit -m "Add build-voice-corpus README"
```

---

## Notes for the implementer

- **Doctrine exception.** yt-dlp is the single deliberate exception to "scrapling-fetch is the sole network skill," scoped to caption retrieval. When wiring `adapters.scrapling_fetch`, confirm the real public function in `skills/scrapling-fetch/skill_api.py` and adjust the import.
- **`published` is relative.** Channel-grid dates are strings like "2 years ago". The plan resolves real `upload_date` from yt-dlp per video; until that enrichment runs, sampling on the relative string will bucket everything into a wrong "year". When implementing the live run, enrich rows with yt-dlp `--print upload_date` (or `--dump-json`) before `sample()`. The offline tests use explicit `published` dates and are unaffected.
- **Linters unchanged.** No `russellian-style` linter is modified. The fused voice is exemplar-driven; discipline stays enforced.
- **scrapling-fetch on Python 3.14** requires the `scrapling[fetchers]` extra (curl_cffi/playwright/browserforge); already installed in this repo's skill venv.

## Deviations made during execution

These three corrections were applied while implementing the plan; the shipped code differs from the task bodies above accordingly.

- **Task 4 (clean).** The plan's `test_clean_vtt_human_subs` asserted `passages[0]["t_start"] == "00:00:01.000"`, but cue 1 of the fixture is a pure stock fragment that strips to empty. `clean_vtt` correctly skips empty passages (`if merged:`), so the surviving passage is cue 2. The shipped test asserts `len(passages) == 1`, `all(p["text"] for p in passages)`, and `passages[0]["t_start"] == "00:00:04.000"`. `clean_vtt` does not emit empty-text passages.
- **Task 6 (discover).** The regex `ytInitialData` extractor truncates if a JSON string value contains `};</script>` or `};` (real video titles do). Replaced with a string/escape-aware brace-matching `extract_initial_data`, plus a regression test for a title containing `};</script>`. `import re` removed.
- **Task 10 (cli).** The plan re-recorded `discovered`/`sampled` unconditionally each run; since `latest_state` is last-write-wins, a rerun regressed `tagged` videos back to `sampled`, breaking resumability (duplicate-id `ValueError`). The shipped `run()` guards each `record` so it never regresses a video to an earlier stage.
- **Task 11 (adapters).** `scrapling_fetch` runs scrapling-fetch through its own venv via subprocess (cwd = the skill dir) rather than importing `scripts.fetch` in-process, which would collide with this tool's own `scripts` package. Confirmed public API: `skill_api.fetch(url).html`.
```
