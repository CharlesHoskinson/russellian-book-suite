"""Grounded argumentation over the Cozo knowledge graph."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .booklogic_kg import compile_argumentation_rules

ASSETS = Path(__file__).resolve().parent.parent / "assets"
KG_SCHEMA = ASSETS / "kg-schema.edn"
ARGUMENTATION_RULES = ASSETS / "kg-rules" / "argumentation-grounded.edn"

_RELATION_OUTPUTS = (
    "attacked",
    "defended",
    "undefeated-attacker",
    "grounded-accepted",
    "grounded-rejected",
    "labels",
    "warnings",
)


def _sort_dicts(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: json.dumps(row, sort_keys=True, separators=(",", ":")),
    )


def _claim_count(store) -> int:
    rows = store.query("?[count(id)] := *claim{id}")
    if not rows:
        return 0
    return int(rows[0][0])


def _run_output(store, output: str, max_iterations: int) -> list[list[Any]]:
    script = compile_argumentation_rules(
        ARGUMENTATION_RULES.read_text(encoding="utf-8"),
        KG_SCHEMA,
        max_iterations=max_iterations,
        output=output,
    )
    return store.query(script)


def _rows3(rows: list[list[Any]], names: tuple[str, str, str]) -> list[dict[str, Any]]:
    return _sort_dicts([
        {names[0]: row[0], names[1]: row[1], names[2]: row[2]}
        for row in rows
    ])


def _rows1(rows: list[list[Any]], name: str) -> list[dict[str, Any]]:
    return _sort_dicts([{name: row[0]} for row in rows])


def _labels(rows: list[list[Any]]) -> list[dict[str, Any]]:
    return _sort_dicts([
        {"claim_id": row[0], "label": row[1]}
        for row in rows
    ])


def _warnings(rows: list[list[Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for warning_type, claim_id, related_id, kind, detail in rows:
        warning: dict[str, Any] = {
            "type": warning_type,
            "claim_id": claim_id,
        }
        if warning_type == "contested-load-bearing-with-undefended-attack":
            warning["attacker_id"] = related_id
            warning["justification"] = {
                "kind": kind,
                "defeaters": [detail],
            }
        elif warning_type == "axiom-only-support":
            warning["support_id"] = related_id
            warning["justification"] = {
                "kind": kind,
                "supports": [detail],
            }
        elif warning_type == "unsupported-load-bearing":
            warning["justification"] = {
                "kind": kind,
                "note": detail,
            }
        else:
            warning["related_id"] = related_id
            warning["justification"] = {"kind": kind, "detail": detail}
        out.append(warning)
    return _sort_dicts(out)


def run_argumentation(store) -> dict[str, Any]:
    """Run the grounded argumentation pass without mutating graph inputs."""
    max_iterations = _claim_count(store)
    raw = {
        output: _run_output(store, output, max_iterations)
        for output in _RELATION_OUTPUTS
    }
    return {
        "engine": "cozo-edn",
        "rules": str(ARGUMENTATION_RULES),
        "derived": {
            "attacked": _rows3(
                raw["attacked"],
                ("claim_id", "attacker_id", "attacker_type"),
            ),
            "defended": _rows3(
                raw["defended"],
                ("claim_id", "attacker_id", "defender_id"),
            ),
            "undefeated-attacker": _rows3(
                raw["undefeated-attacker"],
                ("claim_id", "attacker_id", "attacker_type"),
            ),
            "grounded-accepted": _rows1(raw["grounded-accepted"], "claim_id"),
            "grounded-rejected": _rows1(raw["grounded-rejected"], "claim_id"),
        },
        "labels": _labels(raw["labels"]),
        "warnings": _warnings(raw["warnings"]),
    }


def canonical_argumentation_result(result: dict[str, Any]) -> dict[str, Any]:
    """Canonicalize nested rows for result-set equality assertions."""
    if isinstance(result, dict):
        return {
            key: canonical_argumentation_result(result[key])
            for key in sorted(result)
        }
    if isinstance(result, list):
        return sorted(
            (canonical_argumentation_result(item) for item in result),
            key=lambda item: json.dumps(item, sort_keys=True, separators=(",", ":")),
        )
    return result
