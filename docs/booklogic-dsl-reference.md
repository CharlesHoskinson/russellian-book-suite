# BookLogic DSL Reference

> Canonical author-facing reference for the BookLogic v0.4 declaration-form
> DSL. For wire-format / atomspace details see
> [`skills/neurosym-forge/references/atomspace-edn.md`](../skills/neurosym-forge/references/atomspace-edn.md).
>
> Companion documents:
> - [`grounded-atoms.md`](../skills/neurosym-forge/references/grounded-atoms.md) — Python-regex dialect for `:when` patterns.
> - [`phase-boundaries.md`](../skills/neurosym-forge/references/phase-boundaries.md) — what data crosses each phase boundary.
> - [`rewrite-rule-style.md`](../skills/neurosym-forge/references/rewrite-rule-style.md) — naming and stub-status of `defrule`.
> - [`worked-examples/osmotic-pressure/clojure.md`](../skills/neurosym-forge/references/worked-examples/osmotic-pressure/clojure.md) — narrative walkthrough.
> - [`SUPPORT_MATRIX.md`](../skills/neurosym-forge/SUPPORT_MATRIX.md) — live vs stub backend status.

This document satisfies **REQ-BOOKLOGIC-047** (seven form-family coverage) and
**REQ-BOOKLOGIC-048** (Debugging section).

## 1. DSL philosophy

BookLogic is a typed declarative DSL for **what to verify**; the framework
decides **how** to verify (Z3 / egg / Cozo). Authors write seven form
families — `defsort`, `defpredicate`, `deflift`, `defrule`,
`defconstraint`, `defquery`, `defremedy` — and the compiler chooses
backends per form. The author never writes solver code; the framework
emits it.

Every form is declarative. There is no procedural code in BookLogic source.
The CLJS compiler (`<project>/cljs-orchestrator/src/main/<slug>/booklogic.cljs`,
produced from `assets/project-template/cljs-orchestrator/.../booklogic.cljs.tmpl`)
expands forms into intermediate EDN files under `verifiers/<project>/rules/`;
Python codegen scripts (`skills/neurosym-forge/scripts/codegen_axioms.py` and
`codegen_kg.py`) consume those intermediates and emit Rust source under
`verifiers/<project>/rust-verifier/src/`.

Strong typing via sorts is the DSL's main lever for ruling out bugs early.
`defpredicate` declares argument-sorts and a return-sort at compile time;
mismatch between a `deflift` `:emit` value type and the predicate's
return-sort surfaces during nbb expansion, not at solver time. The cost
is one extra layer of typing: the `defsort` registry must include every
domain entity *before* a predicate can reference it.

## 2. Form reference

The seven form families below sit in the seven `.edn` files under
`verifiers/<project>/rules/booklogic/`:

| Form family    | File                                               | Backend(s)         | Status                         |
|----------------|----------------------------------------------------|--------------------|--------------------------------|
| `defsort`      | `rules/booklogic/sorts.edn`                        | (registry only)    | live                           |
| `defpredicate` | `rules/booklogic/predicates.edn`                   | (registry only)    | live                           |
| `deflift`      | `rules/booklogic/lifts.edn`                        | Python ingester    | live                           |
| `defrule`      | `rules/booklogic/rules.edn`                        | egg (planned)      | stub — CLJS only               |
| `defconstraint`| `rules/booklogic/constraints.edn`                  | z3 / egg / cozo    | z3 live; egg, cozo silent-drop |
| `defquery`     | `rules/booklogic/queries.edn`                      | cozo               | builder live; consumer stub    |
| `defremedy`    | `rules/booklogic/remedies.edn`                     | (external)         | declarative only               |

### 2.1 `defsort`

Declare a domain entity type. Sorts declared here may appear in
`defpredicate` argument-sort and return-sort positions. The four base
sorts (`:int`, `:real`, `:bool`, `:string`) are implicit; only
domain-specific entity types need a `defsort`.

#### Surface syntax

```
(defsort NAME)
```

Where `NAME` is an EDN Keyword in `:kebab-case`. There are no keyword
arguments. The form has no body.

#### Compilation target

