"""cozo_store — the single Python<->store seam over a backend-agnostic store.

REQ-KG-002: the knowledge graph is exposed through ONE Python seam module
(`cozo_store`) presenting ``query(edn) -> rows`` and ``load(relation, rows)``.

REQ-KG-002b: THIS MODULE IS THE ONLY PLACE ALLOWED TO IMPORT ``pycozo`` or to
emit CozoScript text. Everything else routes through :class:`CozoStore` so the
Cozo->Asami swap (REQ-KG-007) stays a one-module change. The pycozo dependency
is isolated inside :class:`CozoBackend`; ``import pycozo`` appears nowhere else.

REQ-KG-007: :class:`CozoStore` talks only to a :class:`Backend`. The real
backend is :class:`CozoBackend` (embedded Cozo via pycozo); :class:`StubBackend`
is a pure-Python in-memory backend that satisfies the same contract for the
query shapes the tests exercise, so later tasks can unit-test without the
embedded Cozo and so the backend can later be swapped (Asami/DataScript) without
touching callers.

REQ-KG-011: :meth:`CozoStore.in_memory` creates exactly one relation per entity
declared in ``assets/kg-schema.edn`` and nothing else.

Identifier translation: ``kg-schema.edn`` uses kebab-case keywords
(``:canonical-text``, ``code-node``). Store identifiers must match
``[a-zA-Z_][a-zA-Z0-9_]*`` -- hyphens are illegal -- so every relation/column
name is snake-cased on the way into the store. The EDN contract stays kebab; the
store layer is snake. :func:`to_snake` is the one translation helper.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable, Mapping, Protocol, runtime_checkable

import edn_format

__all__ = ["CozoStore", "Backend", "CozoBackend", "StubBackend", "to_snake"]


def to_snake(name: str) -> str:
    """Translate a kebab-case schema identifier to a store-legal snake_case one.

    The EDN contract is kebab-case; store identifiers must match
    ``[a-zA-Z_][a-zA-Z0-9_]*``. This is the single kebab->snake helper used for
    both relation names and column names.
    """
    return name.replace("-", "_")


def _kw_name(keyword: Any) -> str:
    """Return the bare name of an edn_format Keyword (kebab, no leading colon)."""
    return keyword.name


# EDN :types keyword -> Cozo value-column type (key columns drop the trailing
# ``?``; value columns keep it). Absent from the map => String.
_COZO_TYPE = {"float": "Float", "int": "Int", "bool": "Bool", "string": "String"}


def _cozo_type(type_kw: str | None) -> str:
    """Map an EDN :types value (bare name, or None) to a Cozo base type name."""
    if type_kw is None:
        return "String"
    return _COZO_TYPE.get(type_kw, "String")


def _parse_schema(
    schema_path: Path,
) -> tuple[dict[str, list[str]], dict[str, dict[str, str]]]:
    """Parse kg-schema.edn into columns + per-column Cozo types.

    Returns ``(relations, types)`` where ``relations`` is
    ``{snake_entity: [snake_col, ...]}`` (first attr is the identity/key column)
    and ``types`` is ``{snake_entity: {snake_col: cozo_base_type}}`` carrying
    only the columns whose EDN type is non-string. Columns absent from a
    relation's type map default to ``String``. Names are snake-cased here so
    callers never see kebab.
    """
    doc = edn_format.loads(schema_path.read_text(encoding="utf-8"))
    entities = doc[edn_format.Keyword("entities")]
    items = entities.dict.items() if hasattr(entities, "dict") else entities.items()
    attrs_kw = edn_format.Keyword("attrs")
    types_kw = edn_format.Keyword("types")

    out: dict[str, list[str]] = {}
    types: dict[str, dict[str, str]] = {}
    for ent_kw, body in items:
        attrs = body[attrs_kw]
        cols = [to_snake(_kw_name(a)) for a in attrs]
        ent = to_snake(_kw_name(ent_kw))
        out[ent] = cols

        raw_types = body.get(types_kw) if hasattr(body, "get") else None
        if raw_types is not None:
            t_items = (
                raw_types.dict.items()
                if hasattr(raw_types, "dict")
                else raw_types.items()
            )
            types[ent] = {
                to_snake(_kw_name(col_kw)): _cozo_type(_kw_name(type_kw))
                for col_kw, type_kw in t_items
            }
        else:
            types[ent] = {}
    return out, types


# -- backend seam (REQ-KG-002b / REQ-KG-007) -------------------------------


@runtime_checkable
class Backend(Protocol):
    """The store boundary :class:`CozoStore` depends on.

    A backend owns relation creation, row upsert, and read queries. Cozo->Asami
    (REQ-KG-007) is a one-class swap: implement these four methods. Names are
    snake-cased by :class:`CozoStore` before they reach the backend.
    """

    def create(
        self, relation: str, cols: list[str], col_types: Mapping[str, str]
    ) -> None:
        """Create ``relation`` with ``cols`` (first col is the key).

        ``col_types`` maps a column to its base type name (Cozo spelling, e.g.
        ``Float``); columns absent default to ``String``.
        """

    def put(self, relation: str, cols: list[str], rows: list[list[Any]]) -> None:
        """Upsert ``rows`` (column-ordered, aligned with ``cols``)."""

    def run(
        self, script: str, params: Mapping[str, Any] | None = None
    ) -> list[list[Any]]:
        """Run a read-only query and return its rows (list of lists)."""

    def list_relations(self) -> set[str]:
        """Return the set of relation names that exist (snake-cased)."""


class CozoBackend:
    """The real backend: an embedded Cozo store via ``pycozo``.

    This is the ONLY class that imports pycozo or emits CozoScript text
    (REQ-KG-002b). The CozoScript emission previously living on ``CozoStore``
    (``:create`` / ``:put`` / ``::relations``) moved here unchanged.
    """

    def __init__(self, client: Any | None = None) -> None:
        if client is None:
            from pycozo.client import Client  # only this module imports pycozo

            client = Client("mem", "", "")
        self._client = client

    def create(
        self, relation: str, cols: list[str], col_types: Mapping[str, str]
    ) -> None:
        """Emit ``:create`` for ``relation`` with the first col as the key.

        Column base types come from ``col_types``; columns without an entry
        default to String. The key column is non-nullable; value columns are
        nullable (trailing ``?``) so a missing field stores as null.
        """
        key, *values = cols
        spec = f"{key}: {col_types.get(key, 'String')}"
        if values:
            spec += " => " + ", ".join(
                f"{c}: {col_types.get(c, 'String')}?" for c in values
            )
        self.run(f":create {relation} {{ {spec} }}")

    def put(self, relation: str, cols: list[str], rows: list[list[Any]]) -> None:
        """Emit ``:put`` for ``rows`` (a list of column-ordered rows)."""
        if not rows:
            return
        col_list = ", ".join(cols)
        script = f"?[{col_list}] <- $rows :put {relation} {{ {col_list} }}"
        self.run(script, {"rows": rows})

    def run(
        self, script: str, params: Mapping[str, Any] | None = None
    ) -> list[list[Any]]:
        """The single call into pycozo. Returns the result rows."""
        result = self._client.run(script, params or {})
        return result["rows"]

    def list_relations(self) -> set[str]:
        """Return relation names via ``::relations`` (column 0 is the name)."""
        return {row[0] for row in self.run("::relations")}


# Query shape the StubBackend understands:
#   ?[col, ...] := *relation{cols...}, <filter>?
# where <filter> is an optional single equality/comparison
#   <col> <op> <literal>     with op in == != < <= > >=
_STUB_QUERY = re.compile(
    r"""^\s*\?\[(?P<out>[^\]]+)\]\s*:=\s*
        \*(?P<rel>\w+)\s*\{(?P<bind>[^}]*)\}
        (?:\s*,\s*(?P<filter>.+?))?\s*$""",
    re.VERBOSE | re.DOTALL,
)
_STUB_FILTER = re.compile(
    r"""^\s*(?P<col>\w+)\s*(?P<op>==|!=|<=|>=|<|>)\s*(?P<lit>.+?)\s*$"""
)


class StubBackend:
    """A pure-Python in-memory backend for the contract-test query shapes.

    YAGNI: this is NOT a Datalog engine. It supports exactly what the P0/P1
    contract tests exercise -- relation creation, row upsert, and the simple
    ``?[cols] := *relation{cols...}, <equality/comparison filter>`` query with at
    most one filter clause. Any other query shape raises ``NotImplementedError``;
    grow it only when a test needs a new shape (and if matching grows complex,
    that's the signal to lean on a real backend instead).
    """

    def __init__(self) -> None:
        # relation -> ordered column names
        self._cols: dict[str, list[str]] = {}
        # relation -> {key value -> column-ordered row}; keyed by col[0] for
        # upsert semantics matching Cozo's :put.
        self._rows: dict[str, dict[Any, list[Any]]] = {}

    def create(
        self, relation: str, cols: list[str], col_types: Mapping[str, str]
    ) -> None:
        self._cols[relation] = list(cols)
        self._rows.setdefault(relation, {})

    def put(self, relation: str, cols: list[str], rows: list[list[Any]]) -> None:
        if relation not in self._cols:
            raise KeyError(f"unknown relation {relation!r}")
        store = self._rows[relation]
        for row in rows:
            store[row[0]] = list(row)  # upsert on the key column

    def list_relations(self) -> set[str]:
        return set(self._cols)

    def run(
        self, script: str, params: Mapping[str, Any] | None = None
    ) -> list[list[Any]]:
        m = _STUB_QUERY.match(script)
        if not m:
            raise NotImplementedError(
                f"StubBackend supports only simple '?[..] := *rel{{..}}, filter' "
                f"queries, not: {script!r}"
            )
        rel = m.group("rel")
        if rel not in self._cols:
            raise KeyError(f"unknown relation {rel!r}")
        bind = [c.strip() for c in m.group("bind").split(",") if c.strip()]
        out = [c.strip() for c in m.group("out").split(",") if c.strip()]
        bind_unknown = set(bind) - set(self._cols[rel])
        if bind_unknown:
            raise KeyError(f"unknown columns {bind_unknown} on {rel!r}")
        if not set(out) <= set(bind):
            raise NotImplementedError(
                f"output cols {out} must be bound by *{rel}{{{bind}}}"
            )

        pred = self._compile_filter(m.group("filter"))
        col_index = {c: i for i, c in enumerate(self._cols[rel])}
        result: list[list[Any]] = []
        for stored in self._rows[rel].values():
            env = {c: stored[col_index[c]] for c in bind}
            if pred(env):
                result.append([env[c] for c in out])
        return result

    @staticmethod
    def _compile_filter(clause: str | None):
        """Compile an optional single comparison clause into a predicate."""
        if clause is None or not clause.strip():
            return lambda env: True
        fm = _STUB_FILTER.match(clause)
        if not fm:
            raise NotImplementedError(
                f"StubBackend supports only a single comparison filter, "
                f"not: {clause!r}"
            )
        col, op, lit = fm.group("col"), fm.group("op"), fm.group("lit")
        literal = _parse_literal(lit)
        ops = {
            "==": lambda a, b: a == b,
            "!=": lambda a, b: a != b,
            "<": lambda a, b: a < b,
            "<=": lambda a, b: a <= b,
            ">": lambda a, b: a > b,
            ">=": lambda a, b: a >= b,
        }
        fn = ops[op]
        # Ordered comparisons against a null cell are an error in real Cozo
        # (raises QueryException "Evaluation of expression failed"); equality
        # against null simply does not match. Mirror both so the stub stays a
        # faithful oracle.
        is_ordered = op in ("<", "<=", ">", ">=")

        def pred(env: Mapping[str, Any]) -> bool:
            if col not in env:
                raise KeyError(f"filter column {col!r} not bound")
            value = env[col]
            if value is None:
                if is_ordered:
                    raise RuntimeError(
                        f"stub: comparison {col!r} {op} against null cell "
                        f"(Cozo would raise QueryException)"
                    )
                return False  # equality with null: no match, as Cozo would skip
            return fn(value, literal)

        return pred


def _parse_literal(text: str) -> Any:
    """Parse a CozoScript scalar literal (string / float / int / bool)."""
    text = text.strip()
    if (text.startswith('"') and text.endswith('"')) or (
        text.startswith("'") and text.endswith("'")
    ):
        return text[1:-1]
    if text in ("true", "false"):
        return text == "true"
    try:
        if any(c in text for c in ".eE"):
            return float(text)
        return int(text)
    except ValueError:
        return text


class CozoStore:
    """A schema-shaped, backend-agnostic seam over a knowledge-graph store.

    Construct via :meth:`in_memory` (real Cozo backend) or directly with a
    :class:`Backend` (e.g. :class:`StubBackend` for offline unit tests). The
    interface (``in_memory``/``load``/``query``/``relations``) is the contract
    consumed by later tasks (projector P0.6, query ports P1) and is what stays
    stable across a backend swap (REQ-KG-007).
    """

    def __init__(
        self,
        backend: Backend,
        relations: Mapping[str, list[str]] | None = None,
        types: Mapping[str, Mapping[str, str]] | None = None,
        schema_path: Path | None = None,
    ) -> None:
        # The store talks only to this backend; no pycozo type leaks here.
        self._backend = backend
        # Retain the schema path so the public EDN seam can compile EDN to
        # CozoScript internally (REQ-KG-002/007). May be None when the store is
        # built from explicit `relations` (e.g. some StubBackend unit tests).
        self._schema_path = Path(schema_path) if schema_path is not None else None
        if relations is None:
            if schema_path is None:
                raise ValueError("CozoStore needs either relations or schema_path")
            relations, parsed_types = _parse_schema(Path(schema_path))
            if types is None:
                types = parsed_types
        # snake relation name -> ordered snake column names (key first).
        self._relations: dict[str, list[str]] = dict(relations)
        # snake relation name -> {snake col -> base type}; cols not present
        # default to String. Drives create's column type spec.
        self._types: dict[str, dict[str, str]] = {
            k: dict(v) for k, v in (types or {}).items()
        }
        # REQ-KG-011: the store holds EXACTLY the declared relations. Reject any
        # pre-existing relation absent from kg-schema.edn before creating the
        # missing declared ones -- a stale/rogue relation must not survive init
        # and become a false dependency for later queries/constraints.
        existing = self._backend.list_relations()
        declared = set(self._relations)
        extra = existing - declared
        if extra:
            raise ValueError(
                f"relations absent from kg-schema.edn: {sorted(extra)}"
            )
        # Create one relation per declared entity (REQ-KG-011).
        for name, cols in self._relations.items():
            if name not in existing:
                self._backend.create(name, cols, self._types.get(name, {}))

    # -- construction ------------------------------------------------------

    @classmethod
    def in_memory(cls, schema_path: Path) -> "CozoStore":
        """Build an in-memory store (Cozo backend) with one relation per entity."""
        return cls(backend=CozoBackend(), schema_path=Path(schema_path))

    # -- public seam -------------------------------------------------------

    def load(self, relation: str, rows: Iterable[Mapping[str, Any]]) -> None:
        """Upsert ``rows`` into ``relation``.

        Dict keys may be kebab or snake; they are normalized to the snake
        columns the store created. Missing columns are filled with None.
        """
        rel = to_snake(relation)
        cols = self._relations.get(rel)
        if cols is None:
            raise KeyError(f"unknown relation {relation!r} (snake {rel!r})")
        matrix: list[list[Any]] = []
        for row in rows:
            norm = {to_snake(k): v for k, v in row.items()}
            matrix.append([norm.get(c) for c in cols])
        self._backend.put(rel, cols, matrix)

    def query_edn(self, edn_text: str) -> list[list[Any]]:
        """Run a booklogic ``defquery`` EDN against the store (REQ-KG-002/007).

        This is the public consumer seam: callers pass EDN, never CozoScript.
        The EDN is compiled to CozoScript INTERNALLY here, so the compile target
        never leaks past the store and the Cozo->Asami backend swap stays a
        one-module change. ``booklogic_kg`` is imported locally to avoid an
        import cycle and to keep its cost off code paths that never query.
        """
        if self._schema_path is None:
            raise ValueError(
                "query_edn needs a schema_path; this store was built from "
                "explicit relations without one"
            )
        from .booklogic_kg import compile_query  # local: avoid import cycle

        script = compile_query(edn_text, self._schema_path)
        return self._backend.run(script)

    def query(self, cozoscript: str) -> list[list[Any]]:
        """Run a raw CozoScript query (INTERNAL).

        This executes CozoScript directly and is the internal raw-script runner
        used by the projector, compiler-execution tests, and other in-tree code
        that legitimately works at the CozoScript layer. Consumers MUST use
        :meth:`query_edn` instead — passing CozoScript here leaks the compile
        target and breaks the backend-swap property (REQ-KG-002/007).
        """
        return self._backend.run(cozoscript)

    def relations(self) -> set[str]:
        """Return the set of relation names that exist in the store (snake-cased)."""
        return self._backend.list_relations()
