from __future__ import annotations
from enum import Enum
from pathlib import Path

CACHE_ROOT = Path.home() / ".cache" / "scrapling-fetch"

class SessionMode(str, Enum):
    PLAIN = "plain"
    STEALTH = "stealth"
    DYNAMIC = "dynamic"

def build_session(mode: SessionMode):
    """Construct a Scrapling session with politeness defaults wired in."""
    if mode == SessionMode.PLAIN:
        from scrapling.engines.static import FetcherSession
        return FetcherSession()
    if mode == SessionMode.STEALTH:
        from scrapling.engines._browsers._stealth import StealthySession
        return StealthySession(headless=True)
    if mode == SessionMode.DYNAMIC:
        from scrapling.engines._browsers._controllers import DynamicSession
        return DynamicSession(headless=True)
    raise ValueError(mode)
