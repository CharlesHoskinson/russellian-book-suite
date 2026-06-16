# Findings — verifier layer (Rust + ClojureScript)

The neurosymbolic verifier layer is where the defects concentrate. Root cause: the four verifiers are **hand-maintained copies that have drifted into four distinct states**. The prior audit's #1 critical (the cljs→Rust contract) was fixed in 2 of 4 crates only.

## Critical: the cljs→Rust verify bridge is dead in epidemiology + osmotic_pressure

**C-001 / C-002.** Confirmed three independent ways (Rust-side agent, cljs-side agent, direct grep).

- `phases.cljs:19` (epidemiology, osmotic_pressure): `(b/verify-formulas (pr-str formulas))` — a **bare vector**. bermuda/adsc send `(pr-str {:version 1 :atoms formulas})`.
- `nl_to_fol.cljs:11-34` (epi, osmotic): emit the nested `{:kind :expression :sort :formula :head {…} :args […]}` tree (grep: 5 `:head`, 0 `:predicate`). bermuda/adsc emit the flat `{:kind :expression :id :predicate :subject :value}` atom (grep: 0 `:head`, 3 `:predicate`).
- Rust consumer: `parse_formulas` requires a top-level `{:atoms […]}` map → `Err("missing or non-vector :atoms")` on a bare vector; even past that, `bind_atoms`/`check_all` read flat `:predicate`/`:subject` and `_ => continue` on nested atoms → solver asserts nothing → trivially `:sat`.
- osmotic is worse: its Rust side is the *newest* partitioned Phase-J engine (9 integration tests), so producer and consumer are maximally out of sync; and the osmotic `ir.cljs Formula` malli schema still `= Atom` (nested), so the broken shape passes the `:pre`/`:post` contracts and reaches the addon — a live path, not dead code.

**Fix:** port bermuda's `legacy-claim->formula` (flat atom), the `{:version 1 :atoms formulas}` wrapper, and the `ir.cljs Formula = [:or FlatExpression OpaqueMarker]` schema to epidemiology and osmotic_pressure. **Confidence: high.**

**C-003.** epidemiology/osmotic_pressure have only `booklogic_test.cljs` — no `nl_to_fol_test`/`phases_test`/bridge test. `.github/workflows/nightly.yml` runs one cljs job, `cljs-bermuda-test`. The Rust integration tests hand-write the flat `{:atoms …}` shape, so `cargo test` is green while the cljs producer emits an unconsumable shape. **Fix:** add flat-atom `nl_to_fol_test` per verifier and a per-verifier cljs CI leg (matrix over the 4).

## High

- **H-03 — kg runs on empty claims (all 4).** `lib.rs:26` calls `kg::ingest_and_summarize(&v.verified)`, but no code writes `Verdict.verified` (declared `ir.rs:42`, only ever defaulted). Through napi, `build_db` always gets 0 claims; bermuda's Q001 contradiction query can't fire; `claim_count` is always 0. Only the direct-call `kg_ingest.rs` test exercises kg with real claims. **Fix:** populate `v.verified` from the parsed claims before the kg block.
- **H-04 — epidemiology `?`-prefix false sat.** `smt.rs:70-74` builds var names with `format!("{}_{}", predicate.trim_start_matches(':'), subject.trim_start_matches(':'))` — strips `:` only. `?dose` → `?dose_?p`, `:dose` → `dose_p`: contradictory bindings on one logical symbol come out `:sat`. adsc's `question_prefixed_predicate_canonicalises_to_same_symbol` test guards exactly this. **Fix:** add a `var_name.rs` mirroring adsc/bermuda and call it.
- **H-08 — stale vendored `_edn_reader.py` (3 of 5).** md5-verified: neurosym-forge (canonical, 295 lines) == adsc-clinical; bermuda/epidemiology/osmotic_pressure are byte-identical at 291 lines and miss a 4-line bare-`/` Symbol fix → mis-parse a `/` Symbol. No CI sync guard (`.checksums.edn` covers only `rules/*.edn`). **Fix:** add a vendored-file checksum gate, or re-scaffold the 3 stale verifiers.
- **H-09 — lossy lift-merge (epi/osmotic).** `booklogic.cljs:469` `(into {} (map …))` drops all but the last lift for a duplicate predicate; bermuda/adsc use a `reduce` that appends `:patterns`. Latent (epi/osmotic lifts.edn have no duplicates yet); bermuda relies on the merge (5 duplicate groups). **Fix:** port the `reduce`-merge.

