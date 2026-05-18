# grounded-atoms

REQ-BOOKLOGIC-041. Regex dialect, subject conventions, and the
`parse-float` / `parse-int` helpers used inside `deflift` forms.

## 1. What "grounded" means

In MeTTa, a grounded atom is one whose `:value` carries a concrete
host-language native — an Int, a Double, a String, a Bool — rather
than a free variable. In this framework, grounded atoms are the
output of the lift pass: an `Edn::Double` or `Edn::Int` (or Bool/Str)
sits in the `:value` slot of an `:expression` atom.

The lift pass converts free-form claim text into grounded atoms by
running each `deflift` regex against the claim's `:canonical-text`.
A successful match coerces the capture group into the predicate's
declared value type and emits an `:expression` atom (see
`references/atomspace-edn.md`).

## 2. The `deflift` form

Surface syntax, from `verifiers/<project>/rules/booklogic/lifts.edn`:

```edn
(deflift L001-osmotic-pressure-pa
  :from :claim/canonical-text
  :when "(?i)osmotic\\s+pressure\\s*(?:=|is|of)?\\s*(?P<v>[0-9]+(?:\\.[0-9]+)?)\\s*Pa"
  :emit (fact ?claim-id :s :osmotic-pressure-pa (parse-float ?v)))
```

Field reference:

- `name` — convention: `L###-kebab-case` matching the predicate name.
- `:from` — which field of the claim to match against. Canonical
  value: `:claim/canonical-text`.
- `:when` — the regex (string). See § 3 for the dialect.
- `:emit` — a `(fact ?claim-id :subject :predicate value-expr)`
  form. `?claim-id` is the bound claim id. `:s` is the literal
  subject Keyword. `value-expr` is a `(parse-float ?v)` or
  `(parse-int ?v)` wrapping a regex capture group; see § 5.

Optional fields:

- `:word-to-int` — a map of word forms to ints, e.g.
  `{:one 1 :two 2}`, consulted by the int-coercion path before falling
  back to `int()`.
- `:provenance` — a free-form map for tracking which source produced
  the lift. Not enforced.

## 3. Regex dialect: Python `(?P<name>...)` is canonical

Patterns are run through Python's `re` module. The canonical named-group
form is `(?P<name>...)`. JS-style `(?<name>...)` is NOT supported by
Python's regex engine directly.

Today, `verifiers/<project>/scripts/ingest_ledger.py` silently rewrites
JS-form named groups to Python form via `_to_python_regex`:

```python
_JS_NAMED_GROUP = re.compile(r"\(\?<([A-Za-z_][A-Za-z0-9_]*)>")

def _to_python_regex(pat: str) -> str:
    """Translate JS-style (?<name>...) groups to Python (?P<name>...).

    The CLJS compiler consumes patterns via JS regex; Python's re
    uses the older Perl-style (?P<name>...) form.
    """
    return _JS_NAMED_GROUP.sub(r"(?P<\1>", pat)
```

That converter is a Tier 2 wart. The Tier 1 endpoint is: lifts.edn
authors MUST write Python form `(?P<v>...)`. The CI regex-compile-check
(part of the Phase A extract gate) will fail on JS form once the
converter is removed.

Other dialect notes:

- Case-insensitive: prefix with `(?i)`.
- Whitespace: `\\s+` (double backslash inside the EDN string).
- Escape backslashes by doubling: the EDN reader unescapes one level.

## 4. `?claim-id` and the `:s` subject placeholder

Inside `:emit`, the bindings have specific meanings:

- `?claim-id` — bound to the upstream claim's `:claim_id`. The ingester
  copies it to the `:id` field of the emitted atom, where it later
  becomes the Z3 tracker name in `assert_and_track`.
- `:s` — the literal subject Keyword. By convention `:s` for a generic
  solution. Domain-specific verifiers use richer names: `:sol` for
  solubility, `:bermuda` for the Bermuda Triangle disambiguator,
  `:specimen` for a patient record. The convention is per-project.
- Any capture group `?<name>` in the regex becomes a binding usable
  inside `parse-float` / `parse-int`.

The subject is a single Keyword for v1. Multi-argument predicates
(e.g. a binary `:dissociates-into` relation) require Tier 3.

## 5. `parse-float` and `parse-int` helpers

Inside `:emit`, value coercion goes through one of two helpers:

- `(parse-float ?v)` — coerces the named capture `v` to `Edn::Double`.
  Strips comma thousand-separators, then `float()`. On failure, the
  lift is silently skipped and the claim falls through to the next
  pattern (or OPAQUE if no pattern matches).
- `(parse-int ?v)` — coerces to `Edn::Int`. Consults `:word-to-int`
  first (so `"two"` becomes `2`); on miss, falls back to `int()`.

Both helpers are defined in the ingester, not the EDN reader; they are
recognised structurally by the `_apply_predicates` walker.

For Bool-typed predicates, omit the helper and let `:value` default to
the spec's `:value` key (typically `true`).

## 6. Worked example: osmotic-pressure lifts.edn

Real content from `verifiers/osmotic_pressure/rules/booklogic/lifts.edn`:

