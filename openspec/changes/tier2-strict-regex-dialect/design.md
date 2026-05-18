# Design: tier2-strict-regex-dialect

## Capability choice: `edn-boundary` (existing), not a new `ingest-regex`

The regex dialect contract is the same class of fact as the EDN
keyword-vs-string distinction (REQ-EDN-049) or the float scientific-notation
ban (REQ-EDN-050): it is a cross-language interchange constraint enforced
at the Python ingest boundary. Putting it under `edn-boundary` keeps all
the "what shapes go over the wire" rules in one capability spec. A new
`ingest-regex` capability would split a single conceptual rule across two
spec files for no benefit.

## Replace converter with assertion (recommended)

Today (~line 80-90 of `ingest_ledger.py`):

```python
_JS_NAMED_GROUP = re.compile(r"\(\?<([A-Za-z_][A-Za-z0-9_]*)>")

def _to_python_regex(pat: str) -> str:
    return _JS_NAMED_GROUP.sub(r"(?P<\1>", pat)
```

Tomorrow:

```python
_JS_NAMED_GROUP = re.compile(r"\(\?<([A-Za-z_][A-Za-z0-9_]*)>")

def _assert_python_regex_dialect(pat: str) -> str:
    """Raise EdnReadError if pat contains JS-style named groups.

    Python's `re` module uses Perl-style `(?P<name>...)`. JS-form
    `(?<name>...)` is the dialect the CLJS compiler consumes; mixing the
    two leaves CLJS and Python disagreeing about what each pattern
    extracts. See references/grounded-atoms.md § Regex dialect.
    """
    if _JS_NAMED_GROUP.search(pat):
        raise EdnReadError(
            f"JS-style named group `(?<name>...)` in regex {pat!r}: "
            "use Python-form `(?P<name>...)` (see references/grounded-atoms.md)."
        )
    return pat
```

Keeping a one-line function (rather than inlining the assertion at the
call site) preserves the explicit-gate-at-the-boundary discipline: every
caller of `_apply_predicates` goes through one named guard. Future
dialect rules (e.g., banning DOTALL-only constructs the CLJS regex
engine cannot mirror) extend the same function.

## Why an `EdnReadError`-shaped exception?

The ingester already raises `EdnReadError` for malformed EDN at the
predicates.edn read boundary. A bad regex inside a `:patterns` vector
is logically the same class of authoring error: the input file is
syntactically EDN but semantically invalid. Same exception class keeps
the authoring-error story coherent.

## Why not delete `_to_python_regex` outright?

The single-function entry point is the documented gate; deleting it
would scatter the dialect check across each `re.search(...)` call site
(`_apply_predicates`, future lift compilers, the eventual standalone
linter). The validator-shaped function keeps the rule discoverable.

## Why this catches what REQ-INGEST-041 doesn't

REQ-INGEST-041 fires *after* extraction: it sees that ≥50 % of claims
turned to OPAQUE and exits. That catches the symptom but reports a
generic "too many OPAQUE" message. The strict-dialect gate fires
*before* extraction starts, points at the specific regex, and names
the specific dialect rule violated. The two gates compose: strict
dialect catches the JS-form mistake even on fixtures small enough that
the OPAQUE fraction stays under threshold.

## Bug7 regression upgrade

REQ-INGEST-048 had to surrogate around the silent converter:

> "Re-injects the sprint-5 silent-failure-by-regex bug and asserts the
> new gate catches it."

The surrogate was a *non-matching* regex (a typo in the literal text),
not the actual `(?<v>)` mutation. After this change, REQ-INGEST-052
asserts the gate fires on the genuine `(?<v>)` mutation — completing
what REQ-INGEST-048's prose described but the surrogate could not test.
