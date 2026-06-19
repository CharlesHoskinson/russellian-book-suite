"""Pure-Python reference evaluator for a declared defquery subset."""
from __future__ import annotations

import operator
from collections.abc import Mapping, Sequence
from typing import Any

import edn_format


DECLARED_SUBSET = {
    "name": "defquery-basic-v1",
    "forms": ["defquery"],
    "where": "entity/attribute triples with joins by shared variables",
    "filter": "ordered comparisons over bound variables and literals",
    "not": "safe negation groups whose variables are bound by the positive body",
    "unsupported": ["aggregation", "defconstraint", "defrules", "recursion"],
}

_FIND = edn_format.Keyword("find")
_WHERE = edn_format.Keyword("where")
_FILTER = edn_format.Keyword("filter")
_NOT = edn_format.Keyword("not")
_COMPARATORS = {
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
    "!=": operator.ne,
    "==": operator.eq,
}


class ReferenceSubsetError(Exception):
    """Raised when a query is outside the declared reference subset."""


def declared_subset() -> dict[str, Any]:
    """Return the rule surface this evaluator claims to cover."""
    return {
        "name": DECLARED_SUBSET["name"],
        "forms": list(DECLARED_SUBSET["forms"]),
        "where": DECLARED_SUBSET["where"],
        "filter": DECLARED_SUBSET["filter"],
        "not": DECLARED_SUBSET["not"],
        "unsupported": list(DECLARED_SUBSET["unsupported"]),
    }


def _to_snake(name: str) -> str:
    return name.replace("-", "_")


def _is_seq(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes))


def _is_var(value: Any) -> bool:
    return isinstance(value, edn_format.Symbol)


def _var_name(value: Any) -> str:
    name = value.name if hasattr(value, "name") else str(value)
    if name.startswith("?"):
        name = name[1:]
    return _to_snake(name)


def _entity_key(value: Any) -> str:
    return f"@{_var_name(value)}"


def _keyword_name(value: Any) -> str:
    return value.name if hasattr(value, "name") else str(value)


def _split_attr(attr_kw: edn_format.Keyword) -> tuple[str, str]:
    namespace = getattr(attr_kw, "namespace", None)
    if namespace is None:
        raise ReferenceSubsetError(
            f"attribute {attr_kw!r} must be namespaced as :entity/attr"
        )
    return _to_snake(namespace), _to_snake(attr_kw.name.split("/", 1)[1])


def _parse_sections(edn_text: str) -> dict[Any, Any]:
    form = edn_format.loads(edn_text)
    if not _is_seq(form) or not form:
        raise ReferenceSubsetError("query must be a (defquery ...) form")
    head = form[0]
    if not (hasattr(head, "name") and head.name == "defquery"):
        raise ReferenceSubsetError(f"expected defquery, got {head!r}")

    sections: dict[Any, Any] = {}
    i = 2
    while i + 1 < len(form):
        sections[form[i]] = form[i + 1]
        i += 2
    if _FIND not in sections:
        raise ReferenceSubsetError("defquery missing :find")
    if _WHERE not in sections:
        raise ReferenceSubsetError("defquery missing :where")
    for term in sections[_FIND]:
        if not _is_var(term):
            raise ReferenceSubsetError("reference subset excludes aggregations")
    return sections


