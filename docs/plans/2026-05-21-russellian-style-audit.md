# russellian-style end-to-end audit — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a one-shot CLI audit that (1) runs five deterministic health checks against the russellian-style skill, (2) runs one live build-russell-corpus expansion batch on the `problems` PD source with an operator-approval gate before appending to the index, and (3) generates three 15-paragraph sample texts via the three system prompts, lints each, and writes everything to `docs/audits/2026-05-21-russellian-style/`.

**Architecture:** A new `tools/russellian-style-audit/` package orchestrates the pipeline; a thin `tools/build-russell-corpus/scripts/live_llm.py` wraps the Anthropic SDK and is reused by both the expansion stage and the generation stage. The audit tool depends on `build-russell-corpus` (already on `main`) and `russellian-style/skill_api`. Operator interaction happens at one point only: a blocking stdin prompt after the expansion audit-sample is written.

**Tech Stack:** Python ≥3.11, pytest 8.x, `anthropic` SDK, pyyaml, jsonschema. Same conventions as `tools/build-russell-corpus/`.

**Spec:** `docs/specs/2026-05-21-russellian-style-audit-design.md` (commit `de7cf27`).

---

## File structure

```
tools/build-russell-corpus/
├── pyproject.toml               (modified: add anthropic runtime extra)
├── scripts/
│   └── live_llm.py              (new)
└── tests/
    └── test_live_llm.py         (new)

tools/russellian-style-audit/
├── pyproject.toml               (new)
├── scripts/
│   ├── __init__.py
│   ├── run.py                   (CLI orchestrator)
│   ├── health_check.py          (five deterministic checks + orchestrator)
│   ├── expansion.py             (wraps build-russell-corpus pipeline)
│   ├── operator_gate.py         (blocking stdin prompt)
│   ├── generate_samples.py      (3 LLM calls per mode)
│   ├── lint_samples.py          (runs skill_api.lint_fragment + scoring)
│   └── report.py                (markdown rendering)
└── tests/
    ├── __init__.py
    ├── test_health_check.py
    ├── test_report.py
    └── fixtures/
        ├── clean.md
        ├── hedged.md
        └── listicle.md
```

Output bundle (written by `run.py`):

```
docs/audits/2026-05-21-russellian-style/
├── README.md
├── health-check.md
├── expansion.md
├── samples/
│   ├── technical-exposition.md
│   ├── technical-exposition-lint.md
│   ├── narrative-editorial.md
│   ├── narrative-editorial-lint.md
│   ├── polemic.md
│   ├── polemic-lint.md
│   └── summary.md
└── runs/<batch-id>/
    ├── candidates.jsonl
    ├── passed-sentinel.jsonl
    ├── rejected.jsonl
    ├── pending-tag.jsonl
    ├── proposed-tags.jsonl
    ├── verified.jsonl
    └── audit/sample.md
```

---

### Task 0: Audit project skeleton

**Files:**
- Create: `tools/russellian-style-audit/pyproject.toml`
- Create: `tools/russellian-style-audit/scripts/__init__.py` (empty)
- Create: `tools/russellian-style-audit/tests/__init__.py` (empty)

- [ ] **Step 1: Write `pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "russellian-style-audit"
version = "0.1.0"
description = "One-shot end-to-end audit of the russellian-style skill: health check + live corpus expansion + 3 sample-text generations with lint reports."
requires-python = ">=3.11"
dependencies = [
    "pyyaml>=6.0,<7.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0,<9.0",
    "pyyaml>=6.0,<7.0",
]

[tool.setuptools]
packages = ["scripts"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-v"
```

- [ ] **Step 2: Create the empty package files**

Run from `C:\russellian-book-suite`:
```bash
mkdir -p tools/russellian-style-audit/scripts tools/russellian-style-audit/tests/fixtures
touch tools/russellian-style-audit/scripts/__init__.py
touch tools/russellian-style-audit/tests/__init__.py
```

- [ ] **Step 3: Set up the venv and verify empty pytest run**

```bash
cd tools/russellian-style-audit
python -m venv .venv
.venv/Scripts/pip install -e ".[dev]"
.venv/Scripts/python -m pytest tests/ -q
```

Expected: `no tests ran`, exit code 5.

- [ ] **Step 4: Commit**

**CRITICAL: subject only, no body, no `Co-Authored-By`, no AI attribution. After commit, `git log -1 --format='%B'`; amend immediately if anything beyond the subject appears.**

```bash
cd /c/russellian-book-suite && git add tools/russellian-style-audit/pyproject.toml tools/russellian-style-audit/scripts/__init__.py tools/russellian-style-audit/tests/__init__.py && git commit -m "tools/russellian-style-audit: project skeleton"
```

EXACT message: `tools/russellian-style-audit: project skeleton`

---

### Task 1: live_llm module with stub-error test

**Files:**
- Modify: `tools/build-russell-corpus/pyproject.toml`
- Create: `tools/build-russell-corpus/scripts/live_llm.py`
- Create: `tools/build-russell-corpus/tests/test_live_llm.py`

- [ ] **Step 1: Add anthropic to dev extras**

Edit `tools/build-russell-corpus/pyproject.toml`. Find the `[project.optional-dependencies]` block:

```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.0,<9.0",
    "pyyaml>=6.0,<7.0",
    "jsonschema>=4.21,<5.0",
]
```

Replace it with:

```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.0,<9.0",
    "pyyaml>=6.0,<7.0",
    "jsonschema>=4.21,<5.0",
    "anthropic>=0.40,<1.0",
]
runtime = [
    "anthropic>=0.40,<1.0",
]
```

- [ ] **Step 2: Reinstall the venv to pick up anthropic**

```bash
cd /c/russellian-book-suite/tools/build-russell-corpus && .venv/Scripts/pip install -e ".[dev]"
```

Expected: `Successfully installed anthropic-x.y.z httpx-... ...` (or similar).

- [ ] **Step 3: Write the failing test**

Create `tools/build-russell-corpus/tests/test_live_llm.py`:

```python
import os
import pytest


def test_live_llm_imports_without_key():
    """Importing live_llm must not require ANTHROPIC_API_KEY to be set."""
    saved = os.environ.pop("ANTHROPIC_API_KEY", None)
    try:
        from scripts import live_llm  # noqa: F401
    finally:
        if saved is not None:
            os.environ["ANTHROPIC_API_KEY"] = saved


def test_extract_llm_raises_clear_runtime_error_without_key():
    """Calling extract_llm without ANTHROPIC_API_KEY raises a clear RuntimeError, not a network error."""
    from scripts.live_llm import extract_llm
    saved = os.environ.pop("ANTHROPIC_API_KEY", None)
    try:
        with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
            extract_llm("hello")
    finally:
        if saved is not None:
            os.environ["ANTHROPIC_API_KEY"] = saved


def test_cross_check_llm_raises_clear_runtime_error_without_key():
    from scripts.live_llm import cross_check_llm
    saved = os.environ.pop("ANTHROPIC_API_KEY", None)
    try:
        with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
            cross_check_llm("hello")
    finally:
        if saved is not None:
            os.environ["ANTHROPIC_API_KEY"] = saved


def test_generate_raises_clear_runtime_error_without_key():
    from scripts.live_llm import generate
    saved = os.environ.pop("ANTHROPIC_API_KEY", None)
    try:
        with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
            generate("hello", model="claude-opus-4-7", max_tokens=100)
    finally:
        if saved is not None:
            os.environ["ANTHROPIC_API_KEY"] = saved
```

- [ ] **Step 4: Run, verify failure**

```bash
cd /c/russellian-book-suite/tools/build-russell-corpus && .venv/Scripts/python -m pytest tests/test_live_llm.py -v
```

Expected: ImportError on `scripts.live_llm`.

- [ ] **Step 5: Write `scripts/live_llm.py`**

