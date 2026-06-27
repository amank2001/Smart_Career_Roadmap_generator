"""Unit tests for TargetRoleService — no live database required.

Tests cover:
- Role title validation
- Custom role validation
- set_target_role with recognized and unrecognized roles
- get_target_role_requirements
- update_target_role_skills
- is_role_recognized
- set_custom_role
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import (
    InvalidCustomRoleError,
    InvalidRoleTitleError,
    NoTargetRoleError,
)
from app.schemas.target_role import (
    CustomRoleInput,
    SkillRequirement as SkillRequirementSchema,
)
from app.services.target_role_service import TargetRoleService


# ── Helpers ────────────────────────────────────────────────────────────────────


def make_skill(
    name: str = "Python",
    proficiency: str = "intermediate",
    category: str = "critical",
) -> SkillRequirementSchema:
    return SkillRequirementSchema(
        skill_name=name,
        required_proficiency=proficiency,
        category=category,
    )


def make_ai_skills(count: int = 5) -> list[SkillRequirementSchema]:
    """Generate a list of skill requirements from the AI provider."""
    skills = [
        ("Python", "advanced", "critical"),
        ("FastAPI", "intermediate", "critical"),
        ("PostgreSQL", "intermediate", "important"),
        ("Docker", "beginner", "important"),
        ("AWS", "beginner", "nice-to-have"),
        ("Kubernetes", "intermediate", "nice-to-have"),
        ("Redis", "beginner", "nice-to-have"),
    ]
    return [
        SkillRequirementSchema(
            skill_name=name,
            required_proficiency=prof,
            category=cat,
        )
        for name, prof, cat in skills[:count]
    ]


def make_service() -> tuple[TargetRoleService, AsyncMock, AsyncMock]:
    """Return a TargetRoleService with mock db and ai_provider."""
    mock_db = AsyncMock()
    mock_ai = AsyncMock()
    svc = TargetRoleService(db=mock_db, ai_provider=mock_ai)
    return svc, mock_db, mock_ai


# ── Role Title Validation ──────────────────────────────────────────────────────


class TestRoleTitleValidation:
    def test_empty_title_raises(self) -> None:
        with pytest.raises(InvalidRoleTitleError):
            TargetRoleService._validate_role_title("")

    def test_whitespace_only_title_raises(self) -> None:
        with pytest.raises(InvalidRoleTitleError):
            TargetRoleService._validate_role_title("   ")

    def test_title_over_100_chars_raises(self) -> None:
        with pytest.raises(InvalidRoleTitleError):
            TargetRoleService._validate_role_title("A" * 101)

    def test_title_exactly_100_chars_passes(self) -> None:
        # Should not raise
        TargetRoleService._validate_role_title("A" * 100)

    def test_valid_title_passes(self) -> None:
        # Should not raise
        TargetRoleService._validate_role_title("Senior Software Engineer")

    def test_single_char_title_passes(self) -> None:
        # Should not raise
        TargetRoleService._validate_role_title("A")


# ── Custom Role Validation ─────────────────────────────────────────────────────


class TestCustomRoleValidation:
    def test_fewer_than_3_skills_raises(self) -> None:
        data = CustomRoleInput.model_construct(
            role_title="Custom Role",
            skills=[make_skill(), make_skill("JS")],
            responsibilities="Build things",
        )
        with pytest.raises(InvalidCustomRoleError):
            TargetRoleService._validate_custom_role_input(data)

    def test_empty_responsibilities_raises(self) -> None:
        data = CustomRoleInput.model_construct(
            role_title="Custom Role",
            skills=[make_skill(), make_skill("JS"), make_skill("Go")],
            responsibilities="",
        )
        with pytest.raises(InvalidCustomRoleError):
            TargetRoleService._validate_custom_role_input(data)

    def test_whitespace_only_responsibilities_raises(self) -> None:
        data = CustomRoleInput.model_construct(
            role_title="Custom Role",
            skills=[make_skill(), make_skill("JS"), make_skill("Go")],
            responsibilities="   ",
        )
        with pytest.raises(InvalidCustomRoleError):
            TargetRoleService._validate_custom_role_input(data)

    def test_valid_custom_role_passes(self) -> None:
        data = CustomRoleInput.model_construct(
            role_title="Custom Role",
            skills=[make_skill(), make_skill("JS"), make_skill("Go")],
            responsibilities="Build and maintain systems",
        )
        # Should not raise
        TargetRoleService._validate_custom_role_input(data)


# ── is_role_recognized ─────────────────────────────────────────────────────────


class TestIsRoleRecognized:
    @pytest.mark.asyncio
    async def test_returns_true_when_5_or_more_skills(self) -> None:
        svc, _, mock_ai = make_service()
        mock_ai.identify_role_skills.return_value = make_ai_skills(5)

        result = await svc.is_role_recognized("Software Engineer")

        assert result is True
        mock_ai.identify_role_skills.assert_awaited_once_with("Software Engineer")

    @pytest.mark.asyncio
    async def test_returns_true_when_more_than_5_skills(self) -> None:
        svc, _, mock_ai = make_service()
        mock_ai.identify_role_skills.return_value = make_ai_skills(7)

        result = await svc.is_role_recognized("DevOps Engineer")

        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_when_fewer_than_5_skills(self) -> None:
        svc, _, mock_ai = make_service()
        mock_ai.identify_role_skills.return_value = make_ai_skills(3)

        result = await svc.is_role_recognized("Obscure Role")

        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_when_no_skills(self) -> None:
        svc, _, mock_ai = make_service()
        mock_ai.identify_role_skills.return_value = []

        result = await svc.is_role_recognized("Nonexistent Role")

        assert result is False
