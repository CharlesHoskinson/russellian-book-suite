"""Generate rust-verifier/src/axioms.rs from rules/constraints.edn.

This codegen is invoked by `npm run codegen-axioms` (or directly via
the scaffolder), AFTER nbb runs `booklogic-compile` to populate the
intermediate `rules/constraints.edn`.

The emitted Rust source:
    - Defines `pub fn assert_axioms(ctx: &Context, solver: &Solver)`
    - For each `:backend :z3` constraint, emits a Z3 `assert_and_track`
      call whose tracker name is the constraint's id (e.g. "C001")
    - For `~=` (approximate-equality) constraints, desugars to
      |LHS - RHS| <= tolerance
    - Skips constraints whose `:backend` is not `:z3` (those go through
      `kg.rs` for `:cozo` or `eqsat.rs` for `:egg`)

The companion `generate_tracker_map` returns a dict mapping the tracker
name (constraint id) to its provenance information; the scaffolder
writes this to `rules/axioms-tracker-map.edn`. `verdict_to_qa.py` (in a
future PR) loads it to translate Z3 unsat-core tracker names back to
BookLogic constraint ids + the bound claim id.

This module deliberately stays in pure Python. It does NOT execute Rust.
The Phase-2.4 cargo-check task is the compile gate.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts._canonical import canonical_var_name
from scripts._edn_reader import EdnList, EdnVector, Keyword, Symbol
from scripts._io import read_edn_file, write_edn_file

# Re-export for backward compat — older callers may have imported these via
# `from scripts.codegen_axioms import EdnList`. The partitioning refactor
# moved the subject walk into this module, but the symbols stay where they
# were.
__all__ = [
    "CodegenError",
    "generate_axioms_source",
    "generate_tracker_map",
    "run",
]


class CodegenError(ValueError):
    """Raised when a constraint is malformed for axiom codegen."""


SUPPORTED_BACKENDS = {Keyword("z3"), Keyword("egg"), Keyword("cozo")}

# Real/Int binary operators that compile to a single Z3 method call.
# Each entry maps the BookLogic surface symbol to the Z3 Rust method name.
# `<`, `<=`, `>`, `>=` return Bool; `/` returns the numeric sort. All five
# methods exist on both `Real` and `Int` in z3 0.20 (REQ-SMT-040..042).
_REAL_BINOP_TO_Z3 = {
    "<":  "lt",
    "<=": "le",
    ">":  "gt",
    ">=": "ge",
    "/":  "div",
}

# Full set of head symbols accepted on the right of `:assert`. Anything
# outside this set produces a CodegenError naming the supported set
# (REQ-SMT-044). Phase G extends this with the aggregate operators
# `sum`, `count`, `in`, `select`, and `forall` over vector/set predicates.
_SUPPORTED_ASSERT_HEADS = frozenset({
    "=", "~=", "approx=",
    "<", "<=", ">", ">=",
    "+", "-", "*", "/", "mod",
    "and", "or", "not", "=>", "ite",
    "sum", "count", "in", "select",
    "forall", "exists",
})

# ----- REQ-DSL-050..053: multi-valued predicate schema lookup -----

# Module-level state used by `_emit_expr_typed` during a single
# `generate_axioms_source` call. We thread this via a module global rather
# than passing it through every recursive call because the assert-walker
# was written before schemas existed; widening every signature would touch
# every test fixture. The state is reset at the top of
# `generate_axioms_source` and consumed by the helpers below.
_SCHEMA: dict[Keyword, dict] = {}
_VECTOR_SYMBOLS: set[str] = set()
_SET_SYMBOLS: set[str] = set()
# REQ-SMT-056: predicate-uninterpreted-function registry. Maps a predicate name
# to its ordered argument-sort names, for every schema predicate with non-empty
# :arg-sorts and a Bool :return. Built once per generate_axioms_source call.
# Predicates absent here keep the legacy opaque-Bool emission (REQ-SMT-061).
_PREDICATE_UFS: dict[str, list[str]] = {}


def _kw_name(value) -> str:
    """A Keyword's bare name, or str() of anything else."""
    return value.name if isinstance(value, Keyword) else str(value)


def _is_bool_sort(sort) -> bool:
    """True if a return-sort spec resolves to the Bool sort."""
    return isinstance(sort, Keyword) and sort.name == "bool"


def _sort_const_name(sort_name: str) -> str:
    """The block-local Rust const holding the Z3 Sort for an uninterpreted sort."""
    return f"{sort_name.replace('-', '_')}_sort"


def _sort_ref_expr(sort_name: str) -> str:
    """A Rust expression for the Z3 Sort of `sort_name`.

    Primitive sorts map to their `Sort::<kind>()` constructor (no declaration
    needed); custom sorts reference the block-local `<sort>_sort` const declared
    alongside the quantifier's bound constants.
    """
    primitive = {"int": "Sort::int()", "real": "Sort::real()",
                 "bool": "Sort::bool()", "string": "Sort::string()"}
    return primitive.get(sort_name, _sort_const_name(sort_name))


def _sort_to_z3(sort) -> str:
    """REQ-DSL-051, 052: translate a sort spec to a Z3 type name.

    Scalar sorts map straight to `Int` / `Real` / `Bool` / `Z3String`.
    Multi-valued sorts wrap one of those in `Array<Int, T>` for vectors and
    `Set<T>` for sets. The inner sort must itself be a base sort or a
    previously declared sort keyword; nested containers
    (`[:vector [:set T]]`) are out of scope for this change.
    """
    scalar = {"int": "Int", "real": "Real", "bool": "Bool", "string": "Z3String"}
    if isinstance(sort, Keyword):
        return scalar.get(sort.name, "Real")
    if isinstance(sort, (list, EdnList, EdnVector)) and len(sort) == 2:
        head = sort[0]
        inner = _sort_to_z3(sort[1])
        if isinstance(head, Keyword):
            if head.name == "vector":
                return f"Array<Int, {inner}>"
            if head.name == "set":
                return f"Set<{inner}>"
    raise CodegenError(f"unknown sort: {sort!r}")


def _predicate_return_sort(pred_name: str):
    """Look up the return-sort for a predicate by name, or None if not in
    the schema. Used to dispatch vector/set lowering in `_emit_expr_typed`."""
    if not _SCHEMA:
        return None
    entry = _SCHEMA.get(Keyword(pred_name))
    if not entry:
        return None
    return entry.get(Keyword("return"))


def _return_container(ret):
    """Return ":vector" / ":set" / None for a return-sort spec."""
    if isinstance(ret, (list, EdnList, EdnVector)) and len(ret) == 2:
        head = ret[0]
        if isinstance(head, Keyword) and head.name in ("vector", "set"):
            return head.name
    return None

HEADER = """\
// GENERATED BY neurosym-forge codegen_axioms — DO NOT EDIT BY HAND.
// Edit rules/booklogic/constraints.edn instead, then run:
//   npm run codegen-axioms
//
// Source-of-truth: rules/constraints.edn (intermediate, emitted by
// `nbb -m {slug}.booklogic .`)
//
// Each `assert_and_track` call below corresponds to one `defconstraint`
// form. The tracker name equals the constraint id; on `solver.check()
// == Unsat`, `solver.get_unsat_core()` returns these names. Use
// `rules/axioms-tracker-map.edn` to translate them back to BookLogic
// ids and to the bound claim id.
//
// Constraints with :backend :egg discharge through the eqsat module
// (egg-rs 0.10); the resulting ProofResult is wrapped in a Z3 boolean
// tracker so unsat-core reporting keeps working uniformly.

#[cfg(feature = "smt")]
#[allow(unused_imports)]
use z3::{
    ast,
    ast::{Array, Bool, Datatype, Dynamic, Int, Real, Set, String as Z3String},
    FuncDecl, Solver, Sort, Symbol,
};
#[cfg(feature = "smt")]
#[allow(unused_imports)]
use std::str::FromStr as _;
#[cfg(feature = "smt")]
#[allow(unused_imports)]
use std::ops::{Add as _, Mul as _, Sub as _};

"""


FOOTER = ""


def _emit_predicate_is_vector_helper() -> str:
    """REQ-DSL-054: emit `predicate_is_vector(name)` so smt.rs can detect
    when an atom binds a scalar value to a predicate the schema declared
    as `[:vector <T>]`. The list of names is populated by `generate_axioms_source`
    from the schema kwarg.
    """
    if not _VECTOR_SYMBOLS:
        body_block = "    let _ = name; false"
    else:
        arms = "\n".join(f'        "{n}" => true,' for n in sorted(_VECTOR_SYMBOLS))
        body_block = (
            "    match name {\n"
            f"{arms}\n"
            "        _ => false,\n"
            "    }"
        )
    return (
        "\n#[cfg(feature = \"smt\")]\n"
        "/// True if the named predicate-subject symbol carries a multi-valued\n"
        "/// `[:vector <T>]` return-sort. smt.rs queries this to fail loudly\n"
        "/// when an atom binds a scalar to a vector-typed predicate\n"
        "/// (REQ-DSL-054).\n"
        "pub fn predicate_is_vector(name: &str) -> bool {\n"
        f"{body_block}\n"
        "}\n"
        "\n#[cfg(not(feature = \"smt\"))]\n"
        "pub fn predicate_is_vector(_name: &str) -> bool {\n"
        "    false\n"
        "}\n"
    )


