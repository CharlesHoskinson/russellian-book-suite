# skill_api.py
"""Public surface of the syntopical-metabook skill.

v0.2 adds the governance layer.
"""
API_VERSION = (0, 2)

from scripts.governance.build_positions import build_positions  # noqa: E402
from scripts.governance.render_per_rule import render_per_rule  # noqa: E402
from scripts.governance.render_consensus_map import render_consensus_map  # noqa: E402

__all__ = ["API_VERSION", "build_positions", "render_per_rule", "render_consensus_map"]
