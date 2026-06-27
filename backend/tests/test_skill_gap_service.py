"""Unit tests for SkillGapService — no live database required.

Tests cover:
- analyze_gaps raises IncompleteProfileError when profile is missing or incomplete
- analyze_gaps raises NoTargetRoleError when no target role is set
- analyze_gaps returns gaps when AI identifies skill gaps
- analyze_gaps handles all_requirements_met scenario with specializations
- analyze_gaps assigns proficiency levels from AI
- get_latest_analysis returns None when no analysis exists
- get_latest_analysis returns the most recent analysis
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.provider import (
    Skill as AISkill,
    SkillGap as AISkillGap,
    SkillRequirement as AISkillRequirement,
)
from app.core.exceptions import IncompleteProfileError, NoTargetRoleError
from app.services.skill_gap_service import SkillGapService


# ── Helpers ────────────────────────────────────────────────────────────────────


def make_profile_orm(
    user_id: uuid.UUID | None = None,
    is_complete: bool = True,
    skills: list | None = None,
) -> MagicMock:
    """Create a mock ProfileORM instance."""
    profile = MagicMock()
    profile.user_id = user_id or uuid.uuid4()
    profile.is_complete = is_complete
    if skills is None:
        skill1 = MagicMock()
        skill1.name = "Python"
        skill1.proficiency_level = "intermediate"
        skill2 = MagicMock()
        skill2.name = "SQL"
        skill2.proficiency_level = "beginner"
        profile.skills = [skill1, skill2]
    else:
        profile.skills = skills
    return profile


def make_target_role_orm(
    user_id: uuid.UUID | None = None,
    role_title: str = "Senior Software Engineer",
    skill_requirements: list | None = None,
) -> MagicMock:
    """Create a mock TargetRoleORM instance."""
    role = MagicMock()
    role.user_id = user_id or uuid.uuid4()
    role.role_title = role_title
    role.is_recognized = True
    if skill_requirements is None:
        req1 = MagicMock()
        req1.skill_name = "Python"
        req1.required_proficiency = "advanced"
        req1.category = "critical"
        req2 = MagicMock()
        req2.skill_name = "System Design"
        req2.required_proficiency = "advanced"
        req2.category = "critical"
        req3 = MagicMock()
        req3.skill_name = "Docker"
        req3.required_proficiency = "intermediate"
        req3.category = "important"
        role.skill_requirements = [req1, req2, req3]
    else:
        role.skill_requirements = skill_requirements
    return role


def make_ai_gaps() -> list[AISkillGap]:
    """Create sample AI skill gaps."""
    return [
        AISkillGap(
            skill_name="System Design",
            category="critical",
            current_proficiency=None,
            required_proficiency="advanced",
        ),
        AISkillGap(
            skill_name="Docker",
            category="important",
            current_proficiency="beginner",
            required_proficiency="intermediate",
        ),
    ]


def make_analysis_orm(
    analysis_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    all_requirements_met: bool = False,
    advanced_specializations: list[str] | None = None,
    gaps: list | None = None,
) -> MagicMock:
    """Create a mock SkillGapAnalysisORM instance."""
    analysis = MagicMock()
    analysis.id = analysis_id or uuid.uuid4()
    analysis.user_id = user_id or uuid.uuid4()
    analysis.all_requirements_met = all_requirements_met
    analysis.advanced_specializations = advanced_specializations
    if gaps is None:
        gap1 = MagicMock()
        gap1.skill_name = "System Design"
        gap1.category = "critical"
        gap1.current_proficiency = None
        gap1.required_proficiency = "advanced"
        gap2 = MagicMock()
        gap2.skill_name = "Docker"
        gap2.category = "important"
        gap2.current_proficiency = "beginner"
        gap2.required_proficiency = "intermediate"
        analysis.skill_gaps = [gap1, gap2]
    else:
        analysis.skill_gaps = gaps
    return analysis


def make_service() -> tuple[SkillGapService, AsyncMock, AsyncMock]:
    """Return a SkillGapService with mock db and ai_provider."""
    mock_db = AsyncMock()
    mock_ai = AsyncMock()
    svc = SkillGapService(db=mock_db, ai_provider=mock_ai)
    return svc, mock_db, mock_ai


# ── analyze_gaps: Prerequisite Checks ──────────────────────────────────────────


class TestAnalyzeGapsPrerequisites:
    @pytest.mark.asyncio
    async def test_raises_incomplete_profile_when_profile_is_none(self) -> None:
        svc, mock_db, _ = make_service()
        # Mock the DB query to return None for the profile
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(IncompleteProfileError):
            await svc.analyze_gaps(uuid.uuid4())

    @pytest.mark.asyncio
    async def test_raises_incomplete_profile_when_profile_not_complete(self) -> None:
        svc, mock_db, _ = make_service()
        profile = make_profile_orm(is_complete=False)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = profile
        mock_db.execute.return_value = mock_result

        with pytest.raises(IncompleteProfileError):
            await svc.analyze_gaps(uuid.uuid4())

    @pytest.mark.asyncio
    async def test_raises_no_target_role_when_target_role_is_none(self) -> None:
        svc, mock_db, _ = make_service()
        user_id = uuid.uuid4()
        profile = make_profile_orm(user_id=user_id, is_complete=True)

        # First call returns profile, second returns None for target role
        mock_result_profile = MagicMock()
        mock_result_profile.scalar_one_or_none.return_value = profile
        mock_result_role = MagicMock()
        mock_result_role.scalar_one_or_none.return_value = None

        mock_db.execute.side_effect = [mock_result_profile, mock_result_role]

        with pytest.raises(NoTargetRoleError):
            await svc.analyze_gaps(user_id)


# ── analyze_gaps: Success Cases ────────────────────────────────────────────────


class TestAnalyzeGapsSuccess:
    @pytest.mark.asyncio
    async def test_returns_gaps_from_ai_analysis(self) -> None:
        svc, mock_db, mock_ai = make_service()
        user_id = uuid.uuid4()
        profile = make_profile_orm(user_id=user_id, is_complete=True)
        target_role = make_target_role_orm(user_id=user_id)
        ai_gaps = make_ai_gaps()

        # Mock DB calls: profile, target_role, flush, flush, reload analysis
        mock_result_profile = MagicMock()
        mock_result_profile.scalar_one_or_none.return_value = profile
        mock_result_role = MagicMock()
        mock_result_role.scalar_one_or_none.return_value = target_role
        analysis_orm = make_analysis_orm(user_id=user_id)
        mock_result_analysis = MagicMock()
        mock_result_analysis.scalar_one_or_none.return_value = analysis_orm

        mock_db.execute.side_effect = [
            mock_result_profile,
            mock_result_role,
            mock_result_analysis,
        ]
        mock_ai.analyze_skill_gaps.return_value = ai_gaps

        result = await svc.analyze_gaps(user_id)

        assert result.all_requirements_met is False
        assert len(result.gaps) == 2
        assert result.gaps[0].skill_name == "System Design"
        assert result.gaps[0].category == "critical"
        assert result.gaps[0].current_proficiency is None
        assert result.gaps[0].required_proficiency == "advanced"
        assert result.gaps[1].skill_name == "Docker"
        assert result.gaps[1].category == "important"
        assert result.gaps[1].current_proficiency == "beginner"
        assert result.advanced_specializations is None
        mock_ai.analyze_skill_gaps.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_returns_specializations_when_all_requirements_met(self) -> None:
        svc, mock_db, mock_ai = make_service()
        user_id = uuid.uuid4()
        profile = make_profile_orm(user_id=user_id, is_complete=True)
        target_role = make_target_role_orm(user_id=user_id, role_title="Data Engineer")

        # AI returns no gaps — all requirements met
        mock_ai.analyze_skill_gaps.return_value = []
        # AI returns specialization skills
        mock_ai.identify_role_skills.return_value = [
            AISkillRequirement(
                skill_name="Advanced Data Pipelines",
                required_proficiency="advanced",
                category="critical",
            ),
            AISkillRequirement(
                skill_name="ML Engineering",
                required_proficiency="advanced",
                category="critical",
            ),
            AISkillRequirement(
                skill_name="Stream Processing",
                required_proficiency="advanced",
                category="important",
            ),
        ]

        # Mock DB calls: profile, target_role, reload analysis
        mock_result_profile = MagicMock()
        mock_result_profile.scalar_one_or_none.return_value = profile
        mock_result_role = MagicMock()
        mock_result_role.scalar_one_or_none.return_value = target_role

        # Build analysis ORM for the reload
        analysis_orm = make_analysis_orm(
            user_id=user_id,
            all_requirements_met=True,
            advanced_specializations=[
                "Advanced Data Pipelines",
                "ML Engineering",
                "Stream Processing",
            ],
            gaps=[],
        )
        analysis_orm.skill_gaps = []
        mock_result_analysis = MagicMock()
        mock_result_analysis.scalar_one_or_none.return_value = analysis_orm

        mock_db.execute.side_effect = [
            mock_result_profile,
            mock_result_role,
            mock_result_analysis,
        ]

        result = await svc.analyze_gaps(user_id)

        assert result.all_requirements_met is True
        assert result.gaps == []
        assert result.advanced_specializations is not None
        assert len(result.advanced_specializations) >= 3
        mock_ai.identify_role_skills.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_ai_called_with_correct_skill_format(self) -> None:
        svc, mock_db, mock_ai = make_service()
        user_id = uuid.uuid4()
        profile = make_profile_orm(user_id=user_id, is_complete=True)
        target_role = make_target_role_orm(user_id=user_id)

        mock_ai.analyze_skill_gaps.return_value = make_ai_gaps()

        mock_result_profile = MagicMock()
        mock_result_profile.scalar_one_or_none.return_value = profile
        mock_result_role = MagicMock()
        mock_result_role.scalar_one_or_none.return_value = target_role
        analysis_orm = make_analysis_orm(user_id=user_id)
        mock_result_analysis = MagicMock()
        mock_result_analysis.scalar_one_or_none.return_value = analysis_orm

        mock_db.execute.side_effect = [
            mock_result_profile,
            mock_result_role,
            mock_result_analysis,
        ]

        await svc.analyze_gaps(user_id)

        # Verify the AI provider was called with properly structured data
        call_args = mock_ai.analyze_skill_gaps.call_args
        current_skills = call_args[0][0]
        target_skills = call_args[0][1]

        assert len(current_skills) == 2
        assert current_skills[0].name == "Python"
        assert current_skills[0].proficiency_level == "intermediate"

        assert len(target_skills) == 3
        assert target_skills[0].skill_name == "Python"
        assert target_skills[0].required_proficiency == "advanced"
        assert target_skills[0].category == "critical"


# ── get_latest_analysis ────────────────────────────────────────────────────────


class TestGetLatestAnalysis:
    @pytest.mark.asyncio
    async def test_returns_none_when_no_analysis_exists(self) -> None:
        svc, mock_db, _ = make_service()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await svc.get_latest_analysis(uuid.uuid4())

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_analysis_schema_when_exists(self) -> None:
        svc, mock_db, _ = make_service()
        user_id = uuid.uuid4()
        analysis_orm = make_analysis_orm(user_id=user_id)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = analysis_orm
        mock_db.execute.return_value = mock_result

        result = await svc.get_latest_analysis(user_id)

        assert result is not None
        assert result.all_requirements_met is False
        assert len(result.gaps) == 2
        assert result.gaps[0].skill_name == "System Design"
        assert result.gaps[1].skill_name == "Docker"

    @pytest.mark.asyncio
    async def test_returns_analysis_with_specializations(self) -> None:
        svc, mock_db, _ = make_service()
        user_id = uuid.uuid4()
        specializations = ["ML Engineering", "Cloud Architecture", "Data Pipelines"]
        analysis_orm = make_analysis_orm(
            user_id=user_id,
            all_requirements_met=True,
            advanced_specializations=specializations,
            gaps=[],
        )
        analysis_orm.skill_gaps = []

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = analysis_orm
        mock_db.execute.return_value = mock_result

        result = await svc.get_latest_analysis(user_id)

        assert result is not None
        assert result.all_requirements_met is True
        assert result.gaps == []
        assert result.advanced_specializations == specializations
