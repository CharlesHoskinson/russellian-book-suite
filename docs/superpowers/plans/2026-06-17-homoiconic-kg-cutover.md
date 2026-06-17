# Homoiconic KG Cutover Implementation Plan (P2 + P3 + P5)

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use `- [ ]`. Each phase below is a SEPARATE PR ("one problem per PR"). Run the full suite per skill before each PR.

**Goal:** Retire the dual knowledge-graph stack. Replace SHACL with EDN constraints (P2), replace pyDatalog with an EDN→Cozo consistency pass (P3), then delete `rdflib`/`pyshacl`/`pyDatalog`, `project_graph`'s RDF emit, `shapes.ttl`, the `.rq` files, and `compile_thesis`'s TTL emit — making Cozo the sole store across `book-knowledge`, `book-compose`, and `book-thesis` (P5).

**Architecture:** "EDN front, Cozo back" (already shipped for queries in P0+P1, for code in P4). The booklogic compiler gains `defconstraint` lowering; projectors gain thesis. `validate_shacl(layout)->ShaclReport` and `run_consistency` keep their public contracts but swap engines underneath, routed through `cozo_store` (no module but `cozo_store` imports `pycozo`). The legacy stack runs in PARALLEL behind characterization goldens until the final cutover gate is green; deletion is the last, revert-able step.

**Tech Stack:** Python 3.14, pycozo (embedded Cozo), edn_format, pytest. Spec: `openspec/changes/homoiconic-kg-edn-front-cozo-back/specs/homoiconic-kg/spec.md` (REQ-KG-009..020). Surface map: this plan's "Cutover surface" appendix.

**Test rigor (non-negotiable, baked into every phase):**
1. **Characterization-first** — a committed golden exists before any behaviour is ported (REQ-KG-005/014). Goldens captured on BOTH bermuda AND a deliberately-violating fixture; the violating golden must be non-empty (no vacuous ports).
2. **Parity** — every port asserts result-set equality vs the legacy engine on both fixtures.
3. **Cross-skill integration** — book-compose preflight/book_preflight/build_release_bundle keep identical pass/fail verdicts through the new path.
4. **Determinism pins** — two-run byte-identical projected rows + canonically-ordered result sets.
5. **No-bypass scans** — after cutover, no source module imports `rdflib`/`pyshacl`/`pyDatalog` or parses/writes the TriG dataset.
6. **Cutover gate** — deletion blocked until all of the above are green (REQ-KG-018).
7. **Adversarial audit** — external GPT audit (audit.md) + two-stage internal review (spec then quality) per task.

---

## Cutover surface (appendix — read before starting)

| Component | File | Public API to preserve | Cross-skill callers |
|---|---|---|---|
| RDF emit | `book-knowledge/scripts/project_graph.py` | `project_graph(layout)->Path` (TriG) | tests; indirectly every TriG reader |
| SHACL gate | `book-knowledge/scripts/validate_shacl.py` + `assets/shapes.ttl` | `validate_shacl(layout)->ShaclReport{conforms,violations[focus_node,path,message],text}` | book-compose `preflight.py:36`, `book_preflight.py:73`, `build_release_bundle.py:36` |
| Competency queries | `assets/queries/*.rq` (8) + `assets/kg-queries/*.edn` (8) | `run_competency_queries(layout)` (KG_BACKEND flag, default `rdflib`) | book-compose; characterization |
| Consistency | `book-thesis/scripts/datalog_consistency.py` + `rules/consistency.dl` | D9/D10/D11 defect report → `qa/datalog-defects.json` | book-thesis QA gate |
| Thesis emit | `book-thesis/scripts/compile_thesis.py` | TTL → `.knowledge/thesis-triples.ttl` | read by datalog_consistency |
| Other RDF readers | `book-compose/scripts/query_chapter_evidence.py`, `book-knowledge/scripts/audit_taxonomy.py` | parse `layout.dataset` TriG | (the deadlock the auditor caught) |
| Status vocabulary | JSON schema `assets/claim-record.schema.json:10`; `shapes.ttl:19` `sh:in`; `claim_validator.VALID_TRANSITIONS:12-18`; `kg-schema.edn` | 5 states proposed/verified/disputed/superseded/refuted | all claim writes |
| Deps | `book-knowledge`, `book-compose`, `book-thesis` pyproject.toml | `rdflib`/`pyshacl`/`pyDatalog` pins + `filterwarnings` | — |

