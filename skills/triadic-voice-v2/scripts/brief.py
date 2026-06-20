"""Compose register + chassis + profile targets into one generation brief."""
from __future__ import annotations

from scripts.register_router import route
from scripts.chassis import select
from scripts.profile_targets import targets, as_prompt, load_profile


def build_generation_brief(topic: str, rotation: int = 0, profile=None) -> dict:
    if profile is None:
        profile = load_profile()
    register = route(topic)
    chassis = select(register, rotation)
    t = targets(register, profile)
    return {
        "topic": topic,
        "register": register,
        "chassis": chassis,
        "targets": t,
        "targets_prompt": as_prompt(t),
        "exemplar_query": {"register": register, "move": chassis["name"]},
    }