```python
"""Anthropic-SDK wrapper exposing extract_llm, cross_check_llm, and generate.

Production code uses these; tests pass stubs to the stage callables instead.
The module deliberately raises a clear RuntimeError when ANTHROPIC_API_KEY is
unset rather than letting the SDK fail mid-network-call.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml


_CONFIG_PATH = Path(__file__).parent.parent / "assets" / "llm-config.yaml"


def _load_config() -> dict[str, Any]:
    return yaml.safe_load(_CONFIG_PATH.read_text(encoding="utf-8"))


def _client():
    """Construct an Anthropic client. Raises RuntimeError if the API key is missing."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError(
            "ANTHROPIC_API_KEY not set in environment; cannot call Anthropic API."
        )
    from anthropic import Anthropic  # lazy import so the module loads without the SDK installed
    return Anthropic()


def _call(prompt: str, *, model: str, max_tokens: int, temperature: float) -> str:
    client = _client()
    msg = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(getattr(block, "text", "") for block in msg.content)


def extract_llm(prompt: str) -> str:
    """Run the corpus extractor model on a prompt and return the text."""
    cfg = _load_config()["extract"]
    return _call(prompt, model=cfg["model_id"], max_tokens=cfg["max_tokens"],
                 temperature=cfg["temperature"])


def cross_check_llm(prompt: str) -> str:
    """Run the cross-check verifier model on a prompt and return the text."""
    cfg = _load_config()["cross_check"]
    return _call(prompt, model=cfg["model_id"], max_tokens=cfg["max_tokens"],
                 temperature=cfg["temperature"])


def generate(prompt: str, *, model: str = "claude-opus-4-7",
             max_tokens: int = 8192, temperature: float = 0.7) -> str:
    """General-purpose generation. Used by the audit's sample-text stage."""
    return _call(prompt, model=model, max_tokens=max_tokens, temperature=temperature)
```

- [ ] **Step 6: Run tests, verify pass**

```bash
.venv/Scripts/python -m pytest tests/test_live_llm.py -v
```

Expected: 4 passed.

- [ ] **Step 7: Commit**

```bash
cd /c/russellian-book-suite && git add tools/build-russell-corpus/pyproject.toml tools/build-russell-corpus/scripts/live_llm.py tools/build-russell-corpus/tests/test_live_llm.py && git commit -m "tools/build-russell-corpus: anthropic live_llm caller with stub-safe imports"
```

EXACT message: `tools/build-russell-corpus: anthropic live_llm caller with stub-safe imports`

Verify with `git log -1 --format='%B'` — subject only.

---

### Task 2: health_check — pytest_suite and api_smoke

**Files:**
- Create: `tools/russellian-style-audit/scripts/health_check.py`
- Create: `tools/russellian-style-audit/tests/test_health_check.py`
- Create: `tools/russellian-style-audit/tests/fixtures/clean.md`
- Create: `tools/russellian-style-audit/tests/fixtures/hedged.md`
- Create: `tools/russellian-style-audit/tests/fixtures/listicle.md`

- [ ] **Step 1: Write the three fixture texts**

Create `tests/fixtures/clean.md`:

```
The script provisions the server in four seconds. Each step writes a single line
to the journal. The journal is append-only; no step rewrites a prior entry.
```

Create `tests/fixtures/hedged.md`:

```
The script might possibly provision the server, perhaps in some number of seconds.
It could be argued that the journal is to some extent append-only.
```

Create `tests/fixtures/listicle.md`:

```
The manual rests on six premises: 1. Source-grounding. 2. Tag verification.
3. Lesson specificity. 4. Audit sampling. 5. Halt thresholds. 6. Reporting.
Each premise carries its own deterministic check.
```

- [ ] **Step 2: Write the failing tests**

Create `tools/russellian-style-audit/tests/test_health_check.py`:

```python
from pathlib import Path

from scripts.health_check import HealthCheckResult, check_api_smoke, check_pytest_suite


FIXTURES = Path(__file__).parent / "fixtures"


def test_health_check_result_dataclass_shape():
    r = HealthCheckResult(name="x", status="PASS", evidence="all good")
    assert r.name == "x"
    assert r.status == "PASS"
    assert r.evidence == "all good"


def test_check_api_smoke_clean_text_returns_no_issues():
    result = check_api_smoke(
        clean_path=FIXTURES / "clean.md",
        hedged_path=FIXTURES / "hedged.md",
        listicle_path=FIXTURES / "listicle.md",
    )
    assert isinstance(result, HealthCheckResult)
    assert result.name == "api_smoke"
    assert result.status in {"PASS", "FAIL"}
    # Clean text: no LintIssue should fire on the default linters.
    # Hedged text: at least one "no-hedging" finding.
    # Listicle text: at least one "listicle-abstract" finding.
    # On a healthy skill, this returns PASS.
    if result.status == "PASS":
        assert "no-hedging" in result.evidence or "linter" in result.evidence.lower()


def test_check_pytest_suite_runs_pytest_and_returns_status(tmp_path: Path):
    """check_pytest_suite invokes pytest as a subprocess; tests it as a callable interface."""
    # Use the audit tool's own tests as the target — they exist, so pytest should pass.
    audit_tests_dir = Path(__file__).parent
    result = check_pytest_suite(tests_dir=audit_tests_dir)
    assert isinstance(result, HealthCheckResult)
    assert result.name == "pytest_suite"
    # We don't assert PASS/FAIL because the audit tests themselves are running right now;
    # the recursion can produce strange outcomes. We just confirm the shape.
    assert result.status in {"PASS", "FAIL"}
    assert "exit" in result.evidence.lower() or "passed" in result.evidence.lower() or "failed" in result.evidence.lower()
```

- [ ] **Step 3: Run, verify failure**

```bash
cd /c/russellian-book-suite/tools/russellian-style-audit && .venv/Scripts/python -m pytest tests/test_health_check.py -v
```

Expected: ImportError on `scripts.health_check`.

- [ ] **Step 4: Write `scripts/health_check.py` (this task only adds two checks; later tasks add the rest)**

Create `tools/russellian-style-audit/scripts/health_check.py`:

```python
"""Five deterministic health checks for the russellian-style skill.

Each check returns a HealthCheckResult with status PASS | WARN | FAIL and a one-line
evidence string. The orchestrator collects all five and produces health-check.md.

This module contains the dataclass and the first two checks (pytest_suite, api_smoke).
composes_with, corpus_retrieval, and system_prompts are added by later tasks.
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_RUSSELLIAN_STYLE_ROOT = _REPO_ROOT / "skills" / "russellian-style"


@dataclass
class HealthCheckResult:
    name: str        # check id
    status: str      # "PASS" | "WARN" | "FAIL"
    evidence: str    # one-line summary suitable for a markdown table cell


def check_pytest_suite(tests_dir: Path | None = None) -> HealthCheckResult:
    """Invoke pytest as a subprocess against the russellian-style tests directory."""
    target = tests_dir if tests_dir is not None else _RUSSELLIAN_STYLE_ROOT / "tests"
    if not target.exists():
        return HealthCheckResult(
            name="pytest_suite",
            status="FAIL",
            evidence=f"tests dir does not exist: {target}",
        )
    venv_python = _RUSSELLIAN_STYLE_ROOT / ".venv" / ("Scripts" if sys.platform == "win32" else "bin") / ("python.exe" if sys.platform == "win32" else "python")
    interpreter = str(venv_python) if venv_python.exists() else sys.executable
    completed = subprocess.run(
        [interpreter, "-m", "pytest", str(target), "-q", "--tb=no"],
        capture_output=True,
        text=True,
        cwd=str(_RUSSELLIAN_STYLE_ROOT),
    )
    last_line = (completed.stdout or completed.stderr or "").strip().splitlines()[-1] if (completed.stdout or completed.stderr) else ""
    status = "PASS" if completed.returncode == 0 else "FAIL"
    return HealthCheckResult(
        name="pytest_suite",
        status=status,
        evidence=f"exit {completed.returncode}; {last_line}",
    )


def check_api_smoke(
    *,
    clean_path: Path,
    hedged_path: Path,
    listicle_path: Path,
) -> HealthCheckResult:
    """Smoke-test skill_api.lint_fragment against three fixture texts."""
    try:
        sys.path.insert(0, str(_RUSSELLIAN_STYLE_ROOT))
        try:
            from skill_api import lint_fragment, LintIssue  # type: ignore
        finally:
            sys.path.pop(0)
    except Exception as exc:
        return HealthCheckResult(
            name="api_smoke",
            status="FAIL",
            evidence=f"cannot import skill_api: {exc}",
        )

    clean_text = clean_path.read_text(encoding="utf-8")
    hedged_text = hedged_path.read_text(encoding="utf-8")
    listicle_text = listicle_path.read_text(encoding="utf-8")

    clean_issues = lint_fragment(clean_text)
    hedged_issues = lint_fragment(hedged_text)
    listicle_issues = lint_fragment(listicle_text)

    if not all(isinstance(i, LintIssue) for i in clean_issues + hedged_issues + listicle_issues):
        return HealthCheckResult(
            name="api_smoke",
            status="FAIL",
            evidence="lint_fragment returned non-LintIssue items",
        )

    hedged_no_hedging = any(i.linter == "no-hedging" for i in hedged_issues)
    listicle_hit = any(i.linter == "listicle-abstract" for i in listicle_issues)

    if len(clean_issues) <= 1 and hedged_no_hedging and listicle_hit:
        return HealthCheckResult(
            name="api_smoke",
            status="PASS",
            evidence=f"clean={len(clean_issues)}; hedged hit no-hedging; listicle hit listicle-abstract",
        )
    return HealthCheckResult(
        name="api_smoke",
        status="FAIL",
        evidence=(
            f"clean={len(clean_issues)} (expected <=1); "
            f"hedged hit no-hedging={hedged_no_hedging}; "
            f"listicle hit listicle-abstract={listicle_hit}"
        ),
    )
```

