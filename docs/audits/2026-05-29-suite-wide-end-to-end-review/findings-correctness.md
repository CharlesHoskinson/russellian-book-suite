# Correctness & bugs — findings

67 confirmed findings. Each survived an independent adversarial-verify pass; the evidence line cites code that was opened and read.

## `sentinel-d9-d13-not-hard-fail` — CRITICAL

**Location:** `skills/book-qa/scripts/sentinel.py:62` · **area:** book-qa/sentinel release gate · **confidence:** high

**Finding.** The sentinel release gate only treats D1-D8 (and critical C-classes) as hard-fail, so the critical reasoning/verification defects D9 (paragraph-orphan), D10 (transitive-contradiction), D11 (failed-entailment) and D13 (verification-unsat) — written into defects.json by lint_artifact — are silently routed to the non-blocking soft-gate and never block release nor get healed.

**Fix.** In _is_hard_fail, block on any critical defect regardless of class: replace the D-class whitelist with `if severity == 'critical' and (class_ in HARD_FAIL_D_CLASSES or class_ in {'D9','D10','D11','D13'} or class_.startswith('C')): return True`, or more robustly treat every severity=='critical' ticket as hard-fail. Add a sentinel test seeding a D11/D13 critical in defects.json and asserting hard_fail_count>0.

**Evidence.** The claim holds against the actual code. In sentinel.py, `_is_hard_fail(class_, severity)` (lines 62-70) returns True only for: (a) D1-D8 with severity critical (HARD_FAIL_D_CLASSES = {"D1".."D8"}, line 30/64), (b) class in {"C2","C13"} (line 66), or (c) any class starting with "C" that is critical (line 68); otherwise it returns False (line 70). D9, D10, D11, D13 are not in the D1-D8 whitelist, are not C2/C13, and do not start with "C", so even when critical they fall through to the non-blocking soft-gate (aggregate() at line 138 routes non-hard_fail tickets to `soft`). lint_artifact.py actually produces these as critical defects written into qa/defects.json: CRITICAL = "critical" (line 54); lint_d9_d12 emits D9 (line 374, default CRITICAL), D10 (line 405, default CRITICAL), D11 (line 437, hardcoded CRITICAL), and lint_d13_verification_unsat emits D13 (lines 473/481, hardcoded CRITICAL). Both are wired into the linter pipeline (lines 566-567) and serialized to qa/defects.json under the "class" key (lines 595-602), which sentinel's _load_stage1 reads via entry.get("class") (line 81) and severity (line 82), passing them to _is_hard_fail (line 92). Thus these critical reasoning/verification defects (paragraph-orphan, transitive-contradiction, failed-entailment, verification-unsat) never count toward hard_fail_count and never set exit code 1 (main, line 193), so they do not block release. This is a material correctness gap: severity-critical defects from the v6 reasoning substrate silently bypass the release gate. Note D12 is correctly important-only, consistent with the claim's exclusion of it.

**Citations.** skills/book-qa/scripts/sentinel.py:30 (HARD_FAIL_D_CLASSES D1-D8), :62-70 (_is_hard_fail logic), :138 (soft routing), :193 (exit code); skills/book-qa/scripts/lint_artifact.py:54 (CRITICAL="critical"), :374,:405,:437 (D9/D10/D11 critical), :473,:481 (D13 critical), :566-567 (wired in), :595-602 (written to qa/defects.json under "class")


---

## `formula-shape-not-consumable-by-smt` — CRITICAL · needs runtime verification

**Location:** `verifiers/bermuda/cljs-orchestrator/src/main/bermuda/nl_to_fol.cljs:21` · **area:** NL→FOL / SMT walk contract · **confidence:** high

**Finding.** nl_to_fol emits nested {:kind :expression :head {...} :args [...]} trees, but smt.rs check_all dispatches on flat :subject/:predicate/:value keys per atom, so every translated formula would be skipped (no subject/predicate/value) even if parsing succeeded — the verifier verifies nothing.

**Fix.** Emit atoms in the flat :kind/:id/:predicate/:subject/:value shape that ir.rs/smt.rs actually read, or document that the CLJS translate path is not the atom-production path and remove it from the verify pipeline.

**Evidence.** The cited code says exactly what the claim asserts. nl_to_fol.cljs `legacy-claim->formula` (lines 21-47) and `event->formula` (56-78) emit nested `{:kind :expression :sort :formula :head {...} :args [...]}` trees; `claim->formula`/`translate-corpus` (80-93) just map this over the corpus, producing a bare vector of such trees. The Rust consumer, smt.rs `bind_atoms` (lines 328-398), only binds an atom when it has flat `:kind :expression` (334), `:predicate` (337-340), `:subject` (341-344), and `:value` (348-351) keys; any atom missing these hits `continue` and contributes nothing to the solver. The nested-tree formulas carry none of these top-level keys, so every translated formula is skipped and the solver asserts nothing (trivially sat) — the verifier verifies nothing on this path. The mismatch is in fact worse than claimed: ir.rs `parse_formulas` (124-142) requires a top-level `{:atoms [...]}` map and reads a flat `:id` per atom, but `phases/verify` (phases.cljs 16-19) serializes translate's bare vector via `pr-str` with no `:atoms` wrapper, so parse_formulas would error 'missing or non-vector :atoms' before binding even runs. The intended wiring is real (translate's malli `:post` is `[:vector ir/Formula]` and verify's `:pre` is the same schema; ir.cljs Formula=Atom is the nested `:kind/:sort` tree, lines 14-19), yet ir.rs's own doc (lines 4-11) shows the production atomspace is the flat Python-emitted `:atoms` shape — confirming the CLJS translate path emits a shape the SMT walk cannot consume. This is a material correctness defect, not a nitpick, and matches the suggested fix (emit flat `:atoms`/`:predicate`/`:subject`/`:value` or remove the translate path from verify). Static analysis is conclusive; no runtime needed.

**Citations.** verifiers/bermuda/cljs-orchestrator/src/main/bermuda/nl_to_fol.cljs:21-47 (nested :expression/:head/:args output), :56-78, :80-93; verifiers/bermuda/rust-verifier/src/smt.rs:328-351 (bind_atoms requires flat :kind/:predicate/:subject/:value, else continue); verifiers/bermuda/rust-verifier/src/ir.rs:4-11,124-142 (expects {:atoms [...]} with flat keys); verifiers/bermuda/cljs-orchestrator/src/main/bermuda/phases.cljs:11-19 (translate->verify wiring, pr-str bare vector); verifiers/bermuda/cljs-orchestrator/src/main/bermuda/ir.cljs:14-19 (Formula=Atom nested tree); verifiers/bermuda/cljs-orchestrator/src/main/bermuda/core.cljs:18-19


---

## `verify-ir-contract-mismatch` — CRITICAL · needs runtime verification

**Location:** `verifiers/bermuda/cljs-orchestrator/src/main/bermuda/phases.cljs:19` · **area:** cljs↔Rust bridge/IR contract · **confidence:** high

**Finding.** phases/verify sends (pr-str formulas) as a bare vector of nested expression maps, but the Rust parse_formulas requires a top-level {:atoms [...]} map and errors 'missing or non-vector :atoms' on a bare vector, so verify can never succeed against the real native addon.

**Fix.** Wrap the payload as (pr-str {:atoms formulas}) and/or have translate-corpus emit flat atoms carrying :id/:predicate/:subject/:value as ir.rs documents; add a round-trip test that feeds translate output through the real parse_formulas shape.

**Evidence.** The claim holds against the actual code. phases.cljs:19 calls (b/verify-formulas (pr-str formulas)). bridge.cljs:7-8 passes that string straight to the native addon's verifyFormulas, which is lib.rs:19's verify_formulas, which calls ir::parse_formulas at lib.rs:20. parse_formulas (ir.rs:124-132) parses the EDN and immediately does parsed.get(":atoms"), requiring a top-level map with an :atoms vector; otherwise it returns Err(Error::Parse("missing or non-vector :atoms")) at ir.rs:131 — the exact error string in the claim. But the payload is what translate-corpus produces: nl_to_fol.cljs:92-93 returns (into [] ...) — a bare CLJS vector of nested {:kind :expression :head ... :args ...} maps. pr-str of that is a top-level EDN vector, so .get(":atoms") yields None and the error fires before any SMT work. So verify can never succeed against the real addon. The mismatch is compounded: ir.rs:1-8 documents the expected atom shape as flat docs with :id/:predicate/:subject/:value (and :id is extracted at ir.rs:135), whereas translate-corpus emits deeply nested expression trees with no top-level :id. This is a material correctness bug, not a nitpick. The static contract is unambiguous; only end-to-end runtime confirmation (whether any test drives this path through the real addon) is unobserved, but that does not change the contract violation.

**Citations.** verifiers/bermuda/cljs-orchestrator/src/main/bermuda/phases.cljs:19 (verify sends (pr-str formulas)); verifiers/bermuda/cljs-orchestrator/src/main/bermuda/bridge.cljs:7-8 (passes string to .verifyFormulas); verifiers/bermuda/cljs-orchestrator/src/main/bermuda/nl_to_fol.cljs:92-93 (translate-corpus returns bare (into [] ...) vector of nested expression maps); verifiers/bermuda/rust-verifier/src/lib.rs:19-21 (verify_formulas -> parse_formulas); verifiers/bermuda/rust-verifier/src/ir.rs:124-132 (requires {:atoms [...]}, else Err "missing or non-vector :atoms"); ir.rs:1-8 and ir.rs:135 (expected flat atom shape with :id)


---

## `adsc-missing-uint-arm-drops-ints` — CRITICAL

**Location:** `verifiers/adsc-clinical/rust-verifier/src/smt.rs:82` · **area:** smt divergence (adsc-clinical) · **confidence:** high

**Finding.** The adsc-clinical smt.rs lacks the Edn::UInt match arm that bermuda added; edn-rs renders bare non-negative integers as Edn::UInt, which falls through to `_ => continue`, so every plain-integer constraint value (e.g. :trial-n 15) is silently dropped and never asserted to Z3 — a silent false-sat.

**Fix.** Port the Edn::UInt arm from bermuda/smt.rs into adsc-clinical/smt.rs (bind as Int with a checked try_into), and treat the two copies as one source via shared codegen to stop them diverging.

**Evidence.** The adsc-clinical smt.rs value-binding `match value` block (lines 82-104) has arms only for Edn::Int, Edn::Double, Edn::Str, and Edn::Bool, then `_ => continue` at line 103. It has no Edn::UInt arm. The bermuda copy (smt.rs lines 362-395) is structurally identical but DOES include an Edn::UInt arm (lines 371-377) with a checked try_into to i64 bound as Int, and a comment explaining "edn-rs renders bare non-negative integers as Edn::UInt rather than Edn::Int ... (e.g. :trial-n 15)". osmotic_pressure has the same fix (smt.rs line 477) plus a regression test (tests/multi_valued_binding.rs:89-123) that asserts edn-rs 0.19 parses positive int literals as Edn::UInt and that two contradictory UInt bindings must be :unsat — proving :sat results when the UInt values are silently dropped via `_ => continue`. adsc-clinical's Cargo.toml pins the same `edn-rs = "0.19"` (line 21), so the parsing behavior is identical. Therefore in adsc-clinical every plain non-negative integer constraint value (the common case for counts like :trial-n 15) hits `_ => continue`, is never asserted to Z3, and contradictory integer constraints would return a false :sat. This is a material correctness defect (silent false-sat), not a stylistic nitpick, and the suggested fix (porting the UInt arm) is correct.

**Citations.** verifiers/adsc-clinical/rust-verifier/src/smt.rs:82-104 (Int/Double/Str/Bool arms then `_ => continue` at 103, no UInt arm); verifiers/bermuda/rust-verifier/src/smt.rs:367-377 (the Edn::UInt arm absent from adsc); verifiers/osmotic_pressure/rust-verifier/src/smt.rs:477 (same fix); verifiers/osmotic_pressure/rust-verifier/tests/multi_valued_binding.rs:84-122 (regression test confirming edn-rs 0.19 yields Edn::UInt and dropped values produce false :sat); verifiers/adsc-clinical/rust-verifier/Cargo.toml:21 (edn-rs = "0.19")


---

## `kg-undefined-relations-runtime-fail` — CRITICAL · needs runtime verification

**Location:** `verifiers/bermuda/rust-verifier/src/kg.rs:193` · **area:** kg / Cozo knowledge-graph · **confidence:** high

**Finding.** ingest_and_summarize runs a Datalog query against stored relations claim/load-bearing and claim/posterior that build_db never creates (it only creates the claim relation), so the query errors and verify_formulas returns Err on every call in the default (kg-enabled) build.

**Fix.** Either create the load-bearing/posterior relations in build_db (populated from the Claim fields), or guard the query so it is skipped when those relations are absent; regenerate kg.rs from a query validated against Cozo. Also fix the non-Cozo syntax (?claim leading-? vars and the `<[?p, 0.8]` comparison are Datomic-style, not Cozo).

**Evidence.** The claim holds against the actual code. build_db (kg.rs:165-185) creates exactly one stored relation: `:create claim {id: String => source: String}` (line 170), and only ever `:put`s into `claim` (line 177). It never creates `claim/load-bearing` or `claim/posterior`. The compiled-by-default `#[cfg(feature = "kg")]` branch of ingest_and_summarize (lines 187-217; `kg` is in `default = ["smt","eqsat","kg"]` in Cargo.toml:10) runs the Q001 script at line 193 against those two non-existent stored relations. In Cozo 0.7, referencing a stored relation that was never `:create`d is an unconditional runtime error during run_script, independent of the claims data (it errors even on an empty slice), so the `.map_err(...)?` at line 200 returns Err(Error::Kg) on every invocation. verify_formulas (lib.rs:19-33) calls ingest_and_summarize at line 27 and propagates that Err via `.map_err(...)?` at line 28, so verify_formulas returns Err. The suggested-fix observations are also correct: the query uses Datomic-style leading-`?` body variables (`?claim`, `?p`) and a prefix comparison form `<[?p, 0.8]`, neither of which is valid Cozo (Cozo uses bare body vars and infix `?p < 0.8`), so the script would also fail to compile even if the relations existed — both fault paths land on the same Err. The only nuance: it is not literally "every call" but every call that first clears parse_formulas and smt::check_all (lib.rs:20-23); that does not reduce materiality. Severity critical is justified — the entire kg path of the verifier is dead in the default build.

**Citations.** verifiers/bermuda/rust-verifier/src/kg.rs:170 (only `claim` relation created), :177 (only inserts into claim), :193 (query references claim/load-bearing and claim/posterior with `?`-prefixed vars and `<[?p, 0.8]`), :200 (Err propagated via map_err/?); verifiers/bermuda/rust-verifier/src/lib.rs:27-28 (verify_formulas propagates the Err); verifiers/bermuda/rust-verifier/Cargo.toml:10 (kg is default-enabled)


---

## `infer-kind-reads-absent-path` — HIGH

**Location:** `skills/book-knowledge/scripts/export_symbolic_trace.py:36` · **area:** symbolic-trace export / provenance · **confidence:** high

**Finding.** _infer_kind keys off manifest['path'] and _manifest_to_event reads manifest['path']/['title'], but the source-manifest schema sets additionalProperties:false and forbids path/title, so production manifests (written by ingest) never carry them — every real exported trace tags sources as :unknown kind despite the manifest's authoritative source_kind field.

**Fix.** Infer kind from manifest['source_kind'] (the field ingest actually writes) and drop the path/title/trust reads, or relax the schema; the export tests pass only because their hand-crafted manifests inject the forbidden path/title keys.

**Evidence.** The exporter's _infer_kind (export_symbolic_trace.py:36-47) keys entirely off manifest['path'] (with a secondary doc_id "thesis" substring check) and never reads source_kind (grep: 0 occurrences in the exporter). _manifest_to_event (lines 50-63) similarly emits :path and :title only when those keys exist. But the authoritative schema source-manifest.schema.json sets additionalProperties:false with properties limited to {doc_name, doc_id, source_kind, sha256, byte_size, ingested_at, ingested_by_run, page_count, node_count, tree_root, trust} — path and title are absent and therefore forbidden, and write_manifest()/load_manifest() validate against it (source_manifest.py:34-50). The real ingest writers confirm this: ingest_pdf.py:76-86 and ingest_markdown.py:65-75 build manifests with source_kind ("pdf"/"markdown") and no path/title/trust. Therefore every production manifest lacks path, _infer_kind falls through to Keyword("unknown") for all sources whose doc_id doesn't contain "thesis", and the authoritative source_kind field is ignored — a real, material correctness/provenance defect. The export tests pass only because their fixture (test_export_symbolic_trace.py:24-30) hand-writes a JSON manifest with the forbidden path/title/trust keys (and missing the required schema keys) directly via write_text, bypassing validate_manifest entirely. The suggested fix (infer kind from source_kind) is correct.

**Citations.** skills/book-knowledge/scripts/export_symbolic_trace.py:36-47 (_infer_kind reads manifest['path'], falls to :unknown), :57-60 (_manifest_to_event reads path/title); skills/book-knowledge/assets/source-manifest.schema.json:5-19 (required source_kind, properties list lacks path/title, additionalProperties:false); skills/book-knowledge/scripts/source_manifest.py:34-44 (write/validate enforce schema); skills/book-knowledge/scripts/ingest_pdf.py:76-87 and ingest_markdown.py:65-76 (real manifests carry source_kind, no path/title); skills/book-knowledge/tests/test_export_symbolic_trace.py:24-30 (fixture injects forbidden path/title/trust via raw write_text)


---

## `propagate-ignores-derivation-edges` — HIGH

**Location:** `skills/book-knowledge/scripts/propagate_belief.py:49` · **area:** belief graph / propagation · **confidence:** high

**Finding.** propagate() never reads graph.derivation_edges, so a derived claim's posterior is computed solely from its own status/sources/counter-claims and ignores its parents entirely, contradicting the docstring and SKILL.md claim of 'belief propagation over the derivation graph'.

**Fix.** Incorporate parent posteriors into each child's evidence inside the iteration loop (e.g. combine the child's own evidence with a function of max/product of parent p-values along derivation_edges), or remove the false 'propagation over the graph' description and the iteration scaffolding.

**Evidence.** The claim holds against the actual code. propagate() (propagate_belief.py:49-68) builds cc_by_target, seeds p[cid] from priors, then loops MAX_ITERATIONS=20 times. But the per-node computation inside the loop (lines 60-63) derives new_p[cid] purely from the node's own base prior, its own sources via _evidence_combine, and its own counter-claim damping. It never reads graph.derivation_edges nor any parent's p value, so a derived claim's posterior is fully independent of its parents. derivation_edges genuinely exists and is populated: belief_graph.py:42 declares it and lines 61-62 fill it from each record's derived_from list, so the data the propagation should consume is present and simply ignored. Because each node's new_p is a pure function of static inputs (prior, sources, counter-claims) and never of the prior iteration's p, every iteration produces identical values; the loop converges on iteration 2 and the entire fixed-point/iteration scaffolding is inert. This contradicts the module docstring at line 1 ("Bayesian belief propagation over the claim ledger's derivation graph") and SKILL.md:43 ("Bayesian belief propagation over PROV-O"). The issue is material, not stylistic: it is a real correctness gap between documented graph propagation and an implementation that performs only per-node local belief computation. No runtime observation is needed; the data flow is fully determinable statically.

**Citations.** skills/book-knowledge/scripts/propagate_belief.py:49-68 (loop body lines 59-63 reference only node.p_prior/status, node.sources, cc_by_target — never graph.derivation_edges); propagate_belief.py:1 (docstring claims propagation over derivation graph); skills/book-knowledge/scripts/belief_graph.py:42 (derivation_edges field) and belief_graph.py:61-62 (populated from derived_from); skills/book-knowledge/SKILL.md:43 ("Bayesian belief propagation over PROV-O")


---

## `healer-skips-critical-reasoning-defects` — HIGH

**Location:** `skills/book-qa/scripts/healer.py:111` · **area:** book-qa/healer · **confidence:** high

**Finding.** prepare_payloads only iterates report['hard_fail_tickets']; because D9-D13 criticals are misclassified as soft-gate by the sentinel, the bounded-iteration healer never receives them, so the documented 'patch critical, max 3 iters' loop cannot act on the metabook/verifier critical defect classes at all.

**Fix.** Fix the sentinel hard-fail classification (root cause); optionally have the healer also consider any soft-gate ticket with severity=='critical' as defensive depth.