`booklogic.cljs`'s `expand-sorts` builds a `:sort-registry` set keyed by
keyword. No Rust source is emitted directly; the registry is consulted
during `defpredicate` validation, after which the sort name appears only
implicitly (as the predicate's argument list).

Phase A's `lint_atomspace.py` cross-checks the sort registry against
references in `predicates.edn`; any predicate arg-sort that names an
undeclared sort fails the build.

#### Worked example

From `verifiers/osmotic_pressure/rules/booklogic/sorts.edn`:

```edn
{:forms
 [(defsort :solution)]}
```

The osmotic-pressure verifier talks about a single domain entity — the
aqueous solution. One `defsort` covers every predicate's argument
position.

For a multi-entity domain (specimen vs reagent, solute vs solvent,
chapter vs section), declare each sort separately:

```edn
{:forms
 [(defsort :specimen)
  (defsort :reagent)
  (defsort :reaction)]}
```

#### Anti-patterns

- **Uppercase names.** `(defsort :Solution)` — the convention is
  `:kebab-case`. The expander does not normalise; `:Solution` and
  `:solution` are distinct keys, and a predicate declared
  `[:Solution]` will OPAQUE-fail when matched against atoms whose
  `:subject` lifts to `:solution`.
- **Redeclaring primitives.** `(defsort :real)` shadows the base
  Real sort. The expander does not warn; the redeclared sort becomes
  a no-op key but signals intent confusion to readers. Reserve
  `:int`, `:real`, `:bool`, `:string` for the implicit set and never
  declare them.
- **Sort proliferation.** A `defsort` per claim id, or one per
  chapter, defeats the typing system — predicates devolve to
  `Any -> Real`. Sorts are domain entities, not record ids. The
  osmotic-pressure verifier deliberately ships exactly one sort.

### 2.2 `defpredicate`

Declare a named observable — a function from one or more sorts to a
return-sort. Predicates are the application heads in
`(predicate subject value)` atoms; `defpredicate` is how the framework
learns that `:molarity` takes a `:solution` and returns a `:real`.

#### Surface syntax

```
(defpredicate :NAME [:ARG-SORT-1 :ARG-SORT-2 ...] :RETURN-SORT)
```

Where:

- `:NAME` is an EDN Keyword in `:kebab-case`.
- The argument-sort vector is one or more Keywords; each MUST be
  either a base sort (`:int`, `:real`, `:bool`, `:string`) or a
  Keyword previously declared via `defsort`.
- `:RETURN-SORT` is a single Keyword, same rule as arg-sorts.

There are no other keyword arguments. The form does not carry a doc
string today; convention is to keep the predicate name self-describing.

#### Compilation target

`booklogic.cljs`'s `expand-predicates` validates each arg-sort and
return-sort against the `:sort-registry` from `expand-sorts`. The
expander emits a `:predicate-registry` map keyed by the predicate
Keyword, with value `{:arg-sorts [...] :return-sort ...}`.

Tier 1's REQ-EDN-052 wraps this map in a `booklogic-schema.edn` artifact
shipped to consumers (book-qa, future tooling); the schema is what makes
predicate signatures available off-machine without re-running the CLJS
expander.

#### Worked example

From `verifiers/osmotic_pressure/rules/booklogic/predicates.edn`:

```edn
{:forms
 [(defpredicate :osmotic-pressure-pa [:solution] :real)
  (defpredicate :vant-hoff-i         [:solution] :real)
  (defpredicate :molarity            [:solution] :real)
  (defpredicate :temperature-k       [:solution] :real)]}
```

Four predicates, all `[:solution] :real`. Note that `:vant-hoff-i` is
declared `:real` even though physical values are typically integer
(1 for sucrose, 2 for NaCl, 3 for CaCl₂). The constraint axiom
multiplies four Real-valued quantities; declaring `i` as `:int` would
force an Int-to-Real cast at every use and risk a sort-mismatch crash
under partial evaluation.

#### Anti-patterns

- **Uppercase predicate names.** `(defpredicate :OsmoticPressurePa ...)`
  — the deflift `:emit` clause will produce atoms with predicate key
  `:OsmoticPressurePa`, but external consumers and human readers
  expect `:osmotic-pressure-pa`. Worse, mixed-case bypasses the
  predicate-registry lookup in some emitter paths and falls through
  to an OPAQUE atom silently.
- **Missing arg-sort vector.** `(defpredicate :molarity :real)` —
  this elides the arg-sorts and looks like a constant declaration.
  The expander hard-errors at nbb time with "expected arg-sort vector".
- **`:int` predicate fed a decimal regex.** Declaring
  `(defpredicate :count [:solution] :int)` but writing a deflift that
  emits `(parse-float ?v)` produces an atom whose `:value` is
  `Edn::Double`; `smt.rs` binds it to a Real Z3 variable, then the
  constraint comparing it against an Int-typed predicate yields a
  Z3 sort mismatch and an `:unknown` verdict. Match the parser to
  the declared sort: `:int` ↔ `parse-int`, `:real` ↔ `parse-float`.
- **Argument-position arity drift.** A predicate declared
  `[:solution]` referenced as `(:molarity ?s1 ?s2)` in a constraint:
  the CLJS validator catches arity mismatch at expand time, but the
  authoring-time error message is terse ("arity") and lands far from
  the offending constraint. Keep arities small (one or two arg-sorts)
  to minimise this risk.

### 2.3 `deflift`

Map prose to atoms. Each `deflift` is a regex-with-`:emit` rule that
turns a claim's canonical text into a grounded atom. The Python
ingester loops over claims; each claim is matched against every active
lift; the first matching lift produces an atom, the rest are skipped.
A claim with no matching lift produces an `:OPAQUE` atom.

#### Surface syntax

```
(deflift NAME
  :from :claim/canonical-text
  :when "PYTHON-REGEX-WITH-NAMED-GROUP"
  :emit (fact ?claim-id SUBJECT :predicate-name VALUE-EXPR)
  :word-to-int {"one" 1 "two" 2 ...})  ; optional
```

Where:

- `NAME` is `L###-kebab-case` — `L` for *lift*, three-digit number,
  kebab-case suffix. Allocate sequentially within the project.
- `:from` is always `:claim/canonical-text` today. The intent is
  forward-compatible: a future Tier might match against
  `:claim/title` or `:claim/locator-text` separately.
- `:when` is a Python regex (the dialect; the ingester is Python).
  Use `(?P<v>...)` for named groups — NOT JS-style `(?<v>...)`.
  Bind the value group `v`; additional groups are allowed but only
  `?v` is plumbed through to the `:emit` clause by default.
- `:emit` is a sexp of the form
  `(fact ?claim-id SUBJECT :predicate VALUE-EXPR)` where:
  - `?claim-id` is the literal symbol `?claim-id` — always there.
  - `SUBJECT` is the subject placeholder — conventionally `:s`
    (literal Keyword) in lift bodies and `?s` (logic variable)
    in constraint bodies. Both surface as `:subject :s` on the
    atom; the `?s`/`:s` distinction is cosmetic and signals
    binding intent to readers.
  - `:predicate` is the Keyword id of a declared predicate.
  - `VALUE-EXPR` is one of: `(parse-float ?v)`, `(parse-int ?v)`,
    `(parse-bool ?v)`, `(string ?v)` (passthrough), or
    `(lookup ?v)` (use `:word-to-int` map).
- `:word-to-int` (optional) is a `{"word" 7 ...}` map used by
  `(lookup ?v)` to coerce English numerals. Used by domains where
  claims say "the answer is seven" rather than "the answer is 7".

#### Compilation target

`booklogic.cljs`'s `expand-lifts` validates predicate references
against the `:predicate-registry`, then emits `rules/predicates.edn`
(the runtime artifact, distinct from `rules/booklogic/predicates.edn`
which is the BookLogic source). The runtime form is consumed by the
Python ingester via `scripts/ingest_ledger.py`.

The runtime `rules/predicates.edn` is the EDN map shown earlier in
`grep` output: one entry per predicate, with `:patterns` listing the
regex strings, `:subject` the canonical subject keyword, `:value-kind`
the parser tag, and `:word-to-int` the (possibly empty) lookup table.

#### Worked example

From `verifiers/osmotic_pressure/rules/booklogic/lifts.edn`:

```edn
(deflift L002-vant-hoff-i
  :from :claim/canonical-text
  :when "(?i)van[' \\s]*t\\s*Hoff(?:\\s+factor)?\\s*(?:i\\s*)?(?:=|is|of)?\\s*(?P<v>[0-9]+(?:\\.[0-9]+)?)"
  :emit (fact ?claim-id :s :vant-hoff-i (parse-float ?v)))
```

Breakdown of the regex:

- `(?i)` — case-insensitive flag.
- `van[' \\s]*t` — allow apostrophe and/or whitespace between
  `van` and `t`. Real text says `van 't Hoff`, `van't Hoff`,
  `van t Hoff` — the character class with `*` quantifier accepts
  all three.
- `\\s*Hoff` — `Hoff` with leading optional whitespace.
- `(?:\\s+factor)?` — non-capturing optional "factor".
- `(?:i\\s*)?` — non-capturing optional `i` literal.
- `(?:=|is|of)?` — non-capturing optional connector.
- `(?P<v>[0-9]+(?:\\.[0-9]+)?)` — the value capture: an integer
  or decimal.

Note the doubled backslashes: EDN string syntax requires escaping
inside double-quoted strings, so a Python regex `\s` is written
`\\s` in EDN source.

#### Anti-patterns

- **JS-style named groups.** `(?<v>...)` instead of `(?P<v>...)` —
  the Python `re` module rejects this at compile time; the
  ingester emits a parse failure for the whole claim ledger.
  The annotated template warns; the Tier 2 follow-up will remove
  the silent JS-to-Python converter that masks this today.
- **Missing `?claim-id` in `:emit`.** The fact head MUST be
  `?claim-id` — the ingester wires up provenance from that
  position. A `:emit` of `(fact :s :predicate ?v)` omits the
  binding and orphans the resulting atom from its claim.
- **Unbound subject.** A `:emit` like
  `(fact ?claim-id ?obj :predicate ?v)` with `?obj` not bound
  anywhere produces an atom whose `:subject` is the literal
  symbol `?obj`. The verifier downstream tries to match this
  against constraint subjects (typically `?s`) and finds nothing.
  Convention: bind the subject literally with `:s` (the keyword)
  unless the lift legitimately extracts a subject from text
  (multi-subject domains).
- **Greedy quantifier between value and unit.** A regex like
  `osmotic\\s+pressure\\s*(.*)\\s*Pa` captures everything between
  the predicate name and the unit, including a stray sentence
  fragment. Anchor the value group tightly:
  `(?P<v>[0-9]+(?:\\.[0-9]+)?)\\s*Pa`.
- **Lift order dependency.** A lift L001 with a loose pattern
  (`molarity[^A-Za-z]*([0-9.]+)`) consumes claims that L007
  (`molarity\\s+is\\s+([0-9.]+)\\s*M`) is intended for. The
  ingester is first-match-wins; lift order in the file matters.
  Write loose lifts last.

### 2.4 `defrule`

Equality-style rewrite rule, intended for an egg-graph equality
saturation pass. **Stub today** — see § 4 of
[`rewrite-rule-style.md`](../skills/neurosym-forge/references/rewrite-rule-style.md).

#### Surface syntax

```
(defrule NAME
  :tags [:TAG-1 :TAG-2 ...]
  :confidence DOUBLE
  :doc "ENGLISH SENTENCE"
  :lhs LHS-PATTERN
  :rhs RHS-PATTERN)
```

Where:

- `NAME` is `R###-kebab-case`.
- `:lhs` and `:rhs` are sexps with free logic variables (`?a`, `?b`,
  `?s`, etc.). Every free var on `:rhs` MUST also appear on `:lhs`.
- `:tags` is a vector of Keywords (`:algebraic`, `:commutative`,
  `:domain-osmotic`, etc.).
- `:confidence` is a Double in `[0.0, 1.0]`. Convention: `1.0` for
  algebraic identities.
- `:doc` is a single English sentence of intent.

#### Compilation target

**STUB.** `defrule` expands to a `:rewrite-rules` registry consulted
by the CLJS-side `phases.cljs` for string-substitution
canonicalisation during display. The `:egg` backend in
`codegen_axioms.py` recognises `defrule`-derived constraints, but
the relevant code path is:

```python
if backend != Keyword("z3"):
    # :egg and :cozo constraints flow through other backends.
    continue
```

— the constraint is silently dropped. No Rust assertion is emitted.
No egg runner exists. Tier 3 of the roadmap promotes `defrule` from
stub to live; until then, rules in `rules.edn` participate in CLJS
display canonicalisation only.

#### Worked example

The osmotic-pressure verifier ships an empty `rules.edn`
(`{:forms []}`) — its single constraint is hand-asserted in
canonical form. A sketch of what an algebraic rule *would* look
like, once egg is live:

```edn
(defrule R001-commute-mult
  :tags [:algebraic :commutative]
  :confidence 1.0
  :doc "Multiplication is commutative."
  :lhs (* ?a ?b)
  :rhs (* ?b ?a))
```

Plus, once `R002-assoc-mult` is added, the e-graph would collapse
every permutation of `(* i M R T)` to a single canonical form before
Z3 asserts the equation.

#### Anti-patterns

- **Assuming the rule reaches Z3.** It does not, today. A
  `defrule` is a CLJS-side rewrite hint; the Z3 assertion comes
  from `defconstraint`. If you write a rule expecting Z3 to
  apply it, the verifier silently produces a `:sat` verdict
  (the rule was never used) on inputs that should be `:unsat`.
- **Unbound variable on `:rhs`.** `:rhs (* ?x 1)` where `?x`
  never appears on `:lhs` — the CLJS rewriter leaves the
  unbound `?x` in its output, producing garbled atoms downstream.
  `lint_atomspace.py` flags this.
- **Non-terminating rule.** `:lhs ?x :rhs (* ?x 1)` rewrites
  forever. Today the CLJS pass is one-shot so the loop only
  appears at fixture-test time; once egg lands, the saturation
  iteration cap is the only safeguard.
- **`:rhs`-only var without the `:eliminating` tag.** Some rules
  legitimately drop a variable
  (`:lhs (+ ?a 0)` → `:rhs ?a` is fine; the reverse is not). The
  linter trusts the `:eliminating` tag to suppress its
  free-variable check; abusing the tag turns the lint off
  globally for that rule.

### 2.5 `defconstraint`

The workhorse form. A `defconstraint` is a sat/unsat predicate
asserted to a solver. The Z3 backend is **live**; the egg and Cozo
backends are registered but silently drop the constraint today
(`codegen_axioms.py` skips them, as quoted above).

#### Surface syntax

```
(defconstraint NAME
  :backend :z3            ; or :egg (DROP) or :cozo (DROP)
  :assert (HEAD ARG ...)
  :track  :claim/id       ; optional; default :claim/id
  :on-unsat {:defect :D## :severity :critical :message "..."})
```

Where:

- `NAME` is `C###-kebab-case`.
- `:backend` is `:z3`, `:egg`, or `:cozo`. Only `:z3` produces
  runtime assertions today.
- `:assert` is a sexp; the assertion grammar is documented below.
- `:track` is the field to use as the Z3 unsat-core tracker; default
  is `:claim/id`. Custom tracking is rare.
- `:on-unsat` is a defect-class block consumed by book-qa:
  - `:defect` — a defect class Keyword (`:D13`, `:D14`, ...).
  - `:severity` — `:critical`, `:warning`, or `:info`.
  - `:message` — single-sentence human-readable explanation.

#### Assert-sexp grammar

The expressions admitted on the right of `:assert`:

- Equality: `(= LHS RHS)`.
- Approximate equality: `(approx= LHS RHS :tolerance N)` where `N`
  is a Double — the assertion is
  `abs(LHS - RHS) <= |LHS| * N` (relative tolerance).
  `~=` is accepted as an alias.
- Boolean connectives: `(and EXPR ...)`, `(or EXPR ...)`,
  `(not EXPR)`, `(=> EXPR EXPR)`.
- Comparison: `(< LHS RHS)`, `(<= LHS RHS)`, `(> LHS RHS)`,
  `(>= LHS RHS)`.
- Arithmetic: `(+ X Y ...)`, `(- X Y ...)`, `(* X Y ...)`,
  `(/ X Y)`.
- Predicate application: `(:predicate-name ?subject)` — looks up
  the Z3 variable bound to the predicate-subject pair via
  `canonical_var_name`.
- Literals: numbers, true/false, EDN strings.

#### Compilation target

Each `:backend :z3` constraint produces a block of Rust source in
`rust-verifier/src/axioms.rs`:

```rust
fn vant_hoff_C001(solver: &Solver, ...) -> Result<()> {
    let osm = Real::new_const("S__osmotic_pressure_pa");
    let i   = Real::new_const("S__vant_hoff_i");
    // ... build assertion ...
    solver.assert_and_track(&assertion, &tracker);
    Ok(())
}
```

— with variable names produced by `canonical_var_name` (REQ-EDN-042,
045, 046; golden vectors at
`skills/neurosym-forge/tests/golden/canonical_var_name.edn`). The
canonical-name function takes a predicate Keyword and a subject
Keyword and returns a stable, cross-language-identical Z3 variable
name. The Python, CLJS, and Rust implementations all agree
character-for-character.

`:backend :egg` and `:backend :cozo` pass validation but are
silently skipped — see § 2.4 above.

#### Worked example

From `verifiers/osmotic_pressure/rules/booklogic/constraints.edn`:

```edn
(defconstraint C001-vant-hoff
  :backend :z3
  :assert (approx= (:osmotic-pressure-pa ?s)
                   (* (:vant-hoff-i ?s) (:molarity ?s) 8.314 (:temperature-k ?s))
                   :tolerance 0.03)
  :track :claim/id
  :on-unsat {:defect :D13
             :severity :critical
             :message "van 't Hoff equation violated"})
```

The single constraint hand-asserts the van 't Hoff equation. With a
3% tolerance, the verifier accepts the published `π` if it agrees
with `i · M · R · T` within 3% of the published value. The clean
fixture (`i=2, M=0.154, T=298.15, π=763.27`) passes; the doctored
fixture (`i=1, M=0.154, T=298.15, π=763.27`) fails with
`C001-vant-hoff` in the unsat core.

#### Anti-patterns

- **Typoed predicate name.** `(:osmotic-pressur-pa ?s)` (missing
  `e`) — `canonical_var_name` happily produces a fresh, unbound
  Z3 variable for the typo. The constraint asserts a relationship
  between a real variable and three unrelated variables, the
  solver returns `:sat` trivially, and the verifier reports
  success on input that should be `:unsat`. There is no
  link-time check that the predicate name appears in the
  predicate registry on the constraint side. The Tier 1
  follow-up REQ-AXIOMS-051 lands this check; until then,
  cross-read every predicate ref against `predicates.edn`.
- **Int-vs-Real sort drift.** Declaring `:temperature-k` as `:int`
  but using `parse-float` in the lift — the atom binds a Real
  variable named `S__temperature_k`, the constraint binds an Int
  variable named `S__temperature_k`, and Z3 sees two distinct
  symbols of the same name. The behaviour is solver-dependent
  but typically yields `:unknown`. Match declared sort to value
  parser; the doc-comment on `defpredicate` (when present)
  should state the unit/type expected.
- **`:backend :egg` for a real assertion.** The constraint is
  silently dropped. The verifier reports `:sat` on input that
  the rule WOULD reject if egg were wired. Fail loudly on
  authoring by adding `:backend :egg` only to constraints that
  are documented as Tier 3 placeholders.
- **`:tolerance` larger than the signal.** `:tolerance 1.0`
  admits 100% relative error — every product comparison is
  trivially satisfied. Use `:tolerance` only for genuine
  measurement noise (1-5%); for exact equalities use
  `(= LHS RHS)`.
- **Hidden Boolean structure.** Nesting `(=> A (and B (or C D)))`
  in a single constraint hides the failure mode from the unsat
  core. Split into named sub-constraints with distinct
  `:on-unsat` defect classes; the core then names the actual
  failing assertion.
- **Free `?s`.** A constraint whose `:assert` references `?s`
  without binding it via predicate application (i.e., no
  `(:some-predicate ?s)` anywhere in the assertion) leaves `?s`
  as a free Z3 symbol. The verifier emits an axiom over a
  universe-of-one and returns `:sat` regardless of the data.
  Every `?s` in a constraint should appear inside at least one
  predicate application.

### 2.6 `defquery`

Datalog rule against the claim graph. Emits via `codegen_kg.py` into
`rust-verifier/src/kg.rs`, where Cozo (embedded, `cozo::DbInstance::new("mem", "", "")`)
runs the rule against an in-memory graph populated from incoming
claims.

#### Surface syntax

```
(defquery NAME
  :backend :cozo
  :body    [DATALOG-CLAUSE ...])
```

Where:

- `NAME` is `Q###-kebab-case`.
- `:backend` must be `:cozo` — only Cozo is registered:
  `SUPPORTED_BACKENDS = {Keyword("cozo")}` in `codegen_kg.py`.
- `:body` is a vector of Cozo-style Datalog clauses. Each clause
  is of the form `(head :- body-1, body-2, ...)`.

#### Compilation target

`codegen_kg.py` consumes the intermediate `rules/queries.edn`
(written by `booklogic.cljs`'s `emit-queries-edn`) and produces a
Rust source file `rust-verifier/src/kg.rs`. Each `defquery` becomes:

- A Cozo script (raw Datalog text).
- A dispatch entry in `ingest_and_summarize` that runs the script
  against the claim graph and pushes any returned row as a defect.

**Status:** the builder is live and emits valid Rust. The consumer
side (`npm run build`) does NOT run the queries by default — Cozo is
compiled in via the `kg` feature, but the orchestrator's call into
`kg.rs` is gated behind a manual code path. External consumers (book-qa,
diagnostic tools) read the generated Rust source and may run the
queries themselves. See `SUPPORT_MATRIX.md`.

#### Worked example

The osmotic-pressure verifier ships an empty `queries.edn`
(`{:forms []}`). A typical "orphan-claim" query would look like:

```edn
(defquery :Q001-orphan-claims
  :backend :cozo
  :body  [(orphan ?c) :- (:claim ?c)
                         (not (:supports-chapter ?c _))])
```

— flagging any claim that does not support any chapter, useful for
catching ingestor drift.

#### Anti-patterns

- **Assuming queries gate the verdict.** They do not, today.
  `defquery` produces declarative artifacts that external tools
  consume; the Z3 sat/unsat verdict is decided entirely by
  `defconstraint` forms. A failing query is a defect, not a
  refutation.
- **`:backend :z3` on `defquery`.** The codegen path rejects
  this immediately — `SUPPORTED_BACKENDS = {Keyword("cozo")}`
  hard-errors on any other Keyword. Spell `:cozo` explicitly.
- **Referencing an undeclared predicate in the body.** Cozo
  throws at runtime ("rule head undefined"); the `npm run build`
  pipeline does NOT lint this today. Cross-read query bodies
  against `predicates.edn` until REQ-KG-051 lands a static
  check.
- **Free variable on the head not bound in the body.** The
  Cozo compiler rejects this with a terse error. Bind every
  head-variable in at least one positive body clause.

### 2.7 `defremedy`

Proposed action when a claim is refuted. Declarative; consumed by
external workflow code (book-qa) at QA time, not inside the verifier.

#### Surface syntax

```
(defremedy NAME
  :when    CONDITION
  :propose ACTION
  :requires KEYWORD)   ; :auto-apply or :human-review
```

Where:

- `NAME` is `W###-kebab-case` (`W` for *workaround*).
- `:when` is a sexp matching against the verdict — e.g.,
  `(unsat-core-contains ?claim)` matches if `?claim` appears in
  the verdict's unsat core.
- `:propose` is a sexp describing the action — e.g.,
  `(ledger/transition ?claim :refuted)`. The action is
  vocabulary-extensible; book-qa is the consumer.
- `:requires` is `:auto-apply` (book-qa applies without prompt)
  or `:human-review` (book-qa surfaces the proposal in its
  report and waits for ack).

#### Compilation target

`booklogic.cljs` emits `:remedy-registry` and writes
`rules/remedies.edn` (the runtime artifact). The verifier itself
ignores it; book-qa reads the file when assembling the QA report.

**Status:** declarative only. The verifier does not execute remedies.

#### Worked example

The osmotic-pressure verifier ships an empty `remedies.edn`. A
typical "refute-on-core" remedy:

```edn
(defremedy :W001-unsat-core-to-refutation
  :when    (unsat-core-contains ?claim)
  :propose (ledger/transition ?claim :refuted)
  :requires :human-review)
```

— if `?claim` lands in the unsat core, propose transitioning its
ledger state to `:refuted`, and require a human acknowledgement
before applying.

#### Anti-patterns

- **`:auto-apply` on cascade-prone transitions.**
  `:propose (ledger/transition ?claim :refuted)` with
  `:requires :auto-apply` will rewrite the ledger on every
  refutation — including transient ones from misconfigured
  lifts. Reserve `:auto-apply` for monotone, narrowly-scoped
  actions (e.g., tagging, indexing); use `:human-review` for
  anything that mutates upstream state.
- **Omitting `:requires`.** The annotated template defaults to
  `:auto-apply` — i.e., the most aggressive setting. Always
  declare `:requires` explicitly.
- **Assuming the verifier runs the remedy.** It does not. A
  remedy declared but not picked up by book-qa is a no-op.
  Verify the consumer.
- **Conflicting remedies on the same `:when`.** Two remedies
  matching the same condition — the order of application is
  consumer-defined. Avoid by writing distinct `:when` clauses.

## 3. Sort system

Sorts are the DSL's main typing lever.

### 3.1 Primitive sorts

Four sorts are always implicit and need no `defsort`:

- `:int` — Z3 Int sort.
- `:real` — Z3 Real sort.
- `:bool` — Z3 Bool sort.
- `:string` — Z3 String sort.

Atom `:value` fields are typed at ingest by the lift's value-parser:
`(parse-int ?v)` → Edn::Int → Z3 Int; `(parse-float ?v)` → Edn::Double
→ Z3 Real; `(parse-bool ?v)` → Edn::Bool → Z3 Bool; `(string ?v)` →
Edn::Str → Z3 String. The atomspace EDN reference
(`atomspace-edn.md` § 7) documents the `_emit_float` normalisation
that keeps `2.0` from collapsing to `Edn::Int` 2.

### 3.2 Declared sorts

Domain entities are declared via `defsort`. A predicate may take any
mix of declared and primitive sorts in its argument list, but the
return-sort is overwhelmingly one of the four primitives — the
verifier asserts predicates equal to values, and only primitive sorts
have value literals.

### 3.3 Validation

`booklogic.cljs`'s `expand-predicates` validates each arg-sort and
return-sort against the union of declared and primitive sorts. An
undeclared sort fails the build with "unknown sort". Phase A's
`lint_atomspace.py` cross-checks atoms against the predicate registry;
a `:value` whose runtime type does not match the predicate's
declared return-sort produces a lint failure.

### 3.4 Domain patterns

Common sort layouts:

- **Single-entity** (osmotic-pressure):
  `(defsort :solution)` and all predicates `[:solution] :real`.
- **Two-entity** (bermuda parishes):
  `(defsort :parish)` and `(defsort :region)`, with predicates like
  `(defpredicate :parish-in [:parish :region] :bool)`.
- **Document-chapter-section** (book-knowledge):
  `(defsort :document) (defsort :chapter) (defsort :section)` with
  predicates like
  `(defpredicate :chapter-of [:chapter :document] :bool)`.

The pattern to avoid: a per-claim-id sort, which devolves the typing
into a flat namespace.

## 4. Cross-language conventions

The BookLogic source is compiled in three places: nbb (CLJS) expands
forms to intermediate EDN; Python codegen emits Rust; CLJS itself
embeds copies of some helpers for runtime use. Cross-language
identity holds on three artifacts.

### 4.1 `canonical_var_name`

REQ-EDN-042, 045, 046. Given a predicate Keyword and a subject
Keyword, returns a stable, cross-language-identical Z3 variable
name. The algorithm:

1. Convert the subject Keyword to its bare name (drop the leading
   colon).
2. Uppercase it, replace `-` with `_`.
3. Convert the predicate Keyword the same way but keep lowercase.
4. Concatenate with a `__` separator: `SUBJECT__predicate_with_underscores`.

Example: subject `:s`, predicate `:osmotic-pressure-pa` →
`S__osmotic_pressure_pa`.

The Python (`scripts/_canonical.py`), CLJS
(`<project>/cljs-orchestrator/src/main/<slug>/canonical.cljs`), and
Rust (`rust-verifier/src/canonical.rs`) implementations all agree
character-for-character. Golden test vectors live at
`skills/neurosym-forge/tests/golden/canonical_var_name.edn`; the
Python test, CLJS test, and Rust integration test all assert against
the same file.

### 4.2 Regex dialect

Python `re` module dialect, only. Use `(?P<v>...)` for named groups.
The JS-style `(?<v>...)` is rejected at lift-compile time. Phase A's
regex-compile gate (REQ-INGEST-041) catches a misspelled or invalid
regex before any claim is processed.

### 4.3 Subject placeholder

Convention:

- In `deflift` `:emit` bodies, use the literal Keyword `:s`. This
  becomes the atom's `:subject` field and surfaces as the SUBJECT
  half of `canonical_var_name`.
- In `defconstraint` `:assert` bodies, use the logic variable
  `?s`. This matches against the atom's `:subject` — but the match
  is positional (every predicate application takes one subject
  arg today), not by name. The `?` vs `:` distinction is cosmetic.

Either form works; the convention signals intent to readers (a
literal subject is fixed; a logic variable is bound by the surrounding
universal-quantifier scope).

### 4.4 `booklogic-schema.edn`

REQ-EDN-052. A Tier 1 artifact that re-exports the predicate
signatures (and the sort registry) in a self-contained EDN file
for off-machine consumers. The schema is validated at ingest time
against the runtime atom stream; an atom whose predicate is not in
the schema, or whose `:value` type does not match the schema's
declared return-sort, fails the ingest gate.

The schema file replaces the implicit "the predicate registry lives
inside booklogic.cljs's compiled output" arrangement that holds
without it.

## 5. Debugging

This section satisfies **REQ-BOOKLOGIC-048**. Four affordances cover
the most common failure modes in BookLogic source.

### 5.1 `make extract` — pre-solver atom preview

Phase A (REQ-INGEST-040). The `make extract` target runs
`extract_preview.py` against the current claim ledger and prints a
per-predicate fact-count summary BEFORE the solver runs. It fails
the build if the OPAQUE-fraction exceeds 0.5 (default threshold).

Sample output for the osmotic-pressure verifier on the clean fixture:

```
Predicate                            Facts  Sample value
molarity                                 1  0.154
osmotic-pressure-pa                      1  763.27
temperature-k                            1  298.15
vant-hoff-i                              1  2.0
------------------------------------------------------------
Total claims                             4
Atoms (expression)                       4
OPAQUE / unmatched                       0   (0.0%)
```

What to look for:

- **Predicate with zero facts.** The corresponding lift's regex did
  not match any claim. Either the regex is wrong (the most common
  case — see § 2.3 anti-patterns) or the claim is genuinely
  absent from the ledger.
- **High OPAQUE fraction.** A claim landed in the ledger with no
  matching lift. Inspect the OPAQUE atom's `:doc` field to see the
  unmatched text; iterate on the lift regex.
- **Decimal vs integer drift.** A predicate declared `:int` with
  sample value `2.0` (note the trailing `.0`) — the lift used
  `parse-float`; either change the predicate to `:real` or change
  the lift's value parser.

This is Phase A's primary debug surface. Most authoring bugs
manifest here as a missing predicate or an OPAQUE cluster; if
`make extract` reports a clean preview, the rest of the pipeline
usually verifies cleanly.

### 5.2 `VERIFIER_SOLVER_TIMEOUT_MS` — solver budget

Phase B (REQ-VERIFIER-BUILD-040). The Rust verifier reads
`VERIFIER_SOLVER_TIMEOUT_MS` from the environment and sets it as
the Z3 solver's timeout in milliseconds.

Default: 30,000 (30 seconds).

Override per-invocation:

```bash
VERIFIER_SOLVER_TIMEOUT_MS=300000 make ci
```

— gives the solver five minutes. Use 300,000 ms when investigating
an `:unknown` verdict; if the verdict resolves to `:sat` or
`:unsat` under the longer budget, the original failure was a
timeout, not an undecidability.

Conversely, a build that wants tight CI gates can set
`VERIFIER_SOLVER_TIMEOUT_MS=5000` and treat any `:unknown` as a
real failure. Phase B's pytest harnesses (REQ-VERIFIER-BUILD-042)
surface `:unknown` as a distinct failure mode rather than passing
or failing silently — see § 5.4.

### 5.3 `VERIFIER_DEBUG_SMT` — dump solver state

Built into the osmotic-pressure verifier's `smt.rs` (and copied to
the project-template via the seed templates). When the environment
variable is set to any non-empty value, the verifier prints the
full Z3 solver state to stderr just before `solver.check()`:

```rust
if std::env::var("VERIFIER_DEBUG_SMT").is_ok() {
    eprintln!("=== Z3 solver state ===\n{}", solver);
    eprintln!("=== /Z3 solver state ===");
}
```

Invocation:

```bash
VERIFIER_DEBUG_SMT=1 make ci 2>&1 | grep -A 200 "Z3 solver state"
```

What to look for:

- **Two variables with the same canonical name and different
  sorts.** The `Int-vs-Real drift` anti-pattern from § 2.5. Search
  the dump for two `declare-fun` lines naming the same symbol;
  the solver treats them as distinct symbols and reports a
  trivial verdict.
- **An expected predicate variable missing.** A typo in a
  constraint's predicate name (the `:osmotic-pressur-pa` case
  from § 2.5) — the variable is named with the typo, and the
  intended-name variable is unbound. Search the dump for the
  expected name; its absence is the bug.
