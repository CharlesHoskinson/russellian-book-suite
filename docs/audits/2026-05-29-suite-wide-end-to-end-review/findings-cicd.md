# CI/CD health — findings

16 confirmed findings. Each survived an independent adversarial-verify pass; the evidence line cites code that was opened and read.

## `branch-protection-check-names-stale` — CRITICAL · needs runtime verification

**Location:** `docs/operations/branch-protection.md:11` · **area:** branch-protection / required status checks · **confidence:** high

**Finding.** The required status-check contexts (lint, scaffold-bake, regression (sprint-5), verifier (bermuda), verifier (osmotic-pressure)) are the OLD split-job names and no longer match any job emitted by ci.yml, which collapsed them into a single 'nix preflight' job plus 'cargo-test (...)' legs, so these required checks can never report and block all merges (or, if not enforced, gate on nothing).

**Fix.** Update both docs/operations/branch-protection.md and scripts/ruleset-apply.sh required_status_checks to the actual ci.yml job names: 'nix preflight (lint + bake + regression + verifiers)' and the per-leg 'cargo-test (...)' / 'python-skill (...)' contexts, or rely solely on the 'ci required ✓' aggregate; remove the dead context names.

**Evidence.** The cited file docs/operations/branch-protection.md lines 11-15 lists five required status-check contexts (lint, scaffold-bake, regression (sprint-5), verifier (bermuda), verifier (osmotic-pressure)). The current .github/workflows/ci.yml emits NONE of these names. Its actual job `name:` values are: 'detect rust/nix changes', 'python-skill (...)', 'nix preflight (lint + bake + regression + verifiers)', 'cargo-test (...)', 'ci divergence summary', and 'ci required ✓'. The ci.yml comment at lines 125-129 explicitly documents that the original five split jobs (lint, scaffold-bake, regression, verifier-bermuda, verifier-osmotic) were intentionally collapsed into the single 'preflight' job to halve wall-time and avoid cache contention — exactly the rename the claim describes. The same five stale contexts are also hard-coded in scripts/ruleset-apply.sh lines 41-45 with strict_required_status_checks_policy=true (line 39), so the ruleset actually applied to main requires checks that no longer report. With strict mode active these dead contexts would block merges (they never reach success). The only required context that still matches a real job is 'ci required ✓' (ci.yml line 229 / docs line 16 / script line 46). The 'needs_runtime_verification' flag is satisfied statically here: GitHub's reported check context equals the job's `name:`, and the mismatch is unambiguous from the code alone. This is a real, material CI-gating defect, not a stylistic nit; severity critical is justified and the suggested fix (update both files to real job names or rely on the 'ci required ✓' aggregate) is correct.

**Citations.** docs/operations/branch-protection.md:11-16 (required contexts lint/scaffold-bake/regression (sprint-5)/verifier (bermuda)/verifier (osmotic-pressure)/ci required ✓); .github/workflows/ci.yml:132 ('nix preflight (lint + bake + regression + verifiers)'), ci.yml:57 ('python-skill (...)'), ci.yml:154 ('cargo-test (...)'), ci.yml:229 ('ci required ✓'), ci.yml:125-129 (comment documenting the 5→1 job collapse); scripts/ruleset-apply.sh:39-46 (strict_required_status_checks_policy true + the same five stale contexts hard-coded).


---

## `ruleset-apply-stale-contexts` — CRITICAL · needs runtime verification

**Location:** `scripts/ruleset-apply.sh:40` · **area:** branch-protection ruleset script · **confidence:** high

**Finding.** ruleset-apply.sh hard-codes required_status_checks contexts 'lint','scaffold-bake','regression (sprint-5)','verifier (bermuda)','verifier (osmotic-pressure)' that ci.yml never produces, so applying the ruleset configures GitHub to wait forever on checks that will never post.

**Fix.** Replace the required_status_checks array with the live ci.yml job names (or just '{ "context": "ci required ✓" }'), since 'ci required ✓' already aggregates preflight/python-skill-matrix/cargo-test results.

**Evidence.** The ruleset at scripts/ruleset-apply.sh lines 40-47 hard-codes required_status_checks contexts "lint", "scaffold-bake", "regression (sprint-5)", "verifier (bermuda)", "verifier (osmotic-pressure)" (plus "ci required ✓"). GitHub status-check contexts are the job display names. ci.yml's actual jobs emit the names: "detect rust/nix changes", "python-skill (...)", "nix preflight (lint + bake + regression + verifiers)" (preflight), "cargo-test (...)", "ci divergence summary", and "ci required ✓" — none of which are "lint", "scaffold-bake", "regression (sprint-5)", "verifier (bermuda)", or "verifier (osmotic-pressure)". The ci.yml comment at lines 125-129 explicitly documents the history: "Originally split into 5 jobs (lint, scaffold-bake, regression, verifier-bermuda, verifier-osmotic) ... Collapsing to one job halves wall-time" — confirming those 5 contexts were removed and folded into the single preflight job. Because strict_required_status_checks_policy is true (line 39) and a merge_queue is configured (lines 50-61), GitHub will wait indefinitely for the 5 contexts that will never post, blocking all merges to the default branch. The issue is real and material (critical). Minor imprecision in the claim: the script already also lists the correct aggregate "ci required ✓" at line 46, so the fix is to drop the 5 stale entries rather than add the aggregate — but the stale entries alone are sufficient to permanently block merges, and the suggested fix (collapse to "ci required ✓", which already aggregates preflight/python-skill-matrix/cargo-test per lines 228-244) is correct.