**Evidence.** The claim holds end-to-end against the actual code. healer.py prepare_payloads iterates only report.get("hard_fail_tickets", []) (line 111), and its own docstring (lines 12-15) confirms soft-gate tickets are skipped. The premise that D9-D13 criticals land in soft-gate is also real, not hypothetical: lint_artifact.py emits D9/D10/D11/D13 as class_ "D9".."D13" with severity "critical" (docstring lines 17-21; emitters at lines 372-381 for D9, 473/481 for D13), and these feed sentinel.py's _load_stage1 which classifies via _is_hard_fail (line 92). _is_hard_fail (lines 62-70) only treats D1-D8 critical as hard-fail (HARD_FAIL_D_CLASSES = {"D1".."D8"} at line 30), and its catch-all critical rule is gated on class_.startswith("C"), which never matches a "D"-prefixed class. So every D9-D13 critical falls through to return False and is appended to soft_gate_tickets (line 138). Consequently the bounded "patch critical, max 3 iters" healer never receives the metabook (D9/D10/D12) or verifier (D11/D13) critical defect classes. This is a high-severity correctness gap: critical reasoning/verification defects silently bypass auto-healing. The bug is real and the root cause is the sentinel's hard-fail classification missing D9-D13, exactly as the suggested fix states; the static evidence is conclusive, so no runtime verification is needed.

**Citations.** skills/book-qa/scripts/healer.py:111 (and docstring lines 12-15); skills/book-qa/scripts/sentinel.py:62-70 (_is_hard_fail), line 30 (HARD_FAIL_D_CLASSES = D1-D8), line 92 (Stage-1 classification), line 138 (soft routing); skills/book-qa/scripts/lint_artifact.py:17-21 (D9-D13 critical doc), 372-381 (D9 emit critical), 473 and 481 (D13 emit CRITICAL); skills/book-qa/SKILL.md:75-78 (D9-D11 critical classes from book-thesis/verifier)


---

## `dedup-substring-drops-distinct-findings` — HIGH

**Location:** `skills/book-review/scripts/aggregate_reviews.py:40` · **area:** metric aggregation · **confidence:** high

**Finding.** _dedup_findings treats any finding whose normalized text contains, or is contained by, an earlier one as a duplicate, so a short generic finding seen first swallows a longer distinct finding and the survivor depends on alphabetical persona order.

**Fix.** Dedup only on exact normalized equality (or a token/similarity threshold), and never collapse via bare substring containment; if collapsing, keep the longer/more-specific text and merge persona attributions.

**Evidence.** Line 40 computes `is_dup = any(norm in s or s in norm for s in seen)`, which is bidirectional substring containment, not exact equality. Combined with the append-only `seen`/`out` logic (lines 41-43), the FIRST finding for a given substring family wins and any later finding that contains it or is contained by it is dropped. Tracing the scenario: if an early-iterated persona emits a short generic finding like "weak argument" it lands in `seen`; a later persona's longer, more-specific finding "weak argument about the gold standard in ch.3" matches `s in norm` and is discarded — the shorter, less-informative text survives. Iteration order is fixed by `_gather_reviews` (line 27 `sorted(reviews_dir.glob("*.md"))`) flattened in that order at lines 51-53, i.e. alphabetical review-file/persona order, so the survivor depends on filename ordering rather than content specificity. This silently drops distinct critical/important findings from the aggregated persona review and is non-deterministic with respect to specificity — a real, material correctness bug in metric/finding aggregation, statically verifiable. The suggested fix (exact normalized equality or similarity threshold, and if collapsing keep the longer text + merge persona attributions) is appropriate.

**Citations.** skills/book-review/scripts/aggregate_reviews.py:40 (`is_dup = any(norm in s or s in norm for s in seen)`); supporting context lines 35-44 (append-only seen/out), line 27 (`sorted(reviews_dir.glob("*.md"))` fixes order), lines 51-57 (flattened pairs fed to _dedup_findings in review order)


---

## `severity-counts-derived-from-dedup` — HIGH

**Location:** `skills/book-review/scripts/aggregate_reviews.py:59` · **area:** metric aggregation / soft-gate · **confidence:** high

**Finding.** severity_counts (which drives the critical>0 soft-gate) is computed from the post-dedup list length, so substring-collapse or dropped 10+ findings can lower the critical count and let a gating chapter pass.

**Fix.** Derive the gating critical count from the raw per-persona findings (or the validated critical_count frontmatter) rather than from the deduplicated display list; keep dedup for presentation only.

**Evidence.** The core claim holds on the still-live legacy gating path. In aggregate_reviews.py, crit_pairs pools every persona's critical findings (line 51), `_dedup_findings` collapses any finding whose normalized text is a substring of an already-seen finding across all personas (lines 35-44, `norm in s or s in norm`), and severity_counts['critical'] is then set to len(critical) of that post-dedup list (lines 55, 59-60). That deduped number is the single value written to persona-review.md as `- Critical: N` (line 86). The gate consumer, book-compose/chapter_contract_check.py, in its legacy branch calls `_read_persona_severity_counts` (line 110) which regex-parses exactly that `- Critical:` line (lines 38-47) into persona_critical_count, and the contract's `persona_critical_count == 0` acceptance test evaluates it (_evaluate_test, check_draft). So substring-collapse across personas can lower the gating critical count below the true number and let a chapter that should block pass. Notably the raw per-persona counts ARE computed (lines 67-73, len(r.critical)) but only rendered in the display table, not read by the gate, contradicting the rubric's claim (severity-rubric.md:70-72) that the gate sums per-persona counts. The suggested fix (gate off raw/validated counts, keep dedup for display) is exactly right. Two caveats that lower but do not negate materiality: (1) the newer verdict.json path (chapter_contract_check.py:81-91) uses an independent gating_criticals field and is preferred when present, so the bug only bites when verdict.json is absent/stale — but that legacy persona-review.md path is real, tested (test_review_pass.py:93), and the documented soft-gate per SKILL.md; (2) the claim's secondary phrase "dropped 10+ findings" is unsupported — there is no item cap in parse_review_report or _dedup_findings. The primary substring-collapse mechanism is genuine, so the finding is confirmed.

**Citations.** skills/book-review/scripts/aggregate_reviews.py:35-44 (_dedup_findings substring collapse across personas), :51 (crit_pairs pools all personas), :55,59-63 (severity_counts['critical']=len(deduped critical)), :67-73 (raw per-persona counts only for display table), :86 (writes single `- Critical:` line); skills/book-compose/scripts/chapter_contract_check.py:38-47 (_read_persona_severity_counts parses that `- Critical:` line), :110-116 (legacy path feeds persona_critical_count), :81-91 (preferred verdict.json path uses independent gating_criticals), :200-210 (check_draft evaluates acceptance tests); skills/book-review/references/severity-rubric.md:70-72 (rubric claims gate sums per-persona counts — mismatch); skills/book-review/scripts/dispatch_review.py:61-78,88-90 (.critical is full raw findings list, no cap)


---

## `findings-numbered-10plus-dropped` — HIGH

**Location:** `skills/book-review/scripts/dispatch_review.py:74` · **area:** review parsing · **confidence:** high

**Finding.** The list-item detector only matches numbered prefixes 1.-9., so any finding numbered 10 or higher is silently dropped from the parsed result.

**Fix.** Replace the fragile startswith tuple with a regex such as re.match(r'^([-*]\s|\d+\.)', line); strip the marker with re.sub(r'^([-*]|\d+\.)\s*', '', line).

**Evidence.** The list-item detector at line 74 uses `line.startswith(("- ", "* ", "1.", "2.", ..., "9."))`. Each numeric prefix is a two-character string like "1." that requires the second character to be a literal period. For a line such as "10. some finding", the second character is "0", not ".", so none of the single-digit prefixes match, and the "- "/"* " bullet prefixes do not match either. I confirmed this by execution: "10. baz", "11. qux", "12. ten" all return matched=False, while "1. foo" and "9. bar" return True. Because the loop only appends to `out` when the startswith check passes (lines 74-77), any finding numbered 10 or higher is silently skipped. This is a real, material correctness defect: a Critical/Important/Minor findings section that uses numbered list markers and reaches double digits will lose every finding from item 10 onward without error. The cited file, line (74), and claim all match the code. (The secondary marker-strip regex at line 75 also mishandles multi-digit numbers, but the central claim about dropping items 10+ holds regardless.)

**Citations.** C:/Users/charl/russellian-book-suite/skills/book-review/scripts/dispatch_review.py:74 (startswith tuple of "1."–"9." prefixes), :70-77 (loop only appends when startswith matches); execution test showing "10. baz"/"11. qux"/"12. ten" => matched=False vs "1. foo"/"9. bar" => True.


---

## `invariants-never-compiled` — HIGH

**Location:** `skills/book-thesis/scripts/compile_thesis.py:103` · **area:** datalog-consistency / thesis-model · **confidence:** high

**Finding.** Author-declared thesis invariants (e.g. bermuda's parish-count, bmd-peg, airport-location) are emitted only as inert :rule/:formal string literals and are never compiled into or loaded as Datalog rules, so the D11 invariant checks the schema promises (schema.yaml: '# Compiled to Datalog rules') never actually fire on the authored invariants.

**Fix.** Either parse each invariant's `formal:` clause and append it to the ruleset loaded by datalog_consistency.run (translating the documented `claims(P,subject,V)` head into the loader's claim_subject/claim_value facts), or drop the `formal:` field and the 'Compiled to Datalog rules' promise and document invariants as advisory only. As-is the central thesis-consistency feature is non-functional for real books.

**Evidence.** The claim holds against the code. In compile_thesis.py the `_add_invariant` function (lines 103-111) emits an invariant's `formal:` clause solely as an inert RDF string literal `NS["formal"]` (and `rule:` as `NS["rule"]`); nothing parses it. In datalog_consistency.py, `_assert_thesis_facts` (lines 93-105) reads only statement/SubArgument/supports/advancedBy/requiresEvidence triples and never touches `NS["formal"]` or `NS["rule"]`, and `pyDatalog.load` (line 173) loads only the static rules/consistency.dl. There is no code path that translates authored `formal:` clauses into rules or facts. The D11 invariant bucket is filled only by `declared_conflict` (ledger conflicts_with) and `unreachable_supports` (lines 186-190) — never by the authored invariants. Moreover the `formal:` clauses in bermuda.yaml (lines 97-122) use a `claims(P,subject,V)`/`contradicts(...)` vocabulary that does not even exist in the loader's TERMS/EXTENSIONAL predicate set (which uses claim_subject/claim_value), so they could not be loaded even if attempted. schema.yaml line 25 explicitly promises invariants are "Compiled to Datalog rules" — a promise the code does not keep. The bermuda parish-count/bmd-peg/airport-location invariants are real authored data that the D11 check can never fire on. This is a material, non-stylistic correctness gap in the central thesis-consistency feature.

**Citations.** skills/book-thesis/scripts/compile_thesis.py:103-111 (formal/rule emitted as inert literals); skills/book-thesis/scripts/datalog_consistency.py:93-105 (_assert_thesis_facts ignores formal/rule), :173 (loads only static consistency.dl), :186-193 (D11 fed only by declared_conflict + unreachable_supports), :28-46 (TERMS/EXTENSIONAL lack claims/contradicts predicates); skills/book-thesis/rules/consistency.dl:1-60 (static ruleset, no authored invariants); skills/book-thesis/thesis/schema.yaml:24-29 ("Compiled to Datalog rules" promise); skills/book-thesis/thesis/bermuda.yaml:97-122 (real parish-count/bmd-peg/airport-location invariants with formal clauses)


---

## `bermuda-fol-connectives-unnamed` — HIGH

**Location:** `verifiers/bermuda/cljs-orchestrator/src/main/bermuda/nl_to_fol.cljs:29` · **area:** NL→FOL translation soundness · **confidence:** high

**Finding.** bermuda's legacy-claim->formula builds every logical connective as an anonymous {:kind :symbol :sort :rule} with NO :name, so forall/implies/and/= are indistinguishable — the generated FOL loses all operator identity, unlike the adsc-clinical copy which names :forall/:implies/:and/:=.

**Fix.** Add :name :forall/:implies/:and/:= to each head map in bermuda's rewrite to match adsc-clinical; the two copies must agree on connective encoding for the verifier to interpret quantifier scope.

**Evidence.** In bermuda's legacy-claim->formula, all four connective heads are emitted as anonymous {:kind :symbol :sort :rule} maps with no :name key (nl_to_fol.cljs lines 29, 32, 34, 37). The outer quantifier, the implication, the conjunction, and the equality are therefore byte-identical as head maps and cannot be distinguished by operator identity — only by structural nesting position. The adsc-clinical copy of the same rewrite names every corresponding head: :name :forall (line 19), :name :implies (line 22), :name :and (line 24), :name := (line 27). The two copies are supposed to be the same translation but disagree on connective encoding; bermuda's version drops the semantic identity a verifier needs to interpret quantifier scope and the logical structure. This is a genuine NL→FOL soundness divergence, not stylistic, and the suggested fix (add :name :forall/:implies/:and/:= to each head) precisely reconciles bermuda with adsc-clinical. The cited line 29 is the outer (forall) head and is accurate. The claim does not depend on runtime behavior; the structural defect is visible statically.

**Citations.** verifiers/bermuda/cljs-orchestrator/src/main/bermuda/nl_to_fol.cljs:29,32,34,37 (heads {:kind :symbol :sort :rule} with no :name); contrast verifiers/adsc-clinical/cljs-orchestrator/src/main/adsc_clinical/nl_to_fol.cljs:19 (:name :forall), :22 (:name :implies), :24 (:name :and), :27 (:name :=)


---

## `bermuda-quantifier-binder-missing-var-name` — HIGH

**Location:** `verifiers/bermuda/cljs-orchestrator/src/main/bermuda/nl_to_fol.cljs:31` · **area:** NL→FOL quantifier scope · **confidence:** high

**Finding.** bermuda emits the forall-bound variable as {:kind :variable :sort :entity} with no :name, so the binder and the body's variable argument (also nameless) cannot be linked — the bound variable is effectively free / capturable, whereas adsc-clinical names both "?subj".

**Fix.** Give the bound variable and its body occurrences a shared :name (e.g. "?subj") so the quantifier actually binds the entity argument.

