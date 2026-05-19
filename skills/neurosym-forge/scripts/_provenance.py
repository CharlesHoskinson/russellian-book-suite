"""PROV-O provenance sidecar for induced BookLogic theories.

REQ-PROV-040..047 — the sidecar `rules/booklogic/induced-theory.prov.edn`
companions `induced-theory.edn` and carries the audit trail for every
induced rule: derived-from atoms, source documents, contradicting atoms
tolerated as advisory, LLM lineage, solver-run outcomes, entrenchment,
status, repair-call count, and cost.

Design constraints
------------------
* The `:prov/*` key set is **closed**. Insertion-time validation rejects
  unknown keys, out-of-enum `:prov/status`, out-of-range
  `:prov/llm-repair-calls`, and out-of-range `:prov/entrenchment`.
* Round-trip must be **byte-stable** (REQ-PROV-045): write -> read ->
  write produces identical bytes. The writer sorts rule ids and emits
  every prov-dict's keys in a canonical schema-defined order; nested
  list-valued fields preserve insertion order; floats are emitted via
  the EDN writer's `_emit_float` (no scientific notation per
  REQ-EDN-050).
* Graceful-degrade on load (REQ-PROV-044): missing or malformed sidecar
  raises `ProvenanceSidecarError` carrying the file path; the caller
  (`forge theory`) catches via `_cli_errors.interpret` and continues
  with an empty sidecar.

The sidecar is pure I/O — no LLM calls, no solver dispatch.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Iterator

from scripts._edn_reader import (
    EdnList,
    EdnReadError,
    EdnVector,
    Keyword,
    read_edn,
)
from scripts._edn_writer import write_edn

# ---------------------------------------------------------------------------
# Schema constants — the closed `:prov/*` key set
# ---------------------------------------------------------------------------

_REQUIRED_KEYS: frozenset[str] = frozenset({
    ":prov/derived-from-atoms",
    ":prov/source-documents",
    ":prov/contradiction-atoms",
    ":prov/proposed-by",
    ":prov/validated-by",
    ":prov/entrenchment",
    ":prov/status",
    ":prov/llm-repair-calls",
    ":prov/cost-usd",
})

_OPTIONAL_KEYS: frozenset[str] = frozenset({
    ":prov/semantic-neighbours",
    ":prov/induced-from-corpus",
})

_ALL_KEYS: frozenset[str] = _REQUIRED_KEYS | _OPTIONAL_KEYS

# Canonical emit order for a prov-dict — required keys first (in schema
# order), then optional keys (in schema order). This is the order the
# writer emits keys for byte stability; readers do not depend on it.
_CANONICAL_KEY_ORDER: tuple[str, ...] = (
    ":prov/derived-from-atoms",
    ":prov/source-documents",
    ":prov/contradiction-atoms",
    ":prov/proposed-by",
    ":prov/validated-by",
    ":prov/entrenchment",
    ":prov/status",
    ":prov/llm-repair-calls",
    ":prov/cost-usd",
    ":prov/semantic-neighbours",
    ":prov/induced-from-corpus",
)

_VALID_STATUSES: frozenset[str] = frozenset({
    ":active",
    ":tentative",
    ":quarantined",
})

_REPAIR_CALLS_MAX: int = 3
_SEMANTIC_NEIGHBOURS_MAX: int = 3


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class ProvenanceSidecarError(ValueError):
    """Raised when a sidecar file is missing, unreadable, or malformed.

    Carries the file path so `_cli_errors.interpret` can surface a
    hand-readable user message naming the file (REQ-PROV-044).
    """

    def __init__(self, path: Path | str, reason: str) -> None:
        self.path = Path(path)
        self.reason = reason
        super().__init__(f"provenance sidecar {self.path}: {reason}")


# ---------------------------------------------------------------------------
# ProvenanceSidecar
# ---------------------------------------------------------------------------

class ProvenanceSidecar:
    """Read / write / mutate `induced-theory.prov.edn`.

    Methods
    -------
    add_rule_provenance(rule_id, prov)
        Insert (or overwrite) a rule's provenance entry. Validates the
        prov dict against the closed `:prov/*` schema.
    lookup(rule_id) -> dict | None
        Fetch a rule's provenance dict, or None if absent.
    iter_rules() -> Iterator[(rule_id, prov_dict)]
        Iterate rules in deterministic sorted order.
    remove_rule(rule_id)
        Drop a rule. Idempotent on unknown ids.
    save(path)
        Serialize to disk as deterministic EDN (sorted rule ids,
        canonical key order within each prov dict, no scientific-notation
        floats).
    load(path) -> ProvenanceSidecar
        Parse from disk. Raises `ProvenanceSidecarError` on missing /
        malformed input.
    """

    def __init__(self, version: int = 1) -> None:
        self.version: int = version
        # Internal storage: rule-id -> prov-dict (strings keyed by ":prov/*").
        # Insertion order is irrelevant — save() sorts the ids on emit.
        self._rules: dict[str, dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def add_rule_provenance(self, rule_id: str, prov: dict) -> None:
        """Insert or overwrite a rule's provenance entry.

        Validates the prov dict against the closed `:prov/*` schema:
        required keys present, no unknown keys, status in enum, repair
        calls in [0, 3], entrenchment in [0.0, 1.0], cost-usd >= 0.0,
        semantic-neighbours capped at 3 entries.

        Raises
        ------
        ValueError
            On any schema violation (per REQ-PROV-041).
        """
        if not isinstance(prov, dict):
            raise ValueError(
                f"provenance entry for {rule_id!r} must be a dict, "
                f"got {type(prov).__name__}"
            )

        _validate_prov_dict(rule_id, prov)
        # Store a shallow copy so callers can't mutate our state by mutating
        # the dict they passed in. Sub-structures (lists, nested dicts) are
        # not deep-copied; this matches the existing _io.py convention and
        # is sufficient because round-trip via EDN re-materialises them.
        self._rules[rule_id] = dict(prov)

    def remove_rule(self, rule_id: str) -> None:
        """Drop a rule. No-op when the id is unknown."""
        self._rules.pop(rule_id, None)

    # ------------------------------------------------------------------
    # Inspection
    # ------------------------------------------------------------------

    def lookup(self, rule_id: str) -> dict | None:
        """Return the provenance dict for a rule, or None if absent."""
        entry = self._rules.get(rule_id)
        if entry is None:
            return None
        # Return a copy so caller mutation doesn't leak in.
        return dict(entry)

    def iter_rules(self) -> Iterator[tuple[str, dict]]:
        """Iterate `(rule_id, prov_dict)` in sorted-id order."""
        for rid in sorted(self._rules.keys()):
            yield rid, dict(self._rules[rid])

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, path: Path) -> None:
        """Write the sidecar to `path` as deterministic EDN.

        Emit discipline:
            * top-level map: `{:version <int> :rules {<rid> <prov> ...}}`
              with `:version` emitted before `:rules`.
            * inner rule map: rule-ids sorted lexicographically.
            * inner prov dict: keys in the schema-defined canonical
              order (`_CANONICAL_KEY_ORDER`), with optional keys
              included only when present.
            * list-valued fields: insertion order preserved.
            * floats: routed through the EDN writer's fixed-point
              emitter (no scientific notation).
        """
        path = Path(path)
        text = self._to_edn_text()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n", encoding="utf-8", newline="\n")

    @classmethod
    def load(cls, path: Path | str) -> "ProvenanceSidecar":
        """Read a sidecar from `path`.

        Raises
        ------
        ProvenanceSidecarError
            On missing file, unreadable EDN, missing `:version`, or
            missing `:rules` (REQ-PROV-044).
        """
        path = Path(path)
        try:
            text = path.read_text(encoding="utf-8")
        except FileNotFoundError as e:
            raise ProvenanceSidecarError(path, f"file not found: {e}") from e
        except OSError as e:
            raise ProvenanceSidecarError(path, f"unreadable: {e}") from e

        try:
            parsed = read_edn(text)
        except EdnReadError as e:
            raise ProvenanceSidecarError(path, f"malformed EDN: {e}") from e

        if not isinstance(parsed, dict):
            raise ProvenanceSidecarError(
                path, f"top-level form is not a map: got {type(parsed).__name__}"
            )

        version = parsed.get(Keyword("version"))
        if version is None:
            raise ProvenanceSidecarError(path, "missing :version key")
        if not isinstance(version, int):
            raise ProvenanceSidecarError(
                path, f":version must be int, got {type(version).__name__}"
            )

        rules = parsed.get(Keyword("rules"))
        if rules is None:
            raise ProvenanceSidecarError(path, "missing :rules key")
        if not isinstance(rules, dict):
            raise ProvenanceSidecarError(
                path, f":rules must be a map, got {type(rules).__name__}"
            )

        sidecar = cls(version=version)
        for rid_form, prov_form in rules.items():
            rid = _keyword_or_str_to_str(rid_form)
            prov_py = _edn_value_to_py(prov_form)
            if not isinstance(prov_py, dict):
                raise ProvenanceSidecarError(
                    path,
                    f"rule {rid!r} provenance is not a map: got {type(prov_py).__name__}",
                )
            # We stored as python dict with `:prov/*` string keys. Skip
            # validation on load so that a hand-edited file with legacy
            # extra keys can still load — but the test contract calls
            # validate on save via add_rule_provenance, so we round-trip
            # through that to keep the closed-schema invariant.
            try:
                sidecar.add_rule_provenance(rid, prov_py)
            except ValueError as e:
                raise ProvenanceSidecarError(
                    path, f"rule {rid!r} fails schema validation: {e}"
                ) from e
        return sidecar

    # ------------------------------------------------------------------
    # Internal — EDN emission
    # ------------------------------------------------------------------

    def _to_edn_text(self) -> str:
        """Render the sidecar to deterministic compact EDN.

        We hand-build the top-level emit so that we can guarantee
        `:version` before `:rules`, sorted rule ids, and canonical prov
        key order — all of which the generic `write_edn` cannot
        guarantee on its own (it preserves insertion order, but our
        invariant must hold across re-builds with different insertion
        orders).
        """
        rule_parts: list[str] = []
        for rid in sorted(self._rules.keys()):
            prov = self._rules[rid]
            rid_emit = _emit_rule_id(rid)
            prov_emit = _emit_prov_dict(prov)
            rule_parts.append(f"{rid_emit} {prov_emit}")
        rules_emit = "{" + " ".join(rule_parts) + "}"
        return "{:version " + str(self.version) + " :rules " + rules_emit + "}"


# ---------------------------------------------------------------------------
# Helpers — validation
# ---------------------------------------------------------------------------

def _validate_prov_dict(rule_id: str, prov: dict) -> None:
    """Validate a prov dict against the closed `:prov/*` schema.

    Raises ValueError on any schema violation.
    """
    keys = set(prov.keys())

    missing = _REQUIRED_KEYS - keys
    if missing:
        # Pick a representative missing key for the message so the regex
        # match in tests like `match="entrenchment"` works on any deletion.
        names = ", ".join(sorted(missing))
        raise ValueError(
            f"rule {rule_id!r} missing required prov keys: {names}"
        )

    unknown = keys - _ALL_KEYS
    if unknown:
        names = ", ".join(sorted(unknown))
        raise ValueError(
            f"rule {rule_id!r} has unknown prov key(s) outside the closed schema: {names}"
        )

    # `:prov/status` enum
    status = prov[":prov/status"]
    if not isinstance(status, str) or status not in _VALID_STATUSES:
        raise ValueError(
            f"rule {rule_id!r} :prov/status must be one of "
            f"{sorted(_VALID_STATUSES)!r}, got {status!r}"
        )

    # `:prov/llm-repair-calls` in [0, 3]
    repair = prov[":prov/llm-repair-calls"]
    if not isinstance(repair, int) or isinstance(repair, bool):
        raise ValueError(
            f"rule {rule_id!r} :prov/llm-repair-calls must be an int, got {repair!r}"
        )
    if repair < 0 or repair > _REPAIR_CALLS_MAX:
        raise ValueError(
            f"rule {rule_id!r} :prov/llm-repair-calls={repair} outside [0, "
            f"{_REPAIR_CALLS_MAX}]"
        )

    # `:prov/entrenchment` in [0.0, 1.0]
    entr = prov[":prov/entrenchment"]
    if isinstance(entr, bool) or not isinstance(entr, (int, float)):
        raise ValueError(
            f"rule {rule_id!r} :prov/entrenchment must be a number, got {entr!r}"
        )
    if entr < 0.0 or entr > 1.0:
        raise ValueError(
            f"rule {rule_id!r} :prov/entrenchment={entr} outside [0.0, 1.0]"
        )

    # `:prov/cost-usd` >= 0.0
    cost = prov[":prov/cost-usd"]
    if isinstance(cost, bool) or not isinstance(cost, (int, float)):
        raise ValueError(
            f"rule {rule_id!r} :prov/cost-usd must be a number, got {cost!r}"
        )
    if cost < 0.0:
        raise ValueError(
            f"rule {rule_id!r} :prov/cost-usd={cost} must be >= 0.0"
        )

    # list-valued required fields
    for list_key in (":prov/derived-from-atoms",
                     ":prov/source-documents",
                     ":prov/contradiction-atoms"):
        v = prov[list_key]
        if not isinstance(v, list):
            raise ValueError(
                f"rule {rule_id!r} {list_key} must be a list, got "
                f"{type(v).__name__}"
            )

    # `:prov/proposed-by` shape
    proposed = prov[":prov/proposed-by"]
    if not isinstance(proposed, dict):
        raise ValueError(
            f"rule {rule_id!r} :prov/proposed-by must be a map, got "
            f"{type(proposed).__name__}"
        )

    # `:prov/validated-by` shape
    validated = prov[":prov/validated-by"]
    if not isinstance(validated, list):
        raise ValueError(
            f"rule {rule_id!r} :prov/validated-by must be a list of maps, got "
            f"{type(validated).__name__}"
        )
    for i, run in enumerate(validated):
        if not isinstance(run, dict):
            raise ValueError(
                f"rule {rule_id!r} :prov/validated-by[{i}] must be a map, got "
                f"{type(run).__name__}"
            )

    # Optional fields
    if ":prov/semantic-neighbours" in prov:
        neighbours = prov[":prov/semantic-neighbours"]
        if not isinstance(neighbours, list):
            raise ValueError(
                f"rule {rule_id!r} :prov/semantic-neighbours must be a list, "
                f"got {type(neighbours).__name__}"
            )
        if len(neighbours) > _SEMANTIC_NEIGHBOURS_MAX:
            raise ValueError(
                f"rule {rule_id!r} :prov/semantic-neighbours has "
                f"{len(neighbours)} entries; max is {_SEMANTIC_NEIGHBOURS_MAX}"
            )

    if ":prov/induced-from-corpus" in prov:
        corpus = prov[":prov/induced-from-corpus"]
        if not isinstance(corpus, str):
            raise ValueError(
                f"rule {rule_id!r} :prov/induced-from-corpus must be a string, "
                f"got {type(corpus).__name__}"
            )


# ---------------------------------------------------------------------------
# Helpers — EDN load (read side)
# ---------------------------------------------------------------------------

def _keyword_or_str_to_str(form: Any) -> str:
    """Coerce a Keyword or str (rule id) to its colon-prefixed string form."""
    if isinstance(form, Keyword):
        return str(form)  # already produces ":ns/name"
    if isinstance(form, str):
        return form
    raise ProvenanceSidecarError(
        Path("<unknown>"),
        f"rule id must be Keyword or str, got {type(form).__name__}",
    )


def _edn_value_to_py(value: Any) -> Any:
    """Recursively normalise an EDN-read value to plain Python types.

    Keywords are emitted as their colon-prefixed string form so callers
    can use `prov[":prov/status"]` directly. EdnList/EdnVector both
    become plain lists.
    """
    if isinstance(value, Keyword):
        return str(value)
    if isinstance(value, dict):
        return {_keyword_or_str_to_str(k): _edn_value_to_py(v)
                for k, v in value.items()}
    if isinstance(value, (EdnList, EdnVector, list)):
        return [_edn_value_to_py(v) for v in value]
    return value


# ---------------------------------------------------------------------------
# Helpers — EDN emit (write side)
# ---------------------------------------------------------------------------

def _emit_rule_id(rid: str) -> str:
    """Emit a rule id as an EDN keyword (e.g. `:induced/r1`).

    Rule ids in our schema always start with `:` (they're keywords).
    Strip the leading `:` and let `write_edn(Keyword(...))` produce the
    canonical form — this guarantees the same byte sequence regardless
    of how the rid was originally produced.
    """
    if rid.startswith(":"):
        body = rid[1:]
        if "/" in body:
            ns, _, name = body.partition("/")
            return write_edn(Keyword(name, namespace=ns))
        return write_edn(Keyword(body))
    # Fallback: emit as a string. This path is only hit if a caller
    # supplied a non-keyword rule id, which is unusual but tolerated.
    return write_edn(rid)


def _emit_prov_dict(prov: dict) -> str:
    """Emit one prov dict in canonical schema order.

    Required keys appear in `_CANONICAL_KEY_ORDER`; optional keys appear
    in their canonical-order slot only when present. Sub-values route
    through `_emit_prov_value` so nested maps (`:prov/proposed-by`,
    `:prov/validated-by` runs) get canonical-sorted keys too.
    """
    parts: list[str] = []
    for key in _CANONICAL_KEY_ORDER:
        if key not in prov:
            continue
        parts.append(_emit_keyword_string(key))
        parts.append(_emit_prov_value(prov[key]))
    return "{" + " ".join(parts) + "}"


def _emit_keyword_string(s: str) -> str:
    """Emit a ':ns/name' or ':name' string as a real EDN keyword.

    Round-trip discipline: a string key stored as `:prov/status` must
    serialise as the keyword `:prov/status`, not the EDN string
    `":prov/status"`. The reader normalises both back to the same
    Python string on load, but for byte stability we must always emit
    the keyword form.
    """
    if not s.startswith(":"):
        return write_edn(s)
    body = s[1:]
    if "/" in body:
        ns, _, name = body.partition("/")
        return write_edn(Keyword(name, namespace=ns))
    return write_edn(Keyword(body))


def _emit_prov_value(v: Any) -> str:
    """Recursively emit a prov-dict value as EDN.

    String values that look like keywords (start with `:`) become real
    EDN keywords. Nested dicts emit with sorted keys for byte stability.
    Lists emit in insertion order. Floats route through the EDN writer's
    fixed-point emitter (no scientific notation per REQ-EDN-050).
    """
    if isinstance(v, dict):
        # Sort nested dict keys for byte stability.
        parts: list[str] = []
        for k in sorted(v.keys()):
            parts.append(_emit_prov_value(k) if not isinstance(k, str)
                         else _emit_keyword_string(k))
            parts.append(_emit_prov_value(v[k]))
        return "{" + " ".join(parts) + "}"
    if isinstance(v, list):
        # Vectors `[...]`. Insertion order preserved.
        return "[" + " ".join(_emit_prov_value(x) for x in v) + "]"
    if isinstance(v, str):
        # `:foo` or `:foo/bar` -> keyword; else plain string.
        if v.startswith(":") and len(v) > 1:
            return _emit_keyword_string(v)
        return write_edn(v)
    # bool, int, float, None all route through write_edn cleanly.
    return write_edn(v)