**Citations.** scripts/ruleset-apply.sh:39-47 (strict policy + the 5 stale contexts + ci required ✓); .github/workflows/ci.yml:56-57,131-132,153-154,183,228-229 (actual job names); .github/workflows/ci.yml:125-129 (comment confirming the 5 old jobs lint/scaffold-bake/regression/verifier-bermuda/verifier-osmotic were collapsed into preflight); scripts/ruleset-apply.sh:50-61 (merge_queue makes blocked checks fatal to merges)


---

## `ci-extra-skips-all-linters` — HIGH · needs runtime verification

**Location:** `skills/russellian-style/tests/conftest.py:19` · **area:** ci/test-gating · **confidence:** high

**Finding.** The [ci] extra installs spaCy but not the en_core_web_sm model, so _spacy_model_available() returns False and conftest collect_ignore_glob silently skips every test_lint_*/test_style_pass_*/integration test — CI passes without ever exercising the linters.

**Fix.** Either download the model in CI (python -m spacy download en_core_web_sm) before pytest, or fail loudly (not silently skip) when the model is absent in a CI context, so the linter suite is actually run.

**Evidence.** The claim holds against the actual code. conftest.py:8-26 defines _spacy_model_available() which returns False unless spacy.load("en_core_web_sm") succeeds, and on False sets collect_ignore_glob to skip every test_lint_*.py (13 files), test_style_pass_*.py, test_bitcoin_samples.py, test_skill_integration.py, and unit/test_skill_api.py — a pytest hook that silently drops those files from collection (no skip markers, no warning). The CI path makes the model genuinely absent: .github/actions/setup-book-python/action.yml:24-28 installs only `pip install -e skill[ci]`; ci.yml:90 passes extra default 'ci'; the pytest step (ci.yml:111-123) never runs `python -m spacy download`. pyproject.toml:16-24 confirms the [ci] extra installs spacy but the comment explicitly states it "intentionally omits spacy model (en_core_web_sm); conftest skip-gate handles missing model." The linter scripts that the skipped tests import (e.g. lint_passive_voice, lint_signal_density, lint_parallel_structure, lint_ai_staccato, lint_common, lint_concrete_instance_density) call spacy.load("en_core_web_sm"), so without the model those tests cannot run and the model is never present in CI. Net effect: the russellian-style python-skill-matrix leg passes green while collecting zero linter tests — the linter suite is never exercised in CI, and the green check is misleading. This is a real, material CI-gating gap, not a stylistic nitpick. The only nuance: the test files are dropped from collection rather than reported as "skipped", so they are invisible (worse than the claim's "skips"), and a handful of non-linter tests still run, so the job isn't fully empty — but the entire linter coverage is silently absent, matching the claim's substance.

**Citations.** skills/russellian-style/tests/conftest.py:8-26 (gate + collect_ignore_glob); skills/russellian-style/pyproject.toml:16-24 ([ci] extra omits model, intentional comment); .github/actions/setup-book-python/action.yml:24-28 (installs [ci], no model download); .github/workflows/ci.yml:90,111-123 (extra='ci' default, pytest step with no spacy download); skills/russellian-style/tests/test_lint_passive_voice.py:1-30 and Grep hit list showing scripts/lint_*.py call spacy.load("en_core_web_sm")


---

## `dependabot-missing-osmotic-cargo` — MEDIUM

**Location:** `.github/dependabot.yml:23` · **area:** dependabot coverage · **confidence:** high

**Finding.** Dependabot watches cargo for verifiers/bermuda/rust-verifier but not verifiers/osmotic_pressure/rust-verifier, even though osmotic_pressure has its own Cargo.lock and is built/tested by ci.yml cargo-test and ci-legacy osmotic-pressure-smoke, leaving its Rust deps un-updated and unmonitored for advisories.

**Fix.** Add a cargo dependabot entry for directory /verifiers/osmotic_pressure/rust-verifier with a weekly interval.

**Evidence.** The cited file .github/dependabot.yml has exactly one cargo entry (line 23-24) pointing at /verifiers/bermuda/rust-verifier, with no entry for /verifiers/osmotic_pressure/rust-verifier. Every supporting fact in the claim checks out: verifiers/osmotic_pressure/rust-verifier/Cargo.lock exists; ci.yml's cargo-test job matrix (line 162) includes osmotic_pressure and runs cargo test against verifiers/osmotic_pressure/rust-verifier/Cargo.toml (line 176); and ci-legacy.yml's osmotic-pressure-smoke job (line 395) does cargo build --features smt in that same crate (lines 443-444). So a crate that is actively built and tested in CI, with a committed lockfile, is not monitored by Dependabot for dependency updates or advisories. This is a real, material coverage gap, not a stylistic nitpick. (Note: epidemiology and adsc-clinical rust-verifiers also lack cargo entries, so the gap is broader than just osmotic_pressure, but that does not weaken the specific claim.) The suggested fix — add a weekly cargo entry for /verifiers/osmotic_pressure/rust-verifier — is correct.

**Citations.** .github/dependabot.yml:23-24 (only bermuda cargo entry); verifiers/osmotic_pressure/rust-verifier/Cargo.lock (exists per Glob); .github/workflows/ci.yml:162 (matrix verifier includes osmotic_pressure), ci.yml:176 (cargo test on its Cargo.toml); .github/workflows/ci-legacy.yml:395 (osmotic-pressure-smoke job), ci-legacy.yml:443-444 (cargo build --features smt)


---

## `budget-missing-comment-file` — MEDIUM · needs runtime verification

**Location:** `.github/workflows/ci-budget.yml:33` · **area:** ci-budget workflow · **confidence:** high

**Finding.** When there are no green runs in the window the Python step prints a message and exits 0 without writing comment.md, but the unconditional 'post PR comment' step then runs 'gh pr comment --body-file comment.md', which fails because the file does not exist, turning an empty window into a spurious red budget check.

**Fix.** Write a fallback comment.md in the no-green-runs branch before SystemExit, or guard the post step with 'if: hashFiles('comment.md') != ''' / test -f comment.md.

**Evidence.** The "compute" step at .github/workflows/ci-budget.yml:33-35 takes an early `raise SystemExit(0)` when there are no green runs (`if not durations`), after only `print("no green runs in window")`. The `comment.md` write happens later at lines 43-47, which is skipped in that branch, so no file is produced. The subsequent "post PR comment" step (lines 49-51) is guarded only by `if: github.event_name == 'pull_request'` (line 50) and unconditionally runs `gh pr comment ... --body-file comment.md` (line 51) with no file-existence check. On a pull_request event (the workflow's primary trigger, lines 3-4) with an empty green-run window, comment.md is absent and `gh pr comment --body-file comment.md` fails, turning a degenerate-but-valid empty window into a red budget check. The exit-0 plus missing-file-plus-unguarded-consumer chain is statically determinable; this is a real, material CI correctness bug, not a stylistic nitpick. The suggested fixes (write a fallback comment.md before SystemExit, or guard the step with hashFiles('comment.md')!='' / test -f) are appropriate.

**Citations.** .github/workflows/ci-budget.yml:33-35 (no-green-runs early SystemExit(0), no comment.md write); :43-47 (comment.md written only in the populated branch); :49-51 (post step guarded only by github.event_name=='pull_request', runs gh pr comment --body-file comment.md unconditionally); :3-4,:13 (pull_request trigger conditions).


---

## `adsc-missing-cargo-lock` — MEDIUM

**Location:** `verifiers/adsc-clinical/rust-verifier/Cargo.toml:0` · **area:** build / dependency pinning (adsc-clinical) · **confidence:** high

**Finding.** adsc-clinical/rust-verifier ships no Cargo.lock (bermuda does), so the same caret/range dependencies (napi 3, z3 0.20, cozo 0.7, egg 0.10) can resolve to different transitive versions than the locked bermuda build, undermining the reproducibility the rayon ~1.10 cap comment is trying to guarantee.

**Fix.** Commit a Cargo.lock for the adsc-clinical verifier (it is a binary/cdylib crate, so the lockfile should be tracked) and verify it resolves the same z3/cozo/graph_builder versions as bermuda.

**Evidence.** Every factual assertion in the claim checks out against the repo. adsc-clinical/rust-verifier ships only Cargo.toml, build.rs, src/ — no Cargo.lock exists anywhere under verifiers/adsc-clinical (Glob for **/Cargo.lock returns nothing), while bermuda, epidemiology, and osmotic_pressure all track a Cargo.lock. The two Cargo.toml files are essentially identical in their dependency set, declaring the same caret/range deps (napi 3, z3 0.20, cozo 0.7, egg 0.10) plus the rayon ~1.10 cap with an identical reproducibility-motivated comment. bermuda's tracked lock pins cozo 0.7.6, graph_builder 0.4.1, rayon 1.10.0, z3 0.20.0; without its own lock, adsc-clinical's `cargo build` resolves these caret deps freshly and can pick up newer compatible transitives (e.g. a future cozo 0.7.x pulling graph_builder >0.4.1), exactly the drift the rayon cap comment is trying to prevent. The identical .gitignore in both dirs (ignores only target/, work/, etc. — not Cargo.lock) confirms the omission is an oversight, not an intentional policy, so bermuda's lock is genuinely tracked and adsc-clinical's is genuinely missing. The crate is a cdylib build artifact, so per Cargo guidance committing the lock is appropriate. This is a real, material reproducibility gap, not a stylistic nitpick. The only nuance: the suggested fix's goal of "same versions as bermuda" isn't automatically guaranteed by merely running `cargo generate-lockfile` today — it would need to be generated/verified against the same registry snapshot — but that does not undermine the core finding.

**Citations.** verifiers/adsc-clinical/rust-verifier/Cargo.toml:16-32 (caret deps + rayon ~1.10 cap comment); Glob verifiers/adsc-clinical/**/Cargo.lock -> no files; Bash ls of rust-verifier dir shows only Cargo.toml, build.rs, src; verifiers/bermuda/rust-verifier/Cargo.toml:16-32 (identical dep set); verifiers/bermuda/rust-verifier/Cargo.lock:640-641 cozo 0.7.6, :1551-1552 graph_builder 0.4.1, :3246-3247 rayon 1.10.0, :5713-5714 z3 0.20.0; verifiers/adsc-clinical/.gitignore:1-9 and verifiers/bermuda/.gitignore:1-9 (identical, Cargo.lock not ignored)


---

## `import-linter-enforces-nothing` — MEDIUM

**Location:** `ci/.import-linter:28` · **area:** ci import-linter · **confidence:** high

**Finding.** The NFR-4 no-direct-HTTP contract has empty root_packages and empty source_modules, so import-linter checks nothing; the accompanying test only asserts the INI parses and lists forbidden module names, giving false confidence that direct HTTP usage is gated when it is not.

**Fix.** Either wire real source_modules (per-skill PYTHONPATH or namespace packages) so the contract actually runs, or replace the parse-only test with a grep/AST scan over skills/*/scripts that fails on requests/httpx/urllib3/aiohttp/playwright imports outside scrapling-fetch. Until then the test should not be framed as enforcing NFR-4.

**Evidence.** The claim is accurate on every material point. In ci/.import-linter, root_packages is empty (line 25-26) and the contract's source_modules is empty (line 31-32, just comments and commented-out future entries). import-linter's "forbidden" contract type only checks imports originating in modules listed under source_modules; with that empty, the contract evaluates zero modules and forbids nothing regardless of the populated forbidden_modules list (requests/httpx/urllib3/aiohttp/playwright, lines 42-46). The accompanying ci/test_lint_no_direct_http.py only (a) asserts the INI parses and has the two expected sections (test_import_linter_config_parses) and (b) asserts the five lib names appear in forbidden_modules (test_forbidden_modules_listed). Neither test ever invokes lint-imports nor scans skill source, so no direct-HTTP usage is gated. The false-confidence framing is real: openspec/changes/add-syntopical-metabook/tasks.md line 16 marks "Set up import-linter to enforce no-direct-http (NFR-4)" as done, and PR-47-REVIEW.md line 28 cites this test as the passing "CI lint" enforcing NFR-4. The config's own header comment concedes source_modules is "intentionally empty" and that the guarantee actually rests on code organization plus a "documentation-level guard," confirming the contract enforces nothing at the tooling level. I confirmed no GitHub workflow references import-linter/lint-imports (grep over .github returned nothing relevant). The suggested fix (real source_modules, or a grep/AST scan over skills/*/scripts) is appropriate. Severity medium is fair: it is not a live bug but a genuine, material gap between claimed and actual enforcement.

**Citations.** C:/Users/charl/russellian-book-suite/ci/.import-linter:25-26 (empty root_packages), :28-32 (contract section with empty source_modules), :41-46 (populated forbidden_modules), :3-17 (comment admitting empty/deferred scope and "documentation-level guard"); C:/Users/charl/russellian-book-suite/ci/test_lint_no_direct_http.py:16-37 (parse-only + forbidden-name-list assertions, no lint-imports run); openspec/changes/add-syntopical-metabook/tasks.md:16 (task marked done); openspec/changes/add-syntopical-metabook/PR-47-REVIEW.md:28 (test framed as enforcing NFR-4); grep over C:/Users/charl/russellian-book-suite/.github found no import-linter/lint-imports invocation.


---

## `no-shadow-writes-untested-enforcement` — MEDIUM

**Location:** `ci/lint_no_shadow_writes.py:40` · **area:** ci no-shadow-writes · **confidence:** high

**Finding.** The actual guard (_guarded_open + _metabook_in_stack + the autouse fixture) has zero test coverage — test_no_shadow_writes.py only calls the pure helpers — and the docstring claims a ci/conftest.py auto-registers the plugin, but no conftest.py exists, so the plugin only fires under explicit -p ci.lint_no_shadow_writes.

**Fix.** Add a test that loads the plugin and asserts a write to a forbidden subdir from a frame whose filename contains 'syntopical_metabook' raises AssertionError (and that a non-metabook write does not). Either add the promised ci/conftest.py or remove the claim from the docstring.

**Evidence.** Both parts of the claim hold against the actual code. (1) Coverage gap: ci/test_no_shadow_writes.py imports only the two pure helpers _is_write_mode and _path_under_workspace_subdir (lines 9-12) and its two tests (lines 15-37) exercise only those. The actual enforcement machinery — _guarded_open (line 44), _metabook_in_stack (line 36, cited line 40 is its `return True`), and the autouse fixture _no_shadow_writes (lines 53-57) — has zero test coverage. The test docstring (line 3) even concedes "Full enforcement fires in Phase 6 when syntopical-metabook scripts exist," confirming the guard path is untested. (2) Phantom conftest: the plugin docstring (lines 8-9) claims "The conftest.py in ci/ can also register it automatically for the ci/ test suite," but a Glob of ci/ returns only __init__.py, lint_no_shadow_writes.py, and the two test files — no ci/conftest.py. conftest.py files exist under skills/ and verifiers/ but none in ci/, so the autouse fixture/plugin only activates under explicit `-p ci.lint_no_shadow_writes`. The issue is material, not stylistic: a security/NFR enforcement guard that is both untested and not auto-registered can silently fail to fire, giving a false sense of protection. This is statically verifiable, so no runtime check was needed.

**Citations.** ci/lint_no_shadow_writes.py:8-9 (docstring claims ci/conftest.py auto-registers); ci/lint_no_shadow_writes.py:36,40,44,53-57 (untested guard: _metabook_in_stack, _guarded_open, autouse fixture); ci/test_no_shadow_writes.py:9-12 (imports only the two pure helpers); ci/test_no_shadow_writes.py:15-37 (tests only _is_write_mode and _path_under_workspace_subdir); ci/test_no_shadow_writes.py:3 (concedes full enforcement untested); Glob of ci/**/*.py returns __init__.py, lint_no_shadow_writes.py, test_lint_no_direct_http.py, test_no_shadow_writes.py — no ci/conftest.py.


---

## `audit-exit-ignores-sample-failures` — MEDIUM

**Location:** `tools/russellian-style-audit/scripts/run.py:148` · **area:** russellian-style-audit run · **confidence:** high

**Finding.** run.py main() returns 0 after the sample-lint stage regardless of samples_pass_count, so an audit where 0/3 modes PASS still exits success; only the stage-1 health check can produce a nonzero exit, making the audit's lint verdict non-blocking.

**Fix.** Return a nonzero exit code (or honor a --strict flag) when any generated sample's verdict is FAIL, so CI/operators can gate on the lint result rather than just the health check.

**Evidence.** The cited file at run.py confirms the claim exactly. In main(), the only path that returns a nonzero exit code is the Stage 1 health-check failure (line 53-62: `if health_verdict == "FAIL": ... return 1`). Stage 3 generates and lints samples (lines 109-138), counting passes into `samples_pass_count` and building a purely cosmetic string `samples_verdict = f"{samples_pass_count}/3 modes PASS"` (line 138). That count is only written into the README (line 141-146) and never compared against anything; control falls through to an unconditional `print(...)` and `return 0` (lines 148-149). `_verdict_from_results` (lines 28-33) is only applied to health-check results, not lint results. So an audit where 0/3 modes PASS still exits 0 — the lint verdict is non-blocking, exactly as claimed. The issue is real and material for CI gating: an operator/CI relying on exit code cannot detect a failing lint outcome. The suggested fix (nonzero exit on any sample FAIL, optionally behind --strict) is appropriate.

**Citations.** C:/Users/charl/russellian-book-suite/tools/russellian-style-audit/scripts/run.py:53-62 (only nonzero return is health-check FAIL); :116,134-138 (samples_pass_count tallied into display-only samples_verdict string); :141-149 (count only written to README, then unconditional return 0); :28-33 (_verdict_from_results applied to health results only)


---

## `competency-hardfail-uncaught-cli` — LOW

**Location:** `skills/book-knowledge/scripts/run_competency_queries.py:128` · **area:** competency queries / gate · **confidence:** medium

**Finding.** When BLOCKING_DEFEASIBLE fires, run_competency_queries raises RuntimeError but main() does not catch it, so the documented release gate surfaces as an unhandled traceback rather than a clean non-zero gate message.

**Fix.** Wrap the call in main() in try/except RuntimeError, print a gate-failure message, and return a distinct non-zero exit code.

**Evidence.** The claim is factually accurate. In run_competency_queries.py, BLOCKING_DEFEASIBLE = True is the module default (line 21, corroborated by CLAUDE.md:78 and AGENTS.md:153). When a defeasible query with severity=critical fires, hard_failures is populated (line 102-103) and run_competency_queries raises RuntimeError at line 128. The CLI entry point main() calls run_competency_queries(layout) at line 140 with no surrounding try/except, and __main__ does raise SystemExit(main(sys.argv)) at line 150. Therefore the RuntimeError propagates out of main() uncaught, so invoking the documented runbook command (python -m scripts.run_competency_queries <workspace>, per SKILL.md:99 and docs/operations/2026-05-12-bundle-c-runbook.md:143) on a workspace that trips the critical gate prints a raw Python traceback rather than a tidy gate-failure message. The issue is real but genuinely minor, matching the claim's own "low" severity: an uncaught RuntimeError still exits non-zero (exit 1), so the gate still blocks correctly; the defect is purely presentational (traceback noise, no distinct exit code) and is confined to the CLI path. The actual in-process release gate runs through book-compose's preflight.py (line 37), which likewise does not wrap the call, but that file is outside the claimed scope. The suggested fix (wrap in main(), print a gate message, return a distinct non-zero code) is reasonable. This is a legitimate cicd/UX observation, not a stylistic nitpick.

**Citations.** skills/book-knowledge/scripts/run_competency_queries.py:21 (BLOCKING_DEFEASIBLE = True); :102-103 (hard_failures populated); :126-130 (raise RuntimeError); :135-146 (main() calls run_competency_queries at :140 with no try/except); :150 (raise SystemExit(main(sys.argv))). Caller: skills/book-compose/scripts/preflight.py:37. Docs: skills/book-knowledge/SKILL.md:99; docs/operations/2026-05-12-bundle-c-runbook.md:143; CLAUDE.md:78.


---

## `dependabot-missing-skill-pip-dirs` — LOW

**Location:** `.github/dependabot.yml:8` · **area:** dependabot coverage · **confidence:** high

**Finding.** Dependabot pip coverage lists only book-qa, book-thesis, and neurosym-forge, omitting the other CI-tested skills with their own pyproject.toml (book-knowledge, book-compose, book-review, russellian-style, review-conductor), so those skills' Python deps are never bumped despite being in the python-skill-matrix.

**Fix.** Add pip dependabot entries for the remaining /skills/<name> directories that have a pyproject.toml, or document why only three are tracked.

**Evidence.** The cited file .github/dependabot.yml lists exactly three pip ecosystem entries: /skills/book-qa (line 9), /skills/book-thesis (line 14), and /skills/neurosym-forge (line 19). A glob shows all of book-knowledge, book-compose, book-review, russellian-style, and review-conductor also have their own pyproject.toml (plus scrapling-fetch and syntopical-metabook). The CI python-skill-matrix in .github/workflows/ci.yml (lines 64-71) tests all eight core skills — book-qa, book-thesis, book-knowledge, book-review, book-compose, russellian-style, review-conductor, neurosym-forge — installing each via pip (extra defaults to 'ci'/'dev'). So the five named skills are CI-tested and have pyproject.toml dependencies, yet dependabot never bumps them. This is a genuine, material coverage gap (not a stylistic nitpick): the three tracked dirs and the five untracked dirs are structurally identical pip-installable skill packages, so the omission is inconsistent and leaves the majority of CI-exercised Python deps unmonitored. The claim's specifics — which three are listed, which five are omitted, and that they are in the python-skill-matrix — are all accurate.

**Citations.** .github/dependabot.yml:8-21 (only book-qa, book-thesis, neurosym-forge pip entries); skills/{book-compose,book-knowledge,book-review,russellian-style,review-conductor}/pyproject.toml exist (glob); .github/workflows/ci.yml:56-71 (python-skill-matrix includes all eight skills); .github/workflows/ci.yml:89-90 (each installed via setup-book-python with pip extra)


---

## `ci-budget-window-conflates-queue-time` — LOW

**Location:** `.github/workflows/ci-budget.yml:30` · **area:** ci-budget workflow · **confidence:** medium

**Finding.** Wall-time is computed as updatedAt minus createdAt of the workflow run, which includes queue/concurrency-wait time (and the concurrency group cancels in-progress runs on non-main refs), so the 'p50/p99 wall-time' it reports against the 120s/240s budgets measures elapsed-since-created, not actual CI execution time, systematically inflating the figure under runner contention.

**Fix.** Derive duration from per-run timing (e.g. gh api run jobs started_at/completed_at, or run_started_at) instead of createdAt, or rename the metric to 'turnaround time' so the budget comparison is meaningful.

**Evidence.** The cited code confirms the core claim. ci-budget.yml:30-32 computes each run's duration as datetime(updatedAt) - datetime(createdAt). For a GitHub Actions workflow run, createdAt is the moment the run is created/queued (not when a runner picks it up); the API exposes run_started_at for execution start. Therefore updatedAt - createdAt is turnaround/elapsed-since-created, which includes queue and concurrency-wait time, yet the script labels it "wall-time" and compares it to execution-oriented budgets of 120s (p50) and 240s (p99) at lines 38-40 / 44-46. That is a genuine measurement-validity defect, not a style nit: under runner contention the reported figure is systematically inflated relative to actual CI execution time. The secondary sub-claim — that the concurrency group "cancels in-progress runs on non-main refs" — is factually true (ci.yml:11-13: group keyed on ref with cancel-in-progress when ref != main), but it does not actually inflate the metric, because cancelled runs get conclusion "cancelled" while the budget script filters to conclusion == "success" only (ci-budget.yml:27), so they are excluded from durations. So that part of the rationale is a partial red herring. The central claim and its impact, however, hold: queue-wait time leaks into successful runs' measured duration. The suggested fix (use run_started_at / per-job started_at/completed_at, or rename to "turnaround time") is appropriate. Severity low is reasonable since it is a reporting/labeling accuracy issue rather than a functional break.

**Citations.** .github/workflows/ci-budget.yml:22 (json fields createdAt,updatedAt), :27 (filters conclusion=="success"), :30-32 (duration = updatedAt - createdAt), :38-40 and :44-46 (labels it "wall-time" vs budgets 120s/240s); .github/workflows/ci.yml:11-13 (concurrency group keyed on github.ref with cancel-in-progress on non-main)


---

## `budget-advisory-only` — LOW

**Location:** `.github/workflows/ci-budget.yml:41` · **area:** ci-budget workflow · **confidence:** high

**Finding.** The budget check computes ok = p50<=120 and p99<=240 but only embeds the status in a PR comment and never exits non-zero, so an over-budget CI run never fails the budget-check job and the 120s/240s budgets are unenforced.

**Fix.** If the budget is meant to gate, add a final step that exits 1 when over budget (or document explicitly that budget-check is advisory-only); otherwise it is dead enforcement.

**Evidence.** The budget-check job has exactly two steps. The first ("compute last-20 wall-time stats", lines 17-48) runs an inline Python script that computes ok = p50 <= 120 and p99 <= 240 at line 41, but only uses ok to render a string in stdout (line 42) and in comment.md (line 47). The script's only nonzero-affecting control is raise SystemExit(0) (line 35) when there are no green runs, which exits zero. There is no raise SystemExit(1)/sys.exit(1) anywhere, and no further step that inspects ok or the over-budget status. The second step ("post PR comment", lines 49-53) merely posts comment.md and is even gated to pull_request events. Since the heredoc Python ends with the ok-derived prints and a successful close, the job process exits 0 regardless of budget. Therefore an over-budget CI run never fails budget-check, and the 120s/240s budgets are advisory-only and unenforced. The claim is accurate. Severity 'low' is fair: it is dead enforcement, not a correctness/security bug, but the finding is real and material (the job's apparent purpose of gating is not actually realized).