**Evidence.** The cited file's legacy-claim->formula meander rewrite emits the forall binder variable at line 30 as {:kind :variable :sort :entity} with NO :name, and the body's variable argument at line 43 is also {:kind :variable :sort :entity} with NO :name. Because neither carries a name, there is nothing tying the binder to the body occurrence, so the body variable is structurally unbound (free/capturable) relative to the quantifier. The claim is further corroborated by three sibling verifiers — osmotic_pressure, adsc-clinical, and epidemiology — which all emit {:kind :variable :name \"?subj\" :sort :entity} for BOTH the binder and the body occurrence, plus a named quantifier head {:kind :symbol :name :forall :sort :rule}. The bermuda file additionally omits :name :forall from the head at line 29, making the quantifier itself unnamed. This is a clear divergence from the established pattern, not a stylistic nitpick: a quantified formula whose bound variable cannot be matched to its body usage is semantically broken. The claim's only minor imprecision is that it cites \"line 31\" for the binder when the nameless binder is actually on line 30 (line 31 begins the nested body expression), but the substance is correct. The suggested fix (give both occurrences a shared :name like \"?subj\") matches exactly what the sibling implementations do.

**Citations.** C:/Users/charl/russellian-book-suite/verifiers/bermuda/cljs-orchestrator/src/main/bermuda/nl_to_fol.cljs:29 (head {:kind :symbol :sort :rule}, no :name), :30 (binder {:kind :variable :sort :entity}, no :name), :43 (body occurrence {:kind :variable :sort :entity}, no :name); contrast verifiers/adsc-clinical/cljs-orchestrator/src/main/adsc_clinical/nl_to_fol.cljs:19-20 and :30 (head :name :forall, binder and body both :name "?subj"); same pattern in verifiers/osmotic_pressure/.../nl_to_fol.cljs:19-20,:30 and verifiers/epidemiology/.../nl_to_fol.cljs:19-20,:30


---

## `holdout-validation-not-wired` — HIGH

**Location:** `skills/neurosym-forge/scripts/_induction_orchestrator.py:219` · **area:** induced-theory acceptance · **confidence:** high

**Finding.** `validate_with_holdout` (the memorization-vs-induction defense) is defined and unit-tested but is never called from `run()` or any production path, so induced candidates are accepted as `survivors` and persisted without any held-out validation — induced theories are not validated before acceptance.

**Fix.** Call holdout validation inside `run()` against the document folds before persisting survivors, routing failures into the rejected list with reason `:memorization`; add an integration test that a memorizing candidate is rejected end-to-end.

**Evidence.** The claim is accurate and material. `validate_with_holdout` is defined at _induction_orchestrator.py:290 and returns a `:memorization` rejection (lines 315-318) when any held-out fold's sat-rate falls below threshold. However, the production entry point `run()` (lines 219-266) executes load atoms -> horn_mine/popper_search/llm_propose -> `dedup_with_rejection_log` into survivors/rejected (line 253) -> `rank_by_semantic_coherence` (line 257) -> `_persist_queue` (line 259) -> `_persist_budget`. There is no holdout step anywhere in this path; survivors are persisted without any held-out validation. A repo-wide grep for `validate_with_holdout` finds only the definition (orchestrator line 290) and the test file test_failure_modes.py (lines 389-392), which calls the function directly rather than through `run()`. No other production script references it (confirmed by grepping survivors/accept/persist/validate/holdout across scripts/). The design doc (tier6-failure-mode-tests/design.md:146-149) explicitly states the orchestrator is supposed to run candidates across folds and reject memorizers with `:memorization`, so this is a genuine wiring gap between the unit-tested defense and the production acceptance path, not an intended separation. Severity is high: the memorization-vs-induction defense is effectively dead code in production, and induced theories are accepted/persisted with no held-out validation.

**Citations.** skills/neurosym-forge/scripts/_induction_orchestrator.py:219-266 (run() production path: dedup->rank->persist, no holdout call); :290-319 (validate_with_holdout definition, unused); skills/neurosym-forge/tests/test_failure_modes.py:389-400 (only caller, invokes directly not via run()); openspec/changes/tier6-failure-mode-tests/design.md:146-149 (intended design: orchestrator runs folds and rejects with :memorization); repo-wide grep of validate_with_holdout returns only the definition and the test, confirming no production caller.


---

## `holdout-ignores-candidate` — HIGH

**Location:** `skills/neurosym-forge/scripts/_induction_orchestrator.py:290` · **area:** holdout validator generality · **confidence:** high

**Finding.** `validate_with_holdout` ignores its `candidate` argument entirely and hard-codes the predicate `doc.get('r0',0) >= 0`, so it validates a fixed predicate rather than the induced rule; the trivial-tautology candidate or any non-r0 rule would pass/fail identically regardless of its actual assert body.

**Fix.** Parse the candidate's `:assert` form and evaluate it per document rather than hard-coding the r0 predicate; until then, do not present this function as a general memorization gate.

**Evidence.** The factual core of the claim is verified directly in the code. `validate_with_holdout(candidate, folds, threshold)` (line 290) never references its `candidate` parameter anywhere in the body; the sat-rate is computed exclusively from the hard-coded predicate `doc.get("r0", 0) >= 0` (line 312). Therefore the candidate's actual `:assert` body is irrelevant: the trivial-tautology candidate, a non-r0 rule, or the memorized candidate all produce identical pass/fail results for a given set of folds. This is the precise behavior the claim describes, and it is materially real (the function cannot validate the induced rule it is handed). I mark it confirmed rather than uncertain because the defect is fully observable statically and does not depend on runtime behavior. One caveat tempering severity: the function's own docstring (lines 302-306) explicitly discloses the hard-coding ("The `r0`-based predicate is hard-coded to match the memorization fixture... Future generalisation... is a Phase-V follow-up"), and the design doc (REQ-TEST-043) frames it as a fixture-scoped regression-test scaffold, with a matching hardcoded stub in test_failure_modes.py (lines 236-258). So the claim's framing that it is "presented as a general memorization gate" is somewhat overstated — the code already disclaims generality. The underlying correctness issue (cannot evaluate the candidate) is nonetheless genuine, so the claim is confirmed, with the note that the suggested fix's premise about misrepresentation is already partially self-addressed by the existing docstring.

**Citations.** C:/Users/charl/russellian-book-suite/skills/neurosym-forge/scripts/_induction_orchestrator.py:290-319 (esp. line 312 hard-coded `doc.get("r0", 0) >= 0`; lines 302-306 docstring disclaiming generality); C:/Users/charl/russellian-book-suite/skills/neurosym-forge/tests/test_failure_modes.py:236-258 (matching hardcoded stub) and 373-399 (REQ-TEST-043 usage); C:/Users/charl/russellian-book-suite/openspec/changes/tier6-failure-mode-tests/design.md:124-149


---

## `phase-v-import-always-fails` — HIGH

**Location:** `skills/neurosym-forge/scripts/_induction_sources.py:73` · **area:** induction LLM proposer wiring · **confidence:** high

**Finding.** The Phase V conditional import targets `propose_candidate`, a symbol that does not exist anywhere in `_induction_proposer.py` (which exports `propose_constraint`/`propose_repair`), so `PHASE_V_AVAILABLE` is permanently False and the real LLM proposer can never activate; even if renamed, the call `_phase_v_propose(schema=schema, cluster=cluster)` passes `cluster=` while `propose_constraint` expects `atom_cluster=`.

**Fix.** Import the symbol that actually exists (`propose_constraint`) and adapt the call site to its real signature (`atom_cluster=cluster`, returning a raw EDN string that must then be wrapped into the candidate dict), or add the `propose_candidate` adapter the import expects; add a test that asserts `PHASE_V_AVAILABLE` is True when the proposer module is present.

**Evidence.** Both parts of the claim hold against the actual code. (1) `_induction_sources.py:73` does `from scripts._induction_proposer import propose_candidate as _phase_v_propose`, but `_induction_proposer.py` defines only `propose_constraint` (line 168) and `propose_repair` (line 227); a repo-wide grep shows `propose_candidate` exists nowhere as a definition — only in this import, a docstring (line 384), and a planning doc. Because the import is wrapped in `try/except Exception` (lines 72-78), it always raises ImportError, so `PHASE_V_AVAILABLE` is permanently False and `llm_propose` (lines 394-400) always takes the stub fallback branch — the real proposer can never activate. (2) Even if the name were corrected to `propose_constraint`, the call site at line 396 `_phase_v_propose(schema=schema, cluster=cluster)` is doubly wrong: `propose_constraint` is keyword-only and expects `atom_cluster=` (line 171), not `cluster=`, so it would raise TypeError (caught by the inner except at 397, falling back to the stub again); and `propose_constraint` returns a raw EDN string (line 224), whereas the call site treats the result as a candidate dict and returns it directly into the candidate list (lines 403-406), so a string would silently corrupt the candidate shape documented at the top of the file. This is a material correctness/wiring defect, not a stylistic nitpick: the Phase V LLM proposer is unreachable, and the failure is masked by broad exception handling. The only mild caveat is the `# pragma: no cover - imported when Phase V lands` comment, which frames the dead import as deliberately forward-looking, but the symbol name still does not match what the module already exports, so the wiring is incorrect today.

**Citations.** skills/neurosym-forge/scripts/_induction_sources.py:70-78 (PHASE_V_AVAILABLE init + try/except import of propose_candidate); :394-406 (llm_propose dispatch, call `_phase_v_propose(schema=schema, cluster=cluster)`, treats result as candidate dict); :384 (docstring naming propose_candidate). skills/neurosym-forge/scripts/_induction_proposer.py:168-173 (propose_constraint signature with keyword-only atom_cluster), :224 (returns raw EDN string), :227 (propose_repair) — no propose_candidate defined. Repo grep for `propose_candidate` returns only the import, the docstring, and docs/plans/2026-05-19-tier6-theory-induction.md.


---

## `generators-emit-unsupported-ops` — HIGH · needs runtime verification

**Location:** `skills/neurosym-forge/scripts/_induction_sources.py:202` · **area:** candidate generators vs grammar set · **confidence:** high

**Finding.** Horn-body candidates emit `(implies ...)` and the Stub LLM proposer emits `(positive ...)`, but neither `implies` nor `positive` is in `SUPPORTED-OPERATORS` (the set has `=>`, not `implies`, and no `positive`); if the grammar gate were ever wired in, every Horn-mined and every Stub candidate would be rejected as `:grammar-fail/illegal-op`.

**Fix.** Emit `=>` instead of `implies` and replace `(positive (:p ?d))` with a supported form such as `(> (:p ?d) 0)`; add a test that runs each generator's output through the grammar gate and asserts conformance.

**Evidence.** Every load-bearing fact in the claim checks out against the actual code. (1) The Horn-body generator emits `(implies (:p1 ?d) (:p2 ?d))` — `_induction_sources.py:202` (Python) and `induce_theory.cljs:137` (CLJS mirror). (2) The Stub LLM proposer emits `(positive (:pred ?d))` — `_induction_sources.py:358` and `induce_theory.cljs:211`. (3) The grammar gate's `SUPPORTED-OPERATORS` set (`_induction_grammar.cljs:37-48`) contains `=>` but neither `implies` nor `positive`; the same three-way-mirrored set in `_induction_proposer.py:49-56` and `codegen_axioms.py:69-76` (`_SUPPORTED_ASSERT_HEADS`) likewise has `=>` and omits both. (4) The gate `grammar-conforming?` (`_induction_grammar.cljs:112-171`) computes `(cset/difference used-ops SUPPORTED-OPERATORS)` and returns `:grammar-fail/illegal-op` for any op outside the set, so `implies` and `positive` would each be rejected. The claim is also self-aware that the gate is not yet wired in ("if the grammar gate were ever wired in"): the orchestrator `-main` (`induce_theory.cljs:364-386`) generates, dedups, and persists candidates without ever calling `grammar-conforming?`; the absent-grammar branch merely tags LLM candidates `:grammar-unvalidated` (line 218). This is material, not stylistic: the codegen backend independently confirms the intended implication head is `=>` (`codegen_axioms.py:1268`, compiling to `.implies(...)`), so `implies`/`positive` are genuinely wrong, not synonyms; and `codegen_axioms.py:713` would also raise CodegenError on `implies`. No test runs generated candidates through the gate — the candidate-generation tests only use `implies` in dedup fixtures (test_candidate_generation.py:297-363), never validating it — so the gap is uncaught. The only nuance is that today the rejection is latent (gate unwired), but the generators are demonstrably emitting operators that the project's own canonical operator set and codegen both reject.

**Citations.** skills/neurosym-forge/scripts/_induction_sources.py:202 (Horn emits `implies`), :358 (Stub emits `positive`); skills/neurosym-forge/scripts/induce_theory.cljs:137,211 (CLJS mirror), :364-386 (gate not wired into -main), :218 (grammar-unvalidated tag); skills/neurosym-forge/scripts/_induction_grammar.cljs:37-48 (SUPPORTED-OPERATORS has `=>`, no `implies`/`positive`), :156-162 (illegal-op via set difference); skills/neurosym-forge/scripts/codegen_axioms.py:69-76 (_SUPPORTED_ASSERT_HEADS), :713-716 (CodegenError on unknown head), :1268-1271 (`=>` is the implication head); skills/neurosym-forge/scripts/_induction_proposer.py:49-56 (BNF mirror); skills/neurosym-forge/tests/test_candidate_generation.py:297-363 (no grammar-gate check on generated output)


---

## `grammar-gate-never-invoked` — HIGH

**Location:** `skills/neurosym-forge/scripts/induce_theory.cljs:364` · **area:** theory-induction validation pipeline · **confidence:** high

**Finding.** The grammar enforcer `_induction_grammar.cljs` (whose docstring claims it is "the FIRST gate before any solver invocation; rejected proposals never reach Z3") is never required or called by either the cljs orchestrator (`-main`) or the Python orchestrator (`run`); `phase-v-grammar-available?` only toggles a `:grammar-unvalidated` origin tag, so candidates are persisted to candidates.edn with zero grammar validation.

**Fix.** Wire `grammar-conforming?`/`grammar-conforming-json` into the orchestrator so every generated candidate is gated before persistence, rejecting non-conforming forms into the rejection log with the grammar-fail tag rather than tagging them and accepting them.

**Evidence.** The grammar enforcer's docstring promises it is "the FIRST gate before any solver invocation; rejected proposals never reach Z3" and exports grammar-conforming? / grammar-conforming-json. But neither orchestrator wires it in. In induce_theory.cljs, -main (lines 364-386) never requires _induction-grammar and never calls grammar-conforming?; the file-existence probe phase-v-grammar-available? (225-231) feeds only stub-propose (218), which uses it merely to toggle the :grammar-unvalidated origin tag. Candidates pass from dedup-with-rejection-log straight into persist-queue (381) with no conformance check. The Python orchestrator run (219-266) imports only _induction_sources, _edn_reader, _io, calls no grammar function, and _induction_sources.py has zero grammar references (grep: no matches). Thus candidates are persisted to candidates.edn with no grammar validation; the only real callers of grammar-conforming-json are the tests. The claim is accurate and the gap is material: the advertised hard gate is effectively dead code, so non-EDN / wrong-head / illegal-op / unknown-predicate forms are tagged-and-accepted rather than rejected. Static evidence is sufficient; no runtime needed.

**Citations.** skills/neurosym-forge/scripts/_induction_grammar.cljs:6-10 (docstring "FIRST gate ... never reach Z3"), :26-29,:112,:201 (public grammar-conforming? / grammar-conforming-json); skills/neurosym-forge/scripts/induce_theory.cljs:218 (only use: origin tag), :225-231 (phase-v-grammar-available? is a mere file-existence probe), :364-386 (-main: no require/no call of grammar), :381 (persist-queue with no gate); skills/neurosym-forge/scripts/_induction_orchestrator.py:33-35 (imports, no grammar), :219-266 (run: no grammar call, dedup->persist); _induction_sources.py grep for grammar => no matches


---

## `tautology-circular-only-in-test-stubs` — HIGH

**Location:** `skills/neurosym-forge/tests/test_failure_modes.py:312` · **area:** failure-mode gates · **confidence:** high

**Finding.** The trivial-tautology gate (REQ-TEST-041) and circular-definition gate (REQ-TEST-042) exist only as test-local stubs (`_stub_validate`, `_stub_grammar_conforming`); `scripts._induction_validator` and `scripts._induction_grammar` (Python) do not exist, and the production `_induction_grammar.cljs` has no `:grammar-fail/circular-definition` tag, so these tests are green while asserting nothing about the real framework.

**Fix.** Implement the tautology pre-check and circular-definition AST check in production code (a real `_induction_validator` and a circular-definition branch in the grammar enforcer) and bind the tests to them; until then the tests give false assurance.

**Evidence.** Every concrete assertion in the claim checks out against the code. (1) The REQ-TEST-041 test (test_failure_modes.py:312-334) and REQ-TEST-042 test (:342-365) both branch on `_has_module("scripts._induction_validator")` / `_has_module("scripts._induction_grammar")`; when absent they fall through to `_stub_validate` (:151) and `_stub_grammar_conforming` (:187), which are test-local functions defined in the same file. (2) `scripts/_induction_validator` (Python) does not exist — Glob of `_induction_*` returns only `_induction_grammar.cljs`, `_induction_orchestrator.py`, `_induction_proposer.py`, `_induction_sources.py`; and a Grep for `def validate`/`circular`/`tautology`/`grammar_conforming` across all `.py` scripts finds no validator and no Python `_induction_grammar`. So both `_has_module` guards are False and the stub path is the only path that ever runs. (3) The production `_induction_grammar.cljs` enumerates exactly five grammar-fail tags (non-edn, wrong-head, unknown-predicate, wrong-sort, illegal-op; lines 15-22) and has no `:grammar-fail/circular-definition` and no tautology check (confirmed by Grep). The stubs themselves implement the tautology pre-check (`_is_trivial_tautology`, :101) and circular-definition AST walk (`_contains_term`, :211) and hardcode the asserted reason strings `:trivial-tautology` (:160) and `:grammar-fail/circular-definition` (:206). Therefore the two tests assert against behavior that exists only in the test file, not the framework, and they ship green while validating nothing about production — a real, material false-assurance gap, not a stylistic nitpick. The severity-high / correctness framing is accurate. The only nuance: the stubs do contain genuine logic mirroring the intended checks, so the tests are not pure no-ops, but they still exercise test-owned code rather than the production gates, which is exactly what the claim states.

**Citations.** skills/neurosym-forge/tests/test_failure_modes.py:326-334 (REQ-TEST-041 stub fallback), :357-365 (REQ-TEST-042 stub fallback), :101-161 (_is_trivial_tautology + _stub_validate hardcoding ":trivial-tautology"), :187-208 (_stub_grammar_conforming hardcoding ":grammar-fail/circular-definition"), :51-60 (_has_module); skills/neurosym-forge/scripts/_induction_grammar.cljs:15-22 (five grammar-fail tags, no circular-definition); Glob skills/neurosym-forge/scripts/_induction_* (no _induction_validator.py, no _induction_grammar.py); Grep of *.py scripts for circular/tautology/grammar_conforming/def validate (none in production).


---

## `missing-gating-report-false-pass` — HIGH

**Location:** `skills/review-conductor/scripts/aggregate_panel.py:45` · **area:** verdict aggregation · **confidence:** high

**Finding.** Aggregation only iterates review .md files that actually exist and continues past parse errors, so a configured gating persona whose subagent crashed or never wrote a report contributes zero criticals and the panel returns 'pass' despite an incomplete review.

**Fix.** After the loop, assert every persona in panel.personas (or at least every gating persona) produced a parseable report; if any are missing or failed to parse, fail closed (e.g. raise, or emit a 'soft-gate-fail'/'hard-gate-fail' verdict) rather than silently scoring it as zero criticals.

**Evidence.** The claim holds against the actual code. In aggregate_panel.py the loop at line 45 iterates only over existing reviews/*.md files (reviews_dir.glob("*.md")) and on a parse failure executes `continue` (lines 46-49), so a configured gating persona whose subagent crashed (no file written) or wrote a malformed report contributes nothing. persona_gates is built from panel.personas (line 37) but is used only as a lookup for personas that DID report (.get(r.persona_id, "advisory"), line 54); there is no reverse check that every gating persona produced a parseable report. With gating_criticals left at 0, the default soft_gate_rule "any_critical_from_gating" returns "pass" (lines 68-69). The majority_critical rule is even more clearly broken: it divides by len(panel.personas) (full configured count, line 73) while counting only personas that reported, biasing toward pass when reports are missing. The upstream aggregate_reviews (called at line 35) has the identical pattern: returns [] if the reviews dir is missing (book-review/scripts/aggregate_reviews.py:24-25) and continues past parse errors (lines 27-31), so it provides no fail-closed guard either. conductor.run_panel dispatches one packet per persona then calls run_aggregation with no completeness verification in between. The issue is real, high-severity (a gating review silently dropping out yields a false "pass"), statically determinable, and the suggested fix (assert every gating persona produced a parseable report or fail closed) is correct.

**Citations.** skills/review-conductor/scripts/aggregate_panel.py:37 (persona_gates built but never reverse-checked), :45-49 (glob existing .md only; continue on ValueError/KeyError), :54-58 (gate lookup only for personas that reported), :68-77 (soft_gate_rule -> "pass" when gating_criticals==0; majority_critical divides by len(panel.personas)); skills/review-conductor/scripts/conductor.py:26-30 (dispatch then aggregate, no completeness check); skills/book-review/scripts/aggregate_reviews.py:24-32 (returns [] for missing dir, continue on parse error)


---

## `persona-id-mismatch-downgrades-gate` — HIGH

**Location:** `skills/review-conductor/scripts/aggregate_panel.py:54` · **area:** severity gating · **confidence:** high

**Finding.** persona_gates.get(r.persona_id, "advisory") silently defaults to 'advisory' when a report's frontmatter persona id does not match any panel persona, so a typo or stale persona id downgrades a gating persona and its criticals never gate.

**Fix.** Treat an unrecognized persona_id (including the empty-string default returned by parse_review_report when the 'persona' frontmatter key is absent) as an error or count its criticals as gating; do not silently default to advisory.

**Evidence.** At aggregate_panel.py:54 the code does `gate = persona_gates.get(r.persona_id, "advisory")`, where `persona_gates` (line 37) is keyed only by the panel's configured persona ids. `r.persona_id` comes from `parse_review_report` (dispatch_review.py:99), which returns `meta.get("persona", "")` — so a report whose frontmatter lacks the `persona` key yields an empty string, and a typo or stale id yields a non-matching string. In either case the `.get(..., "advisory")` default silently classifies the report as advisory. Materiality is real: under the default soft-gate rule `any_critical_from_gating` (lines 67-69) only `gating_criticals` triggers `soft-gate-fail`; criticals from a downgraded persona land in `advisory_criticals` (line 58) and never gate. parse_review_report only raises on missing frontmatter (lines 84-85), never on an unrecognized or empty persona id, so the downgrade is completely silent. This is a correctness bug in severity gating, not a stylistic nitpick. The suggested fix (treat unrecognized/empty persona_id as an error or as gating) is appropriate.

**Citations.** C:/Users/charl/russellian-book-suite/skills/review-conductor/scripts/aggregate_panel.py:37,54,55-58,67-69; C:/Users/charl/russellian-book-suite/skills/book-review/scripts/dispatch_review.py:84-85,99


---

## `adsc-var-name-no-question-strip` — HIGH

**Location:** `verifiers/adsc-clinical/rust-verifier/src/smt.rs:70` · **area:** var-naming divergence (adsc-clinical) · **confidence:** high

**Finding.** adsc-clinical builds var names inline with trim_start_matches(':') only, omitting the ? strip that canonical_var_name (and the cross-language golden vectors) require; any ?-prefixed predicate/subject yields a var name that will not match the codegen-emitted axiom constant, producing a silent false-sat (the binding and the axiom never refer to the same Z3 symbol).

**Fix.** Add var_name.rs to adsc-clinical and call canonical_var_name, identical to bermuda; do not hand-roll the format in smt.rs.

**Evidence.** adsc-clinical/rust-verifier/src/smt.rs:70-74 builds the Z3 var name inline as format!("{}_{}", predicate.trim_start_matches(':'), subject.trim_start_matches(':')) — stripping only ':', not '?'. The cross-language canonical algorithm strips BOTH ':' and '?': Rust bermuda/src/var_name.rs:10-11 uses trim_start_matches(|c| c==':'||c=='?'); Python _canonical.py:28-29 uses lstrip(":?"); the golden vectors at neurosym-forge/tests/golden/canonical_var_name.edn rows 6 and 9 mandate "?osmotic-pressure-pa"/"?s" -> "osmotic-pressure-pa_s" and "?p"/"?s" -> "p_s". The materiality is real: codegen_axioms.py imports and calls canonical_var_name (line 31, 848, 1366) to emit the axiom-side Z3 constant names, so for any '?'-prefixed predicate/subject the generated axiom references e.g. const "p_s" while adsc-clinical's runtime binding creates const "?p_?s" — two distinct Z3 symbols. The binding never constrains the symbol the axiom uses, yielding an unconstrained (trivially satisfiable) formula: a silent false-sat. Bermuda avoids this by calling canonical_var_name (bermuda/src/smt.rs:345). adsc-clinical has no var_name.rs (Glob found only bermuda's), confirming it hand-rolls the format. The only static caveat is whether adsc-clinical inputs ever carry '?' prefixes; the golden vectors and the migration comment at smt.rs:51 (Keyword canonical, Str accepted) show '?'-prefixed string forms are a supported/expected representation, so the divergence is a genuine correctness defect, not a stylistic nitpick. Suggested fix (add var_name.rs + call canonical_var_name) is correct.

**Citations.** verifiers/adsc-clinical/rust-verifier/src/smt.rs:70-74 (inline format, only strips ':'); verifiers/bermuda/rust-verifier/src/var_name.rs:9-13 (canonical strips ':' and '?'); verifiers/bermuda/rust-verifier/src/smt.rs:345 (bermuda calls canonical_var_name); skills/neurosym-forge/scripts/_canonical.py:28-29 (lstrip(":?")); skills/neurosym-forge/scripts/codegen_axioms.py:31,848,1366 (axiom constants emitted via canonical_var_name); skills/neurosym-forge/tests/golden/canonical_var_name.edn:6,9 (?-stripping required); no var_name.rs under verifiers/adsc-clinical (Glob)


---

## `eqsat-saturate-panic-across-ffi` — HIGH

**Location:** `verifiers/bermuda/rust-verifier/src/eqsat.rs:59` · **area:** eqsat · **confidence:** high

**Finding.** canonicalize calls input.parse().expect("parse RecExpr"), so malformed input panics; saturate() (exposed to JS via napi) feeds unvalidated EDN straight into canonicalize, turning a bad input into a panic across the FFI boundary instead of a recoverable Result::Err.

**Fix.** Change canonicalize to return Result<RecExpr<BookLogic>, String> (propagate the parse error) and have saturate map the error into its Result return value, matching prove_equiv's non-panicking parse handling.

**Evidence.** The claim is accurate. At eqsat.rs:58-59, canonicalize(input, budget) does `let expr: RecExpr<BookLogic> = input.parse().expect("parse RecExpr");` which panics on any unparseable input. saturate (eqsat.rs:108-112) declares a Result<String, String> return type but calls canonicalize(terms_edn, ...) directly with no validation, so a malformed terms_edn panics rather than returning Err. That panic crosses the napi FFI boundary: lib.rs:83-85 exposes saturate as a #[napi] function returning napi::Result<String> via `eqsat::saturate(...).map_err(...)`. A panic inside canonicalize unwinds through this napi wrapper rather than being converted to a JS-catchable error/rejected promise (napi-rs catches panics as a process-level abort/uncaught exception, not the structured Result the signature promises). The contrast the finding draws is real and material: prove_equiv (eqsat.rs:81-89) handles the identical parse with `match lhs.parse() { Ok(e) => e, Err(_) => return ProofResult::NotProved }`, i.e. it never panics on bad input. So the same crate has both a panicking and a non-panicking parse path, and the panicking one is the one wired to JS. The suggested fix (make canonicalize return Result and have saturate propagate via its existing Result return) is correct and matches the established non-panicking pattern. This is a genuine correctness/robustness defect, not a stylistic nitpick: untrusted EDN input from JS can crash the Rust addon. Severity high is defensible given an FFI boundary and unvalidated external input. Only minor caveat: the comment at saturate notes EDN-to-s-expression translation is deferred, so in practice non-s-expression EDN would frequently fail to parse and panic, making the bug easy to trigger, which strengthens rather than weakens the finding.

**Citations.** verifiers/bermuda/rust-verifier/src/eqsat.rs:59 (input.parse().expect("parse RecExpr")); eqsat.rs:108-112 (saturate returns Result<String,String> but calls canonicalize unchecked); eqsat.rs:82-89 (prove_equiv's non-panicking match-based parse for contrast); verifiers/bermuda/rust-verifier/src/lib.rs:83-85 (#[napi] pub fn saturate exposing it to JS via napi::Result)


---

## `smt-int-bound-to-real-sort` — HIGH · needs runtime verification

**Location:** `verifiers/bermuda/rust-verifier/src/smt.rs:362` · **area:** smt / Z3 encoding soundness · **confidence:** high

**Finding.** bind_atoms always binds Edn::Int/Edn::UInt as a Z3 Int const, but predicate_is_real exists to flag predicates the codegen declared as Real; an integer value bound to a Real-typed predicate (e.g. land-area-km2_Bermuda) creates an Int const with the same name as the axiom's Real const, which Z3 treats as a distinct/ill-sorted symbol — an unsound or erroring encoding.

**Fix.** In bind_atoms, call crate::axioms::predicate_is_real(var_name) for Int/UInt values and bind as Real::new_const / Real::from_real(n,1) when true, mirroring the axiom sort; otherwise the value binding and the axiom reference will not share a Z3 sort.

**Evidence.** The claim is accurate and material. In bind_atoms (smt.rs:362-377), both Edn::Int and Edn::UInt arms unconditionally call Int::new_const(var_name) with no consultation of predicate_is_real. predicate_is_real exists in axioms.rs:196-202 and returns true for exactly land-area-km2_Bermuda and gdp-usd-billion_Bermuda, the two predicates whose axioms are declared as Real::new_const (axioms.rs:71, 78). The function's own doc comment (axioms.rs:189-194) states "smt.rs uses this to keep value-bindings in the same Z3 sort as the axioms reference," yet it is marked #[allow(dead_code)] and never referenced anywhere in smt.rs (the only sort guard there, check_value_sort_compat at smt.rs:355, checks predicate_is_vector, not real). So when an integer-valued atom binds a Real-typed predicate, smt.rs creates an Int-sorted const named land-area-km2_Bermuda while the axiom creates a Real-sorted const of the same name. In Z3 a symbol's identity includes its sort, so these are distinct symbols — the value binding and the axiom never interact, silently dropping the constraint (unsound), or the typed z3.rs API rejects the cross-sort equality (erroring). This is a genuine encoding-soundness defect, not a stylistic nit. The precise runtime manifestation (silent vs. error) is the only part requiring runtime confirmation, but the sort mismatch is statically certain, and the suggested fix (branch on predicate_is_real to bind as Real::from_real(n,1)) is exactly right.

**Citations.** verifiers/bermuda/rust-verifier/src/smt.rs:362-377 (Int/UInt arms unconditionally use Int::new_const); smt.rs:355-360 (only sort guard is predicate_is_vector); axioms.rs:196-202 (predicate_is_real returns true for land-area-km2_Bermuda, gdp-usd-billion_Bermuda); axioms.rs:71,78 (those predicates' axioms use Real::new_const); axioms.rs:189-195 (doc comment says smt.rs should use predicate_is_real to align sorts; marked #[allow(dead_code)], grep shows zero callers in smt.rs)


---

## `smt-float-truncation-saturation` — HIGH

**Location:** `verifiers/bermuda/rust-verifier/src/smt.rs:381` · **area:** smt / Z3 encoding soundness · **confidence:** high

**Finding.** Double values are encoded as Real::from_rational((v*1_000_000.0) as i64, 1_000_000), which silently truncates beyond 6 decimal places and saturates to i64::MAX for large magnitudes, so a genuinely-equal value can be encoded as unequal (false unsat) or a genuinely-distinct value can collide (false sat).

**Fix.** Encode the double exactly via the IEEE mantissa/exponent or parse the original EDN decimal text into an exact rational; at minimum reject/raise on overflow instead of letting `as i64` saturate, and document the fixed 1e6 scale as a soundness limitation.

**Evidence.** The cited code at smt.rs:378-382 encodes EDN Double atom values into Z3 exactly as claimed: `let v = value.to_float().unwrap_or(0.0); let numerator = (v * 1_000_000.0) as i64; z3_var.eq(&Real::from_rational(numerator, 1_000_000))`. Rust's `f64 as i64` cast is saturating (since Rust 1.45) and truncates toward zero, so both failure modes are real. (a) Truncation: any precision beyond ~6 decimal places is silently discarded, so two genuinely-distinct doubles (e.g. 0.0000003 vs 0.0000004) both map to numerator 0 and collide -> false sat / spurious equality. (b) Saturation: for |v| >= ~9.2e12 the product exceeds i64::MAX and saturates to i64::MAX, so distinct large doubles collide and a value that should equal a large constant can encode to a different rational than that constant produces, giving false unsat or false sat. There is no upstream clamp, overflow guard, or exact-rational path for doubles (the only other Double reference, line 53, is a debug-format string, not the assertion). Notably the integer branch (lines 372-374) DOES guard overflow via try_into + Error, making the Double path an inconsistent and unsound gap. This is a genuine SMT-encoding soundness defect in a verifier, not a stylistic nitpick; the file/line and described behavior match exactly. It is statically determinable from the cast semantics, so no runtime verification is needed.

**Citations.** C:/Users/charl/russellian-book-suite/verifiers/bermuda/rust-verifier/src/smt.rs:378-382 (Double encoding: `(v * 1_000_000.0) as i64` + `Real::from_rational(numerator, 1_000_000)`); contrast with smt.rs:371-377 (UInt branch guards overflow via try_into -> Error); smt.rs:379 (`to_float().unwrap_or(0.0)` lossy fallback); smt.rs:53 (only other Double use is debug format string, not assertion). Grep confirmed no clamp/overflow/saturation guard exists in verifiers/bermuda/rust-verifier/src for the Double path.


---

## `cli-llm-unwired-stub` — HIGH

**Location:** `tools/build-russell-corpus/scripts/cli.py:121` · **area:** build-russell-corpus CLI · **confidence:** high

**Finding.** main() calls args.func(args) with one argument, but cmd_extract/cmd_cross_check have an llm_call parameter that main never supplies, so those two subcommands always fall back to _stub_llm and abort with SystemExit('No LLM caller wired').

**Fix.** Wire a real caller in main() (e.g. import scripts.live_llm and pass extract_llm/cross_check_llm), or have cmd_extract/cmd_cross_check default to live_llm.extract_llm/cross_check_llm instead of _stub_llm. As written the extract and cross-check stages cannot be run from the CLI at all.

**Evidence.** The claim is accurate and material. In cli.py, main() (line 121-122) calls args.func(args) with only the single args argument. cmd_extract (line 23) and cmd_cross_check (line 50) declare a second parameter llm_call: Callable[[str], str] = _stub_llm, which main() never supplies, so both subcommands receive the _stub_llm default. _stub_llm (line 14-15) unconditionally raises SystemExit("No LLM caller wired..."). Therefore the extract and cross-check subcommands abort on every CLI invocation before doing any work, while the other subcommands (derive-vocabulary, sentinel, audit, append) take no llm_call and run fine. The suggested fix is real and correct: scripts/live_llm.py already exposes extract_llm and cross_check_llm (lines 45 and 52) as the Callable[[str], str] production wrappers, documented as the ones "Production code uses," but main() never imports or passes them. No alternate production entry point wires them either — the e2e test (test_e2e.py) calls the stage functions directly with stub callers, bypassing main(), and the plan doc only describes creating live_llm.py without ever updating the CLI dispatch. This is a genuine high-severity correctness gap, not a stylistic nitpick.

**Citations.** tools/build-russell-corpus/scripts/cli.py:14-15 (_stub_llm raises SystemExit), :23 (cmd_extract llm_call default _stub_llm), :33, :50 (cmd_cross_check llm_call default _stub_llm), :57, :89 and :106 (set_defaults func=cmd_extract/cmd_cross_check), :121-122 (args = parser.parse_args(); args.func(args) — single arg); tools/build-russell-corpus/scripts/live_llm.py:45 (extract_llm), :52 (cross_check_llm), :1-3 (docstring: "Production code uses these"); tools/build-russell-corpus/tests/test_e2e.py:65,85 (stubs passed directly to stage fns, not via main); docs/plans/2026-05-21-russell-corpus-expansion.md:2436 (same one-arg dispatch), :2610-2612 (live_llm wrapper step, no CLI wiring)


---

## `sentinel-cross-index-dedup-broken` — HIGH

**Location:** `tools/build-russell-corpus/scripts/sentinel.py:77` · **area:** build-russell-corpus sentinel · **confidence:** high

**Finding.** Check 4 builds existing_locators from content_locator(e.get('content_locator') or e.get('rhetorical_move','')) but the new-candidate key is content_locator(paragraph_text) (first 120 chars of the full paragraph); the stored content_locator is the extractor's short free-form snippet (e.g. 'Philosophy, throughout its history,'), so the two keys never match and a paragraph already in the committed index is never deduped.

**Fix.** Persist the canonical dedup key (content_locator(paragraph_text)) in the index entry and compare against the same canonical key, or store paragraph_text in the index and compute content_locator(e['paragraph_text']). Add a test that seeds an entry with a known paragraph and asserts a re-extracted identical paragraph is rejected as duplicate.

**Evidence.** Check 4 (sentinel.py:77-81) builds existing_locators as content_locator(e.get("content_locator") or e.get("rhetorical_move","")) but the new-candidate key (line 80) is content_locator(candidate["paragraph_text"]). content_locator (corpus_io.py:60-65) returns the first 120 stripped chars of its input. The candidate key is therefore the first 120 chars of the FULL paragraph. The stored index key is something entirely different: (a) in the real committed schema, append_to_index.py:30 persists cand["content_locator"], which is the extractor's short free-form snippet ("first 120 chars" per the prompt but in every fixture it is a short phrase like "Philosophy, throughout its history,", 35 chars); content_locator() of that short string returns it unchanged (35 chars), which does NOT equal the candidate's 120-char key. (b) Worse, the actual existing_index_sample.json entries have no content_locator field at all, so the key falls back to content_locator(rhetorical_move) e.g. "philosophy compared against other studies" — never matching any paragraph prefix. Either way the two key spaces never intersect, so a paragraph already in the committed index is never recognized as a duplicate. The batch path (line 146) correctly keys on content_locator(cand["paragraph_text"]), so intra-batch dedup works; only the cross-index half is broken — exactly as claimed. The in-tree duplicate.json fixture only exercises batch dedup, so tests do not catch it. This is a real, material correctness defect (high severity: duplicate paragraphs from prior runs silently re-admitted), not a stylistic nitpick.

**Citations.** tools/build-russell-corpus/scripts/sentinel.py:77-81 (existing_locators key vs cand_locator key); tools/build-russell-corpus/scripts/sentinel.py:146 (batch path keys correctly on paragraph_text); tools/build-russell-corpus/scripts/corpus_io.py:60-65 (content_locator = first 120 stripped chars); tools/build-russell-corpus/scripts/append_to_index.py:30 (index stores cand["content_locator"], the short snippet); tools/build-russell-corpus/tests/fixtures/existing_index_sample.json:8-22 (committed entries have no content_locator field, only rhetorical_move); tools/build-russell-corpus/tests/fixtures/candidates/good.json:6-7 (content_locator "Philosophy, throughout its history," vs full paragraph_text); tools/build-russell-corpus/tests/test_corpus_io.py:97 (content_locator of full text = distinct 120-char string)


---

## `preflight-ignores-chapter-conformance` — MEDIUM

**Location:** `skills/book-compose/scripts/book_preflight.py:51` · **area:** book preflight gate · **confidence:** high

**Finding.** _check_chapter_release only verifies the chapter manifest exists and is schema-valid; it never inspects shacl_conforms/competency_clean, so a chapter bundle explicitly marked shacl_conforms: false still passes book preflight.

**Fix.** In _check_chapter_release, fail when manifest.get('shacl_conforms') is not True or manifest.get('competency_clean') is not True, so per-chapter conformance is actually enforced rather than silently overridden by the fresh workspace audit only.

**Evidence.** The claim is accurate. `_check_chapter_release` (book_preflight.py:51-61) only verifies the per-chapter `manifest.yaml` exists (line 54) and validates against `RELEASE_SCHEMA` (line 58); it returns `(True, "")` on schema validity and never reads `manifest.get('shacl_conforms')` or `manifest.get('competency_clean')`. Both fields are real, schema-defined manifest properties (release-manifest.schema.json:13-14, type boolean) that are written into each chapter bundle's manifest (build_release_bundle.py:93-94) precisely to record that chapter's conformance state at build time. The only conformance enforcement in `book_preflight` is `_run_workspace_audit` (lines 64-75, 103-114), which re-runs SHACL and competency queries against the CURRENT workspace graph — a different thing from the per-chapter stamped state. So a chapter bundle explicitly stamped `shacl_conforms: false` (e.g. built earlier against a non-conforming slice) still passes `_check_chapter_release`, and if the current workspace happens to conform, the whole `book_preflight` returns passes=True while shipping a chapter that was marked non-conforming. The per-chapter field is silently ignored. This is a genuine correctness gap, not stylistic: the schema deliberately carries these per-chapter booleans yet the gate that consumes the bundles never reads them. The suggested fix (fail when `manifest.get('shacl_conforms') is not True` or `competency_clean is not True` inside `_check_chapter_release`) is the correct remedy. The judgment is fully static; no runtime observation needed.

**Citations.** skills/book-compose/scripts/book_preflight.py:51-61 (_check_chapter_release only checks existence + jsonschema.validate, returns True without reading conformance fields); book_preflight.py:103-114 (only workspace-level audit feeds the passes calculation); skills/book-compose/assets/release-manifest.schema.json:13-14 (shacl_conforms and competency_clean are defined boolean manifest fields); skills/book-compose/scripts/build_release_bundle.py:86-96 (per-chapter manifest writes these fields)


---

## `autodetect-latest-by-mtime` — MEDIUM

**Location:** `skills/book-compose/scripts/build_book.py:38` · **area:** book assembly · **confidence:** high

**Finding.** _autodetect_latest_versions selects the 'latest' chapter version by directory mtime, not by semantic version, so rebuilding or touching an older release directory makes build_book silently assemble a stale chapter version into the book.

**Fix.** Sort candidate versions by parsed semantic version (or require explicit chapter_versions) instead of mtime; if mtime is intentional, document it loudly and warn when the mtime-latest version is not the version-latest.

**Evidence.** The cited code confirms the claim exactly. _autodetect_latest_versions (lines 23-41) walks chapters/releases/, parses each dir name into (chapter_id, version) via regex `^(ch-\d+)-(.+)$`, and stores (version, mtime) tuples. At lines 38-40 it sorts each chapter's candidates by `key=lambda t: t[1]` (the mtime, index 1) with reverse=True and picks candidates[0][0], i.e. the most-recently-modified directory's version string — version (t[0]) is never used as a sort key. So "latest" means newest mtime, not highest semantic version. Because build_book (line 137-138) calls this whenever chapter_versions is None (the default CLI path when no explicit JSON is passed), any operation that updates an older release dir's mtime — re-running a build, a git checkout/clone that rewrites timestamps, a backup-restore, an editor touch, or even copying releases around — would cause an older version (e.g. v1) to be selected over a newer one (e.g. v2) and silently assembled into the book, with no warning and no comparison against the lexically/numerically greatest version. The issue is real and material for correctness: silent assembly of a stale chapter is a serious, hard-to-detect failure mode. mtime ordering is fragile and filesystem-dependent rather than deriving from the version string the regex already extracts. This is static and observable; no runtime needed. (The version format is like v1/v2 per the tests, and the existing autodetect test only seeds one version per chapter, so the multi-version selection path is untested.)

**Citations.** C:/Users/charl/russellian-book-suite/skills/book-compose/scripts/build_book.py:35 (mtime captured), :36 (stores (version, mtime)), :38-40 (sort key=t[1] reverse, picks candidates[0][0]); :137-138 (autodetect used by default in build_book); tests at skills/book-compose/tests/test_build_book.py:159-162 (autodetect test seeds only one version per chapter, multi-version path untested)


---

## `no-orphan-citation-strip-on-assembly` — MEDIUM

**Location:** `skills/book-compose/scripts/build_book.py:71` · **area:** manuscript / HTML assembly · **confidence:** medium

**Finding.** Neither _assemble_manuscript nor write_html_skeleton strips orphan [clm-YYYY-NNNNNN] tokens; CLAUDE.md mandates stripping on the assembled manuscript and merged HTML, and chapter_contract_check only counts tokens (it never removes them), so any leaked token in a draft propagates verbatim into manuscript.md/manuscript.html.

**Fix.** Run the _CITATION_PATTERN strip (from chapter_contract_check) over the assembled manuscript_md and over the manuscript text before HTML inlining, as the known-pitfall note requires.

**Evidence.** The claim holds against the actual code. In build_book.py, _assemble_manuscript (lines 44-81) reads each chapter's draft.md verbatim (line 71: body = (release_dir / "draft.md").read_text(...)), rewrites only the H1 heading, and joins the bodies — there is no orphan-citation strip. The assembled manuscript_md is written directly to manuscript.md (line 152) and passed unchanged to write_html_skeleton (line 158). In render_book_html.py, write_html_skeleton (lines 24-34) only HTML-escapes the title and escapes "</script" in the payload/manuscript before inlining; it performs no [clm-YYYY-NNNNNN] stripping. The _CITATION_PATTERN (chapter_contract_check.py:20) is used solely to COUNT tokens (line 146: citation_tokens = len(_CITATION_PATTERN.findall(text))) feeding a metric; it never removes them, and a count metric can be configured as a pass/fail test but does not mutate text. A repo-wide grep for re.sub / strip / clm- across the scripts dir returns only the counting pattern, confirming no strip exists anywhere in the assembly path. CLAUDE.md's "Known pitfalls" explicitly mandates: "Orphan citation tokens leak. Strip on chapter draft AND assembled manuscript AND merged HTML." The assembled-manuscript and merged-HTML strips are absent, so any leaked token in a draft propagates verbatim into manuscript.md and manuscript.html. The issue is real and material (a documented invariant is unmet), not stylistic. Severity medium is fair: it is a defense-in-depth gap that only manifests when a draft already contains an orphan token, but the contract check counts rather than guarantees removal.

**Citations.** skills/book-compose/scripts/build_book.py:71 (draft.md read verbatim), :77 (join, no strip), :152 (write manuscript.md), :158 (pass manuscript_md to skeleton); skills/book-compose/scripts/render_book_html.py:24-31 (only HTML/script escaping, no token strip); skills/book-compose/scripts/chapter_contract_check.py:20 (_CITATION_PATTERN) and :146 (findall count only, no removal); CLAUDE.md "Known pitfalls": "Orphan citation tokens leak. Strip on chapter draft AND assembled manuscript AND merged HTML."


---

## `bundle-hardcodes-conformance-flags` — MEDIUM

**Location:** `skills/book-compose/scripts/build_release_bundle.py:93` · **area:** release-bundle integrity · **confidence:** high

**Finding.** The chapter release manifest hardcodes shacl_conforms: True and competency_clean: True without running any SHACL or competency check, so a bundle built from a non-conforming workspace falsely advertises conformance.

**Fix.** Either run book-knowledge's validate_shacl + run_competency_queries (as book_preflight does via _run_workspace_audit) and write the real booleans, or drop the two fields from the bundle manifest so they cannot be trusted as decorative truth.

**Evidence.** The cited line is exactly as claimed. In build_release_bundle.py the manifest dict (lines 86-95) sets "shacl_conforms": True (line 93) and "competency_clean": True (line 94) as literal constants. The function body (lines 54-98) never imports or invokes any SHACL or competency check — a grep of the file finds only those two hardcoded literals and nothing else matching preflight/audit/validate_shacl/competency/conforms. So a bundle built from a non-conforming workspace will still advertise conformance. This is material, not stylistic: the sibling real path proves these are meant to be computed — book_preflight.py:64-70 and preflight.py:32-37 actually call validate_shacl(layout) and run_competency_queries(layout), and build_book.py:173 threads the real pre.shacl_conforms into its book manifest. The reference doc release-bundle-format.md:60-61 explicitly documents both fields as "recorded from the pre-flight gate" / "recorded from the competency-query gate," a contract the chapter-bundle code silently breaks. The suggested fix (compute the real booleans via _run_workspace_audit, or drop the fields) is sound. No runtime observation was needed; the falsehood is static.

**Citations.** skills/book-compose/scripts/build_release_bundle.py:86-95 (manifest with hardcoded shacl_conforms: True line 93, competency_clean: True line 94; whole function lines 54-98 has no audit call); contrast skills/book-compose/scripts/book_preflight.py:64-70 and skills/book-compose/scripts/preflight.py:32-37 (real validate_shacl/run_competency_queries calls); skills/book-compose/scripts/build_book.py:173 (real value threaded in); skills/book-compose/references/release-bundle-format.md:60-61 (documents fields as recorded from the gates).


---

## `propagate-iteration-is-dead` — MEDIUM

**Location:** `skills/book-knowledge/scripts/propagate_belief.py:57` · **area:** belief graph / propagation · **confidence:** high

**Finding.** The MAX_ITERATIONS fixed-point loop is dead code: new_p depends only on static inputs (prior, sources, counter-claims) and never on the previous p, so it always converges after the first pass and the iteration/CONVERGENCE_EPSILON machinery does nothing.

**Fix.** Either make the recurrence actually depend on prior-iteration values (needed once derivation edges feed in) or drop the loop and compute posteriors in a single pass.

**Evidence.** In propagate() (lines 57-68) the loop body computes new_p[cid] (lines 60-63) purely from static, loop-invariant inputs: node.p_prior/prior_for_status(node.status), node.sources, the trust dict, and cc_by_target. It never reads the previous-iteration dict p; p is used only to compute delta on line 64. _evidence_combine (22-31) and _apply_counter_damping (34-42) likewise reference no prior-iteration state, and graph.nodes is not mutated in the loop. Therefore pass 1 produces the final values; pass 2 recomputes byte-identical values, delta becomes exactly 0 < CONVERGENCE_EPSILON, and the loop breaks after the second iteration. The result is independent of MAX_ITERATIONS, and the convergence machinery does no work — there is no cross-node coupling (no parent posterior feeding a child), despite the module docstring claiming propagation over a derivation graph. This is a real, material design/correctness gap, not stylistic: the advertised iterative belief propagation is unimplemented and the loop is effectively dead. Severity medium is reasonable because the single-pass output is still well-defined.

**Citations.** C:/Users/charl/russellian-book-suite/skills/book-knowledge/scripts/propagate_belief.py:57-68 (loop), :60-63 (new_p depends only on static inputs), :64-66 (delta/p usage), :22-31 (_evidence_combine), :34-42 (_apply_counter_damping), :1 (docstring claims derivation-graph propagation)


---

## `malformed-report-silently-skipped` — MEDIUM

**Location:** `skills/book-review/scripts/aggregate_reviews.py:28` · **area:** metric aggregation · **confidence:** high

**Finding.** _gather_reviews swallows ValueError/KeyError and continues, so a persona whose subagent emitted a report missing frontmatter is silently dropped from the panel with no warning, shrinking the gate's evidence base.

**Fix.** Collect parse failures and surface them (raise or include a 'failed personas' section in persona-review.md) so a missing/broken review is visible rather than silently reducing the panel.

**Evidence.** The claim is accurate against the code. In aggregate_reviews.py, _gather_reviews iterates the reviews/*.md files and wraps parse_review_report in `try: ... except (ValueError, KeyError): continue` (lines 28-31), with no logging, no failure accumulation, and no propagation. parse_review_report (dispatch_review.py:81-85) raises ValueError exactly when a report is missing frontmatter, so a persona whose subagent emitted a malformed/frontmatter-less report is silently skipped. The downstream output is built solely from the successfully-parsed `reviews` list: per_persona verdicts, severity_counts, and persona_breakdown_by_severity all derive from `reviews` (lines 51-73), and the generated persona-review.md (lines 79-119) contains no "failed personas" or skipped-count section. run_review_pass (review_pass.py:76-83) prepares N dispatch packets but never compares the expected persona count to the number actually parsed, so the shrinkage is invisible to the caller too. This is material, not stylistic: a dropped persona's critical findings vanish from the panel that feeds the review gate, weakening the evidence base with no signal. The suggested fix (collect and surface parse failures) is appropriate.

**Citations.** skills/book-review/scripts/aggregate_reviews.py:27-32 (try/except ValueError,KeyError + continue, no surfacing); skills/book-review/scripts/aggregate_reviews.py:65-73 (per_persona/breakdown built only from parsed reviews); skills/book-review/scripts/aggregate_reviews.py:79-119 (output md has no failed-personas section); skills/book-review/scripts/dispatch_review.py:83-85 (parse_review_report raises ValueError on missing frontmatter); skills/book-review/scripts/review_pass.py:76-83 (run_review_pass never reconciles expected vs parsed persona count)


---

## `counts-ignore-frontmatter` — MEDIUM

**Location:** `skills/book-review/scripts/aggregate_reviews.py:51` · **area:** metric aggregation · **confidence:** high

**Finding.** The aggregator re-derives severity counts from parsed body bullets and entirely ignores the persona-supplied critical_count/important_count/minor_count frontmatter, so a body-vs-frontmatter mismatch (e.g. a parsing drop) goes undetected.

**Fix.** Cross-check parsed bullet counts against the frontmatter *_count fields and flag/raise on mismatch, or treat the frontmatter counts as authoritative for gating.

**Evidence.** The aggregator's severity_counts are derived solely by counting parsed body bullets: aggregate_reviews.py:51-63 builds crit/imp/min pairs from r.critical/r.important/r.minor (the parsed Finding lists) and sets severity_counts to len() of the deduped lists. The persona-supplied frontmatter counts ARE available — parse_review_report (dispatch_review.py:86,107) loads the full frontmatter into raw_metadata, and the report schema (assets/review-report.schema.json:6,11-13) makes critical_count/important_count/minor_count REQUIRED, with the persona-prompt-template.md:33-35 instructing personas to emit them. But aggregate_reviews never reads raw_metadata or those *_count fields anywhere (grep shows no _count reference in aggregate_reviews.py). The body parser (_parse_findings_section, dispatch_review.py:61-78) is brittle — it only recognizes lines beginning with "- ", "* ", or "1." through "9." prefixes, so a finding written without a recognized bullet prefix, a multi-line finding, or numbering past 9 would be silently dropped, producing a body-count that diverges from the authoritative frontmatter count with no detection or flag. This is material because severity_counts['critical'] feeds the persona_critical_count==0 release gate (SKILL.md:14,60), so an undetected undercount could let a critical finding slip the gate. The claim, file, and line are all accurate.

**Citations.** skills/book-review/scripts/aggregate_reviews.py:51-63 (counts derived from parsed body, no frontmatter cross-check); dispatch_review.py:61-78 (brittle bullet-prefix parser), :86,107 (frontmatter loaded into raw_metadata but unused by aggregator); assets/review-report.schema.json:6,11-13 (critical_count/important_count/minor_count required); assets/persona-prompt-template.md:33-35 (personas emit the counts); SKILL.md:14,60 (severity_counts gates release on persona_critical_count==0); tests/fixtures/synthetic_reviews/gottlieb.md:5-7,14-28 (frontmatter counts coexist with body bullets, only the latter are aggregated)


---

## `empty-persona-id-key-collision` — MEDIUM

**Location:** `skills/book-review/scripts/aggregate_reviews.py:65` · **area:** metric aggregation · **confidence:** high

**Finding.** persona_id defaults to empty string on parse, and per_persona / persona_breakdown_by_severity are dicts keyed by persona_id, so two reports with a missing persona field collide on key '' and one persona's verdict/breakdown overwrites the other.

**Fix.** Require a non-empty persona field (raise in parse_review_report or fall back to the report filename stem) before using it as a dict key.

**Evidence.** The claim holds against the actual code. In dispatch_review.py:99, parse_review_report does `persona_id=meta.get("persona", "")`, defaulting to an empty string with no validation/raise when the YAML frontmatter lacks a `persona` field. In aggregate_reviews.py, `per_persona = {r.persona_id: r.verdict for r in reviews}` (line 65) and `persona_breakdown_by_severity[r.persona_id] = {...}` (lines 67-73) are both dicts keyed by persona_id. Two review reports each missing the persona field both yield persona_id == "", so the second report's verdict and severity breakdown silently overwrite the first's; the rendered per-persona verdict table (lines 95-102) then shows only one collapsed "" row. The defensive `except (ValueError, KeyError)` in _gather_reviews (line 30) does not catch this because a missing persona raises neither. Aggregated findings lists themselves survive (they go through _dedup_findings over lists, not dicts), so the loss is scoped to verdicts and per-persona breakdown rows — a real, material correctness bug rather than a nitpick. Severity "medium" and the suggested fix (require non-empty persona or fall back to filename stem) are appropriate. No runtime observation was needed; the behavior is determinable statically.

**Citations.** skills/book-review/scripts/aggregate_reviews.py:65 (per_persona keyed by r.persona_id), :67-73 (persona_breakdown_by_severity keyed by r.persona_id), :95-102 (verdict table iterates per_persona); skills/book-review/scripts/dispatch_review.py:99 (persona_id=meta.get("persona", "")), :81-86 (parse_review_report has no persona validation), :29 (ReviewResult.persona_id field); aggregate_reviews.py:30 (except only catches ValueError/KeyError)


---

## `orphan-floods-real-claims` — MEDIUM · needs runtime verification

**Location:** `skills/book-thesis/scripts/datalog_consistency.py:116` · **area:** datalog-consistency · **confidence:** medium

**Finding.** Every verified claim is asserted as paragraph(cid) but real claims carry no supports_nodes, so reaches_thesis(cid) is always false and orphan_paragraph fires on every claim in a real book, flooding the D9 orphan report with false positives.

**Fix.** Do not assert paragraph(cid) for ledger claims that have no supports edge (or scope orphan_paragraph to actual manuscript paragraphs rather than ledger claim ids); reconcile with lint_supports which is the real paragraph-orphan detector.

**Evidence.** The claim holds. In datalog_consistency.py line 116 every verified ledger claim is asserted as paragraph(cid). The only thing that asserts a supports edge for a claim is line 124, _multi_assert("supports", cid, rec.get("supports_nodes")), which is a no-op when supports_nodes is absent/empty (line 127-129 iterates over `values or []`). In consistency.dl, reaches_thesis(P) (lines 32-33) requires at least one supports(P,N) fact, and orphan_paragraph(P) <= paragraph(P) & ~reaches_thesis(P) (line 36) therefore fires for any claim with no supports edge; run() emits one D9 orphan per such fact (lines 176-178). The decisive empirical premise — that real claims carry no supports_nodes — is confirmed two ways: (1) the canonical claim-record.schema.json (book-knowledge/assets) has "additionalProperties": false and does not define supports_nodes at all (it defines supports_chapters instead), so a schema-conforming claim literally cannot carry supports_nodes; (2) the real example ledger examples/bermuda-manual/claims/ledger.jsonl has 50 claims and 0 occurrences of supports_nodes. The string supports_nodes appears nowhere in the repo except datalog_consistency.py and its own test fixtures, which hand-craft claims with supports_nodes that exist nowhere in production. So against any real book ledger, every verified claim becomes an orphan_paragraph false positive, flooding the D9 report — exactly as claimed. This is material (correctness), not stylistic: orphans is a reported defect class. Note D9 orphans do not fail the gate (gate_failed checks only contradictions/invariants, line 63-64), so it is report pollution rather than a false gate-fail, which matches the medium severity.

**Citations.** skills/book-thesis/scripts/datalog_consistency.py:115-116 (assert claim+paragraph), :124 (supports from supports_nodes), :127-129 (_multi_assert no-op on empty), :176-178 (D9 orphan emission), :63-64 (gate ignores orphans); skills/book-thesis/rules/consistency.dl:32-33 (reaches_thesis needs supports edge), :36 (orphan_paragraph rule); skills/book-knowledge/assets/claim-record.schema.json:36,44 (supports_chapters defined, supports_nodes absent, additionalProperties:false); examples/bermuda-manual/claims/ledger.jsonl (50 claims, 0 with supports_nodes); skills/book-thesis/tests/test_datalog_consistency.py:71-87 (test fixtures inject supports_nodes that real claims lack)


---

## `transitive-contradiction-untested` — MEDIUM

**Location:** `skills/book-thesis/tests/test_datalog_consistency.py:53` · **area:** tests / datalog · **confidence:** high

**Finding.** SKILL.md bills transitive cross-chapter contradiction (A->B in ch-1, B->not-A in ch-2) as the headline Layer-4 capability, but no test or fixture ever asserts an `implies` fact, so the transitive_contradiction rule is entirely unexercised and could be silently broken.

**Fix.** Add a test that writes claims with `implies` edges plus a contradicting value pair and asserts a transitive_contradiction defect is emitted (and deduped against direct contradictions).

**Evidence.** SKILL.md bills transitive cross-chapter contradiction as the headline Layer-4 capability (lines 6-7 "Datalog pass over claim triples for transitive cross-chapter contradictions"; line 30; line 70; and the Tests section line 110 explicitly claims coverage of "contradicting-claim fixture (A->B in ch-1, B->not-A in ch-2)"). The actual transitive_contradiction rule (consistency.dl lines 49-50) fires only via the implies(A,B) edge: it requires an implies fact plus a downstream direct/transitive contradiction. But a repo-wide grep shows zero test or fixture ever asserts an implies fact. test_datalog_consistency.py exercises only direct_contradiction (line 65 asserts "direct_contradiction" in rules), orphan, and clean-pass; none of its claim records carry an "implies" key, so _multi_assert("implies", ...) at datalog_consistency.py:123 is never fed real data. The lone other reference, book-qa's test_d10_transitive_contradiction_picked_up_from_datalog_defects_json, hand-writes a pre-baked datalog-defects.json and only checks that lint_artifact ingests a D10 entry — it never runs the Datalog engine or the rule. So the implies-driven branches of transitive_contradiction (the genuinely transitive, non-direct logic, lines 49-50) are entirely unexercised and could be silently broken (e.g., a typo in the predicate name, a missing TERMS entry, or pyDatalog recursion issues would go undetected). The SKILL.md Tests claim of an "A->B in ch-1, B->not-A in ch-2" fixture is materially false. The claim is true and material; the suggested fix (a test asserting implies edges produce a transitive_contradiction defect, deduped against direct contradictions) is exactly right and would also validate the dedup logic at datalog_consistency.py:183-185 (skip=direct).

**Citations.** skills/book-thesis/SKILL.md:6-7,30,70,110; skills/book-thesis/rules/consistency.dl:48-51; skills/book-thesis/scripts/datalog_consistency.py:123,183-185; skills/book-thesis/tests/test_datalog_consistency.py:53-103 (no implies key in any claim record); skills/book-qa/tests/test_lint_artifact.py:239-258 (stages pre-baked JSON, does not run the rule). Repo-wide grep for "implies|transitive_contradiction" in **/*test*.py returns no book-thesis test asserting an implies fact.


---

## `parse-bool-value-kind-string` — MEDIUM

**Location:** `verifiers/bermuda/cljs-orchestrator/src/main/bermuda/booklogic.cljs:460` · **area:** booklogic value-kind inference · **confidence:** high

**Finding.** infer-value-kind recognizes only parse-int/parse-float/boolean-literal, so lift L005's (parse-bool ?v) emit falls through to :string even though :primary-endpoint-met is declared :bool in predicates.edn — the legacy predicates.edn codegen records a value-kind that contradicts the declared return sort.

**Fix.** Add a (parse-bool ?x) → :bool branch to infer-value-kind (and parse-bool support in the ingester) so boolean lifts type correctly.

**Evidence.** The claim holds end-to-end. infer-value-kind (booklogic.cljs:444-466) only matches parse-int→:int, parse-float→:real, boolean? literal→:bool, else→:string. L005-primary-endpoint-met's emit is (fact ?claim-id :t :primary-endpoint-met (parse-bool ?v)) (adsc-clinical/rules/booklogic/lifts.edn:55), whose body (parse-bool ?v) is a seq headed by parse-bool — not parse-int/parse-float and not a boolean literal — so it falls through to :string. The predicate is declared :bool in booklogic/predicates.edn:30, so the codegened value-kind contradicts the declared return sort. The codegen path is real and load-bearing: -main (booklogic.cljs:561) writes rules/predicates.edn via emit-predicates-edn, and emit-predicates-edn-string (lines 482-497) sets :value-kind solely from (infer-value-kind (:emit lift)) and emits no :value key. The committed rules/predicates.edn:17-26 currently shows :value-kind :bool with :value true, but the codegen would never produce that (no :value emitted, value-kind would be :string), so the committed file is divergent and a regen overwrites it incorrectly. The downstream impact is concrete: with :value-kind :string the ingester (adsc-clinical/scripts/ingest_ledger.py:129-131) extracts the raw matched word ("met"/"missed") as a string value rather than taking the :bool branch (lines 106-107) that emits a boolean. So a predicate declared :bool gets string-typed facts. The ingester already supports the bool branch, confirming the suggested fix (add parse-bool→:bool in infer-value-kind) is the correct and material remedy. Material, not stylistic; statically verifiable.

**Citations.** verifiers/bermuda/cljs-orchestrator/src/main/bermuda/booklogic.cljs:444-466 (infer-value-kind: only parse-int/parse-float/boolean? then :else :string); booklogic.cljs:482-497 (emit-predicates-edn-string sets :value-kind from infer-value-kind, no :value key); booklogic.cljs:561 (-main writes rules/predicates.edn via emit-predicates-edn); verifiers/adsc-clinical/rules/booklogic/lifts.edn:52-55 (L005 emits (parse-bool ?v)); verifiers/adsc-clinical/rules/booklogic/predicates.edn:30 (defpredicate :primary-endpoint-met [:trial] :bool); verifiers/adsc-clinical/rules/predicates.edn:17-26 (committed entry has :value-kind :bool, :value true — divergent from codegen); verifiers/adsc-clinical/scripts/ingest_ledger.py:106-131 (bool branch uses :value; string branch takes raw matched text)


---

## `popper-cljs-python-divergence` — MEDIUM · needs runtime verification

**Location:** `skills/neurosym-forge/scripts/induce_theory.cljs:167` · **area:** induce_theory.cljs vs _induction_sources.py parity · **confidence:** high

**Finding.** The cljs `popper-search` does not skip groups with an empty arg-sort key or fewer than two predicates, whereas the Python `popper_search` does (`if not sort_key or len(names) < 2: continue`); predicates with no `:arg-sorts` are grouped under `[]` and paired in cljs but excluded in Python, so the two implementations that the module header says "must stay in step" produce different candidate sets.

**Fix.** Add the same `(when (and (seq sort-key) (>= (count names) 2)) ...)` guard to the cljs popper search, and add a cross-implementation parity test against a shared fixture.

**Evidence.** The cljs `popper-search` loop (induce_theory.cljs:167-194) iterates `(vals by-sort)` and emits a candidate for every predicate pair in each group, with no guard skipping the empty arg-sort group or short groups. The Python `popper_search` (_induction_sources.py:265-267) has an explicit `if not sort_key or len(names) < 2: continue`. The `len(names) < 2` half is functionally inert in both (a 1-element group yields no pairs anyway via the `(range (inc i) ...)` / `combinations` construction), so it is not a real divergence. But the `not sort_key` / `(seq sort-key)` half is material: predicates with no `:arg-sorts` are grouped under the empty key (`[]` in cljs at lines 161-165, `()` in Python at 263-264). Python drops that group entirely; cljs pairs those predicates and emits `popper-P~Q` candidates. So when a schema has two or more `:real`-returning predicates lacking `:arg-sorts`, the two implementations produce different candidate sets, contradicting the module header's explicit invariant (induce_theory.cljs:6, _induction_sources.py:19-22 — "the two implementations must stay in step"). This is a genuine correctness/parity bug, not stylistic. It is statically determinable; no runtime observation was needed. The suggested fix (add `(when (and (seq sort-key) (>= (count names) 2)) ...)`) is correct, though `(seq sort-key)` is the load-bearing part.

**Citations.** skills/neurosym-forge/scripts/induce_theory.cljs:6 (parity invariant); induce_theory.cljs:161-165 (groups by `(vec (or (:arg-sorts sig) []))`, empty key `[]`); induce_theory.cljs:167-194 (popper-search loop, no skip guard); skills/neurosym-forge/scripts/_induction_sources.py:19-22 (parity invariant); _induction_sources.py:263-264 (groups by `tuple(arg_sorts)`); _induction_sources.py:265-267 (`if not sort_key or len(names) < 2: continue`)


---

## `confabulation-test-module-mismatch` — MEDIUM

**Location:** `skills/neurosym-forge/tests/test_failure_modes.py:357` · **area:** failure-mode test binding · **confidence:** high

**Finding.** `test_proof_level_confabulation_rejected` probes `_has_module("scripts._induction_grammar")` and imports a Python `grammar_conforming`, but the enforcer is a ClojureScript file (`_induction_grammar.cljs`) with no Python module, so the production branch is unreachable and the test can never exercise the real gate even after Phase V lands.

**Fix.** Either shell into nbb to call the cljs `grammar-conforming-json` (as `test_induction_grammar.py` does) or move the circular-definition check into a Python module the test can import; the current `find_spec` probe is structurally incapable of binding.

**Evidence.** The cited test `test_proof_level_confabulation_rejected` (test_failure_modes.py:357-360) gates its production path on `_has_module("scripts._induction_grammar")`, where `_has_module` (line 51-60) is implemented purely as `importlib.util.find_spec(name) is not None` — a Python-module spec probe. The only artifact on disk is `scripts/_induction_grammar.cljs` (Glob confirms no `_induction_grammar.py`), and `find_spec` cannot resolve a ClojureScript file. The cljs file's docstring (lines 24-31) shows its public surface is Clojure (`grammar-conforming?`, `grammar-conforming-json`) returning JSON — there is no Python `grammar_conforming` symbol to import. Therefore the true branch is unreachable and the test always falls through to `_stub_grammar_conforming` (line 362), never exercising the real cljs gate. The suggested fix is corroborated by the sibling test_induction_grammar.py (lines 33-60), which shells into `nbb` against the cljs file via `grammar-conforming-json` — the structurally correct binding the failure-mode test lacks. Note: the enforcer already exists as cljs (it is Phase V's gate), so the probe is incapable of binding now and after Phase V; this strengthens the claim. Real and material: a regression test that can never run against the production enforcer.

