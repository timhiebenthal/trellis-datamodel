"""Shared FastAPI dependencies for route modules."""

from typing import Callable

from trellis_datamodel.exceptions import FeatureDisabledError


def require_feature(
    is_enabled: Callable[[], bool], message: str, status_code: int = 403
) -> Callable[[], None]:
    """
    Build a ``Depends`` guard that rejects requests while a feature is off.

    Args:
        is_enabled: Reads the flag at request time, so config reloads apply
        message: Detail returned to the client when the feature is disabled
        status_code: HTTP status for the disabled response (403 unless a
            feature's spec requires it to look absent with 404)

    Returns:
        A dependency callable raising FeatureDisabledError when disabled
    """

    def guard() -> None:
        if not is_enabled():
            raise FeatureDisabledError(message, status_code=status_code)

    return guard