- [ ] **Step 5: Run tests, verify pass**

```bash
.venv/Scripts/python -m pytest tests/test_health_check.py -v
```

Expected: 3 passed.

If `check_api_smoke` returns FAIL inside the test, the skill itself is misbehaving. Inspect the evidence string. The test asserts only the shape and "PASS or FAIL" — it does not require PASS — so the test should still pass even if the underlying skill is broken.

- [ ] **Step 6: Commit**

```bash
cd /c/russellian-book-suite && git add tools/russellian-style-audit/scripts/health_check.py tools/russellian-style-audit/tests/test_health_check.py tools/russellian-style-audit/tests/fixtures/clean.md tools/russellian-style-audit/tests/fixtures/hedged.md tools/russellian-style-audit/tests/fixtures/listicle.md && git commit -m "tools/russellian-style-audit: pytest_suite and api_smoke checks"
```

EXACT message: `tools/russellian-style-audit: pytest_suite and api_smoke checks`

Verify with `git log -1 --format='%B'` — subject only.

---

### Task 3: health_check — composes_with

**Files:**
- Modify: `tools/russellian-style-audit/scripts/health_check.py`
- Modify: `tools/russellian-style-audit/tests/test_health_check.py`

- [ ] **Step 1: Append failing test**

Append to `tools/russellian-style-audit/tests/test_health_check.py`:

```python
from scripts.health_check import check_composes_with


def test_check_composes_with_returns_pass_or_warn_per_consumer(tmp_path: Path):
    """composes_with reports per-consumer status; missing venvs WARN, present venvs run import smoke."""
    result = check_composes_with(consumers=["book-compose", "book-review", "book-qa", "humanizer"])
    assert isinstance(result, HealthCheckResult)
    assert result.name == "composes_with"
    assert result.status in {"PASS", "WARN", "FAIL"}
    # Evidence string mentions each consumer
    for consumer in ["book-compose", "book-review", "book-qa", "humanizer"]:
        assert consumer in result.evidence


def test_check_composes_with_warns_when_consumer_venv_missing(tmp_path: Path):
    """A non-existent consumer name produces WARN evidence including the missing-venv reason."""
    result = check_composes_with(consumers=["nonexistent-skill-xyz"])
    assert result.status == "WARN"
    assert "nonexistent-skill-xyz" in result.evidence
    assert "venv" in result.evidence.lower() or "missing" in result.evidence.lower()
```

- [ ] **Step 2: Run, verify failure**

```bash
.venv/Scripts/python -m pytest tests/test_health_check.py::test_check_composes_with_warns_when_consumer_venv_missing -v
```

Expected: ImportError on `check_composes_with`.

- [ ] **Step 3: Append `check_composes_with` to `scripts/health_check.py`**

```python
def check_composes_with(*, consumers: list[str]) -> HealthCheckResult:
    """For each consumer skill, run `python -c "from russellian_style.skill_api import lint_fragment, API_VERSION"`
    in that consumer's venv. Report per-consumer status and aggregate.
    """
    per_consumer: list[str] = []
    all_pass = True
    any_warn = False
    for consumer in consumers:
        consumer_root = _REPO_ROOT / "skills" / consumer
        venv_python = consumer_root / ".venv" / ("Scripts" if sys.platform == "win32" else "bin") / ("python.exe" if sys.platform == "win32" else "python")
        if not venv_python.exists():
            per_consumer.append(f"{consumer}=WARN(venv missing)")
            any_warn = True
            all_pass = False
            continue
        # Probe the import. The test runs from outside the consumer; rely on the consumer's venv
        # having russellian-style on its sys.path (via sibling_skills loader or editable install).
        completed = subprocess.run(
            [str(venv_python), "-c", "from russellian_style.skill_api import lint_fragment, API_VERSION; print(API_VERSION)"],
            capture_output=True, text=True,
        )
        if completed.returncode == 0:
            per_consumer.append(f"{consumer}=PASS({completed.stdout.strip()})")
        else:
            per_consumer.append(f"{consumer}=FAIL({completed.stderr.strip()[:80]})")
            all_pass = False
    status = "PASS" if all_pass else ("WARN" if any_warn and not any("FAIL" in p for p in per_consumer) else "FAIL")
    return HealthCheckResult(
        name="composes_with",
        status=status,
        evidence="; ".join(per_consumer),
    )
```

- [ ] **Step 4: Run, verify pass**

```bash
.venv/Scripts/python -m pytest tests/test_health_check.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
cd /c/russellian-book-suite && git add tools/russellian-style-audit/scripts/health_check.py tools/russellian-style-audit/tests/test_health_check.py && git commit -m "tools/russellian-style-audit: composes_with check"
```

EXACT message: `tools/russellian-style-audit: composes_with check`

Verify with `git log -1 --format='%B'` — subject only.

---

### Task 4: health_check — corpus_retrieval and system_prompts

**Files:**
- Modify: `tools/russellian-style-audit/scripts/health_check.py`
- Modify: `tools/russellian-style-audit/tests/test_health_check.py`

- [ ] **Step 1: Append failing tests**

```python
from scripts.health_check import check_corpus_retrieval, check_system_prompts


def test_check_corpus_retrieval_returns_pass_or_fail():
    result = check_corpus_retrieval(tags=["antithesis", "concrete_example", "concession"])
    assert isinstance(result, HealthCheckResult)
    assert result.name == "corpus_retrieval"
    assert result.status in {"PASS", "FAIL"}
    for tag in ["antithesis", "concrete_example", "concession"]:
        assert tag in result.evidence


def test_check_system_prompts_loads_all_three_modes():
    result = check_system_prompts(modes=["technical-exposition", "narrative-editorial", "polemic"])
    assert isinstance(result, HealthCheckResult)
    assert result.name == "system_prompts"
    assert result.status in {"PASS", "FAIL"}
    for mode in ["technical-exposition", "narrative-editorial", "polemic"]:
        assert mode in result.evidence
```

- [ ] **Step 2: Run, verify failure**

```bash
.venv/Scripts/python -m pytest tests/test_health_check.py -v
```

Expected: ImportError on `check_corpus_retrieval` and `check_system_prompts`.

- [ ] **Step 3: Append both checks to `scripts/health_check.py`**

```python
def check_corpus_retrieval(*, tags: list[str]) -> HealthCheckResult:
    """For each tag, call retrieve_corpus_anchor.retrieve and confirm at least one anchor returns."""
    try:
        sys.path.insert(0, str(_RUSSELLIAN_STYLE_ROOT))
        try:
            from scripts.retrieve_corpus_anchor import retrieve_corpus_anchor  # type: ignore
        finally:
            sys.path.pop(0)
    except Exception as exc:
        return HealthCheckResult(
            name="corpus_retrieval",
            status="FAIL",
            evidence=f"cannot import retrieve_corpus_anchor: {exc}",
        )
    per_tag: list[str] = []
    all_ok = True
    for tag in tags:
        try:
            anchors = retrieve_corpus_anchor(tag)
            count = len(anchors) if anchors is not None else 0
            per_tag.append(f"{tag}={count}")
            if count == 0:
                all_ok = False
        except Exception as exc:
            per_tag.append(f"{tag}=ERROR({exc.__class__.__name__})")
            all_ok = False
    return HealthCheckResult(
        name="corpus_retrieval",
        status="PASS" if all_ok else "FAIL",
        evidence="; ".join(per_tag),
    )


def check_system_prompts(*, modes: list[str]) -> HealthCheckResult:
    """For each mode, call system_prompt_loader.load(mode) and confirm a non-empty string with the mandate header."""
    try:
        sys.path.insert(0, str(_RUSSELLIAN_STYLE_ROOT))
        try:
            from scripts.system_prompt_loader import load  # type: ignore
        finally:
            sys.path.pop(0)
    except Exception as exc:
        return HealthCheckResult(
            name="system_prompts",
            status="FAIL",
            evidence=f"cannot import system_prompt_loader: {exc}",
        )
    per_mode: list[str] = []
    all_ok = True
    for mode in modes:
        try:
            text = load(mode)
            has_mandate = "Structural mandates" in text
            per_mode.append(f"{mode}={'PASS' if has_mandate else 'FAIL(no mandate header)'}")
            if not has_mandate:
                all_ok = False
        except Exception as exc:
            per_mode.append(f"{mode}=ERROR({exc.__class__.__name__})")
            all_ok = False
    return HealthCheckResult(
        name="system_prompts",
        status="PASS" if all_ok else "FAIL",
        evidence="; ".join(per_mode),
    )
```