**Citations.** skills/neurosym-forge/tests/test_failure_modes.py:357-362 (find_spec-gated branch importing Python grammar_conforming); skills/neurosym-forge/tests/test_failure_modes.py:51-60 (_has_module = importlib.util.find_spec); skills/neurosym-forge/scripts/_induction_grammar.cljs:1-31 (Clojure-only public surface, no Python module); Glob shows only _induction_grammar.cljs exists, no .py; skills/neurosym-forge/tests/test_induction_grammar.py:33-60 (correct nbb-shell pattern against the cljs).


---

## `skillmd-wrong-import-path` — MEDIUM

**Location:** `skills/review-conductor/SKILL.md:75` · **area:** documentation contract · **confidence:** high

**Finding.** The usage example imports 'from review_conductor.conductor import run_panel' but the installed package is named 'scripts' (pyproject packages=["scripts"], tests import 'from scripts.conductor'), so the documented call fails with ModuleNotFoundError.

**Fix.** Correct the SKILL.md example to 'from scripts.conductor import run_panel' (or rename the package to review_conductor and update tests/pyproject) so the documented entrypoint actually imports.

**Evidence.** The SKILL.md usage example at line 75 documents `from review_conductor.conductor import run_panel`, but the package is actually named `scripts`: pyproject.toml line 26 declares `packages = ["scripts"]`, and the integration tests import `from scripts.conductor import run_panel` (test_conductor_integration.py lines 38 and 51). A repo-wide grep confirms `review_conductor` appears only at SKILL.md:75 with no package, alias, or symlink providing that module name. Running the documented snippet from the skill directory would therefore raise ModuleNotFoundError: No module named 'review_conductor'. This is a real, material correctness defect in a documentation contract that CLAUDE.md explicitly says must keep working commands accurate ("broken commands here mislead operators"), not a stylistic nitpick. The suggested fix (change to `from scripts.conductor import run_panel`) matches what the tests already do.

