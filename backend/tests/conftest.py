"""Shared pytest fixtures and configuration."""

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.fixture
async def client() -> AsyncClient:  # type: ignore[return]
    """Async test client for the FastAPI app (no live DB needed for unit tests)."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
