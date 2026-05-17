import pytest
from scripts.exceptions import (
    FetchFailed, RateLimitExceeded, BlockedRequest, NotAPdf, OfflineMiss,
    ArxivIdNotFound,
)

@pytest.mark.parametrize("exc", [
    FetchFailed, RateLimitExceeded, BlockedRequest, NotAPdf, OfflineMiss, ArxivIdNotFound
])
def test_exception_subclasses_runtime_error(exc):
    assert issubclass(exc, RuntimeError)

def test_fetch_failed_carries_url():
    e = FetchFailed("https://x", reason="timeout")
    assert e.url == "https://x"
    assert "timeout" in str(e)