- **An assertion the author did not write.** A lift fired
  unexpectedly, producing an atom that bound a variable the
  author thought was free. Cross-read against the `make extract`
  output.

This is the most expensive debug affordance — the dump is verbose
— but it answers questions that nothing else can: what does Z3
actually see?

### 5.4 Interpreting `:unknown`

An `:unknown` verdict means Z3 could not decide sat or unsat
within the time budget. Three common causes:

1. **The solver timed out.** Most common. Bump
   `VERIFIER_SOLVER_TIMEOUT_MS` (§ 5.2) and re-run. If the
   verdict resolves to `:sat` or `:unsat`, the original failure
   was budget-bound, not a real undecidability.
2. **The constraint encoding is genuinely undecidable.** Most
   often this means a transcendental function snuck into the
   `:assert` body — Z3's QF_NRA (the fragment used for
   `:real` arithmetic) does not decide `sin`, `cos`, `exp`,
   `log`, or any user-defined function not expressible as a
   polynomial. Refactor the constraint to use only `+`, `-`,
   `*`, `/`, and comparisons.
3. **The encoding has a free variable the solver cannot pin
   down.** A predicate referenced in the assertion that was never
   bound to a value by a lift. Z3 cannot decide a statement
   over an unconstrained Real variable; it returns `:unknown`.
   Cross-read the `make extract` output (§ 5.1) and the
   `VERIFIER_DEBUG_SMT` dump (§ 5.3) — the missing variable
   reveals itself as either a zero-fact predicate or an
   unbound `declare-fun`.

