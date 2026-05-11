from pathlib import Path
import pytest
from scripts.chapter_contract import (
    load_contract, scaffold_contract, ContractValidationError,
)


def test_load_valid_contract():
    contract = load_contract(Path("tests/fixtures/valid_contract.yaml"))
    assert contract["chapter_id"] == "ch-03"
    assert contract["audience"] == "senior-engineer"


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