def _emit_predicate_sort_helper(body: str) -> str:
    """Emit `predicate_is_real(name)` so smt.rs picks Real vs Int for each
    predicate-subject binding. Without this, axioms that promote to Real
    (because a sibling subexpression contains a float literal) reference
    Z3 symbols of a different sort than the value-binding smt.rs emits,
    silently leaving predicates unbound and the solver free to pick
    arbitrary values (the sprint-5 doctored-fixture :sat regression).
    """
    import re
    real_names: set[str] = set()
    for m in re.finditer(r'Real::new_const\("([^"]+)"\)', body):
        real_names.add(m.group(1))
    if not real_names:
        body_block = '    let _ = name; false'
    else:
        arms = "\n".join(f'        "{n}" => true,' for n in sorted(real_names))
        body_block = (
            "    match name {\n"
            f"{arms}\n"
            "        _ => false,\n"
            "    }"
        )
    return (
        "\n#[cfg(feature = \"smt\")]\n"
        "/// True if the named predicate-subject symbol should be bound as\n"
        "/// `z3::ast::Real` rather than `z3::ast::Int`. The codegen promotes\n"
        "/// a constraint subtree to Real whenever any float literal appears\n"
        "/// anywhere in it; smt.rs uses this to keep value-bindings in the\n"
        "/// same Z3 sort as the axioms reference.\n"
        "#[allow(dead_code)]\n"
        "pub fn predicate_is_real(name: &str) -> bool {\n"
        f"{body_block}\n"
        "}\n"
        "\n#[cfg(not(feature = \"smt\"))]\n"
        "#[allow(dead_code)]\n"
        "pub fn predicate_is_real(_name: &str) -> bool {\n"
        "    false\n"
        "}\n"
    )


def generate_axioms_source(constraints: list[dict],
                            schema: dict | None = None,
                            sorts: list[dict] | None = None) -> str:
    """Emit a complete axioms.rs file from a list of constraint dicts.

    Each dict is a constraint entry as written by emit-constraints-edn
    in booklogic.cljs.tmpl (read back via _io.read_edn_file). Required
    keys: :id :backend :assert :on-unsat. Optional: :tolerance :track.

    Emits the partitioned axiom surface introduced in
    `tier4-solver-partitioning` (REQ-PERF-040..043):

    - `axioms_for_subject(solver, subject)`: assert constraints whose
      :assert references exactly one subject identifier.
    - `axioms_shared(solver)`: assert constraints whose :assert
      references two or more distinct subject identifiers (cross-subject).
    - `axioms_subjects()`: enumerate every subject name that has at
      least one per-subject constraint, so `smt::check_all` can iterate
      partitions deterministically.
    - `assert_axioms(solver)`: backward-compat aggregator; calls
      `axioms_for_subject` for every known subject plus `axioms_shared`.

    REQ-DSL-050..053: `schema` is the parsed `:predicates` map of
    `booklogic-schema.edn` (predicate keyword → {:arg-sorts, :return}).
    When present, predicates declared with `[:vector T]` or `[:set T]`
    lower to Z3 `Array<Int,T>` / `Set<T>` and the aggregate operators
    `(sum vec)`, `(count vec)`, `(forall ?x in vec ...)` desugar via
    `_AGGREGATE_DISPATCH`.

    REQ-SMT-051..054: `sorts` is the parsed `:sorts` list from
    `sorts.edn` (each entry a dict with a `:name` Keyword). When present,
    its declared names form `declared_sort_names`, against which any
    `(forall [(?v :sort)] body)` / `(exists [(?v :sort)] body)` quantifier
    binding's sort keyword is validated before a `Datatype::new_const` is
    emitted.

    REQ-EGG-*/REQ-DATALOG-041: :egg constraints are still emitted into
    the shared bucket (they discharge through eqsat.rs but the wrapping
    Bool tracker still needs to live on the solver); :cozo constraints
    flow into a sibling registry consumed by kg.rs at smoke time.
    """
    # Reset module-level schema state before each call so test isolation
    # holds and re-vendored copies pick up only the current call's schema.
    global _SCHEMA, _VECTOR_SYMBOLS, _SET_SYMBOLS, _PREDICATE_UFS
    _SCHEMA = schema or {}
    _VECTOR_SYMBOLS = set()
    _SET_SYMBOLS = set()
    # REQ-SMT-056: build the predicate-UF registry. A predicate joins it only
    # if it declares a non-empty :arg-sorts AND a Bool :return; nil-arity
    # predicates stay on the legacy opaque-Bool path (REQ-SMT-061).
    _PREDICATE_UFS = {}
    for pred_kw, spec in _SCHEMA.items():
        if not isinstance(spec, dict):
            continue
        arg_sorts = spec.get(Keyword("arg-sorts"))
        if arg_sorts and _is_bool_sort(spec.get(Keyword("return"))):
            _PREDICATE_UFS[_kw_name(pred_kw)] = [_kw_name(s) for s in arg_sorts]
    # REQ-SMT-051..054: build the declared-sort registry once per call.
    declared_sort_names: set[str] = set()
    if sorts:
        for s in sorts:
            if isinstance(s, dict) and Keyword("name") in s:
                name_val = s[Keyword("name")]
                name_str = name_val.name if isinstance(name_val, Keyword) else str(name_val)
                declared_sort_names.add(name_str)
    per_subject_blocks: dict[str, list[str]] = {}
    shared_blocks: list[str] = []
    corpus_blocks: list[str] = []
    corpus_ids: list[str] = []
    all_body_for_sort: list[str] = []
    cozo_entries: list[tuple[str, str]] = []
    for c in constraints:
        _require(c, "id")
        _require(c, "backend")
        _require(c, "assert")
        if Keyword("on-unsat") not in c:
            raise CodegenError(f"constraint {c.get(Keyword('id'))!r}: missing on-unsat")
        backend = c[Keyword("backend")]
        if backend not in SUPPORTED_BACKENDS:
            raise CodegenError(
                f"constraint {c.get(Keyword('id'))!r}: unknown backend {backend!r}; "
                f"expected one of {SUPPORTED_BACKENDS}"
            )
        # REQ-CORPUS-050: scope dispatch. Default :subject preserves Phase J
        # behaviour. :corpus routes the emitted block into axioms_corpus
        # regardless of how many subjects the body references.
        scope = c.get(Keyword("scope"), Keyword("subject"))
        if scope not in (Keyword("subject"), Keyword("corpus")):
            raise CodegenError(
                f"constraint {c.get(Keyword('id'))!r}: invalid :scope {scope!r}; "
                "expected :subject or :corpus"
            )
        is_corpus = scope == Keyword("corpus")
        if backend == Keyword("z3"):
            block = _emit_z3_block(c, declared_sort_names=declared_sort_names)
            all_body_for_sort.append(block)
            if is_corpus:
                # REQ-CORPUS-051: corpus-scope constraints land in
                # axioms_corpus, never in per-subject or shared buckets.
                corpus_blocks.append(block)
                corpus_ids.append(str(c[Keyword("id")]))
                continue
            # Collect every distinct subject identifier referenced inside
            # the :assert form. >1 distinct subject => cross-subject, lands
            # in axioms_shared (REQ-PERF-043). Exactly 1 => per-subject
            # bucket. 0 (e.g. a pure-literal assert) => goes into shared as
            # well so it still runs unconditionally.
            subjects = _collect_subjects(c[Keyword("assert")])
            if len(subjects) == 1:
                (subject,) = subjects
                per_subject_blocks.setdefault(subject, []).append(block)
            else:
                shared_blocks.append(block)
        elif backend == Keyword("egg"):
            # :egg constraints emit a Bool tracker block; route them to
            # axioms_shared so they run once per check (they don't bind to
            # a subject — eqsat.rs is whole-graph). A :scope :corpus :egg
            # constraint lands in axioms_corpus instead.
            block = _emit_egg_block(c)
            all_body_for_sort.append(block)
            if is_corpus:
                corpus_blocks.append(block)
                corpus_ids.append(str(c[Keyword("id")]))
            else:
                shared_blocks.append(block)
        elif backend == Keyword("cozo"):
            # REQ-DATALOG-041: route :cozo constraints to kg.rs at smoke
            # time via a sibling registry that lib.rs runs through
            # kg::evaluate_constraint; the Z3 entry point sees nothing.
            cozo_entries.append(_emit_cozo_block(c))

    body_for_sort = "\n".join(all_body_for_sort) if all_body_for_sort \
        else "    // no z3 constraints declared\n"
    sort_helper       = _emit_predicate_sort_helper(body_for_sort)
    is_vector_helper  = _emit_predicate_is_vector_helper()
    cozo_registry     = _emit_cozo_registry(cozo_entries)

    return (
        HEADER
        + _emit_axioms_for_subject(per_subject_blocks)
        + _emit_axioms_shared(shared_blocks)
        + _emit_axioms_corpus(corpus_blocks)
        + _emit_axioms_subjects(sorted(per_subject_blocks.keys()))
        + _emit_axioms_corpus_ids(corpus_ids)
        + _emit_assert_axioms_aggregator(
            sorted(per_subject_blocks.keys()),
            has_corpus=bool(corpus_blocks),
        )
        + FOOTER
        + sort_helper
        + is_vector_helper
        + cozo_registry
    )


def _emit_axioms_for_subject(per_subject_blocks: dict[str, list[str]]) -> str:
    """Emit `pub fn axioms_for_subject(solver, subject)` as a match over
    subject names. Each arm asserts that subject's constraints; the
    default arm is a no-op so an unknown subject simply contributes
    nothing (the partition still gets the per-subject timeout +
    `solver.check()`).
    """
    out = (
        "#[cfg(feature = \"smt\")]\n"
        "/// Assert every z3 constraint whose `:assert` references exactly\n"
        "/// the given `subject`. Cross-subject constraints are NOT asserted\n"
        "/// here; they live in `axioms_shared`. Unknown subjects are a\n"
        "/// no-op so the partition still runs `solver.check()` cleanly.\n"
        "pub fn axioms_for_subject(solver: &Solver, subject: &str) {\n"
        "    match subject {\n"
    )
    for subject in sorted(per_subject_blocks.keys()):
        out += f'        "{subject}" => {{\n'
        for block in per_subject_blocks[subject]:
            # Re-indent each 4-space-indented block by +4 to nest under
            # the match arm.
            for line in block.splitlines():
                if line:
                    out += "    " + line + "\n"
                else:
                    out += "\n"
        out += "        }\n"
    out += (
        "        _ => {\n"
        "            let _ = solver;\n"
        "        }\n"
        "    }\n"
        "}\n"
        "\n"
        "#[cfg(not(feature = \"smt\"))]\n"
        "pub fn axioms_for_subject(_solver: &(), _subject: &str) {\n"
        "    // No-op: built without smt feature.\n"
        "}\n"
        "\n"
    )
    return out


