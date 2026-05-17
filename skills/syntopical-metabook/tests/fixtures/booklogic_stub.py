#!/usr/bin/env python3
"""
Booklogic dev stub. JSON-only. Emits empty results for disputed-questions
and reconcile-concepts; always-reachable verdicts for reachable-from-thesis.
Used by tests until the real CLJS booklogic CLI lands.
"""
from __future__ import annotations
import argparse
import json
import sys
from datetime import datetime, timezone

STUB_VERSION = "0.0.0-stub"
API_VERSION = [0, 1]

def _provenance() -> dict:
    return {
        ":booklogic-version": f'"{STUB_VERSION}"',
        ":ruleset-checksum": '"stub-no-rules"',
        ":produced-at": f'"{datetime.now(timezone.utc).isoformat()}"',
    }

def _validate_input(payload: dict, expected_kind: str) -> None:
    """Minimal schema check: require :kind matches and :api-version present.
    Booklogic-side schema-violation envelope per IF-BL-9 / spec §11.4.3.
    """
    if not isinstance(payload, dict):
        raise SchemaViolation("input must be a JSON object", path=[])
    if payload.get(":kind") != expected_kind:
        raise SchemaViolation(
            f"expected :kind {expected_kind}, got {payload.get(':kind')!r}", path=[":kind"]
        )
    if ":api-version" not in payload:
        raise SchemaViolation("missing :api-version", path=[":api-version"])

class SchemaViolation(Exception):
    def __init__(self, message: str, path: list):
        super().__init__(message)
        self.message = message
        self.path = path

def disputed_questions(payload: dict) -> list:
    _validate_input(payload, ":input/disputed-questions")
    return []

def reconcile_concepts(payload: dict) -> list:
    _validate_input(payload, ":input/reconcile-concepts")
    return []

def reachable_from_thesis(payload: dict) -> dict:
    _validate_input(payload, ":input/reachable-from-thesis")
    candidate = payload.get(":candidate", {})
    cand_id = candidate.get(":id", '""')
    return {
        ":kind": ":verdict",
        ":candidate-id": cand_id,
        ":reachable": True,
        ":rule-trace": [],
        ":branch-witness": None,
        **_provenance(),
    }

def version(_payload: dict) -> dict:
    return {
        ":kind": ":version",
        ":booklogic-version": f'"{STUB_VERSION}"',
        ":api-version": API_VERSION,
        ":ruleset-checksum": '"stub-no-rules"',
    }

HANDLERS = {
    "disputed-questions": disputed_questions,
    "reconcile-concepts": reconcile_concepts,
    "reachable-from-thesis": reachable_from_thesis,
    "version": version,
}

def _error_envelope(code: str, message: str, path: list) -> dict:
    return {
        ":kind": ":error",
        ":code": code,
        ":message": message,
        ":location": {":path": [str(p) for p in path]},
        ":booklogic-version": f'"{STUB_VERSION}"',
    }

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("subcommand", choices=list(HANDLERS))
    p.add_argument("--io", default="json")
    p.add_argument("--timeout-s", type=int, default=60)
    p.add_argument("--ruleset-dir", default=None)
    p.add_argument("--api-version", default="0.1")
    args = p.parse_args()

    if args.io != "json":
        print("stub does not implement EDN mode; use --io json", file=sys.stderr)
        return 1

    payload = {}
    if args.subcommand != "version":
        try:
            raw = sys.stdin.read() or "{}"
            payload = json.loads(raw)
        except json.JSONDecodeError as e:
            print(json.dumps(_error_envelope(":schema-violation", f"invalid JSON: {e}", [])),
                  file=sys.stderr)
            return 1

    try:
        out = HANDLERS[args.subcommand](payload)
    except SchemaViolation as e:
        print(json.dumps(_error_envelope(":schema-violation", e.message, e.path)),
              file=sys.stderr)
        return 1
    print(json.dumps(out))
    return 0

if __name__ == "__main__":
    sys.exit(main())
