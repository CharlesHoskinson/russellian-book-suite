# Security & supply chain — findings

10 confirmed findings. Each survived an independent adversarial-verify pass; the evidence line cites code that was opened and read.

## `actions-not-sha-pinned` — HIGH

**Location:** `.github/workflows/ci.yml:33` · **area:** .github workflows + composite action · **confidence:** high

**Finding.** Every third-party GitHub Action is referenced by a mutable tag/branch rather than a full commit SHA, so a compromised upstream tag (e.g. dorny/paths-filter@v3, DeterminateSystems/nix-installer-action@v22, DeterminateSystems/magic-nix-cache-action@v13, Swatinem/rust-cache@v2, dtolnay/rust-toolchain@stable) can inject code into CI with repo-write/PR-write tokens.

**Fix.** Pin all third-party (and ideally first-party actions/*) action references to a full 40-char commit SHA with a trailing ` # vX.Y.Z` comment, across ci.yml, ci-legacy.yml, ci-budget.yml, nightly-flake-drift.yml, onboarding-bench.yml, and .github/actions/setup-book-python/action.yml. The dtolnay/rust-toolchain@stable branch ref is especially dangerous as it is a moving branch, not even a tag.

**Evidence.** The claim is accurate on every concrete point I could check statically. ci.yml line 33 is exactly `uses: dorny/paths-filter@v3`, and the other named refs exist verbatim: `DeterminateSystems/nix-installer-action@v22` (line 138), `DeterminateSystems/magic-nix-cache-action@v13` (line 139), `Swatinem/rust-cache@v2` (lines 140, 172), and `dtolnay/rust-toolchain@stable` (line 171). None of the third-party (or first-party `actions/*`) references in any workflow are pinned to a 40-char commit SHA — they all use mutable tags (`@v3`, `@v22`, `@v4`, `@v5`, `@v8`) or, in the rust-toolchain case, a moving branch (`@stable`). The same unpinned tags recur across ci-legacy.yml, nightly-flake-drift.yml, onboarding-bench.yml, ci-budget.yml, and the composite action setup-book-python/action.yml (`actions/setup-python@v5`). The exposure is material and not stylistic: ci.yml grants `pull-requests: write` (line 9) and ci-budget.yml also grants `pull-requests: write` (line 9) plus passes `GITHUB_TOKEN` to a step (line 19); a compromised upstream tag/branch would execute attacker code in a job holding a write-capable token, the standard supply-chain risk that SHA pinning mitigates. This is a recognized GitHub security hardening recommendation, so the high severity is justified. The only minor nuance: the dorny/paths-filter and rust-cache steps run in jobs whose token at that moment is read-mostly, but ci.yml's top-level write permission and the magic-nix-cache/checkout steps still run under the broader token grant, and ci-budget.yml clearly has write+token exposure, so the materiality holds. Suggested fix (pin to full SHA with version comment) is the correct remediation.

**Citations.** .github/workflows/ci.yml:9 (pull-requests: write), :33 (dorny/paths-filter@v3), :138 (nix-installer-action@v22), :139 (magic-nix-cache-action@v13), :140 and :172 (Swatinem/rust-cache@v2), :171 (dtolnay/rust-toolchain@stable); .github/actions/setup-book-python/action.yml:19 (actions/setup-python@v5); .github/workflows/ci-budget.yml:9 (pull-requests: write) and :19 (GH_TOKEN); .github/workflows/nightly-flake-drift.yml:15-16; .github/workflows/onboarding-bench.yml:14-23; .github/workflows/ci-legacy.yml:298,325,409 (dtolnay/rust-toolchain@stable)


---

## `import-linter-contract-empty` — HIGH

**Location:** `ci/.import-linter:31` · **area:** ci import-linter (NFR-4) · **confidence:** high

**Finding.** The no-direct-http-outside-scrapling-fetch contract has empty root_packages and empty source_modules, so import-linter has nothing to analyze and the contract can never fail — the NFR-4 'no direct HTTP outside scrapling-fetch' boundary is documentation-only and enforces nothing.

**Fix.** Populate source_modules (and root_packages) with the actual skill package paths, or replace the contract with a working enforcement mechanism; until then the test_lint_no_direct_http.py 'guard' only asserts the config text, not the actual import graph, giving a false sense of enforcement.

**Evidence.** The claim is factually accurate on every point I could verify statically. In ci/.import-linter, the contract's source_modules (line 31) contains only comments (lines 32-40 are commented-out future entries), and root_packages (line 25) is likewise empty. import-linter's forbidden contract operates by walking the import graph of the modules named in source_modules; with that list empty (and no root_packages registered) there is nothing to analyze, so the contract can never produce a violation regardless of what is listed under forbidden_modules. The file's own header comment (lines 3-22) openly states this is "intentionally empty" deferred scope. The companion test ci/test_lint_no_direct_http.py does not invoke lint-imports at all: test_import_linter_config_parses only checks the INI parses and has the expected sections, and test_forbidden_modules_listed only asserts the five library names appear as text in forbidden_modules. So the "guard" asserts config text, not the real import graph — exactly as claimed. This is material, not stylistic: a quick grep shows skills do import the very libraries the contract names (e.g. skills/book-compose/scripts/print_pdf.py and _playwright_check.py import playwright), so the NFR-4 "no direct HTTP outside scrapling-fetch" boundary is presently documentation-only and would not catch a regression. The repo treats this as an intentional deferral rather than a defect, but the security-relevant fact — that the contract enforces nothing and the test gives a false sense of enforcement — holds.

**Citations.** C:/Users/charl/russellian-book-suite/ci/.import-linter:25 (empty root_packages); :31-40 (empty source_modules, only commented future entries); :41-46 (forbidden_modules list); :3-22 (header comment declaring intentional emptiness). C:/Users/charl/russellian-book-suite/ci/test_lint_no_direct_http.py:16-36 (tests only parse config and check forbidden_modules text; never run lint-imports). Grep hits showing real usage of forbidden libs: skills/book-compose/scripts/print_pdf.py and skills/book-compose/scripts/_playwright_check.py (import playwright).


---

## `shadow-write-guard-misses-pathlib` — HIGH · needs runtime verification

**Location:** `ci/lint_no_shadow_writes.py:54` · **area:** ci no-shadow-writes (NFR-5) · **confidence:** high

**Finding.** The NFR-5 guard monkeypatches only builtins.open, but syntopical-metabook overwhelmingly writes via pathlib Path.write_text() / Path.write_bytes() / Path.open() (e.g. manifest.py:11, veto.py:54, triage.py:62, topic_map.py:56, render_*.py), none of which route through builtins.open — so the guard catches almost none of the skill's actual writes to forbidden subdirs.

**Fix.** Patch the write surface metabook actually uses: pathlib.Path.open / Path.write_text / Path.write_bytes (and os.open), not just builtins.open; otherwise the shadow-write invariant is unenforced for the code it targets.

**Evidence.** The NFR-5 guard at ci/lint_no_shadow_writes.py only monkeypatches builtins.open (lines 21, 44-50, 53-56). The syntopical-metabook production scripts write exclusively through pathlib methods: manifest.py:11 and :22 use Path.open("a"), veto.py:54 uses path.open("a"), triage.py:62 uses path.write_text, topic_map.py:56, disputed_questions.py:48/79, concept_reconcile.py:88, coverage_report.py:42, render_consensus_map.py:82/83, render_adversarial.py:70, _positions_io.py:67, _config.py:33, render_per_rule.py:79, and project_lens.py:147 all use Path.write_text. A targeted grep for bare/builtin open( calls across scripts/ returns zero matches. In CPython, pathlib.Path.open / write_text / write_bytes route through io.open (the C _io.open), not the Python-level builtins.open, so patching builtins.open does not intercept any of these calls. The guard therefore catches essentially none of the skill's real write surface — the invariant is unenforced for the exact code it targets. This is a material, high-severity correctness defect in a security/safety guard, not a stylistic nitpick. The CPython routing of Path.open through io.open rather than builtins.open is well-established static knowledge, so no runtime observation is required to reach a confident verdict; the suggested fix (also patch pathlib.Path.open/write_text/write_bytes and os.open) is correct.

**Citations.** C:/Users/charl/russellian-book-suite/ci/lint_no_shadow_writes.py:21,44-50,53-56 (patches only builtins.open); manifest.py:11,22 (Path.open); veto.py:54 (path.open); triage.py:62 (write_text); topic_map.py:56, disputed_questions.py:48/79, concept_reconcile.py:88, coverage_report.py:42, render_consensus_map.py:82-83, render_adversarial.py:70, _positions_io.py:67, project_lens.py:147 (all Path.write_text); grep for bare open( in scripts/ = no matches.


---

## `kg-cozo-single-quote-escape` — MEDIUM

**Location:** `verifiers/bermuda/rust-verifier/src/kg.rs:176` · **area:** kg / Cozo injection · **confidence:** medium

**Finding.** build_db interpolates claim id/source into a Cozo script with only `'`->`\'` replacement and no escaping of backslash or newline, so a claim source containing a backslash or other Cozo-special char can break the script or alter the inserted data (string-injection into the Datalog literal).

**Fix.** Use Cozo parameterized inputs (the params map argument to run_script with $-bound variables) instead of string interpolation, eliminating manual escaping entirely.

**Evidence.** At kg.rs:176-180, build_db builds a Cozo Datalog script via format!, embedding c.id and c.source into single-quoted string literals after applying only `.replace("'", "\\'")`. Backslashes and other Cozo-special characters are not escaped. Cozo's single-quoted string literals use C-style backslash escapes (the code itself relies on this by emitting `\'` to escape a quote), so an input containing a literal backslash — e.g. a Windows path like `C:\Users` or LaTeX/regex content in a claim source — produces `'C:\Users'`, which Cozo will either reject as an invalid escape (breaking the script -> Error::Kg) or reinterpret, altering the stored value relative to the input. ir.rs:117-121 shows Claim.source is a free-form, deserialized String (data-controlled), and id is a ClaimId, so the values are not constrained to a safe charset. This is a genuine string-injection-into-Datalog-literal correctness/security defect, not a stylistic nitpick, and is realistic in a Windows-centric repo where backslashes appear in paths. The suggested fix is sound: run_script already takes a params map (currently Default::default() at line 181), so $-bound parameters would eliminate manual escaping entirely. Static analysis is sufficient; no runtime observation needed to confirm the missing escaping.

**Citations.** verifiers/bermuda/rust-verifier/src/kg.rs:176-182 (format! with `?[id, source] <- [['{}', '{}']] :put claim` and only `.replace("'", "\\'")` on c.id and c.source; params passed as Default::default()); kg.rs:169-174 (run_script signature with params arg); verifiers/bermuda/rust-verifier/src/ir.rs:117-121 (struct Claim { id: ClaimId, source: String }, Deserialize)


---

## `dependabot-pip-coverage-gap` — MEDIUM

**Location:** `.github/dependabot.yml:7` · **area:** dependabot · **confidence:** high

**Finding.** The pip ecosystem block covers only book-qa, book-thesis, and neurosym-forge, leaving 7 of 10 Python skills (book-compose, book-knowledge, book-review, review-conductor, russellian-style, scrapling-fetch, syntopical-metabook) with no dependency-update or vulnerability alerting.

**Fix.** Add a pip update entry (directory: /skills/<name>) for every skill that has a pyproject.toml, in particular scrapling-fetch which pins scrapling==0.4.8 and pulls in trafilatura/playwright — the highest-risk supply-chain surface in the repo.

**Evidence.** The cited .github/dependabot.yml contains exactly three pip ecosystem entries — /skills/book-qa (line 9), /skills/book-thesis (line 14), and /skills/neurosym-forge (line 19) — plus github-actions, cargo, and npm entries. A glob for skills/*/pyproject.toml returns 10 skills, all of which are independently packaged Python projects (CLAUDE.md confirms "Each skill has its own .venv and pyproject.toml"). Subtracting the three covered skills leaves exactly the seven the claim names: book-compose, book-knowledge, book-review, review-conductor, russellian-style, scrapling-fetch, syntopical-metabook. These seven have no Dependabot pip entry, so they receive no automated dependency-update PRs or transitive vulnerability alerts. The claim's specific risk callout is also accurate: skills/scrapling-fetch/pyproject.toml hard-pins scrapling==0.4.8 and trafilatura>=2,<3 (the scrapling stack pulls in a heavy network/parsing/browser-automation surface), and being pinned with no Dependabot coverage means CVEs in those packages would go unflagged. This is a real, material security/maintenance gap, not a stylistic nitpick. The only minor inaccuracy is cosmetic: line 7 itself is a blank line, but the surrounding context fully supports the claim. (Dependabot's reachability of nested directories is well established, so the omission is genuinely an authoring gap, not a tooling constraint.)