**Citations.** skills/review-conductor/SKILL.md:75 (`from review_conductor.conductor import run_panel`); skills/review-conductor/pyproject.toml:26 (`packages = ["scripts"]`); skills/review-conductor/tests/test_conductor_integration.py:38,51 (`from scripts.conductor import run_panel`); repo-wide grep shows `review_conductor` only at SKILL.md:75


---

## `majority-critical-counts-advisory` — MEDIUM

**Location:** `skills/review-conductor/scripts/aggregate_panel.py:73` · **area:** verdict computation · **confidence:** medium

**Finding.** The majority_critical rule counts any persona with a critical (gating OR advisory) and divides by len(panel.personas) including advisory personas, so advisory personas both trigger and inflate the denominator of a gate that is supposed to honor the gating/advisory distinction, and an exact tie passes.

**Fix.** Restrict the majority count and denominator to gating personas (or document that majority_critical intentionally ignores the gate column), and decide tie semantics explicitly (>= vs >).

**Evidence.** The factual core of the claim is accurate against the code. In aggregate_panel.py:72-77 the majority_critical branch sets total = len(panel.personas) and counts critical_personas = sum over per_persona.values() of stats["critical"] > 0. per_persona is populated for every persona that produced a parseable report regardless of its gate (line 53), and load_panel.py:42-79 confirms panel.personas mixes gating and advisory PersonaConfig entries. So advisory personas both (a) contribute a critical that can push critical_personas up and (b) inflate the denominator total. This contradicts the gate-aware bookkeeping the same function does for the other two rules (gating_criticals vs advisory_criticals, lines 54-58), and the spec's stated central principle is precisely the gating/advisory distinction (docs/specs/2026-05-13-review-conductor-design.md:12). The tie claim is also correct: critical_personas > total/2 uses strict greater-than, so with an even persona count an exact half-and-half split (e.g. 2 of 4) evaluates 2 > 2.0 = False and returns "pass"; tie semantics are undocumented. One caveat that keeps this from being a clear-cut deviation: the plan's reference implementation (docs/plans/2026-05-13-review-conductor-and-personas.md:2350-2355) prescribes exactly this gate-ignoring, len(personas)-denominator, strict-> form, so the code matches its documented reference rather than diverging from it; the spec simply never defines majority_critical's intended semantics. Materiality is real but bounded: the rule is in the schema enum (panel-config.schema.json:37) and the branch is reachable, yet no shipped or fixture panel uses it (all configs use any_critical_from_gating) and test_aggregate_panel.py exercises only that rule, so it is an untested latent path. Net: the claim is true as a correctness/ambiguity finding (gate column silently ignored, tie unspecified) on a reachable code path; medium severity is fair.