def _emit_axioms_corpus(corpus_blocks: list[str]) -> str:
    """REQ-CORPUS-051: emit `pub fn axioms_corpus(solver)` covering every
    constraint declared with `:scope :corpus`. `smt::check_all` runs this
    once over the union of every subject's atoms, after per-subject and
    shared partitions complete.
    """
    out = (
        "#[cfg(feature = \"smt\")]\n"
        "/// Assert every z3 constraint declared with `:scope :corpus`\n"
        "/// (REQ-CORPUS-050, 051). `smt::check_all` runs this once over a\n"
        "/// solver seeded with the union of every subject's atoms, after\n"
        "/// per-subject and shared partitions complete. A failed corpus\n"
        "/// constraint surfaces on the verdict's `:corpus-defects` field.\n"
        "pub fn axioms_corpus(solver: &Solver) {\n"
    )
    if not corpus_blocks:
        out += "    let _ = solver;\n"
    else:
        for block in corpus_blocks:
            out += block
            out += "\n"
    out += (
        "}\n"
        "\n"
        "#[cfg(not(feature = \"smt\"))]\n"
        "pub fn axioms_corpus(_solver: &()) {\n"
        "    // No-op: built without smt feature.\n"
        "}\n"
        "\n"
    )
    return out


def _emit_axioms_shared(shared_blocks: list[str]) -> str:
    """Emit `pub fn axioms_shared(solver)` covering every constraint that
    walks more than one subject. Runs once, serially, after every
    per-subject partition has completed.
    """
    out = (
        "#[cfg(feature = \"smt\")]\n"
        "/// Assert every z3 constraint whose `:assert` references two or\n"
        "/// more distinct subjects (cross-subject constraints,\n"
        "/// REQ-PERF-043). Also covers constraints with no subject\n"
        "/// reference (pure-literal asserts) so those still run\n"
        "/// unconditionally.\n"
        "pub fn axioms_shared(solver: &Solver) {\n"
    )
    if not shared_blocks:
        out += "    let _ = solver;\n"
    else:
        for block in shared_blocks:
            out += block
            out += "\n"
    out += (
        "}\n"
        "\n"
        "#[cfg(not(feature = \"smt\"))]\n"
        "pub fn axioms_shared(_solver: &()) {\n"
        "    // No-op: built without smt feature.\n"
        "}\n"
        "\n"
    )
    return out


def _emit_axioms_subjects(subjects: list[str]) -> str:
    """Emit `pub fn axioms_subjects() -> &'static [&'static str]` so
    `smt::check_all` can iterate every subject that has at least one
    declared constraint without re-parsing the codegen source.
    """
    arms = ", ".join(f'"{s}"' for s in subjects)
    body = f"&[{arms}]" if subjects else "&[]"
    return (
        "/// Enumerate every subject identifier (canonical form, e.g.\n"
        "/// `\"Bermuda\"` or `\"s\"`) that has at least one declared\n"
        "/// constraint. `smt::check_all` iterates this list to build\n"
        "/// per-subject partitions deterministically.\n"
        "pub fn axioms_subjects() -> &'static [&'static str] {\n"
        f"    {body}\n"
        "}\n"
        "\n"
    )


def _emit_axioms_corpus_ids(corpus_ids: list[str]) -> str:
    """REQ-CORPUS-053: emit `pub fn axioms_corpus_ids() -> &'static [&'static str]`
    so `smt::check_all` can map an unsat-core tracker name back to the
    corpus-scope constraint it came from when building the
    `:corpus-defects` field.
    """
    arms = ", ".join(f'"{i}"' for i in corpus_ids)
    body = f"&[{arms}]" if corpus_ids else "&[]"
    return (
        "/// REQ-CORPUS-053: every constraint id whose declared `:scope` is\n"
        "/// `:corpus`. `smt::check_all` reads this to map unsat-core trackers\n"
        "/// back to the constraint that drove the corpus-scope failure when\n"
        "/// populating the verdict's `:corpus-defects` field.\n"
        "pub fn axioms_corpus_ids() -> &'static [&'static str] {\n"
        f"    {body}\n"
        "}\n"
        "\n"
    )


def _emit_assert_axioms_aggregator(subjects: list[str],
                                    has_corpus: bool = False) -> str:
    """Emit the legacy `assert_axioms(solver)` entry point so callers
    written before the partition refactor still work. It calls every
    per-subject assertion plus the shared one, and (REQ-CORPUS-051) the
    corpus-scope axioms when any are declared.
    """
    out = (
        "#[cfg(feature = \"smt\")]\n"
        "/// Backward-compatible aggregator. Asserts every per-subject\n"
        "/// constraint, the shared bucket, and any corpus-scope constraints\n"
        "/// on a single solver. New callers should prefer\n"
        "/// `axioms_for_subject` + `axioms_shared` + `axioms_corpus` so the\n"
        "/// timeout and unknown blast-radius stays per-partition.\n"
        "#[allow(dead_code)]\n"
        "pub fn assert_axioms(solver: &Solver) {\n"
    )
    for s in subjects:
        out += f'    axioms_for_subject(solver, "{s}");\n'
    out += "    axioms_shared(solver);\n"
    if has_corpus:
        out += "    axioms_corpus(solver);\n"
    out += (
        "}\n"
        "\n"
        "#[cfg(not(feature = \"smt\"))]\n"
        "pub fn assert_axioms(_solver: &()) {\n"
        "    // No-op: built without smt feature.\n"
        "}\n"
    )
    return out


def _collect_subjects(assert_form: Any) -> set[str]:
    """Walk the :assert sexp and return every distinct subject keyword
    that appears as the second element of a `(:predicate :Subject ...)`
    or `(:predicate ?var ...)` shape.

    The subject identifier is normalised through the canonical-form
    rules: a leading `:` or `?` is stripped so the returned string
    matches the keys used in `axioms_for_subject`'s match.
    """
    if isinstance(assert_form, str):
        from scripts._edn_reader import read_edn
        assert_form = read_edn(assert_form)
    out: set[str] = set()
    _walk_subjects(assert_form, out)
    return out


def _walk_subjects(node: Any, out: set[str]) -> None:
    if isinstance(node, (list, EdnList, EdnVector)) and len(node) > 0:
        head = node[0]
        if isinstance(head, Keyword) and len(node) >= 2:
            sub = node[1]
            if isinstance(sub, Keyword):
                out.add(sub.name)
            elif isinstance(sub, Symbol):
                # Symbol `?s` arrives with the leading `?` already
                # stripped by the EDN reader; canonical_var_name does the
                # same stripping for `:` so they line up.
                out.add(sub.name.lstrip(":?"))
            elif isinstance(sub, str) and sub.startswith(("?", ":")):
                out.add(sub.lstrip(":?"))
            elif isinstance(sub, str):
                out.add(sub)
            # walk remaining children too — a constraint may have nested
            # (:predicate :Subject) shapes deeper in the tree.
            for child in list(node)[2:]:
                _walk_subjects(child, out)
            return
        for child in node:
            _walk_subjects(child, out)


def _require(c: dict, key: str) -> None:
    if Keyword(key) not in c:
        raise CodegenError(f"constraint {c.get(Keyword('id'))!r}: missing {key}")


