# Worked example: end-to-end on `tests/fixtures/small.pdf`

This walkthrough exercises the full pipeline: workspace creation → PDF ingest → claim authoring → verification → graph projection → SHACL validation → competency queries → taxonomy audit → wiki index regeneration.

The fixture `tests/fixtures/small.pdf` is a synthetic two-page PDF with detectable text, used by the test suite. The same shape of commands applies to any local PDF.

## 1. Initialize the workspace

```powershell
cd C:\Users\charl\.claude\skills\book-knowledge
.venv\Scripts\python.exe -c "from scripts.workspace import init_workspace; from pathlib import Path; init_workspace(Path('/tmp/example-book'))"
```

Result: `/tmp/example-book` is created with the standard skeleton — `raw/`, `wiki/`, `claims/`, `graph/`, `chapters/`, `reports/`. `wiki/index.md`, `wiki/log.md`, `wiki/current-status.md`, and `claims/ledger.jsonl` are seeded as empty templates. The CLAUDE.md template is dropped at the workspace root.

## 2. Ingest the PDF

```powershell
.venv\Scripts\python.exe -m scripts.ingest_pdf tests/fixtures/small.pdf /tmp/example-book
```

Expected outputs:

- `/tmp/example-book/raw/pdf/small.pdf` — copy of the source bytes.
- `/tmp/example-book/raw/manifests/small.json` — manifest with `doc_id: small`, `source_kind: pdf`, sha256 of the file, `node_count: 2` (two pages).
- `/tmp/example-book/wiki/sources/small.md` — page-by-page extract:

```markdown
# small

## Page 1
The cat sat on the mat. The dog barked at the cat.

## Page 2
Russell wrote about the philosophy of logical atomism in 1918.
```

- `/tmp/example-book/wiki/log.md` gains a line:

```
- 2026-05-08T12:34:56Z ingest small sha256=a1b2c3d4 nodes=2
```

## 3. Append three claims

Two claims with locator text that appears in the source; one with locator text that does not.

```powershell
.venv\Scripts\python.exe - <<'EOF'
from datetime import datetime, timezone
from pathlib import Path
from scripts.workspace import WorkspaceLayout
from scripts.ledger import append_claim, next_claim_id

layout = WorkspaceLayout(root=Path('/tmp/example-book'))
now = datetime.now(timezone.utc).isoformat(timespec='seconds')

claim_a = {
    "claim_id": next_claim_id(layout),
    "canonical_text": "The cat sat on the mat in the example fixture.",
    "status": "proposed",
    "claim_type": "fact",
    "confidence": 0.9,
    "source_spans": [{"doc_id": "small", "locator_text": "The cat sat on the mat", "page_index": 1}],
    "created_at": now,
}
append_claim(layout, claim_a)

claim_b = dict(claim_a, claim_id=next_claim_id(layout),
               canonical_text="Russell wrote on logical atomism in 1918.",
               source_spans=[{"doc_id": "small", "locator_text": "logical atomism in 1918", "page_index": 2}])
append_claim(layout, claim_b)

claim_c = dict(claim_a, claim_id=next_claim_id(layout),
               canonical_text="The fixture mentions Wittgenstein explicitly.",
               source_spans=[{"doc_id": "small", "locator_text": "Wittgenstein explicitly", "page_index": 2}])
append_claim(layout, claim_c)
EOF
```

Result: three lines appended to `/tmp/example-book/claims/ledger.jsonl`. All three are `proposed`.

## 4. Verify each claim

```powershell
.venv\Scripts\python.exe -m scripts.verify_claim /tmp/example-book --all
```

Expected:

- `clm-2026-000001` ("cat sat on the mat") → transitions to `verified`. Locator text matches the source page. A new ledger entry is appended with `status: verified`, `last_verified_at: <now>`, `review_notes: "locator-text confirmed"`.
- `clm-2026-000002` ("logical atomism in 1918") → transitions to `verified`.
- `clm-2026-000003` ("Wittgenstein explicitly") → stays `proposed`. A failure record is written to `claims/verification/clm-2026-000003.md` listing the missed locator.

`wiki/log.md` gains three `verify-claim` lines.

## 5. Project the graph

```powershell
.venv\Scripts\python.exe -m scripts.project_graph /tmp/example-book
```

Result: `/tmp/example-book/graph/dataset.trig` is regenerated. It contains:

- One named graph per claim under `<base>/graphs/claims/clm-2026-000001` etc.
- `tbf:Claim`, `tbf:status`, `tbf:confidence`, `tbf:hasSourceSpan` triples.
- `prov:wasDerivedFrom` edges from each verified claim to its source spans.
- A run record under `<base>/graphs/runs/<run_id>` describing the projection.

## 6. Validate against SHACL

```powershell
.venv\Scripts\python.exe -m scripts.validate_shacl /tmp/example-book
```

Expected: validation passes. Both verified claims have `prov:wasDerivedFrom` edges (via their source spans), confidence is in [0, 1], status is from the enum, and `hasSourceSpan` is non-empty. The third claim is `proposed`, so the verified-claim sparql constraint does not apply to it.

`/tmp/example-book/graph/reports/shacl-latest.txt` contains:

```
Conforms: True
```

## 7. Run competency queries

```powershell
.venv\Scripts\python.exe -m scripts.run_competency_queries /tmp/example-book
```

Expected:

- `unsupported_claims` → 0 rows.
- `contradiction_scan` → 0 rows.
- `stale_after_source_refresh` → 0 rows.
- `orphan_wiki_pages` → 0 rows (the source page is referenced by the verified claims).
- `chapter_evidence_coverage` → 0 rows (no chapter contracts written yet).

A markdown report is written to `/tmp/example-book/graph/reports/competency-<timestamp>.md` with each query's row count and head.

## 8. Audit the taxonomy

```powershell
.venv\Scripts\python.exe -m scripts.audit_taxonomy /tmp/example-book
```

Expected: empty report. No role-as-subclass edges are present in the seeded schema, so the heuristic finds nothing. Output:

```
audit_taxonomy: 0 violations
```

## 9. Regenerate the wiki index

```powershell
.venv\Scripts\python.exe -m scripts.wiki_index_regen /tmp/example-book
```

Result: `/tmp/example-book/wiki/index.md` lists the new source page with its summary line. Concept and entity sections are empty because none have been authored yet. Orphans and dangles sections report none.

## What this exercise demonstrates

- The pipeline is fully local. No HTTP traffic, no API keys, no cloud OCR.
- The pipeline is deterministic. Re-running steps 2 through 9 on the same inputs produces the same outputs (timestamps aside).
- The state machine is honest. Claim C never reached `verified` because its locator did not appear in the source; the verifier did not paper over the miss.
- The release gate would pass for any chapter that cites only `clm-2026-000001` and `clm-2026-000002`. A chapter that cites `clm-2026-000003` would fail SHACL via `tbf:ChapterSectionShape`.

## Adapting to a real source

For a real PDF, replace `tests/fixtures/small.pdf` with the path of interest. The shape of the workflow is unchanged. Steps 3 through 9 are typically run repeatedly as new claims are authored and as sources are re-ingested.
