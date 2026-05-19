"""REQ-RETRIEVAL-040..045: SemanticIndex smoke + contract.

These tests gate on `sentence_transformers` being available. Without
it (e.g. CI without the optional extra), they skip cleanly. The
missing-model error path itself is exercised in
``test_semantic_index_missing_model.py``.
"""
from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("sentence_transformers")


# ---------------------------------------------------------------------
# REQ-RETRIEVAL-040: class exposes embed_claim / similar_claims / count
# REQ-RETRIEVAL-045: self-exclusion, deterministic ordering, persistence
# ---------------------------------------------------------------------


def test_class_exposes_embed_similar_count(tmp_path: Path) -> None:
    from scripts._semantic_index import SemanticIndex

    idx = SemanticIndex(cache_path=tmp_path / "idx.npz")
    assert idx.count() == 0
    idx.embed_claim(claim_id="c-1", text="hello world")
    assert idx.count() == 1
    neighbours = idx.similar_claims("c-1", k=1)
    assert neighbours[0][0] == "c-1"


def test_insert_then_top_1_is_self(tmp_path: Path) -> None:
    from scripts._semantic_index import SemanticIndex

    idx = SemanticIndex(cache_path=tmp_path / "idx.npz")
    for i in range(10):
        idx.embed_claim(claim_id=f"c-{i}", text=f"observation about disease {i}")
    neighbours = idx.similar_claims("c-3", k=3)
    assert neighbours[0][0] == "c-3"
    # Self-similarity is cosine(v, v) = 1.0; float32 rounding may put
    # the value microscopically above 1.0 (e.g. 1.0000001) — allow a
    # small slack on both sides.
    assert abs(neighbours[0][1] - 1.0) < 1e-5
    assert -1.0 <= neighbours[0][1] <= 1.0 + 1e-5


def test_similar_other_claims_excludes_self(tmp_path: Path) -> None:
    from scripts._semantic_index import SemanticIndex

    idx = SemanticIndex(cache_path=tmp_path / "idx.npz")
    for i in range(10):
        idx.embed_claim(claim_id=f"c-{i}", text=f"observation about disease {i}")
    others = idx.similar_other_claims("c-0", k=3)
    assert len(others) == 3
    assert all(cid != "c-0" for cid, _ in others)


def test_idempotent_embed(tmp_path: Path) -> None:
    from scripts._semantic_index import SemanticIndex

    idx = SemanticIndex(cache_path=tmp_path / "idx.npz")
    idx.embed_claim(claim_id="c-1", text="hello")
    idx.embed_claim(claim_id="c-1", text="hello")  # duplicate
    assert idx.count() == 1


def test_count(tmp_path: Path) -> None:
    from scripts._semantic_index import SemanticIndex

    idx = SemanticIndex(cache_path=tmp_path / "idx.npz")
    assert idx.count() == 0
    for i in range(5):
        idx.embed_claim(claim_id=f"c-{i}", text=f"text {i}")
    assert idx.count() == 5


def test_persistence_round_trip(tmp_path: Path) -> None:
    from scripts._semantic_index import SemanticIndex

    cache = tmp_path / "idx.npz"
    idx1 = SemanticIndex(cache_path=cache)
    idx1.embed_claim(claim_id="c-1", text="hello")
    idx1.embed_claim(claim_id="c-2", text="goodbye")
    idx1.save()
    assert cache.exists()

    idx2 = SemanticIndex(cache_path=cache)
    idx2.load()
    assert idx2.count() == 2
    n = idx2.similar_claims("c-1", k=1)
    assert n[0][0] == "c-1"


def test_persistence_preserves_scores_to_6dp(tmp_path: Path) -> None:
    """REQ-RETRIEVAL-045: scores stable across save/load to 6 decimal places."""
    from scripts._semantic_index import SemanticIndex

    cache = tmp_path / "idx.npz"
    idx1 = SemanticIndex(cache_path=cache)
    texts = [
        ("c-1", "disease prevalence in tropical regions"),
        ("c-2", "vaccine efficacy clinical trial outcomes"),
        ("c-3", "mortality rates rising in coastal towns"),
        ("c-4", "epidemiological survey methodology design"),
    ]
    for cid, text in texts:
        idx1.embed_claim(claim_id=cid, text=text)
    pre = idx1.similar_claims("c-1", k=4)
    idx1.save()

    idx2 = SemanticIndex(cache_path=cache)
    idx2.load()
    post = idx2.similar_claims("c-1", k=4)
    assert len(pre) == len(post)
    for (cid_a, s_a), (cid_b, s_b) in zip(pre, post):
        assert cid_a == cid_b
        assert abs(s_a - s_b) < 1e-6


def test_deterministic_ordering_on_ties(tmp_path: Path) -> None:
    """REQ-RETRIEVAL-045: identical texts -> tie-break by claim_id ascending."""
    from scripts._semantic_index import SemanticIndex

    idx = SemanticIndex(cache_path=tmp_path / "idx.npz")
    # Two claims with identical text produce identical embeddings.
    idx.embed_claim(claim_id="c-zeta", text="exactly the same text")
    idx.embed_claim(claim_id="c-alpha", text="exactly the same text")
    idx.embed_claim(claim_id="c-mid", text="exactly the same text")
    n = idx.similar_claims("c-alpha", k=3)
    # All three have score ~1.0; tie-break by claim_id ascending.
    ids = [cid for cid, _ in n]
    assert ids == ["c-alpha", "c-mid", "c-zeta"]


# ---------------------------------------------------------------------
# REQ-RETRIEVAL-041: cache invalidation on claim-set change
# ---------------------------------------------------------------------


def test_invalidate_on_claims_sha_change(tmp_path: Path) -> None:
    from scripts._semantic_index import SemanticIndex

    idx = SemanticIndex(cache_path=tmp_path / "idx.npz")
    idx.invalidate_if_claims_changed("claims-v1-text")
    idx.embed_claim(claim_id="c-1", text="hello")
    assert idx.count() == 1
    sha_v1 = idx.claims_sha
    # Same content -> no invalidation.
    idx.invalidate_if_claims_changed("claims-v1-text")
    assert idx.count() == 1
    assert idx.claims_sha == sha_v1
    # Changed content -> embeddings dropped, sha updated.
    idx.invalidate_if_claims_changed("claims-v2-different")
    assert idx.count() == 0
    assert idx.claims_sha != sha_v1


def test_sha_persists_across_round_trip(tmp_path: Path) -> None:
    """REQ-RETRIEVAL-041: saved SHA matches loaded SHA."""
    from scripts._semantic_index import SemanticIndex

    cache = tmp_path / "idx.npz"
    idx1 = SemanticIndex(cache_path=cache)
    idx1.invalidate_if_claims_changed("sample-claims-text")
    idx1.embed_claim(claim_id="c-1", text="hello")
    idx1.save()
    sha_saved = idx1.claims_sha

    idx2 = SemanticIndex(cache_path=cache)
    idx2.load()
    assert idx2.claims_sha == sha_saved


def test_load_refuses_cross_encoder(tmp_path: Path) -> None:
    """REQ-RETRIEVAL-041: model_name mismatch -> refuse to load."""
    from scripts._semantic_index import SemanticIndex

    cache = tmp_path / "idx.npz"
    idx1 = SemanticIndex(cache_path=cache)
    idx1.embed_claim(claim_id="c-1", text="hello")
    idx1.save()

    # Construct with a different model_name; load() should leave state empty.
    idx2 = SemanticIndex(cache_path=cache, model_name="some-other/encoder")
    idx2.load()
    assert idx2.count() == 0
