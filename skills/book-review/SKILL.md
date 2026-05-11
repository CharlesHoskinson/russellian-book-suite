---
name: book-review
description: Run multi-persona editorial reviews on a drafted chapter. Five personas (Robert Gottlieb, Lay Reader, Domain Expert, Copyeditor, Enjoyment Reader) read the chapter and return severity-tagged feedback. Critical findings soft-gate chapter release. Use when user says "review chapter X with personas", "Gottlieb pass on this chapter", "run the editorial reviews", "what would Gottlieb say about this draft", "is this chapter ready for review", "soft-gate this chapter". Do NOT use for source ingestion (use book-knowledge), prose-only style fixes (use russellian-style), chapter drafting (use book-compose), or persona reviews on prose outside the book pipeline.
license: MIT
metadata:
  author: charles-hoskinson
  version: 0.1.0
  category: writing
  workspace-aware: true
---

# book-review

You orchestrate multi-persona editorial reviews on chapter drafts in a book-knowledge workspace.

## Operating doctrine

1. **Personas comment; they do not rewrite.** Revisions go through book-compose's drafting workflow, not through this skill.
2. **Five personas, five lenses.** Each is documented in `personas/<id>.md`. Read the persona before invoking it.
3. **Soft-gating only.** Chapter release fails iff any persona returns `severity=critical`. Important and minor findings are advisory.
4. **Local only.** Persona dispatch uses Claude itself via subagent. No external API calls.
5. **Never auto-trigger.** Reviews run only on explicit invocation.

## Workflow

### Stage 1: Preparation
1. Verify the chapter has a draft at `<workspace>/chapters/drafts/<chapter_id>/draft.md`.
2. Read the chapter contract at `<workspace>/chapters/contracts/<chapter_id>.yaml` for context (title, purpose, audience).
3. Read the relevant persona definitions in `personas/`.

### Stage 2: Dispatch packets
Call `scripts/review_pass.py:prepare_dispatch_packets(workspace, chapter_id)`. Returns one `DispatchPacket` per persona, each with a fully-rendered prompt.

### Stage 3: Subagent dispatch
For each packet (parallel-safe):
1. Issue a Task-tool call with `description="Persona review: <persona_display_name>"` and `prompt=packet.prompt`.
2. The subagent reads the persona body as its own role, reads the chapter prose, and writes its review to `packet.output_path`.

### Stage 4: Aggregation
Call `scripts/aggregate_reviews.py:aggregate_reviews(workspace, chapter_id)`. Produces:
- `<workspace>/chapters/drafts/<chapter_id>/persona-review.md` — aggregated report
- Severity counts (critical, important, minor)
- Per-persona verdicts table

### Stage 5: Surface findings
1. Display the aggregated severity counts.
2. If `critical > 0`, list the critical findings and stop. The chapter does not pass review.
3. Surface important and minor findings as advisory.

## Severity rubric

- **Critical** findings BLOCK chapter release. Reserved for what the persona's lens marks as critical (see each persona's definition).
- **Important** findings should be addressed before publication; do not block.
- **Minor** findings are advisory polish.

## References

- `references/persona-design.md` — how to write a new persona
- `references/severity-rubric.md` — what counts as critical for each persona
- `references/worked-example.md` — end-to-end review of a chapter that has a listicle abstract

## Scripts

- `scripts/persona_loader.py` — load persona definitions from `personas/*.md`
- `scripts/dispatch_review.py` — render dispatch prompts; parse review reports
- `scripts/aggregate_reviews.py` — merge per-persona reports into `persona-review.md`
- `scripts/review_pass.py` — orchestrator: prepare_dispatch_packets, run_review_pass

## Personas

- `personas/gottlieb.md` — Robert Gottlieb, legendary editor (cadence, AI-sloppy patterns)
- `personas/lay-reader.md` — intelligent generalist (accessibility)
- `personas/domain-expert.md` — skeptical specialist (factual accuracy)
- `personas/copyeditor.md` — mechanics + cross-chapter consistency
- `personas/enjoyment-reader.md` — pleasure reader (engagement)

## Local-only guarantee

This skill never makes outbound network calls. Persona dispatch happens via Claude's Task tool against the same local Claude. No HTTP libraries are imported. No cloud SDKs are loaded.
