# Architecture & maintainability — findings

22 confirmed findings. Each survived an independent adversarial-verify pass; the evidence line cites code that was opened and read.

## `sentinel-weaker-than-stage1` — HIGH

**Location:** `skills/book-qa/scripts/sentinel.py:193` · **area:** book-qa/gate consistency · **confidence:** high

**Finding.** lint_artifact.main exits 1 on ANY critical defect (including D9-D13), but the aggregating sentinel that is the documented final gate exits 1 only on D1-D8/C-critical hard-fails, so running the full Stage-1-3 pipeline is strictly weaker than running Stage-1 alone and contradicts CLAUDE.md's 'severity=critical defeasible fires hard-fail the QA gate' invariant.

**Fix.** Make the sentinel's hard-fail policy a superset of lint_artifact's critical gate (every critical defect blocks), so the aggregate gate can never pass a build that Stage 1 alone would fail.

**Evidence.** The claim is accurate and the inconsistency is real and material. lint_artifact.main (lint_artifact.py:616-617) sets n_critical = summary["by_severity"][CRITICAL] and returns 1 if any critical defect exists, regardless of class. lint_artifact emits D9-D13 defects with CRITICAL severity by default (lint_d9_d12 at lines 357-439 emits D9/D10/D11 with severity critical; lint_d13_verification_unsat at 456-485 emits D13 critical), and SKILL.md:75-77 documents D9/D10/D11 as critical and D13 likewise. So Stage-1 alone exits 1 on a critical D9-D13 defect. The sentinel, however, classifies hard-fail via _is_hard_fail (sentinel.py:62-70): a D-class is hard-fail only if it is in HARD_FAIL_D_CLASSES = {D1..D8} (line 30) AND critical; C2/C13 and any C* critical also hard-fail; everything else is soft. D9-D13 are neither in HARD_FAIL_D_CLASSES nor start with "C", so a critical D9-D13 defect returns False from _is_hard_fail and is bucketed as soft-gate. The sentinel loads Stage-1 defects.json indiscriminately (_load_stage1 lines 73-94) and main exits 1 only if hard_fail_count > 0 (sentinel.py:193). Therefore a build with a critical D11 (failed-entailment) or D10 (transitive-contradiction) or D13 (verification-unsat) defect and no D1-D8/C-critical issues passes the aggregate sentinel gate (exit 0) but fails Stage-1 alone (exit 1) — the documented final gate (SKILL.md:48-52 stage 3) is strictly weaker. This directly contradicts CLAUDE.md's invariant "severity=critical defeasible fires hard-fail the QA gate," since D10/D11 are precisely the defeasible-reasoning defect classes. Not stylistic: it is a gate-soundness hole.

**Citations.** skills/book-qa/scripts/sentinel.py:30 (HARD_FAIL_D_CLASSES = D1..D8 only); :62-70 (_is_hard_fail excludes D9-D13); :138 (soft/hard split); :193 (exit 1 only on hard_fail_count). skills/book-qa/scripts/lint_artifact.py:357-439 (D9/D10/D11 emitted CRITICAL), :456-485 (D13 CRITICAL), :616-617 (exit 1 on any critical). skills/book-qa/SKILL.md:75-77 (D9/D10/D11 documented critical), :48-52 (sentinel is the Stage-3 aggregate gate). CLAUDE.md "severity=critical defeasible fires hard-fail the QA gate".


---

## `datalog-detectors-mismatch-real-ledger` — HIGH

**Location:** `skills/book-thesis/scripts/datalog_consistency.py:108` · **area:** datalog-consistency · **confidence:** high

**Finding.** The contradiction detectors depend on claim fields (subject/semantic_class, value, implies, conflicts_with, supports_nodes) that the real book-knowledge ledger never carries — the bermuda ledger records only have canonical_text/claim_id/claim_type/confidence/created_at/status/supports_chapters — so direct_contradiction, transitive_contradiction (the headline cross-chapter feature) and declared_conflict can never fire on a real manuscript.

