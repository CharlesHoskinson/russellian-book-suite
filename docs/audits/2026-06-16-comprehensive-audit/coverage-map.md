# Coverage map — graphify communities + test coverage

## Audit coverage vs graphify

11 subsystem agents + 1 cross-cutting + 1 targeted follow-up covered every subsystem in `git ls-files`. Mapping the findings back to graphify's top-10 god nodes and largest communities:

| God node (degree) | Subsystem | Covered by |
|---|---|---|
| `frequencies` (497) | feynman/russellian delta-scoring | **targeted follow-up** (found H-07) — was the initial gap |
| `Keyword` (199) | EDN reader (shared) | verifiers + cross-cutting (found H-08) |
| `abstract_inverted_index` (127) | (OpenAlex fixture) | follow-up — **no code surface**, anticipated bug absent |
| `WorkspaceLayout` (97) | book-knowledge | book-knowledge agent |
| `init_workspace()` (87) | book-knowledge | book-knowledge agent |
| `Correctness & bugs — findings` (68) | (prior-audit doc, not source) | n/a |
| `EdnVector`/`EdnList`/`Symbol` | EDN reader | verifiers + cross-cutting |
| `append_claim()` (40) | book-knowledge ledger | book-knowledge agent |

The coverage check flagged one initial gap — the delta-scoring / corpus-vocabulary cluster (Communities 0 and 1, the two largest) — which the targeted follow-up then closed (finding H-07). No high-centrality community is left unaudited.

The 7 graphify "import cycles" are all self-reference artifacts (one stdlib-only Python file; six intra-file Rust `#[test]` matches) — not real cycles. The "surprising connection" cross-community bridges (neurosym-forge ↔ verifier `_edn_reader`) are same-package name matches, **except** they surfaced the real H-08 (the EDN reader is genuinely duplicated 5×, 3 copies stale).

## Test-coverage gap map (for the remediation coverage track)

Measured by running the suites + reading tests vs scripts:

| Area | State | Gap |
|---|---|---|
| book-knowledge | 174✓ | malformed-LLM input to `generate_for_claim` untested |
| review/QA | 68/55/34/6✓ | **gate exit-codes (`main()`) never asserted** — highest-leverage gap; malformed score-dict untested |
| neurosym-forge | 517✓ | bake test asserts only returncode, not codegen output; no toolchain-free structural validation; tautology gate has no production test |
| feynman-style | 45✓ | **delta scorer smoke-only** — no known-answer test (let H-07 through) |
| verifiers (Rust) | bermuda+osmotic have `tests/`; adsc+epi inline-only | **no test feeds the cljs-emitted shape** through `verify_formulas` (let C-001/C-002 through) |
| verifiers (cljs) | bermuda full; **epi/osmotic booklogic-only** | no `nl_to_fol`/`phases`/bridge tests; **only bermuda runs in CI** |
| tools | build-voice-corpus 58✓, build-russell-corpus✓ | **nothing under tools/ runs in CI**; 14/15 one-shots untested; 4 live canonical-artifact writers have zero coverage |
| Clojure deps | n/a | no CVE scanning (no Dependabot ecosystem) |
| darwin flake | n/a | `supportedSystems` darwin never `nix flake check`'d |

**Coverage targets for remediation:** (1) a per-verifier cljs CI leg + bridge round-trip test; (2) gate exit-code tests for book-qa; (3) a `tools/` CI entry with round-trip/idempotency tests for the 4 canonical writers; (4) a known-answer test for the Feynman delta; (5) a codegen-output assertion in the bake test; (6) a vendored-`_edn_reader` checksum gate; (7) a Clojure CVE-scan nightly job; (8) a darwin `nix flake check` leg.