```edn
{:forms
 [(deflift L001-osmotic-pressure-pa
    :from :claim/canonical-text
    :when "(?i)osmotic\\s+pressure\\s*(?:=|is|of)?\\s*(?P<v>[0-9]+(?:\\.[0-9]+)?)\\s*Pa"
    :emit (fact ?claim-id :s :osmotic-pressure-pa (parse-float ?v)))

  (deflift L002-vant-hoff-i
    :from :claim/canonical-text
    :when "(?i)van[' \\s]*t\\s*Hoff(?:\\s+factor)?\\s*(?:i\\s*)?(?:=|is|of)?\\s*(?P<v>[0-9]+(?:\\.[0-9]+)?)"
    :emit (fact ?claim-id :s :vant-hoff-i (parse-float ?v)))

  (deflift L003-molarity
    :from :claim/canonical-text
    :when "(?i)molarity\\s*(?:M\\s*)?(?:=|is|of)?\\s*(?P<v>[0-9]+(?:\\.[0-9]+)?)"
    :emit (fact ?claim-id :s :molarity (parse-float ?v)))

  (deflift L004-temperature-k
    :from :claim/canonical-text
    :when "(?i)temperature\\s*(?:T\\s*)?(?:=|is|of)?\\s*(?P<v>[0-9]+(?:\\.[0-9]+)?)\\s*K"
    :emit (fact ?claim-id :s :temperature-k (parse-float ?v)))]}
```

Annotations, lift by lift:

- **L001-osmotic-pressure-pa.** Pattern: a case-insensitive match for
  "osmotic pressure" followed by an optional `=`/`is`/`of`, the value,
  and the unit `Pa`. The capture group `v` is coerced to Double.
  Emitted atom: `{:predicate :osmotic-pressure-pa :subject :s
  :value <Double>}`.
- **L002-vant-hoff-i.** Pattern handles the famous apostrophe in
  "van 't Hoff" via `van[' \\s]*t` — a character class allowing
  apostrophe OR whitespace OR neither, then `t`, then more optional
  whitespace, then `Hoff`. The `(?:\\s+factor)?` makes the word
  "factor" optional. Without that flexibility the lift misses real
  textbook prose every other line.
- **L003-molarity.** Pattern matches "molarity" (case-insensitive)
  followed by optional unit-letter `M`. The unit suffix is NOT in the
  pattern because molarity is conventionally given dimensionless on
  the page; the predicate declaration carries the unit semantics.
- **L004-temperature-k.** Same shape as L003 but anchors on the `K`
  suffix so a value like `298.15` only matches when explicitly Kelvin.
  Celsius / Fahrenheit lifts would be separate `deflift` forms with
  unit-converting `:emit` expressions (not present in v1).

## 7. What can go wrong

- **Silent OPAQUE.** Pattern compiles but never matches. Caught by
  Phase A's extract gate (opaque-fraction threshold). Fix: tighten or
  loosen the regex; check whitespace.
- **Regex compile error.** Caught at ingest time as a Python
  `re.error`. The ingester surfaces it with the lift name.
- **Wrong sort.** `parse-float` on a predicate declared `:int` (or
  vice versa) produces a sort mismatch at the Z3 level. Phase C's
  EdnVector / EdnList schema in `rules/booklogic-schema.edn` is the
  first line of defence; the Rust verifier rejects at parse time.
- **Subject mismatch.** Two lifts emitting to the same predicate with
  different subjects (one `:s` and one `:sol`) produce unrelated Z3
  constants. The axiom `(:osmotic-pressure-pa ?s)` only binds to
  whatever subject the constraint quantifies over — pick one
  convention per project.

## 8. Multiple subjects in one project

The `:s` placeholder is per-lift, not per-project. Two projects can
adopt different subject names; one project can use different subject
names for different lifts (e.g. `:bermuda` for triangle-disambiguator
claims, `:vessel` for individual-vessel claims). The constraint must
match the subject name used by the lifts that feed it:

```edn
;; constraints.edn
(defconstraint C001-foo
  :backend :z3
  :assert (= (:p ?bermuda) 1))   ; quantifies over :bermuda subjects
```

This couples constraints to lift conventions. The Phase C schema
will catch a subject-naming mismatch at compile time; until then,
inspection of `work/claims.edn` is the diagnostic.

A common pitfall: copying a constraint from one project to another
without renaming `?s` to match the destination project's convention.
The constraint will quantify over a fresh free variable and Z3 will
return `:sat` trivially. The fix is mechanical: search-and-replace
the subject placeholder across all constraint files when porting.

## 9. Multi-value lifts

The current `deflift` form binds one capture group to one predicate.
Multi-quantity claims like "i = 2, M = 0.154, T = 298.15 K" today
require three separate lifts running over the same text, each with
its own pattern. That is wasteful but correct.

A Tier 3 extension would allow:

```edn
(deflift L010-multi
  :from :claim/canonical-text
  :when "i\\s*=\\s*(?P<i>...)\\s*,\\s*M\\s*=\\s*(?P<m>...)\\s*,\\s*T\\s*=\\s*(?P<t>...)"
  :emit [(fact ?claim-id :s :vant-hoff-i (parse-float ?i))
         (fact ?claim-id :s :molarity   (parse-float ?m))
         (fact ?claim-id :s :temperature-k (parse-float ?t))])
```

emitting three atoms from one match. The current `_apply_predicates`
walker only returns the first match per claim, so this is genuinely
unsupported, not just unidiomatic.

## See also

- `references/atomspace-edn.md` — what the emitted atom looks like.
- `references/phase-boundaries.md` — when lifts run in the pipeline.
- `verifiers/osmotic_pressure/scripts/ingest_ledger.py` — the
  reference implementation of `parse-float` / `parse-int` / the
  word-to-int path.