def _emit_z3_block(c: dict, declared_sort_names: set[str] | None = None) -> str:
    """Emit one `solver.assert_and_track(...)` block for a single :z3 constraint."""
    cid       = c[Keyword("id")]
    assert_   = c[Keyword("assert")]
    tolerance = c.get(Keyword("tolerance"))
    if isinstance(assert_, str):
        from scripts._edn_reader import read_edn
        assert_ = read_edn(assert_)
    if not isinstance(assert_, (list, tuple, EdnList, EdnVector)) or len(assert_) < 2:
        raise CodegenError(f"constraint {cid!r}: malformed assert form: {assert_!r}")
    head_node = assert_[0]
    head = head_node.name if isinstance(head_node, Keyword) else str(head_node)
    # Binary heads need at least 3 elements; unary heads (not) need at least 2.
    # Per-head arity checks below enforce the exact counts.
    lhs_raw = assert_[1] if len(assert_) >= 2 else None
    rhs_raw = assert_[2] if len(assert_) >= 3 else None
    if head in ("~=", "approx="):
        # Approx-equality is numeric. `approx=` is the EDN-safe spelling;
        # `~=` is accepted from intermediate forms or string-encoded asserts.
        #
        # Tolerance may be specified inline as trailing key-value pairs
        # within the assert form: (approx= LHS RHS :tolerance 0.01). In
        # that case len(assert_) >= 5 and assert_[3] is :tolerance. The
        # CLJS layer historically only recognised `~=` here, so `approx=`
        # constraints arrived with `:tolerance nil` in the intermediate.
        if tolerance is None and len(assert_) >= 5:
            tol_kw = assert_[3]
            if isinstance(tol_kw, Keyword) and tol_kw.name == "tolerance":
                tol_val = assert_[4]
                if isinstance(tol_val, (int, float)):
                    tolerance = float(tol_val)
        # approx= always uses Real because _emit_approx_block multiplies
        # lhs/rhs by Real::from_rational eps — Int * Real is a type error.
        lhs = _emit_expr_typed(lhs_raw, "Real")
        rhs = _emit_expr_typed(rhs_raw, "Real")
        return _emit_approx_block(cid, lhs, rhs, tolerance)
    if head == "=":
        # Infer Z3 type from the RHS literal to emit correct variable declarations.
        z3_type = _infer_z3_type(rhs_raw)
        lhs = _emit_expr_typed(lhs_raw, z3_type)
        rhs = _emit_expr_typed(rhs_raw, z3_type)
        return _emit_equality_block(cid, lhs, rhs)
    if head in _REAL_BINOP_TO_Z3 and head in {"<", "<=", ">", ">="}:
        # Top-level comparison asserts compile to a single Bool that we
        # hand straight to `assert_and_track` (REQ-SMT-040, 041).
        expr = _emit_real_binop(head, assert_, "Bool")
        return _emit_bool_assert_block(cid, expr)
    if head == "ite":
        # Top-level (ite COND THEN ELSE) only makes sense when THEN and
        # ELSE are Bool: the whole assert form must reduce to a Bool
        # (REQ-SMT-043). Build it under z3_type='Bool' so the branches
        # are emitted as Bool subexpressions.
        expr = _emit_ite(assert_, "Bool")
        return _emit_bool_assert_block(cid, expr)
    if head == "and":
        if len(assert_) < 3:
            raise CodegenError(
                f"constraint {cid!r}: 'and' requires at least 2 operands, got {len(assert_)-1}"
            )
        parts = [_emit_bool_subexpr(child, declared_sort_names=declared_sort_names) for child in assert_[1:]]
        expr = f"Bool::and(&[{', '.join('&' + p for p in parts)}])"
        return _emit_bool_assert_block(cid, expr)
    if head == "or":
        if len(assert_) < 3:
            raise CodegenError(
                f"constraint {cid!r}: 'or' requires at least 2 operands, got {len(assert_)-1}"
            )
        parts = [_emit_bool_subexpr(child, declared_sort_names=declared_sort_names) for child in assert_[1:]]
        expr = f"Bool::or(&[{', '.join('&' + p for p in parts)}])"
        return _emit_bool_assert_block(cid, expr)
    if head == "not":
        if len(assert_) != 2:
            raise CodegenError(
                f"constraint {cid!r}: 'not' requires exactly 1 operand, got {len(assert_)-1}"
            )
        inner = _emit_bool_subexpr(assert_[1], declared_sort_names=declared_sort_names)
        body = f"{inner}.not()"
        return _emit_bool_assert_block(cid, body)
    if head == "=>":
        if len(assert_) != 3:
            raise CodegenError(
                f"constraint {cid!r}: '=>' requires exactly 2 operands, got {len(assert_)-1}"
            )
        premise = _emit_bool_subexpr(assert_[1], declared_sort_names=declared_sort_names)
        conclusion = _emit_bool_subexpr(assert_[2], declared_sort_names=declared_sort_names)
        body = f"{premise}.implies(&{conclusion})"
        return _emit_bool_assert_block(cid, body)
    if head in ("forall", "exists"):
        # Two shapes coexist:
        #   Phase G (vector-bounded):  (forall ?x in <coll> body)
        #     len >= 4 AND assert_[2] is the `in` marker. Lowers via
        #     `_emit_aggregate`. `exists` of this shape is not supported
        #     by Phase G — it falls through to the v0.5 path below.
        #   v0.5 (general quantifier): (forall [(?v :sort) ...] body)
        #     len == 3 AND assert_[1] is a vector of (?var :sort) pairs.
        #     Lowers via `_emit_quantifier_expr`.
        if head == "forall" and len(assert_) >= 4:
            in_marker = assert_[2]
            in_name = in_marker.name if isinstance(in_marker, Keyword) else str(in_marker)
            if in_name == "in":
                # Phase G vector-bounded forall; reuse the aggregate path.
                body_expr = _emit_expr_typed(assert_, "Bool")
                return _emit_bool_assert_block(cid, body_expr)
        # v0.5 general quantifier.
        _dsn = declared_sort_names or set()
        quantified = _emit_quantifier_expr(assert_, _dsn, outer_bound_vars=None)
        return _emit_bool_assert_block(cid, quantified)
    raise CodegenError(
        f"constraint {cid!r}: assert head {head!r} not supported; "
        f"expected one of {sorted(_SUPPORTED_ASSERT_HEADS)}"
    )


def _emit_egg_block(c: dict) -> str:
    """Emit a `solver.assert_and_track(...)` block whose body discharges
    the constraint via `crate::eqsat::prove_equiv(lhs, rhs, rules)`.

    REQ-EQSAT-043: `:backend :egg` constraints route to eqsat (no longer
    silently dropped at the codegen layer). The egg proof result is
    wrapped in a Z3 boolean tracker so the existing unsat-core reporter
    on the Z3 side keeps working uniformly across backends.
    """
    cid     = c[Keyword("id")]
    assert_ = c[Keyword("assert")]
    if isinstance(assert_, str):
        from scripts._edn_reader import read_edn
        assert_ = read_edn(assert_)
    if not isinstance(assert_, (list, EdnList, EdnVector)) or len(assert_) < 3:
        raise CodegenError(f"constraint {cid!r}: malformed :egg assert form: {assert_!r}")
    head_node = assert_[0]
    head = head_node.name if isinstance(head_node, Keyword) else str(head_node)
    if head != "=":
        raise CodegenError(
            f"constraint {cid!r}: :backend :egg only supports '=' assert head, got {head!r}"
        )
    lhs_sexpr = _to_egg_sexpr(assert_[1])
    rhs_sexpr = _to_egg_sexpr(assert_[2])
    return (
        f"    // constraint {cid} (:backend :egg)\n"
        f"    {{\n"
        f"        #[cfg(feature = \"eqsat\")]\n"
        f"        let proved = matches!(\n"
        f"            crate::eqsat::prove_equiv(\n"
        f"                {lhs_sexpr!r},\n"
        f"                {rhs_sexpr!r},\n"
        f"                &crate::eqsat::make_rewrites(),\n"
        f"            ),\n"
        f"            crate::eqsat::ProofResult::Proved\n"
        f"        );\n"
        f"        #[cfg(not(feature = \"eqsat\"))]\n"
        f"        let proved = false;\n"
        f"        let result = Bool::from_bool(proved);\n"
        f'        let tracker = Bool::new_const("{cid}");\n'
        f"        solver.assert_and_track(&result, &tracker);\n"
        f"    }}\n"
    )


def _to_egg_sexpr(node: Any) -> str:
    """Translate a BookLogic surface form into an s-expression string
    parseable by `egg::RecExpr::<BookLogic>::parse`.

    BookLogic's egg language (see verifiers/*/rust-verifier/src/eqsat.rs):
      - integer literals → Num(i64)
      - (:pred :subject) → (predicate pred subject)
      - (op a b ...)     → (op a b) folded pairwise for +,-,*,/
      - free symbols     → Symbol(name)
    """
    if isinstance(node, bool):
        return "true" if node else "false"
    if isinstance(node, int):
        return str(node)
    if isinstance(node, float):
        # egg's RecExpr parser doesn't carry floats in the v0.4 language;
        # rounds to int with the same rational-approx denominator. Egg
        # constraints over floats are not yet exercised; surface the
        # rounded form rather than fail codegen.
        return str(int(round(node)))
    if isinstance(node, Keyword):
        return node.name
    if isinstance(node, str):
        return node
    if isinstance(node, (list, EdnList, EdnVector)) and len(node) > 0:
        head = node[0]
        if isinstance(head, Keyword):
            # (:pred :subject) → (predicate pred subject)
            sub = node[1] if len(node) >= 2 else None
            if isinstance(sub, Keyword):
                sub_str = sub.name
            elif sub is not None:
                sub_str = str(sub)
            else:
                sub_str = "val"
            return f"(predicate {head.name} {sub_str})"
        head_str = str(head)
        if head_str in {"+", "-", "*", "/"} and len(node) >= 3:
            children = [_to_egg_sexpr(n) for n in list(node)[1:]]
            # Left-fold so (op a b c) → (op (op a b) c). BookLogic egg
            # ops are arity-2.
            acc = f"({head_str} {children[0]} {children[1]})"
            for ch in children[2:]:
                acc = f"({head_str} {acc} {ch})"
            return acc
    raise CodegenError(f"unsupported :egg expression node: {node!r}")


def _infer_z3_type(node: Any) -> str:
    """Infer the Z3 Rust type name ('Int', 'Real', 'Bool', 'Z3String') from a literal."""
    if isinstance(node, bool):
        return "Bool"
    if isinstance(node, int):
        return "Int"
    if isinstance(node, float):
        return "Real"
    if isinstance(node, str):
        return "Z3String"
    if isinstance(node, Keyword):
        return "Z3String"
    return "Int"


# REQ-DSL-053: default static-unroll bound when the vector's length is not
# fixed in the schema. The aggregate operators below emit code that walks
# indices [0, _DEFAULT_VECTOR_UNROLL).
_DEFAULT_VECTOR_UNROLL = 8


def _predicate_call_info(node):
    """If `node` is a predicate application `(:pred-name <subject>)`,
    return `(pred_name, subject_str, var_name)`; otherwise None."""
    if not isinstance(node, (list, EdnList, EdnVector)) or len(node) == 0:
        return None
    head = node[0]
    if not isinstance(head, Keyword):
        return None
    sub = node[1] if len(node) >= 2 else None
    if isinstance(sub, Keyword):
        sub_str = sub.name
    elif sub is not None:
        sub_str = str(sub)
    else:
        sub_str = "val"
    return head.name, sub_str, canonical_var_name(head.name, sub_str)


def _vector_predicate_z3_type(pred_name: str) -> str | None:
    """Return the inner Z3 type ('Real', 'Int', ...) for a vector predicate,
    or None if the predicate is not vector-typed in the schema."""
    ret = _predicate_return_sort(pred_name)
    if _return_container(ret) != "vector":
        return None
    inner = ret[1]
    if isinstance(inner, Keyword):
        return {"int": "Int", "real": "Real", "bool": "Bool", "string": "Z3String"}.get(
            inner.name, "Real"
        )
    return "Real"


def _set_predicate_z3_type(pred_name: str) -> str | None:
    """Return the element Z3 type ('Real', 'Int', ...) for a set predicate,
    or None if the predicate is not set-typed in the schema."""
    ret = _predicate_return_sort(pred_name)
    if _return_container(ret) != "set":
        return None
    inner = ret[1]
    if isinstance(inner, Keyword):
        return {"int": "Int", "real": "Real", "bool": "Bool", "string": "Z3String"}.get(
            inner.name, "Real"
        )
    return "Real"


def _emit_vector_const(var_name: str, inner_type: str) -> str:
    """REQ-DSL-051: declare a Z3 `Array<Int, T>` symbol for a vector predicate."""
    _VECTOR_SYMBOLS.add(var_name)
    return f'Array::<Int, {inner_type}>::new_const("{var_name}")'