The 8 query goldens already exist under `book-knowledge/tests/golden/kg/`. SHACL-report and D9–D11 goldens do NOT yet exist (C0 creates them).

Run tests: `cd skills/<skill> && .venv/Scripts/python.exe -m pytest tests/ -q`.

---

# PHASE C0 — Characterization completion (PR #1)

Freeze the goldens for everything P2/P3 will replace, BEFORE touching it. Skill: `book-knowledge` (+ a thesis golden under book-thesis).

## Task C0.1: a deliberately-violating fixture workspace

**Files:**
- Create: `skills/book-knowledge/tests/fixtures/violating-workspace/` (a minimal `init_workspace` tree with a claims ledger that triggers each SHACL constraint: a claim with status not in the enum is impossible at write-time, so instead include: a `verified` claim with NO source-span (fires the `sh:sparql` "must derive from a source-span" + `hasSourceSpan` minCount), a claim with `confidence` 1.5 (out of range), a chapter section citing a non-verified claim (fires ChapterSectionShape)). Build it programmatically in a fixture helper rather than committing raw RDF.
- Create: `skills/book-knowledge/tests/fixtures/violating_workspace.py` — `build_violating_workspace(tmp_path) -> WorkspaceLayout` using `init_workspace` + `append_claim`, then `project_graph(layout)` to emit its TriG.

- [ ] **Step 1:** write `build_violating_workspace`; assert it produces a TriG dataset with >0 triples and that `validate_shacl` on it returns `conforms == False` with ≥3 violations. RED (helper missing) → GREEN.
- [ ] **Step 2:** Commit `kg(C0.1): violating-workspace fixture for non-vacuous constraint goldens`.

## Task C0.2: SHACL report golden

**Files:**
- Modify: `skills/book-knowledge/scripts/capture_characterization.py` — add `capture_shacl(workspace, out_dir)` that writes a canonical JSON golden of the `ShaclReport` (conforms + sorted violations as `[{focus_node,path,message}]`).
- Create: `skills/book-knowledge/tests/golden/kg/shacl_report_bermuda.json`, `shacl_report_violating.json`.
- Modify: `skills/book-knowledge/tests/test_characterization.py` — add `shacl_report_bermuda` / `shacl_report_violating` to the required-goldens set; add `test_violating_fixture_goldens_nonempty` (the violating SHACL golden has ≥1 violation).

- [ ] **Step 1 (RED):** `test_required_goldens_present[shacl_report_bermuda]` fails (golden absent).
- [ ] **Step 2 (GREEN):** implement `capture_shacl`; generate both goldens (bermuda via its committed dataset; violating via the C0.1 fixture). Canonical sort identical to `_canonical_rows`.
- [ ] **Step 3:** `test_violating_fixture_goldens_nonempty` passes. Commit `kg(C0.2): freeze SHACL conformance/violation goldens (REQ-KG-014)`.

## Task C0.3: D9–D11 consistency golden

**Files:**
- Create: `skills/book-thesis/tests/fixtures/violating_thesis.py` — a thesis YAML + ledger that triggers D9 (orphan sub-argument), D10 (transitive contradiction), D11 (invariant violation).
- Modify: `skills/book-thesis/scripts/datalog_consistency.py` OR add `skills/book-thesis/scripts/capture_consistency.py` — capture the D9/D10/D11 defect set to a canonical JSON golden.
- Create: `skills/book-thesis/tests/golden/consistency/d9_d11_bermuda.json`, `d9_d11_violating.json`.
- Create/Modify: `skills/book-thesis/tests/test_characterization_consistency.py` — required-goldens-present + non-vacuity for the violating golden.

- [ ] **Step 1 (RED):** golden-present test fails.
- [ ] **Step 2 (GREEN):** run the existing pyDatalog `datalog_consistency` on bermuda + the violating fixture; freeze the defect sets. The violating golden must contain ≥1 of each D9/D10/D11.
- [ ] **Step 3:** Commit `kg(C0.3): freeze D9-D11 consistency goldens (REQ-KG-014)`.

**PR #1 gate:** full `book-knowledge` + `book-thesis` suites green; goldens committed; no production behaviour changed.

---

