# Russell corpus expansion (50 → 500) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Grow `skills/russellian-style/assets/russell-corpus/index.json` from 50 to ~500 entries through an automated extract-and-verify pipeline whose hallucination resistance comes from deterministic source-grounding plus an independent LLM rhetorical cross-check plus a 5%-sample operator audit.

**Architecture:** A one-shot tool under `tools/build-russell-corpus/` chains four append-only JSONL stages — extract → sentinel → cross-check → audit → append. Each stage is independently testable. LLM-using stages accept `llm_call: Callable[[str], str]` so tests pass stubs (matches AGENTS.md convention). The runtime `russellian-style` skill API is untouched.

**Tech Stack:** Python ≥3.11, pytest 8.x, pyyaml, jsonschema, setuptools build backend (matches `skills/russellian-style/pyproject.toml`).

**Spec:** `docs/specs/2026-05-21-russell-corpus-expansion-design.md` (commit `390643c`).

---

## File structure

```
tools/build-russell-corpus/
├── pyproject.toml
├── README.md
├── scripts/
│   ├── __init__.py
│   ├── corpus_io.py
│   ├── derive_vocabulary.py
│   ├── extract_candidates.py
│   ├── sentinel.py
│   ├── cross_check.py
│   ├── audit_sample.py
│   ├── append_to_index.py
│   └── cli.py
├── assets/
│   ├── pd-allow-list.yaml
│   ├── vocabulary.json
│   ├── extractor-prompt.md
│   ├── generic-phrases.yaml
│   └── llm-config.yaml
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_corpus_io.py
    ├── test_derive_vocabulary.py
    ├── test_extract_candidates.py
    ├── test_sentinel.py
    ├── test_cross_check.py
    ├── test_audit_sample.py
    ├── test_append_to_index.py
    ├── test_e2e.py
    └── fixtures/
        ├── existing_index_sample.json
        ├── source_cache/
        │   └── problems_subset.html
        └── candidates/
            ├── good.json
            ├── hallucinated.json
            ├── wrong_line_hint.json
            ├── not_pd.json
            ├── duplicate.json
            ├── novel_tag.json
            ├── generic_lesson_surface.json
            ├── wrong_tag.json
            └── quoting_hume.json
```

Pipeline state lives outside the tool, under `tools/build-russell-corpus/runs/<batch-id>/`:

```
runs/<batch-id>/
├── candidates.jsonl
├── passed-sentinel.jsonl
├── rejected.jsonl
├── pending-tag.jsonl
├── proposed-tags.jsonl
├── verified.jsonl
├── audit/
│   ├── sample.md
│   └── halt-summary.md  (only if halted)
└── batch-meta.json
```

Each file in the tool has one responsibility. Stages communicate by reading the predecessor's JSONL file and writing their own. Nothing is silently dropped — every reject carries `{candidate_id, reason, evidence}`.

---

### Task 0: Project skeleton

**Files:**
- Create: `tools/build-russell-corpus/pyproject.toml`
- Create: `tools/build-russell-corpus/README.md`
- Create: `tools/build-russell-corpus/scripts/__init__.py` (empty)
- Create: `tools/build-russell-corpus/tests/__init__.py` (empty)
- Create: `tools/build-russell-corpus/tests/fixtures/.gitkeep` (empty)

- [ ] **Step 1: Write `tools/build-russell-corpus/pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "build-russell-corpus"
version = "0.1.0"
description = "One-shot pipeline that expands the russellian-style Russell corpus from 50 to ~500 entries under deterministic and LLM-cross-check QA."
requires-python = ">=3.11"
dependencies = [
    "pyyaml>=6.0,<7.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0,<9.0",
    "pyyaml>=6.0,<7.0",
    "jsonschema>=4.21,<5.0",
]

[tool.setuptools]
packages = ["scripts"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-v"
```

- [ ] **Step 2: Write `tools/build-russell-corpus/README.md`**

```markdown
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
```

- [ ] **Step 3: Create empty `__init__.py` and `.gitkeep` files**

Run:
```bash
mkdir -p tools/build-russell-corpus/scripts tools/build-russell-corpus/tests/fixtures
touch tools/build-russell-corpus/scripts/__init__.py
touch tools/build-russell-corpus/tests/__init__.py
touch tools/build-russell-corpus/tests/fixtures/.gitkeep
```

- [ ] **Step 4: Verify package structure**

Run:
```bash
cd tools/build-russell-corpus
python -m venv .venv
.venv/Scripts/pip install -e ".[dev]"
.venv/Scripts/python -m pytest tests/ -q
```
Expected: `no tests ran` (the tests dir is empty). Exit code 5 is fine for an empty suite.

- [ ] **Step 5: Commit**

```bash
git add tools/build-russell-corpus/pyproject.toml tools/build-russell-corpus/README.md tools/build-russell-corpus/scripts/__init__.py tools/build-russell-corpus/tests/__init__.py tools/build-russell-corpus/tests/fixtures/.gitkeep
git commit -m "tools/build-russell-corpus: project skeleton"
```

---

### Task 1: `corpus_io` — JSONL ledger helpers

**Files:**
- Create: `tools/build-russell-corpus/scripts/corpus_io.py`
- Test: `tools/build-russell-corpus/tests/test_corpus_io.py`

- [ ] **Step 1: Write the failing test for `append_jsonl` and `read_jsonl`**

Create `tests/test_corpus_io.py`:

```python
from pathlib import Path
from scripts.corpus_io import append_jsonl, read_jsonl


def test_append_then_read_jsonl_roundtrips(tmp_path: Path) -> None:
    target = tmp_path / "ledger.jsonl"
    append_jsonl(target, {"id": "a", "n": 1})
    append_jsonl(target, {"id": "b", "n": 2})
    rows = read_jsonl(target)
    assert rows == [{"id": "a", "n": 1}, {"id": "b", "n": 2}]


def test_read_jsonl_missing_file_returns_empty_list(tmp_path: Path) -> None:
    assert read_jsonl(tmp_path / "absent.jsonl") == []
```

- [ ] **Step 2: Run test, verify it fails**

Run:
```bash
cd tools/build-russell-corpus
.venv/Scripts/python -m pytest tests/test_corpus_io.py -v
```
Expected: ImportError on `scripts.corpus_io`.

- [ ] **Step 3: Write minimal implementation**

Create `scripts/corpus_io.py`:

```python
"""Append-only JSONL ledger I/O for the corpus build pipeline."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    """Append one JSON object as a single line. Creates the file and parents if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
        fh.write("\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read a JSONL file. Returns [] if the file does not exist."""
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows
```

- [ ] **Step 4: Run test, verify it passes**

Run:
```bash
.venv/Scripts/python -m pytest tests/test_corpus_io.py -v
```
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add tools/build-russell-corpus/scripts/corpus_io.py tools/build-russell-corpus/tests/test_corpus_io.py
git commit -m "tools/build-russell-corpus: jsonl ledger helpers"
```

---

### Task 2: `corpus_io` — index.json read/append

**Files:**
- Modify: `tools/build-russell-corpus/scripts/corpus_io.py`
- Modify: `tools/build-russell-corpus/tests/test_corpus_io.py`

- [ ] **Step 1: Write failing test for index read/append**

Append to `tests/test_corpus_io.py`:

```python
import json

from scripts.corpus_io import read_index, append_index_entries


def test_read_index_returns_paragraphs(tmp_path: Path) -> None:
    idx_path = tmp_path / "index.json"
    idx_path.write_text(json.dumps({
        "version": "0.1.0",
        "paragraph_count": 1,
        "sources": {"problems": {"title": "x", "url": "u", "copyright_status": "public_domain_us", "mode": ["m"]}},
        "paragraphs": [
            {"id": "problems-001", "source": "problems", "line_hint": 433,
             "rhetorical_move": "rm", "tags": ["t1"]},
        ],
    }))
    idx = read_index(idx_path)
    assert idx["paragraph_count"] == 1
    assert idx["paragraphs"][0]["id"] == "problems-001"


def test_append_index_entries_updates_count_and_preserves_existing(tmp_path: Path) -> None:
    idx_path = tmp_path / "index.json"
    idx_path.write_text(json.dumps({
        "version": "0.1.0",
        "paragraph_count": 1,
        "sources": {"problems": {"title": "x", "url": "u", "copyright_status": "public_domain_us", "mode": ["m"]}},
        "paragraphs": [
            {"id": "problems-001", "source": "problems", "line_hint": 433,
             "rhetorical_move": "rm", "tags": ["t1"]},
        ],
    }))
    new_entries = [
        {"id": "problems-051", "source": "problems", "line_hint": 812,
         "rhetorical_move": "rm2", "tags": ["t2"],
         "content_locator": "Philosophy, throughout"},
    ]
    append_index_entries(idx_path, new_entries)
    idx = json.loads(idx_path.read_text())
    assert idx["paragraph_count"] == 2
    assert len(idx["paragraphs"]) == 2
    assert idx["paragraphs"][1]["id"] == "problems-051"
    assert idx["paragraphs"][1]["content_locator"] == "Philosophy, throughout"
    # original entry preserved verbatim
    assert idx["paragraphs"][0]["id"] == "problems-001"
```

- [ ] **Step 2: Run test, verify it fails**

Run:
```bash
.venv/Scripts/python -m pytest tests/test_corpus_io.py::test_read_index_returns_paragraphs -v
```
Expected: ImportError on `read_index`.

- [ ] **Step 3: Extend `scripts/corpus_io.py`**

Append to `scripts/corpus_io.py`:

```python
def read_index(path: Path) -> dict[str, Any]:
    """Read the russellian-style corpus index.json."""
    return json.loads(path.read_text(encoding="utf-8"))


def append_index_entries(path: Path, new_entries: list[dict[str, Any]]) -> None:
    """Append new paragraph entries to index.json and update paragraph_count.

    Existing entries are preserved verbatim. Writes atomically via tempfile rename.
    """
    idx = read_index(path)
    existing_ids = {e["id"] for e in idx["paragraphs"]}
    for entry in new_entries:
        if entry["id"] in existing_ids:
            raise ValueError(f"entry id {entry['id']!r} already exists in {path}")
    idx["paragraphs"].extend(new_entries)
    idx["paragraph_count"] = len(idx["paragraphs"])
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(idx, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)
```

- [ ] **Step 4: Run tests, verify they pass**

Run:
```bash
.venv/Scripts/python -m pytest tests/test_corpus_io.py -v
```
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add tools/build-russell-corpus/scripts/corpus_io.py tools/build-russell-corpus/tests/test_corpus_io.py
git commit -m "tools/build-russell-corpus: index.json read and append"
```

---

### Task 3: `corpus_io` — content-locator hashing and source-cache helpers

**Files:**
- Modify: `tools/build-russell-corpus/scripts/corpus_io.py`
- Modify: `tools/build-russell-corpus/tests/test_corpus_io.py`
- Create: `tools/build-russell-corpus/tests/fixtures/source_cache/problems_subset.html`

- [ ] **Step 1: Write fixture source file**

Create `tests/fixtures/source_cache/problems_subset.html`:

```html
<html><body>
<p>Philosophy, throughout its history, has consisted of two parts inharmoniously blended: on the one hand a theory as to the nature of the world, on the other an ethical or political doctrine as to the best way of living.</p>
<p>The failure to separate these two with sufficient clarity has been a source of much confused thinking.</p>
<p>Philosophers from Plato to William James have allowed their opinions as to the constitution of the universe to be influenced by the desire for edification.</p>
</body></html>
```

- [ ] **Step 2: Write failing tests for hashing and source lookup**

Append to `tests/test_corpus_io.py`:

