"""Progress Tracking Service — tracks overall progress, updates skill proficiency, provides timeline."""

from __future__ import annotations

import math
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import DomainError, NoGapAnalysisError
from app.models.profile import Profile as ProfileORM, Skill as SkillORM
from app.models.roadmap import LearningRoadmap as LearningRoadmapORM
from app.models.skill_gap import SkillGapAnalysis as SkillGapAnalysisORM, SkillGap as SkillGapORM
from app.models.weekly_plan import WeeklyPlan as WeeklyPlanORM, WeeklyTask as WeeklyTaskORM
from app.schemas.progress import ProgressSummary, TimelineEntry


class RoadmapNotFoundError(DomainError):
    error_code = "ROADMAP_NOT_FOUND"
    status_code = 404
    message = "No roadmap found for this user"


class WeeklyPlanNotFoundError(DomainError):
    error_code = "WEEKLY_PLAN_NOT_FOUND"
    status_code = 404
    message = "Weekly plan not found"


# Proficiency level hierarchy for upgrades
_PROFICIENCY_HIERARCHY = ["beginner", "intermediate", "advanced"]


class ProgressService:
    """Database-backed service for tracking learning progress."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _get_user_roadmap(self, user_id: UUID) -> LearningRoadmapORM:
        """Fetch the latest roadmap for a user with weekly plans and tasks loaded."""
        result = await self._db.execute(
            select(LearningRoadmapORM)
            .where(LearningRoadmapORM.user_id == user_id)
            .order_by(LearningRoadmapORM.created_at.desc())
            .options(
                selectinload(LearningRoadmapORM.weekly_plans).selectinload(
                    WeeklyPlanORM.tasks
                ),
            )
            .limit(1)
        )
        roadmap = result.scalar_one_or_none()
        if roadmap is None:
            raise RoadmapNotFoundError()
        return roadmap

    async def _get_user_profile(self, user_id: UUID) -> ProfileORM | None:
        """Fetch the user's profile with skills loaded."""
        result = await self._db.execute(
            select(ProfileORM)
            .where(ProfileORM.user_id == user_id)
            .options(selectinload(ProfileORM.skills))
        )
        return result.scalar_one_or_none()

    async def _get_latest_skill_gap_analysis(self, user_id: UUID) -> SkillGapAnalysisORM | None:
        """Fetch the most recent skill gap analysis for a user with gaps loaded."""
        result = await self._db.execute(
            select(SkillGapAnalysisORM)
            .where(SkillGapAnalysisORM.user_id == user_id)
            .order_by(SkillGapAnalysisORM.analyzed_at.desc())
            .options(selectinload(SkillGapAnalysisORM.skill_gaps))
            .limit(1)
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _next_proficiency(current: str | None) -> str:
        """Determine the next proficiency level up from the current level.

        If current is None or not recognized, returns 'beginner'.
        If already at 'advanced', stays at 'advanced'.
        """
        if current is None or current not in _PROFICIENCY_HIERARCHY:
            return "beginner"
        current_index = _PROFICIENCY_HIERARCHY.index(current)
        next_index = min(current_index + 1, len(_PROFICIENCY_HIERARCHY) - 1)
        return _PROFICIENCY_HIERARCHY[next_index]

    def _check_skill_gap_milestone(
        self,
        skill_name: str,
        completed_plan_skills: set[str],
        all_plans: list[WeeklyPlanORM],
    ) -> bool:
        """Check if all weekly plans associated with a skill gap are now completed.

        A skill gap milestone is fully achieved when every weekly plan that has
        tasks for that skill_name has status 'completed'.
        """
        plans_for_skill = [
            plan for plan in all_plans
            if any(task.skill_name == skill_name for task in plan.tasks)
        ]
        return all(plan.status == "completed" for plan in plans_for_skill)

    # ── Public service methods ────────────────────────────────────────────────

    async def get_overall_progress(self, user_id: UUID) -> ProgressSummary:
        """Calculate the user's overall progress through their learning roadmap.

        Progress percentage = floor(completed_plans / total_plans * 100) as integer 0-100.

        Args:
            user_id: The user's unique identifier.

        Returns:
            A ProgressSummary with percentage, completed/total counts, and acquired skills.

        Raises:
            RoadmapNotFoundError: If the user has no roadmap.
        """
        roadmap = await self._get_user_roadmap(user_id)
        plans = roadmap.weekly_plans

        total_plans = len(plans)
        if total_plans == 0:
            return ProgressSummary(
                percentage=0,
                completed_plans=0,
                total_plans=0,
                skills_acquired=[],
            )

        completed_plans = sum(1 for plan in plans if plan.status == "completed")

        # Calculate percentage: floor(completed / total * 100)
        percentage = math.floor(completed_plans / total_plans * 100)

        # Collect skills from completed plans (deduplicated, preserving order)
        skills_acquired: list[str] = []
        for plan in sorted(plans, key=lambda p: p.week_number):
            if plan.status == "completed":
                for task in plan.tasks:
                    if task.skill_name not in skills_acquired:
                        skills_acquired.append(task.skill_name)

        return ProgressSummary(
            percentage=percentage,
            completed_plans=completed_plans,
            total_plans=total_plans,
            skills_acquired=skills_acquired,
        )

    async def update_skill_proficiency(self, user_id: UUID, plan_id: UUID) -> None:
        """Update the user's skill proficiency levels when a weekly plan is completed.

        For each skill associated with the completed plan's tasks, the user's
        proficiency level is upgraded to the next level in the hierarchy
        (beginner -> intermediate -> advanced).

        Also checks if any skill gap milestones have been fully achieved and
        could trigger notifications.

        Args:
            user_id: The user's unique identifier.
            plan_id: The completed weekly plan's ID.

        Raises:
            WeeklyPlanNotFoundError: If the plan doesn't exist.
        """
        # Fetch the plan with tasks
        result = await self._db.execute(
            select(WeeklyPlanORM)
            .where(WeeklyPlanORM.id == plan_id)
            .options(selectinload(WeeklyPlanORM.tasks))
        )
        plan = result.scalar_one_or_none()
        if plan is None:
            raise WeeklyPlanNotFoundError()

        # Collect unique skill names from the plan's tasks
        skill_names: set[str] = set()
        for task in plan.tasks:
            skill_names.add(task.skill_name)

        if not skill_names:
            return

        # Get the user's profile with skills
        profile = await self._get_user_profile(user_id)
        if profile is None:
            return

        # Update proficiency for each skill in the plan
        existing_skill_names = {skill.name: skill for skill in profile.skills}

        for skill_name in skill_names:
            if skill_name in existing_skill_names:
                # Upgrade existing skill proficiency
                skill_orm = existing_skill_names[skill_name]
                skill_orm.proficiency_level = self._next_proficiency(
                    skill_orm.proficiency_level
                )
            else:
                # Add new skill at beginner level
                new_skill = SkillORM(
                    profile_id=profile.id,
                    name=skill_name,
                    proficiency_level="beginner",
                )
                self._db.add(new_skill)

        await self._db.flush()

        # Check skill gap milestone completion and notify
        roadmap = await self._get_user_roadmap(user_id)
        all_plans = roadmap.weekly_plans
        analysis = await self._get_latest_skill_gap_analysis(user_id)

        if analysis is not None:
            for gap in analysis.skill_gaps:
                if self._check_skill_gap_milestone(gap.skill_name, skill_names, all_plans):
                    # Milestone achieved for this skill gap.
                    # In a full implementation, this would emit an event or
                    # create a notification record. For now, this check confirms
                    # the milestone is recognized by the service.
                    pass

    async def get_timeline(self, user_id: UUID) -> list[TimelineEntry]:
        """Get the timeline showing each weekly plan's status and associated skills.

        Returns a list of TimelineEntry objects ordered by week number, each
        showing the plan's status (completed, in-progress, upcoming) and skills.

        Args:
            user_id: The user's unique identifier.

        Returns:
            A list of TimelineEntry objects.

        Raises:
            RoadmapNotFoundError: If the user has no roadmap.
        """
        roadmap = await self._get_user_roadmap(user_id)
        plans = sorted(roadmap.weekly_plans, key=lambda p: p.week_number)

        timeline: list[TimelineEntry] = []
        for plan in plans:
            # Collect unique skills for this plan
            skills: list[str] = []
            for task in plan.tasks:
                if task.skill_name not in skills:
                    skills.append(task.skill_name)

            timeline.append(
                TimelineEntry(
                    week_number=plan.week_number,
                    plan_id=plan.id,
                    status=plan.status,
                    skills=skills,
                )
            )

        return timeline
