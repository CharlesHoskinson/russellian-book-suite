# Overnight autonomous run — homoiconic-kg cutover (P2/P3/P5)

**Started:** 2026-06-16 (autonomous, unattended)
**Branch:** `feat/homoiconic-kg-cutover` (off `796f131`, local only — not pushed/merged)
**Plan:** `docs/superpowers/plans/2026-06-17-homoiconic-kg-cutover.md`
**Engine:** subagent-driven-development (implementer → spec review → code-quality review → fix loop → commit)
**Environment:** book-knowledge + book-thesis venvs built fresh on Python 3.14.5; baseline green
(book-knowledge 258 passed, book-thesis 39 passed) before any change.

## Safety rails
- No push, no merge to main, no PRs opened. Everything is local commits on the branch.
- P5.4 (delete rdflib/pyshacl/pyDatalog + uninstall deps) is NOT auto-executed — prepared for human review.
- Phase gates run the full skill suite; a red suite halts that phase.
- Blocked tasks are recorded and skipped, never faked green.

## Pre-flight finding (baked into C0.1)
`append_claim` runs full JSON-schema validation and `project_graph` emits only valid-ledger claims, so
NO SHACL shape in `shapes.ttl` can fire from a valid ledger (confidence/status/text/hasSourceSpan/the
verified-derives sh:sparql are all tighter at write-time; ChapterSectionShape needs `tbf:ChapterSection`
/`tbf:usesClaim`, which `project_graph` never emits). Resolution: the violating fixture injects violating
triples programmatically via rdflib (reusing project_graph's TBF/SCHEMA/PROV namespaces) on top of the
projected base — still programmatic, no committed raw RDF. Flagged for the audit.

## Progress

| Phase | Task | Status | Commit | Notes |
|---|---|---|---|---|
| C0 | C0.1 violating-workspace fixture | DONE | 4b6f68e | 4 violations (a/b/c), non-vacuous; spec+quality reviewed, fixes applied |
| C0 | C0.2 SHACL report golden | DONE | 46790fe | bermuda {true,[]}; violating {false,4}; byte-stable; both reviews passed |
| C0 | C0.3 D9-D11 consistency golden | DONE | 21f251f | violating: D9+D10+D11 (6 defects); bermuda clean+asserted; both reviews passed |

**Phase C0 (PR #1) gate PASSED** — book-knowledge 268 passed, book-thesis 43 passed; all 5 goldens frozen & non-vacuous; no production behaviour changed.
| P2 | P2.1 status single-source | DONE | 23b0184 | status-enum.edn; VALID_TRANSITIONS derived (byte-equiv); ClaimVocabularyError; 274 passed; both reviews |
| P2 | P2.2 defconstraint→Cozo compiler | DONE | 1f5ac16 | compile_constraint + 5 EDN + goldens; null-negation helper-rule fix; chapter-cites-verified DEFERRED→P2.3; 298 passed; both reviews |
| P2 | P2.3 Cozo-backed validate_shacl + parity | DONE | b1cfbc6 | KG_BACKEND dispatch; canonical-form normalization; chapter-section entity + 6th constraint; parity rdflib==golden==cozo (non-tautological); 304 passed default + cozo smoke clean; both reviews |

**Phase P2 (PR #2) gate:** default rdflib suite 304 passed; validate_shacl parity proven on both backends; KG_BACKEND default stays rdflib (P5.3 flips). book-compose contract preserved (callers use only .conforms; verified by reading — book-compose venv not built). Recursive-SHACL N/A (neither shape recursive). **KNOWN P5.3 INPUT:** RDF-injection test fixtures are now rdflib-pinned; the full suite under KG_BACKEND=cozo is NOT yet all-green (other consumers like run_competency_queries) — P5.3 must flip default + fix remaining consumers + rework/retire RDF-only fixtures.
| P3 | P3.1 thesis→cozo projector | pending | — | — |
| P3 | P3.2 D9-D11 EDN→Cozo + parity | pending | — | — |
| P5 | P5.1 port remaining RDF readers | pending | — | — |
| P5 | P5.2 reconcile 3 divergences | pending | — | — |
| P5 | P5.3 default flip + cutover gate | pending | — | — |
| Z | Phase Z adversarial audit | pending | — | — |
| P5 | P5.4 deletion (PREPARED, not executed) | deferred | — | human review |

(Updated as the run proceeds.)