**Citations.** C:/Users/charl/russellian-book-suite/.github/workflows/ci-budget.yml:41 (ok = p50 <= 120 and p99 <= 240); :42 and :47 (ok only used to format status text); :35 (only explicit exit is SystemExit(0)); :49-53 (only other step just posts the comment, no exit-on-over-budget); whole job body :15-53 contains no nonzero exit path.


---

## `ci-legacy-advisory-d13-vacuous` — LOW · needs runtime verification

**Location:** `.github/workflows/ci-legacy.yml:364` · **area:** ci-legacy bermuda-z3-verify · **confidence:** medium

**Finding.** The bermuda-z3-verify job runs run_verification with --stub and the D13-assertion step is continue-on-error and only prints the ticket count (never asserts > 0), so the 'bermuda end-to-end verify (real Z3)' job passes vacuously and never actually validates that a real-Z3 run produces D13 tickets.

**Fix.** Either gate this job behind the real (non-stub) Z3 path before treating it as signal, or rename it to reflect it is a stubbed smoke test so it is not mistaken for real-Z3 end-to-end verification.

**Evidence.** The cited workflow file confirms every element of the claim statically. The job is named "bermuda end-to-end verify (real Z3)" (line 308). The "run verifier end-to-end" step invokes run_verification with --stub and swallows failures via `|| true` (lines 355-357). The step titled "assert D13 ticket appears" (line 364) is continue-on-error: true (line 369) and its inline Python only computes len(d13) and prints "D13 tickets found: {len(d13)}" (line 382); it never asserts the count is > 0 and never exits non-zero when zero tickets are found (it even exits 0 if defects.json is missing, lines 375-377). The book-qa D13 lint step is likewise continue-on-error with `|| true` (lines 360-363). Thus no step in the job can fail on a missing D13 ticket, so the job passes vacuously regardless of whether a real-Z3 run would produce D13 tickets. The in-file comments explicitly acknowledge this: lines 347-349 and 365-368 state that the --stub run does not trigger D13 tickets and that real D13-via-Z3 is a deferred follow-up. The issue is real and material: the green "real Z3" job provides no actual D13 signal and could be mistaken for genuine end-to-end real-Z3 verification. It is correctly rated low severity since the comments are honest about the gap, but the job name remains misleading. This is verifiable entirely from the workflow file without runtime observation.

