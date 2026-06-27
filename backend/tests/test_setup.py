"""Smoke tests that verify the project is correctly initialised.

These tests do not require a running database or external services.
"""

import importlib

import pytest
from hypothesis import given, settings as h_settings
from hypothesis import strategies as st


# ── Import sanity checks ───────────────────────────────────────────────────────

def test_fastapi_app_importable() -> None:
    """The FastAPI app factory must be importable without errors."""
    module = importlib.import_module("app.main")
    assert hasattr(module, "app"), "app.main must expose an 'app' object"


def test_settings_importable() -> None:
    """Settings must load without errors (uses defaults when .env absent)."""
    from app.core.config import settings  # noqa: F401

    assert settings.jwt_algorithm == "HS256"


def test_exception_classes_importable() -> None:
    """Domain exception classes must be importable."""
    from app.core.exceptions import (  # noqa: F401
        IncompleteProfileError,
        NoTargetRoleError,
        NoGapAnalysisError,
        UnsupportedFormatError,
        FileTooLargeError,
    )


# ── Hypothesis smoke test ──────────────────────────────────────────────────────

@h_settings(max_examples=20)
@given(st.integers())
def test_hypothesis_framework_works(n: int) -> None:
    """Verify that Hypothesis is properly installed and runnable."""
    assert isinstance(n, int)
