# Russell-Delta Scorer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a deterministic, advisory Russell-similarity score (Cosine Delta over most-frequent-word frequencies) to the russellian-style skill, built from a committed reference profile of public-domain Russell prose.

**Architecture:** Three pure-Python modules under `skills/russellian-style/scripts/`: `delta_math.py` (tokenize + frequency + z-score + cosine-delta primitives, shared), `build_delta_profile.py` (network-free builder consuming local cleaned texts → `assets/russell-delta-profile.json`), `score_russell_delta.py` (loads the profile, scores a markdown file, prints JSON). One advisory `russell_delta` block added to `style_pass_report.generate_report_dict()`. Source texts are fetched separately via scrapling-fetch.

**Tech Stack:** Python 3.11+, stdlib only (`re`, `math`, `collections.Counter`, `statistics`, `json`). pytest. No spaCy, no network in the modules or tests.

**Spec:** `openspec/changes/add-russell-delta-scorer/` (REQ-DELTA-001..009), `docs/specs/2026-05-27-russell-delta-scorer-design.md`.

> **Post-implementation note:** the code blocks below show the original cosine-to-segments
> metric, which validation showed did not discriminate (all formal English scored ~1.0).
> The shipped metric is classic Burrows's Delta (mean absolute z-score to the author
> profile) with a three-band verdict. The committed modules and the design doc are the
> source of truth; these blocks are kept as the original plan of record.

---

## File structure

- Create `skills/russellian-style/scripts/delta_math.py` — stylometric primitives (shared by builder + scorer).
- Create `skills/russellian-style/scripts/build_delta_profile.py` — profile builder (network-free).
- Create `skills/russellian-style/scripts/score_russell_delta.py` — scorer + CLI.
- Create `skills/russellian-style/assets/russell-delta-profile.json` — committed profile (built in Task 3).
- Modify `skills/russellian-style/scripts/style_pass_report.py` — add `russell_delta` block to `generate_report_dict`.
- Create `skills/russellian-style/tests/test_delta_math.py`, `tests/test_build_delta_profile.py`, `tests/test_score_russell_delta.py`.

Run tests from the skill root (matches existing tests):
`cd skills/russellian-style && .venv/Scripts/python.exe -m pytest tests/<file> -v` (Windows).

---

### Task 1: delta_math primitives

**Files:**
- Create: `skills/russellian-style/scripts/delta_math.py`
- Test: `skills/russellian-style/tests/test_delta_math.py`

- [ ] **Step 1: Write the failing test**

```python
"""Cites REQ-DELTA-003."""
import pytest
pytestmark = pytest.mark.windows_canary
from scripts.delta_math import tokenize, relative_frequencies, cosine, cosine_delta, zscore


def test_tokenize_lowercases_and_splits():
    assert tokenize("The CAT's hat, and 3 dogs!") == ["the", "cat's", "hat", "and", "dogs"]

def test_relative_frequencies_align_to_mfw():
    toks = ["the", "of", "the", "cat"]
    assert relative_frequencies(toks, ["the", "of", "dog"]) == [0.5, 0.25, 0.0]

def test_relative_frequencies_empty_is_zeros():
    assert relative_frequencies([], ["the", "of"]) == [0.0, 0.0]

def test_cosine_orthogonal_is_zero():
    assert cosine([1.0, 0.0], [0.0, 1.0]) == 0.0

def test_cosine_parallel_is_one():
    assert cosine([1.0, 2.0, 3.0], [2.0, 4.0, 6.0]) == pytest.approx(1.0)

def test_cosine_delta_is_one_minus_cosine():
    assert cosine_delta([1.0, 0.0], [0.0, 1.0]) == pytest.approx(1.0)
    assert cosine_delta([1.0, 1.0], [1.0, 1.0]) == pytest.approx(0.0)

def test_cosine_zero_vector_returns_zero():
    assert cosine([0.0, 0.0], [1.0, 1.0]) == 0.0

def test_zscore_uses_mean_and_stdev_with_zero_guard():
    assert zscore([0.6, 0.1], [0.5, 0.1], [0.1, 0.0]) == [pytest.approx(1.0), 0.0]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd skills/russellian-style && .venv/Scripts/python.exe -m pytest tests/test_delta_math.py -v`
