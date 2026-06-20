from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.fixture import fixture_entrypoint


def test_REQ_KG_901_fixture_requirement():
    assert fixture_entrypoint() == "REQ-KG-901"
