"""REQ-RETRIEVAL-042: build_semantic_index graceful-degrades without
the encoder package.

This test runs even when sentence_transformers IS installed, by
forcing the import to fail. It verifies the script exits 0 and emits
a clear warning instead of crashing.
"""
from __future__ import annotations

import builtins
from pathlib import Path

import pytest

_SAMPLE_CLAIMS_EDN = """{:version 1
 :atoms [
  {:kind :expression :id "c-01" :predicate :rate :subject :A :value 9 :doc "rate in A"}
 ]}
"""


def test_missing_model_graceful_degrade(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    from scripts.build_semantic_index import run

    work = tmp_path / "work"
    work.mkdir()
    (work / "claims.edn").write_text(_SAMPLE_CLAIMS_EDN, encoding="utf-8")

    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "sentence_transformers" or name.startswith(
            "sentence_transformers."
        ):
            raise ImportError("no module named 'sentence_transformers'")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    out = work / "semantic-index.npz"
    rc = run(work / "claims.edn", out)
    # Graceful degrade: exit 0 even though encoder is unavailable.
    assert rc == 0
    captured = capsys.readouterr()
    assert "embedding unavailable" in captured.err
    assert "continuing without semantic index" in captured.err
