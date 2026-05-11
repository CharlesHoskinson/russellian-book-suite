# Smoke Test — book-knowledge — 2026-05-09

## Automated verification (passes)

- 58/58 pytest tests pass: 5 workspace + 5 manifest + 4 ingest_md + 3 ingest_pdf + 6 claim_validator + 6 ledger + 3 verify_claim + 3 detect_conflicts + 3 project_graph + 2 validate_shacl + 3 competency queries + 2 audit_taxonomy + 2 wiki_index_regen + 4 trigger calibration + 1 integration + 6 anthropic compliance.
- Skill is discoverable in Claude Code: confirmed in session-start skill registry as `book-knowledge` with the description loaded from SKILL.md.
- Six reference files in `references/` with substantive content (each ≥ 60 lines, total > 600 lines of progressive-disclosure detail).
- All 13 scripts present and exercising real behavior: workspace.py, ingest_common.py, ingest_pdf.py, ingest_markdown.py, source_manifest.py, claim_validator.py, ledger.py, verify_claim.py, detect_conflicts.py, project_graph.py, validate_shacl.py, run_competency_queries.py, audit_taxonomy.py, wiki_index_regen.py.
- Asset files present: claim-record.schema.json, source-manifest.schema.json, graph-context.jsonld, shapes.ttl, 5 SPARQL queries (.rq), workspace skeleton templates.
- Frontmatter passes Anthropic compliance: kebab-case name (`book-knowledge`), 633-char description, no XML, includes positive triggers and explicit negative triggers naming `book-compose` and `russellian-style` siblings.

## Local-only verification

- No HTTP libraries imported anywhere in `scripts/`. Confirmed:
  - No `import requests`, `httpx`, `urllib.request`
  - No `openai`, `anthropic`, `google.cloud`, or any cloud SDK
  - All processing via `pdfplumber`, `markdown-it-py`, `rdflib`, `pyshacl`, `jsonschema`, `pyyaml`
- pip install (one-time) downloaded packages from PyPI; this is install-time activity, not runtime data flow.
- Workspace files are local; no remote state synchronization.

## End-to-end pipeline verified by integration test

The `test_full_ingest_to_release_gate` integration test exercises:
1. `init_workspace(tmp_path / "book")` — full directory tree created
2. `ingest_pdf(small.pdf, workspace)` — manifest, raw copy, wiki source page, log entry
3. `append_claim(layout, claim)` × 3 — two with valid locator_text, one with text not in source
4. `verify_claim(layout, cid)` × 3 — first two transition proposed → verified; third stays proposed with reason
5. `project_graph(layout)` — TriG dataset with PROV-O wasDerivedFrom triples
6. `wiki_index_regen(layout)` — wiki/index.md rebuilt from tree
7. `validate_shacl(layout)` — conforms == True
8. `run_competency_queries(layout)` — `unsupported_claims` returns 0 rows; competency report written

## Live-session triggering tests (pending user validation)

These require a fresh Claude Code session because the running session has the skill discoverable but cannot reliably test trigger behavior from inside the same conversation.

| Test | Prompt | Expected | Status |
|---|---|---|---|
| Positive 1 | "Initialize a book workspace at /tmp/test-book." | book-knowledge activates | PENDING |
| Positive 2 | "Ingest C:\Users\charl\.claude\skills\book-knowledge\tests\fixtures\small.pdf into /tmp/test-book." | book-knowledge activates, ingest_pdf runs | PENDING |
| Positive 3 | "Audit the knowledge graph for /tmp/test-book." | book-knowledge activates, validate_shacl + competency queries run | PENDING |
| Negative 1 | "Draft chapter 3 from the verified claims." | book-knowledge does NOT activate (book-compose, when built) | PENDING |
| Negative 2 | "Rewrite this passage in Russell style." | book-knowledge does NOT activate (russellian-style) | PENDING |
| Negative 3 | "What does this paper say in plain English?" | book-knowledge does NOT activate (general Q&A) | PENDING |

## Latency baseline (from automated suite)

- Full pytest suite: 3.26s wall-clock on Windows 11.
- Single-PDF ingest: ~0.4s for 3-page synthetic.
- Graph projection (10 claims): ~0.05s.
- SHACL validation on small dataset: ~0.6s.
- Competency query suite (5 queries): ~0.2s.

## Known issues / deviations from plan

- `project_graph.py` was updated to emit plain literals (not `xsd:string`-typed) for `tbf:status` so SPARQL plain-literal comparisons work without explicit datatype annotation. SHACL still passes.
- `project_graph.py` mirrors triples to the default graph in addition to writing them to per-claim named graphs, so plain `rdflib.Graph()` parsing finds them. Downstream `Dataset(default_union=True)` consumers see triples once.
- 486 `DeprecationWarning`s from rdflib/pyshacl internals during pytest. Functional only; will require attention on future rdflib upgrades.

## Next steps

1. Run the six live-session tests above in a fresh Claude Code window.
2. Update this document with PASS/FAIL for each.
3. If any positive trigger fails to activate, expand the description's keyword list. If any negative trigger over-triggers, harden the negative phrasing.
4. Build `book-compose` (sibling skill) — the pending third skill in the russellian-book-forge family.
