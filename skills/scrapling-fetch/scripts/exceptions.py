class FetchError(RuntimeError):
    pass

class FetchFailed(FetchError):
    def __init__(self, url: str, reason: str):
        super().__init__(f"{url}: {reason}")
        self.url = url
        self.reason = reason

class RateLimitExceeded(FetchError):
    pass

class BlockedRequest(FetchError):
    pass

class NotAPdf(FetchError):
    pass

class OfflineMiss(FetchError):
    pass

class ArxivIdNotFound(FetchError):
    pass
