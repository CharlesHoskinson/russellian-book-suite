# Ingest playbook

Local ingest of source materials into a book workspace. The ingest stage is the only point at which raw bytes enter the workspace. Everything downstream — wiki, claims, graph — derives from these immutable inputs.

## Choosing the ingest function

Route by file extension, not by content sniffing:

- `.pdf` → `scripts.ingest_pdf.ingest_pdf`
- `.md`, `.markdown` → `scripts.ingest_markdown.ingest_markdown`

Refuse other extensions. Do not attempt to coerce `.docx`, `.html`, `.txt`, or `.epub`. Convert them to PDF or markdown outside the skill, then re-ingest.

PDFs that lack an embedded text layer are inert. Run an external OCR tool first (Tesseract, ocrmypdf, vendor scanners). The skill itself never invokes OCR. An ingest of an image-only PDF emits `node_count: 0` in the manifest and an empty wiki source page; treat that as a defect signal and OCR the source before proceeding.

## doc_id naming

`compute_doc_id(filename)` derives a kebab-case identifier from the filename stem. Rules:

- Lowercase
- Non-alphanumeric runs collapse to a single hyphen
- Leading and trailing hyphens stripped
- No path components retained

Example: `My Paper (v2).pdf` → `my-paper-v2`.

## Collision handling

A collision is two distinct files (different sha256) producing the same doc_id. The ingest function checks for an existing manifest at `raw/manifests/<doc_id>.json` before writing. If a manifest exists with a different sha256, the new file is assigned `<doc_id>-2`, `<doc_id>-3`, etc., until an unused id is found. The manifest records the actual file sha256, so the collision is auditable.

If the existing manifest has the same sha256, the ingest is idempotent: the manifest is overwritten in place, the raw bytes are not re-copied, and the wiki source page is regenerated. The log entry records `re-ingest` rather than `ingest`.

## Source manifest schema

Every ingest writes `raw/manifests/<doc_id>.json` validated against `assets/source-manifest.schema.json`. Required fields:

- `doc_name` — original filename
- `doc_id` — computed kebab-case stem
- `source_kind` — `pdf` or `markdown`
- `sha256` — 64-hex digest of raw bytes
- `ingested_at` — ISO 8601 UTC timestamp
- `node_count` — number of structural nodes detected (markdown headings or PDF chapters/pages)

Optional fields:

- `byte_size` — file size on disk
- `ingested_by_run` — run identifier passed by the caller
- `page_count` — PDF page count (PDF only)
- `tree_root` — root node identifier of the structural tree

`additionalProperties: false`. Schema violations raise `ManifestValidationError`.

## Wiki source page

Every ingest also writes `wiki/sources/<doc_id>.md`. Markdown ingest preserves the heading tree verbatim. PDF ingest emits page-by-page text extracts under `## Page N` headings. Chapter-style PDFs with a detectable outline are additionally annotated with structural nodes (`### <chapter title>`) keyed by node_id, so claims can locate themselves at chapter granularity rather than page granularity.

The source page is a derivative artifact: it is regenerated on every ingest, never hand-edited. Wiki pages that synthesize across sources live in `wiki/concepts/` and `wiki/entities/` and ARE hand-edited.

## Local-only guarantees

This skill imports `pdfplumber` and `markdown-it-py` and nothing else for parsing. Specifically forbidden:

- PageIndex, Marker API, or any cloud-PDF service
- Tesseract or paddleocr (OCR happens out-of-band)
- Any HTTP client (`requests`, `httpx`, `urllib`) for fetching content
- LLM-driven extraction at ingest time

The ingest pipeline is deterministic byte-in, bytes-out. Re-running on the same file produces the same manifest and the same wiki source page. Determinism is what makes provenance audits possible downstream.

## Failure modes worth knowing

- pdfplumber returns empty strings on encrypted PDFs. Decrypt before ingest.
- Multi-column academic PDFs are extracted in reading order only when pdfplumber's column detection succeeds. Cross-check the wiki source page after first ingest.
- Markdown with broken heading hierarchy (h1 → h3 with no h2) is preserved as-is; the heading tree is not re-balanced.

## Logging

Every successful ingest appends a single line to `wiki/log.md`:

```
- 2026-05-08T12:34:56Z ingest <doc_id> sha256=<hex8> nodes=<n>
```

Re-ingests use `re-ingest` instead of `ingest`. Log lines are append-only. Never edit prior entries.
