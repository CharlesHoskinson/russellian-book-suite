"""Cites REQ-TRIAD-001 (register routing)."""
import pytest
pytestmark = pytest.mark.windows_canary
from scripts.register_router import route, REGISTERS


def test_routes_technical():
    assert route("How does the KZG commitment construction work mechanically?") == "technical-exposition"


def test_routes_polemic():
    assert route("Why 'trustless' is a myth everyone repeats and should stop saying") == "polemic"


def test_defaults_to_narrative():
    assert route("Sending the bit, not the dossier: what ZK proofs let you do") == "narrative-editorial"
    assert REGISTERS == ("technical-exposition", "narrative-editorial", "polemic")
