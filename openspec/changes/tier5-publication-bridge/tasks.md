# Tasks: tier5-publication-bridge

See `docs/plans/2026-05-19-tier5-scale-author.md` Phase T for full
TDD steps. Task numbers track that document.

## Phase T.1 — Annotations JSON emission

- [ ] T1.1: Extend `verdict_to_qa.py` in both verifiers to emit
  `work/manuscript-annotations.json` with the v1 schema
  (`version`, `source_path`, `source_sha256`, `annotations[]`).
  Read `:source-spans` from each defect's atom set and join with
  the verdict's defect rows. (REQ-PUB-040)
- [ ] T1.2: Hash the source markdown at verify time and store the
  digest in `source_sha256`; helper in
  `verifiers/<v>/scripts/_source_hash.py`.

## Phase T.2 — Renderer

- [ ] T2.1: New `skills/neurosym-forge/scripts/render_annotations.py`
  reads the annotations JSON + source markdown and emits
  `<basename>-annotated.html` with `<mark class="severity-...">`
  wraps. Use the existing `markdown` library for the prose-to-HTML
  conversion. (REQ-PUB-041)
- [ ] T2.2: Ship default stylesheet at
  `skills/neurosym-forge/assets/annotations.css` with the three
  severity colour classes; allow `--stylesheet` override.

## Phase T.3 — Defect index

- [ ] T3.1: When `--out-dir` is given, the renderer additionally
  emits `<out-dir>/defect-index.html` listing every defect grouped
  by severity (with Phase S advisory partition honoured) and
  surfacing `verdict_confidence`. (REQ-PUB-042)

## Phase T.4 — Stale-span detection

- [ ] T4.1: At render start, hash the on-disk source and compare
  to `source_sha256`; on mismatch emit a single stderr warning.
  (REQ-PUB-043)
- [ ] T4.2: Per-annotation, if `source[start:end]` looks degenerate
  (no alphabetic chars or out of bounds), emit a per-claim warning
  and skip that annotation while continuing the rest.

## Phase T.5 — CLI surface

- [ ] T5.1: Wire `forge render <manuscript.md> --annotations ...
  [--out-dir ...] [--stylesheet ...]` through the existing
  `scaffold_project.py` CLI entry point (Phase U extends this
  further). (REQ-PUB-044)
- [ ] T5.2: Verifier-project `Makefile` template gains a `render`
  target that invokes `forge render` with the standard
  `work/manuscript-annotations.json` path.

## Phase T.6 — Phase Q `see also` interop

- [ ] T6.1: WHERE Phase Q's `:semantic-neighbours` is enabled,
  pipe each defect's top-3 similar claim ids into the
  `see_also` field of `manuscript-annotations.json`; renderer
  emits a "see also" link cluster per defect. (REQ-PUB-045)

## Phase T.7 — Round-trip test

- [ ] T7.1: New test fixture in `tests/test_render_annotations.py`
  drives a small manuscript through ingest → verify → annotate →
  render and asserts `<mark>` count equals defect count.
  (REQ-PUB-046)
- [ ] T7.2: Stale-span test edits the manuscript between verify
  and render, asserts the warning surfaces and rendering
  continues with the remaining valid annotations.

## Phase T.8 — PR

- [ ] T8.1: Push `plan/tier5-scale-author` (publication-bridge
  slice) and open the PR.
- [ ] T8.2: Merge on green CI.
