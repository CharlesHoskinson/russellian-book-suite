# External adversarial-audit prompt — cutover + deletion (for GPT-5.5)

Paste the XML below into GPT-5.5 (Deep Research Pro). Attach the branch diff
`git diff 45917e7..HEAD` (branch `feat/homoiconic-kg-p5.4-deletion`; `45917e7` is
the end of the prior remediation+P5.1 audit's fixes — i.e. this is the unaudited
delta) and, if uploads are allowed, the files in `<artifacts>`. **Write your
findings report to a file named `audit.md`** (format specified in `<deliverable>`).

This covers the cutover completion: P5.2 (RDF↔Cozo divergence reconciliation),
P5.3 (KG_BACKEND default flip to cozo + the cutover gate), and — the focus — P5.4a,
the IRREVERSIBLE deletion of the pyshacl SHACL stack and the SPARQL/`project_graph`
RDF claim-graph stack. pyDatalog removal (P5.4b) is NOT in this diff.

```xml
<adversarial_audit model="GPT-5.5 Deep Research Pro">

<role>
You are a skeptical staff engineer reviewing the CUTOVER COMPLETION + a large,
partly-IRREVERSIBLE deletion in a Python monorepo of self-contained Claude Code
"skills". The project migrated its knowledge graph from a triple-stack
(rdflib/SPARQL/SHACL + pyDatalog) to a homoiconic "EDN front, Cozo back" store.
The default backend was flipped to Cozo and gated; now the legacy rdflib SHACL +
SPARQL claim-graph stack is being DELETED (the fallback is going away). Your job is
to find correctness/parity/safety defects — especially anything where the deleted
rdflib/SPARQL behaviour is NOT faithfully reproduced by the surviving Cozo path,
because once merged there is no fallback. Cite file:line. A credible audit is not
uniformly negative.
</role>

<context>
Three things landed since the last audit:

- P5.2 (commit 0b65d7a): reconciled the 3 documented RDF↔Cozo query divergences to
  canonical semantics (decisions in docs/audits/2026-06-17-kg-divergence-decisions.md):
  stale_after_source_refresh → adopt the Cozo doc_id join; unsupported_claims →
  source-span is the canonical provenance signal; wiki-page URI → drop the doubled
  `wiki/wiki/` prefix; counter-claim → dedupe to LATEST status per cc id (replacing
  the prior full distinct-(cc,status) history set). All bermuda query goldens
  unchanged (verified).

- P5.3 (commits 811a00d, 7d95f53): flipped the KG_BACKEND DEFAULT to cozo for
  validate_shacl + run_competency_queries; pinned the legacy rdflib-injection tests
  to KG_BACKEND=rdflib; added test_cutover_gate.py (default-is-cozo, bermuda required
  not skipped, clean real-data run).

- P5.4a (commits 9bbc150, 2134435): DELETED the rdflib stacks.
  * P5.4a-1: validate_shacl is now Cozo-ONLY — removed _validate_rdflib, the
    canonical-message remap (_build_canonical_messages / _normalize_pyshacl_violations),
    the Violation.component field; deleted assets/shapes.ttl + the rdflib-injection
    test fixture + the raw pyshacl golden. pyshacl dropped from book-knowledge +
    book-compose pyproject. book-compose's release-bundle non-conforming test now uses
    a raw SOURCELESS verified claim in the ledger (cozo flags verified-derives) instead
    of RDF injection.
  * P5.4a-2: DELETED scripts/project_graph.py (the TriG emit), assets/queries/*.rq (8
    SPARQL queries) + queries/defeasible/_meta.yaml, and the project_graph tests.
    run_competency_queries is now Cozo-only: it discovers queries from kg-queries/*.edn
    + a NEW assets/kg-queries/_meta.yaml manifest (which migrated the query class —
    coverage/consistency/defeasible — and the defeasible severities off the deleted
    .rq directory tree). capture_characterization.capture() now runs the EDN ports over
    a Cozo projection (kept its empty-ledger guard).

DELIBERATELY KEPT (not a deletion gap): rdflib stays — audit_taxonomy (an RDFS
ontology linter) and the book-thesis entailment/lint/exemplar layer
(dispatch_entailment, lint_supports, synthesize_exemplars) parse compile_thesis's
thesis-triples.ttl via rdflib; compile_thesis's TTL emit stays. So the end-state is
"Cozo is the sole CLAIM store," not "sole store." pyDatalog + the consistency.dl /
datalog_consistency pass are NOT yet removed (P5.4b).
</context>

<key_design_decisions_to_attack>
1. The deleted fallback is the headline risk. For EACH deleted capability, is the
   surviving Cozo path a faithful replacement on REAL data, or did a behaviour quietly
   change? (a) validate_shacl: pyshacl validated the projected TriG against shapes.ttl;
   the Cozo path validates the ledger projection via the 9 EDN constraints. Are there
   SHACL shapes in the deleted shapes.ttl with NO EDN-constraint equivalent (a lost
   check)? Diff shapes.ttl (in the patch) against assets/kg-constraints/*.edn. (b)
   run_competency: the 8 deleted .rq SPARQL vs the 8 kg-queries/*.edn — are all 8
   ported, and is the manifest's class/severity for each EXACTLY what the old
   queries/<class>/ tree + _meta.yaml encoded? Any query whose class changed (e.g. a
   defeasible query now mis-classified as coverage → no longer gates)?

2. The new kg-queries/_meta.yaml manifest. Confirm every query's class matches the old
   .rq directory it lived in, and every defeasible severity matches the old _meta.yaml.
   A silent downgrade (critical→minor, or defeasible→coverage) would make the QA gate
   stop blocking. Also: discover_queries now globs kg-queries/*.edn and skips
   `_`-prefixed files — does it correctly exclude _meta.yaml and include exactly the 8?

3. capture_characterization.capture() rewrite. It now writes goldens from cozo rows,
   but the COMMITTED query goldens are SPARQL binding-dicts (e.g. {"claim": "..."}),
   while cozo rows are lists — a FORMAT mismatch. Is that a latent trap (regenerating +
   committing would change the golden format and break test_query_ports' comparison)?
   The empty-ledger guard moved from "0 triples" to "ledger missing/empty" — does it
   still fire on the exact case test_capture_refuses_empty_dataset exercises, and could
   a non-empty ledger that projects to zero rows now slip through?

4. P5.2 counter-claim dedupe-to-latest. The Cozo projection now keeps one row per cc
   (latest status) instead of the full history. rebuttal-presence negates an "addressed"
   cc. Construct the case that diverges from the old (history-preserving) behaviour:
   a cc addressed-then-reopened. Is "the gate treats a reopened rebuttal as unaddressed"
   the intended product semantics, and is there any OTHER consumer of the counter-claim
   relation that relied on the full history?

5. book-compose's release-bundle non-conforming test now writes a RAW sourceless verified
   claim directly to the ledger (append_claim rejects it). Is that a faithful stand-in
   for the deleted RDF-injection (does cozo validate_shacl actually flag a sourceless
   verified claim as non-conforming — verified-derives + source-span-present)? Any risk
   the raw record desyncs from the real claim schema in a way that masks a regression?

6. Deletion completeness / dangling refs. Does ANYTHING still import or call the deleted
   project_graph / shapes.ttl / .rq / _validate_rdflib / _load_dataset / the canonical
   remap? Search the whole tree (incl. book-qa, book-review, neurosym-forge, docs,
   SKILL.md, runbooks). Are there docs/SKILL.md claiming a SHACL/SPARQL/TriG model that
   are now false? (The no-legacy-import scan test is NOT yet added — flag where it would
   catch a straggler.)

7. The rdflib-STAYS decision. Verify it's actually correct and complete: are
   dispatch_entailment / lint_supports / synthesize_exemplars + audit_taxonomy the ONLY
   remaining legitimate rdflib users, or did the deletion leave a module that SHOULD
   have been migrated still on rdflib? Is keeping compile_thesis's TTL emit truly
   required, or could the thesis layer read Cozo?

8. Determinism / cross-platform of the changed goldens + the manifest + the cozo
   capture writer (newline/sort/encoding on Windows).
</key_design_decisions_to_attack>

<artifacts>
git diff 45917e7..HEAD ; and these files on the branch:
- skills/book-knowledge/scripts/{validate_shacl.py, run_competency_queries.py, capture_characterization.py, project_ledger_cozo.py, booklogic_kg.py, cozo_store.py, audit_taxonomy.py}
- skills/book-knowledge/assets/kg-schema.edn
- skills/book-knowledge/assets/kg-constraints/*.edn   (the 9 EDN constraints — the SHACL replacement)
- skills/book-knowledge/assets/kg-queries/*.edn + kg-queries/_meta.yaml   (the 8 query ports + the new manifest)
- skills/book-knowledge/tests/{test_constraint_ports.py, test_presence_ports.py, test_validate_shacl.py, test_query_ports.py, test_run_competency_queries.py, test_cutover_gate.py, test_characterization.py, test_detect_conflicts.py}
- skills/book-knowledge/tests/golden/kg/*.json   (the frozen query + SHACL goldens)
- skills/book-thesis/scripts/{compile_thesis.py, dispatch_entailment.py, lint_supports.py, synthesize_exemplars.py, datalog_consistency.py, consistency_cozo.py}   (the rdflib-STAYS layer + the not-yet-removed pyDatalog)
- skills/book-compose/scripts/{query_chapter_evidence.py, sibling_skills.py}
- skills/book-compose/tests/test_build_release_bundle.py
- docs/audits/2026-06-17-kg-divergence-decisions.md
- docs/superpowers/plans/2026-06-17-homoiconic-kg-cutover.md   (P5.3/P5.4 tasks + the corrected scope)
- the DELETED files appear in the diff: assets/shapes.ttl, assets/queries/*.rq, scripts/project_graph.py
</artifacts>

<remaining_plan_to_stress_test>
P5.4b (NOT in this diff): extract DefectReport/_emit_pairs/_value_str out of
datalog_consistency (consistency_cozo imports them), delete datalog_consistency +
rules/consistency.dl + capture_consistency, wire the QA gate to consistency_cozo,
drop pyDatalog. Close-out: a test_no_legacy_import_after_cutover scan (ban
pyshacl/pyDatalog imports + TriG parsing, with a NARROW rdflib allowlist for
audit_taxonomy + the thesis layer), venv rebuilds without the dropped deps, docs.
Assess: is P5.4a a safe foundation for P5.4b, and what must the no-bypass scan
allowlist to avoid false positives on the legitimately-remaining rdflib users?
</remaining_plan_to_stress_test>

<deliverable>
Write the findings report to a file named **`audit.md`** with this shape:
- a one-paragraph verdict up top: is the cutover + P5.4a deletion SAFE TO MERGE to
  main, or are there blocking issues?
- a findings table: each issue tagged CRITICAL / IMPORTANT / MINOR, with file:line, a
  concrete reproduction or argument, and whether it affects REAL data
  (examples/bermuda-manual + real ledgers) or only synthetic fixtures.
- a section "Deleted-capability parity": for each deleted piece (pyshacl/shapes.ttl,
  the 8 .rq, project_graph), one line on whether the Cozo replacement is faithful and
  what (if anything) was lost.
- a section "P5.4b readiness": is the remaining pyDatalog removal cleanly scoped, and
  the exact allowlist the no-bypass scan needs.
End by disagreeing (or not) with the team's claims: that rdflib must stay (only
audit_taxonomy + the thesis TTL layer), and that every deleted SHACL shape / SPARQL
query has a faithful EDN/Cozo equivalent.
</deliverable>

<constraints>
- Distinguish real-data impact from synthetic-fixture-only impact for every finding.
- Do NOT file findings demanding rdflib's full removal — the thesis layer + audit_taxonomy
  legitimately keep it (that is the documented, intended end-state).
- pyDatalog / datalog_consistency / consistency.dl are intentionally still present (P5.4b).
- Prefer fixes expressible as EDN / CozoScript / small seam changes.
- Be honest about what is solid; the deletion may be largely clean.
</constraints>

</adversarial_audit>
```