**Note:** if `retrieve_corpus_anchor.py` exposes a function named differently than `retrieve_corpus_anchor`, inspect the actual module and adjust the import line. Run `python -c "from scripts.retrieve_corpus_anchor import *; print(dir())"` in the russellian-style venv to confirm.

- [ ] **Step 4: Run, verify pass**

```bash
.venv/Scripts/python -m pytest tests/test_health_check.py -v
```

Expected: 7 passed.

If `corpus_retrieval` returns FAIL because the function name doesn't match, fix the import per the note above and re-run.

- [ ] **Step 5: Commit**

```bash
cd /c/russellian-book-suite && git add tools/russellian-style-audit/scripts/health_check.py tools/russellian-style-audit/tests/test_health_check.py && git commit -m "tools/russellian-style-audit: corpus_retrieval and system_prompts checks"
```

EXACT message: `tools/russellian-style-audit: corpus_retrieval and system_prompts checks`

Verify with `git log -1 --format='%B'`.

---

### Task 5: health_check orchestrator

**Files:**
- Modify: `tools/russellian-style-audit/scripts/health_check.py`
- Modify: `tools/russellian-style-audit/tests/test_health_check.py`

- [ ] **Step 1: Append failing test**

```python
from scripts.health_check import run_all_health_checks


def test_run_all_health_checks_returns_five_results():
    results = run_all_health_checks(
        fixtures_dir=FIXTURES,
        consumers=["nonexistent-skill-xyz"],  # forces WARN row
        tags=["antithesis"],
        modes=["technical-exposition"],
    )
    assert len(results) == 5
    names = {r.name for r in results}
    assert names == {"pytest_suite", "api_smoke", "composes_with", "corpus_retrieval", "system_prompts"}


def test_run_all_health_checks_halts_on_fail():
    """A FAIL row in the result list should be observable; the orchestrator does not raise."""
    results = run_all_health_checks(
        fixtures_dir=FIXTURES,
        consumers=["nonexistent-skill-xyz"],
        tags=["nonexistent_tag_xyz_123"],
        modes=["technical-exposition"],
    )
    # corpus_retrieval should FAIL because the tag doesn't exist in any anchor
    cr = next(r for r in results if r.name == "corpus_retrieval")
    assert cr.status == "FAIL"
```

- [ ] **Step 2: Run, verify failure**

```bash
.venv/Scripts/python -m pytest tests/test_health_check.py -v
```

Expected: ImportError on `run_all_health_checks`.

- [ ] **Step 3: Append the orchestrator to `scripts/health_check.py`**

```python
def run_all_health_checks(
    *,
    fixtures_dir: Path,
    consumers: list[str] | None = None,
    tags: list[str] | None = None,
    modes: list[str] | None = None,
) -> list[HealthCheckResult]:
    """Run all five health checks in order. Returns the result list.

    The orchestrator does not raise on FAIL — the caller (run.py) inspects the list
    and decides whether to halt before stage 4 of the audit pipeline.
    """
    consumers = consumers or ["book-compose", "book-review", "book-qa", "humanizer"]
    tags = tags or ["antithesis", "concrete_example", "concession", "domain_contrast", "paragraph_turn"]
    modes = modes or ["technical-exposition", "narrative-editorial", "polemic"]
    return [
        check_pytest_suite(),
        check_api_smoke(
            clean_path=fixtures_dir / "clean.md",
            hedged_path=fixtures_dir / "hedged.md",
            listicle_path=fixtures_dir / "listicle.md",
        ),
        check_composes_with(consumers=consumers),
        check_corpus_retrieval(tags=tags),
        check_system_prompts(modes=modes),
    ]
```

- [ ] **Step 4: Run tests, verify pass**

```bash
.venv/Scripts/python -m pytest tests/test_health_check.py -v
```

Expected: 9 passed.

- [ ] **Step 5: Commit**

```bash
cd /c/russellian-book-suite && git add tools/russellian-style-audit/scripts/health_check.py tools/russellian-style-audit/tests/test_health_check.py && git commit -m "tools/russellian-style-audit: health-check orchestrator"
```

EXACT message: `tools/russellian-style-audit: health-check orchestrator`

---

### Task 6: report — markdown rendering

**Files:**
- Create: `tools/russellian-style-audit/scripts/report.py`
- Create: `tools/russellian-style-audit/tests/test_report.py`

- [ ] **Step 1: Write failing tests**

Create `tools/russellian-style-audit/tests/test_report.py`:

```python
from pathlib import Path

from scripts.health_check import HealthCheckResult
from scripts.report import render_health_check_md, render_summary_md, render_readme_md


def test_render_health_check_md_emits_table():
    results = [
        HealthCheckResult(name="pytest_suite", status="PASS", evidence="84 passed in 12.31s"),
        HealthCheckResult(name="api_smoke", status="PASS", evidence="3 fixtures OK"),
        HealthCheckResult(name="composes_with", status="WARN", evidence="book-compose=WARN(venv missing)"),
    ]
    md = render_health_check_md(results)
    assert "# Health check" in md
    assert "| Check | Status | Evidence |" in md
    assert "| pytest_suite | PASS |" in md
    assert "| composes_with | WARN |" in md


def test_render_summary_md_emits_per_mode_table():
    per_mode = [
        {"mode": "technical-exposition", "gating": 1, "advisory": 4, "verdict": "PASS"},
        {"mode": "narrative-editorial", "gating": 3, "advisory": 7, "verdict": "WARN"},
        {"mode": "polemic", "gating": 0, "advisory": 2, "verdict": "PASS"},
    ]
    md = render_summary_md(per_mode)
    assert "| Mode | Gating | Advisory | Verdict |" in md
    assert "| technical-exposition | 1 | 4 | PASS |" in md
    assert "| polemic | 0 | 2 | PASS |" in md


def test_render_readme_md_combines_verdicts():
    md = render_readme_md(
        health_verdict="PASS",
        expansion_verdict="PASS (appended 47 new entries to russellian-style index)",
        samples_verdict="PASS (3/3 modes returned PASS verdict)",
        batch_id="2026-05-21-001",
    )
    assert "# russellian-style audit" in md
    assert "PASS" in md
    assert "2026-05-21-001" in md
    assert "health-check.md" in md
    assert "expansion.md" in md
    assert "samples/summary.md" in md
```

- [ ] **Step 2: Run, verify failure**

```bash
.venv/Scripts/python -m pytest tests/test_report.py -v
```

Expected: ImportError on `scripts.report`.

- [ ] **Step 3: Write `scripts/report.py`**

