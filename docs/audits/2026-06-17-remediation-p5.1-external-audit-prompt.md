# External adversarial-audit prompt — P2.4+P3 remediation + P5.1 (for GPT-5.5)

Paste the XML below into GPT-5.5 (Deep Research Pro). Attach the branch diff
`git diff 0eddfdb..HEAD` (branch `feat/homoiconic-kg-p5`; `0eddfdb` is the end of
the PRIOR external audit's scope — `2026-06-17-p2.4-p3-external-audit-prompt.md`)
and, if the tool allows, the files in `<artifacts>`. This covers only the DELTA
since that audit: (a) the remediation of its three findings, and (b) Task P5.1
(the first cutover step). Earlier phases (C0, P2.1–2.4, P3.0–3.2) were audited
previously — do not re-audit them except where this delta changed them.

```xml
<adversarial_audit model="GPT-5.5 Deep Research Pro">

<role>
You are a skeptical staff engineer reviewing a small, high-stakes delta in a Python
monorepo of self-contained Claude Code "skills" (each with its own venv + a
top-level `scripts` package). The repo is mid-migration of a knowledge graph from
rdflib/SPARQL/SHACL + pyDatalog to a homoiconic "EDN front, Cozo back" store; the
legacy stack runs in PARALLEL behind characterization goldens and is deleted only
at the very end (P5.4, NOT in this diff). Two changes landed: (a) the remediation
of a prior external audit's CRITICAL + two IMPORTANTs, and (b) P5.1, the first
cutover step (porting a chapter-evidence reader off the TriG dataset onto Cozo, and
the cross-skill plumbing that required). Find correctness/parity/safety defects the
team's own reviews missed. Cite file:line. A credible audit is not uniformly
negative.
</role>

<context>
DELTA 1 — remediation (commit 94dd6a3) of the prior audit:
- CRITICAL fix: the Cozo consistency CLI (`book-thesis/scripts/consistency_cozo.py`)
  used to always exit 0 and write no artifact. Now `run_consistency_cozo` takes
  `write_artifact=False` (pure by default); `main()` calls it with True (writes
  `<ws>/qa/datalog-defects.json` exactly as `datalog_consistency.run` does) and
  returns `1 if gate_failed(payload) else 0`. `gate_failed(payload)` reads
  `summary.contradictions` / `summary.invariant_violations` and is meant to mirror
  `DefectReport.gate_failed()` (`bool(contradictions) or bool(invariants)`).
- IMPORTANT fix: `_ensure_bk_package` in BOTH `book-thesis` and `book-compose`
  `sibling_skills.py` now validates the cached process-global
  `_book_knowledge_scripts` alias `__path__` and raises `SiblingNotFoundError` on
  mismatch instead of silently serving a different book-knowledge root.
- IMPORTANT fix: documented that a wrong-typed confidence is a DELIBERATE contract
  DIVERGENCE — Cozo's typed `Float?` column makes `CozoStore.load` raise a
  `QueryException` (verified) whereas rdflib/pyshacl reports an `sh:datatype`
  ShaclReport violation. A characterization test pins the load-raise.
- Defensive: `validate_shacl._build_canonical_messages` now raises on a duplicate
  `(path, component)` key.

DELTA 2 — Task P5.1 (commit 8582b59, REQ-KG-019):
- `book-compose/scripts/query_chapter_evidence.py` reborn on Cozo: build a
  `CozoStore` from book-knowledge's `kg-schema.edn`, run `project_ledger` (the
  relational projection of the claim LEDGER), then a booklogic `defquery` joining
  `claim-chapter{claim-id, chapter}` with `claim{id, status:"verified"}` for a
  target chapter URI. The old version ran SPARQL over the parsed TriG dataset.
- `book-compose/scripts/sibling_skills.py`: `book_knowledge_root()` now resolves
  the IN-REPO sibling first (the installed `~/.claude/skills/book-knowledge` is
  stale and, on the dev box, ABSENT), falling back to `~/.claude`. This flips ALL
  of book-compose's book-knowledge module loads (workspace, ledger, project_graph,
  validate_shacl, cozo_store, project_ledger_cozo) to the repo copy.
- `book-compose/pyproject.toml` + venv: added `edn_format` + `pycozo[embedded]`.
- `audit_taxonomy` (book-knowledge) was DELIBERATELY left as an rdflib RDFS-ontology
  linter (its `rdfs:subClassOf` data shape has no claim-model source), excluded from
  the cutover — not ported, not deleted; the P5.3 no-bypass scan must allowlist it.
</context>

<key_design_decisions_to_attack>
1. CLI gate parity. Does `gate_failed(payload)` EXACTLY reproduce
   `DefectReport.gate_failed()` for every case — including a report with only D11
   defects that are NOT invariant_violations (declared_conflict / unreachable_supports
   / sub_arg_no_chapter / missing_evidence all live in the `invariants` bucket and so
   in `summary.invariant_violations`)? Is the written `qa/datalog-defects.json`
   byte-identical to the pyDatalog pass's (same `json.dumps(..., indent=2,
   sort_keys=True) + "\n"`, same encoding/newline on Windows)? Is `run_consistency_cozo`
   genuinely side-effect-free when `write_artifact=False` (so the bermuda parity call
   doesn't dirty the real workspace)?
2. Alias path-guard correctness. `_ensure_bk_package` compares
   `existing.__path__ == [str(bk_scripts)]`. Can this FALSE-POSITIVE (raise when the
   two roots are the same dir but differ in string form — trailing slash, case on
   Windows, forward vs backslash, a symlink/junction vs real path, `..` segments)?
   Can it FALSE-NEGATIVE (a stale alias whose `__path__` was mutated)? Now that BOTH
   book-thesis and book-compose resolve book-knowledge repo-first to the SAME repo
   dir, is the guard ever exercised, or dead? Is raising the right behavior vs
   re-pointing?
3. query_chapter_evidence parity — the load-bearing one. Is the Cozo result-set
   EQUAL to the old SPARQL for ALL inputs, not just the test's "ch-03"? Specifically:
   (a) CHAPTER-URI QUOTING — `project_ledger_cozo` stores `claim-chapter.chapter` as
   `{BASE}chapters/{quote(chapter)}`, but the new query matches the literal
   `{BASE}chapters/{chapter_id}` (NO quote). For a chapter id needing escaping
   (space, slash, unicode, '#'), do these diverge — and did the OLD SPARQL (which
   compared `STR(?chapter)` to an unquoted `target_str` against project_graph's
   quoted URIs) have the same or different behavior? Which is "correct"? (b)
   project_ledger drops `superseded` claims and dedups latest-per-id; did the old
   SPARQL over the TriG do the same (project_graph's emission filter)? Construct an
   input where a claim is verified-then-superseded, or appears twice, and check both
   paths agree. (c) a claim supporting MULTIPLE chapters; (d) status other than
   verified.
4. book-compose repo-first blast radius. Flipping `book_knowledge_root()` to
   repo-first changes which `validate_shacl` book-compose's preflight/release-bundle
   load — now the repo one (with the new `component` field, the `(path,component)`
   remap, `KG_BACKEND` dispatch). Does book-compose's preflight behave IDENTICALLY
   (it consumes `.conforms` / `len(violations)`)? Any path where the repo modules
   need a dep book-compose's venv still lacks (beyond the added edn_format/pycozo)?
   Does loading project_graph/project_ledger_cozo from repo change any emitted URI
   or row vs the previously-loaded installed copy?
5. audit_taxonomy exclusion. Is leaving it an rdflib tool sound for the cutover, or
   does some consumer/gate expect it to read the unified store? Will the P5.3
   no-bypass scan (which forbids `rdflib`/`format="trig"`/`.parse(layout.dataset`)
   need a precise allowlist entry, and is "audit_taxonomy reads RDFS subclass triples
   that the pipeline never emits" actually TRUE (grep for any emitter)?
6. Determinism / cross-platform: the artifact write, the defquery string built by
   f-string interpolation of a URI (any injection/escaping risk if chapter_id
   contained a quote?), and the sorted result set.
</key_design_decisions_to_attack>

<artifacts>
git diff 0eddfdb..HEAD ; and these files on the branch:
- skills/book-thesis/scripts/consistency_cozo.py
- skills/book-thesis/scripts/datalog_consistency.py  (the legacy pass + DefectReport.gate_failed/as_payload it must match)
- skills/book-thesis/scripts/sibling_skills.py
- skills/book-knowledge/scripts/validate_shacl.py  (the dup-key guard)
- skills/book-knowledge/assets/kg-constraints/confidence-present.edn  (the datatype-divergence note)
- skills/book-knowledge/scripts/audit_taxonomy.py
- skills/book-compose/scripts/query_chapter_evidence.py
- skills/book-compose/scripts/sibling_skills.py
- skills/book-compose/scripts/project_ledger_cozo.py ... (it lives in book-knowledge: skills/book-knowledge/scripts/project_ledger_cozo.py — the _chapter_uri quoting)
- skills/book-knowledge/scripts/project_graph.py  (the RDF chapter-URI emission the old SPARQL matched)
- skills/book-compose/tests/test_query_chapter_evidence.py
- skills/book-thesis/tests/test_consistency_cozo_parity.py  (the CLI-gate tests)
- skills/book-thesis/tests/test_cross_skill_cozo_import.py  (the alias-guard test)
- skills/book-knowledge/tests/test_presence_ports.py  (the wrong-type + dup-key tests)
- docs/superpowers/plans/2026-06-17-homoiconic-kg-cutover.md  (P5.1 decisions + the P5.3 cutover-gate checklist)
</artifacts>

<remaining_plan_to_stress_test>
Still ahead: P5.2 (reconcile 3 documented RDF<->Cozo query divergences), P5.3 (flip
KG_BACKEND default to cozo + the 6-point cutover gate — gated on a FULL cozo-green
suite; KNOWN BLOCKER: run_competency_queries + the RDF-injection fixtures aren't
cozo-green), P5.4 (delete rdflib/pyshacl/pyDatalog + the parallel pyDatalog pass +
compile_thesis's TTL emit; KEEP audit_taxonomy). Given P5.1 flipped book-compose to
repo-first and added the Cozo deps, assess: is book-compose now a sound base for the
default flip, and does the no-bypass scan design (with an audit_taxonomy allowlist)
hold? What must P5.3 assert about query_chapter_evidence specifically (chapter-URI
quoting parity, superseded-claim handling)?
</remaining_plan_to_stress_test>

<deliverable>
A findings report: each issue tagged CRITICAL/IMPORTANT/MINOR with file:line, a
concrete reproduction or argument, and whether it affects REAL data
(examples/bermuda-manual + real ledgers) or only synthetic fixtures. Then: a verdict
on whether the remediation fully closed the prior audit's three findings; whether
the query_chapter_evidence port is result-set equal to the SPARQL it replaces (call
out any chapter-URI-quoting or superseded-claim divergence explicitly); and whether
book-compose's repo-first flip is safe. Be specific about what P5.3's gate must add.
</deliverable>

<constraints>
- Distinguish real-data impact from synthetic-fixture-only impact for every finding.
- The legacy stack is intentionally still present (deleted only in P5.4) — no
  "dead code" findings against rdflib/pyshacl/pyDatalog or the parallel passes;
  audit_taxonomy is intentionally still rdflib.
- Do not propose changes that break the valid examples/bermuda-manual workspace.
- Prefer fixes expressible as EDN / CozoScript / small seam changes.
- Be honest about what is solid; this is a small delta and may be largely clean.
</constraints>

</adversarial_audit>
```
