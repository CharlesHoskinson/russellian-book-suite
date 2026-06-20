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


def score_passage(text, register="narrative-editorial", profile=None):
    """Score one passage on the 8 liveliness signals. Returns {signal: score_dict}."""
    from scripts.score import score_passage as _sp
    return _sp(text, register=register, profile=profile)


__all__.append("score_passage")

SIGNAL_NAMES = (
    "cadence", "curiosity", "novelty_continuity", "worked_case",
    "verb_energy", "sv_distance", "concrete_anchor", "analogy_mapping",
)
__all__.append("SIGNAL_NAMES")