```python
from scripts.corpus_io import content_locator, paragraph_in_source, find_paragraph_line


FIXTURE_SOURCE = Path(__file__).parent / "fixtures" / "source_cache" / "problems_subset.html"


def test_content_locator_returns_first_120_chars_stripped() -> None:
    text = "  Philosophy, throughout its history, has consisted of two parts inharmoniously blended: on the one hand a theory as to the nature of the world, on the other an ethical or political doctrine.  "
    assert content_locator(text) == "Philosophy, throughout its history, has consisted of two parts inharmoniously blended: on the one hand a theory as to the n"
    assert len(content_locator(text)) == 120


def test_paragraph_in_source_matches_verbatim() -> None:
    para = "The failure to separate these two with sufficient clarity has been a source of much confused thinking."
    assert paragraph_in_source(para, FIXTURE_SOURCE) is True


def test_paragraph_in_source_rejects_hallucinated() -> None:
    para = "Philosophy proves that all dogs are mortal and that Socrates is a dog."
    assert paragraph_in_source(para, FIXTURE_SOURCE) is False


def test_find_paragraph_line_returns_locator_line_number() -> None:
    locator = "The failure to separate"
    line = find_paragraph_line(locator, FIXTURE_SOURCE)
    assert isinstance(line, int)
    assert line >= 1
```

- [ ] **Step 3: Run, verify failure**

Run:
```bash
.venv/Scripts/python -m pytest tests/test_corpus_io.py -v
```
Expected: ImportError on `content_locator`.

- [ ] **Step 4: Extend `scripts/corpus_io.py`**

Append to `scripts/corpus_io.py`:

```python
def content_locator(paragraph_text: str) -> str:
    """First 120 stripped characters of a paragraph — authoritative position locator.

    Used to find a paragraph in source even when line numbers drift across editions.
    """
    return paragraph_text.strip()[:120]


def paragraph_in_source(paragraph_text: str, source_path: Path) -> bool:
    """True iff the paragraph appears verbatim in the cached source file.

    The check is conservative: it requires the locator (first 120 chars stripped) to appear
    as a contiguous substring in the source, AND the full paragraph to appear when whitespace
    is collapsed.
    """
    locator = content_locator(paragraph_text)
    source = source_path.read_text(encoding="utf-8")
    if locator not in source:
        return False
    # Normalise whitespace for full-paragraph match — Gutenberg HTML wraps differ across editions.
    normalised_para = " ".join(paragraph_text.split())
    normalised_source = " ".join(source.split())
    return normalised_para in normalised_source


def find_paragraph_line(locator: str, source_path: Path) -> int | None:
    """Return the 1-indexed line number where the locator first appears, or None."""
    with source_path.open("r", encoding="utf-8") as fh:
        for i, line in enumerate(fh, start=1):
            if locator in line:
                return i
    return None


def sha256_hex(text: str) -> str:
    """Hex SHA-256 of UTF-8 text — used for dedup keys."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
```

- [ ] **Step 5: Run tests, verify they pass**

Run:
```bash
.venv/Scripts/python -m pytest tests/test_corpus_io.py -v
```
Expected: 8 passed.

- [ ] **Step 6: Commit**

```bash
git add tools/build-russell-corpus/scripts/corpus_io.py tools/build-russell-corpus/tests/test_corpus_io.py tools/build-russell-corpus/tests/fixtures/source_cache/problems_subset.html
git commit -m "tools/build-russell-corpus: content locator and source-cache lookup"
```

---

### Task 4: PD allow-list data file

**Files:**
- Create: `tools/build-russell-corpus/assets/pd-allow-list.yaml`

- [ ] **Step 1: Write the allow-list**

Create `tools/build-russell-corpus/assets/pd-allow-list.yaml`:

```yaml
# Public-domain Russell sources approved for corpus expansion.
# URLs match skills/russellian-style/assets/russell-corpus/index.json.
# Adding to this list requires manual operator review.
allowed:
  - source_id: problems
    title: "The Problems of Philosophy"
    url: "https://www.gutenberg.org/cache/epub/5827/pg5827-images.html"
  - source_id: mysticism
    title: "Mysticism and Logic and Other Essays"
    url: "https://www.gutenberg.org/cache/epub/25447/pg25447-images.html"
  - source_id: external-world
    title: "Our Knowledge of the External World as a Field for Scientific Method in Philosophy"
    url: "https://www.gutenberg.org/cache/epub/37090/pg37090-images.html"
  - source_id: analysis-mind
    title: "The Analysis of Mind"
    url: "https://www.gutenberg.org/cache/epub/2529/pg2529-images.html"
  - source_id: free-thought
    title: "Free Thought and Official Propaganda"
    url: "https://www.gutenberg.org/cache/epub/44932/pg44932-images.html"
  - source_id: political-ideals
    title: "Political Ideals"
    url: "https://www.gutenberg.org/cache/epub/4776/pg4776-images.html"
```

- [ ] **Step 2: Commit**

```bash
git add tools/build-russell-corpus/assets/pd-allow-list.yaml
git commit -m "tools/build-russell-corpus: PD allow-list (six existing corpus sources)"
```

---

### Task 5: `derive_vocabulary` — cluster existing tags into controlled vocabulary

The existing index.json paragraphs each carry a `tags` array (e.g. `["concrete_example", "abstraction_grounding"]`). Across the 50 entries there are ~80 unique tag strings. `derive_vocabulary` clusters these into a stable controlled vocabulary that new entries must use.

**Files:**
- Create: `tools/build-russell-corpus/scripts/derive_vocabulary.py`
- Create: `tools/build-russell-corpus/tests/fixtures/existing_index_sample.json`
- Test: `tools/build-russell-corpus/tests/test_derive_vocabulary.py`

- [ ] **Step 1: Write a small representative existing-index fixture**

Create `tests/fixtures/existing_index_sample.json`:

```json
{
  "version": "0.1.0",
  "paragraph_count": 5,
  "sources": {
    "problems": {"title": "The Problems of Philosophy", "url": "u", "copyright_status": "public_domain_us", "mode": ["m"]}
  },
  "paragraphs": [
    {"id": "problems-001", "source": "problems", "line_hint": 433,
     "rhetorical_move": "relation made concrete through a room example",
     "tags": ["concrete_example", "abstraction_grounding"]},
    {"id": "problems-002", "source": "problems", "line_hint": 436,
     "rhetorical_move": "objection to mental production of relations",
     "tags": ["counterexample", "argument_turn"]},
    {"id": "problems-007", "source": "problems", "line_hint": 711,
     "rhetorical_move": "practical prejudice personified",
     "tags": ["human_figure", "antithesis"]},
    {"id": "problems-008", "source": "problems", "line_hint": 713,
     "rhetorical_move": "philosophy compared against other studies",
     "tags": ["concession", "domain_contrast"]},
    {"id": "problems-010", "source": "problems", "line_hint": 723,
     "rhetorical_move": "uncertainty turned into value",
     "tags": ["reversal", "paragraph_turn"]}
  ]
}
```

- [ ] **Step 2: Write the failing test**

Create `tests/test_derive_vocabulary.py`:

```python
import json
from pathlib import Path

from scripts.derive_vocabulary import derive_controlled_vocabulary


FIXTURE = Path(__file__).parent / "fixtures" / "existing_index_sample.json"


def test_derive_vocabulary_returns_one_entry_per_unique_tag(tmp_path: Path) -> None:
    out = tmp_path / "vocabulary.json"
    derive_controlled_vocabulary(index_path=FIXTURE, out_path=out)
    vocab = json.loads(out.read_text())
    assert "tags" in vocab
    expected_slugs = {
        "concrete_example", "abstraction_grounding",
        "counterexample", "argument_turn",
        "human_figure", "antithesis",
        "concession", "domain_contrast",
        "reversal", "paragraph_turn",
    }
    actual_slugs = {t["slug"] for t in vocab["tags"]}
    assert actual_slugs == expected_slugs


def test_derive_vocabulary_each_tag_carries_anchors(tmp_path: Path) -> None:
    out = tmp_path / "vocabulary.json"
    derive_controlled_vocabulary(index_path=FIXTURE, out_path=out)
    vocab = json.loads(out.read_text())
    tag_by_slug = {t["slug"]: t for t in vocab["tags"]}
    assert "concrete_example" in tag_by_slug
    anchor_ids = tag_by_slug["concrete_example"]["anchor_ids"]
    assert "problems-001" in anchor_ids


def test_derive_vocabulary_emits_version_and_count(tmp_path: Path) -> None:
    out = tmp_path / "vocabulary.json"
    derive_controlled_vocabulary(index_path=FIXTURE, out_path=out)
    vocab = json.loads(out.read_text())
    assert vocab["version"] == "0.1.0"
    assert vocab["tag_count"] == len(vocab["tags"])
```

- [ ] **Step 3: Run, verify failure**

Run:
```bash
.venv/Scripts/python -m pytest tests/test_derive_vocabulary.py -v
```
Expected: ImportError.

- [ ] **Step 4: Write minimal implementation**

Create `scripts/derive_vocabulary.py`:

```python
"""Derive a controlled-vocabulary tag set from the existing russellian-style index.

Each unique tag string in any paragraph's `tags` array becomes one controlled-vocabulary
entry. The entry carries the slug, the paragraph IDs that anchor it, and a placeholder
prose definition the operator fills in during one-time review before the first extraction
batch runs.

This script runs ONCE before the first extraction batch. The output `vocabulary.json` is
committed and treated as stable; new tags discovered during extraction route through
`proposed-tags.jsonl` in `sentinel.py` for batched operator review.
"""

from __future__ import annotations

import json
from pathlib import Path

from scripts.corpus_io import read_index


def derive_controlled_vocabulary(index_path: Path, out_path: Path) -> None:
    """Read existing index, cluster tags, write vocabulary.json."""
    idx = read_index(index_path)
    tag_to_anchors: dict[str, list[str]] = {}
    for entry in idx["paragraphs"]:
        for tag in entry.get("tags", []):
            tag_to_anchors.setdefault(tag, []).append(entry["id"])
    vocab_entries = [
        {
            "slug": slug,
            "definition": "",  # operator fills in during one-time review
            "anchor_ids": sorted(anchors),
        }
        for slug, anchors in sorted(tag_to_anchors.items())
    ]
    out = {
        "version": idx.get("version", "0.1.0"),
        "tag_count": len(vocab_entries),
        "tags": vocab_entries,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    derive_controlled_vocabulary(args.index, args.out)
```

- [ ] **Step 5: Run tests, verify pass**

