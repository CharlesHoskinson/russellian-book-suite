"""Book-compose serializer tests for chapter retrieval bundles."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from scripts import chapter_bundle


def test_build_chapter_bundle_input_uses_book_knowledge_projector(monkeypatch, tmp_path):
    payload = {
        "schema": "chapter-retrieval-bundle/v1",
        "chapter-id": "ch-01",
        "chapter-uri": "https://example.org/book-knowledge/chapters/ch-01",
        "dominant-communities": [],
        "load-bearing-claims": [],
        "unresolved-rebuttals": [],
        "source-span-anchors": [],
    }
    row = {
        "payload": payload,
        "payload_json": json.dumps(payload, indent=2, sort_keys=True) + "\n",
        "payload_edn": "{:schema \"chapter-retrieval-bundle/v1\"}\n",
        "prompt_scaffold": "State the chapter thesis.",
    }

    def fake_loader(name: str):
        assert name == "project_chapter_bundle"
        return SimpleNamespace(
            project_chapter_bundle=lambda workspace, chapter_id: row,
            validate_bundle_payload=lambda candidate: None,
        )

    monkeypatch.setattr(chapter_bundle, "load_book_knowledge_module", fake_loader)

    result = chapter_bundle.build_chapter_bundle_input(tmp_path, "ch-01")

    assert result["chapter_id"] == "ch-01"
    assert result["payload"] == payload
    assert result["json"] == row["payload_json"]
    assert result["edn"] == row["payload_edn"]
    assert result["prompt_scaffold"] == "State the chapter thesis."