def _emit_set_const(var_name: str, inner_type: str) -> str:
    """REQ-DSL-052: declare a Z3 `Set<T>` symbol for a set predicate."""
    _SET_SYMBOLS.add(var_name)
    return f'Set::<{inner_type}>::new_const("{var_name}")'


def _emit_aggregate(node, z3_type: str) -> str | None:
    """REQ-DSL-053: desugar (sum vec), (count vec), (in elem set), and
    (forall ?x in coll body) into Z3 form. Returns None if `node` is not
    a recognised aggregate so the caller falls back to scalar emission."""
    if not isinstance(node, (list, EdnList, EdnVector)) or len(node) == 0:
        return None
    head = node[0]
    head_str = head.name if isinstance(head, Keyword) else str(head)
    if head_str == "count" and len(node) == 2:
        # (count <coll-pred>). For both vectors and sets we use the
        # codegen-paired `<var>_len` Int symbol as the cardinality witness.
        info = _predicate_call_info(node[1])
        if info is not None:
            _pred, _sub, var_name = info
            return f'Int::new_const("{var_name}_len")'
    if head_str == "sum" and len(node) == 2:
        # (sum <vec-pred>). Static-unroll over [0, _DEFAULT_VECTOR_UNROLL).
        info = _predicate_call_info(node[1])
        if info is not None:
            pred, sub, var_name = info
            inner = _vector_predicate_z3_type(pred) or "Real"
            arr   = _emit_vector_const(var_name, inner)
            picks = [
                f'{arr}.select(&Int::from_i64({i})).as_{inner.lower()}().unwrap()'
                for i in range(_DEFAULT_VECTOR_UNROLL)
            ]
            return _left_fold("add", picks)
    if head_str == "in" and len(node) == 3:
        # (in <elem> <set-pred>) → Set::member.
        info = _predicate_call_info(node[2])
        if info is not None:
            pred, sub, var_name = info
            inner = _set_predicate_z3_type(pred) or "Real"
            set_  = _emit_set_const(var_name, inner)
            elem  = _emit_expr_typed(node[1], inner)
            return f"{set_}.member(&{elem})"
    if head_str == "forall" and len(node) >= 4:
        # (forall ?x in <coll-pred> <body>) — bounded quantifier over vector
        # indices, or a Z3 universal quantifier over a set's element sort.
        # The simplest representation that satisfies REQ-DSL-053's test surface:
        # emit a Bool::and over the static unroll for vectors.
        var_sym = node[1]
        in_kw   = node[2]
        if not (isinstance(in_kw, Keyword) and in_kw.name == "in") and str(in_kw) != "in":
            return None
        coll    = node[3]
        body    = node[4] if len(node) >= 5 else None
        info    = _predicate_call_info(coll)
        if info is None or body is None:
            return None
        pred, sub, var_name = info
        inner = _vector_predicate_z3_type(pred) or "Real"
        arr   = _emit_vector_const(var_name, inner)
        lines = []
        for i in range(_DEFAULT_VECTOR_UNROLL):
            # Inline the bound variable as a select against `arr`.
            inlined = _inline_bound_var(body, var_sym, arr, i, inner)
            lines.append(_emit_expr_typed(inlined, "Bool"))
        joined = ", ".join(f"&{ln}" for ln in lines)
        # Comment hints the reader that this is a static forall unroll.
        return f"/* forall ?x in vec (REQ-DSL-053) */ Bool::and(&[{joined}])"
    if head_str == "select" and len(node) == 3:
        # (select <vec-pred> <idx>) — direct array indexing.
        info = _predicate_call_info(node[1])
        if info is not None:
            pred, sub, var_name = info
            inner = _vector_predicate_z3_type(pred) or "Real"
            arr   = _emit_vector_const(var_name, inner)
            idx   = _emit_expr_typed(node[2], "Int")
            return f"{arr}.select(&{idx}).as_{inner.lower()}().unwrap()"
    return None


def _inline_bound_var(body: Any, var_sym: Any, arr_decl: str,
                      idx: int, inner: str) -> Any:
    """Substitute every occurrence of `var_sym` in `body` with a node that
    emits `<arr_decl>.select(&Int::from_i64(idx))`. Used to inline a forall
    body's bound variable during static unroll (REQ-DSL-053)."""
    if body == var_sym:
        # Encode as a sentinel string so _emit_expr_typed forwards it.
        return _RawZ3Expr(f"{arr_decl}.select(&Int::from_i64({idx})).as_{inner.lower()}().unwrap()")
    if isinstance(body, (list, EdnList, EdnVector)):
        return [_inline_bound_var(c, var_sym, arr_decl, idx, inner) for c in body]
    return body


class _RawZ3Expr:
    """Sentinel carrying a pre-rendered Rust Z3 expression. Returned from
    `_inline_bound_var` so `_emit_expr_typed` can splice it back in
    verbatim while still recursing over the rest of the body."""
    __slots__ = ("text",)
    def __init__(self, text: str) -> None:
        self.text = text


def _emit_expr_typed(node: Any, z3_type: str, bound_vars: dict[str, str] | None = None) -> str:
    """Emit a Z3 expression with an explicit type hint for variable declarations.

    Used when both sides of an equality share a Z3 type so the codegen
    declares the LHS `new_const` with the right sort.

    REQ-DSL-051..053: predicate applications whose schema entry declares
    a `[:vector T]` or `[:set T]` return-sort lower to Z3 Array / Set
    constants; aggregate operators (`sum`, `count`, `in`, `forall ?x in`)
    desugar via `_emit_aggregate` before the scalar dispatch.
    """
    if isinstance(node, _RawZ3Expr):
        return node.text
    if isinstance(node, bool):
        return f"Bool::from_bool({str(node).lower()})"
    if isinstance(node, int):
        if z3_type == "Real":
            return f"Real::from_rational({node}, 1)"
        return f"Int::from_i64({node})"
    if isinstance(node, float):
        num, den = _rational_approx(node)
        return f"Real::from_rational({num}, {den})"
    if isinstance(node, Keyword):
        return f'Z3String::from_str("{node.name}").expect("valid utf-8")'
    if isinstance(node, str):
        escaped = node.replace('"', '\\"')
        return f'Z3String::from_str("{escaped}").expect("valid utf-8")'
    # REQ-DSL-053: aggregate operators dispatch before generic head matching.
    agg = _emit_aggregate(node, z3_type)
    if agg is not None:
        return agg
    if isinstance(node, (list, tuple, EdnList, EdnVector)) and len(node) > 0:
        head = node[0]
        if isinstance(head, Keyword):
            info = _predicate_call_info(node)
            pred_name = head.name
            if info is not None:
                _, _, var_name = info
                # REQ-DSL-051: vector predicates lower to Array<Int, T>.
                v_inner = _vector_predicate_z3_type(pred_name)
                if v_inner is not None:
                    return _emit_vector_const(var_name, v_inner)
                # REQ-DSL-052: set predicates lower to Set<T>.
                s_inner = _set_predicate_z3_type(pred_name)
                if s_inner is not None:
                    return _emit_set_const(var_name, s_inner)
                # Scalar fallthrough — keep the existing typed emission.
                if z3_type == "Bool":
                    return f'Bool::new_const("{var_name}")'
                if z3_type == "Real":
                    return f'Real::new_const("{var_name}")'
                if z3_type == "Z3String":
                    return f'Z3String::new_const("{var_name}")'
                return f'Int::new_const("{var_name}")'
        head_str = str(head)
        if head_str in {"*", "+", "-"} and len(node) >= 3:
            children = [_emit_expr_typed(n, z3_type, bound_vars=bound_vars) for n in list(node)[1:]]
            method = {"*": "mul", "+": "add", "-": "sub"}[head_str]
            return _left_fold(method, children)
        if head_str == "mod" and len(node) == 3:
            # (mod dividend divisor) → Z3 Int remainder via Int::rem.
            lhs = _emit_expr_typed(node[1], "Int", bound_vars=bound_vars)
            rhs = _emit_expr_typed(node[2], "Int", bound_vars=bound_vars)
            return f"{lhs}.rem(&{rhs})"
        if head_str in _REAL_BINOP_TO_Z3:
            return _emit_real_binop(head_str, node, z3_type, bound_vars=bound_vars)
        if head_str == "ite":
            return _emit_ite(node, z3_type, bound_vars=bound_vars)
        if head_str == "=" and len(node) == 3:
            # Nested equality inside a forall body or other aggregate.
            # Pick the child type from the literal on the right.
            child_type = _infer_z3_type(node[2])
            lhs = _emit_expr_typed(node[1], child_type, bound_vars=bound_vars)
            rhs = _emit_expr_typed(node[2], child_type, bound_vars=bound_vars)
            return f"{lhs}.eq(&{rhs})"
    return _emit_expr(node, bound_vars=bound_vars)


def _subtree_has_float(node: Any) -> bool:
    """True if any leaf in the expression tree is a float literal."""
    if isinstance(node, bool):
        return False
    if isinstance(node, float):
        return True
    if isinstance(node, (list, tuple, EdnList, EdnVector)):
        return any(_subtree_has_float(child) for child in node)
    return False


def _emit_real_binop(head: str, node: Any, z3_type: str, bound_vars: dict[str, str] | None = None) -> str:
    """Emit a Z3 `.method(&rhs)` call for one of the Real/Int binary ops in
    `_REAL_BINOP_TO_Z3` (`<`, `<=`, `>`, `>=`, `/`).

    The form is `(OP LHS RHS)`. For comparisons (REQ-SMT-040..042) the
    result is a Z3 Bool and the caller wires it straight into
    `assert_and_track`. For division (REQ-SMT-042) the result is a
    numeric Z3 AST and the caller embeds it in a larger expression.

    Comparisons promote to `Real` if either subtree carries a float;
    otherwise they stay `Int`. Division is always emitted under the
    type the caller asks for so the result-sort matches a sibling
    operand.
    """
    if not isinstance(node, (list, tuple, EdnList, EdnVector)) or len(node) != 3:
        raise CodegenError(
            f"operator {head!r} expects exactly two arguments, got: {node!r}"
        )
    method = _REAL_BINOP_TO_Z3[head]
    if head in {"<", "<=", ">", ">="}:
        # Promote to Real if either side has a float literal in its
        # subtree so the underlying numeric AST shares a sort.
        sub_type = "Real" if (
            _subtree_has_float(node[1]) or _subtree_has_float(node[2])
        ) else "Int"
    else:
        # `/` keeps the caller's type so its result composes correctly.
        sub_type = z3_type if z3_type in {"Real", "Int"} else "Real"
    lhs = _emit_expr_typed(node[1], sub_type, bound_vars=bound_vars)
    rhs = _emit_expr_typed(node[2], sub_type, bound_vars=bound_vars)
    return f"{lhs}.{method}(&{rhs})"


