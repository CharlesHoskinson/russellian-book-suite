"""Session builders for scrapling-fetch.

Scrapling 0.4.8 exposes the following politeness primitives on
`FetcherSession.__init__`: `retries`, `retry_delay`, `timeout`,
`impersonate`, `stealthy_headers`, `follow_redirects`, `verify`. We pass
explicit defaults so the configuration is visible to readers and exercised
by tests. We also wrap each session in a per-host rate limiter that
enforces a minimum delay between requests to the same host — Scrapling
0.4.8 does not provide a session-level `download_delay` knob, so we add
one ourselves to satisfy NFR-1 / REQ-SF-3 politeness intent.

`robots_txt_obey` and a production disk cache are NOT exposed on
FetcherSession in 0.4.8 (they exist on the higher-level `Spider` crawler
class, which is the wrong abstraction for a one-shot fetcher). Both are
documented v0.2 follow-ups; see `references/scrapling-tuning.md`.
"""
from __future__ import annotations
import threading
import time
from enum import Enum
from pathlib import Path
from urllib.parse import urlparse

CACHE_ROOT = Path.home() / ".cache" / "scrapling-fetch"

# Politeness defaults — visible here so tests can assert them.
DEFAULT_TIMEOUT_S = 30
DEFAULT_RETRIES = 3
DEFAULT_RETRY_DELAY_S = 1
DEFAULT_IMPERSONATE = "chrome"
DEFAULT_STEALTHY_HEADERS = True
DEFAULT_FOLLOW_REDIRECTS = "safe"
PER_HOST_MIN_DELAY_S = 1.0


class SessionMode(str, Enum):
    PLAIN = "plain"
    STEALTH = "stealth"
    DYNAMIC = "dynamic"


_last_request_by_host: dict[str, float] = {}
_rate_lock = threading.Lock()


def _enforce_per_host_delay(url: str, min_delay_s: float = PER_HOST_MIN_DELAY_S) -> None:
    """Sleep if the previous request to the same host was less than `min_delay_s` ago."""
    host = urlparse(url).hostname or ""
    if not host:
        return
    with _rate_lock:
        last = _last_request_by_host.get(host)
        now = time.monotonic()
        if last is not None:
            elapsed = now - last
            if elapsed < min_delay_s:
                time.sleep(min_delay_s - elapsed)
                now = time.monotonic()
        _last_request_by_host[host] = now


class _RateLimitedSession:
    """Wraps a Scrapling session so each `.get(url, ...)` enforces a per-host delay.

    Forwards every other attribute access (including `.stream`, `__enter__`, `__exit__`)
    to the wrapped session unchanged."""

    def __init__(self, inner, min_delay_s: float = PER_HOST_MIN_DELAY_S):
        self._inner = inner
        self._min_delay_s = min_delay_s

    def get(self, url: str, *args, **kwargs):
        _enforce_per_host_delay(url, self._min_delay_s)
        return self._inner.get(url, *args, **kwargs)

    def stream(self, url: str, *args, **kwargs):
        _enforce_per_host_delay(url, self._min_delay_s)
        return self._inner.stream(url, *args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._inner, name)

    def __enter__(self):
        entered = self._inner.__enter__() if hasattr(self._inner, "__enter__") else self._inner
        return _RateLimitedSession(entered, self._min_delay_s) if entered is not self._inner else self

    def __exit__(self, *exc):
        if hasattr(self._inner, "__exit__"):
            return self._inner.__exit__(*exc)
        return False


def build_session(mode: SessionMode):
    """Construct a Scrapling session with politeness defaults wired in."""
    if mode == SessionMode.PLAIN:
        from scrapling.engines.static import FetcherSession
        sess = FetcherSession(
            timeout=DEFAULT_TIMEOUT_S,
            retries=DEFAULT_RETRIES,
            retry_delay=DEFAULT_RETRY_DELAY_S,
            impersonate=DEFAULT_IMPERSONATE,
            stealthy_headers=DEFAULT_STEALTHY_HEADERS,
            follow_redirects=DEFAULT_FOLLOW_REDIRECTS,
        )
        return _RateLimitedSession(sess)
    if mode == SessionMode.STEALTH:
        from scrapling.engines._browsers._stealth import StealthySession
        return _RateLimitedSession(StealthySession(headless=True))
    if mode == SessionMode.DYNAMIC:
        from scrapling.engines._browsers._controllers import DynamicSession
        return _RateLimitedSession(DynamicSession(headless=True))
    raise ValueError(mode)