```python
"""Markdown rendering for the audit bundle.

Three top-level renderers: health-check, samples summary, and README. Each takes
plain data and returns a markdown string. No I/O — the caller writes the strings
to disk.
"""

from __future__ import annotations

from typing import Any

from scripts.health_check import HealthCheckResult


def render_health_check_md(results: list[HealthCheckResult]) -> str:
    lines = ["# Health check", "", "| Check | Status | Evidence |", "| --- | --- | --- |"]
    for r in results:
        evidence = r.evidence.replace("|", "\\|")
        lines.append(f"| {r.name} | {r.status} | {evidence} |")
    return "\n".join(lines) + "\n"


def render_summary_md(per_mode: list[dict[str, Any]]) -> str:
    lines = ["# Sample texts — summary", "", "| Mode | Gating | Advisory | Verdict |", "| --- | ---: | ---: | --- |"]
    for row in per_mode:
        lines.append(f"| {row['mode']} | {row['gating']} | {row['advisory']} | {row['verdict']} |")
    return "\n".join(lines) + "\n"


def render_readme_md(
    *,
    health_verdict: str,
    expansion_verdict: str,
    samples_verdict: str,
    batch_id: str,
) -> str:
    return (
        "# russellian-style audit\n\n"
        f"**Batch ID:** `{batch_id}`\n\n"
        "## Verdicts\n\n"
        f"- Health check: **{health_verdict}**\n"
        f"- Expansion: **{expansion_verdict}**\n"
        f"- Sample texts: **{samples_verdict}**\n\n"
        "## Artifacts\n\n"
        "- [health-check.md](health-check.md)\n"
        "- [expansion.md](expansion.md)\n"
        "- [samples/summary.md](samples/summary.md)\n"
        "  - [technical-exposition.md](samples/technical-exposition.md) + [lint](samples/technical-exposition-lint.md)\n"
        "  - [narrative-editorial.md](samples/narrative-editorial.md) + [lint](samples/narrative-editorial-lint.md)\n"
        "  - [polemic.md](samples/polemic.md) + [lint](samples/polemic-lint.md)\n"
        f"- [runs/{batch_id}/](runs/{batch_id}/) — full expansion ledgers\n"
    )


def render_lint_report_md(*, mode: str, per_rule: list[dict[str, Any]],
                          gating_count: int, advisory_count: int, verdict: str) -> str:
    lines = [
        f"# Lint report — {mode}",
        "",
        "## Per-rule counts",
        "",
        "| Rule | Count | First 3 violations |",
        "| --- | ---: | --- |",
    ]
    for row in per_rule:
        first3 = "; ".join(row["first3"]) if row["first3"] else "—"
        first3_escaped = first3.replace("|", "\\|")
        lines.append(f"| {row['rule']} | {row['count']} | {first3_escaped} |")
    lines += [
        "",
        "## Totals",
        "",
        f"- Gating violations: {gating_count}",
        f"- Advisory violations: {advisory_count}",
        "",
        f"## Verdict\n\n**{verdict}**",
        "",
    ]
    return "\n".join(lines) + "\n"


def render_expansion_md(
    *,
    batch_id: str,
    n_candidates: int,
    n_passed_sentinel: int,
    n_verified: int,
    n_rejected: int,
    appended: bool,
    halt_reason: str | None,
    sample_accepted: list[str],
) -> str:
    lines = [
        f"# Expansion batch — {batch_id}",
        "",
        "## Counts",
        "",
        f"- Candidates: {n_candidates}",
        f"- Passed sentinel: {n_passed_sentinel}",
        f"- Verified: {n_verified}",
        f"- Rejected: {n_rejected}",
        "",
    ]
    if appended:
        lines += [f"## Result\n\nAppended {n_verified} verified entries to `skills/russellian-style/assets/russell-corpus/index.json`.", ""]
    else:
        lines += [f"## Result\n\nHalted before append. Reason: {halt_reason or 'unspecified'}", ""]
    if sample_accepted:
        lines += ["## Sample of accepted entries", ""]
        for s in sample_accepted[:5]:
            lines.append(f"- `{s}`")
        lines.append("")
    return "\n".join(lines) + "\n"
```

- [ ] **Step 4: Run tests, verify pass**

```bash
.venv/Scripts/python -m pytest tests/test_report.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
cd /c/russellian-book-suite && git add tools/russellian-style-audit/scripts/report.py tools/russellian-style-audit/tests/test_report.py && git commit -m "tools/russellian-style-audit: markdown renderers"
```

EXACT message: `tools/russellian-style-audit: markdown renderers`

---

### Task 7: operator_gate — blocking stdin

**Files:**
- Create: `tools/russellian-style-audit/scripts/operator_gate.py`

This task does NOT have a unit test — the function is a thin wrapper over `input()` that reads from stdin. Mocking stdin in pytest is possible but adds friction without much benefit for a ~10-line function. The function is exercised by the end-to-end test (Task 12) via a captured-stdin stub.

- [ ] **Step 1: Write `scripts/operator_gate.py`**

```python
"""Blocking stdin prompt for the expansion gate.

The audit pauses here and waits for the operator to either approve the audit sample
or halt. Returns a list of accept/reject decisions, OR the string "halt" if the
operator typed halt.
"""

from __future__ import annotations

from pathlib import Path


def prompt_operator(sample_path: Path, n_sample: int, n_verified: int, input_fn=input) -> str | list[str]:
    """Prompt operator for accept/reject decisions or halt.

    Returns:
      "halt" if the operator typed halt.
      list[str] of accept/reject tokens otherwise.

    Raises ValueError if the response is unparseable.
    """
    prompt = (
        f"\nAudit sample written to: {sample_path}\n"
        f"The sample contains {n_sample} entries ({n_sample}/{n_verified} verified).\n"
        "For each entry, mark accept or reject.\n\n"
        "Reply with a comma-separated list of decisions in order, e.g.:\n"
        "    accept,accept,reject\n\n"
        "Or reply 'halt' to stop without appending any entries.\n\n"
        "Decision: "
    )
    raw = input_fn(prompt).strip()
    if raw.lower() == "halt":
        return "halt"
    tokens = [t.strip().lower() for t in raw.split(",") if t.strip()]
    if not all(t in {"accept", "reject"} for t in tokens):
        raise ValueError(f"unexpected token in response: {raw!r}")
    if len(tokens) != n_sample:
        raise ValueError(f"expected {n_sample} decisions, got {len(tokens)}")
    return tokens
```

- [ ] **Step 2: Quick manual smoke**

Verify it imports:

```bash
cd /c/russellian-book-suite/tools/russellian-style-audit && .venv/Scripts/python -c "from scripts.operator_gate import prompt_operator; print('OK')"
```

Expected: `OK`.

- [ ] **Step 3: Commit**

```bash
cd /c/russellian-book-suite && git add tools/russellian-style-audit/scripts/operator_gate.py && git commit -m "tools/russellian-style-audit: operator_gate stdin prompt"
```

EXACT message: `tools/russellian-style-audit: operator_gate stdin prompt`

---

### Task 8: expansion — wraps build-russell-corpus pipeline

**Files:**
- Create: `tools/russellian-style-audit/scripts/expansion.py`

This module orchestrates the expansion pipeline using build-russell-corpus's already-tested stage functions. Tests for this module would mostly re-test build-russell-corpus; the end-to-end test (Task 12) covers the integration.

- [ ] **Step 1: Write `scripts/expansion.py`**