Phase B's pytest harnesses (REQ-VERIFIER-BUILD-042) surface
`:unknown` as a third verdict alongside `:sat` and `:unsat`; the
harness checks `verdict.status == "sat"` (or `"unsat"`) explicitly,
so an `:unknown` from the solver fails the test loudly rather than
masquerading as either pass-state.

The `:unknown` -> diagnose -> fix loop is the standard BookLogic
debug workflow once the regex preview is clean: bump the timeout,
inspect the solver dump, narrow down the offending constraint by
commenting out blocks of `:assert` and re-running.

## 6. Cookbook

Six short worked entries — each ~30-40 lines, with the actual EDN
and one sentence per form.

### 6.1 Osmotic pressure (`verifiers/osmotic_pressure/`)

The flagship example. Cross-reference
[`worked-examples/osmotic-pressure/clojure.md`](../skills/neurosym-forge/references/worked-examples/osmotic-pressure/clojure.md)
for the narrative walkthrough; § 2 above quotes each form file.

```edn
;; sorts.edn
{:forms [(defsort :solution)]}

;; predicates.edn
{:forms
 [(defpredicate :osmotic-pressure-pa [:solution] :real)
  (defpredicate :vant-hoff-i         [:solution] :real)
  (defpredicate :molarity            [:solution] :real)
  (defpredicate :temperature-k       [:solution] :real)]}

;; constraints.edn — one assertion of the van 't Hoff equation
{:forms
 [(defconstraint C001-vant-hoff
    :backend :z3
    :assert (approx= (:osmotic-pressure-pa ?s)
                     (* (:vant-hoff-i ?s) (:molarity ?s) 8.314 (:temperature-k ?s))
                     :tolerance 0.03)
    :on-unsat {:defect :D13 :severity :critical
               :message "van 't Hoff equation violated"})]}
```

