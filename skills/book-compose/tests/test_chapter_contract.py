import pytest

pytestmark = pytest.mark.windows_canary

import json
from pathlib import Path
import jsonschema
import pytest
from scripts.chapter_contract import (
    load_contract, scaffold_contract, ContractValidationError,
)


def test_load_valid_contract():
    contract = load_contract(Path("tests/fixtures/valid_contract.yaml"))
    assert contract["chapter_id"] == "ch-03"
    assert contract["audience"] == "senior-engineer"


def _schema():
    return json.loads(
        (Path(__file__).resolve().parent.parent / "assets" / "chapter-contract.schema.json").read_text(encoding="utf-8")
    )


def _valid_record(prose_mode=None):
    rec = {
        "chapter_id": "ch-01",
        "title": "Test",
        "purpose": "purpose long enough to satisfy schema",
        "audience": "senior-engineer",
        "chapter_type": "reference",
        "evidence_requirements": {"minimum_verified_claims": 0, "max_unresolved_conflicts": 0},
        "acceptance_tests": ["hedge_count == 0"],
        "output_formats": ["markdown"],
    }
    if prose_mode is not None:
        rec["prose_mode"] = prose_mode
    return rec


def test_chapter_contract_accepts_prose_mode():
    jsonschema.validate(instance=_valid_record("narrative-editorial"), schema=_schema())


def test_chapter_contract_accepts_polemic_mode():
    jsonschema.validate(instance=_valid_record("polemic"), schema=_schema())


def test_chapter_contract_accepts_technical_exposition_mode():
    jsonschema.validate(instance=_valid_record("technical-exposition"), schema=_schema())


def test_chapter_contract_omits_prose_mode_is_valid():
    """prose_mode is optional; contracts without it remain valid."""
    jsonschema.validate(instance=_valid_record(prose_mode=None), schema=_schema())


def test_chapter_contract_rejects_unknown_prose_mode():
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=_valid_record("bogus-mode"), schema=_schema())


def test_load_invalid_contract_raises():
    with pytest.raises(ContractValidationError):
        load_contract(Path("tests/fixtures/invalid_contract.yaml"))


def test_scaffold_contract_writes_template(tmp_path):
    out = tmp_path / "ch-99.yaml"
    scaffold_contract("ch-99", out)
    text = out.read_text(encoding="utf-8")
    assert "chapter_id: ch-99" in text
    assert "evidence_requirements:" in text


def test_scaffold_does_not_overwrite_existing(tmp_path):
    out = tmp_path / "ch-99.yaml"
    out.write_text("existing", encoding="utf-8")
    with pytest.raises(FileExistsError):
        scaffold_contract("ch-99", out)
