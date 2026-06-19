"""Public API surface of liveliness-signals."""
from __future__ import annotations
from pathlib import Path
import sys

API_VERSION = (0, 1)
_SKILL_ROOT = Path(__file__).resolve().parent
if str(_SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(_SKILL_ROOT))

__all__ = ["API_VERSION"]

import json as _json


def load_profile():
    """Return the committed Hoskinson style profile (statistics only)."""
    path = _SKILL_ROOT / "assets" / "hoskinson-style-profile.json"
    return _json.loads(path.read_text(encoding="utf-8"))


__all__.append("load_profile")