**Citations.** skills/review-conductor/scripts/aggregate_panel.py:53 (per_persona populated for every persona), :54-58 (gate-aware counting for other rules), :72-77 (majority_critical: total=len(panel.personas), counts any critical>0, strict > total/2); skills/review-conductor/scripts/load_panel.py:42-79 (Panel.personas includes both gating and advisory); docs/specs/2026-05-13-review-conductor-design.md:12 (gating/advisory distinction is the design principle); docs/plans/2026-05-13-review-conductor-and-personas.md:2350-2355 (reference impl matches the code exactly); skills/review-conductor/assets/panel-config.schema.json:37 (rule in enum); skills/review-conductor/tests/test_aggregate_panel.py:27 and fixtures/panel-default.yaml:11 (only any_critical_from_gating is configured/tested)


---

## `concrete-density-no-block-skip` — MEDIUM · needs runtime verification

**Location:** `skills/russellian-style/scripts/lint_concrete_instance_density.py:39` · **area:** linters/concrete-instance-density · **confidence:** high

**Finding.** _paragraphs() splits only on blank lines and never strips markdown headings or fenced code blocks (unlike lint_common.iter_sentences), so a '# Heading' line counts as a zero-concrete-instance paragraph and inflates the 3-consecutive-zero run that triggers the finding.

**Fix.** Reuse lint_common's paragraph splitter (which skips headings/code/list markers) or replicate _is_heading/_is_code_block filtering before counting, so headings and code fences do not count toward zero-instance runs.

**Evidence.** The claim accurately describes the code. In lint_concrete_instance_density.py, _paragraphs() (lines 39-40) splits text purely on blank-line boundaries (re.split(r"\n\s*\n", ...)) and keeps every non-empty block with no markdown awareness. _concrete_count (lines 43-52) only counts spaCy NER entities in _NER_LABELS plus a "the <occupational-noun>" regex; a markdown heading like "# Methods" or a fenced code line contains neither, so it scores 0. The flagging loop (lines 65-83) counts consecutive zero-count paragraphs and fires the finding at a run length of 3. By contrast, the sibling lint_common.iter_sentences (lines 41-51) explicitly filters out headings, code blocks, and list markers via _is_heading/_is_code_block/_is_list_marker (lines 75-84) before processing paragraphs. So heading and code-fence "paragraphs" that this linter retains do count as zero-concrete paragraphs and can extend or bridge the 3-consecutive-zero run that triggers the finding, producing false-positive or inflated runs that the sibling linter would not. This divergence is fully determinable from the source; no runtime observation is required to confirm the differing code paths. The issue is material (correctness, false positives) rather than stylistic, and the suggested fix (reuse/replicate the heading/code filtering) is apt.

**Citations.** skills/russellian-style/scripts/lint_concrete_instance_density.py:39-40 (_paragraphs splits only on blank lines), :43-52 (_concrete_count = NER + occupational-noun regex only), :65-83 (3-consecutive-zero run triggers finding); skills/russellian-style/scripts/lint_common.py:41-51 (iter_sentences skips headings/code/list), :75-84 (_is_code_block/_is_heading/_is_list_marker filters)


---

## `paragraph-motion-no-block-skip` — MEDIUM · needs runtime verification

**Location:** `skills/russellian-style/scripts/lint_paragraph_motion.py:74` · **area:** linters/paragraph-motion · **confidence:** high

**Finding.** _paragraphs() splits on blank lines without removing headings or fenced code blocks, so heading lines and code-fence lines are classified as paragraphs (defaulting to assertion_only) and skew the flat_proportion >0.70 gate.

**Fix.** Filter heading and code-block paragraphs (reuse lint_common splitter) before classify_paragraph so structural markdown does not count as 'flat' prose paragraphs.

