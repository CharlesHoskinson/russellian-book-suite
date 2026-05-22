# russellian-style end-to-end audit (health check + live corpus expansion + 3 sample texts)

Status: draft
Owner: russellian-style

## Problem

The russellian-style skill has the build-russell-corpus tool merged on `main` (PR #121) but the corpus has not yet been expanded live. The skill's runtime surface (12 linters, 3 system prompts, public `lint_fragment` API, corpus retrieval) has not been exercised end-to-end against a live LLM since the merge, and the integration with `book-compose`, `book-review`, `book-qa`, and `humanizer` has not been re-validated against the latest API. The user wants assurance that the skill is healthy, that the upgrade pipeline produces real value, and that the generation contract still produces Russellian prose.

This spec describes a single auditing operation that runs (1) a deterministic health check across the skill's tests and integration points, (2) one live corpus-expansion batch against a public-domain Russell source with an operator gate, and (3) three 15-paragraph sample text generations under the three system prompts, lint-scored and reported.

## Goals

- Confirm the russellian-style pytest suite passes on the current commit.
- Confirm the public API (`lint_fragment`, `LintIssue`, `API_VERSION`) is reachable from the venvs of `book-compose`, `book-review`, `book-qa`, and `humanizer`.
- Confirm the 50-entry corpus is retrievable and produces sensible exemplars for common rhetorical-mode tags.
- Confirm the three system prompts (technical-exposition, narrative-editorial, polemic) load without error.
- Run one live corpus-expansion batch (n=50, source=problems) end-to-end and append the verified entries to `skills/russellian-style/assets/russell-corpus/index.json`, contingent on operator approval of the audit sample.
- Generate three 15-paragraph sample texts (one per mode) via a live LLM and lint each against all 17 registered rules.
- Produce a single committed audit bundle at `docs/audits/2026-05-21-russellian-style/` with a top-level verdict.

## Non-goals

- Modifying the russellian-style skill code, linter rules, or system prompts. Only `assets/russell-corpus/index.json` and `references/russell-corpus-map.md` are mutated (by the expansion stage).
- Running the corpus expansion against multiple PD sources. One source (`problems`) is sufficient as a smoke-test of the live pipeline.
- Generating sample texts both before and after the expansion. Only the after-expansion samples are produced; subjective comparison against a memory of pre-expansion samples is out of scope.
- Modifying the build-russell-corpus tool's stage scripts. Only a thin live-LLM wrapper is added.
- Replacing or extending CI. The audit is a one-shot operator-invoked run, not a recurring check.

## Where it lives

A new one-shot script package under `tools/russellian-style-audit/` with its own `.venv` and `pyproject.toml`, plus one new module `tools/build-russell-corpus/scripts/live_llm.py` added to the existing tool. The audit is invoked from a single CLI:

```
python -m tools.russellian-style-audit.run --batch-id 2026-05-21-001
```

Audit outputs land under `docs/audits/2026-05-21-russellian-style/`. The audit is committable as-is.

```
tools/russellian-style-audit/
├── pyproject.toml
├── scripts/
│   ├── __init__.py
│   ├── run.py                  # CLI orchestrator
│   ├── health_check.py         # five deterministic checks
│   ├── expansion.py            # wraps build-russell-corpus pipeline
│   ├── generate_samples.py     # three LLM calls per system prompt
│   ├── lint_samples.py         # runs skill_api.lint_fragment on each sample
│   ├── report.py               # markdown rendering
│   └── operator_gate.py        # blocking input for the expansion approval
└── tests/
    ├── __init__.py
    ├── test_health_check.py
    └── test_report.py
```

```
tools/build-russell-corpus/scripts/live_llm.py    # new file added to existing tool
```

```
docs/audits/2026-05-21-russellian-style/
├── README.md                   # top-level verdict + index
├── health-check.md             # five health-check rows
├── expansion.md                # batch summary (or halt note)
├── samples/
│   ├── technical-exposition.md
│   ├── technical-exposition-lint.md
│   ├── narrative-editorial.md
│   ├── narrative-editorial-lint.md
│   ├── polemic.md
│   ├── polemic-lint.md
│   └── summary.md
└── runs/<batch-id>/            # full expansion ledgers (preserved)
```

## Live LLM caller

New file `tools/build-russell-corpus/scripts/live_llm.py`:

```python
from __future__ import annotations
import os
from pathlib import Path
from anthropic import Anthropic
import yaml

_CONFIG_PATH = Path(__file__).parent.parent / "assets" / "llm-config.yaml"


def _load_config() -> dict:
    return yaml.safe_load(_CONFIG_PATH.read_text(encoding="utf-8"))


def _client() -> Anthropic:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY not set in environment")
    return Anthropic()


def extract_llm(prompt: str) -> str:
    cfg = _load_config()["extract"]
    msg = _client().messages.create(
        model=cfg["model_id"],
        max_tokens=cfg["max_tokens"],
        temperature=cfg["temperature"],
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in msg.content if hasattr(block, "text"))


def cross_check_llm(prompt: str) -> str:
    cfg = _load_config()["cross_check"]
    msg = _client().messages.create(
        model=cfg["model_id"],
        max_tokens=cfg["max_tokens"],
        temperature=cfg["temperature"],
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in msg.content if hasattr(block, "text"))


def generate(prompt: str, *, model: str = "claude-opus-4-7",
             max_tokens: int = 8192, temperature: float = 0.7) -> str:
    msg = _client().messages.create(
        model=model, max_tokens=max_tokens, temperature=temperature,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in msg.content if hasattr(block, "text"))
```

The `anthropic` SDK is added as a `runtime` extra in `tools/build-russell-corpus/pyproject.toml` so test runs that pin `dev` are unaffected. No test in `tools/build-russell-corpus/tests/` calls these functions directly; one new test `test_live_llm.py` verifies the module imports without `ANTHROPIC_API_KEY` set, and that calling `extract_llm("test")` raises a clear `RuntimeError` rather than failing on a network call.

## Health-check phase

Pure deterministic, no LLM. Runs five checks in sequence:

| Check | Implementation | Pass criterion |
| --- | --- | --- |
| `pytest_suite` | `subprocess.run(["python", "-m", "pytest", "skills/russellian-style/tests/", "-q"])` | Exit code 0 |
| `api_smoke` | Import `skill_api.lint_fragment`; call against three fixture texts (clean, hedged, listicle-abstract); inspect returned `LintIssue` shape | Returns `list[LintIssue]`; clean returns `[]`; hedged returns >=1 issue with `linter == "no-hedging"`; listicle returns >=1 issue with `linter == "listicle-abstract"` |
| `composes_with` | For each consumer in [`book-compose`, `book-review`, `book-qa`, `humanizer`], invoke `<consumer>/.venv/Scripts/python -c "from russellian_style.skill_api import lint_fragment, API_VERSION; print(API_VERSION)"` | All four prints succeed; each reports `(0, 1)` |
| `corpus_retrieval` | Call `retrieve_corpus_anchor.retrieve(tag=t)` for `t` in [`antithesis`, `concrete_example`, `concession`, `domain_contrast`, `paragraph_turn`] | Each call returns a list of >=1 anchor with non-empty `source_id`, `line_hint`, `rhetorical_move` |
| `system_prompts` | For each `mode` in [`technical-exposition`, `narrative-editorial`, `polemic`], call `system_prompt_loader.load(mode)` and assert the returned string contains the literal substring `"Structural mandates"` (a section header present in all three) | All three return non-empty strings with the mandate header |

Each check produces a row in `health-check.md`:

```
| Check | Status | Evidence |
| --- | --- | --- |
| pytest_suite | PASS | 84 passed in 12.31s |
| api_smoke | PASS | 3 fixture texts produced expected LintIssue counts |
...
```

**Halt rule:** if any check returns FAIL, the audit halts before stage 4 (live LLM stages). No API credits are spent on a broken skill. The audit emits a `README.md` with the FAIL verdict and exits non-zero.

The `composes_with` check requires that the four consumer skills have venvs installed with `russellian-style` linked. The audit script discovers each venv path via the convention `skills/<consumer>/.venv/Scripts/python.exe` (Windows) or `skills/<consumer>/.venv/bin/python` (POSIX). If any venv is missing, the check reports WARN (not FAIL) — the skill itself may still be healthy; the consumer venv may just not be installed yet on the operator's machine. Operator inspects the WARN row and decides whether to install or skip.

## Expansion batch run

The audit calls into the existing build-russell-corpus pipeline with `live_llm.extract_llm` and `live_llm.cross_check_llm` bound. The batch parameters:

- `source_id`: `problems`
- `n`: 50 candidate paragraphs
- `batch_id`: passed via CLI (e.g. `2026-05-21-001`)
- Source path: the cached Project Gutenberg HTML at the URL pinned in `assets/pd-allow-list.yaml` for `problems`. If the cache is empty, the audit downloads it once via `scrapling-fetch` (one-time prerequisite — surfaced as a separate "preflight" step in `expansion.md` if needed).

Five stages run in order:

1. `extract_candidates` with live extractor → `runs/<batch-id>/candidates.jsonl`
2. `run_sentinel_batch` → `passed-sentinel.jsonl`, `rejected.jsonl`, `pending-tag.jsonl`, `proposed-tags.jsonl`
3. `run_cross_check_batch` with live cross-check → `verified.jsonl`, more `rejected.jsonl` appends
4. `sample_audit` → `runs/<batch-id>/audit/sample.md` (5% of verified, minimum 1)
5. Operator gate: see "Operator gate" below
6. (Conditional) `append_verified_to_index` + `regenerate_corpus_map` → mutates `skills/russellian-style/assets/russell-corpus/index.json` and `references/russell-corpus-map.md`

`expansion.md` records the per-stage counts (candidates / passed / rejected / verified) and a sample of accepted entries.

### Operator gate

After stage 4 emits `audit/sample.md`, the audit pauses with a blocking prompt to stdin:

```
Audit sample written to: docs/audits/2026-05-21-russellian-style/runs/2026-05-21-001/audit/sample.md
The sample contains N entries (5% of M verified). For each entry, mark accept or reject.

Reply with a comma-separated list of decisions in order — for example:
    accept,accept,reject

Or reply 'halt' to stop without appending any entries to the russellian-style index.

Decision:
```

The operator types their response in the terminal where the audit is running. If `halt`: stage 6 is skipped; `expansion.md` records a halt note; the audit proceeds to stage 5 (sample generation) using the pre-expansion corpus.

If the decisions parse as `accept`/`reject` tokens: `evaluate_audit_decisions(decisions, halt_threshold=0.10)` runs. If the reject rate exceeds 10%, the audit halts with a `halt-summary.md` and skips append. Otherwise stage 6 runs.

**Pre-baked alternative:** if the audit is invoked with `--auto-accept` (an explicit operator concession of trust), the operator gate is skipped and stage 6 runs unconditionally on whatever verified.jsonl contains. The audit's `expansion.md` records the `--auto-accept` flag was used. Default is interactive.

## Sample text generation

After expansion (whether or not the index was appended to), three calls to `live_llm.generate` produce one 15-paragraph text per mode. Each call uses:

- Model: `claude-opus-4-7`
- `max_tokens`: 8192
- Temperature: 0.7 (higher than extract's 0.3 — we want creative prose, not classification)

Each prompt is constructed as:

```
{{ system_prompt_loader.load(mode) }}

# Writing task

Write exactly 15 paragraphs on the following topic. Number each paragraph (1. through 15.).
Each paragraph must perform one of the controlled Russell rhetorical moves; do not repeat the
same move twice in a row.

## Topic

{{ topic_for_mode }}
```

Topics:

- `technical-exposition`: *"Why book-knowledge's claim ledger enforces a five-state machine (proposed → verified → disputed → superseded → refuted) instead of a free-form status field. What invariants the five states preserve, what they make impossible, and what they cost. Treat the reader as an attentive engineer who has not seen this codebase."*
- `narrative-editorial`: *"A chapter introduction for a book on the difference between what machines understand and what they recognize. The chapter is the first the reader meets; it has to set the question without answering it. Open with a concrete scene, name at least one specific person or institution, and end on a sentence that changes the question's pressure."*
- `polemic`: *"An op-ed against the listicle as a form of thought. Argue that ranked lists conceal the relations between their items and that the cost of that concealment is borne by the reader, not the writer. Personify at least one defender of the form. Close on a sentence that reverses the opener."*

Each generation lands at `docs/audits/2026-05-21-russellian-style/samples/<mode>.md` as the raw LLM output, verbatim. If the regex `r"^\s*\d+\."`-counted paragraph count is not 15, the audit emits a WARN row in `samples/summary.md` but accepts the output anyway and proceeds to linting. The LLM's deviation from the count is itself information about the generation contract's reliability.

## Linter scoring and report

For each `samples/<mode>.md`, `skill_api.lint_fragment(text, linters=ALL_17_RULES)` runs against the full registry from `_LINTER_REGISTRY`:

```
ALL_17_RULES = [
    "no-hedging", "active-voice", "signal-density", "parallel-structure",
    "listicle-abstract", "listicle-anaphora",
    "rhythm-uniform-length", "rhythm-repeated-opening",
    "burstiness", "ai-vocabulary",
    "staccato-paragraph-run", "negation-affirmation-template",
    "this-is-conclusion-overuse", "abstract-subject-run",
    "concrete-instance-density", "epistemic-precision", "paragraph-motion",
]
```

Results land at `samples/<mode>-lint.md`:

```
# Lint report — <mode>

## Per-rule counts

| Rule | Count | First 3 violations |
| --- | ---: | --- |
| no-hedging | 0 | — |
| active-voice | 2 | L4:1 ..., L12:1 ..., — |
| signal-density | 0 | — |
...

## Totals
- Gating violations: N (rules in default 10)
- Advisory violations: M (rules in advisory 7)

## Verdict
PASS (gating <= 2) | WARN (gating 3-5) | FAIL (gating > 5)
```

The roll-up `samples/summary.md`:

```
| Mode                 | Gating | Advisory | Verdict |
| ---                  | ---:   | ---:     | ---     |
| technical-exposition |     1  |       4  | PASS    |
| narrative-editorial  |     3  |       7  | WARN    |
| polemic              |     0  |       2  | PASS    |
```

The gating-violation thresholds (≤2 PASS, 3-5 WARN, >5 FAIL) are calibrated assumptions. The implementation plan validates them by running `lint_fragment` against a known-good Russell passage from the corpus and confirming the score lands in PASS range. If the calibration fails, the thresholds are adjusted in the plan, not in this spec.

## Output bundle

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

`README.md` is a one-pager with three verdicts (health-check, expansion, sample-texts), a one-paragraph summary of what happened, and a markdown index linking to each artifact. The bundle is committed as a single commit.

## Halt paths and error handling

| Trigger | Action |
| --- | --- |
| Health-check FAIL | Halt before stage 4; write `README.md` with FAIL verdict; exit non-zero. No API credits spent. |
| `ANTHROPIC_API_KEY` not set | Halt at stage 4; `expansion.md` records the missing env-var; exit non-zero. |
| Anthropic API auth or 5xx failure | Halt at the failing stage; the failure is captured verbatim in the relevant artifact (`expansion.md` or `samples/<mode>.md`); exit non-zero. |
| Operator halts at the expansion gate | Skip append; `expansion.md` notes the halt; continue to stage 5 with the pre-expansion corpus. |
| Audit-sample reject rate > 10% | Skip append; `halt-summary.md` written under `runs/<batch-id>/`; continue to stage 5 with the pre-expansion corpus. |
| Generation returns fewer than 15 paragraphs | Accept the output; emit a WARN row in `samples/summary.md`. |
| A single linter raises | Catch, log to `samples/<mode>-lint.md`, continue with other linters. Mirrors the existing defensive pattern in `skill_api._raw_findings_for_rule`. |
| `subprocess` invocation of consumer-skill venv fails (e.g. venv missing) | `composes_with` records WARN; audit continues. |

## Testing

The audit tool itself is mostly orchestration over already-tested components. Three new test files:

- `tools/russellian-style-audit/tests/test_health_check.py` — unit tests for each of the 5 health checks against fake or fixture skill state. Each check is a callable; tests pass synthetic inputs (a fake `skill_api` module, a fake corpus index, a fake system-prompt path) and assert PASS/WARN/FAIL outcomes.
- `tools/russellian-style-audit/tests/test_report.py` — tests the markdown-rendering functions in `report.py` against expected output strings.
- `tools/build-russell-corpus/tests/test_live_llm.py` — verifies `live_llm.py` imports without `ANTHROPIC_API_KEY` set; calling `extract_llm("test")` raises `RuntimeError` (not a network call). Patches `anthropic.Anthropic` for the "client is constructed" path so no real client is built.

The end-to-end audit run is operator-driven; no integration test exercises the full live path. CI runs the three new test files alongside the existing suites.

## Out of scope

- Modifying the russellian-style skill's linter modules or system prompts.
- Running corpus expansion against multiple PD sources.
- Comparing sample-text quality before and after expansion.
- Extending the audit to recurring CI execution.
- Migrating the existing 50 free-form `rhetorical_move` strings to the controlled vocabulary.

## Open questions

- The `composes_with` check assumes the four consumer skills have their venvs installed. On a fresh clone this isn't true (matches the `AGENTS.md` note about junction-linking venvs). The audit reports WARN per missing venv. A separate operator concern is whether to install all venvs before running the audit; the spec defers this to the operator.
- The 15-paragraph count is enforced by the prompt but not validated server-side. The LLM may emit 14 or 16. The WARN-and-accept policy treats this as observational data. If the LLM consistently misses the count, that's a generation-contract issue for a future round, not an audit failure.
