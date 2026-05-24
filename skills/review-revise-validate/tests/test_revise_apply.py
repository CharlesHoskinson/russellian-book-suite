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


def test_run_revise_empty_clusters_writes_identity_copy(tmp_path):
    """When instructions have no ## Cluster headers, run_revise writes empty
    revisions.json and an identity-copy of the chapter (no dispatch at all)."""
    chapter = tmp_path / "ch.md"
    chapter.write_text(
        "Paragraph one is fine.\n\nParagraph two has a listicle abstract.\n",
        encoding="utf-8",
    )
    instructions = tmp_path / "instructions.md"
    # Deliberately no "## Cluster CXX" headers — old-style plain text
    instructions.write_text("# Revision instructions\n\nCluster C01: revise para 2\n", encoding="utf-8")
    output_dir = tmp_path / "out"

    with patch("scripts.revise.run_persona_via_ollama") as mock_dispatch:
        run_revise(
            chapter_path=chapter,
            instructions_path=instructions,
            output_dir=output_dir,
            chapter_id="ch-01",
            model="gemma4:31b",
        )
        # No dispatch should have been made (no clusters parsed)
        mock_dispatch.assert_not_called()

    assert (output_dir / "revisions.json").exists()
    assert (output_dir / "revised-chapter.md").exists()
    revisions = json.loads((output_dir / "revisions.json").read_text(encoding="utf-8"))
    assert revisions["revisions"] == []
    # Chapter is identity-copied
    revised = (output_dir / "revised-chapter.md").read_text(encoding="utf-8")
    assert "Paragraph two has a listicle abstract." in revised


from scripts.revise import _parse_clusters, InstructionCluster


def test_parse_clusters_extracts_each_cluster_block():
    instructions = """# Revision instructions for ch-01

## Cluster C01 (Critical; 2 personas)
Lines 10-15

Findings:
- gottlieb: a
- ai-slop: b

Fix recipe: ...

## Cluster C02 (Important; 1 personas)
Lines 50-50

Findings:
- lay-reader: c

Fix recipe: ...

## Unanchored findings

- gottlieb: vague comment
"""
    clusters = _parse_clusters(instructions)
    assert len(clusters) == 2
    assert clusters[0].cluster_id == "C01"
    assert clusters[1].cluster_id == "C02"
    # C01 body includes its own heading line
    assert "## Cluster C01" in clusters[0].body_md
    # Cluster bodies do NOT include the Unanchored findings section
    assert "Unanchored" not in clusters[0].body_md
    assert "Unanchored" not in clusters[1].body_md


def test_parse_clusters_empty_when_no_clusters():
    instructions = "# Revision instructions for ch-01\n\n_(no clusters)_\n"
    assert _parse_clusters(instructions) == []


def test_run_revise_dispatches_once_per_cluster(tmp_path):
    """run_revise dispatches the reviser N times for N clusters."""
    chapter = tmp_path / "ch.md"
    chapter.write_text(
        "Paragraph one.\n\nParagraph two.\n\nParagraph three.\n",
        encoding="utf-8",
    )
    instructions = tmp_path / "instructions.md"
    instructions.write_text("""# Revision instructions for ch-01

## Cluster C01 (Critical)
Findings: revise para 2

## Cluster C02 (Important)
Findings: revise para 3
""", encoding="utf-8")
    output_dir = tmp_path / "out"

    call_count = [0]

    def fake_dispatch(*, persona_id, template_path, persona_path, slots, output_path, **kwargs):
        call_count[0] += 1
        # Return a different revision per cluster based on which one is in slots
        if "C01" in slots["revision_instructions"]:
            mock_response = '''```json
{"revisions": [{"cluster_id": "C01", "original": "Paragraph two.", "revised": "Para two rewritten.", "rationale": "C01"}], "unresolved": []}
```'''
        elif "C02" in slots["revision_instructions"]:
            mock_response = '''```json
{"revisions": [{"cluster_id": "C02", "original": "Paragraph three.", "revised": "Para three rewritten.", "rationale": "C02"}], "unresolved": []}
```'''
        else:
            mock_response = '{"revisions": [], "unresolved": []}'
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(mock_response, encoding="utf-8")
        from llm_infra.persona_dispatch import PersonaDispatchResult
        return PersonaDispatchResult(
            artifact_path=output_path,
            elapsed_seconds=1.0,
            response_chars=len(mock_response),
            model_used=kwargs.get("model", "gemma4:31b"),
        )

    with patch("scripts.revise.run_persona_via_ollama", side_effect=fake_dispatch):
        run_revise(
            chapter_path=chapter,
            instructions_path=instructions,
            output_dir=output_dir,
            chapter_id="ch-01",
            model="gemma4:31b",
        )

    assert call_count[0] == 2  # one call per cluster
    revisions = json.loads((output_dir / "revisions.json").read_text(encoding="utf-8"))
    assert len(revisions["revisions"]) == 2
    revised = (output_dir / "revised-chapter.md").read_text(encoding="utf-8")
    assert "Para two rewritten." in revised
    assert "Para three rewritten." in revised


def test_run_revise_continues_when_one_cluster_fails(tmp_path):
    """If cluster 2 returns invalid JSON, cluster 1's revision still applies."""
    chapter = tmp_path / "ch.md"
    chapter.write_text("Paragraph one.\n\nParagraph two.\n", encoding="utf-8")
    instructions = tmp_path / "instructions.md"
    instructions.write_text("""# Revision instructions

## Cluster C01
revise para 1

## Cluster C02
this will fail
""", encoding="utf-8")
    output_dir = tmp_path / "out"

    def fake_dispatch(*, persona_id, template_path, persona_path, slots, output_path, **kwargs):
        if "C01" in slots["revision_instructions"]:
            mock = '''```json
{"revisions": [{"cluster_id": "C01", "original": "Paragraph one.", "revised": "Para one ok.", "rationale": "C01"}], "unresolved": []}
```'''
        else:
            # Malformed JSON for C02
            mock = '```json\n{not valid json\n```'
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(mock, encoding="utf-8")
        from llm_infra.persona_dispatch import PersonaDispatchResult
        return PersonaDispatchResult(output_path, 1.0, len(mock), kwargs.get("model", "gemma4:31b"))

    with patch("scripts.revise.run_persona_via_ollama", side_effect=fake_dispatch):
        run_revise(
            chapter_path=chapter,
            instructions_path=instructions,
            output_dir=output_dir,
            chapter_id="ch-01",
            model="gemma4:31b",
        )

    revisions = json.loads((output_dir / "revisions.json").read_text(encoding="utf-8"))
    assert len(revisions["revisions"]) == 1
    assert revisions["revisions"][0]["cluster_id"] == "C01"
    assert len(revisions["unresolved"]) == 1
    assert revisions["unresolved"][0]["cluster_id"] == "C02"
    revised = (output_dir / "revised-chapter.md").read_text(encoding="utf-8")
    assert "Para one ok." in revised
