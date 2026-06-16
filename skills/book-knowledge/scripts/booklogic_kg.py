"""booklogic_kg — pure EDN->CozoScript compiler (REQ-KG-003).

Homoiconic layer: booklogic EDN is the source of truth and Cozo is the compile
target. :func:`compile_query` lowers a booklogic ``defquery`` form into a
CozoScript string, validating every entity/attr reference against the
``kg-schema.edn`` contract. It is a PURE function: it reads only the schema
file (no pycozo import, no running store), and its output is deterministic
(body atoms emit in source order).

This is a deliberately MINIMAL skeleton. P1 authors the eight competency
queries as EDN and grows this compiler to cover the clause types they need
(aggregation, ordered filters). Extend it only when a real query proves the
need -- do not speculatively add operators.

Grammar supported in P0.5
=========================
A ``defquery`` is the flat EDN list::

    (defquery <name-keyword>
      :find  [<?var> ...]
      :where [[<?evar> :<entity>/<attr> <?var-or-literal>] ...]
      :not   [[<?evar> :<entity>/<attr> <?var-or-literal>] ...])   ; optional

Variable lowering and joins
---------------------------
The compiler models a VARIABLE ENVIRONMENT: every EDN ``?var`` becomes a
CozoScript inline variable, and a column is bound to it by *renaming* in the
stored-relation atom, ``*<relation>{<col>: <var>}``. Two atoms that bind the
SAME variable to one of their columns therefore unify on it -- that is a join,
expressed by Cozo's same-named-binding rule, not by emitting two independent
columns.

* ``:find`` lists the head/output variables (EDN symbols like ``?id``). Each
  find var must be bound somewhere in the body; the emitted head is
  ``?[<vars>]`` with the leading ``?`` stripped.
* ``:where`` is a vector of triples ``[?evar :entity/attr value]``. Triples
  that share the same entity var ``?evar`` collapse into ONE atom
  ``*<snake_entity>{...}``. A triple whose value is a ``?var`` binds the column
  to that var (``col: var``); the same var in another atom unifies (join). A
  triple whose value is a literal becomes an inline match (``col: <literal>``).
* ``:not`` is an optional vector of triples; each entity-var group becomes a
  Cozo negation ``not *<snake_entity>{...}``. A variable used in the negation
  MUST already be bound by the positive body -- the compiler threads it through
  by renaming the negated atom's column to that same var, so "verified claims
  with no source span" lowers to a safe negation. (Cozo rejects a negation
  whose only column is an unbound variable as "unsafe negation".)

Identifier translation reuses :func:`cozo_store.to_snake`: the EDN contract is
kebab-case (``:claim/canonical-text``) and the store layer is snake-case
(``canonical_text``); names are snake-cased on the way into CozoScript. EDN var
names are snake-cased too so a kebab var (``?claim-id``) is a legal Cozo
identifier.

Validation: the entity (keyword namespace) must be a declared entity in
``kg-schema.edn`` and the attr (keyword name after the slash) must be one of
that entity's ``:attrs``; a triple must have arity 3 -- otherwise
:func:`compile_query` raises ``ValueError`` naming the offender.
"""
from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

import edn_format

from scripts.cozo_store import to_snake

__all__ = ["compile_query"]

_FIND = edn_format.Keyword("find")
_WHERE = edn_format.Keyword("where")
_NOT = edn_format.Keyword("not")


def _load_schema_attrs(schema_path: Path) -> dict[str, set[str]]:
    """Return ``{kebab_entity: {kebab_attr, ...}}`` from kg-schema.edn.

    Kept in kebab-case so validation messages name the offender exactly as the
    author wrote it in the EDN query.
    """
    doc = edn_format.loads(Path(schema_path).read_text(encoding="utf-8"))
    entities = doc[edn_format.Keyword("entities")]
    items = entities.dict.items() if hasattr(entities, "dict") else entities.items()
    attrs_kw = edn_format.Keyword("attrs")
    out: dict[str, set[str]] = {}
    for ent_kw, body in items:
        out[ent_kw.name] = {a.name for a in body[attrs_kw]}
    return out


def _split_attr(attr_kw: edn_format.Keyword) -> tuple[str, str]:
    """Split ``:entity/attr`` into ``(entity, attr)`` (both kebab)."""
    ns = getattr(attr_kw, "namespace", None)
    if ns is None:
        raise ValueError(
            f"attribute {attr_kw!r} must be namespaced as :entity/attr"
        )
    return ns, attr_kw.name.split("/", 1)[1]


def _var_name(sym: Any) -> str:
    """Snake-cased bare name of a ``?var`` symbol (leading ``?`` stripped).

    EDN vars may be kebab (``?claim-id``); the store layer is snake, so the
    Cozo variable name is snake-cased to stay a legal identifier and to match
    the column names it unifies with.
    """
    name = sym.name if hasattr(sym, "name") else str(sym)
    if name.startswith("?"):
        name = name[1:]
    return to_snake(name)


def _is_var(value: Any) -> bool:
    return isinstance(value, edn_format.Symbol)


