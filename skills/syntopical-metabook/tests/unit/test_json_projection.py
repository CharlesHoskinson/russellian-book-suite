"""Smoke test of the JSON projection helpers in booklogic_adapter.

The bijectivity property is partially exercisable on the Python side: given
a Python-shaped object -> JSON projection, the resulting JSON conforms to the
projection table in requirements doc §11.4.4. The full json<->edn<->json identity
(IF-BL-15) requires the real booklogic CLI to verify; this test pins what the
Python projection produces so downstream regressions are caught.
"""
from scripts.booklogic_adapter import (
    _claim_to_json, _concept_to_json, _candidate_to_json, _tree_to_json,
    _sexpr_to_json,
)

class C:
    def __init__(self, **kw):
        self.__dict__.update(kw)

def test_claim_projection_shape():
    c = C(
        id="claim-x",
        state="verified",
        tags=["finality", "longest-chain"],
        source_id="source-y",
        body=["asserts", "X", "Y"],
        locator="p.7 §3.2",
    )
    j = _claim_to_json(c)
    assert j[":kind"] == ":claim"
    assert j[":id"] == '"claim-x"'
    assert j[":state"] == ":verified"
    assert j[":tags"] == ['"finality"', '"longest-chain"']
    assert j[":source-id"] == '"source-y"'
    assert j[":body"] == {"$list": ['"asserts"', '"X"', '"Y"']}
    assert j[":provenance"][":locator"] == '"p.7 §3.2"'

def test_concept_projection_shape():
    c = C(slug="nakamoto", title="Nakamoto Consensus",
          surface_forms=["longest-chain rule"], sources=["s-1"])
    j = _concept_to_json(c)
    assert j[":kind"] == ":concept"
    assert j[":slug"] == '"nakamoto"'
    assert j[":surface-forms"] == ['"longest-chain rule"']
    assert j[":sources"] == ['"s-1"']

def test_candidate_projection_includes_score_as_number():
    cand = C(id="arxiv:1234", extracted_concepts=[
        C(slug="p", title="", surface_forms=[], sources=[]),
    ], embedding_score=0.82)
    j = _candidate_to_json(cand)
    assert j[":embedding-score"] == 0.82
    assert len(j[":extracted-concepts"]) == 1

def test_tree_projection_handles_root_node():
    node = C(node_id="ch1.n1", statement="finality is reached", tags=["finality"],
             required_evidence_kind="empirical", parent_id=None)
    tree = C(chapter_id="ch-01", nodes=[node])
    j = _tree_to_json(tree)
    assert j[":chapter-id"] == '"ch-01"'
    assert j[":nodes"][0][":parent-id"] is None
    assert j[":nodes"][0][":required-evidence-kind"] == ":empirical"

def test_sexpr_string_wraps_in_quotes():
    assert _sexpr_to_json("asserts") == '"asserts"'

def test_sexpr_list_uses_dollar_list_envelope():
    assert _sexpr_to_json(["a", ["b", "c"]]) == {
        "$list": ['"a"', {"$list": ['"b"', '"c"']}],
    }
