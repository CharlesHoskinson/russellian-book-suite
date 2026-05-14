# MeTTa idioms in CLJS + Rust

This reference maps the core MeTTa idioms onto the CLJS+Rust substrate used by `neurosym-forge`-scaffolded projects.

## `(= lhs rhs)` — function expression

In MeTTa, `(= lhs rhs)` is a *function expression*: `lhs` is a recognition template (a pattern over atoms), and `rhs` is the body that replaces any matching expression. Multiple clauses with the same head give pattern-matched function-definition behaviour. The term "equality declaration" is colloquial; MeTTa's authoritative term is "function expression".

In the scaffold:

- Stored as a flat rewrite-rule record in `rules/*.edn` with shape `{id, lhs, rhs, doc, tags}`
- Applied via `meander.epsilon/rewrite` in `cljs-orchestrator/src/main/<slug>/nl_to_fol.cljs`
- Variable-balance is enforced: every free `?x` on `rhs` must appear on `lhs` unless tagged `eliminating`

Add a rule via `add_rewrite_rule.py`. Never hand-edit `rules/*.edn` — the checksum linter will flag it.

## `(: x T)` — type assignment

In MeTTa, `(: x T)` is a *type assignment*: atom `x` has type `T`. Function types are written `(-> T1 T2 ... Ret)` in native MeTTa.

In the scaffold, every atom carries a `:sort` field. Sorts are primitive keywords (`:int`, `:real`, `:bool`, `:entity`), function types (`{:kind :fn :args [...] :ret ...}`), or enums (`{:kind :enum :members [...]}`). In native MeTTa, function types use `(-> T1 T2 ... Ret)`; the EDN IR encodes this as `{:kind :fn :args [...] :ret ...}`.

malli `m/=>` schemas at every function boundary in `phases.cljs` enforce sort consistency at runtime.

Add a sort via `add_sort.py`.

## `!` — top-level evaluation directive

In MeTTa, `!` is a **top-level directive**: prefixing a top-level atom with `!` causes it to be evaluated and the result returned to the user, rather than added to the atomspace as data. It is not an in-expression force-evaluation operator — it acts only at the top level of a MeTTa program or REPL session.

The scaffold's `^:force` metadata is an analogy, not a direct encoding. EDN atoms tagged `^:force` are evaluated immediately by the CLJS phase driver and replaced in-place with the result; in v0.1 this applies only to grounded atoms whose CLJS thin shim is annotated `:force`. The intent is similar — skip storage, produce a value now — but the mechanism and scope differ from MeTTa's `!`.

## `(match $space pattern template)`

Queries the named atomspace (`$space`) for atoms matching `pattern`, then projects each match through `template`. The conventional self-reference to the current atomspace is `&self`, so the standard idiom is `(match &self pattern template)`.

In the scaffold, the atomspace is the cozo store plus `core.logic.pldb` in-memory. A query is a `core.logic/run*` form over a cozo Datalog clause, then a meander template substitution. See `cljs-orchestrator/src/main/<slug>/unify.cljs`.

## `(superpose (a b c))` — non-determinism

Produces non-deterministic branching: all of `a`, `b`, `c` are possible results simultaneously. The CLJS driver wraps an alternative set in `lazy-seq`. Each branch is shipped to Rust as a separate `assert_and_track` block with a per-branch tracker.

## `(collapse expr)` — reification

`collapse` converts a nondeterministic result into a tuple of all branches. It does not reduce to a single verdict; it collects every branch `expr` can produce and returns them as a tuple.

In the scaffold, the CLJS driver collects each branch from the `lazy-seq` and the verdict EDN reports which branch was chosen and why. The collapse here selects one branch (the Rust verifier's chosen verdict) — a stronger reduction than MeTTa's tuple-returning `collapse`.

## Grounded atoms

A grounded atom is a host-language value or function. In the scaffold:

- Declared in `rules/grounded.edn`
- Backed by a `#[napi]` Rust function in `rust-verifier/src/<lib>.rs`
- Reachable from CLJS through a thin shim in `bridge.cljs`

Add one via `add_grounded_atom.py`. Default libraries: `z3`, `egg`, `cozo`, `tectonic`, `custom`.

## Self-reflection

In MeTTa, self-reflection is a **runtime** capability: programs read and modify their own atomspace via `add-atom`, `remove-atom`, and `get-atoms` on `&self`. Any MeTTa expression can inspect or extend the live atomspace.

The scaffold encodes a **restricted** form: build-time, helper-mediated, checksummed. `rules/*.edn` is data, but the skill's `add_*` helpers are the only sanctioned editors. Manual edits are detected via checksums in `rules/.checksums.edn` and flagged by `lint_rewrite_coverage.py`. This is a safety policy — controlled mutation in place of MeTTa's open runtime self-modification.

Each scaffolded project is itself a Claude Code skill (it ships its own `SKILL.md`). The forge scaffolds skills.

---

## What this mapping does NOT cover

The sections above cover the idioms the scaffold encodes directly. Several MeTTa concepts appear in real programs and grounded-atom implementations but are outside the scaffold's current scope:

- **`&self`** — the conventional symbol for the current atomspace, used in `(match &self ...)`. The scaffold calls its store the "atomspace" but does not expose `&self` as a first-class binding.
- **`(-> T1 T2 ... Ret)`** — MeTTa's native function-type notation. The EDN IR uses `{:kind :fn :args [...] :ret ...}` instead.
- **`(let $var value body)`** — sequential binding, ubiquitous in real MeTTa programs. The scaffold has no direct equivalent; CLJS `let` is used in generated code instead.
- **`Empty` / `NotReducible`** — special non-result atoms. `Empty` signals no result; `NotReducible` signals that an expression cannot be reduced further. Grounded atoms that interact with match results need to handle both.
- **`collapse-bind` / `superpose-bind`** — the minimal-MeTTa primitives underlying `collapse` and `superpose`. The scaffold works at the higher-level `collapse`/`superpose` abstraction.

Writing a grounded atom that interacts with any of these requires reading the Hyperon docs at https://trueagi-io.github.io/hyperon-experimental/metta/.
