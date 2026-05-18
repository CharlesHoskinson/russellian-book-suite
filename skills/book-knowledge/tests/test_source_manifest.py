from datetime import datetime, timezone
from pathlib import Path

import pytest
from scripts.source_manifest import (
    compute_doc_id,
    compute_sha256,
    write_manifest,
    load_manifest,
    ManifestValidationError,
)


def test_compute_doc_id_is_kebab_case():
    assert compute_doc_id("My Important Paper.pdf") == "my-important-paper"
    assert compute_doc_id("foo_bar.MD") == "foo-bar"


def test_compute_doc_id_strips_punctuation():
    assert compute_doc_id("Smith & Jones (2024) — v2.pdf") == "smith-jones-2024-v2"


def test_compute_sha256_is_stable(tmp_path):
    f = tmp_path / "x.txt"
    f.write_bytes(b"hello world")
    assert compute_sha256(f) == "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"


def test_write_and_load_manifest_roundtrip(tmp_path):
    record = {
        "doc_name": "small.pdf",
        "doc_id": "small",
        "source_kind": "pdf",
        "sha256": "b" * 64,
        "ingested_at": datetime.now(timezone.utc).isoformat(),
        "node_count": 12,
        "page_count": 3,
    }
    out = tmp_path / "small.json"
    write_manifest(out, record)
    loaded = load_manifest(out)
    assert loaded == record


def test_write_manifest_rejects_invalid_record(tmp_path):
    bad = {"doc_name": "x", "doc_id": "Has Spaces", "source_kind": "pdf",
           "sha256": "z" * 64, "ingested_at": "2026-05-09T00:00:00Z", "node_count": 0}
    with pytest.raises(ManifestValidationError):
        write_manifest(tmp_path / "bad.json", bad)


def test_trust_field_accepted_by_schema(tmp_path):
    record = {
        "doc_name": "thesis",
        "doc_id": "thesis",
        "source_kind": "markdown",
        "sha256": "c" * 64,
        "ingested_at": "2026-05-01T00:00:00Z",
        "node_count": 20,
        "trust": 1.0,
    }
    out = tmp_path / "thesis.json"
    # should not raise
    write_manifest(out, record)
    loaded = load_manifest(out)
    assert loaded["trust"] == 1.0


def test_trust_field_boundary_values(tmp_path):
    for trust_val in (0.0, 0.5, 1.0):
        record = {
            "doc_name": "source",
            "doc_id": "source",
            "source_kind": "pdf",
            "sha256": "d" * 64,
            "ingested_at": "2026-05-01T00:00:00Z",
            "node_count": 1,
            "trust": trust_val,
        }
        write_manifest(tmp_path / f"source-{trust_val}.json", record)


def test_trust_field_out_of_range_rejected(tmp_path):
    for trust_val in (-0.1, 1.1, 2.0):
        record = {
            "doc_name": "source",
            "doc_id": "source",
            "source_kind": "pdf",
            "sha256": "e" * 64,
            "ingested_at": "2026-05-01T00:00:00Z",
            "node_count": 1,
            "trust": trust_val,
        }
        with pytest.raises(ManifestValidationError):
            write_manifest(tmp_path / "bad-trust.json", record)


def test_bermuda_synthesizer_manifest_is_schema_valid(tmp_path):
    """Manifest emitted by synthesize_bermuda_ledger must pass schema validation."""
    import sys
    import importlib
    # The synthesizer is in tools/ at the repo root; locate it relative to this file.
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    tools_dir = repo_root / "tools"
    if str(tools_dir) not in sys.path:
        sys.path.insert(0, str(tools_dir))
    synthesize_mod = importlib.import_module("synthesize_bermuda_ledger")

    # Copy the bermuda thesis YAML into tmp_path so synthesizer has something to read.
    bermuda_thesis = repo_root / "examples" / "bermuda-manual" / "thesis" / "bermuda-manual.yaml"
    if not bermuda_thesis.exists():
        import pytest; pytest.skip("bermuda thesis not found")

    ws = tmp_path / "bermuda"
    (ws / "thesis").mkdir(parents=True)
    import shutil
    shutil.copy(bermuda_thesis, ws / "thesis" / "bermuda-manual.yaml")

    synthesize_mod.synthesize(ws)

    manifest_path = ws / "raw" / "manifests" / "thesis.json"
    assert manifest_path.exists()
    loaded = load_manifest(manifest_path)  # raises ManifestValidationError if invalid
    assert loaded["doc_id"] == "thesis"
    assert loaded["trust"] == 1.0