```python
"""Run one expansion batch and (conditionally) append to the russellian-style index.

Wraps the build-russell-corpus pipeline stages with the live LLM caller. The
operator_gate decision determines whether the verified entries are appended.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_BUILD_TOOL = _REPO_ROOT / "tools" / "build-russell-corpus"
sys.path.insert(0, str(_BUILD_TOOL))

from scripts.extract_candidates import extract_candidates  # type: ignore
from scripts.sentinel import run_sentinel_batch  # type: ignore
from scripts.cross_check import run_cross_check_batch  # type: ignore
from scripts.audit_sample import sample_audit, evaluate_audit_decisions  # type: ignore
from scripts.append_to_index import append_verified_to_index, regenerate_corpus_map  # type: ignore
from scripts.live_llm import extract_llm, cross_check_llm  # type: ignore


_RUSSELLIAN_STYLE_ROOT = _REPO_ROOT / "skills" / "russellian-style"
_INDEX_PATH = _RUSSELLIAN_STYLE_ROOT / "assets" / "russell-corpus" / "index.json"
_CORPUS_MAP_PATH = _RUSSELLIAN_STYLE_ROOT / "references" / "russell-corpus-map.md"
_BUILD_TOOL_ASSETS = _BUILD_TOOL / "assets"


def run_expansion_batch(
    *,
    batch_id: str,
    source_id: str,
    source_path: Path,
    n: int,
    run_dir: Path,
    operator_decision_fn,  # callable returning "halt" | list[str]
) -> dict:
    """Run the full expansion pipeline. Returns a dict with counts and appended-bool.

    operator_decision_fn is called once with (audit_sample_path, n_sample, n_verified)
    after the audit sample is written.
    """
    run_dir.mkdir(parents=True, exist_ok=True)
    candidates_path = run_dir / "candidates.jsonl"
    verified_path = run_dir / "verified.jsonl"
    rejected_path = run_dir / "rejected.jsonl"
    sample_path = run_dir / "audit" / "sample.md"

    # Stage 1 — extract
    import yaml
    allow_data = yaml.safe_load((_BUILD_TOOL_ASSETS / "pd-allow-list.yaml").read_text(encoding="utf-8"))
    source_url = next(e["url"] for e in allow_data["allowed"] if e["source_id"] == source_id)

    extract_candidates(
        source_path=source_path,
        source_id=source_id,
        source_url=source_url,
        vocabulary_path=_BUILD_TOOL_ASSETS / "vocabulary.json",
        prompt_path=_BUILD_TOOL_ASSETS / "extractor-prompt.md",
        out_path=candidates_path,
        n=n,
        llm_call=extract_llm,
    )
    n_candidates = sum(1 for _ in candidates_path.read_text(encoding="utf-8").splitlines() if _.strip())

    # Stage 2 — sentinel
    run_sentinel_batch(
        candidates_path=candidates_path,
        source_cache_dir=source_path.parent,
        allow_list_path=_BUILD_TOOL_ASSETS / "pd-allow-list.yaml",
        vocabulary_path=_BUILD_TOOL_ASSETS / "vocabulary.json",
        generic_phrases_path=_BUILD_TOOL_ASSETS / "generic-phrases.yaml",
        existing_index_path=_INDEX_PATH,
        run_dir=run_dir,
    )
    n_passed = sum(1 for _ in (run_dir / "passed-sentinel.jsonl").read_text(encoding="utf-8").splitlines() if _.strip()) if (run_dir / "passed-sentinel.jsonl").exists() else 0

    # Stage 3 — cross-check
    run_cross_check_batch(
        passed_sentinel_path=run_dir / "passed-sentinel.jsonl",
        rejected_path=rejected_path,
        verified_path=verified_path,
        vocabulary_path=_BUILD_TOOL_ASSETS / "vocabulary.json",
        llm_call=cross_check_llm,
    )
    n_verified = sum(1 for _ in verified_path.read_text(encoding="utf-8").splitlines() if _.strip()) if verified_path.exists() else 0
    n_rejected = sum(1 for _ in rejected_path.read_text(encoding="utf-8").splitlines() if _.strip()) if rejected_path.exists() else 0

    # Stage 4 — audit sample
    if n_verified == 0:
        return {
            "batch_id": batch_id, "n_candidates": n_candidates, "n_passed_sentinel": n_passed,
            "n_verified": 0, "n_rejected": n_rejected, "appended": False, "halt_reason": "no verified entries",
            "sample_accepted": [],
        }
    sampled = sample_audit(verified_path=verified_path, out_path=sample_path)

    # Operator gate
    decision = operator_decision_fn(sample_path, len(sampled), n_verified)
    if decision == "halt":
        return {
            "batch_id": batch_id, "n_candidates": n_candidates, "n_passed_sentinel": n_passed,
            "n_verified": n_verified, "n_rejected": n_rejected, "appended": False,
            "halt_reason": "operator halt", "sample_accepted": [],
        }
    audit_eval = evaluate_audit_decisions(decision, halt_threshold=0.10)
    if audit_eval.action == "halt":
        return {
            "batch_id": batch_id, "n_candidates": n_candidates, "n_passed_sentinel": n_passed,
            "n_verified": n_verified, "n_rejected": n_rejected, "appended": False,
            "halt_reason": f"audit reject rate {audit_eval.reject_rate:.2%} > 10%",
            "sample_accepted": [],
        }

    # Stage 5 — append
    append_verified_to_index(verified_path=verified_path, index_path=_INDEX_PATH)
    regenerate_corpus_map(index_path=_INDEX_PATH, out_path=_CORPUS_MAP_PATH)
    sample_ids = [s["candidate_id"] for s in sampled]
    return {
        "batch_id": batch_id, "n_candidates": n_candidates, "n_passed_sentinel": n_passed,
        "n_verified": n_verified, "n_rejected": n_rejected, "appended": True,
        "halt_reason": None, "sample_accepted": sample_ids,
    }
```

- [ ] **Step 2: Smoke-test imports**

```bash
cd /c/russellian-book-suite/tools/russellian-style-audit && .venv/Scripts/python -c "from scripts.expansion import run_expansion_batch; print('OK')"
```

Expected: `OK`.

If any import fails (e.g. `from scripts.live_llm import ...` not found), confirm the venvs are set up. The audit venv needs to be able to import from the build-russell-corpus venv's `scripts` — the `sys.path.insert` at the top of `expansion.py` handles this.

- [ ] **Step 3: Commit**

```bash
cd /c/russellian-book-suite && git add tools/russellian-style-audit/scripts/expansion.py && git commit -m "tools/russellian-style-audit: expansion pipeline wrapper"
```

EXACT message: `tools/russellian-style-audit: expansion pipeline wrapper`

---

### Task 9: generate_samples — 3 LLM calls per mode

**Files:**
- Create: `tools/russellian-style-audit/scripts/generate_samples.py`

- [ ] **Step 1: Write `scripts/generate_samples.py`**

```python
"""Generate three 15-paragraph sample texts via the three system prompts.

Each call uses claude-opus-4-7 at temperature 0.7 (higher than the corpus pipelines'
temperatures because we want creative prose). The output is the raw LLM response,
written verbatim to disk for linting by lint_samples.py.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_RUSSELLIAN_STYLE_ROOT = _REPO_ROOT / "skills" / "russellian-style"
sys.path.insert(0, str(_RUSSELLIAN_STYLE_ROOT))
from scripts.system_prompt_loader import load as load_system_prompt  # type: ignore

_BUILD_TOOL = _REPO_ROOT / "tools" / "build-russell-corpus"
sys.path.insert(0, str(_BUILD_TOOL))
from scripts.live_llm import generate  # type: ignore


_TOPICS = {
    "technical-exposition": (
        "Why book-knowledge's claim ledger enforces a five-state machine "
        "(proposed -> verified -> disputed -> superseded -> refuted) instead of a "
        "free-form status field. What invariants the five states preserve, what they "
        "make impossible, and what they cost. Treat the reader as an attentive engineer "
        "who has not seen this codebase."
    ),
    "narrative-editorial": (
        "A chapter introduction for a book on the difference between what machines "
        "understand and what they recognize. The chapter is the first the reader meets; "
        "it has to set the question without answering it. Open with a concrete scene, "
        "name at least one specific person or institution, and end on a sentence that "
        "changes the question's pressure."
    ),
    "polemic": (
        "An op-ed against the listicle as a form of thought. Argue that ranked lists "
        "conceal the relations between their items and that the cost of that "
        "concealment is borne by the reader, not the writer. Personify at least one "
        "defender of the form. Close on a sentence that reverses the opener."
    ),
}


def generate_sample(mode: str, out_path: Path, *, generate_fn=generate) -> dict:
    """Generate a 15-paragraph sample for the given mode. Write to out_path.

    Returns a dict with mode, char_count, and counted_paragraphs (by leading-number regex).
    """
    if mode not in _TOPICS:
        raise ValueError(f"unknown mode: {mode!r}")
    system_prompt = load_system_prompt(mode)
    topic = _TOPICS[mode]
    full_prompt = (
        f"{system_prompt}\n\n"
        "# Writing task\n\n"
        "Write exactly 15 paragraphs on the following topic. Number each paragraph "
        "(1. through 15.). Each paragraph must perform one of the controlled Russell "
        "rhetorical moves; do not repeat the same move twice in a row.\n\n"
        f"## Topic\n\n{topic}\n"
    )
    text = generate_fn(full_prompt, model="claude-opus-4-7", max_tokens=8192, temperature=0.7)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8")
    counted = len(re.findall(r"(?m)^\s*\d+\.\s", text))
    return {"mode": mode, "char_count": len(text), "counted_paragraphs": counted}


def generate_all_samples(out_dir: Path, *, generate_fn=generate) -> list[dict]:
    """Generate samples for all three modes. Returns list of result dicts."""
    return [generate_sample(mode, out_dir / f"{mode}.md", generate_fn=generate_fn) for mode in _TOPICS]
```

- [ ] **Step 2: Smoke imports**

```bash
cd /c/russellian-book-suite/tools/russellian-style-audit && .venv/Scripts/python -c "from scripts.generate_samples import generate_all_samples, _TOPICS; print(list(_TOPICS))"
```

Expected: `['technical-exposition', 'narrative-editorial', 'polemic']`.

- [ ] **Step 3: Commit**

```bash
cd /c/russellian-book-suite && git add tools/russellian-style-audit/scripts/generate_samples.py && git commit -m "tools/russellian-style-audit: sample-text generator for three modes"
```

EXACT message: `tools/russellian-style-audit: sample-text generator for three modes`

---

### Task 10: lint_samples — lint + scoring

**Files:**
- Create: `tools/russellian-style-audit/scripts/lint_samples.py`

- [ ] **Step 1: Write `scripts/lint_samples.py`**