## Medium

- **M — bermuda/osmotic dropped the `Edn::Str` predicate/subject arm.** `bind_atoms` matches `Edn::Key` only and `_ => continue`; adsc/epidemiology also accept `Edn::Str`. The contract permits string predicates (ir.rs doc + tests), so a string-form atom is silently skipped → under-constrained → false `:sat`. **Fix:** add the `Edn::Str` arm or document keyword-only as the hard contract.
- **M — adsc `approx=` tolerance silently dropped.** `booklogic.cljs:242` recognizes only `~=`; adsc's own `constraints.edn` uses `(approx= …)`, so `extract-tolerance` returns nil and the constraint's `:tolerance` is dropped from codegen, weakening generated Z3. epi/osmotic recognize both. **Fix:** unify to `#{'approx= '~=}` in all four.
- **M — no Rust test exercises the cljs-emitted shape.** Every Rust test hand-writes the flat `:atoms` shape the Rust side wants, never the shape the cljs translator emits — which is why C-001/C-002 ship green. **Fix:** add a round-trip test from `translate-corpus` output through `verify_formulas` asserting a real `:unsat`.

## Low / Info

- `eqsat.rs:65,95` `runner.roots[0/1]` indexing — safe today (no empty-roots path); noted for the FFI-panic dimension. No `unsafe`/`unwrap`/`expect`/panic exists on any production (non-test) Rust path; the napi boundary is panic-safe.
- `prove_equiv`/`canonicalize` (eqsat) are not referenced by any `axioms.rs` — the eqsat backend is not yet wired into constraint discharge (latent, not a regression).
- epi/osmotic `infer-value-kind` missing the `parse-bool → :bool` arm bermuda/adsc have (latent).

## Reconciliation of the prior verifier criticals

| Prior critical | Status |
|---|---|
| `smt.rs` flat-atom vs nested-tree contract | **FIXED in bermuda + adsc; STILL OPEN in epidemiology + osmotic (C-001/C-002)** |
| `phases/verify` bare-vector vs `{:atoms …}` | **FIXED in bermuda + adsc; STILL OPEN in epi + osmotic** |
| `kg.rs` queries undefined relations → Err | **FIXED** (bermuda creates relations; epi/osmotic/adsc dropped the query) — but kg now runs on empty input (H-03) |
| adsc `smt.rs` missing `Edn::UInt` arm → false sat | **FIXED** (all 4 have the UInt arm, with tests) |
| bermuda/adsc near-duplicates drifted | **WORSE — now a 4-way drift** (see table) |

## 4-way drift table

| Aspect | adsc-clinical | bermuda | epidemiology | osmotic_pressure |
|---|---|---|---|---|
| cljs emits flat atom | ✅ | ✅ | ❌ nested | ❌ nested |
| `phases/verify` wraps `{:atoms …}` | ✅ | ✅ | ❌ bare vector | ❌ bare vector |
| **→ cljs→Rust verify works** | ✅ | ✅ | **❌ BROKEN** | **❌ BROKEN** |
| `Edn::UInt` arm | ✅ | ✅ | ✅ | ✅ |
| var-name canonicaliser (`:`+`?`) | `var_name.rs` | `var_name.rs` | ❌ inline, `:` only | `canonical.rs` |
| predicate/subject accepts `Edn::Str` | ✅ | ❌ Key-only | ✅ | ❌ Key-only |
| booklogic lift-merge | reduce ✅ | reduce ✅ | lossy `into {}` ❌ | lossy `into {}` ❌ |
| booklogic `approx=` recognized | ❌ `~=` only (live `approx=`!) | ❌ `~=` only | ✅ | ✅ |
| `_edn_reader.py` bare-`/` fix | ✅ | ❌ stale | ❌ stale | ❌ stale |
| kg.rs | empty stub | relations + Q001 | claim-only stub | claim-only stub |
| `v.verified` populated for kg | no | no | no | no |
| cljs tests | nl_to_fol+booklogic | full (8 files) | **booklogic only** | **booklogic only** |
| run in CI nightly | no | **yes** | no | no |

**Two fix lineages:** bermuda+adsc have the flat-atom bridge fix but the older `~=`-only recognizer; epi+osmotic have the newer `approx=` recognizer but the broken nested-tree bridge. **No single verifier is fully current.** The durable fix is to stop hand-maintaining four copies — generate them from one source, or sync-check the vendored files.
