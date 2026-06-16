"""cozo_store — the single Python<->store seam over an embedded Cozo store.

REQ-KG-002: the knowledge graph is exposed through ONE Python seam module
(`cozo_store`) backed by an embedded Cozo store via `pycozo`, presenting
``query(edn) -> rows`` and ``load(relation, rows)``.

REQ-KG-002b: THIS MODULE IS THE ONLY PLACE ALLOWED TO IMPORT ``pycozo`` or to
emit CozoScript text. Everything else routes through :class:`CozoStore` so the
Cozo->Asami swap (REQ-KG-007) stays a one-module change. A later task (P0.4)
extracts a Backend protocol from this class; pycozo usage is therefore kept
behind small private methods (``_create``/``_put``/``_run``).

REQ-KG-011: :meth:`CozoStore.in_memory` creates exactly one Cozo relation per
entity declared in ``assets/kg-schema.edn`` and nothing else.

Identifier translation: ``kg-schema.edn`` uses kebab-case keywords
(``:canonical-text``, ``code-node``). CozoScript identifiers must match
``[a-zA-Z_][a-zA-Z0-9_]*`` -- hyphens are illegal -- so every relation/column
name is snake-cased on the way into Cozo. The EDN contract stays kebab; the
Cozo layer is snake. :func:`to_snake` is the one translation helper.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Mapping

import edn_format

__all__ = ["CozoStore", "to_snake"]


def to_snake(name: str) -> str:
    """Translate a kebab-case schema identifier to a Cozo-legal snake_case one.

    The EDN contract is kebab-case; CozoScript identifiers must match
    ``[a-zA-Z_][a-zA-Z0-9_]*``. This is the single kebab->snake helper used for
    both relation names and column names.
    """
    return name.replace("-", "_")


def _kw_name(keyword: Any) -> str:
    """Return the bare name of an edn_format Keyword (kebab, no leading colon)."""
    return keyword.name


def _parse_schema(schema_path: Path) -> dict[str, list[str]]:
    """Parse kg-schema.edn into ``{snake_entity: [snake_col, ...]}``.

    The first attr of each entity is its identity (key) column; the rest are
    value columns. Names are snake-cased here so callers never see kebab.
    """
    doc = edn_format.loads(schema_path.read_text(encoding="utf-8"))
    entities = doc[edn_format.Keyword("entities")]
    items = entities.dict.items() if hasattr(entities, "dict") else entities.items()
    attrs_kw = edn_format.Keyword("attrs")

    out: dict[str, list[str]] = {}
    for ent_kw, body in items:
        attrs = body[attrs_kw]
        cols = [to_snake(_kw_name(a)) for a in attrs]
        out[to_snake(_kw_name(ent_kw))] = cols
    return out


class CozoStore:
    """A schema-shaped, backend-agnostic-friendly seam over an embedded Cozo store.

    Construct via :meth:`in_memory`. The interface (``in_memory``/``load``/
    ``query``/``relations``) is the contract consumed by later tasks (projector
    P0.6, query ports P1) and is what P0.4 lifts into a Backend protocol.
    """

    def __init__(self, client: Any, relations: Mapping[str, list[str]]) -> None:
        # client is a pycozo.client.Client; typed Any so no pycozo type leaks.
        self._client = client
        # snake relation name -> ordered snake column names (key first).
        self._relations: dict[str, list[str]] = dict(relations)

    # -- construction ------------------------------------------------------

    @classmethod
    def in_memory(cls, schema_path: Path) -> "CozoStore":
        """Build an in-memory store with one relation per kg-schema.edn entity."""
        from pycozo.client import Client  # only this module imports pycozo

        client = Client("mem", "", "")
        relations = _parse_schema(Path(schema_path))
        store = cls(client, relations)
        for name, cols in relations.items():
            store._create(name, cols)
        return store

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
        self._put(rel, cols, matrix)

    def query(self, cozoscript: str) -> list[list[Any]]:
        """Run a read-only CozoScript query and return its rows (list of lists)."""
        result = self._run(cozoscript)
        return result["rows"]

    def relations(self) -> set[str]:
        """Return the set of relation names that exist in the store (snake-cased)."""
        result = self._run("::relations")
        # column 0 of ::relations is the relation name.
        return {row[0] for row in result["rows"]}

    # -- private pycozo-touching helpers (P0.4 swap boundary) ---------------

    def _create(self, relation: str, cols: list[str]) -> None:
        """Emit ``:create`` for ``relation`` with the first col as the key."""
        key, *values = cols
        spec = f"{key}: String"
        if values:
            spec += " => " + ", ".join(f"{c}: String?" for c in values)
        self._run(f":create {relation} {{ {spec} }}")

    def _put(self, relation: str, cols: list[str], matrix: list[list[Any]]) -> None:
        """Emit ``:put`` for ``matrix`` (a list of column-ordered rows)."""
        if not matrix:
            return
        col_list = ", ".join(cols)
        script = f"?[{col_list}] <- $rows :put {relation} {{ {col_list} }}"
        self._run(script, {"rows": matrix})

    def _run(self, script: str, params: Mapping[str, Any] | None = None) -> dict:
        """The single call into pycozo. Returns the raw result dict."""
        return self._client.run(script, params or {})