def _format_literal(value: Any) -> str:
    """Render an EDN literal as a CozoScript scalar (strings quoted)."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return f'"{value}"'


class _Atom:
    """One stored-relation atom under construction for a single entity var.

    Collects column bindings in first-seen order. Each binding is either a
    variable rename (``col: var``) or an inline literal match (``col: lit``).
    """

    def __init__(self, relation: str) -> None:
        self.relation = relation
        self._order: list[str] = []  # snake columns, first-seen order
        self._binding: dict[str, str] = {}  # col -> rendered RHS (var or literal)

    def bind(self, col: str, rhs: str) -> None:
        if col not in self._binding:
            self._order.append(col)
        self._binding[col] = rhs

    def render(self, negate: bool = False) -> str:
        inner = ", ".join(f"{c}: {self._binding[c]}" for c in self._order)
        atom = f"*{self.relation}{{{inner}}}"
        return f"not {atom}" if negate else atom


def _compile_clauses(
    clauses: Any,
    schema: dict[str, set[str]],
    env: set[str],
    *,
    negate: bool,
) -> list[str]:
    """Lower a :where / :not vector into rendered atoms.

    Triples sharing an entity var collapse into one ``*relation{...}`` atom.
    A var-valued column binds the column to that var (``col: var``) and records
    the var in ``env`` (the variable environment of bound names) so later atoms
    and :find can reference it; reusing a var name in another atom yields a join.
    A literal-valued column emits an inline match (``col: literal``).

    For ``negate=True`` (a :not clause) every var used must ALREADY be in ``env``
    (bound by the positive body); otherwise the negation would be unsafe (Cozo
    rejects "Encountered unsafe negation"). Negation atoms do not extend ``env``.
    """
    order: list[str] = []  # evar keys in first-seen order
    atoms: dict[str, _Atom] = {}

    for triple in clauses:
        if isinstance(triple, (str, bytes)) or not isinstance(triple, Sequence) or len(triple) != 3:
            raise ValueError(
                f"malformed triple {triple!r}: expected "
                f"[?evar :entity/attr value] (arity 3)"
            )
        evar, attr_kw, value = triple[0], triple[1], triple[2]
        entity, attr = _split_attr(attr_kw)
        if entity not in schema:
            raise ValueError(
                f"unknown entity ':{entity}' in clause {triple!r} "
                f"(not declared in kg-schema.edn)"
            )
        if attr not in schema[entity]:
            raise ValueError(
                f"unknown attr ':{entity}/{attr}' in clause {triple!r} "
                f"(not an attr of entity ':{entity}' in kg-schema.edn)"
            )

        key = _var_name(evar)
        if key not in atoms:
            order.append(key)
            atoms[key] = _Atom(to_snake(entity))
        col = to_snake(attr)

        if _is_var(value):
            var = _var_name(value)
            if negate and var not in env:
                raise ValueError(
                    f"unsafe negation in clause {triple!r}: variable "
                    f"'?{var}' is not bound by the positive :where body"
                )
            atoms[key].bind(col, var)
            if not negate:
                env.add(var)
        else:
            atoms[key].bind(col, _format_literal(value))

    return [atoms[k].render(negate=negate) for k in order]


def compile_query(edn: str, schema_path: Path) -> str:
    """Compile a booklogic ``defquery`` EDN string into CozoScript.

    Pure: reads only ``schema_path`` (the kg-schema.edn contract); never
    imports pycozo or touches a store. Deterministic: body atoms emit in
    source order. Raises ``ValueError`` for a malformed form, a malformed
    triple, an unbound :find/negation variable, or an entity/attr not declared
    in the schema.
    """
    schema = _load_schema_attrs(Path(schema_path))
    form = edn_format.loads(edn)

    if not isinstance(form, (tuple, list)) or len(form) < 1:
        raise ValueError("query must be a (defquery ...) form")
    head = form[0]
    if not (hasattr(head, "name") and head.name == "defquery"):
        raise ValueError(f"expected a defquery form, got {head!r}")

    # The form is flat: defquery <name> :find [..] :where [..] (:not [..])?
    # Walk it as keyword/value pairs after the name.
    sections: dict[Any, Any] = {}
    i = 2  # skip 'defquery' and the name keyword
    while i + 1 < len(form):
        sections[form[i]] = form[i + 1]
        i += 2

    if _FIND not in sections:
        raise ValueError("defquery missing :find clause")
    if _WHERE not in sections:
        raise ValueError("defquery missing :where clause")

    # Variable environment: the set of body variables bound by :where atoms.
    # :find and :not variables must resolve against it.
    env: set[str] = set()
    positive = _compile_clauses(sections[_WHERE], schema, env, negate=False)
    negations: list[str] = []
    if _NOT in sections:
        negations = _compile_clauses(sections[_NOT], schema, env, negate=True)

    find_vars = [_var_name(v) for v in sections[_FIND]]
    for v in find_vars:
        if v not in env:
            raise ValueError(
                f":find variable '?{v}' is not bound by the :where body"
            )

    # Order in CozoScript body: positive atoms, then negation atoms. Each atom
    # already carries its column renames and inline literal matches, so no
    # trailing equality filters are needed.
    body_str = ", ".join(positive + negations)
    head_str = f"?[{', '.join(find_vars)}]"
    return f"{head_str} := {body_str}"
