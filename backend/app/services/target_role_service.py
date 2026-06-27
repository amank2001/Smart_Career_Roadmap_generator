"""Target Role Service — manages target role selection, skill requirements, and custom roles."""

import uuid
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.provider import AIProvider
from app.core.exceptions import (
    InvalidCustomRoleError,
    InvalidRoleTitleError,
    NoTargetRoleError,
)
from app.models.target_role import SkillRequirement as SkillRequirementORM
from app.models.target_role import TargetRole as TargetRoleORM
from app.schemas.target_role import (
    CustomRoleInput,
    SkillRequirement as SkillRequirementSchema,
    TargetRole as TargetRoleSchema,
    TargetRoleRequirements,
)


class TargetRoleService:
    """Database-backed service for target role management."""

    def __init__(self, db: AsyncSession, ai_provider: AIProvider) -> None:
        self._db = db
        self._ai_provider = ai_provider

    # ── Validation helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _validate_role_title(role_title: str) -> None:
        """Raise InvalidRoleTitleError if role title is empty or exceeds 100 chars."""
        if not role_title or not role_title.strip() or len(role_title) > 100:
            raise InvalidRoleTitleError()

    @staticmethod
    def _validate_custom_role_input(data: CustomRoleInput) -> None:
        """Raise InvalidCustomRoleError if custom role input is invalid."""
        if len(data.skills) < 3 or not data.responsibilities.strip():
            raise InvalidCustomRoleError()

    # ── Private DB helpers ─────────────────────────────────────────────────────

    async def _get_target_role_orm(self, user_id: UUID) -> TargetRoleORM | None:
        """Fetch the TargetRole ORM row (with skills eagerly loaded) for a user."""
        result = await self._db.execute(
            select(TargetRoleORM)
            .where(TargetRoleORM.user_id == user_id)
            .options(selectinload(TargetRoleORM.skill_requirements))
        )
        return result.scalar_one_or_none()

    async def _delete_existing_target_role(self, user_id: UUID) -> None:
        """Delete any existing target role for the user (one per user constraint)."""
        existing = await self._get_target_role_orm(user_id)
        if existing is not None:
            await self._db.delete(existing)
            await self._db.flush()

    @staticmethod
    def _orm_to_schema(target_role_orm: TargetRoleORM) -> TargetRoleSchema:
        """Convert a TargetRoleORM instance to a TargetRole Pydantic schema."""
        skills = [
            SkillRequirementSchema(
                skill_name=sr.skill_name,
                required_proficiency=sr.required_proficiency,
                category=sr.category,
            )
            for sr in target_role_orm.skill_requirements
        ]
        return TargetRoleSchema(
            id=target_role_orm.id,
            user_id=target_role_orm.user_id,
            role_title=target_role_orm.role_title,
            is_recognized=target_role_orm.is_recognized,
            skills=skills,
        )

    # ── Public service methods ─────────────────────────────────────────────────

    async def set_target_role(self, user_id: UUID, role_title: str) -> TargetRoleSchema:
        """Set a recognized target role by querying the AI provider for skills.

        If the AI returns fewer than 5 skills, the role is marked as unrecognized
        but still saved with whatever skills were returned.

        Raises:
            InvalidRoleTitleError: If role title is empty or exceeds 100 characters.
        """
        self._validate_role_title(role_title)

        # Query AI provider for the role's required skills
        ai_skills = await self._ai_provider.identify_role_skills(role_title)

        is_recognized = len(ai_skills) >= 5

        # Delete any existing target role for this user
        await self._delete_existing_target_role(user_id)

        # Create new target role
        target_role_orm = TargetRoleORM(
            id=uuid.uuid4(),
            user_id=user_id,
            role_title=role_title,
            is_recognized=is_recognized,
        )
        self._db.add(target_role_orm)
        await self._db.flush()

        # Create skill requirement records
        for skill in ai_skills:
            skill_orm = SkillRequirementORM(
                id=uuid.uuid4(),
                target_role_id=target_role_orm.id,
                skill_name=skill.skill_name,
                required_proficiency=skill.required_proficiency,
                category=skill.category,
            )
            self._db.add(skill_orm)

        await self._db.flush()

        # Reload with relationships
        refreshed = await self._get_target_role_orm(user_id)
        assert refreshed is not None
        return self._orm_to_schema(refreshed)

    async def preview_role_requirements(self, role_title: str) -> TargetRoleRequirements:
        """Query the AI for a role's skill requirements without saving anything.

        Used by the frontend to preview a role before the user commits to it.

        Raises:
            InvalidRoleTitleError: If role title is empty or exceeds 100 characters.
        """
        self._validate_role_title(role_title)

        ai_skills = await self._ai_provider.identify_role_skills(role_title)
        is_recognized = len(ai_skills) >= 5

        skills = [
            SkillRequirementSchema(
                skill_name=skill.skill_name,
                required_proficiency=skill.required_proficiency,
                category=skill.category,
            )
            for skill in ai_skills
        ]

        return TargetRoleRequirements(
            role_title=role_title,
            skills=skills,
            recognized=is_recognized,
        )

    async def get_target_role_requirements(
        self, user_id: UUID
    ) -> TargetRoleRequirements:
        """Return the user's current target role requirements.

        Raises:
            NoTargetRoleError: If the user has no target role set.
        """
        target_role_orm = await self._get_target_role_orm(user_id)
        if target_role_orm is None:
            raise NoTargetRoleError()

        skills = [
            SkillRequirementSchema(
                skill_name=sr.skill_name,
                required_proficiency=sr.required_proficiency,
                category=sr.category,
            )
            for sr in target_role_orm.skill_requirements
        ]

        return TargetRoleRequirements(
            role_title=target_role_orm.role_title,
            skills=skills,
            recognized=target_role_orm.is_recognized,
        )

    async def update_target_role_skills(
        self, user_id: UUID, skills: list[SkillRequirementSchema]
    ) -> TargetRoleSchema:
        """Replace all skill requirements for the user's current target role.

        Raises:
            NoTargetRoleError: If the user has no target role set.
        """
        target_role_orm = await self._get_target_role_orm(user_id)
        if target_role_orm is None:
            raise NoTargetRoleError()

        # Delete existing skill requirements
        for existing_skill in list(target_role_orm.skill_requirements):
            await self._db.delete(existing_skill)
        await self._db.flush()

        # Create new skill requirement records
        for skill in skills:
            skill_orm = SkillRequirementORM(
                id=uuid.uuid4(),
                target_role_id=target_role_orm.id,
                skill_name=skill.skill_name,
                required_proficiency=skill.required_proficiency,
                category=skill.category,
            )
            self._db.add(skill_orm)

        await self._db.flush()

        # Reload with relationships
        refreshed = await self._get_target_role_orm(user_id)
        assert refreshed is not None
        return self._orm_to_schema(refreshed)

    async def is_role_recognized(self, role_title: str) -> bool:
        """Check if a role is recognized by querying the AI provider.

        Returns True if the AI provider returns at least 5 skills for the role.
        """
        ai_skills = await self._ai_provider.identify_role_skills(role_title)
        return len(ai_skills) >= 5

    async def set_custom_role(
        self, user_id: UUID, data: CustomRoleInput
    ) -> TargetRoleSchema:
        """Set a custom (unrecognized) target role with user-provided skills.

        Raises:
            InvalidRoleTitleError: If role title is empty or exceeds 100 characters.
            InvalidCustomRoleError: If fewer than 3 skills or empty responsibilities.
        """
        self._validate_role_title(data.role_title)
        self._validate_custom_role_input(data)

        # Delete any existing target role for this user
        await self._delete_existing_target_role(user_id)

        # Create new target role marked as unrecognized
        target_role_orm = TargetRoleORM(
            id=uuid.uuid4(),
            user_id=user_id,
            role_title=data.role_title,
            is_recognized=False,
            responsibilities=data.responsibilities,
        )
        self._db.add(target_role_orm)
        await self._db.flush()

        # Create skill requirement records from user-provided skills
        for skill in data.skills:
            skill_orm = SkillRequirementORM(
                id=uuid.uuid4(),
                target_role_id=target_role_orm.id,
                skill_name=skill.skill_name,
                required_proficiency=skill.required_proficiency,
                category=skill.category,
            )
            self._db.add(skill_orm)

        await self._db.flush()

        # Reload with relationships
        refreshed = await self._get_target_role_orm(user_id)
        assert refreshed is not None
        return self._orm_to_schema(refreshed)
