# Capability delta: publication-bridge — change: tier5-publication-bridge

This change introduces a new capability `publication-bridge`,
the framework's path from verdicts to author-facing defect
surfacing on the source manuscript. Today verdicts land in
`work/verdict.edn` and `qa/verification-defects.json`; neither
reaches a human author reading prose. After this change, every
verifier emits an annotations JSON and the framework ships a
`forge render` command that overlays the defects on the source
markdown as colorised HTML.

## ADD

### REQ-PUB-040 — Ubiquitous

`verdict_to_qa.py` in every verifier SHALL emit
`work/manuscript-annotations.json` whose schema is

```json
{
  "version": 1,
  "source_path": "...",
  "source_sha256": "...",
  "annotations": [
    {"claim_id": "...", "source_span": [start, end],
     "severity": "...", "declared_severity": "...",
     "message": "...", "defect_confidence": 0.0,
     "defect_id": "...", "constraint_id": "..."}
  ]
}
```

The `version` field SHALL be the integer `1`; future schema
changes SHALL bump this integer. `source_sha256` SHALL be the
hex digest of the source markdown captured at verify time.

**Rationale:** A versioned schema lets downstream tools (the
renderer, third-party annotation viewers, future IDE plugins)
detect incompatible changes statically rather than discovering
them by parsing errors; capturing the source hash at verify time
is what makes stale-span detection possible (REQ-PUB-043).
**Tested by:**
`tests/test_verdict_to_qa.py::test_manuscript_annotations_schema_v1`
(added in T1.1)

### REQ-PUB-041 — Ubiquitous

The framework SHALL ship a renderer at
`skills/neurosym-forge/scripts/render_annotations.py` that
accepts `manuscript-annotations.json` plus the source markdown
and emits HTML in which each annotation's source span is wrapped
in `<mark class="severity-{severity}" data-claim-id="..."
data-defect-id="..." title="{message}">`. CSS classes
`severity-hard`, `severity-soft`, and `severity-advisory`
SHALL each be defined in
`skills/neurosym-forge/assets/annotations.css` with distinct
default colours.

**Rationale:** Authors need defects visible in-context on the
prose they're editing; the `<mark>` element is the semantic
HTML primitive for highlighting and accepts `data-*` attributes
that let optional JS layers add richer behaviour without
re-parsing the document.
**Tested by:**
`tests/test_render_annotations.py::test_marks_wrap_source_spans`
(added in T2.1)

### REQ-PUB-042 — Optional feature

WHERE `--out-dir <dir>` is given on the renderer command line,
the renderer SHALL additionally emit `<dir>/defect-index.html`
summarising every defect across the corpus grouped by severity
(honouring Phase S's `:advisory` partition by listing advisories
in a separate section) with clickable links to each defect's
in-context position in the annotated manuscript HTML. The index
SHALL surface the verdict's `verdict_confidence` value at the
top level.

**Rationale:** A defect index gives operators a single-page
overview of the corpus's defects; the clickable jumps close the
loop between "see the list" and "see the prose" without forcing
them to grep claim ids by hand.
**Tested by:**
`tests/test_render_annotations.py::test_defect_index_groups_by_severity`
(added in T3.1)

### REQ-PUB-043 — Unwanted behaviour

IF a source span in `manuscript-annotations.json` does not match
the on-disk source markdown's byte range — either because the
file's sha256 differs from `source_sha256` or because the
`source[start:end]` substring is degenerate (no alphabetic
characters or out of bounds) — THEN the renderer SHALL emit a
warning to stderr naming the offending claim id and SHALL SKIP
that annotation while continuing to render the remaining valid
annotations. The renderer SHALL NOT abort on stale spans.

**Rationale:** Authors edit between verify and render runs;
aborting the render on the first stale span would make the
command brittle in exactly the workflow it's meant to support.
Warnings preserve visibility without sacrificing utility.
**Tested by:**
`tests/test_render_annotations.py::test_stale_span_warns_and_skips`
(added in T4.2)

### REQ-PUB-044 — Ubiquitous

The render command SHALL be exposed at the CLI surface as
`forge render <manuscript.md> --annotations <annotations.json>
[--out-dir <dir>] [--stylesheet <path>]`. Every verifier-project
template SHALL ship a `make render` target wired to the standard
`work/manuscript-annotations.json` path so authors do not have to
type the flags for the default workflow.

**Rationale:** Two surfaces — the explicit CLI for flexibility,
the Make target for ergonomics — mirror the framework's existing
`forge` + `make ci` pattern and keep onboarding consistent.
**Tested by:**
`tests/test_forge_cli.py::test_render_subcommand_exposed`
(added in T5.1)

### REQ-PUB-045 — Optional feature

WHERE the verifier ran with Phase Q's `:semantic-neighbours`
enabled, each annotation in `manuscript-annotations.json` SHALL
include a `see_also` field listing the top-3 semantically similar
claim ids, and the renderer SHALL emit a "see also" link cluster
per annotation pointing at the cited claims' in-document
positions. WHERE `:semantic-neighbours` is disabled (default),
the `see_also` field SHALL be absent and the renderer SHALL omit
the link cluster.

**Rationale:** Phase T and Phase Q compose when both are
enabled; keeping the `see_also` field optional means Phase T
ships standalone without forcing Phase Q's dependency on
embedding storage.
**Tested by:**
`tests/test_render_annotations.py::test_see_also_links_emitted_when_semantic_neighbours_enabled`
(added in T6.1)

### REQ-PUB-046 — Ubiquitous

A round-trip test suite SHALL drive a small fixture manuscript
through ingest → verify → annotate → render and SHALL assert that
the resulting HTML's `<mark>` element count equals the verdict's
defect count. A stale-span variant of the same fixture SHALL
exercise REQ-PUB-043 by editing the manuscript between verify and
render and asserting the warning surfaces while the unaffected
annotations still render correctly.

**Rationale:** The unit-level tests cover each stage in
isolation; the round-trip is what proves the schema, the
renderer, and the CLI agree on the data shapes. Without it the
pieces can pass independently and still produce broken output
end-to-end.
**Tested by:**
`tests/test_render_annotations.py::test_round_trip_mark_count_equals_defect_count`,
`tests/test_render_annotations.py::test_round_trip_stale_span_warns`
(added in T7.1, T7.2)
