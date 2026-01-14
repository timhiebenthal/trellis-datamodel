"""
Domain exception types for consistent error handling across the application.

These exceptions are mapped to HTTP status codes via FastAPI exception handlers
in server.py to provide consistent API error responses.
"""


class DomainError(Exception):
    """Base exception for domain-level errors."""

    def __init__(self, message: str, detail: str | None = None):
        """
        Initialize domain error.

        Args:
            message: Human-readable error message
            detail: Optional additional detail for debugging
        """
        super().__init__(message)
        self.message = message
        self.detail = detail


class NotFoundError(DomainError):
    """Raised when a requested resource is not found."""

    pass


class ValidationError(DomainError):
    """Raised when input validation fails."""

    pass


class ConfigurationError(DomainError):
    """Raised when configuration is invalid or missing."""

    pass


class FileOperationError(DomainError):
    """Raised when file operations fail."""

    pass


class FeatureDisabledError(DomainError):
    """Raised when a feature is disabled in configuration."""

    pass