**Fix.** Align the asserted-fact extraction with the actual ledger schema (or extend book-knowledge's claim schema to emit subject/value/implies), and add a fixture/test that drives transitive_contradiction via real `implies` data instead of only synthetic test records that inject the otherwise-absent fields.

**Evidence.** The contradiction detectors depend on claim fields that the real ledger does not carry, and two of them — the headline ones — can never fire. In datalog_consistency.py:108-124, _assert_claim_facts derives claim_value only from a "value" key (line 119-120), implies only from an "implies" key (line 123), and supports edges from "supports_nodes" (line 124). The canonical claim schema (skills/book-knowledge/assets/claim-record.schema.json:5-44) sets "additionalProperties": false and its property list contains NO "value", "implies", or "supports_nodes" keys, so a schema-valid ledger record can never carry them. The real bermuda ledger (examples/bermuda-manual/claims/ledger.jsonl, all 51 records) carries only claim_id/canonical_text/claim_type/confidence/created_at/status/supports_chapters (+ optional p_prior/p_posterior/load_bearing/counter_claim_ids/generated_by_run/review_notes/source_spans) — none of subject, value, implies, supports_nodes, conflicts_with, or semantic_class. Per the rules (rules/consistency.dl:28,42,49-51): direct_contradiction requires states/3 = claim_subject & claim_value, and claim_value is never asserted, so direct_contradiction can never fire; transitive_contradiction (rules 49-51) requires implies (never asserted) or reduces to direct_contradiction (which never fires), so it too can never fire. The test suite confirms the gap: the fixtures in test_datalog_consistency.py:56-96 inject subject/value/supports_nodes — fields that would themselves FAIL schema validation under additionalProperties:false — and grep shows transitive_contradiction/implies appear in NO test file at all (only in the script, rules, and one thesis YAML where "implies" is mere prose, thesis/bermuda.yaml:109). One nuance trims the claim's edge: declared_conflict reads conflicts_with (line 122), which IS a valid schema field (schema line 37, used in project_graph.py:88), so declared_conflict is not categorically impossible on a real ledger — only unused in the bermuda example. But the central, material assertion holds: the two headline cross-chapter detectors are dead code against any real manuscript, exercised only by synthetic, schema-invalid test records.

**Citations.** skills/book-thesis/scripts/datalog_consistency.py:108-124; skills/book-thesis/rules/consistency.dl:28,42,45-51; skills/book-knowledge/assets/claim-record.schema.json:5-44; examples/bermuda-manual/claims/ledger.jsonl:1-51; skills/book-thesis/tests/test_datalog_consistency.py:56-96; skills/book-thesis/tests/fixtures/ledger-entailment.jsonl:1-2; skills/book-knowledge/scripts/project_graph.py:88


---

## `state-machine-doc-drift` — MEDIUM

**Location:** `skills/book-knowledge/references/claims-and-provenance.md:7` · **area:** claim state machine / docs · **confidence:** high

**Finding.** The reference doc (and SKILL.md line 39) describe a four-state machine omitting 'refuted' and a transition table without disputed->refuted, contradicting claim_validator.VALID_TRANSITIONS, the schema enum, the SHACL sh:in list, and CLAUDE.md which all define five states with refuted as terminal.

**Fix.** Update claims-and-provenance.md and SKILL.md to document all five states (proposed, verified, disputed, superseded, refuted) and the disputed->refuted transition to match the code.

**Evidence.** The cited reference doc documents only four claim states and a transition table that both omit `refuted` and the `disputed → refuted` transition, while four other authoritative sources define five states with `refuted` as terminal. claim_validator.VALID_TRANSITIONS (claim_validator.py:12-17) lists proposed/verified/disputed/superseded/refuted, includes `disputed → refuted`, and makes both `superseded` and `refuted` terminal (empty sets). The schema enum (claim-record.schema.json:10) and the SHACL sh:in list (shapes.ttl:19) both enumerate all five states. CLAUDE.md explicitly says "Five states: proposed, verified, disputed, superseded, refuted. superseded and refuted are terminal." The doc's enum on line 33 also omits `refuted`. SKILL.md line 39 likewise describes only "proposed → verified → disputed → superseded". This is a genuine, material doc-vs-code drift, not a stylistic nitpick: an operator following the reference doc would wrongly believe `refuted` is not a valid status and that the enforced `disputed → refuted` transition is illegal. The claim is true and the suggested fix is correct.

**Citations.** skills/book-knowledge/references/claims-and-provenance.md:5-23 (four states, transition table omitting refuted) and :33 (status enum omits refuted); skills/book-knowledge/scripts/claim_validator.py:12-17 (VALID_TRANSITIONS, five states, disputed→refuted, refuted terminal); skills/book-knowledge/assets/claim-record.schema.json:10 (enum with refuted); skills/book-knowledge/assets/shapes.ttl:19 (sh:in includes refuted); skills/book-knowledge/SKILL.md:39 (state machine omits refuted); CLAUDE.md "Five states ... refuted ... terminal".


---

## `generate-counter-claims-no-cli` — MEDIUM

**Location:** `skills/book-knowledge/scripts/generate_counter_claims.py:0` · **area:** counter-claim generation / CLI · **confidence:** high

**Finding.** SKILL.md line 101 documents 'python -m scripts.generate_counter_claims <workspace>' as a runnable command, but the module has no main()/__main__/argparse entrypoint, so the documented invocation runs nothing.

**Fix.** Add a __main__ CLI entrypoint (or remove the line from SKILL.md); note the function also requires an llm_call callable that no CLI currently supplies.

**Evidence.** SKILL.md line 101 documents `.venv\Scripts\python.exe -m scripts.generate_counter_claims <workspace>` as a runnable command, listed alongside sibling commands like propagate_belief and verify_claim. But generate_counter_claims.py (read in full, lines 1-92) contains only four function definitions (prompt_for_claim, _latest_claim_record, generate_for_claim, generate_for_all_load_bearing) and module-level constants — no `if __name__ == \"__main__\"`, no argparse, no main(), no sys.argv handling. A grep for those tokens returns nothing for this file, whereas the same grep confirms propagate_belief.py and verify_claim.py (documented identically) DO have entrypoints. So `python -m scripts.generate_counter_claims <workspace>` imports the module and runs nothing — silently doing no work. The issue is real and material: the documented operator command is non-functional, and CLAUDE.md explicitly warns that broken commands in SKILL.md mislead operators. The finding's secondary note also holds: both runnable functions require an llm_call callable (lines 43, 79) that no CLI supplies, so even adding a bare __main__ would need to wire that up.

**Citations.** C:/Users/charl/russellian-book-suite/skills/book-knowledge/scripts/generate_counter_claims.py:1-92 (no __main__/argparse/main; functions at 29, 33, 42-43, 78-79); C:/Users/charl/russellian-book-suite/skills/book-knowledge/SKILL.md:101 (documented command); grep confirms propagate_belief.py and verify_claim.py have entrypoints while generate_counter_claims.py does not.


---

## `d11-claim-binding-rarely-fires-writeback` — MEDIUM · needs runtime verification

**Location:** `skills/book-qa/scripts/lint_artifact.py:437` · **area:** book-qa/propose_writeback · **confidence:** medium

**Finding.** D11 failed-entailment defects set where=paragraph_id and detail referencing a supports-node, so _extract_claim_id (which only recovers a clm-YYYY-NNNNNN token) typically yields claim_id=None; consequently the D11->unsupported_claim writeback path in propose_writeback almost never has a claim_id to act on, making the documented D11 ledger-transition proposal largely inert in practice.

**Fix.** Carry the offending claim_id explicitly on the D11 Defect (e.g. from entry.get('claim_id') or the supports-node's bound claim) rather than relying on regex recovery from free text, so propose_writeback can bind it.

**Evidence.** The claim is accurate and the gap is real. D11 defects are emitted at lint_artifact.py:437 with where = entry.get("where") or entry.get("paragraph_id") or "paragraph" (line 427) and a detail string that embeds the supports-node id, not a claim id (lines 428-432). The only mechanism that binds a claim_id onto a defect is _enrich_defects (lines 537-543), which calls _extract_claim_id (lines 520-524); that helper searches only where+detail for CLM_BARE_RE = clm-\d{4}-\d{6} (line 64) and has no entry.get("claim_id") fallback for D11. The canonical producer-side field shapes confirm that paragraph_id values are slugs like "ch-05-p12" and supports-node ids are human slugs like "history-shapes-government"/"atomic-decomposition" (test_lint_artifact.py:266-272, test_bundle_c_writeback.py:83-84, synthesize_exemplars.py:133), none of which match the clm token pattern. Consequently D11 defects almost never receive a claim_id. Downstream, propose_writeback._defect_to_ticket drops any defect lacking claim_id (propose_writeback.py:79-81), and transition_rules additionally gates on claim_current_status=="verified" (transition_rules.py:14-19). So the documented D11 -> unsupported_claim ledger transition is effectively inert: with no claim_id, the ticket is filtered out before dispatch. No production entailment-results.json exists in the repo, but the field shapes are pinned by the canonical D11 test fixture (test_lint_artifact.py:261-290, which sets only paragraph_id/supports/verdict and never a claim_id), so the conclusion is determinable statically rather than truly runtime-dependent. The suggested fix (carry claim_id explicitly on the D11 Defect, or add an entry.get("claim_id") passthrough in _enrich_defects) is the correct remediation. Severity medium is fair: the path is documented and tested in isolation (transition_rules tests pass a hand-built claim_id) but the real emitter never supplies one, so the feature silently no-ops in practice.

**Citations.** skills/book-qa/scripts/lint_artifact.py:64 (CLM_BARE_RE), :427-437 (D11 emit: where=paragraph_id, detail=supports-node), :520-524 (_extract_claim_id regex-only), :537-543 (_enrich_defects binds claim_id only via regex, no claim_id fallback), :566-569 (lint_d9_d12 + _enrich_defects in pipeline); skills/book-qa/scripts/propose_writeback.py:79-81 (defects without claim_id dropped); skills/book-qa/scripts/transition_rules.py:12-19 (D11->unsupported_claim, requires status verified); skills/book-qa/tests/test_lint_artifact.py:261-290 (canonical D11 fixture: paragraph_id/supports/verdict only, no claim_id); skills/book-qa/tests/test_lint_artifact.py:266-272 and tests/test_bundle_c_writeback.py:83-84 (supports-node ids are non-clm slugs)


---

## `schema-never-validated` — MEDIUM

**Location:** `skills/book-review/scripts/dispatch_review.py:81` · **area:** schema discipline · **confidence:** high

**Finding.** assets/review-report.schema.json and the jsonschema dependency exist, but parse_review_report never validates frontmatter against the schema, so the chapter_id pattern, verdict enum, and required count fields are unenforced.

**Fix.** Load the schema and jsonschema.validate(meta) in parse_review_report (or a dedicated validator) so malformed reports are rejected rather than silently coerced.

**Evidence.** The schema asset (review-report.schema.json) defines a chapter_id pattern (^ch-[0-9]{2,3}$), a verdict enum (APPROVED/APPROVED_WITH_NOTES/NEEDS_WORK/REJECT), and required integer count fields plus reviewed_at; the jsonschema>=4.21 dependency is declared twice in pyproject.toml. Yet parse_review_report (dispatch_review.py:81-108) parses frontmatter with yaml.safe_load and reads fields via meta.get(...) with silent fallback defaults (e.g. verdict defaults to "APPROVED", chapter_id to ""), never invoking jsonschema.validate. A repo-wide grep found no import jsonschema, no from jsonschema, and no reference to the schema file or any validate call in book-review/scripts; the only jsonschema mentions are the unused pyproject dependency lines. The two callers (aggregate_reviews.py:29, tests) likewise route through this unvalidated parser. So malformed reports (bad chapter_id, invalid verdict, missing/negative counts) are silently coerced rather than rejected. This is material, not stylistic: it violates the repo's own stated discipline (CLAUDE.md: schema changes must touch both the JSON Schema and a validator), and the required count fields aren't even consulted by the parser. The claim is statically verifiable and accurate.

**Citations.** skills/book-review/scripts/dispatch_review.py:81-108 (parse_review_report uses meta.get with defaults, no validation); skills/book-review/assets/review-report.schema.json:5-16 (required fields, chapter_id pattern, verdict enum); skills/book-review/pyproject.toml:12,20 (jsonschema dependency declared); grep for jsonschema/validate/schema across skills/book-review/scripts found no matches (only pyproject deps)


---

## `real-manuscript-no-carriers` — MEDIUM · needs runtime verification

**Location:** `examples/bermuda-manual/book/releases/6.0.0/manuscript.md:0` · **area:** pipeline integration · **confidence:** high

**Finding.** The shipped 6.0.0 manuscript contains zero `::: paragraph` fenced divs and zero `supports:` comments, so running lint_supports against it would flag essentially every prose paragraph as a D9 no-support orphan — book-compose does not emit the back-pointers book-thesis requires, leaving the two skills unintegrated in practice.

**Fix.** Wire book-compose to emit per-paragraph supports carriers (or gate book-thesis lint_supports to only run on manuscripts that declare carriers) so the D9 gate reflects real intent rather than always failing.

**Evidence.** The shipped 6.0.0 manuscript contains zero `::: paragraph` fenced divs and zero `supports:` comments (grep count = 0 for both carrier syntaxes that lint_supports.py recognizes). lint_supports.py classifies any paragraph with `supports is None` as a critical D9 no-support orphan and exits 1 if any orphan exists. book-compose emits no carriers anywhere (grep for `supports=|::: paragraph|supports:` across skills/book-compose returns no files), while book-thesis/SKILL.md explicitly states the contract that "every paragraph in a draft carries a `supports:` field." The decisive evidence is the committed runtime artifact: examples/bermuda-manual/qa/supports-defects.json reports total_paragraphs 333, supported 0, orphan_no_support 333, and all 6 thesis sub-arguments unadvanced; examples/bermuda-manual/qa/defects.json summarizes 333 critical D9 defects. The suite-wide audit confirms D9 is critical and release-gating. So running lint_supports against the real manuscript does flag essentially every prose paragraph as a D9 orphan, and book-compose does not produce the back-pointers book-thesis requires — the two skills are unintegrated in practice. The issue is real and material (release-blocking critical gate), not stylistic. Minor caveat: the linter's expected TTL path (.knowledge/thesis-triples.ttl) is absent and the graph instead lives at graph/dataset.trig, but the populated supports-defects.json proves the lint already ran and produced exactly the predicted 333-orphan result, so the wiring gap is demonstrated, not hypothetical.

**Citations.** examples/bermuda-manual/book/releases/6.0.0/manuscript.md (0 `::: paragraph`, 0 `supports:` via Grep); skills/book-thesis/scripts/lint_supports.py:91-97,119-157,169-171,242-245 (carrier regexes, no-support D9, exit 1); skills/book-thesis/SKILL.md:28 (per-paragraph supports contract); examples/bermuda-manual/qa/supports-defects.json:2-16 (total_paragraphs 333, supported 0, orphan_no_support 333, 6 unadvanced); examples/bermuda-manual/qa/defects.json:1-15 (333 critical D9); docs/audits/2026-05-21-suite-wide-linter-review.md:80 (D9 critical, release-gate); skills/book-compose (Grep for supports carrier emission: no files)


---

## `d12-two-definitions` — MEDIUM

**Location:** `skills/book-thesis/scripts/lint_supports.py:187` · **area:** defect-model · **confidence:** high

**Finding.** D12 'unadvanced-sub-argument' has two incompatible definitions: lint_supports flags a sub-arg if no paragraph's `supports:` names it, while datalog_consistency flags it only if no chapter `advances` it — the same defect class can fire in one tool and pass in the other for the same book.

**Fix.** Pick one canonical D12 semantics (chapter-advances vs paragraph-supports) and have both scripts compute it the same way, or split into two distinct defect codes with distinct names in SKILL.md/book-qa.

**Evidence.** The two tools emit the same defect code D12 ("unadvanced sub-argument") from incompatible computations over different data sources. lint_supports.py builds `cited` only from paragraph `supports:` markers in the manuscript markdown that transitively reach :Thesis (lines 169-191), then flags every non-Thesis node not in `cited` as D12 "unadvanced" with detail "named by no paragraph's supports". datalog_consistency.py instead derives D12 from graph-level `advancedBy` triples in the TTL: it asserts `advances(Ch, N)` from `advancedBy` triples (lines 102-103), and consistency.dl rules `advanced(N) <= advances(Ch, N)` / `unadvanced_sub_arg(N) <= sub_arg(N) & ~advanced(N)` (lines 54-55) flag a sub-arg as D12 only when no chapter advances it, with detail "has no chapter advancing it". Because paragraph `supports:` markers and `advancedBy` chapter triples are distinct, independently authored signals, the same sub-argument can be chapter-advanced (passes datalog D12) yet named by no paragraph's supports (fails lint_supports D12), or vice versa. Both surface under the identical class string "D12" with near-identical names, so any consumer treating D12 as a single defect class gets contradictory verdicts for the same book. This is a real, material architecture/semantics divergence, not a stylistic nitpick.

**Citations.** skills/book-thesis/scripts/lint_supports.py:184 (cited.add(p.supports) gated on paragraph supports reaching Thesis), :187-191 (sub_args - cited -> D12 "unadvanced", detail "named by no paragraph's supports"); skills/book-thesis/scripts/datalog_consistency.py:102-103 (advances asserted from advancedBy triples), :191-193 (D12 unadvanced_sub_arg, detail "has no chapter advancing it"); skills/book-thesis/rules/consistency.dl:53-55 (advanced(N) <= advances(Ch,N); unadvanced_sub_arg(N) <= sub_arg(N) & ~advanced(N))


---

## `booklogic-lift-merge-divergence` — MEDIUM

**Location:** `verifiers/adsc-clinical/cljs-orchestrator/src/main/adsc_clinical/booklogic.cljs:491` · **area:** booklogic predicates.edn codegen divergence · **confidence:** high

**Finding.** adsc-clinical's emit-predicates-edn-string uses (into {} (map lift-to-predicate-entry ...)), which silently drops all-but-last pattern when two lifts target the same predicate, whereas bermuda's copy reduces and concatenates :patterns — divergent behavior for multi-lift predicates.

**Fix.** Port bermuda's merging reduce into adsc-clinical so multiple lifts for one predicate accumulate their :patterns instead of overwriting; keep the two copies in sync.

**Evidence.** The claim is accurate and the divergence is real and material. In adsc-clinical, emit-predicates-edn-string builds entries via (into {} (map lift-to-predicate-entry lift-rules)) (booklogic.cljs:493). lift-to-predicate-entry returns a [pred {:patterns [pattern] ...}] pair per lift (lines 481-488). When two lifts target the same predicate, (into {} ...) over a seq of pairs with duplicate keys keeps only the last pair, so the earlier lift's :patterns is silently dropped. Bermuda's copy uses the identical lift-to-predicate-entry but a different emit-predicates-edn-string: a reduce that, on (contains? acc pred), does (update-in acc [pred :patterns] conj (:pattern lift)) to concatenate patterns, with a docstring explicitly stating multiple lifts are merged (bermuda booklogic.cljs:477-497). This is a determinate static fact about Clojure(Script) into/map semantics, not a stylistic nitpick: the two generators emit different predicates.edn for any input with multiple lifts on one predicate. Severity medium is fair — it only matters when such multi-lift inputs exist, but when they do, adsc-clinical loses lift patterns. The suggested fix (port bermuda's merging reduce) is correct.

**Citations.** C:/Users/charl/russellian-book-suite/verifiers/adsc-clinical/cljs-orchestrator/src/main/adsc_clinical/booklogic.cljs:481-494 (lift-to-predicate-entry returns single-pattern pair; line 493 uses (into {} (map lift-to-predicate-entry lift-rules))). C:/Users/charl/russellian-book-suite/verifiers/bermuda/cljs-orchestrator/src/main/bermuda/booklogic.cljs:468-497 (same helper at 468-475; emit-predicates-edn-string at 477-497 uses a reduce with (update-in acc [pred :patterns] conj ...) to merge patterns, docstring lines 478-480 documenting the merge).


---

## `phases-precond-vector-of-map` — MEDIUM

**Location:** `verifiers/adsc-clinical/cljs-orchestrator/src/main/adsc_clinical/phases.cljs:12` · **area:** phases contract divergence · **confidence:** high

**Finding.** adsc-clinical translate's :pre validates [:vector ir/Claim] (legacy claims only) while bermuda validates [:vector ir/ClaimOrEvent]; feeding the adsc-clinical orchestrator a book-knowledge event-trace (the documented new input shape) fails the precondition even though its nl_to_fol can't handle events anyway — the two orchestrators have diverged on supported input.

**Fix.** Decide whether adsc-clinical accepts event traces; if so port the ClaimOrEvent schema and event dispatch from bermuda, otherwise document the divergence explicitly.

**Evidence.** The claim is accurate on every statically-checkable point. adsc-clinical's phases.cljs:12 has `:pre (m/validate [:vector ir/Claim] claims)`, accepting only legacy Claim maps, while bermuda's phases.cljs:12 has `:pre (m/validate [:vector ir/ClaimOrEvent] items)`. adsc-clinical's ir.cljs defines only `Claim` (lines 21-30) and has no `EventHead`/`Event`/`ClaimOrEvent` schemas, whereas bermuda's ir.cljs defines all three (lines 32-46), with `ClaimOrEvent = [:or Claim Event]` and `Event = [:tuple EventHead :map]`. Correspondingly, bermuda's nl_to_fol.cljs dispatches on input shape (claim->formula handles both vectors-as-events via event->formula and maps-as-claims), while adsc-clinical's nl_to_fol.cljs only has a meander rewrite for the Claim map shape and would send any 2-tuple event to the `?other → :OPAQUE` fallback — so it indeed cannot translate events even if the precondition allowed them. A book-knowledge event trace element is a `[head payload]` tuple, which is not a valid Claim map, so it fails adsc-clinical's `:pre`. The event-trace input shape is real and documented (bermuda has ingest-trace/trace_to_ledger/run_verification plumbing and EventHead's docstring explicitly cites the book-knowledge exporter; the tier1 spec references an `ingest-trace` EARS spec vendored into each scaffolded project). The two orchestrators, both scaffolded from neurosym-forge's common template, have genuinely diverged: bermuda got the backwards-compatible event upgrade and adsc-clinical did not, and the divergence is silent (no comment/doc in adsc-clinical noting it only accepts legacy claims). This is a material architecture/contract divergence, not a stylistic nitpick. The only minor caveat is that "fails the precondition even though its nl_to_fol can't handle events anyway" is correct but slightly understates that the precondition is arguably doing the right thing for this verifier's capabilities; nonetheless the documented-divergence and missing-explicit-documentation concern stands. Severity medium is reasonable.

**Citations.** verifiers/adsc-clinical/cljs-orchestrator/src/main/adsc_clinical/phases.cljs:11-14 ([:vector ir/Claim] pre); verifiers/bermuda/cljs-orchestrator/src/main/bermuda/phases.cljs:11-14 ([:vector ir/ClaimOrEvent] pre); verifiers/adsc-clinical/cljs-orchestrator/src/main/adsc_clinical/ir.cljs:21-30 (only Claim, no Event/ClaimOrEvent); verifiers/bermuda/cljs-orchestrator/src/main/bermuda/ir.cljs:32-46 (EventHead/Event/ClaimOrEvent defined); verifiers/adsc-clinical/cljs-orchestrator/src/main/adsc_clinical/nl_to_fol.cljs:11-37 (Claim-map-only rewrite, ?other->:OPAQUE); verifiers/bermuda/cljs-orchestrator/src/main/bermuda/nl_to_fol.cljs:56-93 (event->formula dispatch); docs/plans/2026-05-18-tier1-general-purpose.md:22 (ingest-trace EARS spec referenced)


---

## `duplicate-readme-linter-contradictory-gating` — MEDIUM

**Location:** `tools/lint_readme.py:33` · **area:** tools readme linters · **confidence:** high

**Finding.** Two README linters exist with contradictory gating definitions: the legacy tools/lint_readme.py classifies burstiness and ai-vocabulary as ADVISORY (8 gating rules, fail on any one), while tools/readme-lint/scripts/lint_readme.py classifies them as GATING (10 gating rules, fail only if gating_count>2) — so the same rule blocks in one tool and is advisory in the other.

**Fix.** Delete the legacy tools/lint_readme.py (no longer referenced by lefthook/Makefile/CI) or reconcile its rule classification with tools/readme-lint; keep a single source of truth for which rules gate the README.

**Evidence.** Both README linters exist and have contradictory rule classifications. The legacy tools/lint_readme.py defines GATING_RULES as 8 rule names (lines 33-42) and explicitly places ai-vocabulary (line 50) and burstiness (line 51) in ADVISORY_RULES, with fail-on-any-gating semantics (line 79: `return 1 if gate else 0`). The active tools/readme-lint/scripts/lint_readme.py defines GATING_RULES as 10 rule names including burstiness and ai-vocabulary (lines 39-44), with a softer fail-if-gating_count>2 threshold (line 65: `self.passes = self.gating_count <= 2`). So the identical rules burstiness and ai-vocabulary are advisory in one tool and gating in the other — a genuine contradiction in the source of truth for README gating. The materiality holds: lefthook.yml:24 and Makefile:55 both invoke only the readme-lint tool; the legacy tools/lint_readme.py is referenced nowhere in the active pipeline (only its own docstring and a dated QA doc docs/qa/README-QA-2026-05-17.md), confirming it is stale duplicate logic. This is a real maintenance hazard, not a stylistic nitpick. Not runtime-dependent — the rule sets are static literals.

**Citations.** tools/lint_readme.py:33-42 (GATING_RULES, 8 names), tools/lint_readme.py:50-51 (ai-vocabulary, burstiness in ADVISORY_RULES), tools/lint_readme.py:79 (fail on any gating); tools/readme-lint/scripts/lint_readme.py:39-44 (GATING_RULES, 10 names incl. burstiness, ai-vocabulary), tools/readme-lint/scripts/lint_readme.py:65 (passes = gating_count <= 2); lefthook.yml:24 and Makefile:55 (both invoke only tools/readme-lint scripts.lint_readme); grep showing tools/lint_readme.py referenced only in its own docstring and docs/qa/README-QA-2026-05-17.md


---

## `forge-path-shadowing` — LOW

**Location:** `skills/book-knowledge/scripts/__init__.py:19` · **area:** package layout / imports · **confidence:** medium

**Finding.** neurosym-forge's scripts dir is inserted at __path__[0], so it is searched before book-knowledge's own scripts; any future module-name collision would cause forge's module to shadow book-knowledge's, a latent correctness hazard.

**Fix.** Append forge's dir (__path__.append) instead of insert(0, ...) so book-knowledge's own modules always take precedence, or import the forge EDN modules under an explicit aliased package.

**Evidence.** The cited __init__.py (skills/book-knowledge/scripts/__init__.py:19) does `__path__.insert(0, _FORGE_SCRIPTS_DIR)`, prepending neurosym-forge's scripts dir to the package search path. I verified at runtime that scripts.__path__ resolves to ['...neurosym-forge/scripts', '...book-knowledge/scripts'] — forge's directory is searched first. Python's path-based FileFinder iterates __path__ in order and returns the first match, so for any submodule name present in both directories, `import scripts.<name>` would resolve to forge's copy, shadowing book-knowledge's own module. The mechanism the claim describes is therefore real and confirmed, not speculative. The issue is genuinely latent (not stylistic): today the only common filename is __init__.py itself (which is not resolved via __path__), so no collision fires now — consistent with the claim's own 'future module-name collision' framing and severity=low. The materiality is reinforced by the repo's own CLAUDE.md, which states cross-skill imports go through sibling_skills.py 'under an aliased package namespace to avoid scripts.* collisions' — the repo already treats scripts.* collisions as a real risk, yet this file merges forge into the same scripts namespace with forge taking precedence, the opposite of the established pattern. The suggested fix (append instead of insert(0), or use an aliased package) is sound. Low severity is accurate because the hazard is latent rather than active.

**Citations.** skills/book-knowledge/scripts/__init__.py:18-19 (`if _FORGE_SCRIPTS_DIR not in __path__: __path__.insert(0, _FORGE_SCRIPTS_DIR)`); runtime check: scripts.__path__ == ['...neurosym-forge/scripts', '...book-knowledge/scripts'] (forge first); directory listing shows only __init__.py is currently common to both scripts dirs (no live collision); CLAUDE.md cross-skill conventions section documents sibling_skills.py aliasing 'to avoid scripts.* collisions'.


---

## `panel-size-doc-inconsistency` — LOW

**Location:** `skills/book-review/SKILL.md:67` · **area:** documentation · **confidence:** high

**Finding.** SKILL.md is internally inconsistent on panel size: the description and Personas list specify seven personas, but the Workflow/Usage sections say 'full five-persona pass', misleading operators about how many subagents dispatch.

**Fix.** Update the Usage and Workflow lines to 'full seven-persona pass' to match the shipped personas/ directory and load_all behavior.

**Evidence.** The cited line 67 reads: '"Review chapter X with personas" — full five-persona pass.' This contradicts the rest of the same SKILL.md, which states "Seven personas" in the description (line 3) and "Dispatches up to seven persona subagents in parallel" (line 14), and lists exactly seven named personas in the Personas section (lines 33-39: Gottlieb, Lay Reader, Domain Expert, Copyeditor, Enjoyment Reader, AI-Slop Detector, First-Time Visitor). The personas/ directory ships exactly those seven files, confirming seven is the correct count and "five" is the stale/erroneous value. This is a real, material doc-accuracy defect, not stylistic nitpicking: the Usage line is the operator-facing description of what the primary trigger phrase dispatches, and CLAUDE.md explicitly states SKILL.md usage must stay accurate because "broken commands here mislead operators." An operator reading line 67 would expect five subagents when the workflow actually dispatches one packet per persona (seven). The suggested fix (change "five-persona" to "seven-persona") matches the shipped personas/ directory and the parallel-dispatch behavior described in the Workflow section (line 54, "one packet per persona"). Severity low is appropriate since it is a documentation-only count mismatch with no runtime consequence.

**Citations.** C:/Users/charl/russellian-book-suite/skills/book-review/SKILL.md:67 ("full five-persona pass"); contradicted by SKILL.md:3 ("Seven personas"), SKILL.md:14 ("up to seven persona subagents in parallel"), SKILL.md:33-39 (seven named personas), SKILL.md:54 ("one packet per persona"); personas/ dir contains exactly 7 files (ai-slop-detector.md, copyeditor.md, domain-expert.md, enjoyment-reader.md, first-time-visitor.md, gottlieb.md, lay-reader.md).


---

## `dead-evidence-rules` — LOW

**Location:** `skills/book-thesis/rules/consistency.dl:57` · **area:** datalog rules · **confidence:** high

**Finding.** The evidence_met/missing_evidence rules (and the requires_evidence facts that feed them) are computed but never queried by datalog_consistency.run, which only _collects orphan/contradiction/conflict/unreachable/unadvanced — so the missing-evidence detector is dead code.

**Fix.** Either _collect('missing_evidence',2) in run() and emit a defect (e.g. a D12/D11 'evidence-slot-unmet'), or remove the evidence_met/missing_evidence/requires_evidence machinery if not intended for v6.0.

**Evidence.** The rules file defines evidence_met/2 and missing_evidence/2 (consistency.dl:58-59), fed by the requires_evidence extensional facts (asserted in datalog_consistency.py:104-105 from the requiresEvidence triples). But run() (datalog_consistency.py:154-198) only _collects orphan_paragraph, direct_contradiction, transitive_contradiction, declared_conflict, unreachable_supports, and unadvanced_sub_arg. There is no _collect("missing_evidence", 2) or _collect("evidence_met", 2) anywhere, so the derived predicate is never queried and no defect is ever emitted from it. A repo-wide grep shows missing_evidence/evidence_met appear only in the rule definitions, the TERMS create_terms string (lines 32-33), and a doc comment (line 24) — never in any query or report-building code. The module docstring (lines 5-9) enumerates defect classes D9/D10/D11/D12 with no missing-evidence class. So the rules, the derived facts, and the requires_evidence machinery feeding them are dead with respect to the reporting path. This is a real, material gap (an intended invariant check that silently never fires), not a stylistic nitpick; the claim does not depend on runtime behavior and is statically verifiable. Severity "low" is reasonable since it is a missing detector rather than a wrong result.

**Citations.** skills/book-thesis/rules/consistency.dl:57-59 (evidence_met/missing_evidence rules); skills/book-thesis/scripts/datalog_consistency.py:104-105 (requires_evidence asserted); datalog_consistency.py:175-193 (run() _collect calls — no missing_evidence); datalog_consistency.py:32-33 (TERMS declares missing_evidence/evidence_met but only as terms); grep across repo shows no _collect/query of missing_evidence or evidence_met


---

## `verdict-schema-vs-rust-keys` — LOW

**Location:** `verifiers/bermuda/cljs-orchestrator/src/main/bermuda/ir.cljs:48` · **area:** cljs↔Rust verdict contract · **confidence:** high

**Finding.** ir/Verdict declares :verified-claims/:proofs/:graph-summary but the Rust emit_verdict actually emits :explanation/:queries/:cozo-defects/:corpus-defects and never emits :verified-claims/:proofs — the malli post-condition passes only because malli maps are open, so the schema documents fields the verifier never produces and omits fields it always does.

**Fix.** Align ir/Verdict with the keys emit_verdict actually serializes (:explanation, :queries, :cozo-defects, :corpus-defects) and drop or mark-optional the unused :verified-claims/:proofs.

**Evidence.** The CLJS ir/Verdict schema (ir.cljs:48-54) declares :status, :verified-claims, :core, :proofs, :graph-summary. The Rust emit_verdict (ir.rs:145-204) serializes exactly :status, :core, :explanation, :queries, :cozo-defects, :corpus-defects — and nothing else. The only overlap is :status and :core. So the schema declares :verified-claims/:proofs/:graph-summary which the verifier never emits, and omits :explanation/:queries/:cozo-defects/:corpus-defects which it always emits. The schema is used as a malli :post condition in phases.cljs:18 on the parsed Rust verdict. Malli [:map] schemas are open (extra keys permitted) and the three drifted keys are all {:optional true}, so the validation passes despite the mismatch — exactly the mechanism the claim describes. The claim mislabels :graph-summary (claims it's declared, which it is) but is otherwise precisely accurate; minor wording aside, this is a real contract-documentation drift that the open-map semantics silently mask. Severity low is fair: it does not break validation, but the schema misdocuments the actual cljs↔Rust verdict contract.

**Citations.** verifiers/bermuda/cljs-orchestrator/src/main/bermuda/ir.cljs:48-54 (Verdict schema); verifiers/bermuda/rust-verifier/src/ir.rs:145-204 (emit_verdict emits :status/:core/:explanation/:queries/:cozo-defects/:corpus-defects); verifiers/bermuda/cljs-orchestrator/src/main/bermuda/phases.cljs:18 (:post (m/validate ir/Verdict %))


---

## `duplicated-placeholder-helper` — LOW

**Location:** `skills/review-conductor/scripts/outcomes_loader.py:21` · **area:** shared helpers · **confidence:** high

**Finding.** _PLACEHOLDER_TEXTS and _is_placeholder are duplicated verbatim in aggregate_panel.py and outcomes_loader.py, so any future change to placeholder detection must be made in two places and can drift.

**Fix.** Extract _is_placeholder/_PLACEHOLDER_TEXTS into a single shared module (or reuse book-review's definition via sibling_skills) and import it in both files.

**Evidence.** Both files in the same scripts/ directory contain byte-for-byte identical definitions of _PLACEHOLDER_TEXTS and _is_placeholder. In outcomes_loader.py: `_PLACEHOLDER_TEXTS = {"_(none)_", "(none)", "_none_", "none"}` (line 21) and `_is_placeholder` (lines 24-26). In aggregate_panel.py the exact same set literal (line 12) and identical function body (lines 15-17). Both are used for the same purpose (filtering placeholder findings parsed from review reports). This is genuine logic duplication, not coincidental similarity: the strip-chain `text.strip().lower().strip("_*-").strip()` and the dual-membership check are non-trivial and would silently drift if one is edited without the other. The duplication is real and material (any change to placeholder detection semantics must be mirrored), though severity is low as claimed since both copies live in the same package and the logic is small. The suggested fix is viable: both files already import via the local `sibling_skills` module, so extracting into a shared sibling module is straightforward.

**Citations.** skills/review-conductor/scripts/outcomes_loader.py:21,24-26 (and uses at 34,38,42); skills/review-conductor/scripts/aggregate_panel.py:12,15-17 (and use at 25). Grep across the whole repo confirms these are the only two definitions, both verbatim identical.


---

## `sweeping-abstraction-never-consumed` — LOW

**Location:** `skills/russellian-style/scripts/lint_ai_vocabulary.py:91` · **area:** assets/ai-vocabulary · **confidence:** high

**Finding.** The supplement's named pattern 'sweeping_abstraction_subject' (with head_nouns and exemption) is fully specified in ai-vocabulary-supplement.json but the linter explicitly defers it, so this advertised pattern is dead config that detects nothing.

**Fix.** Either implement the dependency-parse-based subject check (the parser is already loaded elsewhere in this skill) or remove the pattern from the supplement so the catalog does not overstate coverage.

**Evidence.** The supplement JSON defines four patterns. The linter explicitly handles three of them — false_certainty (line 49), magic_adverb (line 63), transition_adverb_starter (line 77) — each building a regex/matcher and emitting findings. The fourth, sweeping_abstraction_subject, is fully specified in the supplement (id, description, head_nouns list, exemption) but the linter does nothing with it: line 91 is a bare comment "# Note: sweeping_abstraction_subject requires a dependency parser; deferred." with no code reading patterns_by_id['sweeping_abstraction_subject'], head_nouns, or exemption. A repo-wide grep confirms the only references are the JSON definition and the deferral comment — no consumer anywhere. So this advertised pattern detects nothing; it is dead config that overstates the catalog's coverage. The issue is real and material (a configured detection rule silently produces zero findings), though severity is appropriately low since it fails open (no false negatives in active rules, just a missing capability). The suggested fix is sound.

**Citations.** skills/russellian-style/scripts/lint_ai_vocabulary.py:91 (deferral comment, no implementation); skills/russellian-style/scripts/lint_ai_vocabulary.py:49,63,77 (the three patterns that ARE consumed); skills/russellian-style/assets/ai-vocabulary-supplement.json:13-18 (full spec of the unused pattern with head_nouns and exemption); grep across skills/russellian-style shows only the JSON definition and the deferral comment reference the pattern — no consumer.


---

## `legacy-lint-readme-dead-code` — LOW

**Location:** `tools/lint_readme.py:0` · **area:** tools readme linters · **confidence:** high

**Finding.** tools/lint_readme.py is dead code: lefthook, Makefile, and the readme-lint test suite all invoke tools/readme-lint/scripts/lint_readme.py instead, and only stale docs reference the old top-level script.

**Fix.** Remove tools/lint_readme.py and update the stale doc references in docs/qa/README-QA-2026-05-17.md and the spec, to avoid two divergent implementations of the same gate.

**Evidence.** The claim holds. Two distinct implementations of the README lint gate exist: the top-level tools/lint_readme.py (a generic single-file/stdin linter with GATING/ADVISORY rule split and a VERDICT line) and tools/readme-lint/scripts/lint_readme.py (a section-aware runner that splits README at H2 boundaries, reads per-section voice declarations, and gates on >2 violations per section). Every active invoker targets the latter: lefthook.yml:24 runs `cd tools/readme-lint && .venv/bin/python -m scripts.lint_readme`; Makefile:55 runs the same command for the `readme-lint` target (also reachable via `make preflight`/`lint`? no — readme-lint is its own target invoked per the README); and the test suites tools/readme-lint/tests/test_lint_readme.py and test_real_readme.py both `from scripts.lint_readme import ...` resolving to the readme-lint package, not the top-level script. The top-level tools/lint_readme.py is imported/invoked by nothing in the build or test machinery — the only references are its own usage docstring and stale documentation: docs/qa/README-QA-2026-05-17.md (lines 7, 13, 44, dated before the 2026-05-22 rewrite) names `tools/lint_readme.py` as the lint helper. So tools/lint_readme.py is genuinely dead code maintaining a divergent second implementation of the same gate (different rule taxonomy, no H2/voice parsing), which is a real, material architecture issue. One nuance on the suggested fix: the spec reference at docs/specs/2026-05-22-readme-rewrite-design.md:58 ("line-based H2 splitter in lint_readme.py") actually describes the NEW readme-lint script (which contains the H2 splitter), not the old top-level one which has no splitter — so that particular doc line is not a stale reference to the dead file. The core claim and the qa-doc stale references are nonetheless accurate.

**Citations.** tools/lint_readme.py:1-83 (generic single-file linter, no H2 splitter, self-referential docstring only); tools/readme-lint/scripts/lint_readme.py:109-249 (the real section-aware runner with parse_readme/run_full_lint/main); lefthook.yml:22-24 (readme-lint hook invokes tools/readme-lint .venv -m scripts.lint_readme); Makefile:5,54-55 (readme-lint target invokes the same); tools/readme-lint/tests/test_lint_readme.py:3,81 and tools/readme-lint/tests/test_real_readme.py:12 (import from scripts.lint_readme in the readme-lint package); docs/qa/README-QA-2026-05-17.md:7,13,44 (stale references to tools/lint_readme.py); docs/specs/2026-05-22-readme-rewrite-design.md:58 (H2-splitter reference actually describes the new script, not the dead one)


---

## `expansion-writes-real-corpus-bypassing-runs` — LOW

**Location:** `tools/russellian-style-audit/scripts/expansion.py:154` · **area:** russellian-style-audit expansion · **confidence:** medium

**Finding.** run_expansion_batch appends directly to the live skills/russellian-style/assets/russell-corpus/index.json and rewrites the live corpus-map on operator accept, mutating committed skill assets from a tool/audit run rather than into the batch's isolated runs/ directory.

**Fix.** Stage the append into a per-batch output and require an explicit promote step (or guard behind a flag) before mutating the committed russellian-style asset, so an audit run cannot silently rewrite a shipped corpus file.

**Evidence.** The claim is accurate. In expansion.py the module-level constants resolve to committed skill assets: _INDEX_PATH = skills/russellian-style/assets/russell-corpus/index.json (line 63) and _CORPUS_MAP_PATH = skills/russellian-style/references/russell-corpus-map.md (line 64), both computed off _REPO_ROOT, not off the per-batch run_dir. The Stage 5 append (lines 154-155) calls append_verified_to_index(index_path=_INDEX_PATH) and regenerate_corpus_map(out_path=_CORPUS_MAP_PATH) directly against those live paths. append_to_index.py confirms there is no staging: append_verified_to_index calls append_index_entries(index_path, new_entries) on the passed path (line 43) and regenerate_corpus_map does out_path.write_text(...) in place (line 76). The run_dir passed by run.py (bundle/runs/<batch_id>, run.py:47) only receives intermediate candidates/verified/rejected/sample files; the final accepted output bypasses it and lands in the committed assets. There is no promote step or isolation flag; the only guards are the operator gate plus a <10% audit-reject threshold (expansion.py:137-151), and --auto-accept (run.py:81-83) bypasses even the operator gate. So an audit/tool run does rewrite shipped russellian-style corpus files in place. Given CLAUDE.md's single-writer ledger-ownership conventions, this cross-tool in-place mutation of committed skill assets is a real, low-severity architectural concern. It is gated rather than truly silent, but the substance of the finding holds.

**Citations.** tools/russellian-style-audit/scripts/expansion.py:62-64 (asset path constants off _REPO_ROOT); expansion.py:154-155 (append + regenerate against live paths); expansion.py:82-86 (run_dir holds only intermediates); tools/russellian-style-audit/scripts/run.py:47 (run_dir = bundle/runs/<batch_id>), run.py:81-91 (gate/auto-accept and call); tools/build-russell-corpus/scripts/append_to_index.py:43 (append_index_entries on passed index_path), :76 (out_path.write_text in place)


---

## `audit-bundle-path-not-batch-scoped` — LOW

**Location:** `tools/russellian-style-audit/scripts/run.py:24` · **area:** russellian-style-audit run · **confidence:** high

**Finding.** The audit bundle root is hardcoded to docs/audits/2026-05-21-russellian-style and is not parameterised by --batch-id, so re-running with a different batch-id overwrites the prior bundle's README/health-check/samples (only runs/<batch-id>/ is isolated).

**Fix.** Incorporate batch_id (and/or date) into the bundle root path so successive audit runs do not clobber earlier reports.

**Evidence.** The claim is accurate. At line 24 the bundle root is a hardcoded literal `_REPO_ROOT / "docs" / "audits" / "2026-05-21-russellian-style"` with no batch_id or date parameterisation. At line 43 `bundle = _AUDIT_BUNDLE_ROOT` assigns this fixed path directly; the only batch-scoped path is `run_dir = bundle / "runs" / args.batch_id` (line 47). All other report artifacts are written to the shared `bundle` root: `health-check.md` (line 51), `README.md` (lines 60 and 141), `expansion.md` (lines 66, 75, 98), and the entire `samples/` directory (`samples_dir = bundle / "samples"`, line 45; written at lines 113/121/137). Re-running `python -m scripts.run --batch-id <new-id>` will `mkdir(..., exist_ok=True)` over the same root and `write_text` over each of those files, clobbering the prior batch's reports while only `runs/<batch-id>/` stays isolated. This is a real, material architectural issue for an audit tool whose purpose is to retain per-batch reports, though severity is reasonably rated low since the per-run data under `runs/` is preserved. The finding does not depend on runtime behavior — it is clear from the static path construction.

**Citations.** C:/Users/charl/russellian-book-suite/tools/russellian-style-audit/scripts/run.py:24 (hardcoded `_AUDIT_BUNDLE_ROOT`); :43 (`bundle = _AUDIT_BUNDLE_ROOT`); :45 (`samples_dir = bundle / "samples"`); :47 (`run_dir = bundle / "runs" / args.batch_id` — only batch-scoped path); :51, :60, :98, :141 (README/health-check/expansion written to shared `bundle`)


---

## `duplicate-contract-load-in-assembly` — INFO

**Location:** `skills/book-compose/scripts/build_book.py:57` · **area:** manuscript assembly · **confidence:** medium

**Finding.** build_book loads each chapter contract via load_contract twice (once in _assemble_manuscript for titles, again in book_summary.collect_chapter_data), redundant disk reads and re-validation of the same YAML per chapter.

**Fix.** Load contracts once and thread the titles/contracts through to both manuscript assembly and summary building.

**Evidence.** The claim holds against the actual code. In build_book (build_book.py:151 and 154) both _assemble_manuscript and build_book_summary are invoked with the same workspace and chapter_versions in a single build. _assemble_manuscript loops chapters and calls load_contract(contracts_dir / f"{chapter_id}.yaml") at build_book.py:57-59 solely to read contract["title"]. build_book_summary delegates to collect_chapter_data, which loops the same chapters and calls the identical load_contract(contracts_dir / f"{chapter_id}.yaml") at book_summary.py:58-59 (also using purpose and chapter_type). The path is constructed identically (chapters/contracts/<id>.yaml) in both places. load_contract (chapter_contract.py:51-54) performs an uncached disk read_text plus jsonschema.validate on every call, with no memoization anywhere. So each chapter's contract YAML is read from disk and re-validated exactly twice per build. The issue is real and material (redundant I/O + jsonschema validation scaling with chapter count), though severity "info" is fair since it is a performance/architecture concern, not a correctness bug. The suggested fix (load contracts once and thread titles/contracts to both consumers) is sound.

**Citations.** C:/Users/charl/russellian-book-suite/skills/book-compose/scripts/build_book.py:57-59 (load_contract in _assemble_manuscript), :151 and :154 (both consumers called); C:/Users/charl/russellian-book-suite/skills/book-compose/scripts/book_summary.py:58-59 (load_contract in collect_chapter_data), :101 (build_book_summary calls collect_chapter_data); C:/Users/charl/russellian-book-suite/skills/book-compose/scripts/chapter_contract.py:51-54 (load_contract: uncached read_text + jsonschema.validate)


---

## `markdown-it-py-unused-dep` — INFO

**Location:** `skills/russellian-style/pyproject.toml:12` · **area:** packaging · **confidence:** high

**Finding.** markdown-it-py is declared as a runtime (and [ci]) dependency but is never imported anywhere in the skill; all parsing is regex+spaCy.

**Fix.** Remove markdown-it-py from dependencies, or actually use it for the ad-hoc markdown paragraph/code-block splitting that is currently duplicated by hand-rolled regex in several linters.

**Evidence.** markdown-it-py is declared as a runtime dependency (pyproject.toml line 12) and again in the [ci] extra (line 20), but no Python file in skills/russellian-style imports it. Targeted greps for markdown_it, MarkdownIt, mdit, "import markdown", and "markdown-it" across all .py files returned zero matches; the only hits for "markdown-it-py" are the two pyproject.toml declarations themselves. The 18 files containing the substring "markdown" only do so in comments/docstrings/strings, not as the package. The claim that parsing is hand-rolled is corroborated by lint_common.py, where _split_paragraphs splits on blank lines and _is_code_block detects fences via para.lstrip().startswith("```") and 4-space indents — i.e., regex/string heuristics, not a markdown-it parser, with spaCy handling sentence segmentation. This is a real, material packaging issue: an unused runtime dependency forces every install to pull markdown-it-py (and its mdurl transitive dep) for no benefit. Static analysis is fully sufficient here; the dependency could in principle only be reached via dynamic import, but no such import string exists anywhere, so the verdict is confirmed rather than uncertain.

**Citations.** skills/russellian-style/pyproject.toml:12 (runtime dep), pyproject.toml:20 ([ci] dep); zero imports found via grep for markdown_it|MarkdownIt|mdit|import markdown across all .py files; skills/russellian-style/scripts/lint_common.py:54-76 (_split_paragraphs blank-line split and _is_code_block fence/indent regex confirm hand-rolled markdown handling)


---
