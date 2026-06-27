"""AI-specific domain exceptions.

These are re-exported from ``app.core.exceptions`` so that code within the
``app.ai`` package can import them without a circular dependency, and external
callers can import from either location.
"""

from app.core.exceptions import (  # noqa: F401 – re-exported on purpose
    AIResponseError,
    AITimeoutError,
    AIUnavailableError,
)

__all__ = [
    "AITimeoutError",
    "AIUnavailableError",
    "AIResponseError",
]