**Evidence.** The cited `_paragraphs()` at line 74-75 splits only on blank-line boundaries (`re.split(r"\n\s*\n", text)`) with no filtering of structural markdown. `lint_paragraph_motion` (line 80-86) feeds every such block straight into `classify_paragraph` and computes `flat_prop = flat_count/len(shapes)` against the >0.70 gate. Tracing `classify_paragraph`: a heading block (e.g. `# Introduction`) becomes a single "sentence" via `_sentences` (split on `(?<=[.!?])\s+`), matches none of the marker regexes, and falls to `len(sents) <= 1 -> "assertion_only"` (line 68-69), which is in the `flat` set (line 84). A fenced-code line (` ``` `) or an indented code line likewise yields one non-marker sentence -> `assertion_only` (flat). So headings and code-fence lines are counted as flat prose paragraphs and inflate both the numerator and denominator of `flat_prop`, skewing the >0.70 gate. The suggested fix is also concretely supported: the sibling `lint_common.py` already provides `_split_paragraphs` (line 54) plus `_is_code_block` (line 75) and `_is_heading` (line 79) helpers that could be reused to filter structural blocks before classification. The issue is real and material to correctness of the linter's gate, though the impact magnitude depends on document structure (advisory-severity rule), so it is medium rather than high impact.

**Citations.** C:/Users/charl/russellian-book-suite/skills/russellian-style/scripts/lint_paragraph_motion.py:74-75 (_paragraphs splits only on blank lines, no filtering); :80-86 (every block classified, flat_prop computed); :47-69 (classify_paragraph routes single-sentence non-marker blocks to assertion_only); :84 (flat set includes assertion_only/assertion_justification); :89 (>0.70 gate). lint_common.py:54 (_split_paragraphs), :75 (_is_code_block), :79 (_is_heading) — existing reusable filters.


---

## `adsc-no-sort-compat-check` — MEDIUM

**Location:** `verifiers/adsc-clinical/rust-verifier/src/smt.rs:82` · **area:** smt divergence (adsc-clinical) · **confidence:** high

**Finding.** adsc-clinical lacks the REQ-DSL-054 check_value_sort_compat guard present in bermuda, so binding a scalar to a vector/set-typed predicate is not rejected; combined with the missing UInt arm and ?-strip, the adsc verifier is materially less sound than bermuda for the same DSL.

**Fix.** Regenerate the adsc-clinical rust-verifier from the same neurosym-forge codegen revision as bermuda so the sort-compat guard, UInt handling, and canonical var naming are all present.

**Evidence.** Direct comparison of the two verifiers confirms all three divergences asserted. (1) Sort-compat guard: bermuda defines check_value_sort_compat (smt.rs:37-63) and calls it in bind_atoms (smt.rs:355-360) to reject scalars bound to [:vector T]/[:set T] predicates per REQ-DSL-054; adsc-clinical/smt.rs has no such function and no call site, so the scalar value match (line 82) silently asserts a scalar equality with no shape check — a real soundness gap. (2) UInt arm: bermuda handles Edn::UInt(n) identically to Edn::Int (smt.rs:371-377) because edn-rs renders bare non-negative integers as UInt; adsc-clinical's match (smt.rs:82-104) has Int/Double/Str/Bool then _ => continue, so UInt values are silently dropped (never asserted), weakening verification. (3) Canonical naming/?-strip: bermuda uses canonical_var_name (var_name.rs:9-13) stripping both ':' and '?'; adsc-clinical inlines trim_start_matches(':') only (smt.rs:70-74) and has no var_name.rs module at all, so ?-prefixed identifiers yield divergent Z3 var names. All three are static, observable in source, and jointly make adsc materially less sound than bermuda for the same DSL. Not a stylistic nitpick: dropped integer constraints and missing sort guard both let unsound bindings pass as sat.

**Citations.** verifiers/adsc-clinical/rust-verifier/src/smt.rs:70-74 (inline ':'-only var name), :82-104 (value match lacking UInt arm and any sort-compat call); verifiers/bermuda/rust-verifier/src/smt.rs:37-63 (check_value_sort_compat / REQ-DSL-054), :355-360 (guard call in bind_atoms), :371-377 (Edn::UInt arm), :345 (canonical_var_name use); verifiers/bermuda/rust-verifier/src/var_name.rs:9-13 (strips ':' and '?'); adsc-clinical has no var_name.rs (Glob: no files found).


---

## `verdict-graph-summary-dropped` — MEDIUM

**Location:** `verifiers/bermuda/rust-verifier/src/ir.rs:145` · **area:** ir / cljs-Rust verdict contract · **confidence:** high

**Finding.** emit_verdict never serializes graph_summary (nor verified or semantic_neighbours), so the kg GraphSummary that lib.rs computes and stores on the verdict is silently discarded on the EDN return trip even though the cljs Verdict schema declares :graph-summary.

**Fix.** Emit a :graph-summary {:claim-count N :contradictions [...]} map in emit_verdict when v.graph_summary is Some, so the contradiction data reaches the cljs consumer; or remove the dead kg summary computation in lib.rs if it is intentionally unused.

**Evidence.** The claim holds against the actual code. emit_verdict (ir.rs:145-204) serializes only :status, :core, :explanation, :queries, :cozo-defects, and :corpus-defects; it never emits :graph-summary (nor :verified). Yet the Verdict struct carries graph_summary: Option<GraphSummary> (ir.rs:48), and under the kg feature lib.rs:27-29 computes kg::ingest_and_summarize(&v.verified) and stores it on v.graph_summary immediately before calling emit_verdict at lib.rs:32. The cljs consumer's Verdict schema explicitly declares [:graph-summary {:optional true} :map] (ir.cljs:54), so the contract on the cljs side expects this key. Because emit_verdict omits it and the cljs field is {:optional true}, the GraphSummary (claim_count plus the contradictions vector built in kg.rs ingest_and_summarize) is silently dropped on the EDN return trip with no validation error to surface the loss. This is a real correctness gap, not a stylistic nitpick: contradiction data that lib.rs deliberately computes never reaches the orchestrator. The one scoping caveat is that the computation and thus the loss only occur when the kg cargo feature is enabled (the assignment lives inside #[cfg(feature = \"kg\")]); the suggested fix (emit :graph-summary when Some, or delete the dead kg computation) is correct. Static reasoning fully resolves this; no runtime observation needed.

**Citations.** verifiers/bermuda/rust-verifier/src/ir.rs:145-204 (emit_verdict body, no :graph-summary); ir.rs:48 (graph_summary field); ir.rs:111-115 (GraphSummary struct); verifiers/bermuda/rust-verifier/src/lib.rs:24-32 (computes and stores kg_summary then calls emit_verdict); verifiers/bermuda/cljs-orchestrator/src/main/bermuda/ir.cljs:48-54 (Verdict schema declares :graph-summary {:optional true})


---

## `find-paragraph-line-wrapped-html` — MEDIUM · needs runtime verification

**Location:** `tools/build-russell-corpus/scripts/corpus_io.py:85` · **area:** build-russell-corpus corpus_io · **confidence:** high

**Finding.** find_paragraph_line searches for the 120-char locator as a substring of a single physical line, but paragraph_in_source (Check 2) whitespace-normalises across lines; real Gutenberg HTML wraps paragraphs across many ~70-char lines, so a candidate that passes Check 2 will fail Check 3 with locator-not-found, and the test fixture hides this by using unwrapped single-line <p> tags.

**Fix.** Match the locator against a whitespace-normalised view of the source (or stream a sliding window) so line-wrapped paragraphs resolve a line number consistently with paragraph_in_source; add a fixture with realistically wrapped HTML.

**Evidence.** The claim is accurate and material. find_paragraph_line (corpus_io.py:85-91) does a raw `locator in line` substring test per physical line with no whitespace normalisation, whereas paragraph_in_source (corpus_io.py:68-82) normalises whitespace across the whole file (" ".join(source.split())). content_locator returns the first 120 stripped chars (corpus_io.py:60-65). In sentinel.py the same 120-char locator is fed to both: Check 2 (sentinel.py:66) uses paragraph_in_source, and Check 3 (sentinel.py:70) uses find_paragraph_line, rejecting with "locator-not-found" (sentinel.py:71-72) if no single line contains the full 120-char string. Real Gutenberg HTML wraps paragraphs at ~70 chars, so a 120-char locator necessarily straddles a line break and cannot be a substring of any one physical line — meaning a candidate that passes Check 2 systematically fails Check 3. This is a real correctness bug in the pipeline, not a nitpick. The test suite hides it exactly as claimed: the fixture problems_subset.html (lines 2-4) places each <p> paragraph on a single physical line; the only wrapped-HTML test (test_corpus_io.py:118-130) exercises paragraph_in_source alone and never calls find_paragraph_line; and the find_paragraph_line test (test_corpus_io.py:111-115) passes a short 23-char substring "The failure to separate" rather than the real 120-char content_locator output, so it never crosses a wrap boundary even if the fixture were wrapped. The bug is statically evident from the divergent matching strategies; no runtime observation is required.

**Citations.** tools/build-russell-corpus/scripts/corpus_io.py:60-65 (content_locator 120 chars); corpus_io.py:68-82 (paragraph_in_source whitespace-normalised); corpus_io.py:85-91 (find_paragraph_line per-physical-line substring, no normalisation); tools/build-russell-corpus/scripts/sentinel.py:66 (Check 2) and :70-72 (Check 3 locator-not-found with same 120-char locator); tools/build-russell-corpus/tests/fixtures/source_cache/problems_subset.html:2-4 (single-line <p> tags); tools/build-russell-corpus/tests/test_corpus_io.py:111-115 (find_paragraph_line tested with short substring) and :118-130 (wrapped test only exercises paragraph_in_source)


---

## `extract-jsonl-only-silent-drop` — MEDIUM

**Location:** `tools/build-russell-corpus/scripts/extract_candidates.py:39` · **area:** build-russell-corpus extract · **confidence:** high

**Finding.** extract_candidates assumes the LLM returns one JSON object per line and silently skips any non-JSONL output; a JSON array or pretty-printed response yields an empty candidates file with no error, deferring the failure to a confusing zero-candidate sentinel run.

**Fix.** Detect and parse a top-level JSON array (and reject/log when zero candidates were parsed from non-empty LLM output) instead of silently dropping every line; raise or warn when 0 of N requested candidates parse.

**Evidence.** The cited code (extract_candidates.py:39-48) parses the raw LLM response line-by-line with json.loads, catching JSONDecodeError per line and continuing with the comment "malformed LLM output: skip line; sentinel will catch absence downstream" (line 46-47). This means any non-JSONL response is silently dropped: a top-level JSON array (e.g. "[{...},{...}]") parses as one whole-string json.loads only if the entire array is on a single line, but a pretty-printed object/array spanning multiple lines yields a JSONDecodeError on every partial line and produces an empty candidates file with no error or warning. The function returns None regardless of how many of the N requested candidates parsed; there is no comparison of parsed count against n. The prompt template (extractor-prompt.md:20) does instruct JSONL ("emit one JSON object on its own line"), so the happy path matches the contract, but the claim is precisely about the silent-failure mode when the LLM deviates — a common occurrence given LLMs frequently emit code-fenced or pretty-printed JSON. Downstream, run_sentinel_batch (sentinel.py:120-124) iterates the empty file, skips blank lines, and writes nothing to any ledger — exactly the deferred "confusing zero-candidate sentinel run" the claim describes. No stage anywhere raises or warns when 0 of N candidates parse. The code comment itself admits the design defers failure detection to a downstream absence sentinel rather than catching it at parse time. This is a real, material correctness/robustness gap, not a stylistic nitpick; the suggested fix (detect top-level arrays, and warn/raise when 0 of N non-empty output parses) is appropriate.

**Citations.** tools/build-russell-corpus/scripts/extract_candidates.py:38-48 (line 39 splitlines loop, line 44 json.loads per line, lines 45-47 silent skip on JSONDecodeError with "sentinel will catch absence downstream" comment, no count check before return at 48); assets/extractor-prompt.md:20 (JSONL contract "emit one JSON object on its own line"); scripts/sentinel.py:120-124 (empty candidates file iterated, blank lines skipped, no zero-count detection)


---

## `sentinel-seed-entries-have-no-locator` — MEDIUM

**Location:** `tools/build-russell-corpus/scripts/sentinel.py:78` · **area:** build-russell-corpus sentinel · **confidence:** high

**Finding.** The committed seed index entries carry neither content_locator nor paragraph_text, so the dedup fallback uses content_locator(rhetorical_move) — comparing a lesson string against a paragraph prefix — making dedup against all pre-existing entries structurally impossible.

**Fix.** Backfill content_locator (paragraph-prefix form) onto seed entries during a one-time migration, or change derive/append to always store the canonical locator; do not silently fall back to rhetorical_move which is semantically unrelated to the paragraph text.

**Evidence.** The committed seed index (skills/russellian-style/assets/russell-corpus/index.json) holds 50 paragraph entries, each carrying only id, source, line_hint, rhetorical_move, and tags — none has content_locator or paragraph_text. sentinel.py line 77-78 builds existing_locators as content_locator(e.get("content_locator") or e.get("rhetorical_move", "")) for every existing entry. content_locator() is just text.strip()[:120] (corpus_io.py:60-65), with no normalization that could bridge the two string spaces. So for all 50 seed entries the fallback yields the rhetorical_move lesson string (e.g. "relation made concrete through a room example"), while the candidate's cand_locator (line 80) is the first 120 chars of the actual paragraph_text. A lesson string can never equal a paragraph prefix, so the dedup check at line 81 can never fire against any seed entry — dedup against the entire pre-seeded corpus is structurally impossible. Only entries appended later via _project_candidate_to_index_entry (append_to_index.py:24-31) store content_locator and thus dedup correctly; the 50 seeds — the most likely re-extraction collisions — are unprotected. No migration backfills content_locator (grep across both tools/build-russell-corpus and skills/russellian-style found none on the index). This is a genuine, material correctness defect, not a stylistic nitpick; medium severity is apt.

**Citations.** C:/Users/charl/russellian-book-suite/tools/build-russell-corpus/scripts/sentinel.py:77-82; corpus_io.py:60-65 (content_locator = strip()[:120]); skills/russellian-style/assets/russell-corpus/index.json:43-93 (50 seed entries, all lacking content_locator/paragraph_text); scripts/append_to_index.py:24-31 (only newly-appended entries get content_locator)


---

## `manuscript-heading-rewrite-requires-h1` — LOW

**Location:** `skills/book-compose/scripts/build_book.py:73` · **area:** manuscript assembly · **confidence:** medium

**Finding.** _assemble_manuscript injects the chapter number/title only into the first line starting with '# '; a draft.md that opens with '## ' or has no H1 gets no chapter heading and merges into the previous chapter with only a '---' rule separating them.

**Fix.** If no '# ' heading is found in the draft body, prepend a synthesized '# Chapter {n}: {title}' heading rather than leaving the chapter headingless.

**Evidence.** The code at build_book.py:73-76 iterates body_lines and rewrites only the first line where raw.startswith("# "), then breaks. If a draft.md has no H1 (e.g., it opens with "## " or has no top-level heading), the break never fires, body_lines is unchanged, and no "# Chapter {n}: {title}" heading is injected. At lines 77-80 each chapter body is then joined with the prior chapter via only a "---" rule and blank lines, so a headingless body has no H1 and structurally reads as a continuation under the previous chapter's heading — exactly as the claim states. Nothing upstream guarantees an H1: build_release_bundle.py copies draft.md byte-for-byte (line 65; references/release-bundle-format.md says "copied byte-for-byte"), and book_preflight.py never inspects draft content for a heading (it only checks contract validity, manifest schema, and SHACL). The test fixtures (test_build_book.py:32-33) always supply drafts that begin with "# ", so the no-H1 fallback is unhandled and untested. The claim is accurate. Materiality is modest/low: drafts conventionally lead with an H1 (drafting-playbook.md), so the broken case is an edge case rather than the common path — consistent with the claim's "low" severity. The suggested fix (synthesize a "# Chapter {n}: {title}" when no "# " line is found) is correct and would close the gap.

**Citations.** skills/book-compose/scripts/build_book.py:73-77 (heading-rewrite loop with break, only first "# " line); build_book.py:79-80 ("---" separator between chapters); skills/book-compose/scripts/book_preflight.py:51-61,88-114 (no draft-content/H1 check in preflight); skills/book-compose/scripts/build_release_bundle.py:65 (draft.md copied byte-for-byte); skills/book-compose/tests/test_build_book.py:31-33 (fixtures always start with "# ", no-H1 path untested)


---

## `persona-gate-trivial-pass-outside-workspace` — LOW

**Location:** `skills/book-compose/scripts/chapter_contract_check.py:68` · **area:** persona gate metrics · **confidence:** medium

**Finding.** _compute_persona_metrics returns persona_reviews_complete: True with all critical counts 0 when no workspace root (CLAUDE.md) is found above the draft, so a draft outside a workspace trivially satisfies persona_critical_count == 0 and persona_reviews_complete == True.

**Fix.** Return persona_reviews_complete: False when the workspace root cannot be located, so the persona gate cannot be passed by drafting outside a workspace.

**Evidence.** The cited branch at lines 68-74 of chapter_contract_check.py returns persona_critical_count: 0 and persona_reviews_complete: True whenever _find_workspace_root_from_draft (lines 23-28) returns None, i.e. when no CLAUDE.md is found in the draft path or any parent. The standard chapter contracts (e.g. assets/chapter-contract.template.yaml:25-26 and all examples/bermuda-manual/chapters/contracts/ch-*.yaml) gate on exactly persona_critical_count == 0 and persona_reviews_complete == True, both of which are satisfied trivially by this branch with no review having occurred. This is inconsistent with the other no-review branches in the same function: when a workspace IS located but the review file is missing (lines 96-102) or stale (lines 103-109), the code correctly returns persona_reviews_complete: False, and the test test_no_persona_review_fails_complete_check (test_persona_metrics.py:32-36) asserts that intended False behavior. So the no-workspace branch uniquely lets the persona soft-gate be passed without any review. The issue is real but materiality is bounded/low: per CLAUDE.md conventions drafts live inside a workspace whose root has a CLAUDE.md marker, so the workspace root is normally found; the bypass only fires for drafts placed outside any workspace, an atypical setup, and the gate is a soft gate. The suggested fix (return persona_reviews_complete: False on missing workspace root) is correct and consistent with the function's other branches.

**Citations.** skills/book-compose/scripts/chapter_contract_check.py:66-74 (no-workspace branch returns critical_count 0 + reviews_complete True); :23-28 (_find_workspace_root_from_draft returns None when no CLAUDE.md); :96-109 (contrasting branches return reviews_complete False); skills/book-compose/tests/test_persona_metrics.py:32-36 (asserts False when review absent in-workspace); skills/book-compose/assets/chapter-contract.template.yaml:25-26 and examples/bermuda-manual/chapters/contracts/ch-01.yaml:27-28 (gate tests persona_critical_count == 0 and persona_reviews_complete == True)


---

## `persona-metrics-missing-advisory-in-fallback` — LOW

**Location:** `skills/book-compose/scripts/chapter_contract_check.py:110` · **area:** persona gate metrics · **confidence:** high

**Finding.** Only the verdict.json branch emits persona_advisory_critical_count; the panel-review.md/persona-review.md fallback branches omit it, so a contract acceptance_test referencing persona_advisory_critical_count is silently skipped (treated as pass) whenever the legacy markdown path is used.

**Fix.** Add persona_advisory_critical_count (default 0) to the markdown-fallback and missing-file return dicts so the metric key is always present.

**Evidence.** The claim is accurate. In _compute_persona_metrics, only the verdict.json branch (line 87) emits persona_advisory_critical_count. The three other return dicts — the missing-file fallback (lines 97-102), the stale-review fallback (lines 104-108), and the markdown-parse path (lines 111-116) — all omit persona_advisory_critical_count. Combined with _evaluate_test's guard `if metric not in metrics: return True` (lines 175-176), any acceptance_test referencing persona_advisory_critical_count is silently treated as a pass whenever the verdict.json path is not taken (legacy panel-review.md/persona-review.md path, stale review, or no review file). This is a real correctness gap: the gate silently skips a test rather than failing or erroring. Materiality is genuinely low — it only manifests if a contract actually references that specific metric AND verdict.json is absent/stale — so the severity:low rating is appropriate. The suggested fix (default 0 in the fallback/missing-file dicts) is correct and matches the repo's stated schema discipline of keeping keys present/backward-compatible. The other persona keys (critical/important/minor/reviews_complete) are consistently present across all branches, underscoring that the advisory key's omission is an oversight rather than intentional.

**Citations.** C:/Users/charl/russellian-book-suite/skills/book-compose/scripts/chapter_contract_check.py:87 (verdict branch emits persona_advisory_critical_count); :97-102, :104-108, :111-116 (fallback/missing-file return dicts omit it); :175-176 (`if metric not in metrics: return True` — missing metric silently passes)


---

## `check-address-cache-leaks-keys` — LOW

**Location:** `skills/book-compose/scripts/check_address.py:34` · **area:** counter-claim addressing · **confidence:** medium

**Finding.** On a cache hit check_address returns {**cached, 'mechanism': 'llm'} unfiltered, so any extra keys persisted in the cache file (and an un-normalized 'addressed' value) leak into the result, unlike the fresh-verifier branch which normalizes addressed to bool and returns a fixed key set.

**Fix.** Reconstruct the return dict from cached explicitly: {'addressed': bool(cached['addressed']), 'mechanism': 'llm', 'supporting_paragraph': cached.get('supporting_paragraph')}.

**Evidence.** The claim accurately describes the code. At check_address.py:34 the cache-hit branch returns `{**cached, "mechanism": "llm"}`, spreading every key from the cached JSON unfiltered and passing through whatever `addressed` value was stored (no bool() coercion). The fresh-verifier branch at lines 37-39 instead constructs a fixed three-key dict and normalizes `addressed` via `bool(verdict["addressed"])`. Crucially, line 36 caches `json.dumps(verdict)` — the raw verifier output, not the normalized dict — so any extra keys (e.g. confidence/reasoning) or a non-bool `addressed` the verifier returns get persisted and then leak only on the cache-hit path. This is a genuine asymmetry: identical inputs yield different result-dict shapes depending on cache state, and it violates the documented return contract at line 21 ({addressed, mechanism, supporting_paragraph}). Materiality is low: the only in-repo verifier (the test stub) returns exactly {addressed, supporting_paragraph} with a real bool, so tests in test_check_address.py never exercise the divergence, and the downstream consumer promote_addressed.py keys off addressed_ids rather than the dict shape. But it is a real correctness/contract bug, not pure stylistic nitpicking, and the suggested fix (reconstruct the dict explicitly from cached) is correct.

**Citations.** skills/book-compose/scripts/check_address.py:21 (documented return contract), :32-34 (cache-hit spreads cached unfiltered, no bool coercion), :36 (caches raw verdict, not normalized), :37-39 (fresh branch fixed keys + bool()); skills/book-compose/tests/test_check_address.py:4-12,31-40 (stub verifier returns clean dict, so divergence untested); skills/book-knowledge/scripts/promote_addressed.py:10-24 (consumer uses addressed_ids, not the result dict shape)


---

## `verify-claim-doc-reads-wrong-file` — LOW

**Location:** `skills/book-knowledge/references/claims-and-provenance.md:68` · **area:** verification / docs · **confidence:** high

**Finding.** The doc states verify_claim opens wiki/sources/<doc_id>.md to cross-check locator_text, but verify_claim._load_source_text actually reads the raw file (raw/markdown/<doc_name> or re-extracts the PDF); the doc misdescribes the verification source.

**Fix.** Correct the doc to say verification reads the raw ingested file (raw/markdown or raw/pdf via pdfplumber), not the wiki summary page.

**Evidence.** The doc at claims-and-provenance.md:68 states verify_claim "opens the cited wiki/sources/<doc_id>.md" and searches it for locator_text. The actual implementation in verify_claim.py disagrees: verify_claim (line 57-58) calls _load_source_text, which (lines 29-41) loads the source manifest and then reads the RAW ingested file — for markdown it reads layout.raw_markdown / doc_name (lines 35-36), and for PDF it opens layout.raw_pdf / doc_name and re-extracts text via pdfplumber (lines 38-40). It never references wiki/sources/. Both the module docstring (line 1) and the CLI description (line 86) explicitly say the check runs "against raw/ files," corroborating the code over the doc. The misdescription is material: an operator debugging a failed verification per the doc would inspect the wrong directory (the wiki summary) instead of the raw source. The suggested fix (say it reads raw/markdown or raw/pdf via pdfplumber) matches the code exactly. This is static, no runtime needed.

**Citations.** skills/book-knowledge/references/claims-and-provenance.md:68 ("opens the cited wiki/sources/<doc_id>.md"); skills/book-knowledge/scripts/verify_claim.py:29-41 (_load_source_text reads raw_markdown/doc_name or raw_pdf/doc_name via pdfplumber); verify_claim.py:58 (calls _load_source_text(layout, span["doc_id"])); verify_claim.py:1 and :86 ("against raw/ files").


---

## `counter-claim-id-collision` — LOW

**Location:** `skills/book-knowledge/scripts/counter_claims.py:45` · **area:** counter-claim id generation · **confidence:** medium

**Finding.** next_counter_claim_id returns cc-YYYY-{token_hex(3)} without consulting existing ids, so within a single generate_for_claim loop (and across the ledger) two generated counter-claims can collide on id, and a collision would conflate two distinct rivals under latest-per-id dedup.

**Fix.** Check generated id against existing counter-claim ids (and ids minted earlier in the same batch) and regenerate on collision, or widen the random suffix.

**Evidence.** The cited code matches the claim exactly. next_counter_claim_id (counter_claims.py:45-50) returns f"cc-{year}-{secrets.token_hex(3)}" with no lookup of existing ids and no in-batch tracking; token_hex(3) is only 3 bytes (24 bits) of entropy. generate_for_claim (generate_counter_claims.py:53-66) calls next_counter_claim_id once per rival inside a loop and appends each record, again with no collision check across the batch or the ledger. The downstream consequence the claim describes is real: counter-claims are deduplicated by id via latest_per(..., "id") at propagate_belief.py:162, and latest_per is last-write-wins (io_utils.py:36-46), so two distinct counter-claims minted with the same id would collapse into one, silently dropping a distinct rival from belief propagation/damping. The claim only asserts that such a collision is possible and that, if it occurs, it conflates two rivals — both statements are accurate. The author self-rates severity "low," which is appropriate: a collision is improbable in practice (birthday-bound 50% chance needs ~4,800 counter-claims sharing the same year prefix; a single batch produces only a handful), but the claim does not overstate this. The bug is real and material to the closed-loop ledger's correctness invariant, not a stylistic nitpick. The suggested fix (regenerate on collision or widen the suffix) is sound.

**Citations.** C:/Users/charl/russellian-book-suite/skills/book-knowledge/scripts/counter_claims.py:45-50 (id generation, no existing-id consult); generate_counter_claims.py:53-66 (per-rival loop calls next_counter_claim_id with no dedup); io_utils.py:36-46 (latest_per is last-write-wins); propagate_belief.py:162 (counter-claims deduped via latest_per(..., "id") — the conflation site)


---

## `generate-counter-claims-skips-validation` — LOW

**Location:** `skills/book-knowledge/scripts/generate_counter_claims.py:73` · **area:** ledger append / provenance · **confidence:** high

**Finding.** generate_for_claim appends an updated claim record by writing raw JSON directly to the ledger, bypassing append_claim/validate_claim, so a malformed counter_claim_ids update (or a target record that no longer validates) can be written to the append-only ledger unchecked.

**Fix.** Route the updated record through ledger.append_claim so the schema validator runs before the write.

**Evidence.** The cited code at generate_counter_claims.py:69-74 builds an updated copy of the target claim record (adding new counter_claim_ids) and writes it to the ledger by opening layout.ledger in append mode and doing fh.write(json.dumps(updated, ...)). This is exactly the same low-level write that the canonical writer append_claim performs (ledger.py:45-46), except append_claim first calls validate_claim(record) (ledger.py:41-44), which runs jsonschema.validate against claim-record.schema.json (claim_validator.py:25-29). By going around append_claim, the function skips schema validation: the new counter_claim_ids list, or a target record that was read from the ledger but no longer conforms to the current schema, would be written to the append-only ledger unchecked. The code comment at lines 67-68 even states it is appending an updated claim record, confirming intent. The suggested fix (route through ledger.append_claim) is correct and trivial. The repo conventions (CLAUDE.md: append-only ledgers, schema discipline) make this a real correctness/provenance concern rather than a stylistic nitpick, consistent with the low severity assigned. No runtime observation was needed; the bypass is statically evident.

**Citations.** skills/book-knowledge/scripts/generate_counter_claims.py:69-74 (raw direct write to layout.ledger); skills/book-knowledge/scripts/ledger.py:40-46 (append_claim validates then writes the identical line); skills/book-knowledge/scripts/claim_validator.py:25-29 (validate_claim runs jsonschema against the schema)


---

## `d6-docstring-band-drift` — LOW

**Location:** `skills/book-qa/scripts/lint_artifact.py:10` · **area:** book-qa/lint_artifact docs · **confidence:** high

**Finding.** The module docstring states the D6 paragraph-variance cv band is [0.4, 1.1] but the actual default in lint_d6_paragraph_variance is (0.4, 1.2) (matching SKILL.md), so the docstring misreports the gate threshold.

**Fix.** Update the docstring on line 10 to read 'within-chapter cv outside [0.4, 1.2]'.

**Evidence.** The module docstring at line 10 documents the D6 paragraph-length variance band as "within-chapter cv outside [0.4, 1.1]", but the actual implementation in lint_d6_paragraph_variance (line 269) defaults cv_band to (0.4, 1.2). The runtime error message (line 286) interpolates the real band values, producing [0.4, 1.2], and SKILL.md line 72 also documents [0.4, 1.2]. So the docstring's upper bound of 1.1 is inconsistent with the code default, the emitted message, and the skill docs. The claim is true. It is a real (if low-severity) documentation drift: it misreports the gate threshold to anyone reading the module header, which is material for an operator-facing linter doc. The suggested fix (change to [0.4, 1.2]) is correct.

**Citations.** skills/book-qa/scripts/lint_artifact.py:10 (docstring "[0.4, 1.1]"); :269 (cv_band default (0.4, 1.2)); :286 (error msg uses cv_band[0]/cv_band[1]); skills/book-qa/SKILL.md:72 ("[0.4, 1.2]")


---

## `lint-supports-stale-comment` — LOW

**Location:** `skills/book-thesis/scripts/lint_supports.py:147` · **area:** lint-supports paragraph scan · **confidence:** high

**Finding.** The inline comment 'HTML comments do not start with "<" because we strip them first' is false — HTML-comment-carried blocks literally begin with '<!--' (start with '<') and are not pre-stripped; the code happens to work only because the COMMENT_RE.match guard rescues them, so the comment misleads future maintainers about the control flow.

**Fix.** Correct or remove the comment to reflect that '<'-prefixed blocks are kept only when COMMENT_RE matches the HTML-comment supports carrier.

**Evidence.** The inline comment at line 147 claims "HTML comments do not start with '<' because we strip them first." This is false. The HTML-comment supports carrier is defined by COMMENT_RE (line 95-97) as `^\s*<!--\s*supports:...`, i.e. blocks literally beginning with `<!--`. The only stripping applied to the block is `stripped = block.strip()` (line 145), which removes surrounding whitespace, NOT the `<!--` token — so an HTML-comment block's `stripped` value still starts with `<`. Consequently `stripped.startswith(("#","|","<",...))` at line 146 is True for HTML comments, and they DO enter the conditional; they are saved from the `continue` at line 149 only because `COMMENT_RE.match(stripped)` (line 148) succeeds. So the control flow is the opposite of what the comment describes: HTML comments do start with `<` and are not pre-stripped; they survive purely via the COMMENT_RE rescue guard. The comment actively misleads a maintainer about why the branch works. This is a genuine, material (if low-severity) documentation/correctness defect, matching the claim and suggested fix.

**Citations.** C:/Users/charl/russellian-book-suite/skills/book-thesis/scripts/lint_supports.py:95-97 (COMMENT_RE matches `^\s*<!--\s*supports:`), :145 (`stripped = block.strip()` — whitespace only), :146 (startswith includes `"<"`), :147 (the false comment), :148-149 (`if not COMMENT_RE.match(stripped): continue` — the actual rescue guard)


---

## `induce-popper-real-keyword-vs-string` — LOW · needs runtime verification

**Location:** `skills/neurosym-forge/scripts/induce_theory.cljs:160` · **area:** theory induction predicate typing · **confidence:** low

**Finding.** popper-search filters real-preds with (= (:return sig) :real), but load-schema reads booklogic-schema.edn whose :return for multi-valued sorts is stored as a vector [:vector T] and scalar returns may be read as keywords — if the schema serialized returns as strings/vectors the equality check silently yields zero real-preds and Popper emits nothing.

**Fix.** Normalize the :return read (handle keyword and [:vector/:set T] container) before the (= :real) test, mirroring booklogic return-inner-sort.

**Evidence.** popper-search filters real-valued predicates with a bare equality test `(= (:return sig) :real)` (induce_theory.cljs:160). The schema it reads, rules/booklogic-schema.edn, is emitted by emit-schema-edn-string (booklogic.cljs.tmpl:513-528), which preserves each predicate's :return VERBATIM. Per REQ-DSL-050/055 (booklogic.cljs.tmpl:192-208, 519-521), a return-sort is either a scalar keyword (:real) OR a one-layer container vector [:vector T] / [:set T]. The schema is loaded via edn/read-string (induce_theory.cljs:50-52, 84-86), which preserves keywords and vectors natively — so a predicate declared with return [:vector :real] is read as the vector [:vector :real], and the equality check `(= [:vector :real] :real)` is false. Such a predicate is genuinely real-valued but is silently excluded from real-preds, so Popper emits no approx= candidates for it. The booklogic side already defines and uses `return-inner-sort` (booklogic.cljs.tmpl:202-208, 254) to normalize exactly this container-vs-scalar distinction; popper-search fails to mirror it, which is the substance of the finding and matches the suggested fix. The claim is partly imprecise: it speculates returns "may be read as strings" — that path does not occur, since EDN keywords are preserved by read-string, not coerced to strings. But the vector/keyword mismatch it identifies is real, with a concrete supported example ([:vector :real]) confirmed in the booklogic test template (lines 224-230). Severity low is fair: it only bites verifiers that actually declare multi-valued real returns, and the failure is silent (zero/fewer real-preds) rather than a crash.

**Citations.** skills/neurosym-forge/scripts/induce_theory.cljs:160 (filter (= (:return sig) :real)); induce_theory.cljs:50-52 (read-edn-file uses edn/read-string); induce_theory.cljs:84-86 (load-schema reads booklogic-schema.edn); assets/project-template/cljs-orchestrator/src/main/__project__/booklogic.cljs.tmpl:192-208 (valid-return-sort? allows [:vector/:set T]; return-inner-sort normalizer); booklogic.cljs.tmpl:519-528 (emit-schema-edn preserves :return verbatim); assets/.../booklogic_test.cljs.tmpl:221-240 (real example: defpredicate :solutes [:solution] [:vector :real] → :return [:vector :real])


---

## `abstract-subject-run-line-and-paragraph-bound` — LOW

**Location:** `skills/russellian-style/scripts/lint_ai_staccato.py:210` · **area:** linters/ai-staccato · **confidence:** medium

**Finding.** _abstract_subject_run resets run state per paragraph and reports every run with the paragraph's start_line, so it misses runs that cross a paragraph break and gives identical (paragraph-start) line numbers to multiple distinct runs in one paragraph.

**Fix.** Track the per-sentence line offset for the run start and, if cross-paragraph runs are intended by the name, carry run_subj/run_len across paragraph iterations instead of resetting on each paragraph.

**Evidence.** Both sub-claims hold against the actual code. (1) Run state is reset per paragraph: _abstract_subject_run initializes run_subj=None and run_len=0 inside the `for start_line, text in paragraphs` loop (lines 221-222), so a run of same-subject sentences that crosses a paragraph break is never tracked across iterations — at the end of each paragraph any in-progress run is flushed (lines 242-245) and re-zeroed on the next paragraph. (2) Every finding is reported at the paragraph start_line: all three append sites (lines 230-232, 237-239, 242-245) pass `start_line`, and _abstract_run_finding stores it verbatim as `"line": para_start_line` (line 254). So two distinct runs occurring in the same paragraph both get the paragraph's first line, and the line never reflects the offset of the sentence where the run actually began. The issue is real and material (the `line` field is the author-facing pointer, and "consecutive sentences" runs spanning a paragraph break are silently missed), though correctly rated low/advisory — it is reporting-precision and edge-coverage degradation, not a crash or false positive. The suggested fix (track a per-sentence line offset for the run start, and decide whether cross-paragraph runs should carry state) directly addresses both observed defects.

**Citations.** skills/russellian-style/scripts/lint_ai_staccato.py:210-246 (function body, per-paragraph reset at 221-222, append sites at 230-232/237-239/242-245); :249-262 (_abstract_run_finding stores "line": para_start_line at 254)


---

## `concrete-density-single-run-only` — LOW

**Location:** `skills/russellian-style/scripts/lint_concrete_instance_density.py:69` · **area:** linters/concrete-instance-density · **confidence:** medium

**Finding.** The 'flagged' boolean stops after the first zero-instance run, so a document with multiple distinct dead zones reports only the first, and the avg<0.5 fallback is suppressed whenever any run fired even if other regions also lack instances.

**Fix.** Emit one finding per distinct zero-instance run (reset the flag when a non-zero paragraph breaks the run) rather than latching after the first.

**Evidence.** The primary claim is accurate. At line 64 `flagged` is initialized False, set True at line 83 after the first qualifying run, and never reset. The loop emit guard at line 69 is `i - run_start + 1 >= 3 and not flagged`, while line 85 resets `run_start = None` on any non-zero paragraph. So a document with two distinct dead zones (e.g. counts [0,0,0,5,0,0,0]) emits a finding only for the first run: at i=2 it fires and latches flagged=True; the second run starting at i=4 reaches length 3 at i=6 but is suppressed by `not flagged`. This is a real, material correctness limitation — the linter under-reports distinct zero-instance regions. The secondary part of the claim about the avg<0.5 fallback is technically true (line 88 uses `not findings`, so any emitted run suppresses the global-average fallback), but that suppression is arguably intentional non-double-reporting since the average check is a document-level fallback rather than a per-region check; it is the weaker/debatable half. The suggested fix (reset the flag when a non-zero paragraph breaks the run, emitting one finding per distinct run) correctly addresses the confirmed core defect. No runtime observation is needed — the latch behavior is fully determinable from the static control flow.

**Citations.** C:/Users/charl/russellian-book-suite/skills/russellian-style/scripts/lint_concrete_instance_density.py:64 (flagged=False init), :65-85 (loop: line 69 guard `>=3 and not flagged`, line 83 `flagged=True` never reset, line 85 `run_start=None` resets run but not flag), :88 (`if avg < 0.5 and not findings`)


---

## `hedges-titlecase-skip-too-broad` — LOW

**Location:** `skills/russellian-style/scripts/lint_hedges.py:29` · **area:** linters/hedges · **confidence:** medium

**Finding.** The AMBIGUOUS_TITLE_CASE skip fires for a capitalized hedge anywhere in a sentence, not just sentence-initial, so a genuinely hedging capitalized token (e.g. in title-case prose or after a colon) is silently dropped; also the whitelist entry 'tends' can never match because the rule list only contains 'tends to'/'tend to'.

**Fix.** Restrict the title-case skip to sentence-initial position (match.start()==0 within the sentence) and drop the dead 'tends' entry; rely on real surname/month proper-noun checks rather than blanket capitalization.

**Evidence.** Both sub-claims hold against the actual code. (1) Line 29 gates the skip solely on `lower in AMBIGUOUS_TITLE_CASE and matched_token[0].isupper()` with no positional check; `match.start()` is computed but only used for the column at line 36, never to restrict the skip to sentence-initial position. So any capitalized modal hedge (may/might/could/should/would) anywhere in a sentence — after a colon, in title-case prose, mid-fragment — is silently dropped, despite the line-30 comment intending only proper-noun/sentence-initial cases. (2) The 'tends' whitelist entry is dead: the regex is built only from rules['hedge_terms'] (line 18), and the rules file (assets line 8) contains 'tend to'/'tends to'/'tended to' but no standalone 'tends'. group(1) for the matching alternative is 'tends to', whose lowercase is 'tends to', never the bare 'tends', so `lower in AMBIGUOUS_TITLE_CASE` can never be true for that entry. The issue is a genuine correctness defect (false-negative hedge detections), though narrow in scope, consistent with the stated low severity. The suggested fix (gate on sentence-initial position and drop the dead entry) is sound.

**Citations.** skills/russellian-style/scripts/lint_hedges.py:12,18-22,26-37 (esp. line 29 skip with no start() guard; match.start() used only at line 36); skills/russellian-style/assets/russellian-rules.json:3-11 (hedge_terms has 'tend to'/'tends to'/'tended to', no standalone 'tends'); skills/russellian-style/scripts/lint_common.py:32-51 (iter_sentences yields per-sentence text fed to finditer)


---

## `no-shadow-writes-substring-false-positive` — LOW

**Location:** `ci/lint_no_shadow_writes.py:29` · **area:** ci no-shadow-writes · **confidence:** medium

**Finding.** _path_under_workspace_subdir flags any absolute path containing a component named raw/claims/wiki/graph anywhere (including unrelated dirs that happen to be so named), and _metabook_in_stack matches any filename substring 'syntopical-metabook', so the guard can both false-positive on incidental paths and, as an autouse open() monkeypatch, intercept every write in the whole pytest session.

**Fix.** Anchor the check to the resolved workspace root (only forbid <workspace>/raw, <workspace>/claims, etc.) rather than any path component match, and scope the autouse fixture to the metabook test package rather than the entire session.

**Evidence.** Both technical assertions in the claim are literally true in the code. _path_under_workspace_subdir (lines 28-33) resolves the path and does `any(p in _FORBIDDEN_DIRS for p in parts)`, i.e. it flags any absolute path with a component named raw/claims/wiki/graph anywhere, with no anchoring to a resolved workspace root — confirmed, and even exercised by the unit test which passes an unrelated tmp_path/raw and asserts True. _metabook_in_stack (lines 36-41) does a substring match `g in filename` over the lowercased frame filename, so any path containing 'syntopical-metabook'/'syntopical_metabook' matches. The fixture (lines 53-56) is `@pytest.fixture(autouse=True)` with no scope, and its own docstring says it patches builtins.open 'for every test in the session', so it does intercept every write wherever the plugin is loaded. The issue is real though low-severity: a spurious AssertionError requires BOTH the unanchored path match AND a metabook frame (the `and` on line 46), so the conjunction limits false positives, and the open() wrapper otherwise just re-delegates to _real_open with no behavior change. The unanchored component match and unscoped session-wide monkeypatch are genuine latent fragilities, and the suggested fix (anchor to workspace root, scope the fixture to the metabook package) is apt. This matches the claim's own 'low' severity, so it is confirmed rather than overstated.

**Citations.** ci/lint_no_shadow_writes.py:18-19 (_FORBIDDEN_DIRS, _GUARD_FRAMES), :28-33 (_path_under_workspace_subdir unanchored component match), :36-41 (_metabook_in_stack substring match), :44-50 (_guarded_open conjunction), :53-56 (autouse session-wide fixture + docstring); ci/test_no_shadow_writes.py:24-30 (test passes unrelated tmp_path/raw, asserts True, demonstrating no workspace anchoring)


---

## `append-index-entry-id-redundant-reconstruct` — LOW

**Location:** `tools/build-russell-corpus/scripts/append_to_index.py:20` · **area:** build-russell-corpus append · **confidence:** medium

**Finding.** _project_candidate_to_index_entry splits candidate_id on '-' and rejoins it as f'{source_id}-{numeric_suffix}', which simply reproduces the original candidate_id unless it contained no hyphen; the split/rejoin is dead manipulation and would silently corrupt IDs whose numeric suffix is not the final segment.

**Fix.** Use cand['candidate_id'] directly for id and derive source from the allow-list / source_id field rather than reconstructing it by string surgery on the id.

**Evidence.** The cited code (append_to_index.py:20-26) splits candidate_id on '-', takes the last segment as numeric_suffix and rejoins the rest as source_id, then sets id = f"{source_id}-{numeric_suffix}". Given any candidate_id containing at least one hyphen, this rejoin is an identity transform: it reproduces the original candidate_id exactly, so using it for "id" is dead string manipulation (cand['candidate_id'] would be equivalent). That half of the claim is exactly right. More materially, the same surgery is used for the "source" field, and it is WRONG for the project's real multi-segment sources. The PD allow-list (assets/pd-allow-list.yaml:11,14,17,20) defines source_ids like external-world, analysis-mind, free-thought, political-ideals, marriage-morals. The fat candidate carries an explicit "source_id" field (extractor-prompt.md:25; fixtures), and cross_check.py:102 writes the full candidate (including source_id) to verified.jsonl. But _project_candidate_to_index_entry ignores cand['source_id'] and instead reconstructs source from candidate_id. For the real fixture quoting_hume.json (candidate_id "external-099", source_id "external-world"), the reconstruction yields source="external" — diverging from the true allow-list source_id "external-world". So the committed index entry's source is silently corrupted whenever the candidate_id prefix is a single token while the actual source_id is multi-token. The suggested fix (use cand['candidate_id'] directly and read source from the explicit source_id field) is correct and the explicit field is already present. The only imprecision in the claim is the phrase "silently corrupt IDs whose numeric suffix is not the final segment": the id itself is never corrupted (rejoin is identity), and even for ids like "problems-001-dup" the id is preserved; the corruption actually lands on the source field. Despite that mislabeling of which field breaks, the defect described (dead reconstruct + reconstruction-by-surgery that should use the explicit source_id) is real, reproducible from committed fixtures, and material.

**Citations.** tools/build-russell-corpus/scripts/append_to_index.py:18-31 (split/rejoin for id and source); assets/pd-allow-list.yaml:11,14,17,20 (multi-segment source_ids external-world/analysis-mind/free-thought/political-ideals/marriage-morals); assets/extractor-prompt.md:24-25 (candidate carries both candidate_id and explicit source_id); tools/build-russell-corpus/tests/fixtures/candidates/quoting_hume.json:2-3 (candidate_id "external-099" vs source_id "external-world" — reconstructed source="external" is wrong); tools/build-russell-corpus/scripts/cross_check.py:102 (verified.jsonl receives the full candidate including source_id, which append_to_index then ignores)


---

## `readme-full-lint-crashes-on-missing-voice` — LOW

**Location:** `tools/readme-lint/scripts/lint_readme.py:243` · **area:** tools readme-lint · **confidence:** high

**Finding.** The lefthook/Makefile readme-lint command runs run_full_lint over the whole README, and parse_readme raises ValueError on any H2 section lacking a '<!-- voice: -->' declaration, so the pre-commit hook crashes with a traceback (not a clean lint failure) the moment a new section is added without a voice tag.

**Fix.** Catch ValueError in main()'s full-lint path and emit a clear 'section X missing voice declaration' error with a nonzero exit code, mirroring the --section path's error handling.

**Evidence.** The claim is accurate. The lefthook hook (lefthook.yml:24) and Makefile target (Makefile:55) both invoke `python -m scripts.lint_readme` with no `--section` argument, so `main()` falls through to the full-lint branch at line 243: `results, exit_code = run_full_lint(args.readme)` with no surrounding try/except. `run_full_lint` (line 207) calls `parse_readme`, whose inner `flush()` raises `ValueError(f"Section without voice declaration: ...")` at line 121 whenever an H2 section has no `<!-- voice: -->` tag. So adding any voice-less section makes the hook abort with an uncaught ValueError traceback. This is in clear contrast to the `--section` path (lines 232-239), which wraps `parse_single_section` in try/except for both LookupError and ValueError and returns a clean exit code 2 with an "ERROR: ..." message. The asymmetry the finding describes is real and the suggested fix (mirror the --section error handling in the full-lint path) is appropriate. Note the impact is bounded: because `main()` is wrapped in `raise SystemExit(main())` and the exception propagates, the process still exits nonzero, so the commit is still blocked — the defect is the ugly traceback / poor error message rather than a gate that silently passes. That matches the finding's stated "low" severity and its own wording ("crashes with a traceback (not a clean lint failure)"). Confirmed statically; no runtime needed.

**Citations.** C:/Users/charl/russellian-book-suite/tools/readme-lint/scripts/lint_readme.py:243 (full-lint path, no try/except); :207-210 (run_full_lint calls parse_readme); :119-121 (flush raises ValueError on missing voice); :230-242 (--section path catches LookupError/ValueError, returns 2); :248-249 (raise SystemExit(main())). C:/Users/charl/russellian-book-suite/lefthook.yml:22-24 (hook runs lint_readme with no --section). C:/Users/charl/russellian-book-suite/Makefile:54-55 (readme-lint target, no --section).


---

## `hedges-col-multiline-offset` — INFO

**Location:** `skills/russellian-style/scripts/lint_hedges.py:36` · **area:** linters/hedges · **confidence:** medium

**Finding.** col is computed as sentence.col + match.start(), which is only correct when the matched token is on the same physical line as the sentence start; for a sentence spanning multiple wrapped lines the reported column is wrong.

**Fix.** Resolve the match's line/col from the absolute offset within the paragraph (as lint_common._resolve_line_col does) rather than adding an intra-sentence char offset to the sentence's starting column.

**Evidence.** The claim is true and the issue is real. In lint_hedges.py:36 the column is computed as `sentence.col + match.start()`, where `sentence.col` is the 1-indexed column of the sentence's start (resolved correctly by lint_common._resolve_line_col, which accounts for newlines) and `match.start()` is the char offset of the hedge token within the stripped sentence text. lint_common._split_paragraphs joins consecutive non-blank source lines with "\n" (lint_common.py:71), so a paragraph — and a single sentence within it — can contain embedded newlines (wrapped source). When a hedge token sits on a continuation line, the correct behavior (as _resolve_line_col does at lint_common.py:101-108) is to bump the line by the number of intervening newlines and reset the column relative to the last newline. The naive addition at line 36 does neither: it leaves the reported `line` pinned to the sentence's start line and lets `col` accumulate monotonically past the physical line width, so both line and col are wrong for any multi-line-spanning sentence. The other linters that consume iter_sentences (lint_passive_voice.py:34, lint_signal_density.py:62) avoid the problem by reporting only sentence.col; lint_hedges is the lone offender. The suggested fix (resolve from the absolute paragraph offset via _resolve_line_col rather than adding an intra-sentence offset to the sentence column) is the correct remedy, though it requires the linter to retain the sentence's absolute paragraph char offset, which iter_sentences does not currently expose. Severity "info" is appropriate: it only degrades the accuracy of a lint report's location, not correctness of detection.

**Citations.** skills/russellian-style/scripts/lint_hedges.py:36 (col = sentence.col + match.start()); lint_common.py:50-51 (sentence start line/col via _resolve_line_col); lint_common.py:70-71 (paragraphs join lines with "\n"); lint_common.py:101-108 (_resolve_line_col handles embedded newlines); lint_passive_voice.py:34 and lint_signal_density.py:62 (sibling linters report only sentence.col)


---