def _normalize_rows(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [{_to_snake(str(key)): value for key, value in row.items()} for row in rows]


class ReferenceDatalogEvaluator:
    """Evaluate the declared EDN defquery subset without calling Cozo."""

    def __init__(self, relations: Mapping[str, Sequence[Mapping[str, Any]]]) -> None:
        self._relations = {
            _to_snake(relation): _normalize_rows(rows)
            for relation, rows in relations.items()
        }

    @staticmethod
    def declared_subset() -> dict[str, Any]:
        return declared_subset()

    def evaluate(self, edn_text: str) -> list[list[Any]]:
        sections = _parse_sections(edn_text)
        envs: list[dict[str, Any]] = [{}]
        for triple in sections[_WHERE]:
            envs = self._apply_triple(envs, triple)
        if _FILTER in sections:
            envs = self._apply_filters(envs, sections[_FILTER])
        if _NOT in sections:
            envs = self._apply_negations(envs, sections[_NOT])

        rows: list[list[Any]] = []
        for env in envs:
            row = []
            for term in sections[_FIND]:
                name = _var_name(term)
                if name not in env:
                    raise ReferenceSubsetError(
                        f":find variable '?{name}' is not bound"
                    )
                row.append(env[name])
            rows.append(row)
        return rows

    def _apply_triple(
        self,
        envs: list[dict[str, Any]],
        triple: Any,
    ) -> list[dict[str, Any]]:
        if not _is_seq(triple) or len(triple) != 3:
            raise ReferenceSubsetError(
                f"malformed triple {triple!r}: expected [?e :entity/attr value]"
            )
        evar, attr_kw, value = triple
        relation, column = _split_attr(attr_kw)
        rows = self._relations.get(relation, [])
        out: list[dict[str, Any]] = []
        for env in envs:
            for index, row in enumerate(rows):
                next_env = self._match_row(env, evar, relation, index, row)
                if next_env is None:
                    continue
                next_env = self._match_value(next_env, row.get(column), value)
                if next_env is not None:
                    out.append(next_env)
        return out

    def _match_row(
        self,
        env: dict[str, Any],
        evar: Any,
        relation: str,
        index: int,
        row: Mapping[str, Any],
    ) -> dict[str, Any] | None:
        identity = (relation, row.get("id", index))
        key = _entity_key(evar)
        bound = env.get(key)
        if bound is not None and bound != identity:
            return None
        next_env = dict(env)
        next_env[key] = identity
        return next_env

    def _match_value(
        self,
        env: dict[str, Any],
        cell: Any,
        value: Any,
    ) -> dict[str, Any] | None:
        if _is_var(value):
            name = _var_name(value)
            if name in env:
                return env if env[name] == cell else None
            next_env = dict(env)
            next_env[name] = cell
            return next_env
        return env if cell == value else None

    def _apply_filters(
        self, envs: list[dict[str, Any]], clauses: Any
    ) -> list[dict[str, Any]]:
        out = envs
        for clause in clauses:
            if not _is_seq(clause) or len(clause) != 3:
                raise ReferenceSubsetError(
                    f"malformed filter {clause!r}: expected [<op> ?var rhs]"
                )
            op, lhs, rhs = clause
            op_name = _keyword_name(op)
            if op_name not in _COMPARATORS:
                raise ReferenceSubsetError(f"unsupported comparator {op_name!r}")
            lhs_name = _var_name(lhs)
            comparator = _COMPARATORS[op_name]
            filtered: list[dict[str, Any]] = []
            for env in out:
                if lhs_name not in env or env[lhs_name] is None:
                    continue
                left = env[lhs_name]
                if _is_var(rhs):
                    rhs_name = _var_name(rhs)
                    if rhs_name not in env or env[rhs_name] is None:
                        continue
                    right = env[rhs_name]
                else:
                    right = rhs
                if comparator(left, right):
                    filtered.append(env)
            out = filtered
        return out

    def _apply_negations(
        self, envs: list[dict[str, Any]], clauses: Any
    ) -> list[dict[str, Any]]:
        groups = _group_by_entity_var(clauses)
        out: list[dict[str, Any]] = []
        for env in envs:
            if not any(self._group_matches(env, group) for group in groups):
                out.append(env)
        return out

    def _group_matches(self, env: dict[str, Any], group: list[Any]) -> bool:
        envs = [dict(env)]
        for triple in group:
            envs = self._apply_triple(envs, triple)
            if not envs:
                return False
        return bool(envs)


def _group_by_entity_var(clauses: Any) -> list[list[Any]]:
    groups: dict[str, list[Any]] = {}
    order: list[str] = []
    for triple in clauses:
        if not _is_seq(triple) or len(triple) != 3:
            raise ReferenceSubsetError(
                f"malformed negation triple {triple!r}: expected arity 3"
            )
        key = _var_name(triple[0])
        if key not in groups:
            order.append(key)
            groups[key] = []
        groups[key].append(triple)
    return [groups[key] for key in order]
