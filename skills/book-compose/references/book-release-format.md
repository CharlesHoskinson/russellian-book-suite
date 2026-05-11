# Book Release Format

A book release is the publishable artifact for an entire book at one version. It aggregates the chapter releases produced in Stage 5 into a single bundle suitable for distribution. The bundle is a directory under `<workspace>/book/releases/<version>/` produced by `scripts/build_book.py:build_book`. It contains the concatenated manuscript Markdown, the deterministic HTML skeleton, the Playwright-rendered PDF when Chromium is installed, the per-chapter summary, the cited-claims slice, copies of every chapter release that fed the build, and a schema-validated manifest.

## Directory layout

```
<workspace>/book/releases/<version>/
├── manuscript.md
├── manuscript.html
├── manuscript.pdf            (optional; requires Playwright + Chromium)
├── book-manifest.yaml
├── summary.json
├── claims-bibliography.jsonl
└── chapter-bundles/
    ├── ch-01-<chapter-version>/
    ├── ch-02-<chapter-version>/
    └── ...
```

### `manuscript.md`

The concatenated source of truth. `build_book._assemble_manuscript` reads each chapter's `draft.md` from its release bundle, normalises the chapter heading to `# Chapter <n>: <title>`, prepends a generated table of contents, and joins the chapters with horizontal rules. The Markdown source is invariant across renderers. Pandoc, Playwright, and any downstream tool all read this file as the canonical text. The file always exists.

### `manuscript.html`

The canonical interactive view. The deterministic skeleton at `assets/book-html-skeleton.html` is rendered by `scripts/render_book_html.py:write_html_skeleton` with the book payload inlined as `<script>` blocks. Claude later invokes the `web-artifacts-builder-anthropic` Skill tool to replace the `BOOK_APP_INSERTION_POINT` marker with a React+Tailwind+shadcn book browser. The resulting HTML works offline. It always exists.

### `manuscript.pdf`

Rendered from `manuscript.html` by `scripts/print_pdf.py:print_pdf` via headless Chromium. The PDF is the print artifact of the HTML, not an independent typesetting pass. Print-CSS rules in the HTML hide the TOC sidebar, search bar, theme toggle, and download buttons, then break each chapter onto a new page. The PDF is optional. `build_book` calls `is_playwright_ready()` first; if Playwright or Chromium is absent, the step is skipped silently and `outputs` omits `manuscript.pdf`.

### `book-manifest.yaml`

Schema-validated metadata. The schema is `assets/book-manifest.schema.json`. `additionalProperties: false`; unknown fields are rejected and the build aborts.

Required fields:

- `book_id` — stable identifier for the book. Pattern `^[a-z0-9][a-z0-9-]*$`.
- `title` — reader-facing book title.
- `version` — release version string. See conventions below.
- `built_at` — RFC 3339 timestamp of the build.
- `chapters_included` — ordered list of chapter ids in the manuscript.
- `outputs` — list of artifact filenames present in the bundle. Always contains `manuscript.md` and `manuscript.html`. Contains `manuscript.pdf` only when the Playwright step succeeded.
- `total_word_count` — integer sum of per-chapter word counts.
- `total_claim_count` — integer sum of per-chapter cited-claim counts.

Optional fields:

- `chapter_versions` — map from `chapter_id` to the chapter release version that fed the book build.
- `shacl_conforms` — boolean recorded from the book pre-flight gate.
- `competency_clean` — boolean. True when the workspace had zero unsupported claims and zero contradictions at build time.
- `sources_bibliography` — sorted list of `doc_id` values cited across the book.

### `summary.json`

The data payload that feeds the React app. Produced by `scripts/book_summary.py:build_book_summary`. Contains per-chapter abstract seeds, section headings, word counts, claim counts, and the chapter draft text. The same JSON is inlined into `manuscript.html` as the `book-payload` script block.

### `claims-bibliography.jsonl`

The verified-claim records cited across the book scope, one JSON object per line, sorted by `claim_id`. Each record is the latest revision drawn from the claim ledger via `book-knowledge`'s `read_claims`. A reviewer can re-verify the book using only this file plus the source documents.

### `chapter-bundles/`

Byte-for-byte copies of each chapter release that fed the build. The book is therefore self-contained: the chapter-level manifests, draft sources, evidence summaries, and claims slices remain reachable without the workspace.

## Version-string conventions

`build_book` accepts any non-empty string. Two conventions are recommended:

- Semantic version (`v1.2.0`, `1.0.0-rc1`). Use when the book has a release cadence with API-shaped guarantees and breaking-change semantics matter.
- Date-stamped (`2026-05-08`, `2026-05-08-r2`). Use for date-pinned periodic builds where chronological ordering is the dominant concern.

Pick one convention per book and keep it. Mixing semver and date stamps within a single book makes ordering ambiguous.

## Reproducibility guarantee

A book release plus the workspace at the build SHA reconstructs the bundle byte-for-byte, modulo two well-defined sources of drift:

1. The `built_at` timestamp in `book-manifest.yaml` changes on every build.
2. `manuscript.pdf` may differ when the operator's Chromium version differs from the build-time version. `manuscript.md` is invariant. `manuscript.html` is invariant up to the React app rendering, which is itself deterministic given the same payload and the same web-artifacts-builder-anthropic skill version.

The reproducibility test:

1. Check out the workspace at the SHA recorded in the manifest.
2. Re-run `build_book(workspace, version, chapter_versions, book_title, book_id)` with the same `chapter_versions` map.
3. `diff` `manuscript.md`, `summary.json`, `claims-bibliography.jsonl`, and `book-manifest.yaml` (after stripping `built_at`). All four files must match.

`chapter_versions` is the load-bearing input. Pinning per-chapter versions in the manifest means a later chapter revision does not retroactively change a prior book release.

## Role of each artifact

- `manuscript.md` is the source of truth. All downstream renders derive from it. Cite this file in scholarly contexts.
- `manuscript.html` is the canonical interactive view. Readers open this in a browser. Print-CSS rules are baked in.
- `manuscript.pdf` is a render of the HTML, not an independent artifact. Treat it as the print proof of the HTML view.
- `book-manifest.yaml` is the integrity ledger. Downstream tooling reads it rather than scanning the directory.
- `summary.json`, `claims-bibliography.jsonl`, and `chapter-bundles/` make the bundle self-auditing.