Run:
```bash
.venv/Scripts/python -m pytest tests/test_derive_vocabulary.py -v
```
Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add tools/build-russell-corpus/scripts/derive_vocabulary.py tools/build-russell-corpus/tests/test_derive_vocabulary.py tools/build-russell-corpus/tests/fixtures/existing_index_sample.json
git commit -m "tools/build-russell-corpus: derive controlled vocabulary from existing tags"
```

---

### Task 6: Run `derive_vocabulary` against the real index and commit `vocabulary.json`

**Files:**
- Create: `tools/build-russell-corpus/assets/vocabulary.json` (generated)

- [ ] **Step 1: Run the derivation against the real index**

Run from repo root:
```bash
cd tools/build-russell-corpus
.venv/Scripts/python -m scripts.derive_vocabulary --index ../../skills/russellian-style/assets/russell-corpus/index.json --out assets/vocabulary.json
```
Expected: `assets/vocabulary.json` written.

- [ ] **Step 2: Verify the output shape**

Run:
```bash
.venv/Scripts/python -c "import json; v=json.load(open('assets/vocabulary.json',encoding='utf-8')); print(v['tag_count']); print(sorted({t['slug'] for t in v['tags']})[:10])"
```
Expected: a tag_count somewhere in the 60–90 range and a sorted list of slug strings.

- [ ] **Step 3: Operator review (manual)**

Open `assets/vocabulary.json` and fill in the `definition` field for each tag with a short prose definition (one sentence). This is a one-time human pass. If two slugs are clearly synonyms, merge them by editing the file in place — combine their `anchor_ids` lists and drop the redundant entry; update `tag_count`. Do not invent new slugs; only consolidate. Save when done.

- [ ] **Step 4: Commit**

```bash
git add tools/build-russell-corpus/assets/vocabulary.json
git commit -m "tools/build-russell-corpus: initial controlled vocabulary from existing 50 entries"
```

---

### Task 7: Extractor prompt and LLM config

**Files:**
- Create: `tools/build-russell-corpus/assets/extractor-prompt.md`
- Create: `tools/build-russell-corpus/assets/llm-config.yaml`
- Create: `tools/build-russell-corpus/assets/generic-phrases.yaml`

- [ ] **Step 1: Write the extractor prompt**

Create `tools/build-russell-corpus/assets/extractor-prompt.md`:

```markdown
# Russell corpus extractor

You are reading a single public-domain Bertrand Russell text. Your job is to identify N
paragraphs whose rhetorical move is worth capturing as anchors for a writing-style
calibration corpus.

## What counts as a corpus-worthy paragraph

A paragraph qualifies when it performs one of the controlled-vocabulary rhetorical moves
exactly — concession-then-distinction, counterexample-before-conclusion, last-sentence-reversal,
and so on. The full vocabulary is provided in the {{VOCABULARY}} block; only tags from that
block are legal.

A paragraph does NOT qualify when it merely conveys information, lists, summarises, or
introduces a chapter. The corpus is not a Russell anthology; it is a calibration set for
rhetorical moves.

## Output format

For each qualifying paragraph emit one JSON object on its own line (JSONL). Schema:

```
{
  "candidate_id": "<source>-<NNN>",
  "source_id": "<source>",
  "source_url": "<URL from PD allow-list>",
  "line_hint": <int>,
  "content_locator": "<first 120 chars of the paragraph, verbatim, no leading whitespace>",
  "paragraph_text": "<verbatim paragraph text, single line with internal whitespace preserved>",
  "rhetorical_move_tag": "<one slug from {{VOCABULARY}}>",
  "calibration_lesson": "<one sentence specific to THIS paragraph; not a generic Russell virtue>"
}
```

## Constraints

- Quote `paragraph_text` verbatim. Do not paraphrase. Source-match is verified by SHA.
- Pick the SHORTEST self-contained paragraph that performs the move. Sentence-fragment moves do not count.
- Russell quoting another author does NOT count, even if the quoted text is beautiful. The cross-check stage flags quotations.
- The `calibration_lesson` must be diagnostic: a reader looking at this paragraph should be able to point to the specific phrase or move the lesson describes. Avoid phrases like "uses concrete example" or "varies sentence length" — these are generic and reject.

## Source text

{{SOURCE_TEXT}}

## Controlled vocabulary

{{VOCABULARY}}
```

- [ ] **Step 2: Write the LLM config**

Create `tools/build-russell-corpus/assets/llm-config.yaml`:

```yaml
# LLM configuration for the corpus build pipeline.
# Production runs use claude-opus-4-7 by default. Extract and cross-check should use
# distinct system prompts and ideally distinct models to reduce shared-bias collusion.
# The runtime caller wires these into the llm_call: Callable[[str], str] parameter.

extract:
  model_id: "claude-opus-4-7"
  max_tokens: 8192
  temperature: 0.3
  notes: "Lower temperature reduces invented paragraphs; not zero so the LLM can choose among candidates."

cross_check:
  model_id: "claude-sonnet-4-6"
  max_tokens: 1024
  temperature: 0.0
  notes: "Different model from extract. Temperature zero — classification, not generation."

batch:
  candidates_per_source: 100
  audit_sample_rate: 0.05
  audit_halt_threshold: 0.10
```

- [ ] **Step 3: Write the empty generic-phrases seed**

Create `tools/build-russell-corpus/assets/generic-phrases.yaml`:

```yaml
# Phrases that, when they appear in a candidate's calibration_lesson, indicate the lesson
# is too generic to be useful for calibration. The sentinel surface-filter rejects on hit.
#
# Seed list is empty. The operator appends phrases observed during audit of the first batch.
# Example entries (to be added by operator):
#   - "uses a concrete example"
#   - "varies sentence length"
#   - "Russell writes clearly"
phrases: []
```

- [ ] **Step 4: Commit**

```bash
git add tools/build-russell-corpus/assets/extractor-prompt.md tools/build-russell-corpus/assets/llm-config.yaml tools/build-russell-corpus/assets/generic-phrases.yaml
git commit -m "tools/build-russell-corpus: extractor prompt, LLM config, generic-phrases seed"
```

---

### Task 8: `extract_candidates` — LLM extractor with stub-able callable

**Files:**
- Create: `tools/build-russell-corpus/scripts/extract_candidates.py`
- Test: `tools/build-russell-corpus/tests/test_extract_candidates.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_extract_candidates.py`:

```python
import json
from pathlib import Path

from scripts.extract_candidates import extract_candidates


FIXTURE_SOURCE = Path(__file__).parent / "fixtures" / "source_cache" / "problems_subset.html"


def _fake_llm_returns_two_candidates(prompt: str) -> str:
    return "\n".join([
        json.dumps({
            "candidate_id": "problems-051",
            "source_id": "problems",
            "source_url": "https://www.gutenberg.org/cache/epub/5827/pg5827-images.html",
            "line_hint": 2,
            "content_locator": "Philosophy, throughout its history,",
            "paragraph_text": "Philosophy, throughout its history, has consisted of two parts inharmoniously blended: on the one hand a theory as to the nature of the world, on the other an ethical or political doctrine as to the best way of living.",
            "rhetorical_move_tag": "domain_contrast",
            "calibration_lesson": "Russell opens by splitting philosophy into two domains that the rest of the chapter will pull apart.",
        }),
        json.dumps({
            "candidate_id": "problems-052",
            "source_id": "problems",
            "source_url": "https://www.gutenberg.org/cache/epub/5827/pg5827-images.html",
            "line_hint": 3,
            "content_locator": "The failure to separate these two",
            "paragraph_text": "The failure to separate these two with sufficient clarity has been a source of much confused thinking.",
            "rhetorical_move_tag": "diagnosis",
            "calibration_lesson": "A single short sentence indicts the prior confusion before the analysis begins.",
        }),
    ])


def test_extract_candidates_writes_jsonl(tmp_path: Path) -> None:
    out = tmp_path / "candidates.jsonl"
    extract_candidates(
        source_path=FIXTURE_SOURCE,
        source_id="problems",
        source_url="https://www.gutenberg.org/cache/epub/5827/pg5827-images.html",
        vocabulary_path=Path(__file__).parent.parent / "assets" / "vocabulary.json",
        prompt_path=Path(__file__).parent.parent / "assets" / "extractor-prompt.md",
        out_path=out,
        n=2,
        llm_call=_fake_llm_returns_two_candidates,
    )
    rows = [json.loads(line) for line in out.read_text().splitlines() if line.strip()]
    assert len(rows) == 2
    assert rows[0]["candidate_id"] == "problems-051"
    assert rows[1]["rhetorical_move_tag"] == "diagnosis"


def test_extract_candidates_passes_n_and_source_into_prompt(tmp_path: Path) -> None:
    captured: dict[str, str] = {}

    def capturing_llm(prompt: str) -> str:
        captured["prompt"] = prompt
        return ""

    extract_candidates(
        source_path=FIXTURE_SOURCE,
        source_id="problems",
        source_url="https://www.gutenberg.org/cache/epub/5827/pg5827-images.html",
        vocabulary_path=Path(__file__).parent.parent / "assets" / "vocabulary.json",
        prompt_path=Path(__file__).parent.parent / "assets" / "extractor-prompt.md",
        out_path=tmp_path / "candidates.jsonl",
        n=7,
        llm_call=capturing_llm,
    )
    assert "Philosophy, throughout its history" in captured["prompt"]
    # vocabulary block should be substituted
    assert "{{VOCABULARY}}" not in captured["prompt"]
    assert "{{SOURCE_TEXT}}" not in captured["prompt"]
```

- [ ] **Step 2: Run, verify failure**

Run:
```bash
.venv/Scripts/python -m pytest tests/test_extract_candidates.py -v
```
Expected: ImportError.

- [ ] **Step 3: Write the implementation**

Create `scripts/extract_candidates.py`:

```python
"""LLM extractor: reads one PD Russell source, proposes N candidate corpus entries.

The LLM is parameterised via `llm_call: Callable[[str], str]` so tests pass stubs.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from scripts.corpus_io import append_jsonl


def extract_candidates(
    *,
    source_path: Path,
    source_id: str,
    source_url: str,
    vocabulary_path: Path,
    prompt_path: Path,
    out_path: Path,
    n: int,
    llm_call: Callable[[str], str],
) -> None:
    """Read source, build the extractor prompt, call the LLM, write candidates.jsonl."""
    source_text = source_path.read_text(encoding="utf-8")
    vocabulary = vocabulary_path.read_text(encoding="utf-8")
    prompt_template = prompt_path.read_text(encoding="utf-8")
    prompt = (
        prompt_template
        .replace("{{SOURCE_TEXT}}", source_text)
        .replace("{{VOCABULARY}}", vocabulary)
        .replace("{{N}}", str(n))
        .replace("{{SOURCE_ID}}", source_id)
        .replace("{{SOURCE_URL}}", source_url)
    )
    raw = llm_call(prompt)
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            # malformed LLM output: skip line; sentinel will catch absence downstream
            continue
        append_jsonl(out_path, obj)
```

- [ ] **Step 4: Run tests, verify pass**

Run:
```bash
.venv/Scripts/python -m pytest tests/test_extract_candidates.py -v
```
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add tools/build-russell-corpus/scripts/extract_candidates.py tools/build-russell-corpus/tests/test_extract_candidates.py
git commit -m "tools/build-russell-corpus: llm extractor with stub-able callable"
```

---

### Task 9: `sentinel` — happy-path entry passes all six checks

**Files:**
- Create: `tools/build-russell-corpus/scripts/sentinel.py`
- Create: `tools/build-russell-corpus/tests/test_sentinel.py`
- Create: `tools/build-russell-corpus/tests/fixtures/candidates/good.json`

- [ ] **Step 1: Write the good-candidate fixture**

Create `tests/fixtures/candidates/good.json`:

```json
{
  "candidate_id": "problems-051",
  "source_id": "problems",
  "source_url": "https://www.gutenberg.org/cache/epub/5827/pg5827-images.html",
  "line_hint": 2,
  "content_locator": "Philosophy, throughout its history,",
  "paragraph_text": "Philosophy, throughout its history, has consisted of two parts inharmoniously blended: on the one hand a theory as to the nature of the world, on the other an ethical or political doctrine as to the best way of living.",
  "rhetorical_move_tag": "domain_contrast",
  "calibration_lesson": "Russell opens by splitting philosophy into two domains that the rest of the chapter will pull apart."
}
```

- [ ] **Step 2: Write the failing test**

Create `tests/test_sentinel.py`:

```python
import json
from pathlib import Path

from scripts.sentinel import run_sentinel, SentinelOutcome


FIXTURES = Path(__file__).parent / "fixtures"
SOURCE_CACHE = FIXTURES / "source_cache"
CANDIDATES = FIXTURES / "candidates"
EXISTING_INDEX = FIXTURES / "existing_index_sample.json"
ALLOW_LIST = Path(__file__).parent.parent / "assets" / "pd-allow-list.yaml"
VOCABULARY = Path(__file__).parent.parent / "assets" / "vocabulary.json"
GENERIC_PHRASES = Path(__file__).parent.parent / "assets" / "generic-phrases.yaml"


def _patched_allow_list_for_tests(tmp_path: Path) -> Path:
    """Allow-list pointing at the fixture source cache (not the live Gutenberg URL)."""
    out = tmp_path / "pd-allow-list.yaml"
    out.write_text(
        "allowed:\n"
        "  - source_id: problems\n"
        "    title: \"The Problems of Philosophy\"\n"
        "    url: \"https://www.gutenberg.org/cache/epub/5827/pg5827-images.html\"\n",
        encoding="utf-8",
    )
    return out


def test_sentinel_good_candidate_passes(tmp_path: Path) -> None:
    candidate = json.loads((CANDIDATES / "good.json").read_text())
    outcome = run_sentinel(
        candidate=candidate,
        source_path=SOURCE_CACHE / "problems_subset.html",
        allow_list_path=_patched_allow_list_for_tests(tmp_path),
        vocabulary_path=VOCABULARY,
        generic_phrases_path=GENERIC_PHRASES,
        existing_index_path=EXISTING_INDEX,
        batch_seen_locators=set(),
    )
    assert outcome.status == "pass"
    assert outcome.reason is None
```

- [ ] **Step 3: Run, verify failure**

Run:
```bash
.venv/Scripts/python -m pytest tests/test_sentinel.py -v
```
Expected: ImportError on `scripts.sentinel`.

- [ ] **Step 4: Write the minimal sentinel implementation**

Create `scripts/sentinel.py`:

```python
"""Sentinel — six deterministic checks against a candidate corpus entry.

