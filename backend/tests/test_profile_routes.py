"""Integration tests for Profile API endpoints.

Tests use FastAPI's TestClient (sync) with mocked services injected
via app dependency overrides. No live database or AI provider required.
"""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.core.exceptions import (
    ExtractionFailedError,
    FileTooLargeError,
    UnsupportedFormatError,
)
from app.main import app
from app.schemas.profile import Profile, Skill
from app.services.protocols import ResumeAnalysisResultModel, UploadedFile

# ── Helpers ────────────────────────────────────────────────────────────────────

FAKE_USER_ID = uuid.uuid4()
FAKE_PROFILE_ID = uuid.uuid4()


def _make_profile(**overrides: Any) -> Profile:
    defaults: dict[str, Any] = dict(
        id=FAKE_PROFILE_ID,
        user_id=FAKE_USER_ID,
        current_job_title="Software Engineer",
        years_of_experience=5,
        skills=[Skill(name="Python"), Skill(name="FastAPI")],
        is_complete=True,
    )
    defaults.update(overrides)
    return Profile(**defaults)


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_profile_service() -> MagicMock:
    """Return a MagicMock that satisfies the ProfileService interface."""
    svc = MagicMock()
    svc.create_profile = AsyncMock(return_value=_make_profile())
    svc.update_profile = AsyncMock(return_value=_make_profile())
    svc.get_profile = AsyncMock(return_value=_make_profile())
    return svc


@pytest.fixture
def mock_resume_analyzer() -> MagicMock:
    """Return a MagicMock that satisfies the ResumeAnalyzerService interface."""
    svc = MagicMock()
    svc.analyze_resume = AsyncMock(
        return_value=ResumeAnalysisResultModel(
            success=True,
            extracted_data={
                "skills": ["Python", "FastAPI"],
                "job_history": [{"title": "Dev", "company": "Acme", "years": 3}],
                "years_of_experience": 5,
            },
        )
    )
    return svc


@pytest.fixture
def authenticated_client(mock_profile_service: MagicMock, mock_resume_analyzer: MagicMock) -> TestClient:
    """TestClient with auth, DB, and service dependencies all overridden."""
    from app.api.deps import get_current_user_id
    from app.api.routes.profile import get_profile_service, get_resume_analyzer_service
    from app.core.database import get_db

    async def _fake_user_id() -> uuid.UUID:
        return FAKE_USER_ID

    async def _fake_db():  # type: ignore[return]
        yield MagicMock()

    app.dependency_overrides[get_current_user_id] = _fake_user_id
    app.dependency_overrides[get_db] = _fake_db
    app.dependency_overrides[get_profile_service] = lambda: mock_profile_service
    app.dependency_overrides[get_resume_analyzer_service] = lambda: mock_resume_analyzer

    yield TestClient(app)

    app.dependency_overrides.clear()


# ── POST /api/profile — create profile ────────────────────────────────────────