# PHASE P2 — SHACL → EDN constraints (PR #2)

Skill: `book-knowledge` (+ a no-op import check in book-compose). The legacy `pyshacl` path stays; we add the Cozo path behind the SAME `validate_shacl` contract and prove parity.

## Task P2.1: status vocabulary single source (REQ-KG-009 / REQ-KG-009b / REQ-KG-020)

**Files:**
- Create: `skills/book-knowledge/assets/status-enum.edn` — the single source: `{:states [:proposed :verified :disputed :superseded :refuted] :transitions {:proposed #{:verified :disputed :superseded} :verified #{:disputed :superseded} :disputed #{:verified :superseded :refuted} :superseded #{} :refuted #{}}}`.
- Modify: `skills/book-knowledge/scripts/claim_validator.py` — derive `VALID_TRANSITIONS` from `status-enum.edn` (load + parse), not a literal dict.
- Modify: `kg-schema.edn` — (if it carries a status enum) reference the same values; otherwise leave (status is a free string column, enforced by the constraint).
- Decision: `assets/claim-record.schema.json` keeps its literal enum for now (JSON Schema cannot `$ref` an EDN file); add `tests/test_status_enum_single_source.py::test_json_schema_matches_edn_source` to PIN that the JSON-Schema enum equals the EDN states (drift guard, since JSON Schema can't derive). The SHACL `sh:in` source is deleted in P5, removing one copy.
- Create: `skills/book-knowledge/tests/test_status_enum_single_source.py` — `test_one_source_feeds_both`, `test_no_second_enum_copy` (the SHACL `sh:in` and the validator literal are gone/derived), `test_transition_matrix_uses_single_source`, `test_json_schema_matches_edn_source`.

- [ ] **Step 1 (RED):** `test_transition_matrix_uses_single_source` — assert `claim_validator.VALID_TRANSITIONS` is derived (e.g. mutate the loaded EDN states in a monkeypatched copy and confirm the validator can't name an out-of-source status). Fails (currently a literal).
- [ ] **Step 2 (GREEN):** add `status-enum.edn`; rewrite `VALID_TRANSITIONS` to load+build from it (keep the exact same transitions — characterized by existing `test_claim_validator.py`).
- [ ] **Step 3:** run `test_claim_validator.py` (unchanged behaviour) + the new tests. Commit `kg(P2.1): single EDN status source feeds validator + transition matrix (REQ-KG-009/020)`.

## Task P2.2: `defconstraint` → Cozo violation-rule compiler (REQ-KG-003 / REQ-KG-012)

**Files:**
- Modify: `skills/book-knowledge/scripts/booklogic_kg.py` — add `compile_constraint(edn, schema_path) -> str`, a PURE function lowering a `defconstraint` to a CozoScript rule that yields violation rows `[focus_node, path, message]`. Reuse the existing variable-lowering / join / negation / filter machinery from `compile_query`.
- Create: `skills/book-knowledge/assets/kg-constraints/*.edn` — one `defconstraint` per SHACL constraint:
  - `status-enum.edn` — `:violation` when `?status` not in the enum (compiled from `status-enum.edn` states): focus=claim, path="tbf:status", message from the constraint.
  - `confidence-range.edn` — `?confidence < 0.0 or > 1.0`.
  - `text-cardinality.edn` — claim missing `canonical-text` (minCount 1) — note: maxCount 1 is guaranteed by the projector (one row per claim), document that.
  - `source-span-present.edn` — claim with no source-span (minCount 1).
  - `verified-derives.edn` — the `sh:sparql`: `verified` claim with no source-span (semantically equal to source-span-present for verified; reproduce as its own message to match the SHACL violation text).
  - `chapter-cites-verified.edn` — chapter section citing a non-verified claim.
- Create: `skills/book-knowledge/tests/test_booklogic_constraint_compile.py` — golden EDN→CozoScript per constraint (byte-identical, REQ-KG-003); `test_compile_without_store`; undeclared-entity error.

- [ ] **Step 1 (RED):** `test_defconstraint_golden` — compile `confidence-range.edn`, assert byte-identical to a committed golden string. Fails (no `compile_constraint`).
- [ ] **Step 2 (GREEN):** implement `compile_constraint`; author the goldens by running the compiler against a live store first to confirm the CozoScript is valid, THEN freeze. (Same discipline as the P0 compiler: tests EXECUTE against real Cozo, not just string-match.)
- [ ] **Step 3:** Commit `kg(P2.2): defconstraint->Cozo violation-rule compiler + constraint EDN (REQ-KG-003/012)`.

## Task P2.3: Cozo-backed `validate_shacl` + parity (REQ-KG-012 / REQ-KG-013)

**Files:**
- Modify: `skills/book-knowledge/scripts/validate_shacl.py` — add a `_validate_cozo(layout) -> ShaclReport` path (projects the ledger via `project_ledger`/`project_graphify`-style into a `CozoStore`, runs each compiled constraint, assembles `ShaclReport`). Gate behind `KG_BACKEND` (default still `rdflib`). Route store access through `cozo_store` only (REQ-KG-002b). Keep `ShaclReport`/`Violation` dataclasses unchanged.
- Create: `skills/book-knowledge/tests/test_constraint_ports.py` — `test_constraints_match_shacl_golden` (Cozo path conforms+violations result-set equal to the C0.2 goldens on bermuda AND violating fixture).
- Modify: `skills/book-knowledge/tests/test_validate_shacl.py` — `test_cozo_path_matches_contract` (same `ShaclReport` shape + `conforms` verdict both paths); `test_callers_import_unchanged` (import `book-compose` preflight/book_preflight/build_release_bundle modules via `sibling_skills`, assert `validate_shacl` is called with the `(layout)` signature — a smoke that the contract holds).

- [ ] **Step 1 (RED):** `test_constraints_match_shacl_golden` fails (no Cozo path).
- [ ] **Step 2 (GREEN):** implement `_validate_cozo`; reconcile violation `focus_node`/`path` representation with the SHACL golden (the focus node is a claim URI in SHACL; decide canonical form — claim id vs URI — and record it; update the C0.2 golden ONLY if you consciously choose the corrected form, documenting it as a divergence like the query ports did).
- [ ] **Step 3:** both paths green on both fixtures; `test_callers_import_unchanged` green. Commit `kg(P2.3): Cozo-backed validate_shacl behind contract + parity (REQ-KG-012/013)`.

**PR #2 gate:** full `book-knowledge` suite green; `KG_BACKEND=cozo pytest` AND default both green; book-compose suite green (unchanged). Recursive-SHACL: confirm in the PR description that neither shape is recursive (they aren't — record it, satisfies the P2 fixpoint task).

## Task P2.4: close the Cozo presence/datatype gap (post-audit — REQ-KG-012)

External audit (2026-06-17, GPT-5.5) finding, confirmed against branch: the EDN→Cozo port only ports the constraints whose violation is a *bound value* (status `sh:in`, confidence range) plus the two minCount negations already done (`text-cardinality`, `source-span-present`). It does NOT port **`tbf:status` minCount**, **`tbf:confidence` minCount**, or the two **`sh:datatype`** checks (`schema:text` `xsd:string`, `tbf:confidence` `xsd:decimal`). `CozoStore` makes value columns nullable and back-fills missing fields with `None` (`cozo_store.py:163,397`), and the value filters guard nulls away (`booklogic_kg.py:269`) — so under `KG_BACKEND=cozo` a claim missing `status`/`confidence`, or carrying a wrong-typed `confidence`, **conforms**, while pyshacl flags it. Real ledger data is shielded by `claim-record.schema.json`, but a projector or hand-edited-ledger regression escapes the Cozo gate — and the gate silently weakens the moment **P5.3 flips the default to cozo**. This is the substance behind the audit's verdict caveat.

**Files:**
- Create: `assets/kg-constraints/status-present.edn`, `confidence-present.edn` — minCount-1 negations on `tbf:status` / `tbf:confidence` (mirror the `source-span-present` negation shape, not the value-filter shape, so absent ≠ dropped).
- Create: `assets/kg-constraints/{text,confidence}-datatype.edn` — datatype guards. Decide first whether Cozo's typed columns already make a wrong type *unrepresentable* (if `confidence` is a typed `Float?` column, a string row can't load — then the gap is a *load-time crash*, not a silent conform, and the fix is a typed-load error surfaced as a violation rather than a new constraint; see I-2 residual). Port only the checks that are representable; document any that the column typing subsumes.
- Modify: `scripts/validate_shacl.py` — **fix finding #2 (= internal I-2) here, because this task is what activates it:** re-key `_build_canonical_messages` / `_normalize_pyshacl_violations` on a stable `constraint_id` (or `(path, sh:sourceConstraintComponent)`) instead of bare `sh:path`. Adding minCount on the `confidence` path puts a *second* distinct message on that path, so the path-keyed map (`validate_shacl.py:107,140`) would now silently collapse range-vs-minCount. Alternatively drop `message` from the engine-parity contract and assert messages in a separate test.
- Modify: `tests/fixtures/violating_workspace.py` (+ `_raw`) — add a status-less and a confidence-less row, and a wrong-typed-confidence row, so the new constraints are exercised non-vacuously (also closes internal M-1: `status-enum`/`text-cardinality` currently unexercised by the golden).
- Modify: the C0.2 goldens (`shacl_report_violating.json` + `_raw`) — regenerate; the new violations must appear in BOTH engines. Note the regeneration in the run log (same de-circularization discipline as I-1).

- [ ] **Step 1 (RED):** new fixture rows produce violations under rdflib but NOT under cozo (demonstrates the gap); message-collision test fails on the confidence path.
- [ ] **Step 2 (GREEN):** add the EDN constraints + re-key the message map; both engines now agree on the enlarged violation set.
- [ ] **Step 3:** default + `KG_BACKEND=cozo` suites green; goldens non-vacuous. Commit `kg(P2.4): port status/confidence minCount+datatype; key parity on constraint_id (REQ-KG-012, audit I-2)`.

**Ordering:** P2.4 is a hard prerequisite for **P5.3** — do not flip the default backend until the Cozo gate is at parity with pyshacl on presence/datatype, or the cutover ships a weaker runtime gate than it replaces.

---

# PHASE P3 — Retire pyDatalog (PR #3)

Skill: `book-thesis` (+ `book-knowledge` for the consistency compiler if shared). Legacy pyDatalog stays; add the Cozo path + parity.

**Cross-skill import decision (resolves the run-handoff blocker) — RESOLVED to option (b).** P3 needs book-thesis to import book-knowledge's Cozo modules. The plan and external audit initially leaned to option (c) (a new shared package both skills install). On inspecting the code at implementation time that premise weakened: the repo ALREADY has the aliased cross-skill loader (`book-compose`/`book-review` `sibling_skills.py`) AND a repo-relative fallback pattern (`feynman_style_root()` tries `~/.claude/skills/<name>` then falls back to the in-repo sibling). There is NO existing shared-package pattern; every skill is self-contained with its own venv. So **option (b) is chosen** (user-confirmed 2026-06-17): give book-thesis a `sibling_skills.py` whose `book_knowledge_root()` mirrors `feynman_style_root()` (installed-then-repo fallback) and loads `cozo_store` / `booklogic_kg` / `project_ledger_cozo` under the `_book_knowledge_scripts` alias. The one blocker — `booklogic_kg.py:87` uses an absolute `from scripts.cozo_store import to_snake` that breaks under aliased loading — is fixed by making it relative (`from .cozo_store import to_snake`), matching how `validate_shacl.py` already imports it. (c) was judged to fight the self-contained-skill architecture for too little gain; **avoid (a)** (sync `~/.claude` ← repo) — it re-couples the repo to installed-copy state. Done either way: `pycozo[embedded]` + `edn_format` added to book-thesis's `pyproject.toml` + venv (DONE). This is **Task P3.0**, before P3.1, so the projector imports cleanly.

## Task P3.1: `thesis→cozo` projector (REQ-KG-016)

**Files:**
- Create: `skills/book-thesis/scripts/project_thesis_cozo.py` — `project_thesis(workspace, store)`: read `thesis/<id>.yaml`, load `thesis-node`/`sub-argument`/invariant rows into Cozo per `kg-schema.edn` (entities already declared at lines ~140-151; add an `invariant` entity if absent). Leave the YAML unmodified. Mirror `project_ledger_cozo` patterns (synthetic ids via SHA1 `\x1f`-join).
- Create: `skills/book-thesis/tests/test_thesis_projector.py` — `test_projects_thesis_nodes` (rows land; YAML byte-identical before/after), determinism (two-run identical).
- Modify (if needed): `kg-schema.edn` — add `invariant` entity; update `book-knowledge/tests/test_kg_schema.py::EXPECTED_ENTITIES`.

- [ ] **Step 1 (RED):** `test_projects_thesis_nodes` fails (module missing).
- [ ] **Step 2 (GREEN):** implement; reuse `CozoStore.in_memory`.
- [ ] **Step 3:** Commit `kg(P3.1): thesis->cozo projector (REQ-KG-016)`.

## Task P3.2: D9–D11 EDN→Cozo consistency pass + parity (REQ-KG-015)

**Files:**
- Create: `skills/book-thesis/assets/kg-consistency/d9_orphan.edn`, `d10_contradiction.edn`, `d11_invariant.edn` — booklogic queries over the thesis+claim Cozo relations reproducing each defect class. (D10 transitive contradiction needs recursive Datalog — Cozo supports recursive rules; pin the recursive form against a live store, like P4.2's PageRank caveat.)
- Modify: `skills/book-thesis/scripts/datalog_consistency.py` — add a `KG_BACKEND=cozo` path: `project_thesis` + `project_ledger` into one store, run the EDN consistency queries, emit the SAME `qa/datalog-defects.json` shape and the SAME exit codes (0 clean / 1 on D10|D11). Keep the pyDatalog path as default until the gate.
- Create: `skills/book-thesis/tests/test_consistency_ports.py` — `test_d9_d11_match_golden` (Cozo defect set result-set equal to the C0.3 goldens on bermuda + violating fixture).

- [ ] **Step 1 (RED):** `test_d9_d11_match_golden` fails.
- [ ] **Step 2 (GREEN):** author the EDN, executing against a live store; reconcile any RDF↔Cozo defect-shape divergence (document if intentional).
- [ ] **Step 3:** both paths green on both fixtures; exit codes identical. Commit `kg(P3.2): D9-D11 EDN->Cozo consistency pass + parity (REQ-KG-015)`.

**PR #3 gate:** full `book-thesis` suite green; both backends green. (pyDatalog NOT yet removed — that's the gate in P5.)

---

# PHASE P5 — Cutover (PR #4, then PR #5 for deletion)

## Task P5.1: port the remaining RDF-dataset readers (REQ-KG-019)

**Decisions (user-confirmed 2026-06-17):**
- **`audit_taxonomy` is OUT of the claim-graph cutover scope.** Its test injects raw `rdfs:subClassOf` Turtle and asserts detection, but the claim/thesis projection NEVER emits subClassOf — it is a standalone RDFS-ontology linter orthogonal to the homoiconic claim store, with no claim-model source to project into a Cozo `taxonomy` relation. So it stays an rdflib tool: NOT ported, NOT deleted in P5.4. The P5.3 no-bypass scan must ALLOWLIST it (it legitimately uses rdflib, but never reads the claim dataset/TriG the cutover retires).
- **`query_chapter_evidence` (book-compose) is ported via the P3.0 pattern.** book-compose gets the same cross-skill treatment book-thesis got: repo-sibling-first `book_knowledge_root()` (+ alias path-guard) in its `sibling_skills.py`, and `edn_format` + `pycozo[embedded]` added to its venv/pyproject. The query becomes a defquery over the existing `claim` + `claim-chapter` relations (verified claims supporting a chapter), projected by `project_ledger_cozo` — no TriG parsing.

**Files:**
- Modify: `skills/book-compose/scripts/sibling_skills.py` — `book_knowledge_root()` resolve the in-repo sibling first, `~/.claude` fallback; `_ensure_bk_package` validates the cached alias `__path__`.
- Modify: `skills/book-compose/pyproject.toml` + venv — add `edn_format`, `pycozo[embedded]`.
- Modify: `skills/book-compose/scripts/query_chapter_evidence.py` — build a `CozoStore`, `project_ledger`, run the chapter-evidence defquery; drop the SPARQL/TriG path.
- The existing `tests/test_query_chapter_evidence.py` (seeds via `append_claim`+`project_graph`, so the ledger is present) is the characterization oracle; add a no-TriG test proving the cutover (works with the dataset absent, ledger present). `audit_taxonomy` is left untouched.

- [ ] **Step 1 (RED):** capture goldens from the rdflib path; write the parity test; it fails for the not-yet-ported Cozo path.
- [ ] **Step 2 (GREEN):** port both; result-set equal; neither parses TriG.
- [ ] **Step 3:** Commit `kg(P5.1): port query_chapter_evidence + audit_taxonomy to Cozo (REQ-KG-019)`.

## Task P5.2: reconcile the 3 divergences (REQ-KG-017)

**Files:**
- Modify: `skills/book-knowledge/assets/kg-queries/{stale_after_source_refresh,unsupported_claims}.edn` + the relevant projector quirks in `project_ledger_cozo.py`.
- Create: `docs/audits/2026-06-17-kg-divergence-decisions.md` — record the chosen canonical semantics for each of the 3 divergences.
- Update the affected goldens under `tests/golden/kg/` to the canonical semantics.

- [ ] **Step 1:** decide each (recommended: adopt the Cozo `doc_id` join for stale; adopt source-span-only negation for unsupported and project `derived_from` only if a real workspace needs it; drop the `wiki/wiki/` double prefix and dedupe `ccStatus` to latest-per-id). Record decisions.
- [ ] **Step 2 (RED→GREEN):** update goldens + queries; `test_query_ports.py::test_all_eight_match_golden` green against reconciled goldens; add synthetic-fire tests proving the corrected semantics actually fire (non-vacuous).
- [ ] **Step 3:** Commit `kg(P5.2): reconcile 3 RDF<->Cozo divergences to canonical semantics (REQ-KG-017)`.

## Task P5.3: flip default backend + cutover gate (REQ-KG-010 / REQ-KG-018)

**Prerequisite (audit):** **P2.4 must be complete** — flipping the default to cozo while the Cozo gate skips status/confidence presence + datatype ships a runtime gate strictly weaker than the pyshacl one it replaces. The cutover-gate test below must therefore also assert presence/datatype parity, not just the 8-query + range goldens.

**Cutover-gate assertions (from the P2.4+P3 external audit, 2026-06-17 — the gate MUST check all of these):**
1. Cozo and legacy **consistency** produce identical defect payloads on a non-vacuous violating fixture AND a real clean workspace (not just the all-zero bermuda golden, which is a clean smoke test, not proof).
2. **CLI exit codes match** the legacy gate: clean → 0, defects → nonzero. (`consistency_cozo.main` now does this + writes `qa/datalog-defects.json` in the legacy shape — P2.4/P3.2 audit fix; the gate must keep asserting it.)
3. `qa/datalog-defects.json` is written in the same shape by whichever pass the gate invokes.
4. **SHACL parity** explicitly covers missing-status, missing-confidence, AND the wrong-type confidence/text behaviour. NB: wrong-type is a DOCUMENTED contract DIVERGENCE, not equivalence — Cozo raises a load-time `QueryException` where rdflib reports an `sh:datatype` violation; the gate must assert the *intended* behaviour for each engine, not assume equality.
5. **Cross-skill imports** are tested in ONE interpreter with conflicting repo/installed roots (the `_book_knowledge_scripts` alias now validates its `__path__` and raises on mismatch — P3.0 audit fix).
6. Cutover CI must **FAIL (not silently skip)** if the real `examples/bermuda-manual` fixture is absent — a skipped real-data leg is not parity proof.

**Added by the remediation+P5.1 external audit (2026-06-17):**
7. **`qa/datalog-defects.json` byte/text comparison** — assert the Cozo CLI's artifact is byte-identical to the legacy pass's (a JSON-parse compare misses newline/sort/encoding drift; book-thesis `test_cozo_artifact_byte_identical_to_legacy` already does this — extend to the gate).
8. **`query_chapter_evidence` parity cases** — escaped/non-slug chapter ids, a claim supporting MULTIPLE chapters, non-verified claims, and duplicate/latest + verified-then-superseded records (project_ledger drops only the latest-superseded, deduped latest-per-id — assert the Cozo result matches that, not the raw ledger).
9. **Chapter-id URI contract — DECIDED:** the query mints the chapter URI with `urllib.quote()` exactly as `project_ledger_cozo._chapter_uri` / `project_graph` do (P5.1 fix), so ANY chapter id (not just URL-safe slugs) joins correctly and the EDN literal is injection-safe. The gate asserts an escape-needing id resolves; do NOT reintroduce a raw-id lookup.
10. **`audit_taxonomy` no-bypass allowlist is NARROW** — the scan exempts ONLY `audit_taxonomy.py` (a standalone RDFS-ontology linter), not any claim/thesis-graph reader; every other module must be rdflib/TriG-free.

**Files:**
- Modify: `run_competency_queries.py`, `validate_shacl.py`, `datalog_consistency.py` — flip `KG_BACKEND` default to `cozo`.
- Create: `skills/book-knowledge/tests/test_cutover_gate.py` — `test_blocks_until_all_fixtures_pass` (every characterization golden — 8 queries + SHACL + D9-D11 — reproduced by the Cozo path); `test_no_legacy_import_after_cutover` (whole-suite scan: no `import rdflib|pyshacl|pyDatalog`, no `format="trig"`/`.parse(layout.dataset` in any non-deleted source); mirror the F4 no-bypass scan widened across all three skills).

- [ ] **Step 1 (RED):** the gate test fails while legacy imports remain.
- [ ] **Step 2:** flip defaults; run the whole multi-skill suite on the Cozo path.
- [ ] **Step 3:** Commit `kg(P5.3): default KG_BACKEND=cozo + cutover gate (REQ-KG-010/018)`. **This is the last PR (#4) BEFORE deletion** — merge and let it bake; the legacy stack is still present and revert-able.

## Task P5.4: delete the legacy stack (REQ-KG-018) — PR #5

**Files (delete):** `project_graph.py` RDF emit (or the whole module if nothing else uses it), `assets/shapes.ttl`, `assets/queries/*.rq`, `compile_thesis.py`'s TTL emit, `book-thesis/rules/consistency.dl`, the rdflib-based internals of `validate_shacl`/`datalog_consistency`.
**Files (modify):** the three pyproject.toml — drop `rdflib`/`pyshacl`/`pyDatalog` deps + the `filterwarnings` lines.
**Files (docs):** README.md, AGENTS.md, CLAUDE.md, `docs/operations/*`, the skill SKILL.md files — update to the single-graph model.

- [ ] **Step 1:** delete; rebuild each venv WITHOUT rdflib/pyshacl/pyDatalog (`pip install -e .[dev]`); confirm `test_no_legacy_import_after_cutover` green and nothing imports the deleted modules.
- [ ] **Step 2:** full suite green across book-knowledge / book-compose / book-thesis / book-qa with the legacy deps UNINSTALLED (proves no hidden dependency).
- [ ] **Step 3:** update docs. Commit `kg(P5.4): delete rdflib/pyshacl/pyDatalog + RDF/SHACL/TTL stack; Cozo sole store (REQ-KG-018)`.

---

# PHASE Z — Audit (after each PR + final)

- [ ] Two-stage internal review (spec-compliance then code-quality) per task, per subagent-driven-development.
- [ ] After the cutover PRs, generate an external GPT adversarial audit (XML prompt → `audit.md` → `docs/audits/2026-06-17-homoiconic-kg-cutover-audit.md` with a resolution note), same pattern as P0+P1 and P4. Calibrate any auditor "tighten validation" findings against the REAL bermuda + a real thesis workspace before applying (the P4 lesson: synthetic-only audits can propose fixes that break real data).

---

## Self-review

- **Spec coverage:** C0→REQ-KG-014; P2.1→009/009b/020; P2.2→003/012; P2.3→012/013; P3.1→016; P3.2→015; P5.1→019; P5.2→017; P5.3→010/018; P5.4→015b/018. Every REQ-KG-009..020 maps to a task.
- **The auditor-caught deadlock** (REQ-KG-018 blocks cutover on `query_chapter_evidence`/`audit_taxonomy`) is resolved by P5.1 ordering it BEFORE the gate (P5.3).
- **The 5th status copy** (`VALID_TRANSITIONS`) is covered by P2.1/REQ-KG-020.
- **Rollback:** the legacy stack survives until P5.4; P5.3 (gate + default flip) is a separate, bakeable PR, so deletion is a clean revert if a consumer breaks.
- **Risk — recursive Datalog (D10):** flagged in P3.2 to pin the recursive Cozo form against a live store (same caveat as P4.2 PageRank).
- **Risk — focus-node representation** in the SHACL port (URI vs id) is called out in P2.3 as a conscious, documented decision, not a silent mismatch.
