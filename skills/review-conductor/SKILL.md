---
name: review-conductor
description: Orchestrate configurable multi-persona editorial review panels over book-review. Use when user says "run the panel", "review chapter with the conductor", "run the seven-persona panel", "soft-gate this chapter via review-conductor". Loads a panel YAML config, calls book-review's dispatch primitives, applies per-persona severity gates (gating vs advisory), emits panel-review.md plus verdict.json. Do NOT use for source ingestion (use book-knowledge), prose-only style rewrites (use russellian-style), chapter drafting (use book-compose), or persona definition (use book-review).
license: MIT
metadata:
  author: charles-hoskinson
  version: 0.1.0
  category: writing
  workspace-aware: true
  invokes: book-review
---

# review-conductor

Panel-orchestration sibling for `book-review`. Owns multi-panel review coordination: load a YAML panel config, dispatch the configured personas through book-review's primitives, apply per-persona severity gates, emit a verdict.

## What it owns

- `panels/*.yaml` — declarative panel configs (which personas, which severity rule per persona, which output paths).
- `assets/panel-config.schema.json` and `assets/verdict.schema.json` — schema validation for the above.
- `scripts/load_panel.py` — YAML loader + schema validation.
- `scripts/dispatch_panel.py` — packet construction; few-shot injection from Outcomes exemplars.
- `scripts/aggregate_panel.py` — per-persona severity gate; verdict computation; report rendering.
- `scripts/outcomes_loader.py` — loads exemplars from `book-review/references/outcomes/<exemplar>/`.
- `scripts/conductor.py` — public entrypoint `run_panel(workspace, chapter_id, panel_path, dispatcher)`.

## What it does NOT own

- Persona definitions — owned by `book-review/personas/`.
- Subagent dispatch infrastructure — caller-provided dispatcher callable.
- Sentence-grain prose discipline — `russellian-style`.
- Source ingestion or claim ledger — `book-knowledge`.
- Post-build defect gating — `book-qa`.

## Panel configuration

A panel is a YAML file at `panels/<panel-id>.yaml`. The chapter-default panel:

```yaml
panel_id: chapter-default
artifact_scope: chapter
personas:
  - id: gottlieb
    severity_gate: gating
  - id: lay-reader
    severity_gate: advisory
  - id: domain-expert
    severity_gate: gating
  - id: copyeditor
    severity_gate: gating
  - id: enjoyment-reader
    severity_gate: advisory
  - id: ai-slop-detector
    severity_gate: gating
    delegates_to: humanizer
  - id: first-time-visitor
    severity_gate: advisory
verdict:
  hard_gate: false
  soft_gate_rule: any_critical_from_gating
outcomes:
  exemplar_paths:
    - ../book-review/references/outcomes/readme-pass-2026-05-13/
  per_persona_exemplars: 1
output:
  panel_report_path: "chapters/drafts/{chapter_id}/panel-review.md"
  verdict_path: "chapters/drafts/{chapter_id}/verdict.json"
```

`severity_gate: gating` means a critical finding from this persona soft-gates release; `advisory` means it surfaces but does not gate. `soft_gate_rule` selects how the per-persona criticals roll up to a panel-level verdict (`any_critical_from_gating` is the default).

## Usage

```python
from scripts.conductor import run_panel
from pathlib import Path

verdict = run_panel(
    workspace=Path("/path/to/workspace"),
    chapter_id="ch-01",
    panel_path=Path("panels/chapter-default.yaml"),
    dispatcher=None,  # default: caller dispatches via Task tool
)
```

The `dispatcher` callable receives one `PanelPacket` per persona and is responsible for the actual subagent invocation. The conductor writes `verdict.json` plus `panel-review.md` to the workspace and returns the verdict dict.

## Composes with

- `book-review` — imports `persona_loader`, `dispatch_review`, `aggregate_reviews`, `review_pass` via `sibling_skills.load_book_review_module`.
- `humanizer` — the `ai-slop-detector` persona delegates to humanizer's catalog.
- `book-compose` — Stage 7 invokes the conductor instead of `book-review.run_review_pass` directly.

## Tests

```bash
.venv/Scripts/python.exe -m pytest tests/ -q
```

Twenty-nine tests across schema validation, panel loading, sibling loading, outcomes selection, dispatch construction, aggregation, and a stubbed-dispatcher integration test.
