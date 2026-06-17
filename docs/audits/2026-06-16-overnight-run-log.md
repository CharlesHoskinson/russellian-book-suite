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
| Z | Phase Z adversarial audit | DONE | 06d2d54 | internal audit: 1 CRIT + 3 IMP + 5 MIN; verdict "sound to build P3 on" |
| Z | Audit remediation C-1/I-1/I-3 | DONE | 53572e6 | confidence lower bound ported (engines agree); raw-pyshacl golden + normalizer test; chapter constraint marked unwired; 309 passed |
| Z | External GPT-5.5 audit prompt | DONE | (this commit) | docs/audits/2026-06-17-...-external-audit-prompt.md |
| P3 | P3.1 thesis→cozo projector | DEFERRED | — | BLOCKED — cross-skill import architecture decision (see Handoff) |
| P3 | P3.2 D9-D11 EDN→Cozo + parity | DEFERRED | — | depends on P3.1 |
| P5 | P5.1 port remaining RDF readers | DEFERRED | — | depends on P3 |
| P5 | P5.2 reconcile 3 divergences | DEFERRED | — | query-port divergences (P1 scope) |
| P5 | P5.3 default flip + cutover gate | DEFERRED | — | needs full cozo suite green + RDF-fixture rework |
| P5 | P5.4 deletion | DEFERRED | — | last step; human review |

---

## RUN SUMMARY & HANDOFF (run ended here — clean stop before P3)

**Completed & reviewed (all on branch `feat/homoiconic-kg-cutover`, local only — NOT pushed/merged):**
- **PR #1 / Phase C0** — three equivalence-oracle goldens frozen (SHACL bermuda+violating, D9–D11 bermuda+violating), each non-vacuous, each through implementer + spec-review + code-quality-review + fix loop.
- **PR #2 / Phase P2** — status single-source (P2.1), pure `defconstraint`→Cozo compiler + 5→6→7 constraint EDN (P2.2), Cozo-backed `validate_shacl` behind `KG_BACKEND` with non-tautological parity (P2.3). Default backend stays `rdflib`.
- **Phase Z** — internal adversarial audit + remediation of its CRITICAL (C-1) and key IMPORTANTs + an external GPT-5.5 audit prompt.
- **Gates:** book-knowledge **309 passed**, book-thesis **43 passed** on the default backend; cozo smoke clean for touched files.

**Why the run stopped before P3 (a real decision, not a failure):** P3 (retire pyDatalog) requires **book-thesis to import book-knowledge's Cozo modules**, which hits a cross-cutting architecture choice the run should not make unilaterally:
- `sibling_skills` resolves book-knowledge to `~/.claude/skills/book-knowledge` — a **distinct, stale** copy (no P2 changes; its venv has no pycozo), NOT the repo copy.
- Both skills define a top-level `scripts` package (name collision); book-knowledge has at least one absolute `from scripts.cozo_store import …` that breaks aliased cross-skill loading.
- book-thesis's venv lacks `pycozo` + `edn_format`.

