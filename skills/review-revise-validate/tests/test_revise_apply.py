"""Tests for revise.py - JSON extraction + Phase B apply."""
from __future__ import annotations

import json

import pytest

from scripts.revise import _extract_json_object


def test_extract_json_object_from_code_fence():
    response = '''Some preamble.

```json
{"revisions": [{"original": "a", "revised": "b", "rationale": "x"}],
 "unresolved": []}
```

Some trailing text.'''
    obj = _extract_json_object(response)
    assert obj["revisions"][0]["original"] == "a"
    assert obj["unresolved"] == []


def test_extract_json_object_bare_object():
    response = '''{"revisions": [], "unresolved": []}'''
    obj = _extract_json_object(response)
    assert obj == {"revisions": [], "unresolved": []}


def test_extract_json_object_no_json_raises():
    response = "I'm sorry, I cannot help with that request."
    with pytest.raises(ValueError, match="no JSON"):
        _extract_json_object(response)


def test_extract_json_object_malformed_json_raises():
    response = '''```json
{not valid json
```'''
    with pytest.raises(ValueError, match="JSON"):
        _extract_json_object(response)


from scripts.revise import apply_revisions, ApplyError


def test_apply_revisions_happy_path(tmp_path):
    chapter = tmp_path / "ch.md"
    chapter.write_text(
        "Paragraph one.\n\nParagraph two has a listicle abstract.\n\nParagraph three.\n",
        encoding="utf-8",
    )
    revisions_obj = {
        "revisions": [
            {
                "cluster_id": "C01",
                "original": "Paragraph two has a listicle abstract.",
                "revised": "Paragraph two argues the point in prose.",
                "rationale": "Cluster C01 (listicle abstract)",
            }
        ],
        "unresolved": [],
    }
    out_path = tmp_path / "revised.md"
    apply_revisions(chapter_path=chapter, revisions_obj=revisions_obj, output_path=out_path)
    revised = out_path.read_text(encoding="utf-8")
    assert "Paragraph two argues the point in prose." in revised
    assert "Paragraph two has a listicle abstract." not in revised
    assert "Paragraph one." in revised
    assert "Paragraph three." in revised


def test_apply_revisions_missing_original_raises(tmp_path):
    chapter = tmp_path / "ch.md"
    chapter.write_text("Paragraph one.\nParagraph two.\n", encoding="utf-8")
    revisions_obj = {
        "revisions": [
            {
                "cluster_id": "C01",
                "original": "Paragraph that does not exist verbatim.",
                "revised": "anything",
                "rationale": "C01",
            }
        ],
        "unresolved": [],
    }
    out_path = tmp_path / "revised.md"
    with pytest.raises(ApplyError) as exc:
        apply_revisions(chapter_path=chapter, revisions_obj=revisions_obj, output_path=out_path)
    assert "C01" in str(exc.value)


def test_apply_revisions_writes_failures_file(tmp_path):
    chapter = tmp_path / "ch.md"
    chapter.write_text("Paragraph one.\n", encoding="utf-8")
    revisions_obj = {
        "revisions": [
            {"cluster_id": "C01", "original": "absent A", "revised": "x", "rationale": "x"},
            {"cluster_id": "C02", "original": "absent B", "revised": "y", "rationale": "y"},
        ],
        "unresolved": [],
    }
    out_path = tmp_path / "revised.md"
    with pytest.raises(ApplyError) as exc:
        apply_revisions(chapter_path=chapter, revisions_obj=revisions_obj, output_path=out_path)
    assert len(exc.value.failures) == 2
    cluster_ids = [f["cluster_id"] for f in exc.value.failures]
    assert "C01" in cluster_ids and "C02" in cluster_ids


def test_apply_revisions_preserves_whitespace_in_original(tmp_path):
    chapter = tmp_path / "ch.md"
    chapter.write_text("Paragraph one.\nParagraph two.\n", encoding="utf-8")
    revisions_obj = {
        "revisions": [
            {
                "cluster_id": "C01",
                "original": "Paragraph one.\n",
                "revised": "Para one revised.\n",
                "rationale": "C01",
            }
        ],
        "unresolved": [],
    }
    out_path = tmp_path / "revised.md"
    apply_revisions(chapter_path=chapter, revisions_obj=revisions_obj, output_path=out_path)
    assert out_path.read_text(encoding="utf-8").startswith("Para one revised.\n")


from unittest.mock import patch

from scripts.revise import run_revise


def test_run_revise_dispatches_via_run_persona_via_ollama_and_parses_json(tmp_path):
    chapter = tmp_path / "ch.md"
    chapter.write_text(
        "Paragraph one is fine.\n\nParagraph two has a listicle abstract.\n",
        encoding="utf-8",
    )
    instructions = tmp_path / "instructions.md"
    instructions.write_text("# Revision instructions\n\nCluster C01: revise para 2\n", encoding="utf-8")
    output_dir = tmp_path / "out"

    mock_response = '''```json
{
  "revisions": [
    {"cluster_id": "C01",
     "original": "Paragraph two has a listicle abstract.",
     "revised": "Paragraph two argues the point in prose.",
     "rationale": "C01"}
  ],
  "unresolved": []
}
```'''

    with patch("scripts.revise.run_persona_via_ollama") as mock_dispatch:
        from llm_infra.persona_dispatch import PersonaDispatchResult
        def fake_dispatch(*, persona_id, template_path, persona_path, slots, output_path, **kwargs):
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(mock_response, encoding="utf-8")
            return PersonaDispatchResult(
                artifact_path=output_path,
                elapsed_seconds=1.0,
                response_chars=len(mock_response),
                model_used=kwargs.get("model", "gemma4:31b"),
            )
        mock_dispatch.side_effect = fake_dispatch

        run_revise(
            chapter_path=chapter,
            instructions_path=instructions,
            output_dir=output_dir,
            chapter_id="ch-01",
            model="gemma4:31b",
        )

    assert (output_dir / "revisions-raw-response.md").exists()
    assert (output_dir / "revisions.json").exists()
    assert (output_dir / "revised-chapter.md").exists()
    revisions = json.loads((output_dir / "revisions.json").read_text(encoding="utf-8"))
    assert revisions["revisions"][0]["cluster_id"] == "C01"
    revised = (output_dir / "revised-chapter.md").read_text(encoding="utf-8")
    assert "Paragraph two argues the point in prose." in revised