**Citations.** C:/Users/charl/russellian-book-suite/.github/workflows/ci-legacy.yml:308 (job name "bermuda end-to-end verify (real Z3)"); :355-357 (run_verification --stub || true); :360-363 (book-qa D13 lint, continue-on-error + || true); :364 (step "assert D13 ticket appears"); :369 (continue-on-error: true); :382 (only prints "D13 tickets found: {len(d13)}", no assertion); :347-349 and :365-368 (comments acknowledging --stub does not trigger D13 and real-Z3 D13 is a follow-up)


---

## `divergence-summary-misreports-per-os` — LOW

**Location:** `.github/workflows/ci.yml:206` · **area:** ci divergence summary · **confidence:** high

**Finding.** The divergence table maps a single aggregate needs.python-skill-matrix.result onto all three OS columns, so a failure in only the macOS leg renders Linux and Windows as 'see legs' too (and a pass renders all three 'pass' even if a leg was skipped), making the per-OS table misleading rather than diagnostic.

**Fix.** Either drop the per-OS columns (the result is matrix-aggregate, not per-OS) or parse per-leg results via 'gh api' / the actions API to populate columns accurately; the doc already concedes the limitation, so at minimum stop labeling columns by OS.

**Evidence.** The cited block (lines 204-221) builds a table with columns explicitly labeled "Linux | macOS | Windows", but for the python-skill row it derives all three column values (ps_l, ps_m, ps_w) from a single scalar, needs.python-skill-matrix.result. In every case branch (success, failure, skipped, cancelled, default) the three columns are set to identical values, so they cannot diverge by OS. Thus a failure confined to one leg (e.g. macOS) prints "see legs" under Linux and Windows too, and a "success" prints "pass" for all three even if a leg was skipped — exactly as claimed. The columns purport to be per-OS but the data is matrix-aggregate, making the table misleading rather than diagnostic. The workflow's own preamble (lines 200-202) concedes the data is aggregate. This is statically determinable from the YAML; no runtime observation is needed. The cargo-test row (lines 213-221) has the same aggregate-vs-per-column structure, reinforcing the pattern. Severity "low" is fair: it is a reporting/diagnostic accuracy issue in a summary table, not a correctness defect in the build itself, but it is a real, material defect (the table can actively mislead an operator about which OS leg broke), not a stylistic nitpick.