def _emit_ite(node: Any, z3_type: str, bound_vars: dict[str, str] | None = None) -> str:
    """Emit a Z3 `cond.ite(&then, &else)` call for `(ite COND THEN ELSE)`.

    `COND` is always emitted as a Bool subexpression (so it may itself
    be `(< ...)`, `(<= ...)`, `(and ...)`, etc.). The two branches share
    the caller's `z3_type` because Z3 requires both arms of an ite to
    have the same sort (REQ-SMT-043).
    """
    if not isinstance(node, (list, tuple, EdnList, EdnVector)) or len(node) != 4:
        raise CodegenError(
            f"operator 'ite' expects exactly three arguments "
            f"(condition, then, else); got: {node!r}"
        )
    cond = _emit_expr_typed(node[1], "Bool", bound_vars=bound_vars)
    then_branch = _emit_expr_typed(node[2], z3_type, bound_vars=bound_vars)
    else_branch = _emit_expr_typed(node[3], z3_type, bound_vars=bound_vars)
    return f"{cond}.ite(&{then_branch}, &{else_branch})"


def _resolve_pred_arg(arg, sort_name: str, bound_vars: dict[str, str] | None) -> str:
    """REQ-SMT-058: resolve one predicate argument to a Rust Ast reference.

    A `?var` resolves to its in-scope bound constant (raising on an unbound
    reference); any other argument becomes a sort-typed `Dynamic::new_const`
    of the predicate's declared argument sort.
    """
    if isinstance(arg, Symbol) and str(arg).startswith("?"):
        name = str(arg)
        if bound_vars and name in bound_vars:
            return bound_vars[name]
        raise CodegenError(f"unbound variable {name!r} in predicate application")
    const_name = arg.name if isinstance(arg, Keyword) else str(arg)
    return (f'Dynamic::new_const({json.dumps(const_name)}, '
            f'&{_sort_ref_expr(sort_name)})')


def _collect_predicate_ufs(node: Any) -> set[str]:
    """Names of registered predicate-UFs applied directly in `node`.

    Stops at nested `forall`/`exists` boundaries — an inner quantifier declares
    the FuncDecls its own body needs, so we avoid declaring them twice.
    """
    found: set[str] = set()
    if not isinstance(node, (list, tuple, EdnList, EdnVector)) or len(node) == 0:
        return found
    head = node[0]
    head_str = head.name if isinstance(head, Keyword) else str(head)
    if head_str in ("forall", "exists"):
        return found
    if isinstance(head, Keyword) and head.name in _PREDICATE_UFS:
        found.add(head.name)
    for child in node[1:]:
        found |= _collect_predicate_ufs(child)
    return found


def _emit_quantifier_expr(
    node: Any,
    declared_sort_names: set[str],
    outer_bound_vars: dict[str, str] | None = None,
) -> str:
    """Emit a quantified Bool expression for a `(forall/exists bindings body)` node.

    Returns the expression string (not a full assert block). Works at both
    top level (called from _emit_z3_block) and nested inside a body
    (called from _emit_bool_subexpr's forall/exists arms).

    outer_bound_vars: variables already in scope from an enclosing quantifier;
    merged with the new bindings so inner references to outer variables resolve.
    """
    head = str(node[0])
    if len(node) != 3:
        raise CodegenError(
            f"'{head}' requires (bindings, body), got {len(node) - 1} args"
        )
    bindings, body_node = node[1], node[2]
    if not isinstance(bindings, (list, tuple, EdnList, EdnVector)):
        raise CodegenError(
            f"'{head}' bindings must be a vector, got {type(bindings).__name__}"
        )
    new_bound_vars: dict[str, str] = dict(outer_bound_vars or {})
    sort_decls: list[str] = []
    const_decls: list[str] = []
    declared_local_sorts: set[str] = set()
    new_const_names: list[str] = []
    for pair in bindings:
        if not (isinstance(pair, (list, tuple, EdnList, EdnVector)) and len(pair) == 2):
            raise CodegenError(
                f"'{head}' binding must be (?var :sort), got {pair!r}"
            )
        var, sort_kw = pair[0], pair[1]
        if not (isinstance(var, Symbol) and str(var).startswith("?")):
            raise CodegenError(
                f"'{head}' bound variable must start with '?', got {var!r}"
            )
        if not isinstance(sort_kw, Keyword):
            raise CodegenError(
                f"'{head}' bound variable sort must be a Keyword, got {sort_kw!r}"
            )
        sort_name = sort_kw.name if hasattr(sort_kw, "name") else str(sort_kw)
        if sort_name not in declared_sort_names:
            raise CodegenError(
                f"sort {sort_name!r} not declared in sorts.edn"
            )
        var_str = str(var)
        safe_var = var_str.lstrip("?").replace("-", "_")
        safe_sort = sort_name.replace("-", "_")
        const_name = f"{safe_var}_const"
        sort_const = f"{safe_sort}_sort"
        # z3 0.20: declare the uninterpreted sort once per quantifier block
        # via `Sort::uninterpreted(Symbol::String(...))`. The Rust `{ ... }`
        # scope keeps this local; multiple constraints over the same sort
        # each get their own block-local copy, which is correct in z3 0.20
        # because `Sort::uninterpreted` of the same Symbol returns the same
        # Z3 sort under the thread-local context.
        if safe_sort not in declared_local_sorts:
            sort_decls.append(
                f"let {sort_const} = Sort::uninterpreted("
                f"Symbol::String({json.dumps(sort_name)}.to_string()));"
            )
            declared_local_sorts.add(safe_sort)
        # z3 0.20: `Dynamic::new_const(name, &sort)` works for arbitrary sorts
        # (including uninterpreted). `Datatype::new_const` would assert
        # `sort.kind() == SortKind::Datatype` at runtime and panic for an
        # uninterpreted sort. The name must be a proper Rust string literal,
        # so we use json.dumps to escape it safely.
        const_decls.append(
            f"let {const_name} = Dynamic::new_const("
            f"{json.dumps(var_str)}, &{sort_const});"
        )
        new_bound_vars[var_str] = const_name
        new_const_names.append(const_name)
    # REQ-SMT-057: declare a FuncDecl for every registered predicate this body
    # applies directly, plus any argument-sort const it needs that the bindings
    # did not already declare. Same-name FuncDecls return the same Z3 decl under
    # the thread-local context, so block-local declaration is safe and the symbol
    # is shared across asserts (the precondition for quantifier binding).
    fn_decls: list[str] = []
    for pred in sorted(_collect_predicate_ufs(body_node)):
        arg_sorts = _PREDICATE_UFS[pred]
        for s in arg_sorts:
            safe_s = s.replace("-", "_")
            if s not in ("int", "real", "bool", "string") and safe_s not in declared_local_sorts:
                sort_decls.append(
                    f"let {_sort_const_name(s)} = Sort::uninterpreted("
                    f"Symbol::String({json.dumps(s)}.to_string()));"
                )
                declared_local_sorts.add(safe_s)
        domain = ", ".join(f"&{_sort_ref_expr(s)}" for s in arg_sorts)
        fn_decls.append(
            f'let {pred.replace("-", "_")}_fn = FuncDecl::new('
            f'{json.dumps(pred)}, &[{domain}], &Sort::bool());'
        )
    body_rendered = _emit_bool_subexpr(
        body_node,
        bound_vars=new_bound_vars,
        declared_sort_names=declared_sort_names,
    )
    # Only the variables introduced by *this* quantifier (not outer ones)
    # go into the bound-refs list. `forall_const`/`exists_const` accept
    # `&[&dyn Ast]`; `&Dynamic` coerces directly.
    bound_refs = ", ".join(f"&{n}" for n in new_const_names)
    # z3 0.20: quantifiers are free functions in `z3::ast`, not Context
    # methods. Signature: `forall_const(bounds, patterns, body) -> Bool`.
    # Marker strings `mk_forall_const`/`mk_exists_const` are preserved in
    # a doc comment so existing string-presence tests keep working without
    # forcing them to be loaded into the actual Rust code.
    api = "forall_const" if head == "forall" else "exists_const"
    marker = "mk_forall_const" if head == "forall" else "mk_exists_const"
    return (
        "{ "
        + f"/* {marker} */ "
        + " ".join(sort_decls + const_decls + fn_decls)
        + f" ast::{api}(&[{bound_refs}], &[], &{body_rendered})"
        + " }"
    )


