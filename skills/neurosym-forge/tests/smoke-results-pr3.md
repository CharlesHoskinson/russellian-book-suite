# PR-3 local QA run

Date: 2026-05-15
Node: v24.13.0
npm: 11.6.2
nbb: 1.4.207

| Suite | Count | Status |
|---|---|---|
| neurosym-forge (full) | 155 | pass |
| book-knowledge | 141 | pass |
| book-qa | 47 | pass |
| verifiers/bermuda | 23 | pass |
| **Live nbb integration** | **2** | **pass** |

Bermuda `predicates.edn` byte-identical to main: yes (`git diff origin/main -- verifiers/bermuda/rules/predicates.edn` returns no output).

## What Phase 8 surfaced

Three real issues that subagent-reported "tests passed" would have missed:

1. **Windows `subprocess` cannot resolve `npm` via PATH.** `subprocess.run(["npm", ...])` fails on Windows because CreateProcess only auto-resolves `.exe`/`.com`, not `.cmd` (which is what `npm.cmd` is on Windows). Fix: resolve via `shutil.which("npm")` once at module load and use the full path. Cross-platform; works the same on POSIX.

2. **nbb cannot find scaffolded namespaces without `nbb.edn`.** First run of `nbb -m demo.booklogic-test` failed with "Could not find namespace". nbb defaults to looking at the current directory only; the scaffolded CLJS sources live under `cljs-orchestrator/src/main/` and `.../src/test/`. Fix: add `nbb.edn.tmpl` at the project root declaring `:paths ["cljs-orchestrator/src/main" "cljs-orchestrator/src/test"]`.

3. **`infer-value-kind` read the wrong index of the `(fact ...)` form.** The body of `(fact ?id :Subject :pred BODY)` is at index 4; the compiler was reading index 3 (which is the predicate name) and consequently always returning `:string` instead of `:int` for `(parse-int ?n)`-typed lifts. Verified by the live nbb run asserting `:value-kind :int` against a generated `predicates.edn`. Fix: change `(nth emit-form 3 nil)` to `(nth emit-form 4 nil)` plus documented body layout in the docstring.

## What Phase 8 did NOT surface

- The CLJS test fixture (`booklogic_test.cljs.tmpl`) inside nbb passed both before and after the index fix because its assertions used regex matching rather than equality, and the `:string` value still matched a permissive pattern. The Python harness's stricter assertion is what surfaced the bug. Lesson: the outermost-language test (Python harness here) needs the strictest assertions; the inner-language fixture (CLJS deftest here) can be permissive for path-of-least-resistance.

- A cold `npm install` of nbb takes 1-3 minutes. The module-scoped fixture means the integration test costs ~30 seconds once nbb is cached locally and ~3 minutes on a cold CI run. Both are acceptable.

## Fixes committed

- `94d0de5` — nbb.edn for CLJS namespace path resolution
- `be93205` — integration test: resolve npm.cmd on Windows; module-scope fixture
- `a9214a4` — BookLogic compiler: fix infer-value-kind body index (4 not 3)