Expected: FAIL (module does not exist).

- [ ] **Step 3: Write minimal implementation**

```python
"""Stylometric primitives for Russell-Delta (Cosine Delta over MFW frequencies)."""
from __future__ import annotations

import math
import re
from collections import Counter

_TOKEN_RE = re.compile(r"[a-z']+")


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def relative_frequencies(tokens: list[str], mfw: list[str]) -> list[float]:
    total = len(tokens)
    if total == 0:
        return [0.0] * len(mfw)
    counts = Counter(tokens)
    return [counts.get(w, 0) / total for w in mfw]


def zscore(freqs: list[float], mean: list[float], stdev: list[float]) -> list[float]:
    return [(f - m) / s if s > 0 else 0.0 for f, m, s in zip(freqs, mean, stdev)]


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def cosine_delta(a: list[float], b: list[float]) -> float:
    return 1.0 - cosine(a, b)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd skills/russellian-style && .venv/Scripts/python.exe -m pytest tests/test_delta_math.py -v`
Expected: PASS (8 tests).

- [ ] **Step 5: Commit**

```bash
git -C C:\russellian-book-suite add skills/russellian-style/scripts/delta_math.py skills/russellian-style/tests/test_delta_math.py
git -C C:\russellian-book-suite commit -m "Add delta_math stylometric primitives"
```

---

### Task 2: profile builder

**Files:**
- Create: `skills/russellian-style/scripts/build_delta_profile.py`
- Test: `skills/russellian-style/tests/test_build_delta_profile.py`

- [ ] **Step 1: Write the failing test**

```python
"""Cites REQ-DELTA-001, REQ-DELTA-002, REQ-DELTA-006."""
import pytest
pytestmark = pytest.mark.windows_canary
from scripts.build_delta_profile import strip_gutenberg, segment_tokens, build_profile


def test_strip_gutenberg_removes_boilerplate():
    raw = "header junk\n*** START OF THE PROJECT ***\nreal body here\n*** END OF THE PROJECT ***\nfooter"
    assert strip_gutenberg(raw).strip() == "real body here"

def test_segment_tokens_drops_short_tail():
    toks = list("a" * 0) + ["w"] * 25
    segs = segment_tokens(["w"] * 25, size=10, min_size=10)
    assert [len(s) for s in segs] == [10, 10]   # trailing 5 dropped

def test_build_profile_shapes_and_determinism():
    texts = {
        "a": " ".join(["the of and the of cat"] * 200),   # >=2 segments at small size
        "b": " ".join(["the and of dog the of"] * 200),
    }
    p = build_profile(texts, n_features=4, segment_words=50, min_segment=20)
    assert p["method"] == "cosine-delta"
    assert p["n_features"] == 4
    assert len(p["mfw"]) == 4
    assert p["mfw"][0] == "the"                      # most frequent first
    assert len(p["mean"]) == 4 and len(p["stdev"]) == 4
    assert len(p["segments_z"]) == p["n_segments"]
    assert all(len(z) == 4 for z in p["segments_z"])
    assert set(p["internal_delta"]) >= {"p10", "p50", "p90", "max", "mean", "count"}
    assert "source prose" not in str(p).lower() or "no source prose" in p["source_policy"].lower()
    # determinism
    p2 = build_profile(texts, n_features=4, segment_words=50, min_segment=20)
    assert p == {k: v for k, v in p2.items() if k != "built_at"} | {"built_at": p["built_at"]} or \
        {k: v for k, v in p.items() if k != "built_at"} == {k: v for k, v in p2.items() if k != "built_at"}

def test_build_profile_needs_two_segments():
    with pytest.raises(ValueError):
        build_profile({"a": "the of and"}, n_features=2, segment_words=50, min_segment=20)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd skills/russellian-style && .venv/Scripts/python.exe -m pytest tests/test_build_delta_profile.py -v`
Expected: FAIL (module does not exist).

- [ ] **Step 3: Write minimal implementation**