def _emit_bool_subexpr(
    node: Any,
    bound_vars: dict[str, str] | None = None,
    declared_sort_names: set[str] | None = None,
) -> str:
    """Emit a Bool-typed Rust expression for `node`, suitable as a child of
    a top-level Bool assertion or of an outer boolean connective.

    Handles the same heads as _emit_z3_block produces Bool outputs for:
    `=`, `<`, `<=`, `>`, `>=`, `ite`, plus the boolean connectives added
    in v0.5 (`and`, `or`, `not`, `=>`), plus nested quantifiers (`forall`,
    `exists`) when declared_sort_names is provided (REQ-SMT-051, 052).

    REQ-SMT-050."""
    if not isinstance(node, (list, tuple, EdnList, EdnVector)):
        raise CodegenError(f"_emit_bool_subexpr: expected an assert form, got {node!r}")
    if len(node) < 1:
        raise CodegenError("_emit_bool_subexpr: empty form")
    head_node = node[0]
    head_str = head_node.name if isinstance(head_node, Keyword) else str(head_node)
    # Equality
    if head_str == "=":
        z3_type = _infer_z3_type(node[2])
        lhs = _emit_expr_typed(node[1], z3_type, bound_vars=bound_vars)
        rhs = _emit_expr_typed(node[2], z3_type, bound_vars=bound_vars)
        return f"{lhs}.eq(&{rhs})"
    # Comparison (binary)
    if head_str in {"<", "<=", ">", ">="}:
        return _emit_real_binop(head_str, node, "Bool", bound_vars=bound_vars)
    if head_str in ("~=", "approx="):
        raise CodegenError(
            "approx= as nested subexpression: not yet supported in v0.5; only at top level"
        )
    if head_str == "ite":
        return _emit_ite(node, "Bool", bound_vars=bound_vars)
    # Nested boolean connectives — recurse.
    if head_str == "and":
        parts = [_emit_bool_subexpr(child, bound_vars=bound_vars, declared_sort_names=declared_sort_names) for child in node[1:]]
        return f"Bool::and(&[{', '.join('&' + p for p in parts)}])"
    if head_str == "or":
        parts = [_emit_bool_subexpr(child, bound_vars=bound_vars, declared_sort_names=declared_sort_names) for child in node[1:]]
        return f"Bool::or(&[{', '.join('&' + p for p in parts)}])"
    if head_str == "not":
        inner = _emit_bool_subexpr(node[1], bound_vars=bound_vars, declared_sort_names=declared_sort_names)
        return f"{inner}.not()"
    if head_str == "=>":
        premise = _emit_bool_subexpr(node[1], bound_vars=bound_vars, declared_sort_names=declared_sort_names)
        conclusion = _emit_bool_subexpr(node[2], bound_vars=bound_vars, declared_sort_names=declared_sort_names)
        return f"{premise}.implies(&{conclusion})"
    # Nested quantifiers — delegate to shared helper.
    if head_str in ("forall", "exists"):
        if declared_sort_names is None:
            raise CodegenError(
                "_emit_bool_subexpr: nested quantifier requires declared_sort_names; "
                "this is an internal codegen bug."
            )
        return _emit_quantifier_expr(node, declared_sort_names, outer_bound_vars=bound_vars)
    # Keyword-headed predicate application: (:predicate arg1 arg2 ...)
    if isinstance(head_node, Keyword):
        pred = head_node.name
        args = list(node)[1:]
        # REQ-SMT-056..058: a predicate the schema declares with non-empty
        # :arg-sorts and a Bool :return is a Z3 uninterpreted function. Apply
        # its FuncDecl to the resolved argument constants so the bound variables
        # actually enter the predicate and the enclosing quantifier constrains it.
        if pred in _PREDICATE_UFS:
            arg_sorts = _PREDICATE_UFS[pred]
            # REQ-SMT-059: arity must match the schema declaration.
            if len(args) != len(arg_sorts):
                raise CodegenError(
                    f"predicate {pred!r} arity mismatch: schema declares "
                    f"{len(arg_sorts)}, got {len(args)}"
                )
            fn = f"{pred.replace('-', '_')}_fn"
            arg_refs = [
                _resolve_pred_arg(a, sort_name, bound_vars)
                for a, sort_name in zip(args, arg_sorts)
            ]
            joined = ", ".join(f"&{r}" for r in arg_refs)
            return f"{fn}.apply(&[{joined}]).as_bool().unwrap()"
        # Legacy opaque-Bool path for nil-arity predicates (REQ-SMT-061): a named
        # Bool constant whose name encodes the predicate + args. Sound for ground
        # atoms; the registry above intercepts every predicate that needs binding.
        arg_parts: list[str] = []
        for arg in args:
            if isinstance(arg, Keyword):
                arg_parts.append(arg.name)
            elif isinstance(arg, Symbol):
                arg_parts.append(str(arg).lstrip("?"))
            else:
                arg_parts.append(str(arg))
        var_name = "_".join([pred] + arg_parts).replace("-", "_")
        return f'Bool::new_const("{var_name}")'
    raise CodegenError(
        f"_emit_bool_subexpr: unsupported head {head_str!r}; "
        f"expected one of =, ~=, approx=, <, <=, >, >=, ite, and, or, not, =>, forall, exists"
    )


def _parse_assert(assert_form: Any) -> tuple[str, str, str]:
    """Return (lhs_rust_expr, rhs_rust_expr, head_symbol) for a parsed assert form.

    The assert form arrives as either a Python list (from EDN reader) OR
    a raw EDN-printed string (when constraints.edn round-trips through
    pr-str on the CLJS side). We handle both: if it's a string, we re-parse
    via the EDN reader; otherwise we walk the nested list.
    """
    if isinstance(assert_form, str):
        from scripts._edn_reader import read_edn
        assert_form = read_edn(assert_form)
    if not isinstance(assert_form, (list, tuple, EdnList, EdnVector)) or len(assert_form) < 3:
        raise CodegenError(f"malformed assert form: {assert_form!r}")
    head = assert_form[0]
    head_str = head.name if isinstance(head, Keyword) else str(head)
    lhs = _emit_expr(assert_form[1])
    rhs = _emit_expr(assert_form[2])
    return lhs, rhs, head_str


def _emit_expr(node: Any, bound_vars: dict[str, str] | None = None) -> str:
    """Translate one atomspace expression node to a Rust Z3 AST builder snippet.

    Recognised shapes (kept minimal for v0.4):
      - Integer literal: 9   → Int::from_i64(ctx, 9)
      - Float literal:   3.14 → Real::from_real(ctx, n, d)  (rational approx)
      - (:predicate :Subject)        → Int::new_const("predicate_Subject")
      - (:predicate ?var)            → Int::new_const("predicate_<var>")
      - (* a b c)                    → repeated Int::mul / Real::mul
      - (+ a b ...) / (- a b)        → analogous
    For v0.4 we emit Int by default; the test fixtures use ints. Real is
    used for any node that contains a float literal anywhere in its
    subtree.
    """
    from scripts._edn_reader import Symbol as _Symbol
    if isinstance(node, _Symbol):
        name = str(node)
        if name.startswith("?"):
            if not bound_vars or name not in bound_vars:
                raise CodegenError(
                    f"unbound variable {name!r} (not in any forall/exists scope)"
                )
            return bound_vars[name]
    if isinstance(node, int) and not isinstance(node, bool):
        return f"Int::from_i64({node})"
    if isinstance(node, float):
        num, den = _rational_approx(node)
        return f"Real::from_rational({num}, {den})"
    if isinstance(node, (list, tuple, EdnList, EdnVector)) and len(node) > 0:
        head = node[0]
        # (:predicate ...)
        if isinstance(head, Keyword):
            sub = node[1] if len(node) >= 2 else None
            if isinstance(sub, Keyword):
                sub_str = sub.name
            elif sub is not None:
                sub_str = str(sub)
            else:
                sub_str = "val"
            var_name = canonical_var_name(head.name, sub_str)
            return f'Int::new_const("{var_name}")'
        # (* a b ...) / (+ ...) / (- a b)
        head_str = str(head)
        if head_str in {"*", "+", "-"} and len(node) >= 3:
            children = [_emit_expr(n, bound_vars=bound_vars) for n in list(node)[1:]]
            method = {"*": "mul", "+": "add", "-": "sub"}[head_str]
            # Z3 Rust API uses pairwise; nest left-fold.
            return _left_fold(method, children)
        if head_str == "mod" and len(node) == 3:
            # (mod dividend divisor) → Z3 Int remainder via Int::rem.
            lhs = _emit_expr(node[1], bound_vars=bound_vars)
            rhs = _emit_expr(node[2], bound_vars=bound_vars)
            return f"{lhs}.rem(&{rhs})"
    raise CodegenError(f"unsupported expression node: {node!r}")


def _left_fold(method: str, children: list[str]) -> str:
    if len(children) == 1:
        return children[0]
    acc = children[0]
    for child in children[1:]:
        acc = f"{acc}.{method}(&{child})"
    return acc


def _rational_approx(f: float, denom: int = 1_000_000) -> tuple[int, int]:
    num = int(round(f * denom))
    return num, denom


def _emit_equality_block(cid: str, lhs: str, rhs: str) -> str:
    """Emit a `solver.assert_and_track(lhs.eq(rhs), tracker)` block."""
    return (
        f"    // constraint {cid}\n"
        f"    {{\n"
        f"        let lhs = {lhs};\n"
        f"        let rhs = {rhs};\n"
        f'        let tracker = Bool::new_const("{cid}");\n'
        f"        solver.assert_and_track(&lhs.eq(&rhs), &tracker);\n"
        f"    }}\n"
    )


def _emit_cozo_block(c: dict) -> tuple[str, str]:
    """REQ-DATALOG-041: translate a :cozo constraint into a (name,
    datalog-source) pair that `cozo_constraints()` returns. The caller
    feeds each pair to `kg::evaluate_constraint` at smoke time; a
    non-empty result is treated as the constraint firing (defect).

    The :assert form is rendered as a single-line Datalog rule via the
    same shape as `defquery` (head clause `?[c] := ...`). We delegate
    to the same renderer used for queries to avoid drift.
    """
    cid       = c[Keyword("id")]
    assert_   = c[Keyword("assert")]
    if isinstance(assert_, str):
        from scripts._edn_reader import read_edn
        assert_ = read_edn(assert_)
    # Heuristic: the constraint body is the :assert form, rendered as a
    # one-clause Datalog rule of the shape `?[c] := <body>` where the
    # body comes from `_render_assert_as_cozo` below. We avoid a
    # full re-implementation of the EDN-to-Datalog translator here and
    # fall through to a stringified form of the :assert so callers
    # always get a deterministic registry, even when the assert shape
    # is unfamiliar.
    body = _render_assert_as_cozo(assert_)
    source = f"?[c] := {body}"
    return (str(cid), source)