**Citations.** C:/Users/charl/russellian-book-suite/.github/workflows/ci.yml:200-202 (preamble conceding aggregate-only data), :204 (per-OS column headers Linux|macOS|Windows), :206-212 (single PYTHON_SKILL_RESULT scalar fanned identically into ps_l/ps_m/ps_w across all case branches), :220 (table row emitting the three identical columns); :213-219 same pattern for cargo-test.


---

## `cargo-edition-2024-toolchain` — LOW · needs runtime verification

**Location:** `skills/neurosym-forge/assets/project-template/rust-verifier/Cargo.toml.tmpl:3` · **area:** rust-verifier scaffold template · **confidence:** medium

**Finding.** The scaffolded `Cargo.toml` pins `edition = "2024"`, which requires Rust 1.85+ (stabilized Feb 2025); scaffolded projects built on older toolchains fail to compile with no `rust-version`/MSRV declaration to surface the requirement clearly.

**Fix.** Add `rust-version = "1.85"` to the `[package]` table so cargo emits an actionable MSRV error, and document the toolchain requirement in the scaffolded README.

**Evidence.** The cited template pins `edition = "2024"` (the claim cites line 3; it is actually on line 4, a harmless off-by-one — the content is unambiguously present). Edition 2024 was stabilized in Rust 1.85 (Feb 2025), so any scaffolded project built on an older toolchain will fail. A repo-wide grep across the neurosym-forge skill shows no `rust-version`, `rust-toolchain.toml`, `1.85`, or MSRV declaration anywhere in the template, and the scaffolded README.md.tmpl documents only `npm install`/`npm run build` with no toolchain-version requirement. So the factual core of the claim holds: edition 2024 is pinned with no MSRV/toolchain pin to surface the requirement. The severity is correctly rated low — note that cargo itself does emit an edition-support error on old toolchains (so it is not a silent failure), but that diagnostic points at the cargo/edition mismatch rather than a clean MSRV message; adding `rust-version = "1.85"` is a legitimate, non-stylistic hygiene fix. The claim is true and the issue is real, if minor.

**Citations.** skills/neurosym-forge/assets/project-template/rust-verifier/Cargo.toml.tmpl:4 (edition = "2024"; lines 1-4 are the [package] table with name/version/edition only, no rust-version); skills/neurosym-forge/assets/project-template/README.md.tmpl:6-17 (Build section documents only npm, no Rust toolchain version); repo-wide grep over skills/neurosym-forge for rust-version|toolchain|1.85|MSRV|rustc returned no MSRV/rust-version/rust-toolchain declaration in the template.


---
