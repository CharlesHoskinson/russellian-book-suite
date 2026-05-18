"""Conformance suite for the booklogic JSON-wire contract.

These tests run against the dev stub by default. When the real CLJS booklogic
CLI lands, the same tests run nightly via `pytest -m live` against the real
binary by setting BOOKLOGIC_BIN.
"""
import json
import subprocess
import sys
from pathlib import Path


STUB = Path(__file__).resolve().parents[2] / "fixtures" / "booklogic_stub.py"

def _run(subcmd: str, payload: dict | None = None, io: str = "json"):
    cmd = [sys.executable, str(STUB), subcmd, "--io", io]
    return subprocess.run(
        cmd,
        input=json.dumps(payload) if payload is not None else "",
        capture_output=True,
        text=True,
        timeout=10,
    )

def test_disputed_questions_empty_input():
    r = _run("disputed-questions", {
        ":kind": ":input/disputed-questions",
        ":api-version": [0, 1],
        ":claims": [],
    })
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout) == []

def test_reconcile_concepts_empty_input():
    r = _run("reconcile-concepts", {
        ":kind": ":input/reconcile-concepts",
        ":api-version": [0, 1],
        ":concepts": [],
    })
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout) == []

def test_reachable_from_thesis_returns_verdict():
    r = _run("reachable-from-thesis", {
        ":kind": ":input/reachable-from-thesis",
        ":api-version": [0, 1],
        ":candidate": {":kind": ":candidate", ":id": '"arxiv:x"',
                       ":extracted-concepts": [], ":embedding-score": 0.8},
        ":thesis-tree": {":kind": ":thesis-tree", ":chapter-id": '"ch-01"', ":nodes": []},
    })
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out[":kind"] == ":verdict"
    assert out[":reachable"] is True
    assert out[":candidate-id"] == '"arxiv:x"'

def test_version_emits_version_atom():
    r = _run("version")
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out[":kind"] == ":version"
    assert out[":booklogic-version"] == '"0.0.0-stub"'
    assert out[":api-version"] == [0, 1]

def test_stub_rejects_edn_mode():
    r = _run("version", io="edn")
    assert r.returncode != 0
    assert "EDN" in r.stderr

def test_schema_violation_on_wrong_kind():
    r = _run("disputed-questions", {
        ":kind": ":input/reconcile-concepts",  # wrong!
        ":api-version": [0, 1],
        ":claims": [],
    })
    assert r.returncode == 1
    err = json.loads(r.stderr)
    assert err[":kind"] == ":error"
    assert err[":code"] == ":schema-violation"
