# Uncertain & runtime-dependent findings

These were raised but could not be confirmed by static analysis alone — most require running the Nix/Linux CI or the test suite, which this review did not do. Treat them as leads, not confirmed defects.

## `verdict-defaults-approved-fail-open` — MEDIUM (correctness)

**Location:** `skills/book-review/scripts/dispatch_review.py:101`

**Claim.** A review report missing the verdict field defaults to 'APPROVED', a fail-open default that can mask a persona that failed to emit a verdict.

**Why uncertain.** The literal claim is accurate: dispatch_review.py:101 does `verdict=meta.get("verdict", "APPROVED")`, a fail-open default, and parse_review_report (lines 81-108) does not enforce the schema's required `verdict` field (review-report.schema.json:5,10), so a report omitting verdict silently reads as APPROVED. However, the claimed materiality is overstated. The parsed `verdict` string only flows into `per_persona_verdicts` (aggregate_reviews.py:65, 95-102), which is rendered into an informational table in persona-review.md and copied into verdict.json. The actual release gate in review-conductor's aggregate_panel.py (lines 39-79) computes pass/soft-gate-fail purely from severity counts of findings (gating vs advisory criticals), NOT from the per-persona verdict string. So a missing verdict produces a misleading "APPROVED" in a report table but cannot mask a gate failure — the gate never consults the string. The bug is therefore real but cosmetic/reporting-level (low severity), not the medium-severity gate-masking defect the claim describes. Because the claim's core defect (the default exists and fail-open) is confirmed while its stated impact/severity mechanism is wrong, and judging whether this rises to a "real and material" issue versus stylistic depends on how one weighs misleading-report vs gate-masking, I return uncertain rather than confirmed or refuted.


---

## `opaque-fallback-divergence` — MEDIUM (correctness)

**Location:** `verifiers/bermuda/cljs-orchestrator/src/main/bermuda/nl_to_fol.cljs:47`

**Claim.** bermuda's legacy ?other fallback returns {:kind :symbol :sort :formula} with no :name while adsc-clinical (and bermuda's own event path) tag it :name :OPAQUE, so downstream OPAQUE-fraction gates that key on :name :OPAQUE will undercount unmatched claims from the legacy branch.

**Why uncertain.** The structural half of the claim is literally true: bermuda's legacy ?other fallback at nl_to_fol.cljs:47 returns {:kind :symbol :sort :formula} with NO :name, whereas bermuda's own unknown-event branch (line 78) and adsc-clinical's ?other branch (adsc_clinical/nl_to_fol.cljs:34) both emit :name :OPAQUE. The test unknown-event-head-emits-opaque (nl_to_fol_test.cljs:117-123) even asserts the event branch matches "the legacy ?other branch," yet the legacy branch is missing the :name those others carry, so the two bermuda paths are genuinely divergent and the OPAQUE marker is inconsistent. That part of the finding holds. However, the claimed material harm — that "downstream OPAQUE-fraction gates that key on :name :OPAQUE will undercount unmatched claims from the legacy branch" — is not supported by the code. The only OPAQUE-fraction gate is _extract_preview_lib.run (verifiers/bermuda/scripts/_extract_preview_lib.py:60-65), which counts atoms produced by the Python ingest_ledger._claim_to_atom path; that Python path correctly stamps Keyword("OPAQUE") at ingest_ledger.py:333. The cljs nl_to_fol.cljs output is a separate pipeline: translate-corpus feeds phases/verify -> bridge/verify-formulas (the Rust SMT verifier) under a malli ir/Formula contract (phases.cljs:11-19), and a grep of the entire cljs-orchestrator shows no OPAQUE-fraction gate consuming the formula stream. So the specific undercount mechanism in the claim cannot fire through the asserted gate. The fix (adding :name :OPAQUE for consistency with the sibling copy and the event branch) is reasonable, but whether any real consumer counts the cljs legacy fallback's :name depends on the Rust verifier / unobserved downstream that I cannot inspect statically, so I cannot confirm material correctness impact. Verdict: uncertain — true divergence, but the stated harm is not demonstrably real against the cited gate.


---

## `posix-file-url-malformed` — LOW (correctness)

**Location:** `skills/book-compose/scripts/print_pdf.py:35`