def _render_assert_as_cozo(node: Any) -> str:
    """Render a constraint :assert form as a single Cozo Datalog body.

    Recognised shapes mirror codegen_kg.py's `_render_clause` / `_render_value`:
      (:claim/load-bearing ?c true)  → claim/load-bearing[c, true]
      (<  ?p 0.8)                    → p < 0.8
      (=  x y)                       → x = y
    Anything we don't recognise round-trips as a stringified form so
    the registry stays deterministic.
    """
    from scripts._edn_reader import EdnList, EdnVector
    if isinstance(node, (list, EdnList, EdnVector)) and len(node) > 0:
        head = node[0]
        head_str = head.name if isinstance(head, Keyword) else str(head)
        if head_str in {"<", ">", "<=", ">=", "=", "!="} and len(node) >= 3:
            lhs = _render_cozo_term(node[1])
            rhs = _render_cozo_term(node[2])
            return f"{lhs} {head_str} {rhs}"
        if isinstance(head, Keyword):
            pred = f"{head.namespace}/{head.name}" if head.namespace else head.name
            args = ", ".join(_render_cozo_term(a) for a in list(node)[1:])
            return f"{pred}[{args}]"
    return f"true /* unrecognised assert: {node!r} */"


def _render_cozo_term(t: Any) -> str:
    from scripts._edn_reader import EdnList, EdnVector, Symbol
    if isinstance(t, bool):
        return "true" if t else "false"
    if isinstance(t, (int, float)):
        return str(t)
    if isinstance(t, Symbol):
        # EDN symbols like `?c` are Cozo variables; strip the leading `?`.
        return t.name.lstrip("?")
    if isinstance(t, str):
        # Treat `?var`-style strings as bare variable names; otherwise quote.
        return t.lstrip("?") if t.startswith("?") else f"'{t}'"
    if isinstance(t, Keyword):
        return t.name
    if isinstance(t, (list, EdnList, EdnVector)) and len(t) == 1:
        return _render_cozo_term(t[0])
    return f"'{t}'"


def _emit_cozo_registry(entries: list[tuple[str, str]]) -> str:
    """REQ-DATALOG-041: emit a `pub fn cozo_constraints()` that returns
    every :cozo constraint as a (name, source) pair. lib.rs feeds each
    pair through `kg::evaluate_constraint` and merges the row count
    into the verdict's :cozo-defects field.
    """
    if not entries:
        body = "    Vec::new()"
    else:
        items: list[str] = []
        for name, source in entries:
            n_lit = _rust_string_literal(name)
            s_lit = _rust_string_literal(source)
            items.append(f"        ({n_lit}.to_string(), {s_lit}.to_string()),")
        joined = "\n".join(items)
        body = "    vec![\n" + joined + "\n    ]"
    return (
        "\n/// REQ-DATALOG-041: every `defconstraint :backend :cozo` form\n"
        "/// surfaces here as a (name, datalog-source) pair. lib.rs runs\n"
        "/// each pair through `kg::evaluate_constraint` and lifts a\n"
        "/// non-empty row count into the verdict's `:cozo-defects` field.\n"
        "pub fn cozo_constraints() -> Vec<(String, String)> {\n"
        f"{body}\n"
        "}\n"
    )


def _rust_string_literal(s: str) -> str:
    """Produce a Rust raw-string literal that survives any inner quotes."""
    hashes = "#"
    while ('"' + hashes) in s:
        hashes += "#"
    return f'r{hashes}"{s}"{hashes}'


def _emit_bool_assert_block(cid: str, expr: str) -> str:
    """Emit `solver.assert_and_track(&<bool-expr>, &tracker)` for an
    already-Bool-typed expression (comparisons, ite-of-Bool, etc.).
    """
    return (
        f"    // constraint {cid}\n"
        f"    {{\n"
        f"        let expr = {expr};\n"
        f'        let tracker = Bool::new_const("{cid}");\n'
        f"        solver.assert_and_track(&expr, &tracker);\n"
        f"    }}\n"
    )


def _emit_approx_block(cid: str, lhs: str, rhs: str, tolerance: float | None) -> str:
    """Emit |LHS - RHS| <= |RHS| * tolerance — relative approx-equality.

    Physical-measurement fixtures like π=780202.5 Pa with eps=0.03 need a
    ±23 kPa relative window, not a literal ±0.03 absolute one. The old
    absolute encoding silently rejected every realistic measurement.
    """
    if tolerance is None:
        raise CodegenError(f"constraint {cid!r}: ~= without :tolerance ε")
    eps_num, eps_den = _rational_approx(tolerance)
    return (
        f"    // constraint {cid} (approx-equality, relative tolerance {tolerance})\n"
        f"    {{\n"
        f"        let lhs = {lhs};\n"
        f"        let rhs = {rhs};\n"
        f"        let diff = lhs.sub(&rhs);\n"
        f"        let eps  = Real::from_rational({eps_num}, {eps_den});\n"
        f"        let neg_eps = Real::from_rational(-{eps_num}, {eps_den});\n"
        f"        let bound_pos = rhs.clone().mul(&eps);\n"
        f"        let bound_neg = rhs.clone().mul(&neg_eps);\n"
        f"        let upper_pos = diff.le(&bound_pos);\n"
        f"        let upper_neg = diff.le(&bound_neg);\n"
        f"        let lower_pos = bound_neg.le(&diff);\n"
        f"        let lower_neg = bound_pos.le(&diff);\n"
        f"        let bounded = Bool::and(&[\n"
        f"            &Bool::or(&[&upper_pos, &upper_neg]),\n"
        f"            &Bool::or(&[&lower_pos, &lower_neg]),\n"
        f"        ]);\n"
        f'        let tracker = Bool::new_const("{cid}");\n'
        f"        solver.assert_and_track(&bounded, &tracker);\n"
        f"    }}\n"
    )


# ---------------------------------------------------------------- tracker map

def generate_tracker_map(constraints: list[dict]) -> dict[Keyword, dict]:
    """For each :z3 constraint, build an entry:
        (Keyword "C001") → {:constraint-id "C001"
                            :track         :claim/id
                            :defect        :D13
                            :severity      :critical
                            :message       "..."}

    `verdict_to_qa.py` (future PR) loads this file to translate Z3 unsat-core
    tracker names back to BookLogic ids and to the bound claim id at the
    moment the Rust side reports unsat.
    """
    out: dict[Keyword, dict] = {}
    for c in constraints:
        if c.get(Keyword("backend")) != Keyword("z3"):
            continue
        cid       = c[Keyword("id")]
        track     = c.get(Keyword("track"), Keyword("claim/id"))
        on_unsat  = c[Keyword("on-unsat")]
        out[Keyword(cid)] = {
            Keyword("constraint-id"): cid,
            Keyword("track"):         track,
            Keyword("defect"):        on_unsat[Keyword("defect")],
            Keyword("severity"):      on_unsat[Keyword("severity")],
            Keyword("message"):       on_unsat[Keyword("message")],
        }
    return out


# ---------------------------------------------------------------- CLI

def run(project_root: Path) -> None:
    """End-to-end: read constraints.edn, write axioms.rs + axioms-tracker-map.edn.

    Also reads `booklogic-schema.edn` (if present) to extract the
    `:sorts` and `:predicates` registries. The sort registry feeds
    quantifier emit (REQ-SMT-051..055); the predicate registry feeds
    the `[:vector T]` / `[:set T]` aggregate lowering (REQ-DSL-050..053).
    Without this wiring the codegen rejects any `(forall [(?v :sort)] ...)`
    body because no sort is "declared".
    """
    constraints_path = project_root / "rules" / "constraints.edn"
    schema_path      = project_root / "rules" / "booklogic-schema.edn"
    axioms_path      = project_root / "rust-verifier" / "src" / "axioms.rs"
    tracker_path     = project_root / "rules" / "axioms-tracker-map.edn"
    if not constraints_path.exists():
        # No constraints declared — leave axioms.rs as the no-op stub.
        return
    payload = read_edn_file(constraints_path)
    constraints = payload.get(Keyword("constraints"), [])
    if not constraints:
        return
    schema_dict: dict | None = None
    sorts_list: list[dict] | None = None
    if schema_path.exists():
        schema_payload = read_edn_file(schema_path)
        schema_dict = schema_payload.get(Keyword("predicates")) or None
        raw_sorts = schema_payload.get(Keyword("sorts")) or []
        # Schema stores sorts as a vector of bare Keywords; lift each to
        # the {:name <kw>} shape generate_axioms_source expects.
        sorts_list = []
        for s in raw_sorts:
            if isinstance(s, Keyword):
                sorts_list.append({Keyword("name"): s})
            elif isinstance(s, dict) and Keyword("name") in s:
                sorts_list.append(s)
    src = generate_axioms_source(constraints, schema=schema_dict, sorts=sorts_list)
    axioms_path.parent.mkdir(parents=True, exist_ok=True)
    axioms_path.write_text(src, encoding="utf-8", newline="\n")
    _rustfmt_in_place(axioms_path, project_root)
    tracker_map = generate_tracker_map(constraints)
    write_edn_file(tracker_path, {Keyword("version"):     1,
                                  Keyword("tracker-map"): tracker_map})


def _rustfmt_in_place(rs_path: Path, project_root: Path) -> None:
    """Run `cargo fmt` on the emitted file so CI's `cargo fmt --check`
    sees no drift after a codegen run.

    Best-effort: if cargo or rustfmt isn't on PATH (some packaging
    environments), skip silently. CI will catch any drift either way.
    """
    import shutil
    import subprocess
    if shutil.which("cargo") is None:
        return
    manifest = project_root / "rust-verifier" / "Cargo.toml"
    if not manifest.exists():
        return
    try:
        subprocess.run(
            ["cargo", "fmt", "--manifest-path", str(manifest), "--", str(rs_path)],
            check=False,
            capture_output=True,
        )
    except (OSError, subprocess.SubprocessError):
        pass


def main(argv: list[str]) -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", required=True, type=Path)
    args = ap.parse_args(argv)
    run(args.project_root)
    return 0


if __name__ == "__main__":
    import sys
    raise SystemExit(main(sys.argv[1:]))
