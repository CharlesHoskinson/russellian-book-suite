# Design: tier5-publication-bridge

## Annotations JSON schema (v1)

```json
{
  "version": 1,
  "source_path": "manuscript/chapter-03.md",
  "source_sha256": "ab12cd34...",
  "annotations": [
    {
      "claim_id": "C042-mizuno-trial-n",
      "source_span": [4821, 4889],
      "severity": "hard",
      "declared_severity": "hard",
      "message": "trial-n disagrees with chapter 7 (37 vs 42)",
      "defect_confidence": 0.92,
      "defect_id": "D042-trial-data-disagrees",
      "constraint_id": "X042-trial-n-agrees",
      "see_also": ["C051-mizuno-2008-citation"]
    }
  ]
}
```

The schema's first field is `version: 1` — bumping the integer
is the breaking-change signal for downstream consumers. The
`source_sha256` is captured at verify time and is what the
renderer checks against the on-disk markdown to detect stale
spans (see §3).

`source_span` is a byte-range `[start, end)` against the
markdown source. `severity` is the post-downgrade value from
Phase S; `declared_severity` is what the constraint declared.
`defect_confidence` is the Phase S min-of-chain. `see_also`
(optional) is populated only when Phase Q's
`:semantic-neighbours` is enabled — the top-3 similar claim ids.

## Renderer HTML output shape

`render_annotations.py` reads the markdown source, walks the
annotations in source-span order, and emits HTML with two pieces:

1. The source markdown converted to HTML via the existing
   `markdown` library (the same one `book-compose` uses).
2. Each annotation's span wrapped in `<mark class="severity-{severity}"
   data-claim-id="..." data-defect-id="...">`. The `<mark>` element
   has a `title` attribute carrying the defect message so hovering
   shows a tooltip; the `data-*` attributes let optional JS overlay
   richer UIs without re-parsing the HTML.

CSS classes the renderer emits:

| severity     | class                       | default colour       |
|--------------|-----------------------------|----------------------|
| `:hard`      | `severity-hard`             | red background       |
| `:soft`      | `severity-soft`             | yellow background    |
| `:advisory`  | `severity-advisory`         | grey background      |

Defaults ship in `skills/neurosym-forge/assets/annotations.css`;
authors can override by passing `--stylesheet path/to/custom.css`.

## Stale-span handling

If the manuscript was edited after the verifier ran, the byte
ranges in the annotations no longer line up with the on-disk
source. The renderer detects this two ways:

1. The annotations' `source_sha256` doesn't match a fresh hash
   of the source file. The renderer emits one summary warning:
   `"manuscript modified since verification (sha256 mismatch); annotations may be misaligned"`.
2. Per-annotation, if `source[start:end]` doesn't contain
   alphabetic characters (a heuristic for "this byte range fell
   into whitespace or off the end"), the renderer emits a
   warning naming the claim id and skips that annotation.

The renderer does not abort on stale spans; it produces the best
HTML it can and emits the warnings to stderr so the author sees
them in the terminal.

## `defect-index.html` summary

When `--out-dir` is given, the renderer also emits
`<out-dir>/defect-index.html` — a single page listing every
defect across the corpus, grouped by severity, each entry a
clickable link to its in-context position in the annotated
manuscript HTML. The index respects the Phase S
`:advisory-defects` partition: a separate section beneath the
main defects lists advisories distinctly.

The index also surfaces the verdict's `verdict_confidence` as a
top-level number (e.g., "Verdict confidence: 0.78").

## CLI surface

`forge render` is the new top-level CLI command. Invocation:

```
forge render manuscript/chapter-03.md \
  --annotations work/manuscript-annotations.json \
  --out-dir work/rendered/
```

Default `--out-dir` is `work/rendered/`. The output filename is
`<basename>-annotated.html`. `make render` in the verifier
project's Makefile wires this command to the standard
`work/manuscript-annotations.json` path so authors don't have to
type the flags.

## Phase Q integration — `see also`

If the verifier was built with `:semantic-neighbours` enabled
(Phase Q REQ-RETRIEVAL-044), each defect's verdict entry already
carries the top-3 similar claim ids. Phase T passes these through
to `manuscript-annotations.json`'s `see_also` field. The renderer
adds a "see also" link cluster under each annotation's tooltip
pointing at the cited similar claims' in-document positions. If
`:semantic-neighbours` was disabled (default), `see_also` is
absent from the JSON and the renderer omits the link cluster.
This composition keeps Phase T usable without Phase Q while
amplifying both when run together.
