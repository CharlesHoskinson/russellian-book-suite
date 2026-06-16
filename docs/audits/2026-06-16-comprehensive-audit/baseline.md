# Audit baseline — 2026-06-16

**Commit:** 86c478ba9533f2bc975e8541673245a7f6e8c188 (branch `audit/2026-06-16-comprehensive`, off `main`)
**Method:** graphify-partitioned hybrid matrix, parallel `Agent` subagents, adversarial verification of Critical/High. Static analysis on Windows + per-subsystem pytest where deps install cleanly.
**Graph:** `graphify-out/` — 16,264 nodes, 22,391 edges, 1,394 communities.

## Scope (git ls-files counts)

| Subsystem | Python | Tests | Notes |
|---|---|---|---|
| book-knowledge | 62 | 43 | RDF/SPARQL/SHACL + claims ledger (core) |
| book-compose | 51 | 35 | composition |
| book-thesis | 12 | 15 | |
| paragraph-weaver | 30 | 15 | |
| russellian-style | 56 | 51 | |
| feynman-style | 34 | 19 | |
| triadic-voice | 0 | 0 | SKILL.md-only (new since prior audit) |
| halmos | 13 | 6 | |
| book-review | 14 | 10 | |
| review-conductor | 19 | 20 | |
| book-qa | 19 | 34 | release gate |
| iacr-review | 4 | 2 | |
| iacr-math-prose | 0 | 0 | template-only |
| neurosym-forge | 97 | 100 | scaffolding + booklogic |
| scrapling-fetch | 26 | 18 | |
| syntopical-metabook | 76 | 55 | now full-pytest (PR #225) |
| verifiers (rust) | 49 .rs | — | 4 crates |
| verifiers (cljs/edn) | 119 | — | orchestrators + booklogic rules |
| tools | 68 .py | — | voice-corpus, corpora, readme-lint, synthesis |
| ci + nix + .github | 30 | — | audited 2026-06-16 (PRs #224/#225) |

## Prior audit (2026-05-29) — reconciliation anchor

136 raised, **115 confirmed (7 critical, 29 high, 41 medium, 35 low, 3 info)**. Top criticals:
1. **Verifier chain doesn't verify** — 5/7 criticals on the cljs `nl_to_fol` → Rust `smt.rs`/`kg.rs` path (contract mismatches, dropped `Edn::UInt`, missing KG relations).
2. **book-qa gate under-blocks** — `sentinel.py:62` routes D9–D13 to the soft gate; they never block release.
3. **Branch-protection drift** — `branch-protection.md` / `ruleset-apply.sh` require old split-job check names that `ci.yml` no longer emits.
4. **Supply-chain** — actions pinned to mutable tags (LIKELY FIXED — current CI is SHA-pinned), `no-direct-http` vacuous contract, `no_shadow_writes` only patched `builtins.open` (LIKELY FIXED — now covers pathlib + os.open).

Each subsystem agent reconciles its slice against the relevant `docs/audits/2026-05-29-suite-wide-end-to-end-review/findings-*.md` file (fixed / still-open / new).

## Baseline test + lint status

Per-suite pytest pass counts are gathered by the subsystem agents (each installs its own deps and runs `pytest`), aggregated into the final report. Ruff and the `ci/` suite were verified green on `main` as of PRs #224/#225 (2026-06-16).
