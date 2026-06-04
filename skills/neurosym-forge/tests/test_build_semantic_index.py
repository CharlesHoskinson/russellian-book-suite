"""REQ-RETRIEVAL-043: build_semantic_index reads claims.edn and writes .npz.

These tests gate on `sentence_transformers` being available. Without
it, they skip; the script's graceful-degrade path (silently exit 0 on
missing dep) is exercised in ``test_build_semantic_index_no_model.py``.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.windows_canary

import os
from pathlib import Path

import pytest

pytest.importorskip("sentence_transformers")
import numpy as np  # noqa: E402


_SAMPLE_CLAIMS_EDN = """{:version 1
 :atoms [
  {:kind :expression :id "c-01" :predicate :rate :subject :A :value 9 :doc "rate of disease in town A"}
  {:kind :expression :id "c-02" :predicate :rate :subject :B :value 4 :doc "rate of disease in town B"}
  {:kind :expression :id "c-03" :predicate :rate :subject :C :value 7 :doc "rate of disease in town C"}
  {:kind :symbol :id "ctx-01" :name :CONTEXT :context true}
 ]}
"""


def _write_claims(work: Path, edn: str = _SAMPLE_CLAIMS_EDN) -> Path:
    work.mkdir(parents=True, exist_ok=True)
    p = work / "claims.edn"
    p.write_text(edn, encoding="utf-8")
    return p


def test_target_embeds_active_claims_edn(tmp_path: Path) -> None:
    """REQ-RETRIEVAL-043: building the index produces a .npz with the
    expected shape (one row per :doc atom, context atoms excluded).
    """
    from scripts.build_semantic_index import run

    claims = _write_claims(tmp_path / "work")
    out = tmp_path / "work" / "semantic-index.npz"
    rc = run(claims, out)
    assert rc == 0
    assert out.exists()

    z = np.load(out, allow_pickle=True)
    # 3 :expression atoms with :doc; context atom excluded.
    assert z["embeddings"].shape[0] == 3
    assert z["embeddings"].shape[1] == 384
    ids = [str(c) for c in z["claim_ids"]]
    assert sorted(ids) == ["c-01", "c-02", "c-03"]


def test_cache_hit_skips_reembed(tmp_path: Path, capsys) -> None:
    """REQ-RETRIEVAL-041: re-running with unchanged claims.edn reuses
    the existing .npz without re-embedding.
    """
    from scripts.build_semantic_index import run

    claims = _write_claims(tmp_path / "work")
    out = tmp_path / "work" / "semantic-index.npz"
    rc1 = run(claims, out)
    assert rc1 == 0
    mtime1 = out.stat().st_mtime_ns

    # Second invocation, same content -> cache hit, no re-write.
    rc2 = run(claims, out)
    assert rc2 == 0
    captured = capsys.readouterr()
    assert "cache hit" in captured.err
    # File should not have been re-written.
    assert out.stat().st_mtime_ns == mtime1


def test_cache_invalidates_on_claim_change(tmp_path: Path) -> None:
    """REQ-RETRIEVAL-041: changing claims.edn re-embeds and the stored
    SHA is updated.
    """
    from scripts._semantic_index import SemanticIndex
    from scripts.build_semantic_index import run

    claims = _write_claims(tmp_path / "work")
    out = tmp_path / "work" / "semantic-index.npz"
    run(claims, out)
    idx1 = SemanticIndex(cache_path=out)
    idx1.load()
    sha1 = idx1.claims_sha

    # Mutate the claims.edn (add a new atom).
    modified = _SAMPLE_CLAIMS_EDN.replace(
        "{:kind :symbol :id \"ctx-01\"",
        "{:kind :expression :id \"c-04\" :predicate :rate :subject :D :value 2 :doc \"rate of disease in town D\"} {:kind :symbol :id \"ctx-01\"",
    )
    _write_claims(tmp_path / "work", modified)
    run(claims, out)
    idx2 = SemanticIndex(cache_path=out)
    idx2.load()
    assert idx2.claims_sha != sha1
    assert idx2.count() == 4


def test_missing_claims_edn_exits_zero(tmp_path: Path) -> None:
    """Graceful degrade: no claims.edn -> no .npz, exit 0."""
    from scripts.build_semantic_index import run

    out = tmp_path / "work" / "semantic-index.npz"
    rc = run(tmp_path / "work" / "missing.edn", out)
    assert rc == 0
    assert not out.exists()


def test_disable_env_var_skips(tmp_path: Path, monkeypatch) -> None:
    """REQ-RETRIEVAL-042: NEUROSYM_EMBED_DISABLE=1 skips the embed."""
    from scripts.build_semantic_index import run

    claims = _write_claims(tmp_path / "work")
    out = tmp_path / "work" / "semantic-index.npz"
    monkeypatch.setenv("NEUROSYM_EMBED_DISABLE", "1")
    rc = run(claims, out)
    assert rc == 0
    assert not out.exists()
