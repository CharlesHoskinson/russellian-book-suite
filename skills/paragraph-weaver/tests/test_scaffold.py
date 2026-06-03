# tests/test_scaffold.py
"""Scaffold smoke test: packages import from the skill root."""
from __future__ import annotations

import pytest
pytestmark = pytest.mark.windows_canary


def test_engine_package_importable():
    import engine  # noqa: F401
    import targets  # noqa: F401
    import scripts  # noqa: F401