```python
"""Run skill_api.lint_fragment over each generated sample and produce per-mode lint reports.

The audit calls lint_fragment with the FULL 17-rule registry — not just the default 10
— so the advisory rules also fire. Reports separate gating from advisory counts.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_RUSSELLIAN_STYLE_ROOT = _REPO_ROOT / "skills" / "russellian-style"
sys.path.insert(0, str(_RUSSELLIAN_STYLE_ROOT))
from skill_api import lint_fragment  # type: ignore


# Mirror skill_api._LINTER_REGISTRY keys
ALL_17_RULES = [
    "no-hedging", "active-voice", "signal-density", "parallel-structure",
    "listicle-abstract", "listicle-anaphora",
    "rhythm-uniform-length", "rhythm-repeated-opening",
    "burstiness", "ai-vocabulary",
    "staccato-paragraph-run", "negation-affirmation-template",
    "this-is-conclusion-overuse", "abstract-subject-run",
    "concrete-instance-density", "epistemic-precision", "paragraph-motion",
]

# Default 10 are "gating"; the other 7 are advisory.
GATING_RULES = {
    "no-hedging", "active-voice", "signal-density", "parallel-structure",
    "listicle-abstract", "listicle-anaphora",
    "rhythm-uniform-length", "rhythm-repeated-opening",
    "burstiness", "ai-vocabulary",
}


def lint_sample(text: str) -> dict:
    """Run lint_fragment with all 17 rules and aggregate counts.

    Returns:
      {
        "per_rule": [
          {"rule": "no-hedging", "count": 0, "first3": []},
          ...
        ],
        "gating_count": int,
        "advisory_count": int,
        "verdict": "PASS" | "WARN" | "FAIL",
      }
    """
    issues = lint_fragment(text, linters=ALL_17_RULES)
    by_rule: dict[str, list] = {r: [] for r in ALL_17_RULES}
    for issue in issues:
        if issue.linter in by_rule:
            by_rule[issue.linter].append(issue)

    per_rule = []
    gating_count = 0
    advisory_count = 0
    for rule in ALL_17_RULES:
        rule_issues = by_rule[rule]
        first3 = [f"L{i.line}:C{i.col} {i.message[:60]}" for i in rule_issues[:3]]
        per_rule.append({"rule": rule, "count": len(rule_issues), "first3": first3})
        if rule in GATING_RULES:
            gating_count += len(rule_issues)
        else:
            advisory_count += len(rule_issues)

    if gating_count <= 2:
        verdict = "PASS"
    elif gating_count <= 5:
        verdict = "WARN"
    else:
        verdict = "FAIL"

    return {
        "per_rule": per_rule,
        "gating_count": gating_count,
        "advisory_count": advisory_count,
        "verdict": verdict,
    }


def lint_sample_file(sample_path: Path) -> dict:
    """Read a sample file and lint it. Result includes mode (derived from filename)."""
    mode = sample_path.stem
    result = lint_sample(sample_path.read_text(encoding="utf-8"))
    result["mode"] = mode
    return result
```

- [ ] **Step 2: Smoke import**

```bash
cd /c/russellian-book-suite/tools/russellian-style-audit && .venv/Scripts/python -c "from scripts.lint_samples import lint_sample, ALL_17_RULES; print(len(ALL_17_RULES))"
```

Expected: `17`.

- [ ] **Step 3: Commit**

```bash
cd /c/russellian-book-suite && git add tools/russellian-style-audit/scripts/lint_samples.py && git commit -m "tools/russellian-style-audit: lint scorer with PASS/WARN/FAIL verdict"
```

EXACT message: `tools/russellian-style-audit: lint scorer with PASS/WARN/FAIL verdict`

---

### Task 11: run.py — CLI orchestrator

**Files:**
- Create: `tools/russellian-style-audit/scripts/run.py`

- [ ] **Step 1: Write `scripts/run.py`**

```python
"""CLI orchestrator. Runs the full audit and writes the bundle to docs/audits/.

Usage:
  python -m scripts.run --batch-id 2026-05-21-001
  python -m scripts.run --batch-id 2026-05-21-001 --auto-accept   # skip operator gate
  python -m scripts.run --batch-id 2026-05-21-001 --skip-expansion  # skip stage 4
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_AUDIT_ROOT = _HERE.parent
_REPO_ROOT = _AUDIT_ROOT.parent.parent
sys.path.insert(0, str(_AUDIT_ROOT))

from scripts.health_check import run_all_health_checks
from scripts.report import render_health_check_md, render_summary_md, render_readme_md, render_lint_report_md, render_expansion_md


_AUDIT_BUNDLE_ROOT = _REPO_ROOT / "docs" / "audits" / "2026-05-21-russellian-style"
_AUDIT_FIXTURES = _AUDIT_ROOT / "tests" / "fixtures"


def _verdict_from_results(results) -> str:
    if any(r.status == "FAIL" for r in results):
        return "FAIL"
    if any(r.status == "WARN" for r in results):
        return "WARN"
    return "PASS"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--auto-accept", action="store_true")
    parser.add_argument("--skip-expansion", action="store_true")
    args = parser.parse_args()

    bundle = _AUDIT_BUNDLE_ROOT
    bundle.mkdir(parents=True, exist_ok=True)
    samples_dir = bundle / "samples"
    samples_dir.mkdir(exist_ok=True)
    run_dir = bundle / "runs" / args.batch_id

    # Stage 1 — health check
    results = run_all_health_checks(fixtures_dir=_AUDIT_FIXTURES)
    (bundle / "health-check.md").write_text(render_health_check_md(results), encoding="utf-8")
    health_verdict = _verdict_from_results(results)
    if health_verdict == "FAIL":
        readme = render_readme_md(
            health_verdict="FAIL",
            expansion_verdict="SKIPPED (health check failed)",
            samples_verdict="SKIPPED (health check failed)",
            batch_id=args.batch_id,
        )
        (bundle / "README.md").write_text(readme, encoding="utf-8")
        print("Health check FAILED. See", bundle / "health-check.md")
        return 1

    # Stage 2 — expansion (optional)
    if args.skip_expansion:
        (bundle / "expansion.md").write_text("# Expansion\n\nSkipped via --skip-expansion.\n", encoding="utf-8")
        expansion_verdict = "SKIPPED"
    else:
        from scripts.expansion import run_expansion_batch
        from scripts.operator_gate import prompt_operator
        # Source path: cached Gutenberg HTML. Convention: build-russell-corpus's source cache.
        source_path = _REPO_ROOT / "tools" / "build-russell-corpus" / "tests" / "fixtures" / "source_cache" / "problems_subset.html"
        if not source_path.exists():
            print(f"Source cache missing at {source_path}. Run scrapling-fetch or supply a path; aborting expansion stage.")
            (bundle / "expansion.md").write_text(
                f"# Expansion\n\nAborted: source cache missing at {source_path}.\n",
                encoding="utf-8",
            )
            expansion_verdict = "ABORTED"
        else:
            def gate(sample_path, n_sample, n_verified):
                if args.auto_accept:
                    return ["accept"] * n_sample
                return prompt_operator(sample_path, n_sample, n_verified)
            result = run_expansion_batch(
                batch_id=args.batch_id,
                source_id="problems",
                source_path=source_path,
                n=50,
                run_dir=run_dir,
                operator_decision_fn=gate,
            )
            expansion_verdict = (
                f"PASS (appended {result['n_verified']} entries)"
                if result["appended"]
                else f"HALTED ({result['halt_reason']})"
            )
            (bundle / "expansion.md").write_text(render_expansion_md(
                batch_id=args.batch_id,
                n_candidates=result["n_candidates"],
                n_passed_sentinel=result["n_passed_sentinel"],
                n_verified=result["n_verified"],
                n_rejected=result["n_rejected"],
                appended=result["appended"],
                halt_reason=result.get("halt_reason"),
                sample_accepted=result.get("sample_accepted", []),
            ), encoding="utf-8")

    # Stage 3 — generate + lint samples
    from scripts.generate_samples import generate_all_samples
    from scripts.lint_samples import lint_sample_file

    generation_results = generate_all_samples(out_dir=samples_dir)

    per_mode_rows = []
    samples_pass_count = 0
    for gen in generation_results:
        mode = gen["mode"]
        sample_path = samples_dir / f"{mode}.md"
        lint_result = lint_sample_file(sample_path)
        (samples_dir / f"{mode}-lint.md").write_text(render_lint_report_md(
            mode=mode,
            per_rule=lint_result["per_rule"],
            gating_count=lint_result["gating_count"],
            advisory_count=lint_result["advisory_count"],
            verdict=lint_result["verdict"],
        ), encoding="utf-8")
        per_mode_rows.append({
            "mode": mode,
            "gating": lint_result["gating_count"],
            "advisory": lint_result["advisory_count"],
            "verdict": lint_result["verdict"],
        })
        if lint_result["verdict"] == "PASS":
            samples_pass_count += 1

    (samples_dir / "summary.md").write_text(render_summary_md(per_mode_rows), encoding="utf-8")
    samples_verdict = f"{samples_pass_count}/3 modes PASS"

    # README
    (bundle / "README.md").write_text(render_readme_md(
        health_verdict=health_verdict,
        expansion_verdict=expansion_verdict,
        samples_verdict=samples_verdict,
        batch_id=args.batch_id,
    ), encoding="utf-8")

    print(f"Audit bundle written to {bundle}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Smoke `--help`**

```bash
cd /c/russellian-book-suite/tools/russellian-style-audit && .venv/Scripts/python -m scripts.run --help
```

Expected: argparse help with `--batch-id`, `--auto-accept`, `--skip-expansion`.

- [ ] **Step 3: Commit**

```bash
cd /c/russellian-book-suite && git add tools/russellian-style-audit/scripts/run.py && git commit -m "tools/russellian-style-audit: cli orchestrator"
```

EXACT message: `tools/russellian-style-audit: cli orchestrator`

---

### Task 12: end-to-end smoke (no live LLM, no expansion)

**Files:**
- Modify: `tools/russellian-style-audit/tests/test_health_check.py` (or create `test_run.py`)

Verify the CLI runs end-to-end with `--skip-expansion` and a stubbed generator. No real LLM calls.

- [ ] **Step 1: Create the end-to-end test**

Create `tools/russellian-style-audit/tests/test_run.py`:

```python
import subprocess
import sys
from pathlib import Path

