import json
from datetime import datetime, timezone
from pathlib import Path

import jsonschema
import pytest

ASSETS = Path(__file__).resolve().parent.parent / "assets"


def _schema():
    return json.loads((ASSETS / "book-manifest.schema.json").read_text(encoding="utf-8"))


def _good_manifest(**overrides):
    base = {
        "book_id": "bermuda-manual",
        "title": "Life in Bermuda",
        "version": "1.0.0",
        "built_at": datetime.now(timezone.utc).isoformat(),
        "chapters_included": ["ch-01", "ch-02"],
        "chapter_versions": {"ch-01": "v1", "ch-02": "v1"},
        "outputs": ["manuscript.md", "manuscript.html"],
        "total_word_count": 13466,
        "total_claim_count": 175,
    }
    base.update(overrides)
    return base


def test_valid_manifest_passes():
    jsonschema.validate(_good_manifest(), _schema())


def test_missing_required_field_fails():
    bad = _good_manifest()
    del bad["title"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, _schema())


def test_invalid_book_id_pattern_fails():
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(_good_manifest(book_id="Bermuda Manual"), _schema())


def test_negative_word_count_fails():
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(_good_manifest(total_word_count=-1), _schema())


def test_extra_property_rejected():
    bad = _good_manifest()
    bad["unexpected"] = "x"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, _schema())