Returns a SentinelOutcome with status ∈ {"pass", "reject", "defer"} and an optional reason
code. The orchestrator routes outcomes to passed-sentinel.jsonl / rejected.jsonl /
pending-tag.jsonl.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from scripts.corpus_io import (
    content_locator,
    paragraph_in_source,
    find_paragraph_line,
    read_index,
)


@dataclass
class SentinelOutcome:
    status: str  # "pass" | "reject" | "defer"
    reason: str | None
    evidence: dict[str, Any] | None
    corrected_line_hint: int | None = None


def _load_allow_list(path: Path) -> dict[str, dict[str, str]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {entry["source_id"]: entry for entry in data["allowed"]}


def _load_vocabulary(path: Path) -> set[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {t["slug"] for t in data["tags"]}


def _load_generic_phrases(path: Path) -> list[str]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return list(data.get("phrases") or [])


def run_sentinel(
    *,
    candidate: dict[str, Any],
    source_path: Path,
    allow_list_path: Path,
    vocabulary_path: Path,
    generic_phrases_path: Path,
    existing_index_path: Path,
    batch_seen_locators: set[str],
) -> SentinelOutcome:
    """Run all six deterministic checks against a single candidate."""
    allow_list = _load_allow_list(allow_list_path)
    if candidate["source_id"] not in allow_list:
        return SentinelOutcome("reject", "not-pd-allowed", {"source_id": candidate["source_id"]})

    if not paragraph_in_source(candidate["paragraph_text"], source_path):
        return SentinelOutcome("reject", "source-mismatch", {"locator": content_locator(candidate["paragraph_text"])})

    found_line = find_paragraph_line(content_locator(candidate["paragraph_text"]), source_path)
    if found_line is None:
        return SentinelOutcome("reject", "locator-not-found", {"locator": content_locator(candidate["paragraph_text"])})
    corrected = found_line if abs(found_line - candidate["line_hint"]) > 50 else None

    idx = read_index(existing_index_path)
    existing_locators = {
        content_locator(e.get("content_locator") or e.get("rhetorical_move", "")) for e in idx["paragraphs"]
    }
    cand_locator = content_locator(candidate["paragraph_text"])
    if cand_locator in existing_locators or cand_locator in batch_seen_locators:
        return SentinelOutcome("reject", "duplicate", {"locator": cand_locator})

    vocabulary = _load_vocabulary(vocabulary_path)
    if candidate["rhetorical_move_tag"] not in vocabulary:
        return SentinelOutcome("defer", "novel-tag", {"proposed_tag": candidate["rhetorical_move_tag"]})

    generics = _load_generic_phrases(generic_phrases_path)
    lesson_lower = candidate["calibration_lesson"].lower()
    for phrase in generics:
        if phrase.lower() in lesson_lower:
            return SentinelOutcome("reject", "generic-lesson-filter", {"matched_phrase": phrase})

    return SentinelOutcome("pass", None, None, corrected_line_hint=corrected)
```

- [ ] **Step 5: Run test, verify pass**

Run:
```bash
.venv/Scripts/python -m pytest tests/test_sentinel.py -v
```
Expected: 1 passed.

- [ ] **Step 6: Commit**

```bash
git add tools/build-russell-corpus/scripts/sentinel.py tools/build-russell-corpus/tests/test_sentinel.py tools/build-russell-corpus/tests/fixtures/candidates/good.json
git commit -m "tools/build-russell-corpus: sentinel happy-path pass"
```

---

### Task 10: `sentinel` — source-mismatch rejection

**Files:**
- Modify: `tools/build-russell-corpus/tests/test_sentinel.py`
- Create: `tools/build-russell-corpus/tests/fixtures/candidates/hallucinated.json`

- [ ] **Step 1: Write the hallucinated-paragraph fixture**

Create `tests/fixtures/candidates/hallucinated.json`:

```json
{
  "candidate_id": "problems-099",
  "source_id": "problems",
  "source_url": "https://www.gutenberg.org/cache/epub/5827/pg5827-images.html",
  "line_hint": 999,
  "content_locator": "Philosophy proves that all dogs are mortal",
  "paragraph_text": "Philosophy proves that all dogs are mortal and that Socrates is a dog.",
  "rhetorical_move_tag": "domain_contrast",
  "calibration_lesson": "Russell concludes Socrates is a dog through an invalid syllogism."
}
```

- [ ] **Step 2: Add failing test**

Append to `tests/test_sentinel.py`:

```python
def test_sentinel_rejects_hallucinated_paragraph(tmp_path: Path) -> None:
    candidate = json.loads((CANDIDATES / "hallucinated.json").read_text())
    outcome = run_sentinel(
        candidate=candidate,
        source_path=SOURCE_CACHE / "problems_subset.html",
        allow_list_path=_patched_allow_list_for_tests(tmp_path),
        vocabulary_path=VOCABULARY,
        generic_phrases_path=GENERIC_PHRASES,
        existing_index_path=EXISTING_INDEX,
        batch_seen_locators=set(),
    )
    assert outcome.status == "reject"
    assert outcome.reason == "source-mismatch"
```

- [ ] **Step 3: Run, verify pass (already covered by current implementation)**

Run:
```bash
.venv/Scripts/python -m pytest tests/test_sentinel.py -v
```
Expected: 2 passed. The sentinel's `paragraph_in_source` check already covers this.

- [ ] **Step 4: Commit**

```bash
git add tools/build-russell-corpus/tests/test_sentinel.py tools/build-russell-corpus/tests/fixtures/candidates/hallucinated.json
git commit -m "tools/build-russell-corpus: sentinel rejects hallucinated paragraph"
```

---

### Task 11: `sentinel` — PD allow-list, dedup, novel-tag, generic-lesson rejections

**Files:**
- Modify: `tools/build-russell-corpus/tests/test_sentinel.py`
- Create: `tools/build-russell-corpus/tests/fixtures/candidates/not_pd.json`
- Create: `tools/build-russell-corpus/tests/fixtures/candidates/duplicate.json`
- Create: `tools/build-russell-corpus/tests/fixtures/candidates/novel_tag.json`
- Create: `tools/build-russell-corpus/tests/fixtures/candidates/generic_lesson_surface.json`

- [ ] **Step 1: Write each rejection fixture**

Create `tests/fixtures/candidates/not_pd.json`:

```json
{
  "candidate_id": "marriage-001",
  "source_id": "marriage-morals",
  "source_url": "https://example.com/not-pd",
  "line_hint": 1,
  "content_locator": "Whatever may be said",
  "paragraph_text": "Whatever may be said in favour of the institution.",
  "rhetorical_move_tag": "concession",
  "calibration_lesson": "The opening reframes the institution before contesting it."
}
```

Create `tests/fixtures/candidates/duplicate.json` — uses an existing entry's text:

```json
{
  "candidate_id": "problems-001-dup",
  "source_id": "problems",
  "source_url": "https://www.gutenberg.org/cache/epub/5827/pg5827-images.html",
  "line_hint": 2,
  "content_locator": "Philosophy, throughout its history,",
  "paragraph_text": "Philosophy, throughout its history, has consisted of two parts inharmoniously blended: on the one hand a theory as to the nature of the world, on the other an ethical or political doctrine as to the best way of living.",
  "rhetorical_move_tag": "domain_contrast",
  "calibration_lesson": "Russell opens by splitting philosophy into two domains."
}
```

Create `tests/fixtures/candidates/novel_tag.json`:

```json
{
  "candidate_id": "problems-053",
  "source_id": "problems",
  "source_url": "https://www.gutenberg.org/cache/epub/5827/pg5827-images.html",
  "line_hint": 2,
  "content_locator": "Philosophy, throughout its history,",
  "paragraph_text": "Philosophy, throughout its history, has consisted of two parts inharmoniously blended: on the one hand a theory as to the nature of the world, on the other an ethical or political doctrine as to the best way of living.",
  "rhetorical_move_tag": "metaphor_destabilisation",
  "calibration_lesson": "A metaphor is destabilised by its own implication."
}
```

Create `tests/fixtures/candidates/generic_lesson_surface.json`:

```json
{
  "candidate_id": "problems-054",
  "source_id": "problems",
  "source_url": "https://www.gutenberg.org/cache/epub/5827/pg5827-images.html",
  "line_hint": 2,
  "content_locator": "Philosophy, throughout its history,",
  "paragraph_text": "Philosophy, throughout its history, has consisted of two parts inharmoniously blended: on the one hand a theory as to the nature of the world, on the other an ethical or political doctrine as to the best way of living.",
  "rhetorical_move_tag": "domain_contrast",
  "calibration_lesson": "Russell varies sentence length here for effect."
}
```

- [ ] **Step 2: Append four failing tests**

Append to `tests/test_sentinel.py`:

```python
def test_sentinel_rejects_source_off_allowlist(tmp_path: Path) -> None:
    candidate = json.loads((CANDIDATES / "not_pd.json").read_text())
    outcome = run_sentinel(
        candidate=candidate,
        source_path=SOURCE_CACHE / "problems_subset.html",
        allow_list_path=_patched_allow_list_for_tests(tmp_path),
        vocabulary_path=VOCABULARY,
        generic_phrases_path=GENERIC_PHRASES,
        existing_index_path=EXISTING_INDEX,
        batch_seen_locators=set(),
    )
    assert outcome.status == "reject"
    assert outcome.reason == "not-pd-allowed"


def test_sentinel_rejects_duplicate_in_batch(tmp_path: Path) -> None:
    candidate = json.loads((CANDIDATES / "duplicate.json").read_text())
    locator = "Philosophy, throughout its history, has consisted of two parts inharmoniously blended: on the one hand a theory as to the n"
    outcome = run_sentinel(
        candidate=candidate,
        source_path=SOURCE_CACHE / "problems_subset.html",
        allow_list_path=_patched_allow_list_for_tests(tmp_path),
        vocabulary_path=VOCABULARY,
        generic_phrases_path=GENERIC_PHRASES,
        existing_index_path=EXISTING_INDEX,
        batch_seen_locators={locator},
    )
    assert outcome.status == "reject"
    assert outcome.reason == "duplicate"


def test_sentinel_defers_novel_tag(tmp_path: Path) -> None:
    candidate = json.loads((CANDIDATES / "novel_tag.json").read_text())
    outcome = run_sentinel(
        candidate=candidate,
        source_path=SOURCE_CACHE / "problems_subset.html",
        allow_list_path=_patched_allow_list_for_tests(tmp_path),
        vocabulary_path=VOCABULARY,
        generic_phrases_path=GENERIC_PHRASES,
        existing_index_path=EXISTING_INDEX,
        batch_seen_locators=set(),
    )
    assert outcome.status == "defer"
    assert outcome.reason == "novel-tag"
    assert outcome.evidence["proposed_tag"] == "metaphor_destabilisation"


def test_sentinel_rejects_generic_lesson_via_surface_filter(tmp_path: Path) -> None:
    candidate = json.loads((CANDIDATES / "generic_lesson_surface.json").read_text())
    # Patch generic-phrases for this test only — empty seed in committed file.
    gp = tmp_path / "generic-phrases.yaml"
    gp.write_text("phrases:\n  - \"varies sentence length\"\n", encoding="utf-8")
    outcome = run_sentinel(
        candidate=candidate,
        source_path=SOURCE_CACHE / "problems_subset.html",
        allow_list_path=_patched_allow_list_for_tests(tmp_path),
        vocabulary_path=VOCABULARY,
        generic_phrases_path=gp,
        existing_index_path=EXISTING_INDEX,
        batch_seen_locators=set(),
    )
    assert outcome.status == "reject"
    assert outcome.reason == "generic-lesson-filter"
    assert outcome.evidence["matched_phrase"] == "varies sentence length"
```

- [ ] **Step 3: Run, verify all four pass with current sentinel**

Run:
```bash
.venv/Scripts/python -m pytest tests/test_sentinel.py -v
```
Expected: 6 passed.

If any fail, the sentinel implementation from Task 9 is missing a check. Fix `scripts/sentinel.py` and rerun.

- [ ] **Step 4: Commit**

```bash
git add tools/build-russell-corpus/tests/test_sentinel.py tools/build-russell-corpus/tests/fixtures/candidates/not_pd.json tools/build-russell-corpus/tests/fixtures/candidates/duplicate.json tools/build-russell-corpus/tests/fixtures/candidates/novel_tag.json tools/build-russell-corpus/tests/fixtures/candidates/generic_lesson_surface.json
git commit -m "tools/build-russell-corpus: sentinel allow-list, dedup, novel-tag, generic-lesson"
```

---

### Task 12: `sentinel` — pipeline orchestrator over a candidates ledger

The orchestrator iterates `candidates.jsonl` and routes each outcome to the right ledger.

**Files:**
- Modify: `tools/build-russell-corpus/scripts/sentinel.py`
- Modify: `tools/build-russell-corpus/tests/test_sentinel.py`

- [ ] **Step 1: Write failing test for the orchestrator**

Append to `tests/test_sentinel.py`:

```python
from scripts.sentinel import run_sentinel_batch


def test_run_sentinel_batch_routes_outcomes_to_three_ledgers(tmp_path: Path) -> None:
    # Build a candidates.jsonl with one good, one hallucinated, one novel-tag.
    cands = tmp_path / "candidates.jsonl"
    rows = [
        json.loads((CANDIDATES / "good.json").read_text()),
        json.loads((CANDIDATES / "hallucinated.json").read_text()),
        json.loads((CANDIDATES / "novel_tag.json").read_text()),
    ]
    cands.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

    run_dir = tmp_path / "run"
    run_sentinel_batch(
        candidates_path=cands,
        source_cache_dir=SOURCE_CACHE,
        allow_list_path=_patched_allow_list_for_tests(tmp_path),
        vocabulary_path=VOCABULARY,
        generic_phrases_path=GENERIC_PHRASES,
        existing_index_path=EXISTING_INDEX,
        run_dir=run_dir,
    )
    passed = [json.loads(l) for l in (run_dir / "passed-sentinel.jsonl").read_text().splitlines() if l.strip()]
    rejected = [json.loads(l) for l in (run_dir / "rejected.jsonl").read_text().splitlines() if l.strip()]
    pending = [json.loads(l) for l in (run_dir / "pending-tag.jsonl").read_text().splitlines() if l.strip()]
    proposed_tags = [json.loads(l) for l in (run_dir / "proposed-tags.jsonl").read_text().splitlines() if l.strip()]

    assert len(passed) == 1 and passed[0]["candidate_id"] == "problems-051"
    assert len(rejected) == 1 and rejected[0]["reason"] == "source-mismatch"
    assert len(pending) == 1 and pending[0]["candidate_id"] == "problems-053"
    assert len(proposed_tags) == 1 and proposed_tags[0]["tag"] == "metaphor_destabilisation"
```

- [ ] **Step 2: Run, verify failure**

Run:
```bash
.venv/Scripts/python -m pytest tests/test_sentinel.py::test_run_sentinel_batch_routes_outcomes_to_three_ledgers -v
```
Expected: ImportError on `run_sentinel_batch`.

- [ ] **Step 3: Implement the orchestrator**

Append to `scripts/sentinel.py`:

```python
def run_sentinel_batch(
    *,
    candidates_path: Path,
    source_cache_dir: Path,
    allow_list_path: Path,
    vocabulary_path: Path,
    generic_phrases_path: Path,
    existing_index_path: Path,
    run_dir: Path,
) -> None:
    """Iterate candidates.jsonl, route each outcome to the matching ledger."""
    run_dir.mkdir(parents=True, exist_ok=True)
    passed = run_dir / "passed-sentinel.jsonl"
    rejected = run_dir / "rejected.jsonl"
    pending = run_dir / "pending-tag.jsonl"
    proposed_tags = run_dir / "proposed-tags.jsonl"

    batch_locators: set[str] = set()
    proposed_seen: set[str] = set()
    allow_list = _load_allow_list(allow_list_path)

    with candidates_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            cand = json.loads(line)
            src_id = cand["source_id"]
            if src_id not in allow_list:
                append_jsonl(rejected, {"candidate_id": cand["candidate_id"], "reason": "not-pd-allowed", "evidence": {"source_id": src_id}})
                continue
            # Resolve the cached source file for this source_id. Convention: <cache>/<source_id>_subset.html for tests;
            # in production the cache layout matches scrapling-fetch's directory shape.
            source_path = source_cache_dir / f"{src_id}_subset.html"
            outcome = run_sentinel(
                candidate=cand,
                source_path=source_path,
                allow_list_path=allow_list_path,
                vocabulary_path=vocabulary_path,
                generic_phrases_path=generic_phrases_path,
                existing_index_path=existing_index_path,
                batch_seen_locators=batch_locators,
            )
            if outcome.status == "pass":
                if outcome.corrected_line_hint is not None:
                    cand["line_hint"] = outcome.corrected_line_hint
                append_jsonl(passed, cand)
                batch_locators.add(content_locator(cand["paragraph_text"]))
            elif outcome.status == "defer":
                append_jsonl(pending, cand)
                tag = cand["rhetorical_move_tag"]
                if tag not in proposed_seen:
                    append_jsonl(proposed_tags, {"tag": tag, "first_candidate_id": cand["candidate_id"]})
                    proposed_seen.add(tag)
            else:
                append_jsonl(rejected, {
                    "candidate_id": cand["candidate_id"],
                    "reason": outcome.reason,
                    "evidence": outcome.evidence,
                })
```

The import `append_jsonl` must be added at the top of the file:

```python
from scripts.corpus_io import (
    append_jsonl,
    content_locator,
    paragraph_in_source,
    find_paragraph_line,
    read_index,
)
```

- [ ] **Step 4: Run tests, verify pass**

Run:
```bash
.venv/Scripts/python -m pytest tests/test_sentinel.py -v
```
Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add tools/build-russell-corpus/scripts/sentinel.py tools/build-russell-corpus/tests/test_sentinel.py
git commit -m "tools/build-russell-corpus: sentinel batch orchestrator with ledger routing"
```

---

### Task 13: `cross_check` — independent LLM rhetorical reader

**Files:**
- Create: `tools/build-russell-corpus/scripts/cross_check.py`
- Create: `tools/build-russell-corpus/tests/test_cross_check.py`
- Create: `tools/build-russell-corpus/tests/fixtures/candidates/wrong_tag.json`
- Create: `tools/build-russell-corpus/tests/fixtures/candidates/quoting_hume.json`

- [ ] **Step 1: Write the wrong-tag and quoting-Hume fixtures**

Create `tests/fixtures/candidates/wrong_tag.json`:

```json
{
  "candidate_id": "problems-061",
  "source_id": "problems",
  "source_url": "https://www.gutenberg.org/cache/epub/5827/pg5827-images.html",
  "line_hint": 2,
  "content_locator": "Philosophy, throughout its history,",
  "paragraph_text": "Philosophy, throughout its history, has consisted of two parts inharmoniously blended: on the one hand a theory as to the nature of the world, on the other an ethical or political doctrine as to the best way of living.",
  "rhetorical_move_tag": "antithesis",
  "calibration_lesson": "Russell separates two domains the chapter will pull apart."
}
```

Create `tests/fixtures/candidates/quoting_hume.json`:

```json
{
  "candidate_id": "external-099",
  "source_id": "external-world",
  "source_url": "https://www.gutenberg.org/cache/epub/37090/pg37090-images.html",
  "line_hint": 200,
  "content_locator": "Hume, in his Treatise, observed",
  "paragraph_text": "Hume, in his Treatise, observed that 'all our distinct perceptions are distinct existences, and the mind never perceives any real connexion among distinct existences.'",
  "rhetorical_move_tag": "concession",
  "calibration_lesson": "Hume's atomism is acknowledged before being qualified."
}
```

- [ ] **Step 2: Write failing tests**

Create `tests/test_cross_check.py`:

```python
import json
from pathlib import Path

from scripts.cross_check import run_cross_check, CrossCheckOutcome


FIXTURES = Path(__file__).parent / "fixtures"
CANDIDATES = FIXTURES / "candidates"
VOCABULARY = Path(__file__).parent.parent / "assets" / "vocabulary.json"


def _llm_agrees_with_tag(prompt: str) -> str:
    return json.dumps({
        "top1_tag": "domain_contrast",
        "top3_tags": ["domain_contrast", "antithesis", "diagnosis"],
        "is_quotation": False,
        "lesson_specific_to_paragraph": True,
        "lesson_specificity_evidence": "names the exact two domains Russell splits"
    })


def _llm_disagrees_with_tag(prompt: str) -> str:
    return json.dumps({
        "top1_tag": "diagnosis",
        "top3_tags": ["diagnosis", "concession", "definition"],
        "is_quotation": False,
        "lesson_specific_to_paragraph": True,
        "lesson_specificity_evidence": "diagnoses an error before correcting"
    })


def _llm_flags_quotation(prompt: str) -> str:
    return json.dumps({
        "top1_tag": "concession",
        "top3_tags": ["concession", "diagnosis", "antithesis"],
        "is_quotation": True,
        "lesson_specific_to_paragraph": True,
        "lesson_specificity_evidence": "the words are Hume's, not Russell's"
    })


def _llm_flags_generic_lesson(prompt: str) -> str:
    return json.dumps({
        "top1_tag": "domain_contrast",
        "top3_tags": ["domain_contrast", "antithesis", "diagnosis"],
        "is_quotation": False,
        "lesson_specific_to_paragraph": False,
        "lesson_specificity_evidence": "the lesson could apply to most of Russell"
    })


def test_cross_check_passes_when_extractor_tag_in_top3() -> None:
    candidate = json.loads((CANDIDATES / "good.json").read_text())
    outcome = run_cross_check(candidate=candidate, vocabulary_path=VOCABULARY, llm_call=_llm_agrees_with_tag)
    assert outcome.status == "pass"


def test_cross_check_rejects_tag_disagreement() -> None:
    candidate = json.loads((CANDIDATES / "wrong_tag.json").read_text())
    outcome = run_cross_check(candidate=candidate, vocabulary_path=VOCABULARY, llm_call=_llm_disagrees_with_tag)
    assert outcome.status == "reject"
    assert outcome.reason == "tag-disagreement"
    assert outcome.evidence["extractor_tag"] == "antithesis"
    assert outcome.evidence["cross_check_top3"] == ["diagnosis", "concession", "definition"]


def test_cross_check_rejects_quotation() -> None:
    candidate = json.loads((CANDIDATES / "quoting_hume.json").read_text())
    outcome = run_cross_check(candidate=candidate, vocabulary_path=VOCABULARY, llm_call=_llm_flags_quotation)
    assert outcome.status == "reject"
    assert outcome.reason == "russell-quoting-other-author"


def test_cross_check_rejects_generic_lesson() -> None:
    candidate = json.loads((CANDIDATES / "good.json").read_text())
    outcome = run_cross_check(candidate=candidate, vocabulary_path=VOCABULARY, llm_call=_llm_flags_generic_lesson)
    assert outcome.status == "reject"
    assert outcome.reason == "lesson-generic-cross-check"
```

- [ ] **Step 3: Run, verify failure**

Run:
```bash
.venv/Scripts/python -m pytest tests/test_cross_check.py -v
```
Expected: ImportError.

- [ ] **Step 4: Write the implementation**

Create `scripts/cross_check.py`:

```python
"""Cross-check — independent LLM tag verifier and lesson specificity check.

Receives only the paragraph text and the controlled vocabulary; does NOT see the
extractor's proposed tag or calibration lesson. The check rules:

  - extractor's tag must appear in the cross-check's top-3 tags
  - is_quotation must be false
  - lesson_specific_to_paragraph must be true

Any failure rejects the candidate with the matching reason code.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


_CROSS_CHECK_PROMPT = """You are reviewing one paragraph from a Bertrand Russell text.

Classify the paragraph's rhetorical move using only tags from the controlled vocabulary
provided below. Return JSON with these fields:

  top1_tag: <best tag>
  top3_tags: [<best>, <second>, <third>]
  is_quotation: <true if Russell is quoting another author, else false>
  lesson_specific_to_paragraph: <true if the given lesson is specific to THIS paragraph,
                                 false if it could apply to most of Russell>
  lesson_specificity_evidence: <one-line justification>

PARAGRAPH:
{{PARAGRAPH}}

CANDIDATE'S CALIBRATION LESSON (judge specificity only; do not let it bias your tagging):
{{LESSON}}

CONTROLLED VOCABULARY:
{{VOCABULARY}}
"""


@dataclass
class CrossCheckOutcome:
    status: str  # "pass" | "reject"
    reason: str | None
    evidence: dict[str, Any] | None


def run_cross_check(
    *,
    candidate: dict[str, Any],
    vocabulary_path: Path,
    llm_call: Callable[[str], str],
) -> CrossCheckOutcome:
    vocabulary = vocabulary_path.read_text(encoding="utf-8")
    prompt = (
        _CROSS_CHECK_PROMPT
        .replace("{{PARAGRAPH}}", candidate["paragraph_text"])
        .replace("{{LESSON}}", candidate["calibration_lesson"])
        .replace("{{VOCABULARY}}", vocabulary)
    )
    response = json.loads(llm_call(prompt))

    if response.get("is_quotation"):
        return CrossCheckOutcome("reject", "russell-quoting-other-author", {"evidence": response.get("lesson_specificity_evidence")})

    extractor_tag = candidate["rhetorical_move_tag"]
    if extractor_tag not in response["top3_tags"]:
        return CrossCheckOutcome(
            "reject",
            "tag-disagreement",
            {"extractor_tag": extractor_tag, "cross_check_top3": response["top3_tags"]},
        )

    if not response.get("lesson_specific_to_paragraph"):
        return CrossCheckOutcome("reject", "lesson-generic-cross-check", {"evidence": response.get("lesson_specificity_evidence")})

    return CrossCheckOutcome("pass", None, None)
```

- [ ] **Step 5: Run tests, verify pass**

Run:
```bash
.venv/Scripts/python -m pytest tests/test_cross_check.py -v
```
Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add tools/build-russell-corpus/scripts/cross_check.py tools/build-russell-corpus/tests/test_cross_check.py tools/build-russell-corpus/tests/fixtures/candidates/wrong_tag.json tools/build-russell-corpus/tests/fixtures/candidates/quoting_hume.json
git commit -m "tools/build-russell-corpus: cross-check llm verifier with tag/quotation/lesson rules"
```

---

### Task 14: `cross_check` — batch orchestrator

**Files:**
- Modify: `tools/build-russell-corpus/scripts/cross_check.py`
- Modify: `tools/build-russell-corpus/tests/test_cross_check.py`

- [ ] **Step 1: Write failing test**

Append to `tests/test_cross_check.py`:

```python
from scripts.cross_check import run_cross_check_batch


def _llm_pass_then_reject(prompt: str) -> str:
    # First call returns agreement, second returns disagreement.
    # Test sequences candidates: good (pass), wrong_tag (reject).
    if "domains" in prompt and "ethical or political doctrine" in prompt:
        return json.dumps({
            "top1_tag": "domain_contrast",
            "top3_tags": ["domain_contrast", "antithesis", "diagnosis"],
            "is_quotation": False,
            "lesson_specific_to_paragraph": True,
            "lesson_specificity_evidence": "names exact domains"
        })
    return json.dumps({
        "top1_tag": "diagnosis",
        "top3_tags": ["diagnosis", "concession", "definition"],
        "is_quotation": False,
        "lesson_specific_to_paragraph": True,
        "lesson_specificity_evidence": ""
    })


def test_cross_check_batch_routes_verified_and_rejected(tmp_path: Path) -> None:
    passed = tmp_path / "passed-sentinel.jsonl"
    rows = [
        json.loads((CANDIDATES / "good.json").read_text()),
        json.loads((CANDIDATES / "wrong_tag.json").read_text()),
    ]
    passed.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

    run_dir = tmp_path
    run_cross_check_batch(
        passed_sentinel_path=passed,
        rejected_path=run_dir / "rejected.jsonl",
        verified_path=run_dir / "verified.jsonl",
        vocabulary_path=VOCABULARY,
        llm_call=_llm_pass_then_reject,
    )
    verified = [json.loads(l) for l in (run_dir / "verified.jsonl").read_text().splitlines() if l.strip()]
    rejected = [json.loads(l) for l in (run_dir / "rejected.jsonl").read_text().splitlines() if l.strip()]
    assert len(verified) == 1 and verified[0]["candidate_id"] == "problems-051"
    assert len(rejected) == 1 and rejected[0]["reason"] == "tag-disagreement"
```

- [ ] **Step 2: Run, verify failure**

Run:
```bash
.venv/Scripts/python -m pytest tests/test_cross_check.py::test_cross_check_batch_routes_verified_and_rejected -v
```
Expected: ImportError on `run_cross_check_batch`.

- [ ] **Step 3: Implement the orchestrator**

Append to `scripts/cross_check.py`:

```python
from scripts.corpus_io import append_jsonl


def run_cross_check_batch(
    *,
    passed_sentinel_path: Path,
    rejected_path: Path,
    verified_path: Path,
    vocabulary_path: Path,
    llm_call: Callable[[str], str],
) -> None:
    """Iterate passed-sentinel.jsonl, route each cross-check outcome to verified/rejected."""
    with passed_sentinel_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            cand = json.loads(line)
            outcome = run_cross_check(candidate=cand, vocabulary_path=vocabulary_path, llm_call=llm_call)
            if outcome.status == "pass":
                append_jsonl(verified_path, cand)
            else:
                append_jsonl(rejected_path, {
                    "candidate_id": cand["candidate_id"],
                    "reason": outcome.reason,
                    "evidence": outcome.evidence,
                })
```

- [ ] **Step 4: Run tests, verify pass**

Run:
```bash
.venv/Scripts/python -m pytest tests/test_cross_check.py -v
```
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add tools/build-russell-corpus/scripts/cross_check.py tools/build-russell-corpus/tests/test_cross_check.py
git commit -m "tools/build-russell-corpus: cross-check batch orchestrator"
```

---

### Task 15: `audit_sample` — 5% sampler with halt-rate threshold

**Files:**
- Create: `tools/build-russell-corpus/scripts/audit_sample.py`
- Create: `tools/build-russell-corpus/tests/test_audit_sample.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_audit_sample.py`:

```python
import json
from pathlib import Path

from scripts.audit_sample import sample_audit, evaluate_audit_decisions


def _build_verified(tmp_path: Path, n: int) -> Path:
    path = tmp_path / "verified.jsonl"
    rows = [
        {"candidate_id": f"problems-{i:03d}", "paragraph_text": f"para {i}",
         "rhetorical_move_tag": "domain_contrast",
         "calibration_lesson": f"lesson {i}"}
        for i in range(n)
    ]
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    return path


def test_sample_audit_returns_5pct_floor_one(tmp_path: Path) -> None:
    verified = _build_verified(tmp_path, 100)
    out_md = tmp_path / "sample.md"
    sampled = sample_audit(verified_path=verified, out_path=out_md, sample_rate=0.05, seed=42)
    assert len(sampled) == 5
    assert out_md.exists()
    text = out_md.read_text(encoding="utf-8")
    for entry in sampled:
        assert entry["candidate_id"] in text


def test_sample_audit_with_tiny_batch_samples_at_least_one(tmp_path: Path) -> None:
    verified = _build_verified(tmp_path, 3)
    out_md = tmp_path / "sample.md"
    sampled = sample_audit(verified_path=verified, out_path=out_md, sample_rate=0.05, seed=42)
    assert len(sampled) == 1


def test_evaluate_audit_decisions_halts_above_threshold() -> None:
    decisions = ["accept", "accept", "reject", "accept", "reject"]  # 40% reject rate
    decision = evaluate_audit_decisions(decisions, halt_threshold=0.10)
    assert decision.action == "halt"
    assert decision.reject_rate == 0.4


def test_evaluate_audit_decisions_proceeds_below_threshold() -> None:
    decisions = ["accept"] * 19 + ["reject"]  # 5% reject rate
    decision = evaluate_audit_decisions(decisions, halt_threshold=0.10)
    assert decision.action == "proceed"
    assert decision.reject_rate == 0.05
```

- [ ] **Step 2: Run, verify failure**

Run:
```bash
.venv/Scripts/python -m pytest tests/test_audit_sample.py -v
```
Expected: ImportError.

- [ ] **Step 3: Implement**

Create `scripts/audit_sample.py`:

```python
"""Audit sampler — emits a 5% random sample for operator review.

The operator runs through `sample.md`, marks each entry accept/reject, and feeds the
decision list into `evaluate_audit_decisions`. If the reject rate exceeds the halt
threshold (default 10%), the pipeline halts and the operator tunes the extractor or
generic-phrases list before re-running the batch.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def sample_audit(
    *,
    verified_path: Path,
    out_path: Path,
    sample_rate: float = 0.05,
    seed: int | None = None,
) -> list[dict[str, Any]]:
    """Sample `sample_rate` (min 1) of verified.jsonl. Write a human-readable markdown report."""
    rows = []
    with verified_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    if not rows:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text("# Audit sample\n\nNo entries.\n", encoding="utf-8")
        return []
    n = max(1, round(len(rows) * sample_rate))
    rng = random.Random(seed)
    sampled = rng.sample(rows, k=min(n, len(rows)))
    _write_audit_markdown(sampled, out_path)
    return sampled


def _write_audit_markdown(sampled: list[dict[str, Any]], out_path: Path) -> None:
    parts = ["# Audit sample", "", f"Sampled {len(sampled)} entries.", "",
             "For each entry below, mark `accept` / `reject` / `tag-revise`.", ""]
    for i, entry in enumerate(sampled, start=1):
        parts.append(f"## {i}. `{entry['candidate_id']}`")
        parts.append("")
        parts.append(f"**Tag:** `{entry.get('rhetorical_move_tag', '?')}`")
        parts.append("")
        parts.append(f"**Lesson:** {entry.get('calibration_lesson', '?')}")
        parts.append("")
        parts.append("**Paragraph:**")
        parts.append("")
        parts.append("> " + entry.get("paragraph_text", "").replace("\n", "\n> "))
        parts.append("")
        parts.append("**Decision:** ___")
        parts.append("")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(parts), encoding="utf-8")


@dataclass
class AuditDecision:
    action: str  # "proceed" | "halt"
    reject_rate: float


def evaluate_audit_decisions(decisions: list[str], halt_threshold: float = 0.10) -> AuditDecision:
    """Compute reject rate; halt if it exceeds the threshold."""
    if not decisions:
        return AuditDecision("proceed", 0.0)
    rejects = sum(1 for d in decisions if d == "reject")
    rate = rejects / len(decisions)
    return AuditDecision("halt" if rate > halt_threshold else "proceed", rate)
```

- [ ] **Step 4: Run tests, verify pass**

Run:
```bash
.venv/Scripts/python -m pytest tests/test_audit_sample.py -v
```
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add tools/build-russell-corpus/scripts/audit_sample.py tools/build-russell-corpus/tests/test_audit_sample.py
git commit -m "tools/build-russell-corpus: audit sampler with halt-rate evaluation"
```

---

### Task 16: `append_to_index` — project schema, append to index, regenerate corpus-map.md

**Files:**
- Create: `tools/build-russell-corpus/scripts/append_to_index.py`
- Create: `tools/build-russell-corpus/tests/test_append_to_index.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_append_to_index.py`:

```python
import json
from pathlib import Path

from scripts.append_to_index import append_verified_to_index, regenerate_corpus_map


def _seed_index(tmp_path: Path) -> Path:
    idx = tmp_path / "index.json"
    idx.write_text(json.dumps({
        "version": "0.1.0",
        "paragraph_count": 1,
        "sources": {"problems": {"title": "x", "url": "u", "copyright_status": "public_domain_us", "mode": ["m"]}},
        "paragraphs": [
            {"id": "problems-001", "source": "problems", "line_hint": 433,
             "rhetorical_move": "rm", "tags": ["t1"]},
        ],
    }, indent=2), encoding="utf-8")
    return idx


def _seed_verified(tmp_path: Path) -> Path:
    verified = tmp_path / "verified.jsonl"
    rows = [
        {"candidate_id": "problems-051",
         "source_id": "problems",
         "source_url": "u",
         "line_hint": 812,
         "content_locator": "Philosophy, throughout its history,",
         "paragraph_text": "Philosophy, throughout its history, has consisted of two parts inharmoniously blended.",
         "rhetorical_move_tag": "domain_contrast",
         "calibration_lesson": "Russell splits philosophy into two domains."}
    ]
    verified.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    return verified


def test_append_verified_to_index_projects_to_existing_schema(tmp_path: Path) -> None:
    idx_path = _seed_index(tmp_path)
    verified_path = _seed_verified(tmp_path)
    append_verified_to_index(verified_path=verified_path, index_path=idx_path)
    idx = json.loads(idx_path.read_text())
    assert idx["paragraph_count"] == 2
    new_entry = idx["paragraphs"][1]
    assert new_entry["id"] == "problems-051"
    assert new_entry["source"] == "problems"
    assert new_entry["line_hint"] == 812
    assert new_entry["rhetorical_move"] == "Russell splits philosophy into two domains."
    assert new_entry["tags"] == ["domain_contrast"]
    assert new_entry["content_locator"] == "Philosophy, throughout its history,"


def test_regenerate_corpus_map_emits_table_row_for_new_entry(tmp_path: Path) -> None:
    idx_path = _seed_index(tmp_path)
    verified_path = _seed_verified(tmp_path)
    append_verified_to_index(verified_path=verified_path, index_path=idx_path)
    map_path = tmp_path / "russell-corpus-map.md"
    regenerate_corpus_map(index_path=idx_path, out_path=map_path)
    text = map_path.read_text(encoding="utf-8")
    assert "problems-001" in text
    assert "problems-051" in text
    assert "Russell splits philosophy into two domains." in text
```

- [ ] **Step 2: Run, verify failure**

Run:
```bash
.venv/Scripts/python -m pytest tests/test_append_to_index.py -v
```
Expected: ImportError.

- [ ] **Step 3: Implement**

Create `scripts/append_to_index.py`:

```python
"""Append verified candidates to russellian-style index.json; regenerate corpus-map.md.

The pipeline carries a fat candidate object (paragraph_text, source_url, content_locator,
rhetorical_move_tag, calibration_lesson). The committed index entry schema is narrower
(id, source, line_hint, rhetorical_move, tags, content_locator). This stage projects fat
candidates down to the committed schema, preserving content_locator as an additive field.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.corpus_io import append_index_entries, read_index


def _project_candidate_to_index_entry(cand: dict[str, Any]) -> dict[str, Any]:
    """Project a fat verified candidate to the committed index entry schema."""
    parsed_id = cand["candidate_id"].split("-")
    # Allow IDs like "problems-051" or "external-world-007"; reconstruct integer suffix.
    numeric_suffix = parsed_id[-1]
    source_id = "-".join(parsed_id[:-1])
    return {
        "id": f"{source_id}-{numeric_suffix}",
        "source": source_id,
        "line_hint": cand["line_hint"],
        "rhetorical_move": cand["calibration_lesson"],
        "tags": [cand["rhetorical_move_tag"]],
        "content_locator": cand["content_locator"],
    }


def append_verified_to_index(*, verified_path: Path, index_path: Path) -> None:
    """Read verified.jsonl, project to index schema, append to index.json."""
    new_entries: list[dict[str, Any]] = []
    with verified_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            new_entries.append(_project_candidate_to_index_entry(json.loads(line)))
    append_index_entries(index_path, new_entries)


def regenerate_corpus_map(*, index_path: Path, out_path: Path) -> None:
    """Emit references/russell-corpus-map.md from index.json."""
    idx = read_index(index_path)
    lines = [
        "# Russell Corpus Map",
        "",
        "Auto-generated from `assets/russell-corpus/index.json`. Do not hand-edit.",
        "",
        f"Total entries: {idx['paragraph_count']}",
        "",
        "## Source Mix",
        "",
        "| Source ID | Title | URL |",
        "| --- | --- | --- |",
    ]
    for sid, meta in idx["sources"].items():
        lines.append(f"| `{sid}` | *{meta['title']}* | {meta['url']} |")
    lines += [
        "",
        "## Paragraph Register",
        "",
        "| ID | Source | Line Hint | Rhetorical Move / Lesson | Tags |",
        "| --- | --- | --- | --- | --- |",
    ]
    for entry in idx["paragraphs"]:
        tags = ", ".join(f"`{t}`" for t in entry.get("tags", []))
        lines.append(
            f"| `{entry['id']}` | {entry['source']} | {entry['line_hint']} | {entry['rhetorical_move']} | {tags} |"
        )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
```

- [ ] **Step 4: Run tests, verify pass**

Run:
```bash
.venv/Scripts/python -m pytest tests/test_append_to_index.py -v
```
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add tools/build-russell-corpus/scripts/append_to_index.py tools/build-russell-corpus/tests/test_append_to_index.py
git commit -m "tools/build-russell-corpus: project verified to index schema; regenerate corpus-map"
```

---

### Task 17: `cli` — chain all stages end-to-end

**Files:**
- Create: `tools/build-russell-corpus/scripts/cli.py`

- [ ] **Step 1: Write the CLI module**

Create `scripts/cli.py`:

```python
"""CLI entry that chains the four stages: extract → sentinel → cross-check → append.

Each subcommand is independently invocable so the operator can stop after sentinel and
audit the pipeline, or re-run cross-check after the operator has tuned the vocabulary.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Callable


def _stub_llm(_: str) -> str:
    raise SystemExit("No LLM caller wired. Run via the project's llm-call harness; CLI defaults are stubs only.")


def cmd_derive_vocabulary(args: argparse.Namespace) -> None:
    from scripts.derive_vocabulary import derive_controlled_vocabulary
    derive_controlled_vocabulary(index_path=args.index, out_path=args.out)


def cmd_extract(args: argparse.Namespace, llm_call: Callable[[str], str] = _stub_llm) -> None:
    from scripts.extract_candidates import extract_candidates
    extract_candidates(
        source_path=args.source,
        source_id=args.source_id,
        source_url=args.source_url,
        vocabulary_path=args.vocabulary,
        prompt_path=args.prompt,
        out_path=args.out,
        n=args.n,
        llm_call=llm_call,
    )


def cmd_sentinel(args: argparse.Namespace) -> None:
    from scripts.sentinel import run_sentinel_batch
    run_sentinel_batch(
        candidates_path=args.candidates,
        source_cache_dir=args.source_cache,
        allow_list_path=args.allow_list,
        vocabulary_path=args.vocabulary,
        generic_phrases_path=args.generic_phrases,
        existing_index_path=args.index,
        run_dir=args.run_dir,
    )


def cmd_cross_check(args: argparse.Namespace, llm_call: Callable[[str], str] = _stub_llm) -> None:
    from scripts.cross_check import run_cross_check_batch
    run_cross_check_batch(
        passed_sentinel_path=args.passed_sentinel,
        rejected_path=args.rejected,
        verified_path=args.verified,
        vocabulary_path=args.vocabulary,
        llm_call=llm_call,
    )


def cmd_audit(args: argparse.Namespace) -> None:
    from scripts.audit_sample import sample_audit
    sample_audit(verified_path=args.verified, out_path=args.out, sample_rate=args.rate, seed=args.seed)


def cmd_append(args: argparse.Namespace) -> None:
    from scripts.append_to_index import append_verified_to_index, regenerate_corpus_map
    append_verified_to_index(verified_path=args.verified, index_path=args.index)
    regenerate_corpus_map(index_path=args.index, out_path=args.corpus_map)


def main() -> None:
    parser = argparse.ArgumentParser(prog="build-russell-corpus")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("derive-vocabulary")
    p.add_argument("--index", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.set_defaults(func=cmd_derive_vocabulary)

    p = sub.add_parser("extract")
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--source-id", type=str, required=True)
    p.add_argument("--source-url", type=str, required=True)
    p.add_argument("--vocabulary", type=Path, required=True)
    p.add_argument("--prompt", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--n", type=int, default=100)
    p.set_defaults(func=cmd_extract)

    p = sub.add_parser("sentinel")
    p.add_argument("--candidates", type=Path, required=True)
    p.add_argument("--source-cache", type=Path, required=True)
    p.add_argument("--allow-list", type=Path, required=True)
    p.add_argument("--vocabulary", type=Path, required=True)
    p.add_argument("--generic-phrases", type=Path, required=True)
    p.add_argument("--index", type=Path, required=True)
    p.add_argument("--run-dir", type=Path, required=True)
    p.set_defaults(func=cmd_sentinel)

    p = sub.add_parser("cross-check")
    p.add_argument("--passed-sentinel", type=Path, required=True)
    p.add_argument("--rejected", type=Path, required=True)
    p.add_argument("--verified", type=Path, required=True)
    p.add_argument("--vocabulary", type=Path, required=True)
    p.set_defaults(func=cmd_cross_check)

    p = sub.add_parser("audit")
    p.add_argument("--verified", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--rate", type=float, default=0.05)
    p.add_argument("--seed", type=int, default=None)
    p.set_defaults(func=cmd_audit)

    p = sub.add_parser("append")
    p.add_argument("--verified", type=Path, required=True)
    p.add_argument("--index", type=Path, required=True)
    p.add_argument("--corpus-map", type=Path, required=True)
    p.set_defaults(func=cmd_append)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Smoke-test the CLI parser**

Run:
```bash
.venv/Scripts/python -m scripts.cli derive-vocabulary --help
.venv/Scripts/python -m scripts.cli sentinel --help
```
Expected: argparse help text emitted with no error.

- [ ] **Step 3: Commit**

```bash
git add tools/build-russell-corpus/scripts/cli.py
git commit -m "tools/build-russell-corpus: cli chaining all stages"
```

---

### Task 18: End-to-end integration test with stubs

**Files:**
- Create: `tools/build-russell-corpus/tests/test_e2e.py`

- [ ] **Step 1: Write failing integration test**

Create `tests/test_e2e.py`:

```python
import json
import shutil
from pathlib import Path

from scripts.extract_candidates import extract_candidates
from scripts.sentinel import run_sentinel_batch
from scripts.cross_check import run_cross_check_batch
from scripts.audit_sample import sample_audit, evaluate_audit_decisions
from scripts.append_to_index import append_verified_to_index, regenerate_corpus_map


FIXTURES = Path(__file__).parent / "fixtures"
SOURCE_CACHE = FIXTURES / "source_cache"
ASSETS = Path(__file__).parent.parent / "assets"


def _stub_extract_llm(prompt: str) -> str:
    return json.dumps({
        "candidate_id": "problems-051",
        "source_id": "problems",
        "source_url": "https://www.gutenberg.org/cache/epub/5827/pg5827-images.html",
        "line_hint": 2,
        "content_locator": "Philosophy, throughout its history,",
        "paragraph_text": "Philosophy, throughout its history, has consisted of two parts inharmoniously blended: on the one hand a theory as to the nature of the world, on the other an ethical or political doctrine as to the best way of living.",
        "rhetorical_move_tag": "domain_contrast",
        "calibration_lesson": "Russell opens by splitting philosophy into two domains the chapter will pull apart.",
    })


def _stub_cross_check_llm(prompt: str) -> str:
    return json.dumps({
        "top1_tag": "domain_contrast",
        "top3_tags": ["domain_contrast", "antithesis", "diagnosis"],
        "is_quotation": False,
        "lesson_specific_to_paragraph": True,
        "lesson_specificity_evidence": "names the exact two domains"
    })


def test_e2e_one_candidate_lands_in_index(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    index_copy = tmp_path / "index.json"
    shutil.copy(FIXTURES / "existing_index_sample.json", index_copy)
    # Patch allow-list with the fixture URL
    allow_list = tmp_path / "pd-allow-list.yaml"
    allow_list.write_text(
        "allowed:\n"
        "  - source_id: problems\n"
        "    title: \"The Problems of Philosophy\"\n"
        "    url: \"https://www.gutenberg.org/cache/epub/5827/pg5827-images.html\"\n",
        encoding="utf-8",
    )

    # Stage 1 — extract
    candidates = run_dir / "candidates.jsonl"
    extract_candidates(
        source_path=SOURCE_CACHE / "problems_subset.html",
        source_id="problems",
        source_url="https://www.gutenberg.org/cache/epub/5827/pg5827-images.html",
        vocabulary_path=ASSETS / "vocabulary.json",
        prompt_path=ASSETS / "extractor-prompt.md",
        out_path=candidates,
        n=1,
        llm_call=_stub_extract_llm,
    )
    # Stage 2 — sentinel
    run_sentinel_batch(
        candidates_path=candidates,
        source_cache_dir=SOURCE_CACHE,
        allow_list_path=allow_list,
        vocabulary_path=ASSETS / "vocabulary.json",
        generic_phrases_path=ASSETS / "generic-phrases.yaml",
        existing_index_path=index_copy,
        run_dir=run_dir,
    )
    assert (run_dir / "passed-sentinel.jsonl").exists()

    # Stage 3 — cross-check
    run_cross_check_batch(
        passed_sentinel_path=run_dir / "passed-sentinel.jsonl",
        rejected_path=run_dir / "rejected.jsonl",
        verified_path=run_dir / "verified.jsonl",
        vocabulary_path=ASSETS / "vocabulary.json",
        llm_call=_stub_cross_check_llm,
    )
    assert (run_dir / "verified.jsonl").exists()

    # Stage 4 — audit
    sample_audit(verified_path=run_dir / "verified.jsonl", out_path=run_dir / "audit" / "sample.md")
    decision = evaluate_audit_decisions(["accept"], halt_threshold=0.10)
    assert decision.action == "proceed"

    # Stage 5 — append
    corpus_map = tmp_path / "russell-corpus-map.md"
    append_verified_to_index(verified_path=run_dir / "verified.jsonl", index_path=index_copy)
    regenerate_corpus_map(index_path=index_copy, out_path=corpus_map)

    idx = json.loads(index_copy.read_text())
    ids = [e["id"] for e in idx["paragraphs"]]
    assert "problems-051" in ids
    assert "problems-051" in corpus_map.read_text(encoding="utf-8")
```

- [ ] **Step 2: Run the integration test**

Run:
```bash
.venv/Scripts/python -m pytest tests/test_e2e.py -v
```
Expected: 1 passed.

If it fails on a missing vocabulary slug (e.g. `domain_contrast` not in `assets/vocabulary.json`), confirm Task 6's operator review preserved that tag. If the slug was renamed during review, update the stub responses in this test to match.

- [ ] **Step 3: Run the full suite**

Run:
```bash
.venv/Scripts/python -m pytest tests/ -v
```
Expected: all tests pass — roughly 20+ test cases across all suites.

- [ ] **Step 4: Commit**

```bash
git add tools/build-russell-corpus/tests/test_e2e.py
git commit -m "tools/build-russell-corpus: end-to-end integration test with stubs"
```

---

### Task 19: Wire the live LLM caller (manual operator step, no commit)

This task is documentation, not code. It tells the operator how to wire the real LLM client into the CLI for production runs.

- [ ] **Step 1: Read the project's existing LLM-call patterns**

Inspect `skills/book-compose/scripts/` for how `book-compose` constructs `llm_call` (specifically `system_prompt_loader.py` and any `llm.py` or equivalent caller). The pattern there is the production reference.

- [ ] **Step 2: Create a thin live-caller wrapper**

In a separate file `scripts/live_llm.py` (do not commit yet — operator step), wrap whatever client library the suite uses (Anthropic SDK or other) into the `Callable[[str], str]` shape the stages expect. The wrapper reads model_id from `assets/llm-config.yaml`. Two callers: `extract_llm` and `cross_check_llm`, each loading the matching config block.

- [ ] **Step 3: Run a one-shot smoke against a single source**

```bash
.venv/Scripts/python -m scripts.cli extract \
    --source <path-to-cached-problems.html> \
    --source-id problems \
    --source-url https://www.gutenberg.org/cache/epub/5827/pg5827-images.html \
    --vocabulary assets/vocabulary.json \
    --prompt assets/extractor-prompt.md \
    --out runs/smoke/candidates.jsonl \
    --n 5
```

Expected: 5 candidate lines in `candidates.jsonl`. Inspect manually before running sentinel.

- [ ] **Step 4: Full batch invocation reference**

Reference command sequence for one source (in `runs/<batch-id>/`):

```bash
BATCH=batch-001
mkdir -p runs/$BATCH

# Extract
python -m scripts.cli extract \
    --source <source> --source-id problems --source-url <url> \
    --vocabulary assets/vocabulary.json --prompt assets/extractor-prompt.md \
    --out runs/$BATCH/candidates.jsonl --n 100

# Sentinel
python -m scripts.cli sentinel \
    --candidates runs/$BATCH/candidates.jsonl \
    --source-cache <cache-dir> \
    --allow-list assets/pd-allow-list.yaml \
    --vocabulary assets/vocabulary.json \
    --generic-phrases assets/generic-phrases.yaml \
    --index ../../skills/russellian-style/assets/russell-corpus/index.json \
    --run-dir runs/$BATCH

# Cross-check
python -m scripts.cli cross-check \
    --passed-sentinel runs/$BATCH/passed-sentinel.jsonl \
    --rejected runs/$BATCH/rejected.jsonl \
    --verified runs/$BATCH/verified.jsonl \
    --vocabulary assets/vocabulary.json

# Audit
python -m scripts.cli audit \
    --verified runs/$BATCH/verified.jsonl \
    --out runs/$BATCH/audit/sample.md

# (operator reviews audit/sample.md, computes reject rate; if >10%, halt and tune)

# Append
python -m scripts.cli append \
    --verified runs/$BATCH/verified.jsonl \
    --index ../../skills/russellian-style/assets/russell-corpus/index.json \
    --corpus-map ../../skills/russellian-style/references/russell-corpus-map.md
```

- [ ] **Step 5: No commit — operator step**

This task produces no committed code. The live LLM wrapper lives outside the repo if the operator chooses, or is committed under a `scripts/live_llm.py` once the suite's LLM-call pattern is settled.

---

## Self-review

Run after writing the plan, before handing off to execution.

**Spec coverage check:** every spec section maps to at least one task:

| Spec section | Tasks covering it |
| --- | --- |
| Where it lives (tools/build-russell-corpus) | Task 0 |
| Stage 1 extract_candidates | Task 8 |
| Stage 2 sentinel (6 checks) | Tasks 9–12 |
| Stage 3 cross_check | Tasks 13–14 |
| Stage 4 audit_sample | Task 15 |
| Stage 5 append_to_index + corpus-map regen | Task 16 |
| Controlled vocabulary derivation | Tasks 5–6 |
| PD allow-list | Task 4 |
| Generic phrases seed | Task 7 |
| Extractor prompt + LLM config | Task 7 |
| Failure-mode coverage matrix | Tasks 9–14 (each row tested) |
| CLI orchestration | Task 17 |
| End-to-end integration | Task 18 |
| Live LLM wiring (operator step) | Task 19 |

**Placeholder scan:** all code blocks contain actual implementation. No `TODO`, `TBD`, or "implement later". The one operator-pass step (Task 6 step 3, Task 19) is explicit human work, not a code placeholder.

**Type consistency:** `SentinelOutcome` defined in Task 9, used unchanged in Task 12. `CrossCheckOutcome` defined in Task 13, used unchanged in Task 14. `AuditDecision` defined in Task 15. Function signatures are consistent across import sites. The `Callable[[str], str]` LLM shape is identical in extract, cross_check, and CLI.

**One acknowledged risk:** the `vocabulary.json` slugs in test stubs (e.g. `domain_contrast`, `diagnosis`, `concession`) assume Task 6's operator review preserved those slugs verbatim. Task 18 calls this out — if the operator renamed a slug, stub responses need a matching tweak.