The single constraint is enough to verify every claim in the
ledger against the published `π`. The clean fixture passes; the
doctored fixture surfaces C001 in the unsat core.

### 6.2 Parishes count (Bermuda verifier — sketch)

A two-sort domain. Each parish belongs to a region; a top-level
fact says how many parishes a region contains.

```edn
;; sorts.edn
{:forms [(defsort :parish) (defsort :region)]}

;; predicates.edn
{:forms
 [(defpredicate :parish-in     [:parish :region] :bool)
  (defpredicate :region-count  [:region] :int)]}

;; constraints.edn
{:forms
 [(defconstraint C001-bermuda-nine
    :backend :z3
    :assert (= (:region-count :bermuda) 9)
    :on-unsat {:defect :D02 :severity :critical
               :message "Bermuda has nine parishes, not the published count"})]}
```

The lift extracts "Bermuda has nine parishes" → `:region-count`
of `:bermuda` = 9 (via `:word-to-int {"nine" 9}`). The constraint
asserts the published count exactly; any other ledger claim
contradicting nine surfaces C001.

### 6.3 Temperature-bounded reaction (toy)

A reaction proceeds only between two bounds. Useful template for
any domain with a `lo < x < hi -> P(x)` shape.

```edn
;; sorts.edn
{:forms [(defsort :reaction)]}

;; predicates.edn
{:forms
 [(defpredicate :reactor-temp-k     [:reaction] :real)
  (defpredicate :lower-bound-k      [:reaction] :real)
  (defpredicate :upper-bound-k      [:reaction] :real)
  (defpredicate :reaction-proceeds  [:reaction] :bool)]}

;; constraints.edn
{:forms
 [(defconstraint C001-temp-window
    :backend :z3
    :assert (=> (and (< (:lower-bound-k ?r) (:reactor-temp-k ?r))
                     (< (:reactor-temp-k ?r) (:upper-bound-k ?r)))
                (:reaction-proceeds ?r))
    :on-unsat {:defect :D14 :severity :critical
               :message "Reaction did not proceed within stated temperature window"})]}
```

