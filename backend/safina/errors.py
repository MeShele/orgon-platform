"""Safina API error handling."""


class SafinaError(Exception):
    """Base Safina API error.

    `status_code` carries the HTTP code Safina returned (when the error
    is a wrapped HTTP failure) so callers can distinguish a 4xx user
    error from a 5xx infra failure without parsing message strings.
    """

    def __init__(
        self,
        message: str,
        line: str | None = None,
        status_code: int | None = None,
    ):
        self.message = message
        self.line = line
        self.status_code = status_code
        super().__init__(message)


class SafinaAuthError(SafinaError):
    """Signature or authentication failure."""
    pass


class SafinaNetworkError(SafinaError):
    """Network/connectivity issues."""
    pass


class SafinaValidationError(SafinaError):
    """Invalid request parameters."""
    pass