class TestCreateProfile:
    def test_happy_path_returns_200_with_profile(
        self, authenticated_client: TestClient, mock_profile_service: MagicMock
    ) -> None:
        payload = {
            "current_job_title": "Software Engineer",
            "years_of_experience": 5,
            "skills": [{"name": "Python"}, {"name": "FastAPI"}],
        }
        response = authenticated_client.post("/api/profile", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["current_job_title"] == "Software Engineer"
        assert data["years_of_experience"] == 5
        assert len(data["skills"]) == 2
        assert data["is_complete"] is True
        mock_profile_service.create_profile.assert_awaited_once()

    def test_missing_skills_returns_422(self, authenticated_client: TestClient) -> None:
        payload = {
            "current_job_title": "Engineer",
            "years_of_experience": 3,
            # "skills" is intentionally omitted
        }
        response = authenticated_client.post("/api/profile", json=payload)
        assert response.status_code == 422

    def test_empty_skills_list_returns_422(self, authenticated_client: TestClient) -> None:
        payload = {
            "current_job_title": "Engineer",
            "years_of_experience": 3,
            "skills": [],
        }
        response = authenticated_client.post("/api/profile", json=payload)
        assert response.status_code == 422

    def test_negative_experience_returns_422(self, authenticated_client: TestClient) -> None:
        payload = {
            "current_job_title": "Engineer",
            "years_of_experience": -1,
            "skills": [{"name": "Python"}],
        }
        response = authenticated_client.post("/api/profile", json=payload)
        assert response.status_code == 422

    def test_job_title_too_long_returns_422(self, authenticated_client: TestClient) -> None:
        payload = {
            "current_job_title": "A" * 101,
            "years_of_experience": 5,
            "skills": [{"name": "Python"}],
        }
        response = authenticated_client.post("/api/profile", json=payload)
        assert response.status_code == 422


# ── PUT /api/profile — update profile ─────────────────────────────────────────

class TestUpdateProfile:
    def test_happy_path_returns_200_with_profile(
        self, authenticated_client: TestClient, mock_profile_service: MagicMock
    ) -> None:
        payload = {"current_job_title": "Senior Engineer"}
        response = authenticated_client.put("/api/profile", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["current_job_title"] == "Software Engineer"  # from mock
        mock_profile_service.update_profile.assert_awaited_once()

    def test_empty_body_is_valid_partial_update(
        self, authenticated_client: TestClient, mock_profile_service: MagicMock
    ) -> None:
        """All fields are optional in UpdateProfileInput."""
        response = authenticated_client.put("/api/profile", json={})
        assert response.status_code == 200
        mock_profile_service.update_profile.assert_awaited_once()

    def test_invalid_experience_returns_422(self, authenticated_client: TestClient) -> None:
        payload = {"years_of_experience": 999}
        response = authenticated_client.put("/api/profile", json=payload)
        assert response.status_code == 422


# ── GET /api/profile — get profile ────────────────────────────────────────────

class TestGetProfile:
    def test_returns_200_when_profile_exists(
        self, authenticated_client: TestClient, mock_profile_service: MagicMock
    ) -> None:
        response = authenticated_client.get("/api/profile")

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == str(FAKE_USER_ID)
        assert data["current_job_title"] == "Software Engineer"
        mock_profile_service.get_profile.assert_awaited_once()

    def test_returns_404_when_no_profile(
        self, authenticated_client: TestClient, mock_profile_service: MagicMock
    ) -> None:
        mock_profile_service.get_profile = AsyncMock(return_value=None)
        response = authenticated_client.get("/api/profile")

        assert response.status_code == 404

    def test_returns_correct_skills(
        self, authenticated_client: TestClient
    ) -> None:
        response = authenticated_client.get("/api/profile")
        data = response.json()
        skill_names = [s["name"] for s in data["skills"]]
        assert "Python" in skill_names
        assert "FastAPI" in skill_names


# ── POST /api/profile/resume — upload resume ──────────────────────────────────

class TestUploadResume:
    def test_success_returns_200_with_extracted_data(
        self, authenticated_client: TestClient, mock_resume_analyzer: MagicMock
    ) -> None:
        content = b"Jane Doe\nSoftware Engineer\nPython, FastAPI"
        response = authenticated_client.post(
            "/api/profile/resume",
            files={"file": ("resume.txt", content, "text/plain")},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "extracted_data" in data
        assert "skills" in data["extracted_data"]
        mock_resume_analyzer.analyze_resume.assert_awaited_once()

    def test_extracted_data_not_saved_to_profile(
        self,
        authenticated_client: TestClient,
        mock_profile_service: MagicMock,
    ) -> None:
        """The resume endpoint must NOT call profile service — user must confirm first."""
        content = b"Resume text"
        authenticated_client.post(
            "/api/profile/resume",
            files={"file": ("resume.txt", content, "text/plain")},
        )
        mock_profile_service.create_profile.assert_not_awaited()
        mock_profile_service.update_profile.assert_not_awaited()

    def test_unsupported_format_returns_415(
        self,
        authenticated_client: TestClient,
        mock_resume_analyzer: MagicMock,
    ) -> None:
        mock_resume_analyzer.analyze_resume = AsyncMock(side_effect=UnsupportedFormatError())
        content = b"<html>not a resume</html>"
        response = authenticated_client.post(
            "/api/profile/resume",
            files={"file": ("resume.html", content, "text/html")},
        )
        assert response.status_code == 415

    def test_file_too_large_returns_413(
        self,
        authenticated_client: TestClient,
        mock_resume_analyzer: MagicMock,
    ) -> None:
        mock_resume_analyzer.analyze_resume = AsyncMock(side_effect=FileTooLargeError())
        # Simulate large file content
        content = b"x" * 100
        response = authenticated_client.post(
            "/api/profile/resume",
            files={"file": ("big_resume.pdf", content, "application/pdf")},
        )
        assert response.status_code == 413

    def test_extraction_failed_returns_422(
        self,
        authenticated_client: TestClient,
        mock_resume_analyzer: MagicMock,
    ) -> None:
        mock_resume_analyzer.analyze_resume = AsyncMock(side_effect=ExtractionFailedError())
        content = b""
        response = authenticated_client.post(
            "/api/profile/resume",
            files={"file": ("corrupt.pdf", content, "application/pdf")},
        )
        assert response.status_code == 422
