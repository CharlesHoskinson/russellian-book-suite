"""REQ-RETRIEVAL-042: missing-model error names remediation.

This test runs even when ``sentence_transformers`` is installed: it
simulates the ImportError by injecting a sentinel into ``sys.modules``
that raises on attribute access. The point is to assert the error
message tells the user the install command.
"""
from __future__ import annotations

import builtins
from pathlib import Path

import pytest


def test_missing_sentence_transformers_raises_clear_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts._semantic_index import (
        EmbeddingUnavailableError,
        SemanticIndex,
    )

    # Force the import of sentence_transformers to fail.
    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "sentence_transformers" or name.startswith(
            "sentence_transformers."
        ):
            raise ImportError("no module named 'sentence_transformers'")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    idx = SemanticIndex(cache_path=tmp_path / "idx.npz")
    with pytest.raises(EmbeddingUnavailableError) as excinfo:
        idx.embed_claim(claim_id="c-1", text="hello")
    msg = str(excinfo.value)
    # Remediation must name the install command (REQ-RETRIEVAL-042).
    assert "pip install sentence-transformers" in msg
    # Mention the opt-out env var so authors can degrade gracefully.
    assert "NEUROSYM_EMBED_DISABLE" in msg
