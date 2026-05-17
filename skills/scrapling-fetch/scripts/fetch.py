from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal
import os
from scripts.exceptions import FetchFailed, OfflineMiss
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
        # FetcherSession is a context manager; enter it to get the live session
        # with .get() instance methods. StealthySession/DynamicSession are also
        # context managers but are used differently — for those, store as-is and
        # call .get() (they expose it directly via __enter__ too).
        if hasattr(sess_obj, '__enter__') and hasattr(sess_obj, 'get'):
            _session_cache[mode] = sess_obj
        elif hasattr(sess_obj, '__enter__'):
            # Enter the context to obtain the underlying session with .get()
            live = sess_obj.__enter__()
            _session_cache[mode] = live
        else:
            _session_cache[mode] = sess_obj
    return _session_cache[mode]

def fetch(url: str, mode: Mode = "plain", timeout_s: int = 20) -> Page:
    if os.environ.get("SCRAPLING_OFFLINE") == "1":
        raise OfflineMiss(f"offline mode and {url} not in cache")
    sess = _session_for_mode(mode)
    try:
        resp = sess.get(url, timeout=timeout_s)
    except Exception as e:
        raise FetchFailed(url, reason=str(e)) from e
    return Page(
        url=url,
        final_url=getattr(resp, "url", url),
        status=resp.status,
        html=resp.html,
        fetched_at=datetime.now(timezone.utc),
        headers=dict(getattr(resp, "headers", {})),
    )