**Decision needed (pick one), then P3 can proceed:**
1. **Sync `~/.claude/skills/book-knowledge` ← repo** and load via `sibling_skills` (matches book-compose's model; but the repo is no longer self-contained — depends on installed-copy state).
2. **Add a repo-relative aliased loader** (point the `_book_knowledge_scripts` alias at `skills/book-knowledge/scripts`) — repo self-contained; diverges from the installed-skill model; must also fix the absolute `from scripts.…` import.
3. **Refactor the shared Cozo code** (cozo_store, compile_constraint, project_ledger, kg-schema) into a common importable location both skills depend on — cleanest long-term; largest blast radius.
Whichever is chosen: add `pycozo[embedded]` + `edn_format` to book-thesis's pyproject + venv. The external audit prompt asks GPT-5.5 to weigh in on this too.

**Open audit findings deliberately deferred (documented, none affect real bermuda data):**
- **I-2 residual** — the path-keyed message remap can mislabel/collapse multiple pyshacl violations sharing one path, and the Cozo path *crashes* on a wrong-datatype confidence (typed-column load). Synthetic-only (JSON schema forbids on real data). Fix when convenient: key on `(path, sh:sourceConstraintComponent)` or drop message from the parity contract.
- **M-1** — `status-enum` + `text-cardinality` constraints are correct but unexercised by the violating golden (both engines verified to agree). Add a frobnicated-status + text-less row to the fixtures to exercise all 7.
- **M-2** — `test_callers_import_unchanged` is hollow (doesn't import the 3 book-compose callers; the contract does hold in practice).
- **M-3** — `_validate_cozo` derives `conforms = not violations`; `_validate_rdflib` uses pyshacl's own flag. They line up for all shipped cases; consider unifying.
- **M-4** — `capture_consistency` docstring claims side-effect-free, but `run()` writes `qa/datalog-defects.json`; regeneration needs `compile_thesis` first.
- **M-5** — compiler emits a redundant `!is_null(var)` per filter clause (cosmetic; in golden bytes).
- **REQ-KG-012/013 are PARTIAL** until a real `chapter-section` projector exists (chapter-cites-verified has no production data path).

**A pre-existing property worth a product decision:** the JSON-schema record contract is strictly stronger than the SHACL/EDN constraints, so `validate_shacl` conforms on ALL real (ledger-sourced) workspaces — the constraint gate only ever fires on synthetic fixtures. The migration faithfully preserves this; but the team may want to decide whether the SHACL gate earns its keep post-cutover or should be retired rather than ported.

**To resume:** `git switch feat/homoiconic-kg-cutover`; venvs are built at `skills/book-knowledge/.venv` and `skills/book-thesis/.venv` (Python 3.14). Nothing pushed; review/squash/split into PRs as desired.

(Updated as the run proceeds.)

---

## External audit resolution (2026-06-17, GPT-5.5 Deep Research Pro, static run over the bundle)

Four findings; triaged against the live branch:

- **[NEW — actionable] Cozo skips `minCount`/`datatype` for `status` + `confidence`.** Confirmed: only value-violation constraints (status `sh:in`, confidence range) and the two minCount negations (`text-cardinality`, `source-span-present`) are ported. `status` minCount, `confidence` minCount, and the `xsd:string`/`xsd:decimal` datatype checks are NOT — so under `KG_BACKEND=cozo` a presence/type-defective claim conforms while pyshacl flags it. Real ledger data shielded by `claim-record.schema.json`; projector/manual-ledger regressions escape, and the gate weakens at the P5.3 default flip. **Folded into new plan Task P2.4 (hard prereq for P5.3).**
- **[= internal I-2] Path-keyed message remap collapses distinct components.** Confirmed and latent today; becomes ACTIVE once P2.4 adds a second message on the `confidence` path. **Fix scheduled inside P2.4** (re-key on `constraint_id`/component, or drop message from the parity contract).
- **[= internal I-3] `chapter-cites-verified` synthetic-only.** Already marked unwired; REQ-KG-012/013 PARTIAL. No change.
- **[= internal M-2] `test_callers_import_unchanged` hollow.** Already tracked, MINOR. No change.

**Verdict:** agrees C-1 is fixed; agrees the SHACL real-data no-op is acceptable for migration parity but adds the caveat that it must not be sold as a runtime gate unless Cozo also catches projection omissions — which is exactly what P2.4 closes. C0+P2 is a sound base for P3; **not** a P5 cutover base until P2.4 lands.

**Cross-skill import:** auditor recommends **(c) refactor shared Cozo code into a common importable location** (matches the handoff lean); (b) acceptable bridge; avoid (a). **Folded into plan as Task P3.0**, ahead of P3.1.

| P2 | P2.4 status/confidence minCount + (path,component) remap | DONE | c3675da | TDD; status-present + confidence-present EDN; rdflib remap re-keyed on (path, sourceConstraintComponent) closing audit I-2; datatype subsumed by Cozo Float? typing; +4 presence tests, +2 compile goldens. **book-knowledge 317 passed (default); 45 passed (KG_BACKEND=cozo SHACL subset).** Two-stage review (correctness + quality) clean. P5.3 prerequisite satisfied. |

**Now resumable at P3.0** (cross-skill Cozo refactor, option c) → P3.1. book-knowledge venv was brought current this run (`pip install -e .[dev]` added edn_format + pycozo[embedded]); book-thesis venv still lacks them (P3.0 input).

| P3 | P3.0 cross-skill Cozo import bridge | DONE | b047cb2 | **Chose option (b), not (c)** (user-confirmed): repo already has the aliased loader + a repo-relative fallback pattern; a new shared package would fight the self-contained-skill model. New `book-thesis/scripts/sibling_skills.py` resolves book-knowledge **repo-sibling-first** (never the stale ~/.claude copy), loads `cozo_store` + `booklogic_kg` under the `_book_knowledge_scripts` alias. Fixed `booklogic_kg.py` abs import → relative so it loads under the alias. book-thesis venv: +edn_format +pycozo[embedded]. Scoped to cozo_store+booklogic_kg (NOT project_ledger_cozo — avoids the jsonschema/pdfplumber ledger stack). +4 tests. **book-thesis 47 passed; book-knowledge 317 passed.** Correctness review clean (verdict: sound foundation for P3.1). |

| P3 | P3.1 thesis→cozo projector | DONE | 2c02e38 | `book-thesis/scripts/project_thesis_cozo.py`: `project_thesis(workspace, store, book_id=None)` loads root thesis-node (id "thesis") + sub-arguments (parent normalized) + invariants (subject + pinned/forbidden parsed via reused `compile_thesis._parse_invariant_formal`) into the shared store via the P3.0 bridge. New `:invariant` entity in kg-schema.edn (test_kg_schema updated). YAML read-only; deterministic. Scoped out: required_evidence/advanced_by_chapters (RDF path still feeds D9-D11). +6 tests. **book-thesis 53 passed; book-knowledge 317 passed.** Correctness review clean. |

| P3 | P3.2 D9–D11 EDN→Cozo consistency + parity | DONE | 6a315dd | **Decisions (user-confirmed): CozoScript program (not an EDN defrules compiler) + extend shared kg-schema.** `rules/consistency.cozo` is a recursive multi-rule port of consistency.dl (reaches transitive closure; transitive_contradiction recursion; stratified negation). `consistency_cozo.run_consistency_cozo` projects the spine (P3.1) + a faithful `_assert_claim_facts` mirror, runs each head, and assembles the report by REUSING datalog_consistency's DefectReport/_emit_pairs/_value_str/detail-strings. 5 new fact tables in kg-schema (claim-fact, claim-implies, paragraph-supports, sub-arg-chapter, sub-arg-evidence). Parity proven vs both C0.3 goldens AND vs the live pyDatalog pass; +end-to-end missing_evidence test; +rule-level coverage for the 3 rules no golden fires. **book-thesis 60 passed; book-knowledge 317 passed.** Correctness review clean. |

**PHASE P3 COMPLETE** — pyDatalog is fully PORTED (cross-skill bridge P3.0, thesis projector P3.1, consistency pass P3.2), running in parallel behind parity. It is NOT yet deleted; that is P5.4 after the cutover gate.

**Now resumable at P5** (cutover): P5.1 port the remaining RDF readers (`query_chapter_evidence`, `audit_taxonomy`); P5.2 reconcile the 3 documented RDF↔Cozo query divergences; **P5.3 flip `KG_BACKEND` default to cozo + cutover gate — gated on P2.4 (done) AND a full cozo-green suite** (the handoff's known blocker: other consumers like `run_competency_queries` not yet cozo-green; RDF-injection fixtures rdflib-pinned); P5.4 delete rdflib/pyshacl/pyDatalog. P5 also retires the parallel pyDatalog consistency pass + `compile_thesis`'s TTL emit once the Cozo pass is the default.