The implication is one-way: if temperature is in the window, the
reaction proceeds. The converse (reaction proceeds → temperature
in the window) would be a separate constraint.

### 6.4 String-typed entity match (toy)

A binomial-species lift extracts the Latin name and checks that
the ledger's recorded species matches.

```edn
;; sorts.edn
{:forms [(defsort :specimen)]}

;; predicates.edn
{:forms
 [(defpredicate :species [:specimen] :string)]}

;; lifts.edn
{:forms
 [(deflift L001-species
    :from :claim/canonical-text
    :when "(?i)species\\s+is\\s+(?P<v>[A-Z][a-z]+\\s+[a-z]+)"
    :emit (fact ?claim-id :s :species (string ?v)))]}

;; constraints.edn — assert the canonical species matches the recorded one
{:forms
 [(defconstraint C001-species-match
    :backend :z3
    :assert (= (:species ?s) "Pinus strobus")
    :on-unsat {:defect :D03 :severity :critical
               :message "Specimen species does not match the canonical name"})]}
```

Note that string equality in Z3 is decidable when both sides are
ground (one variable, one literal). This is a workable pattern for
small-alphabet identity checks; for free-text matching, use a
predicate-based approach instead.

### 6.5 Count-by-aggregation (toy)

Count claims per chapter via a `defquery`. Demonstrates the
declarative Cozo-only path.

