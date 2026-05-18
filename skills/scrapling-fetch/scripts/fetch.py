from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal
import os
from scripts.exceptions import (
    FetchFailed,
    OfflineMiss,
    RateLimitExceeded,
    BlockedRequest,
)
from scripts.session import build_session, SessionMode

Mode = Literal["plain", "stealth", "dynamic"]

@dataclass
class Page:
    url: str
    final_url: str
    status: int
    html: str
    fetched_at: datetime
    headers: dict

_session_cache: dict[str, object] = {}

def _session_for_mode(mode: Mode):
    if mode not in _session_cache:
        sess_obj = build_session(SessionMode(mode))
        # Scrapling 0.4.8's FetcherSession exposes .get only after __enter__,
        # and a wrapper that defines its own .get can still delegate to an
        # un-entered inner — so `hasattr(sess_obj, 'get')` is not a sufficient
        # readiness signal. Always enter the context manager when it exists.
        if hasattr(sess_obj, '__enter__'):
            _session_cache[mode] = sess_obj.__enter__()
        else:
            _session_cache[mode] = sess_obj
    return _session_cache[mode]


def _response_html(resp) -> str:
    """Extract the HTML body from a Scrapling response.

    Scrapling 0.4.8 carries the body on `html_content`; earlier and future
    versions have used `html` and `text`. Try in order so the fetcher stays
    compatible across upstream changes."""
    return (
        getattr(resp, "html_content", None)
        or getattr(resp, "html", None)
        or getattr(resp, "text", None)
        or ""
    )

def _dispatch_status(url: str, status: int) -> None:
    """Translate non-success HTTP status codes into typed exceptions.

    Spec: REQ-SF-4 (typed exceptions). 2xx and 3xx are success / redirect-follow;
    Scrapling's `follow_redirects='safe'` resolves 3xx internally, so a 3xx
    here is a redirect Scrapling chose not to follow."""
    if 200 <= status < 400:
        return
    if status == 429:
        raise RateLimitExceeded(f"{url}: HTTP 429 Too Many Requests")
    if status == 403:
        raise BlockedRequest(f"{url}: HTTP 403 Forbidden")
    raise FetchFailed(url, reason=f"HTTP {status}")

def fetch(url: str, mode: Mode = "plain", timeout_s: int = 20) -> Page:
    if os.environ.get("SCRAPLING_OFFLINE") == "1":
        raise OfflineMiss(f"offline mode and {url} not in cache")
    sess = _session_for_mode(mode)
    try:
        resp = sess.get(url, timeout=timeout_s)
    except (RateLimitExceeded, BlockedRequest, FetchFailed):
        raise
    except Exception as e:
        raise FetchFailed(url, reason=str(e)) from e
    _dispatch_status(url, resp.status)
    return Page(
        url=url,
        final_url=getattr(resp, "url", url),
        status=resp.status,
        html=_response_html(resp),
        fetched_at=datetime.now(timezone.utc),
        headers=dict(getattr(resp, "headers", {})),
    )