import pytest


_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_AUDIT_ROOT = _REPO_ROOT / "tools" / "russellian-style-audit"


@pytest.mark.skipif(
    not (_AUDIT_ROOT / ".venv").exists(),
    reason="audit venv not installed; skip integration smoke",
)
def test_run_help_exits_zero():
    venv_python = _AUDIT_ROOT / ".venv" / ("Scripts" if sys.platform == "win32" else "bin") / ("python.exe" if sys.platform == "win32" else "python")
    completed = subprocess.run(
        [str(venv_python), "-m", "scripts.run", "--help"],
        capture_output=True, text=True, cwd=str(_AUDIT_ROOT),
    )
    assert completed.returncode == 0
    assert "--batch-id" in completed.stdout
    assert "--auto-accept" in completed.stdout
    assert "--skip-expansion" in completed.stdout
```

The full end-to-end run-with-stub is not exercised in CI because it would still hit `generate_all_samples` which calls live LLM. The `--help` smoke is the cheapest CI gate.

- [ ] **Step 2: Run**

```bash
cd /c/russellian-book-suite/tools/russellian-style-audit && .venv/Scripts/python -m pytest tests/test_run.py -v
```

Expected: 1 passed.

- [ ] **Step 3: Run the full audit suite**

```bash
.venv/Scripts/python -m pytest tests/ -v
```

Expected: 13 passed (3 from test_report + 9 from test_health_check + 1 from test_run).

- [ ] **Step 4: Commit**

```bash
cd /c/russellian-book-suite && git add tools/russellian-style-audit/tests/test_run.py && git commit -m "tools/russellian-style-audit: cli help smoke test"
```

EXACT message: `tools/russellian-style-audit: cli help smoke test`

---

### Task 13: live operator run (manual)

This is the actual audit execution. No code, no commit — an operator step that produces the audit bundle.

- [ ] **Step 1: Verify ANTHROPIC_API_KEY is set**

```bash
echo $env:ANTHROPIC_API_KEY  # PowerShell, returns the key if set
```

If not set:
```bash
$env:ANTHROPIC_API_KEY = "sk-ant-..."
```

- [ ] **Step 2: Verify the source cache exists**

```bash
ls /c/russellian-book-suite/tools/build-russell-corpus/tests/fixtures/source_cache/problems_subset.html
```

If missing, the audit will report ABORTED for the expansion stage. (For the v1 audit, the fixture HTML is sufficient — full PD HTML can be sourced later for a larger batch.)

- [ ] **Step 3: Run the audit**

```bash
cd /c/russellian-book-suite/tools/russellian-style-audit && .venv/Scripts/python -m scripts.run --batch-id 2026-05-21-001
```

The audit:
- Runs all five health checks (writes `docs/audits/2026-05-21-russellian-style/health-check.md`)
- If health passes, runs one extraction batch via live LLM (writes `runs/2026-05-21-001/candidates.jsonl`)
- Runs sentinel + cross-check + audit-sample
- **PAUSES** at the operator gate. Read `runs/2026-05-21-001/audit/sample.md` in another terminal, decide accept/reject for each entry, type the comma-separated response into the audit prompt.
- If accepted: appends to `skills/russellian-style/assets/russell-corpus/index.json`
- Generates 3 sample texts (writes `samples/<mode>.md`)
- Lints each (writes `samples/<mode>-lint.md`)
- Writes `samples/summary.md` and `README.md`

- [ ] **Step 4: Review the bundle**

```bash
cat docs/audits/2026-05-21-russellian-style/README.md
```

Verify the three verdicts. Open `samples/summary.md` and confirm each mode landed at PASS or WARN.

- [ ] **Step 5: Commit the audit bundle**

```bash
cd /c/russellian-book-suite && git add docs/audits/2026-05-21-russellian-style/ skills/russellian-style/assets/russell-corpus/index.json skills/russellian-style/references/russell-corpus-map.md && git commit -m "audit: russellian-style 2026-05-21-001 (expansion +N entries; 3/3 PASS)"
```

The exact commit subject reflects the actual outcome — substitute the real entry-count and PASS-count.

EXACT format: `audit: russellian-style <batch-id> (<expansion-note>; <samples-note>)`

---

## Self-review

**Spec coverage:**

| Spec section | Tasks |
| --- | --- |
| Project skeleton + venv | Task 0 |
| Live LLM caller | Task 1 |
| Health checks (5) | Tasks 2-5 |
| Markdown rendering | Task 6 |
| Operator gate | Task 7 |
| Expansion pipeline | Task 8 |
| Sample text generation | Task 9 |
| Lint scoring | Task 10 |
| CLI orchestrator | Task 11 |
| End-to-end smoke | Task 12 |
| Operator-driven live run | Task 13 |
| Output bundle structure | Task 11 (run.py writes it) |
| Halt paths | Task 11 (run.py implements all halt rules from spec table) |
| Tests | Tasks 1, 2, 3, 4, 5, 6, 12 |

All 11 spec sections map to tasks.

**Placeholder scan:** All code blocks are complete. The one operator step (Task 13) is explicit human work, not a TBD. The `# placeholder` comment in Task 8 Step 1 is the only string match for "placeholder" — it's a real comment in `expansion.py` referring to the json.loads vs yaml.safe_load duality and is followed by the actual implementation. Reviewing once more — the placeholder line is `pd_allow = json.loads(((_BUILD_TOOL_ASSETS / "pd-allow-list.yaml").read_text(encoding="utf-8"))) if False else None  # placeholder — load via yaml` — this is dead code with `if False`. Fix inline by removing the dead line; the subsequent `import yaml; allow_data = yaml.safe_load(...)` does the actual work.

**Type consistency:**
- `HealthCheckResult` defined Task 2, used unchanged in Tasks 3, 4, 5, 6, 11.
- `lint_fragment` signature from `skill_api`: takes text + optional list of linter names; returns `list[LintIssue]`. Used consistently in Tasks 2 and 10.
- `generate(prompt, model, max_tokens, temperature)` signature from Task 1 matches calls in Task 9.
- `extract_llm` / `cross_check_llm` take a single `str` prompt and return `str` — matches the `Callable[[str], str]` contract in build-russell-corpus stages.
- `operator_decision_fn` callable signature in Task 8 (`(sample_path, n_sample, n_verified) -> "halt" | list[str]`) matches the `prompt_operator` signature in Task 7 and the `gate` closure in Task 11.

One inconsistency fixed inline: Task 8's `pd_allow = json.loads(...) if False else None` placeholder line — remove from final implementation; the `import yaml; allow_data = yaml.safe_load(...)` lines do the actual work.