```edn
;; predicates.edn
{:forms
 [(defpredicate :claim     [:string] :bool)
  (defpredicate :in-chapter [:string :string] :bool)]}

;; queries.edn
{:forms
 [(defquery :Q001-claims-per-chapter
    :backend :cozo
    :body    [(claims-in ?ch ?n) :- (:claim ?c) (:in-chapter ?c ?ch),
                                    ?n = count(?c)])]}
```

The query's output is a list of `(chapter, count)` rows; book-qa
consumes it to render the per-chapter claim density in the QA
report. The verifier itself does not act on the rows.

### 6.6 Auto-applied remedy on duplicate-id

A defremedy that auto-corrects a known cosmetic defect.

```edn
;; remedies.edn
{:forms
 [(defremedy :W001-dedup-claim-id
    :when    (verdict/defect :D04 ?claim)
    :propose (ledger/rename ?claim (suffix ?claim "-dup"))
    :requires :auto-apply)]}
```

D04 is the "duplicate claim id" defect class. The remedy renames
the second occurrence with a `-dup` suffix. Auto-apply is
acceptable here because the rename is monotone and reversible.
Compare this to a `(ledger/transition ?claim :refuted)` action,
which should always require `:human-review` (§ 2.7).

---

## Cross-references

- [`skills/neurosym-forge/SKILL.md`](../skills/neurosym-forge/SKILL.md) — the parent skill doc.
- [`skills/neurosym-forge/SUPPORT_MATRIX.md`](../skills/neurosym-forge/SUPPORT_MATRIX.md) — live vs stub per backend.
- [`skills/neurosym-forge/references/atomspace-edn.md`](../skills/neurosym-forge/references/atomspace-edn.md) — wire format.
- [`skills/neurosym-forge/references/grounded-atoms.md`](../skills/neurosym-forge/references/grounded-atoms.md) — Python regex dialect for lifts.
- [`skills/neurosym-forge/references/phase-boundaries.md`](../skills/neurosym-forge/references/phase-boundaries.md) — what crosses each phase boundary.
- [`skills/neurosym-forge/references/rewrite-rule-style.md`](../skills/neurosym-forge/references/rewrite-rule-style.md) — defrule conventions and stub status.
- [`skills/neurosym-forge/references/metta-idioms.md`](../skills/neurosym-forge/references/metta-idioms.md) — MeTTa-style mapping.
- [`skills/neurosym-forge/references/worked-examples/osmotic-pressure/clojure.md`](../skills/neurosym-forge/references/worked-examples/osmotic-pressure/clojure.md) — narrative walkthrough.
- `verifiers/osmotic_pressure/rules/booklogic/` — the canonical BookLogic source for the flagship example.
