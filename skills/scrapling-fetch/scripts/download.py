from __future__ import annotations
import hashlib
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from scripts.exceptions import NotAPdf, FetchFailed

@dataclass
class DownloadResult:
    path: Path
    sha256: str
    bytes: int
    content_type: str


class _CurlStreamResponse:
    """Wraps a curl_cffi streaming response to expose headers and iter_bytes()."""

    def __init__(self, session, url: str):
        self._session = session
        self._url = url
        self._response = None
        self.headers: dict = {}

    def __enter__(self):
        self._response = self._session.get(self._url, stream=True)
        self.headers = dict(self._response.headers)
        return self

    def __exit__(self, *a):
        if self._response is not None:
            self._response.close()

    def iter_bytes(self, chunk_size: int = 8192):
        if self._response is None:
            raise RuntimeError("Stream not entered")
        yield from self._response.iter_content(chunk_size=chunk_size)


class _StreamSession:
    """Minimal session adapter that provides stream(url) -> context manager."""

    def __init__(self):
        from curl_cffi.requests import Session
        self._curl = Session()

    def stream(self, url: str) -> _CurlStreamResponse:
        return _CurlStreamResponse(self._curl, url)


_stream_session = None


def _session_for_stream() -> _StreamSession:
    global _stream_session
    if _stream_session is None:
        _stream_session = _StreamSession()
    return _stream_session


def download_pdf(url: str, dest: Path) -> DownloadResult:
    sess = _session_for_stream()
    h = hashlib.sha256()
    n = 0
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        with sess.stream(url) as resp:
            ct = resp.headers.get("content-type", "")
            if "pdf" not in ct.lower():
                raise NotAPdf(f"{url} returned {ct!r}")
            with dest.open("wb") as f:
                for chunk in resp.iter_bytes(chunk_size=8192):
                    h.update(chunk)
                    n += len(chunk)
                    f.write(chunk)
        return DownloadResult(path=dest, sha256=h.hexdigest(), bytes=n, content_type=ct)
    except NotAPdf:
        if dest.exists():
            dest.unlink()
        raise
    except Exception as e:
        if dest.exists():
            dest.unlink()
        raise FetchFailed(url, reason=str(e)) from e
