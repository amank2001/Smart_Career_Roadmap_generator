"""Skill Gap Analyzer Service — compares user skills against target role requirements."""

import uuid
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.provider import (
    AIProvider,
    Skill as AISkill,
    SkillGap as AISkillGap,
    SkillRequirement as AISkillRequirement,
)
from app.core.exceptions import IncompleteProfileError, NoTargetRoleError
from app.models.profile import Profile as ProfileORM
from app.models.skill_gap import SkillGap as SkillGapORM
from app.models.skill_gap import SkillGapAnalysis as SkillGapAnalysisORM
from app.models.target_role import TargetRole as TargetRoleORM
from app.schemas.skill_gap import SkillGap, SkillGapAnalysis


class SkillGapService:
    """Database-backed service for skill gap analysis."""

    def __init__(self, db: AsyncSession, ai_provider: AIProvider) -> None:
        self._db = db
        self._ai_provider = ai_provider

    # ── Private DB helpers ─────────────────────────────────────────────────────

    async def _get_profile(self, user_id: UUID) -> ProfileORM | None:
        """Fetch the Profile ORM row (with skills eagerly loaded) for a user."""
        result = await self._db.execute(
            select(ProfileORM)
            .where(ProfileORM.user_id == user_id)
            .options(selectinload(ProfileORM.skills))
        )
        return result.scalar_one_or_none()

    async def _get_target_role(self, user_id: UUID) -> TargetRoleORM | None:
        """Fetch the TargetRole ORM row (with skill_requirements loaded) for a user."""
        result = await self._db.execute(
            select(TargetRoleORM)
            .where(TargetRoleORM.user_id == user_id)
            .options(selectinload(TargetRoleORM.skill_requirements))
        )
        return result.scalar_one_or_none()

    async def _get_analysis_orm(self, analysis_id: UUID) -> SkillGapAnalysisORM | None:
        """Fetch a SkillGapAnalysis by ID with skill_gaps loaded."""
        result = await self._db.execute(
            select(SkillGapAnalysisORM)
            .where(SkillGapAnalysisORM.id == analysis_id)
            .options(selectinload(SkillGapAnalysisORM.skill_gaps))
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _analysis_orm_to_schema(analysis_orm: SkillGapAnalysisORM) -> SkillGapAnalysis:
        """Convert a SkillGapAnalysisORM instance to a SkillGapAnalysis schema."""
        gaps = [
            SkillGap(
                skill_name=gap.skill_name,
                category=gap.category,
                current_proficiency=gap.current_proficiency,
                required_proficiency=gap.required_proficiency,
            )
            for gap in analysis_orm.skill_gaps
        ]
        return SkillGapAnalysis(
            gaps=gaps,
            all_requirements_met=analysis_orm.all_requirements_met,
            advanced_specializations=analysis_orm.advanced_specializations,
        )

    # ── Public service methods ─────────────────────────────────────────────────

    async def analyze_gaps(self, user_id: UUID) -> SkillGapAnalysis:
        """Run skill gap analysis for a user.

        Compares the user's current skills against their target role requirements
        using AI analysis. Persists the result and returns it.

        Raises:
            IncompleteProfileError: If profile is None or not complete.
            NoTargetRoleError: If no target role is selected.
        """
        # Check prerequisite: profile must be complete
        profile = await self._get_profile(user_id)
        if profile is None or not profile.is_complete:
            raise IncompleteProfileError()

        # Check prerequisite: target role must be selected
        target_role = await self._get_target_role(user_id)
        if target_role is None:
            raise NoTargetRoleError()

        # Build AI input from ORM models
        current_skills = [
            AISkill(
                name=skill.name,
                proficiency_level=skill.proficiency_level,
            )
            for skill in profile.skills
        ]

        target_skills = [
            AISkillRequirement(
                skill_name=req.skill_name,
                required_proficiency=req.required_proficiency,
                category=req.category,
            )
            for req in target_role.skill_requirements
        ]

        # Call AI to analyze gaps
        ai_gaps: list[AISkillGap] = await self._ai_provider.analyze_skill_gaps(
            current_skills, target_skills
        )

        # Determine if all requirements are met
        all_requirements_met = len(ai_gaps) == 0
        advanced_specializations: list[str] | None = None

        # If all requirements met, suggest advanced specialization areas
        if all_requirements_met:
            # Use identify_role_skills to derive specialization areas from the role
            specialization_skills = await self._ai_provider.identify_role_skills(
                f"Senior {target_role.role_title} Specialist"
            )
            # Extract unique skill names as specialization suggestions
            specializations = [
                skill.skill_name for skill in specialization_skills
            ]
            # Ensure at least 3 specializations
            if len(specializations) < 3:
                # Fallback: add generic advanced areas based on target role
                fallback_areas = [
                    f"Advanced {target_role.role_title} Architecture",
                    f"{target_role.role_title} Team Leadership",
                    f"{target_role.role_title} Performance Optimization",
                ]
                for area in fallback_areas:
                    if area not in specializations:
                        specializations.append(area)
                    if len(specializations) >= 3:
                        break
            advanced_specializations = specializations[:6]  # Cap at a reasonable number

        # Persist the analysis to database
        analysis_orm = SkillGapAnalysisORM(
            id=uuid.uuid4(),
            user_id=user_id,
            all_requirements_met=all_requirements_met,
            advanced_specializations=advanced_specializations,
        )
        self._db.add(analysis_orm)
        await self._db.flush()

        # Persist individual skill gaps
        for gap in ai_gaps:
            gap_orm = SkillGapORM(
                id=uuid.uuid4(),
                analysis_id=analysis_orm.id,
                skill_name=gap.skill_name,
                category=gap.category,
                current_proficiency=gap.current_proficiency,
                required_proficiency=gap.required_proficiency,
            )
            self._db.add(gap_orm)

        await self._db.flush()

        # Reload with relationships and return schema
        refreshed = await self._get_analysis_orm(analysis_orm.id)
        assert refreshed is not None
        return self._analysis_orm_to_schema(refreshed)

    async def get_latest_analysis(self, user_id: UUID) -> SkillGapAnalysis | None:
        """Fetch the most recent skill gap analysis for the user.

        Returns None if no analysis exists for the user.
        """
        result = await self._db.execute(
            select(SkillGapAnalysisORM)
            .where(SkillGapAnalysisORM.user_id == user_id)
            .order_by(SkillGapAnalysisORM.analyzed_at.desc())
            .options(selectinload(SkillGapAnalysisORM.skill_gaps))
            .limit(1)
        )
        analysis_orm = result.scalar_one_or_none()
        if analysis_orm is None:
            return None
        return self._analysis_orm_to_schema(analysis_orm)
