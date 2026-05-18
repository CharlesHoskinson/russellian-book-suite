"""REQ-EDN-050: _emit_float never produces scientific notation."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts._edn_writer import _emit_float, EdnWriteError


PROBE_FINITE = [
    1.0, 0.0, -0.0,
    1e-20, 1e-10, 6.022e23, -1.5e-7,
    1.234567890123, 1e308, 1e-308,
    -1e-300, 3.141592653589793,
]


@pytest.mark.parametrize("v", PROBE_FINITE)
def test_no_scientific_notation(v):
    s = _emit_float(v)
    assert "e" not in s.lower(), (
        f"_emit_float({v!r}) = {s!r} contains 'e'"
    )


@pytest.mark.parametrize("v", PROBE_FINITE)
def test_has_decimal_point(v):
    s = _emit_float(v)
    assert "." in s, (
        f"_emit_float({v!r}) = {s!r} lacks decimal point; would parse as Int"
    )


def test_non_finite_raises():
    import math
    for v in (math.inf, -math.inf, math.nan):
        with pytest.raises(EdnWriteError):
            _emit_float(v)
