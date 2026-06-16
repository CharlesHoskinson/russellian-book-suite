"""booklogic_kg — pure EDN->CozoScript compiler (REQ-KG-003).

Homoiconic layer: booklogic EDN is the source of truth and Cozo is the compile
target. :func:`compile_query` lowers a booklogic ``defquery`` form into a
CozoScript string, validating every entity/attr reference against the
``kg-schema.edn`` contract. It is a PURE function: it reads only the schema
file (no pycozo import, no running store), and its output is deterministic
(body atoms emit in source order).

This is a deliberately MINIMAL skeleton. P1 authors the eight competency
queries as EDN and grows this compiler to cover the clause types they need
(joins across entity vars, aggregation, ordered filters). Extend it only when a
real query proves the need -- do not speculatively add operators.

Grammar supported in P0.5
=========================
A ``defquery`` is the flat EDN list::

    (defquery <name-keyword>
      :find  [<?var> ...]
      :where [[<?evar> :<entity>/<attr> <?var-or-literal>] ...]
      :not   [[<?evar> :<entity>/<attr> <?var-or-literal>] ...])   ; optional

* ``:find`` lists the head/output variables (EDN symbols like ``?id``). The
  emitted head is ``?[<vars>]`` with the leading ``?`` stripped from each var.
* ``:where`` is a vector of triples ``[?evar :entity/attr value]``. Triples
  that share the same entity var ``?evar`` are grouped into ONE body atom
  ``*<snake_entity>{<cols>}`` whose columns are the attrs (in first-seen
  order). A triple whose value is a literal (string/number/bool) additionally
  emits a filter ``<col> <op> <literal>`` (``==``). A triple whose value is a
  variable simply binds that column to the variable.
* ``:not`` is an optional vector of triples; each entity-var group becomes a
  Cozo negation ``not *<snake_entity>{<cols>}`` appended after the positive
  body. This is the lowering of SPARQL ``FILTER NOT EXISTS``.

Identifier translation reuses :func:`cozo_store.to_snake`: the EDN contract is
kebab-case (``:claim/canonical-text``) and the store layer is snake-case
(``canonical_text``); names are snake-cased on the way into CozoScript.

Validation: the entity (keyword namespace) must be a declared entity in
``kg-schema.edn`` and the attr (keyword name after the slash) must be one of
that entity's ``:attrs`` -- otherwise :func:`compile_query` raises
``ValueError`` naming the offender.
"""
from __future__ import annotations

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
    """Bare name of a ``?var`` symbol with the leading ``?`` stripped."""
    name = sym.name if hasattr(sym, "name") else str(sym)
    return name[1:] if name.startswith("?") else name


def _is_var(value: Any) -> bool:
    return isinstance(value, edn_format.Symbol)


def _format_literal(value: Any) -> str:
    """Render an EDN literal as a CozoScript scalar (strings quoted)."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return f'"{value}"'


def _compile_clauses(
    clauses: Any, schema: dict[str, set[str]], negate: bool
) -> tuple[list[str], list[str]]:
    """Lower a :where / :not vector into (body atoms, equality filters).

    Triples sharing an entity var collapse into one ``*relation{cols}`` atom.
    When ``negate`` is true the atom is prefixed ``not `` and literal triples
    are not emitted as separate filters (Cozo binds the literal inside the
    negated atom is out of scope for P0.5 -- negations here are existence
    checks keyed by the bound variable).
    """
    # Preserve first-seen order of entity vars and their columns.
    order: list[str] = []
    rels: dict[str, str] = {}  # evar -> snake entity
    cols: dict[str, list[str]] = {}  # evar -> ordered snake cols
    filters: list[str] = []

    for triple in clauses:
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
        if key not in rels:
            order.append(key)
            rels[key] = to_snake(entity)
            cols[key] = []
        col = to_snake(attr)
        if col not in cols[key]:
            cols[key].append(col)
        if not negate and not _is_var(value):
            filters.append(f"{col} == {_format_literal(value)}")

    atoms = []
    for key in order:
        atom = f"*{rels[key]}{{{', '.join(cols[key])}}}"
        atoms.append(f"not {atom}" if negate else atom)
    return atoms, filters


def compile_query(edn: str, schema_path: Path) -> str:
    """Compile a booklogic ``defquery`` EDN string into CozoScript.

    Pure: reads only ``schema_path`` (the kg-schema.edn contract); never
    imports pycozo or touches a store. Deterministic: body atoms emit in
    source order. Raises ``ValueError`` for a malformed form or an
    entity/attr not declared in the schema.
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

    find_vars = [_var_name(v) for v in sections[_FIND]]
    body, filters = _compile_clauses(sections[_WHERE], schema, negate=False)
    if _NOT in sections:
        neg_atoms, _ = _compile_clauses(sections[_NOT], schema, negate=True)
        body += neg_atoms  # negations follow the positive body and filters

    # Order in CozoScript body: positive atoms, then equality filters, then
    # negation atoms. This keeps the equality filters adjacent to the positive
    # atoms whose columns they constrain.
    positive = [a for a in body if not a.startswith("not ")]
    negations = [a for a in body if a.startswith("not ")]
    body_str = ", ".join(positive + filters + negations)
    head_str = f"?[{', '.join(find_vars)}]"
    return f"{head_str} := {body_str}"
