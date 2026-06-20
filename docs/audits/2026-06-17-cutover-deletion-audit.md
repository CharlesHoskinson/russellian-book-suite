# Cutover + deletion audit - findings

## Verdict

P5.4a has no blocking runtime parity defect in the surviving Cozo claim-store path. The SHACL and SPARQL deletions appear safe for real ledger data, with the documented P5.2 semantic changes explicit and tested. I would fix the characterization-capture format/empty-guard issue before relying on regenerated goldens after merge; it is not a live-data gate failure, but it can corrupt the post-deletion oracle. The remaining issues are tooling, manifest hardening, and stale/dead legacy references.

## Findings

| Severity | Finding | Evidence | Impact |
| --- | --- | --- | --- |
| IMPORTANT | `capture_characterization.capture()` no longer writes the format that the committed query-golden comparator expects, and its empty guard is weaker than the old dataset guard. The writer emits row lists, while `test_query_ports` still treats goldens as SPARQL binding dicts. A non-empty ledger that projects to zero rows, for example only latest `superseded` claims, also passes the line-size guard and can write all-empty goldens. | `files/skills__book-knowledge__scripts__capture_characterization.py:117` checks only ledger existence/size; `:131-136` writes `[[...]]` rows. `files/skills__book-knowledge__tests__test_query_ports.py:44-50` expects dict rows and indexes by sorted binding keys. `project_ledger_cozo.py:226-228` drops superseded claims after the guard. | Tooling/oracle risk, not live runtime. Regenerating goldens post-deletion can either break the tests or commit vacuous all-empty query goldens. |
| MINOR | Query manifest handling is correct now, but missing metadata silently defaults to `coverage` and defeasible severity silently defaults to `minor`. A typo or omitted manifest key can downgrade a future blocking query instead of failing discovery. | `files/skills__book-knowledge__scripts__run_competency_queries.py:55` defaults missing class to `coverage`; `:110` defaults missing severity to `minor`. Current manifest entries match the deleted tree and severities at `files/skills__book-knowledge__assets__kg-queries___meta.yaml:7-28`, and the deleted defeasible severities match `branch-diff_45917e7..HEAD.diff:603-614`. | Future gate-hardening risk only. Current real data is unaffected because all 8 query entries are present and correct. |
| MINOR | Stale/dead legacy references remain and will either mislead maintainers or trip a whole-tree no-bypass scan. | `capture_characterization.py:1-24` still describes RDF/SPARQL/dataset goldens; `:52-59` keeps an unused rdflib binding-dict helper; `:151` says `assets/queries/`. `project_ledger_cozo.py:50-62` still claims counter-claims preserve every `(cc, status)` history row, while the actual code dedupes latest at `:281-300`. `test_run_competency_queries.py:8-41` imports rdflib and defines an unused TriG helper. | No live-data impact. Documentation/test cleanup before P5.4b/no-bypass. |

## Deleted-Capability Parity

- `pyshacl` / `shapes.ttl`: faithful for the real ledger-backed claim model. The deleted shapes map to the 9 EDN constraints: text minCount, status presence/enum, confidence presence/range-low/range-high, source-span presence, verified-derives, and chapter-cites-verified. The old `schema:text` maxCount/datatype and confidence datatype checks are structurally covered by the one-row relation plus JSON schema / Cozo typed columns for valid writes; corrupt raw ledgers remain a documented divergence. `chapter-cites-verified` is synthetic-only today because no production projector emits `chapter-section` rows.
- The 8 `.rq` competency queries: all 8 are represented under `kg-queries/*.edn`, and `_meta.yaml` preserves old class/severity: `contradiction_scan` stays consistency; four coverage queries stay coverage; `rebuttal-presence` and `posterior-floor` stay critical defeasible; `contested-rebuttal-window` stays important defeasible. The P5.2 divergences are explicit canonical choices: stale source joins on `doc_id`, unsupported claims require source-span provenance, wiki page URIs drop doubled `wiki/`, and counter-claims use latest status.
- `project_graph.py`: safe to delete for the claim store. `project_ledger_cozo` now owns the real ledger projection into Cozo. What is lost is arbitrary raw RDF/TriG injection validation, which was already synthetic-test-only for this stack.

## P5.4b Readiness

The remaining pyDatalog removal is cleanly scoped but needs one extraction step: `consistency_cozo.py` still imports `DefectReport`, `_emit_pairs`, `_iter_claims`, `_resolve_claims_path`, `_value_str`, and `load_claim_facts` from `datalog_consistency.py` (`files/skills__book-thesis__scripts__consistency_cozo.py:31-36`). Move those shared helpers into a neutral module before deleting `datalog_consistency.py` and `rules/consistency.dl`.

No-bypass allowlist should be narrow:

- `skills/book-knowledge/scripts/audit_taxonomy.py`: allowed `rdflib` and `format="trig"`/Turtle parse for standalone RDFS taxonomy linting only.
- `skills/book-thesis/scripts/compile_thesis.py`: allowed `rdflib` for emitting `thesis-triples.ttl`.
- `skills/book-thesis/scripts/dispatch_entailment.py`: allowed `rdflib` for reading the thesis TTL layer.
- Also allow the documented thesis TTL readers `lint_supports.py` and `synthesize_exemplars.py` if still present.

After P5.4b there should be no `pyshacl` imports, no `pyDatalog` imports, no `project_graph` calls, no `assets/queries/*.rq` readers, and no claim-stack TriG parse/write path outside the allowlist above. If the scan covers tests/docs, first remove the dead rdflib helper in `test_run_competency_queries.py` and refresh stale capture/projector docs.

## Team-Claim Check

I agree that `rdflib` must stay for `audit_taxonomy` and the thesis TTL layer; it should not stay for the claim store. I mostly agree that every deleted SHACL shape and SPARQL query has a faithful EDN/Cozo equivalent for real ledger data, with the caveat that `chapter-cites-verified` has no production row source yet and the characterization capture tool is not format-compatible with the existing query-golden oracle.
