"""Cites REQ-LIVE-004 (CLI parses --register and stays advisory)."""
import json
import pytest
pytestmark = pytest.mark.windows_canary
from scripts.score import main


@pytest.mark.needs_model
def test_cli_register_flag_leading(tmp_path, capsys):
    f = tmp_path / "in.md"
    f.write_text("The bank holds your money. You trust it completely.", encoding="utf-8")
    rc = main(["score.py", "--register", "polemic", str(f)])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["register"] == "polemic"


@pytest.mark.needs_model
def test_cli_positional_only(tmp_path, capsys):
    f = tmp_path / "in.md"
    f.write_text("The bank holds your money. You trust it completely.", encoding="utf-8")
    rc = main(["score.py", str(f)])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["register"] == "narrative-editorial"
