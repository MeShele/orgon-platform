"""Safina API error handling."""


class SafinaError(Exception):
    """Base Safina API error."""

    def __init__(self, message: str, line: str | None = None):
        self.message = message
        self.line = line
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