**Citations.** C:/Users/charl/russellian-book-suite/.github/dependabot.yml:8-21 (only book-qa, book-thesis, neurosym-forge pip entries); Glob skills/*/pyproject.toml lists all 10 skills; C:/Users/charl/russellian-book-suite/skills/scrapling-fetch/pyproject.toml:5-9 (scrapling==0.4.8, trafilatura>=2,<3)


---

## `dependabot-cargo-npm-gap` — MEDIUM

**Location:** `.github/dependabot.yml:23` · **area:** dependabot · **confidence:** high

**Finding.** Cargo and npm coverage is limited to verifiers/bermuda only; the adsc-clinical, epidemiology, and osmotic_pressure verifiers each have their own Cargo.toml/Cargo.lock and package.json/package-lock.json that receive no Dependabot updates.

**Fix.** Add cargo entries for verifiers/{adsc-clinical,epidemiology,osmotic_pressure}/rust-verifier and npm entries for verifiers/{adsc-clinical,epidemiology,osmotic_pressure}; the Clojure deps.edn files have no native Dependabot support and should be flagged for manual review or a clj-watson scan.

**Evidence.** The dependabot config has exactly two non-pip ecosystem entries: cargo at /verifiers/bermuda/rust-verifier (line 23-24) and npm at /verifiers/bermuda (line 28-29). No entries exist for the adsc-clinical, epidemiology, or osmotic_pressure verifiers. Glob confirms all three (plus bermuda) have a rust-verifier/Cargo.toml and a package.json, so the three uncovered verifiers genuinely receive no Dependabot dependency updates for their Rust crates or npm packages. This is a real, material security gap: vulnerable transitive deps in those manifests will not be flagged. All four verifiers also have a deps.edn (Clojure), which Dependabot does not support natively, so the suggested manual-review/clj-watson flagging is appropriate. One small factual imprecision in the claim: adsc-clinical has Cargo.toml and package.json but NO Cargo.lock or package-lock.json (only bermuda, epidemiology, osmotic_pressure have lock files). This does not undermine the finding — adsc-clinical still has uncovered manifests, and Dependabot resolves from the manifest dir regardless. The core claim (cargo/npm coverage limited to bermuda; three other verifiers uncovered; Clojure unsupported) holds.

**Citations.** C:/Users/charl/russellian-book-suite/.github/dependabot.yml:23-31 (cargo only at verifiers/bermuda/rust-verifier, npm only at verifiers/bermuda); Glob results: verifiers/{adsc-clinical,bermuda,epidemiology,osmotic_pressure}/rust-verifier/Cargo.toml and verifiers/{adsc-clinical,bermuda,epidemiology,osmotic_pressure}/package.json all exist; Cargo.lock and package-lock.json exist for bermuda/epidemiology/osmotic_pressure but NOT adsc-clinical; deps.edn present in all four verifiers


---

## `shadow-write-guard-test-only` — MEDIUM · needs runtime verification

**Location:** `ci/lint_no_shadow_writes.py:53` · **area:** ci no-shadow-writes (NFR-5) · **confidence:** high

**Finding.** The guard is an autouse pytest fixture, so it only ever runs inside the test session and never in production; a forbidden write only trips it if some test happens to exercise the exact write path through builtins.open, making NFR-5 a test-time best-effort rather than an enforced boundary.

**Fix.** Document this as test-time-only and add explicit tests that drive each metabook writer through the guarded path, or move enforcement into the WorkspaceLayout/IO layer that all writers must go through so the invariant holds at runtime, not just opportunistically under pytest.

**Evidence.** The NFR-5 guard is implemented exclusively as an autouse pytest fixture (`_no_shadow_writes`) that monkeypatches `builtins.open` for the test session only (ci/lint_no_shadow_writes.py:53-57). monkeypatch restores `builtins.open` at test teardown, so the guard has zero effect outside pytest — it never runs in production. The check (`_guarded_open`) only fires when (a) a test is running, (b) `mode` is a write mode, (c) the resolved path contains a forbidden subdir component, AND (d) a `syntopical_metabook` frame is on the stack. So a forbidden write is caught only if some test happens to drive that exact write path through the patched `builtins.open`. The only test file, ci/test_no_shadow_writes.py, does not even do that: it exercises the pure helpers `_is_write_mode` and `_path_under_workspace_subdir` on synthetic paths, never calls `_guarded_open`, and explicitly notes the safe write "won't trigger" the guard (line 28). Its docstring concedes "Full enforcement fires in Phase 6 when syntopical-metabook scripts exist," and no test drives any metabook writer through the guard. There is no integration into WorkspaceLayout or any shared IO layer that all writers must traverse. The ledger-ownership invariant in CLAUDE.md is therefore not enforced at runtime by this mechanism. The claim is accurate and the gap is material for a security/integrity boundary (NFR-5): it is test-time, opportunistic best-effort, not an enforced runtime boundary.

**Citations.** ci/lint_no_shadow_writes.py:44-50 (_guarded_open logic, requires _metabook_in_stack), ci/lint_no_shadow_writes.py:53-57 (autouse fixture, monkeypatch builtins.open scoped to test session only); ci/test_no_shadow_writes.py:1-38 (only tests helper functions, line 28 comment "we're not in the metabook stack, guard won't trigger", line 3 "Full enforcement fires in Phase 6"); README.md:1545 (plugin "execute inside those test suites, not as separate jobs"); openspec/changes/add-syntopical-metabook/PR-47-REVIEW.md:69 confirms autouse-fixture design.


---

## `script-escape-case-sensitive` — LOW

**Location:** `skills/book-compose/scripts/render_book_html.py:21` · **area:** book HTML render · **confidence:** medium

**Finding.** _escape_for_script_block only replaces the lowercase literal '</script'; a manuscript containing '</SCRIPT' or '</Script' (HTML end tags are case-insensitive to browsers) will prematurely close the inlined <script> payload and break the book browser.

**Fix.** Use a case-insensitive regex sub (re.sub(r'</script', '<\\/script', text, flags=re.IGNORECASE)) or escape every '</' to '<\/' inside the script block.

**Evidence.** The code at render_book_html.py:21 escapes only the lowercase literal via text.replace("</script", "<\\/script"). The skeleton (book-html-skeleton.html lines 28-33) inlines both book_payload_json and manuscript_md inside genuine <script> elements, and both pass through _escape_for_script_block. Per the HTML5 tokenizer, the script-data end-tag is matched case-insensitively: any "</" followed by the letters s-c-r-i-p-t in any case (e.g. </SCRIPT, </Script) closes the element. Therefore a manuscript containing an uppercase or mixed-case </script... sequence would prematurely terminate the script block, breaking the static fallback rendering / book browser and constituting an injection escape. Because these are non-fiction books that can legitimately quote HTML/code, mixed-case end tags are plausible, not a contrived edge. The function's docstring promises to prevent the embedded script tag from breaking, which it does not fully do. The claim is accurate and the issue is real and material (low severity, as labeled); the suggested case-insensitive re.sub fix is appropriate.

**Citations.** C:/Users/charl/russellian-book-suite/skills/book-compose/scripts/render_book_html.py:19-21,29-30 (escape uses lowercase-only replace and is applied to both payloads); C:/Users/charl/russellian-book-suite/skills/book-compose/assets/book-html-skeleton.html:28-33 (payloads inlined inside real <script> blocks)


---

## `ci-legacy-npm-install-no-lock` — LOW

**Location:** `.github/workflows/ci-legacy.yml:281` · **area:** ci-legacy supply chain · **confidence:** medium

**Finding.** The cljs-bermuda-test and bermuda-z3-verify/osmotic jobs run `npm install` (not `npm ci`), so the committed package-lock.json is not enforced and transitive deps can resolve to newer/unintended versions at CI time, weakening reproducibility and the supply-chain guarantee.

**Fix.** Use `npm ci` to install strictly from the lockfile; if the lockfile genuinely drifts from package.json, fix the lockfile rather than masking it with `npm install`, since `npm install` silently mutates the resolved dependency set.

**Evidence.** The factual core of the claim is accurate. In .github/workflows/ci-legacy.yml the cljs-bermuda-test job runs `npm install --no-audit --no-fund` (line 281), the bermuda-z3-verify job runs `npm install` (line 336), and the osmotic-pressure-smoke job runs `npm install` (line 431) — none use `npm ci`. Committed lockfiles exist for both projects (verifiers/bermuda/package-lock.json ~115KB and verifiers/osmotic_pressure/package-lock.json ~117KB), and the bermuda job even sets a cache key on the lockfile (line 271). Because `npm install` reconciles toward package.json and can update/mutate the resolved dependency set rather than installing strictly from the lockfile, the lockfile is not enforced and transitive deps can resolve to unintended versions — a real (if low-severity) reproducibility/supply-chain weakening, matching the finding's own "low/medium" rating. The suggested fix (use `npm ci`, repair the lockfile rather than masking drift) is the correct posture. Caveats that keep this at low severity: this is a legacy workflow building verifier smoke tests (not shipped artifacts), and the choice is a deliberate, documented tradeoff — the inline comment at lines 278-280 states the lockfile "sometimes drifts from package.json across PRs in flight, and `npm ci` is strict-fail there." So it is an intentional decision, not an accidental oversight, but the security concern the finding raises is genuine.

**Citations.** C:/Users/charl/russellian-book-suite/.github/workflows/ci-legacy.yml:281 (`run: npm install --no-audit --no-fund`); same file:336 and :431 (`run: npm install`); :278-280 (comment documenting deliberate use of `npm install` over `npm ci` due to lockfile drift); :271 (cache-dependency-path keys on package-lock.json); committed lockfiles verifiers/bermuda/package-lock.json and verifiers/osmotic_pressure/package-lock.json present on disk.


---

## `shadow-write-substring-overmatch` — LOW

**Location:** `ci/lint_no_shadow_writes.py:33` · **area:** ci no-shadow-writes (NFR-5) · **confidence:** medium

**Finding.** _path_under_workspace_subdir flags any absolute path containing a component named raw/claims/wiki/graph anywhere (after .resolve()), so legitimate writes under unrelated directories that merely happen to contain such a path segment (e.g. a CI checkout or temp dir named 'graph') would be falsely blocked when metabook is on the stack.

**Fix.** Anchor the check to the resolved workspace root (only forbid <workspace_root>/<subdir>/...) rather than matching the subdir name at any depth of the absolute path.

**Evidence.** The cited code matches the claim exactly. `_path_under_workspace_subdir` (lines 28-33) calls `Path(path).resolve().parts` then `return any(p in _FORBIDDEN_DIRS for p in parts)`, where `_FORBIDDEN_DIRS = {"raw","claims","wiki","graph"}` (line 18). This flags a path if ANY component of the fully-resolved absolute path equals a forbidden name, with no anchoring to a workspace root. So a legitimate write under an unrelated directory whose absolute path happens to include a segment named graph/wiki/raw/claims (e.g. a CI checkout dir or temp dir) would be falsely blocked when a metabook frame is on the stack (guard at line 46 requires both this match and `_metabook_in_stack()`). The `.resolve()` step makes it worse by expanding to the full absolute path including all parent components. The behavior is statically observable and does not need runtime verification. The suggested fix (anchor to `<workspace_root>/<subdir>/...`) is the correct remedy. Materiality is genuinely low: this is a test-time pytest plugin guarding NFR-5, not a production security boundary, and it requires the somewhat-specific coincidence of a forbidden directory name in the resolved path plus metabook on the stack. But the overmatch is real and not stylistic — it is a correctness defect in the path-matching logic exactly as claimed.

**Citations.** C:/Users/charl/russellian-book-suite/ci/lint_no_shadow_writes.py:18 (_FORBIDDEN_DIRS), :28-33 (_path_under_workspace_subdir using resolve().parts + any-component membership test, the cited line 33), :44-50 (_guarded_open guard combining path match with metabook-in-stack), :53-56 (autouse pytest fixture confirming this is test-time only)


---
