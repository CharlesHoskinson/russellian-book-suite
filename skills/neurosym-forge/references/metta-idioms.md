# MeTTa idioms in CLJS + Rust

This reference maps the seven core MeTTa idioms onto the CLJS+Rust substrate used by `neurosym-forge`-scaffolded projects.

## `(= lhs rhs)` — equality declaration

A MeTTa equality declares `lhs` rewritable to `rhs`. In the scaffold:

- Stored as a rewrite-rule record in `rules/*.edn` with shape `{id, lhs, rhs, doc, tags}`
- Applied via `meander.epsilon/rewrite` in `cljs-orchestrator/src/main/<slug>/nl_to_fol.cljs`
- Variable-balance is enforced: every free `?x` on `rhs` must appear on `lhs` unless tagged `eliminating`

Add a rule via `add_rewrite_rule.py`. Never hand-edit `rules/*.edn` — the checksum linter will flag it.

## `(: x T)` — type declaration

Every atom carries a `:sort` field. Sorts are primitive keywords (`:int`, `:real`, `:bool`, `:entity`), function types (`{:kind :fn :args [...] :ret ...}`), or enums (`{:kind :enum :members [...]}`).

malli `m/=>` schemas at every function boundary in `phases.cljs` enforce sort consistency at runtime.

Add a sort via `add_sort.py`.

## `!expr` — force evaluation

EDN atoms tagged `^:force` are evaluated immediately by the CLJS phase driver and replaced in-place with the result. In v0.1 this only kicks in on grounded atoms whose CLJS thin shim is annotated `:force` — a deferred backend call becomes synchronous.

## `(match $space pattern template)`

The atomspace is the cozo store + `core.logic.pldb` in-memory. A query is a `core.logic/run*` form over a cozo Datalog clause, then a meander template substitution. See `cljs-orchestrator/src/main/<slug>/unify.cljs`.

## `(superpose (a b c))` / `(collapse expr)`

Non-deterministic branching. The CLJS driver wraps an alternative set in `lazy-seq`. Each branch is shipped to Rust as a separate `assert_and_track` block with a per-branch tracker; the verdict EDN reports which branch was chosen.

`collapse` is the inverse: reduce the lazy-seq to a single verdict.

## Grounded atoms

A grounded atom is a host-language value or function. In the scaffold:

- Declared in `rules/grounded.edn`
- Backed by a `#[napi]` Rust function in `rust-verifier/src/<lib>.rs`
- Reachable from CLJS through a thin shim in `bridge.cljs`

Add one via `add_grounded_atom.py`. Default libraries: `z3`, `egg`, `cozo`, `tectonic`, `custom`.

## Self-reflection

`rules/*.edn` is data. The skill's `add_*` helpers are the only sanctioned editors; manual edits are detected via checksums in `rules/.checksums.edn` and flagged by `lint_rewrite_coverage.py`.

Each scaffolded project is itself a Claude Code skill (it ships its own `SKILL.md`). The forge scaffolds skills.
