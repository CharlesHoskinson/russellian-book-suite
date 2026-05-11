# Release Bundle Format

A release bundle is the unit of publishable output. One bundle corresponds to one chapter at one version. The bundle is a directory under `chapters/releases/<chapter_id>-<version>/` produced by `scripts/build_release_bundle.py:build_release_bundle`. It contains the chapter's Markdown source, the optional Pandoc-derived outputs, the cited-claims slice, the style-pass report, and a schema-validated manifest.

## Directory layout

```
chapters/releases/<chapter_id>-<version>/
├── draft.md
├── draft.pdf            (optional)
├── draft.epub           (optional)
├── draft.tex            (optional)
├── evidence-summary.md
├── style-pass-report.md
├── claims-slice.jsonl
└── manifest.yaml
```

### `draft.md`

The chapter's Markdown source, copied byte-for-byte from `chapters/drafts/<chapter_id>/draft.md`. Always present. Mermaid blocks, footnote citations, and raw-LaTeX blocks are preserved. Pandoc reads this file when producing the derived outputs.

### `draft.pdf`, `draft.epub`, `draft.tex`

Pandoc-derived outputs. Each is produced only when:

1. The chapter contract's `output_formats` array names the format.
2. The Pandoc binary is on the operator's `PATH`.
3. The Pandoc invocation exits with code zero.

If any precondition fails, the corresponding output is silently absent from the bundle. The manifest's `outputs` list reflects what was actually produced; downstream tooling reads the manifest rather than scanning the directory.

The PDF and LaTeX outputs use `assets/pandoc/manuscript.tex` as the template and `xelatex` as the engine. The EPUB output uses Pandoc's built-in EPUB3 writer with no custom template.

### `evidence-summary.md`

Per-claim citation list produced by `scripts/evidence_summary.py:build_evidence_summary`. One section per cited claim. Each section names the claim id, the canonical text, the confidence value, and one bullet per source span. A source span is the tuple `(doc_id, page_index, locator_text)`. The summary is read by reviewers to verify provenance without opening the workspace's claim ledger.

### `style-pass-report.md`

The concatenated per-section reports emitted by russellian-style during Stage 4. Each section block carries the section number, the rewritten-line count, and the four core metrics: hedge count, passive-voice ratio, modifier-budget violations, parallel-structure violations. Reviewers read this file to verify that the chapter passed style discipline before release.

### `claims-slice.jsonl`

The exact verified-claim records cited in this release, one JSON object per line, sorted by `claim_id`. Each line is the latest revision of the claim drawn from the workspace's claim ledger via `book-knowledge`'s `read_claims`. The slice is the canonical input for re-verification: a downstream auditor who has only the bundle can reconstruct exactly which claims were trusted, and re-fetch the source spans to confirm them.

### `manifest.yaml`

Schema-validated metadata. The schema is `assets/release-manifest.schema.json`. Required fields:

- `chapter_id` — the chapter's stable identifier.
- `version` — the release version string.
- `built_at` — RFC 3339 timestamp of the build.
- `outputs` — list of output filenames present in the bundle (`draft.md` plus whichever Pandoc outputs succeeded).
- `sources_included` — sorted list of `doc_id` values backing the cited claims.
- `claim_slice_count` — integer count of cited claims.

Optional fields:

- `shacl_conforms` — boolean recorded from the pre-flight gate.
- `competency_clean` — boolean recorded from the competency-query gate.

`additionalProperties: false`. Unknown fields are rejected by the schema validator. The build aborts if the manifest fails validation.

## Reproducibility guarantee

A release bundle plus the workspace at the time-of-build SHA reconstructs the chapter byte-for-byte, modulo two well-defined sources of drift:

1. The `built_at` timestamp in the manifest changes on every build.
2. Pandoc-derived outputs (`draft.pdf`, `draft.epub`, `draft.tex`) may differ when the operator's Pandoc version differs from the build-time version. The Markdown source (`draft.md`) is invariant across Pandoc versions because `build_release_bundle` does not touch it after the copy.

Concretely, the reproducibility test is:

1. Check out the workspace at the SHA recorded in the bundle's `manifest.yaml`.
2. Re-run `build_release_bundle(workspace, chapter_id, version, formats)`.
3. `diff` the new bundle's `draft.md`, `evidence-summary.md`, `claims-slice.jsonl`, and `manifest.yaml` (after stripping `built_at`) against the original. All four files must match.

The `claims-slice.jsonl` invariant deserves emphasis. Because the slice is keyed by `claim_id` and recorded at the workspace SHA, the same SHA always yields the same slice. A claim revised after the bundle was built does not retroactively change the bundle. This is the property that makes the bundle citable in scholarly contexts: a reader who fetches the bundle today sees the same evidence the author saw at build time.

## Handling missing Pandoc

The `_run_pandoc` helper inside `build_release_bundle.py` wraps the subprocess call in a try-except over `FileNotFoundError` and `CalledProcessError`. When Pandoc is absent or fails, the helper returns `False`; the format is omitted from the bundle and from the manifest's `outputs` list. The build does not fail; the Markdown bundle is always produced.

Operators who require all formats should verify Pandoc is on `PATH` before invoking the build. The skill does not install Pandoc and does not prompt the user to do so.
