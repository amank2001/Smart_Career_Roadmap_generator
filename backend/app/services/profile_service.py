"""Concrete implementation of the ProfileService protocol."""

import uuid
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import (
    InvalidExperienceError,
    InvalidSkillCountError,
    JobTitleTooLongError,
    SkillNameTooLongError,
)
from app.models.profile import Profile as ProfileORM
from app.models.profile import Skill as SkillORM
from app.schemas.profile import (
    CreateProfileInput,
    Profile,
    Skill,
    UpdateProfileInput,
)


class ProfileService:
    """Database-backed implementation of the ProfileService protocol."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ── Validation helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _validate_create_input(data: CreateProfileInput) -> None:
        """Raise domain errors for invalid CreateProfileInput values."""
        if len(data.current_job_title) > 100:
            raise JobTitleTooLongError()
        if not (0 <= data.years_of_experience <= 50):
            raise InvalidExperienceError()
        if not (1 <= len(data.skills) <= 50):
            raise InvalidSkillCountError()
        for skill in data.skills:
            if len(skill.name) > 60:
                raise SkillNameTooLongError()

    @staticmethod
    def _validate_update_input(data: UpdateProfileInput) -> None:
        """Raise domain errors for invalid UpdateProfileInput values."""
        if data.current_job_title is not None and len(data.current_job_title) > 100:
            raise JobTitleTooLongError()
        if data.years_of_experience is not None and not (
            0 <= data.years_of_experience <= 50
        ):
            raise InvalidExperienceError()
        if data.skills is not None:
            if not (1 <= len(data.skills) <= 50):
                raise InvalidSkillCountError()
            for skill in data.skills:
                if len(skill.name) > 60:
                    raise SkillNameTooLongError()

    # ── Private DB helpers ─────────────────────────────────────────────────────

    async def _get_profile_orm(self, user_id: UUID) -> ProfileORM | None:
        """Fetch the Profile ORM row (with skills eagerly loaded) for a user."""
        result = await self._db.execute(
            select(ProfileORM)
            .where(ProfileORM.user_id == user_id)
            .options(selectinload(ProfileORM.skills))
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _orm_to_schema(profile_orm: ProfileORM) -> Profile:
        """Convert a ProfileORM instance (with skills loaded) to a Profile schema."""
        skills = [
            Skill(
                name=skill.name,
                proficiency_level=skill.proficiency_level,
            )
            for skill in profile_orm.skills
        ]
        return Profile(
            id=profile_orm.id,
            user_id=profile_orm.user_id,
            current_job_title=profile_orm.current_job_title or "",
            years_of_experience=profile_orm.years_of_experience or 0,
            skills=skills,
            is_complete=profile_orm.is_complete,
        )

    # ── Public service methods ─────────────────────────────────────────────────

    async def create_profile(self, user_id: UUID, data: CreateProfileInput) -> Profile:
        """Create a new profile and its associated skills in the database.

        Raises domain errors if validation fails.
        """
        self._validate_create_input(data)

        profile_orm = ProfileORM(
            id=uuid.uuid4(),
            user_id=user_id,
            current_job_title=data.current_job_title,
            years_of_experience=data.years_of_experience,
        )
        profile_orm.is_complete = self.is_profile_complete_from_fields(
            job_title=data.current_job_title,
            skills=data.skills,
        )

        self._db.add(profile_orm)
        # Flush to get the generated profile id before creating skills
        await self._db.flush()

        skill_orms = [
            SkillORM(
                id=uuid.uuid4(),
                profile_id=profile_orm.id,
                name=skill.name,
                proficiency_level=skill.proficiency_level,
            )
            for skill in data.skills
        ]
        for skill_orm in skill_orms:
            self._db.add(skill_orm)

        await self._db.flush()

        # Reload with skills eager-loaded to build the response schema
        refreshed = await self._get_profile_orm(user_id)
        assert refreshed is not None  # just created
        return self._orm_to_schema(refreshed)

    async def update_profile(self, user_id: UUID, data: UpdateProfileInput) -> Profile:
        """Update an existing profile's fields and replace skills when provided.

        Raises domain errors if validation fails.
        """
        self._validate_update_input(data)

        profile_orm = await self._get_profile_orm(user_id)
        if profile_orm is None:
            # Auto-create a minimal profile row when none exists yet
            profile_orm = ProfileORM(
                id=uuid.uuid4(),
                user_id=user_id,
            )
            self._db.add(profile_orm)
            await self._db.flush()
            # Re-fetch with relationships loaded
            profile_orm = await self._get_profile_orm(user_id)
            assert profile_orm is not None

        if data.current_job_title is not None:
            profile_orm.current_job_title = data.current_job_title
        if data.years_of_experience is not None:
            profile_orm.years_of_experience = data.years_of_experience

        if data.skills is not None:
            # Replace all existing skills with the new list
            for existing_skill in list(profile_orm.skills):
                await self._db.delete(existing_skill)
            await self._db.flush()

            new_skills = [
                SkillORM(
                    id=uuid.uuid4(),
                    profile_id=profile_orm.id,
                    name=skill.name,
                    proficiency_level=skill.proficiency_level,
                )
                for skill in data.skills
            ]
            for skill_orm in new_skills:
                self._db.add(skill_orm)
            await self._db.flush()

        # Recompute completeness
        current_skills = data.skills if data.skills is not None else [
            Skill(name=s.name, proficiency_level=s.proficiency_level)
            for s in profile_orm.skills
        ]
        current_title = data.current_job_title or profile_orm.current_job_title or ""
        profile_orm.is_complete = self.is_profile_complete_from_fields(
            job_title=current_title,
            skills=current_skills,
        )

        await self._db.flush()

        refreshed = await self._get_profile_orm(user_id)
        assert refreshed is not None
        return self._orm_to_schema(refreshed)

    async def get_profile(self, user_id: UUID) -> Profile | None:
        """Return the profile for a user, or None if it doesn't exist."""
        profile_orm = await self._get_profile_orm(user_id)
        if profile_orm is None:
            return None
        return self._orm_to_schema(profile_orm)

    def is_profile_complete(self, profile: Profile) -> bool:
        """Return True iff the profile has a non-empty job title and at least one skill."""
        return bool(profile.current_job_title) and len(profile.skills) >= 1

    # ── Static helper used internally without a Profile schema instance ────────

    @staticmethod
    def is_profile_complete_from_fields(job_title: str, skills: list[Skill]) -> bool:
        """Return True iff job_title is non-empty and there is at least one skill."""
        return bool(job_title) and len(skills) >= 1