```python
"""Build the Russell-Delta reference profile from local cleaned text files.

Network-free. Fetching of public-domain sources is a separate step via
scrapling-fetch; this module only computes statistics.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean as _mean, pstdev

from scripts.delta_math import tokenize, relative_frequencies, zscore, cosine_delta

_START_RE = re.compile(r"\*\*\*\s*START OF.*?\*\*\*", re.IGNORECASE | re.DOTALL)
_END_RE = re.compile(r"\*\*\*\s*END OF", re.IGNORECASE)


def strip_gutenberg(text: str) -> str:
    m = _START_RE.search(text)
    if m:
        text = text[m.end():]
    m = _END_RE.search(text)
    if m:
        text = text[:m.start()]
    return text


def segment_tokens(tokens: list[str], size: int, min_size: int) -> list[list[str]]:
    segs = [tokens[i:i + size] for i in range(0, len(tokens), size)]
    return [s for s in segs if len(s) >= min_size]


def _percentile(sorted_vals: list[float], p: float) -> float:
    if not sorted_vals:
        return 0.0
    k = min(len(sorted_vals) - 1, int(round(p * (len(sorted_vals) - 1))))
    return round(sorted_vals[k], 6)


def build_profile(texts: dict[str, str], n_features: int = 300,
                  segment_words: int = 2500, min_segment: int = 1000) -> dict:
    segments: list[list[str]] = []
    for raw in texts.values():
        toks = tokenize(strip_gutenberg(raw))
        segments.extend(segment_tokens(toks, segment_words, min_segment))
    if len(segments) < 2:
        raise ValueError("need >= 2 segments to build a profile")

    total: Counter[str] = Counter()
    for seg in segments:
        total.update(seg)
    mfw = [w for w, _ in total.most_common(n_features)]

    seg_freqs = [relative_frequencies(seg, mfw) for seg in segments]
    mean = [_mean(col) for col in zip(*seg_freqs)]
    stdev = [pstdev(col) for col in zip(*seg_freqs)]
    segments_z = [zscore(f, mean, stdev) for f in seg_freqs]

    deltas: list[float] = []
    for i in range(len(segments_z)):
        for j in range(i + 1, len(segments_z)):
            deltas.append(cosine_delta(segments_z[i], segments_z[j]))
    deltas.sort()
    internal = {
        "p10": _percentile(deltas, 0.10),
        "p50": _percentile(deltas, 0.50),
        "p90": _percentile(deltas, 0.90),
        "max": round(deltas[-1], 6) if deltas else 0.0,
        "mean": round(_mean(deltas), 6) if deltas else 0.0,
        "count": len(deltas),
    }

    return {
        "version": "0.1.0",
        "method": "cosine-delta",
        "n_features": len(mfw),
        "segment_words": segment_words,
        "tokenizer": "lowercase tokens matching [a-z']+",
        "source_policy": "statistics computed from public-domain Project Gutenberg texts; no source prose stored",
        "reference_ids": sorted(texts.keys()),
        "n_segments": len(segments),
        "mfw": mfw,
        "mean": [round(x, 9) for x in mean],
        "stdev": [round(x, 9) for x in stdev],
        "segments_z": [[round(x, 6) for x in z] for z in segments_z],
        "internal_delta": internal,
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def build_from_dir(src_dir: Path, out_path: Path, **kw) -> dict:
    texts = {p.stem: p.read_text(encoding="utf-8", errors="replace")
             for p in sorted(Path(src_dir).glob("*.txt"))}
    profile = build_profile(texts, **kw)
    Path(out_path).write_text(json.dumps(profile, indent=1), encoding="utf-8")
    return profile


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print("usage: build_delta_profile.py <src_dir> <out.json>", file=sys.stderr)
        return 2
    p = build_from_dir(Path(argv[1]), Path(argv[2]))
    print(f"profile: {p['n_segments']} segments, {p['n_features']} features, "
          f"internal p50={p['internal_delta']['p50']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd skills/russellian-style && .venv/Scripts/python.exe -m pytest tests/test_build_delta_profile.py -v`