**Claim.** The file URL is built as 'file:///' + resolved path; on POSIX a resolved path already starts with '/', producing the malformed 'file:////home/...' (four slashes), so PDF render on Linux/macOS may fail to load the HTML.

**Why uncertain.** The cited line is exactly as claimed. On POSIX, `Path.resolve()` returns an absolute path already prefixed with a single `/` (e.g. `/home/user/manuscript.html`), and the `.replace("\\","/")` call is a no-op there, so concatenating `"file:///"` yields `file:////home/user/manuscript.html` with four slashes — a non-canonical file URI per RFC 8089, where the path is parsed as `//home/...` (an empty authority followed by a network-path-like reference). The static portion of the claim (malformed four-slash URI on POSIX) is unambiguously true from reading the code, and the suggested fix `Path(html_path).resolve().as_uri()` is the correct platform-agnostic construction (it also correctly handles Windows drive letters and percent-encodes spaces/special chars, which the current string concatenation does not). The Windows path used in this repo works fine because the resolved path starts with a drive letter (`C:/...`) giving the correct `file:///C:/...`. However, whether Chromium/Playwright actually fails to LOAD the four-slash URL on Linux/macOS is the load-bearing materiality question, and that is runtime behavior I cannot observe statically — many URL parsers (including some Chromium versions) tolerantly normalize `file:////` to `file:///`. The finding itself flags `needs_runtime_verification: true`. Because the real impact (render failure vs. silent tolerance) hinges on unobservable runtime behavior, I return uncertain rather than confirmed.


---

## `competency-query-name-collision` — LOW (correctness)

**Location:** `skills/book-knowledge/scripts/run_competency_queries.py:89`

**Claim.** findings is keyed by query stem only (not by class), so two .rq files sharing a stem across coverage/consistency/defeasible dirs silently overwrite each other's results, and a defeasible fire can be masked by a same-named non-defeasible query.

**Why uncertain.** The mechanical core of the claim is true: at line 89, `findings[name] = rows` keys results by query stem (`f.stem`) only, discarding the `cls` from the `(cls, name, query_path)` tuple produced by `discover_queries` (lines 24-37). So two `.rq` files sharing a stem across coverage/consistency/defeasible would overwrite each other in the `findings` dict, and downstream consumers that read by stem (e.g. book_preflight.py:73-74 reads `findings["unsupported_claims"]` and `findings["contradiction_scan"]`) would see the wrong rows. That part of the finding holds. However, the claim is materially wrong on two counts that bear on severity. (1) The specific harm asserted — "a defeasible fire can be masked by a same-named non-defeasible query" — is false. The defeasible warning/blocking logic (lines 91-103) operates on the local `rows` of the iteration where `cls == "defeasible"`, appends to a `warnings` LIST (not a dict) and to `hard_failures`, and raises RuntimeError at line 128 entirely independently of the `findings` dict. A stem collision cannot suppress a defeasible escalation. Moreover discovery order is coverage→consistency→defeasible→flat, so a defeasible stem would overwrite a non-defeasible one in `findings`, the reverse of the claimed direction. (2) Crucially, the issue is purely latent: the actual asset tree has zero stem collisions across the three class dirs (coverage uses snake_case like unsupported_claims/contradiction_scan; defeasible uses kebab-case like rebuttal-presence). So no current overwrite occurs. The finding is thus a real latent design fragility (correct that the key should be namespaced or uniqueness asserted, matching the suggested fix), but its stated impact is mischaracterized and there is no present-day defect. Because confirming the claim as written would endorse an inaccurate causal mechanism, while flatly refuting it would deny the genuine latent keying weakness, I return uncertain.


---

## `aggregate-output-nondeterministic-timestamp` — LOW (correctness)

**Location:** `skills/book-review/scripts/aggregate_reviews.py:82`

**Claim.** persona-review.md embeds datetime.now(timezone.utc) on every run, so the aggregated panel output is not byte-reproducible even when inputs are identical.