Expected: PASS. (If `test_build_profile_shapes_and_determinism`'s determinism assertion is awkward, simplify it to compare the two profiles with `built_at` removed.)

- [ ] **Step 5: Commit**

```bash
git -C C:\russellian-book-suite add skills/russellian-style/scripts/build_delta_profile.py skills/russellian-style/tests/test_build_delta_profile.py
git -C C:\russellian-book-suite commit -m "Add Russell-Delta profile builder"
```

---

### Task 3: fetch sources and build the committed profile

**Files:**
- Create (temporary, not committed): a fetch script under `C:\Users\charl\AppData\Local\Temp\delta_fetch.py`
- Create: `skills/russellian-style/assets/russell-delta-profile.json`

- [ ] **Step 1: Fetch the 19 works via scrapling-fetch**

Write `C:\Users\charl\AppData\Local\Temp\delta_fetch.py`:

```python
import os, re, html
from scripts.fetch import fetch          # run with PYTHONPATH=<scrapling-fetch skill root>
from scripts.exceptions import FetchFailed

IDS = [5827, 25447, 37090, 2529, 4776, 44932, 13940, 690, 77894, 41654,
       17350, 72981, 67104, 73782, 70302, 55610, 66225, 52091, 77427]
OUT = r"C:\Users\charl\AppData\Local\Temp\russell_delta_src"
os.makedirs(OUT, exist_ok=True)

def strip_html(s: str) -> str:
    s = re.sub(r"(?is)<(script|style).*?</\1>", " ", s)
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    return html.unescape(s)

for eid in IDS:
    body = None
    for url in (f"https://www.gutenberg.org/cache/epub/{eid}/pg{eid}.txt",
                f"https://www.gutenberg.org/files/{eid}/{eid}-0.txt",
                f"https://www.gutenberg.org/cache/epub/{eid}/pg{eid}-images.html"):
        try:
            p = fetch(url, timeout_s=60)
            if p.status == 200 and len(p.html) > 30000:
                body = strip_html(p.html) if url.endswith(".html") else p.html
                break
        except FetchFailed:
            continue
    if body:
        open(os.path.join(OUT, f"{eid}.txt"), "w", encoding="utf-8").write(body)
        print("OK", eid, len(body))
    else:
        print("MISS", eid)
```

Run:
```bash
cd /c/russellian-book-suite/skills/scrapling-fetch
PYTHONPATH="C:\russellian-book-suite\skills\scrapling-fetch" python /tmp/delta_fetch.py
```
Expected: `OK <id> <bytes>` for ~17-19 ids. Note any `MISS` and retry with an alternate path; proceed if >= 15 succeed (enough text for a stable profile).

- [ ] **Step 2: Build the committed profile**

```bash
cd /c/russellian-book-suite/skills/russellian-style
.venv/Scripts/python.exe -m scripts.build_delta_profile \
  "C:\Users\charl\AppData\Local\Temp\russell_delta_src" \
  assets/russell-delta-profile.json
```
Expected: prints `profile: <N> segments, 300 features, internal p50=<float>`. Confirm the file exists and `n_segments` is in the low hundreds.

- [ ] **Step 3: Sanity-check the asset has no prose**

Run: `cd /c/russellian-book-suite && .venv/Scripts/python.exe -c "import json;d=json.load(open(r'skills/russellian-style/assets/russell-delta-profile.json'));print(d['n_segments'],d['n_features'],list(d)[:6]);assert all(isinstance(w,str) and ' ' not in w for w in d['mfw'])"`
Expected: prints counts; the assertion confirms `mfw` are single tokens (no stored sentences/prose).

- [ ] **Step 4: Commit the asset**

```bash
git -C C:\russellian-book-suite add skills/russellian-style/assets/russell-delta-profile.json
git -C C:\russellian-book-suite commit -m "Add committed Russell-Delta reference profile"
```

---

### Task 4: the scorer

**Files:**
- Create: `skills/russellian-style/scripts/score_russell_delta.py`
- Test: `skills/russellian-style/tests/test_score_russell_delta.py`

- [ ] **Step 1: Write the failing test**

```python
"""Cites REQ-DELTA-003, REQ-DELTA-004, REQ-DELTA-005, REQ-DELTA-006."""
import pytest
pytestmark = pytest.mark.windows_canary
from scripts.build_delta_profile import build_profile
from scripts.score_russell_delta import score


@pytest.fixture
def fixture_profile():
    texts = {
        "a": " ".join(["the of and to the of a in the of"] * 400),
        "b": " ".join(["the to and of a the in of the and"] * 400),
    }
    return build_profile(texts, n_features=6, segment_words=50, min_segment=20)

def test_score_shape(fixture_profile):
    r = score("the of and to the of a in the of " * 200, fixture_profile, min_words=1000)
    assert r["metric"] == "russell-cosine-delta"
    assert set(r["band"]) == {"p10", "p50", "p90"}
    assert r["verdict"] in ("within Russell's range", "outside Russell's range")
    assert isinstance(r["delta"], float)

def test_in_distribution_text_is_within_range(fixture_profile):
    # text drawn from the same token mix scores within Russell's band
    r = score("the of and to the of a in the of " * 300, fixture_profile, min_words=10)
    assert r["delta"] <= fixture_profile["internal_delta"]["p90"] + 1e-9
    assert r["verdict"] == "within Russell's range"

def test_out_of_distribution_text_scores_outside(fixture_profile):
    # alien token mix (no shared function-word signature)
    r = score("zebra zebra quux quux blorp blorp " * 300, fixture_profile, min_words=10)
    assert r["verdict"] == "outside Russell's range"

def test_min_length_guard_sets_reliable_false(fixture_profile):
    r = score("the of and the", fixture_profile, min_words=1000)
    assert r["reliable"] is False
    assert r["n_words"] == 4

def test_determinism(fixture_profile):
    t = "the of and to the of a the in of " * 200
    assert score(t, fixture_profile) == score(t, fixture_profile)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd skills/russellian-style && .venv/Scripts/python.exe -m pytest tests/test_score_russell_delta.py -v`
Expected: FAIL (module does not exist).

- [ ] **Step 3: Write minimal implementation**

```python
"""Advisory Russell-similarity score (Cosine Delta to the reference profile)."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from statistics import mean as _mean

from scripts.lint_common import load_markdown
from scripts.delta_math import tokenize, relative_frequencies, zscore, cosine_delta

PROFILE_PATH = Path(__file__).resolve().parent.parent / "assets" / "russell-delta-profile.json"
MIN_WORDS = 1000


def load_profile(path: Path = PROFILE_PATH) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def score(text: str, profile: dict, min_words: int = MIN_WORDS) -> dict:
    tokens = tokenize(text)
    freqs = relative_frequencies(tokens, profile["mfw"])
    tz = zscore(freqs, profile["mean"], profile["stdev"])
    deltas = [cosine_delta(tz, s) for s in profile["segments_z"]]
    delta = round(_mean(deltas), 6) if deltas else 1.0
    band = profile["internal_delta"]
    verdict = "within Russell's range" if delta <= band["p90"] else "outside Russell's range"
    return {
        "metric": "russell-cosine-delta",
        "delta": delta,
        "band": {"p10": band["p10"], "p50": band["p50"], "p90": band["p90"]},
        "verdict": verdict,
        "n_words": len(tokens),
        "reliable": len(tokens) >= min_words,
    }


def score_file(path, profile_path: Path = PROFILE_PATH) -> dict:
    return score(load_markdown(Path(path)), load_profile(profile_path))


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: score_russell_delta.py <markdown-file>", file=sys.stderr)
        return 2
    print(json.dumps(score_file(argv[1]), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd skills/russellian-style && .venv/Scripts/python.exe -m pytest tests/test_score_russell_delta.py -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git -C C:\russellian-book-suite add skills/russellian-style/scripts/score_russell_delta.py skills/russellian-style/tests/test_score_russell_delta.py
git -C C:\russellian-book-suite commit -m "Add Russell-Delta scorer"
```

---

### Task 5: advisory report integration

**Files:**
- Modify: `skills/russellian-style/scripts/style_pass_report.py` (add to `generate_report_dict`)
- Test: append to `skills/russellian-style/tests/test_score_russell_delta.py`

- [ ] **Step 1: Write the failing test (append)**

```python
def test_report_dict_includes_russell_delta(tmp_path):
    from scripts.style_pass_report import generate_report_dict
    md = tmp_path / "s.md"
    md.write_text("# T\n\n" + ("The nineteenth century discovered pure mathematics. " * 60), encoding="utf-8")
    rep = generate_report_dict(md)
    assert rep["russell_delta"]["metric"] == "russell-cosine-delta"
    assert "verdict" in rep["russell_delta"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd skills/russellian-style && .venv/Scripts/python.exe -m pytest tests/test_score_russell_delta.py::test_report_dict_includes_russell_delta -v`
Expected: FAIL (KeyError `russell_delta`).

- [ ] **Step 3: Implement — add import and one block**

In `style_pass_report.py`, add near the other script imports (after line 23):

```python
from .score_russell_delta import score_file as _russell_delta_score_file
```

In `generate_report_dict`, immediately before the final `return {`, add:

```python
    russell_delta = _russell_delta_score_file(source_path)
```

and add this key to the returned dict (advisory; does not gate):

```python
        "russell_delta": russell_delta,
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd skills/russellian-style && .venv/Scripts/python.exe -m pytest tests/test_score_russell_delta.py -v`
Expected: PASS (6 tests). (Requires the committed profile from Task 3 and the spaCy venv, since `generate_report_dict` runs all linters.)

- [ ] **Step 5: Commit**

```bash
git -C C:\russellian-book-suite add skills/russellian-style/scripts/style_pass_report.py skills/russellian-style/tests/test_score_russell_delta.py
git -C C:\russellian-book-suite commit -m "Surface Russell-Delta as advisory entry in style report"
```

---

### Task 6: regression + real-world sanity

**Files:** none new.

- [ ] **Step 1: Full russellian-style suite**

Run: `cd skills/russellian-style && .venv/Scripts/python.exe -m pytest tests/ -q`
Expected: PASS (all prior tests + the three new test files). No regressions.

- [ ] **Step 2: Score real Russell vs the earlier imitation**

Run (uses the committed profile):
```bash
cd /c/russellian-book-suite/skills/russellian-style
.venv/Scripts/python.exe -m scripts.score_russell_delta "C:\Users\charl\AppData\Local\Temp\compare\real-russell-math.md"
.venv/Scripts/python.exe -m scripts.score_russell_delta "C:\Users\charl\AppData\Local\Temp\compare\generated-math-history.md"
```
Expected: the real excerpt's delta is within the band; record both numbers in the change notes. (If `Temp\compare\*.md` no longer exist, score any real Russell `.txt` from the source cache and the prior generated essay instead.) This is a sanity check, not a gate; if the real excerpt scores `outside`, note it — it signals the band needs widening, a finding for the follow-up recalibration iteration.

- [ ] **Step 3: Record results**

Append the two Delta numbers and the verdict to `openspec/changes/add-russell-delta-scorer/tasks.md` under a new "Sanity results" line, then:

```bash
git -C C:\russellian-book-suite add openspec/changes/add-russell-delta-scorer/tasks.md
git -C C:\russellian-book-suite commit -m "Record Russell-Delta sanity numbers"
```

---

## Self-review (completed during planning)

- **Spec coverage:** REQ-DELTA-001 (asset, Task 3 + builder schema Task 2); 002 (builder, Task 2); 003 (cosine delta to segments, Task 1 + Task 4); 004 (JSON output shape, Task 4); 005 (min-length guard, Task 4); 006 (deterministic + network-free, Tasks 1/2/4 tests); 007 (advisory only — no gate wiring anywhere, report adds a dict key); 008 (report entry, Task 5); 009 (curated corpus ids, Task 3 fetch list). All mapped.
- **Placeholder scan:** none — full module code and exact commands given.
- **Type/name consistency:** `tokenize`, `relative_frequencies`, `zscore`, `cosine`, `cosine_delta` defined in Task 1 and used unchanged in Tasks 2/4; profile keys (`mfw`, `mean`, `stdev`, `segments_z`, `internal_delta`) consistent between builder (Task 2) and scorer (Task 4); `score`/`score_file` names consistent between Task 4 and Task 5.

## Not in scope

- Gating on Delta; budget-linter recalibration; the rubric "virtues" judge; detector-precision fixes (all named follow-ups in the design doc).
- Opening the PR / pushing — operator's decision.