**Why uncertain.** The factual half of the claim is verified: aggregate_reviews.py:82 writes `_Aggregated {datetime.now(timezone.utc).isoformat(...)}_` into persona-review.md, so identical review inputs yield byte-different output across runs (only the timestamp line differs). That part is unambiguously true. Whether this is a real and material issue is genuinely unclear. On one hand, the suite demonstrably values byte-determinism in comparable artifacts (the syntopical positions.edn writer is explicitly "byte-deterministic" with dedicated test_write_is_byte_deterministic / test_byte_deterministic tests). On the other hand, nothing scopes that contract to this file: no SKILL.md, spec, or test for aggregate_reviews asserts byte-reproducibility — the three write-path tests (test_aggregate_reviews.py:38-46) check only substring presence, and persona-review.md is a human-facing editorial summary under chapters/drafts/, not a content-hashed artifact or append-only ledger row. The "Aggregated <time>" stamp is also semantically legitimate (records when aggregation ran), and the suggested fix of deriving it from latest reviewed_at would discard real information. So the claim is literally true but its severity hinges on an unstated intent — is byte-reproducibility a requirement for this specific output? I cannot establish that from the code; the determinism evidence in the repo points at other modules, not this one. Hence uncertain rather than confirmed (the defect is real-but-arguably-immaterial) or refuted (the embedded now() is genuinely there).


---

## `multiline-findings-split` — LOW (correctness)

**Location:** `skills/book-review/scripts/dispatch_review.py:70`

**Claim.** _parse_findings_section iterates physical lines and treats every marker-prefixed line as a separate Finding, so a single finding spanning multiple bulleted/numbered sub-points is counted as several findings, inflating severity counts.

**Why uncertain.** The code description in the claim is literally accurate: `_parse_findings_section` (dispatch_review.py:70-78) iterates `section_body.splitlines()` and appends one `Finding` for every physical line beginning with a list marker (`- `, `* `, `1.`...`9.`), with no logic to fold continuation or nested sub-bullet lines into the preceding finding. So if a finding were authored across multiple marker-prefixed lines, the parser would over-count, and since parse_review_report derives critical/important/minor counts from list lengths (lines 88-90) rather than the frontmatter *_count fields, that over-count would surface. HOWEVER, whether this is a real/material defect depends entirely on reviewer output that the contract forbids: the persona-prompt-template (lines 42-50) mandates "this exact structure" with each finding as a single top-level list line (`1. **<line ref>:** <finding> — <required action>`), and there is no nested-list construct in the template. The test fixture (test_dispatch_review.py:48-56) confirms the expected one-line-per-finding shape. So the inflation only occurs when a subagent violates the documented single-line format — a runtime/LLM-output behavior I cannot observe statically. The suggested fix's second branch ("document that each top-level list item is one finding") is already effectively satisfied by the template. This sits at the fragile-parser boundary: the mechanism is real but materiality hinges on out-of-contract LLM output I cannot confirm, so I cannot rate it a confirmed material bug nor cleanly refute the described mechanism.


---

## `ci-legacy-npm-install-defeats-ci` — LOW (cicd)

**Location:** `.github/workflows/ci-legacy.yml:281`

**Claim.** cljs-bermuda-test sets cache: npm keyed on package-lock.json but then runs 'npm install' (not 'npm ci'), which can rewrite the lockfile and silently drift dependencies versus the locked set, so the lockfile-cache key and the actually-installed deps can diverge and the job no longer validates the committed lockfile.

**Why uncertain.** The static facts of the claim are confirmed: setup-node caches npm keyed on verifiers/bermuda/package-lock.json (lines 270-271) and the install step runs `npm install --no-audit --no-fund`, not `npm ci` (line 281). The code comment at lines 278-280 explicitly documents this as a deliberate choice: the bermuda lockfile drifts from package.json across in-flight PRs and `npm ci` strict-fails there, so `npm install` is used while the cache key still references the lockfile. The claim's core assertion — that `npm install` "can rewrite the lockfile and silently drift dependencies" so the lockfile-keyed cache and installed deps diverge — is a runtime-dependent statement: whether `npm install` actually mutates the lockfile depends on the in-repo sync state of package-lock.json vs package.json at job time, which cannot be observed from the workflow file alone. Additionally, the framing that the job "no longer validates the committed lockfile" mischaracterizes the job's purpose: cljs-bermuda-test is a shadow-cljs compile + node test job, not a lockfile-validation gate, and the maintainer documented the tradeoff intentionally. The cache-reliability concern is technically plausible but low-impact and already acknowledged in-code, making this closer to restating a documented design decision than surfacing an undocumented defect. Because the material consequence (actual lockfile rewriting/drift) hinges on runtime repo state that is not statically determinable, the correct verdict is uncertain.


---
