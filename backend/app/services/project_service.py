"""Project Suggester Service — suggests hands-on projects and manages completion."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.provider import AIProvider
from app.core.exceptions import OutcomeTooLongError, ProjectNotFoundError
from app.models.project import ProjectSuggestion as ProjectSuggestionORM
from app.models.weekly_plan import WeeklyPlan as WeeklyPlanORM
from app.schemas.common import ProficiencyLevel
from app.schemas.project import ProjectSuggestion as ProjectSuggestionSchema


# Maximum allowed length for a project outcome description.
_MAX_OUTCOME_LENGTH = 500


class ProjectSuggesterService:
    """Database-backed service for project suggestions and completion tracking."""

    def __init__(self, db: AsyncSession, ai_provider: AIProvider) -> None:
        self._db = db
        self._ai_provider = ai_provider

    # ── ORM to schema conversion ──────────────────────────────────────────────

    @staticmethod
    def _project_orm_to_schema(project_orm: ProjectSuggestionORM) -> ProjectSuggestionSchema:
        """Convert a ProjectSuggestionORM instance to a ProjectSuggestion schema."""
        return ProjectSuggestionSchema(
            id=project_orm.id,
            title=project_orm.title,
            objectives=project_orm.objectives,
            deliverables=project_orm.deliverables,
            technologies=project_orm.technologies,
            estimated_weeks=project_orm.estimated_weeks,
            complexity=project_orm.complexity,
            completed=project_orm.completed,
            outcome_description=project_orm.outcome_description,
            dismissed=project_orm.dismissed,
        )

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _get_project(self, project_id: UUID) -> ProjectSuggestionORM:
        """Fetch a project suggestion by ID.

        Raises:
            ProjectNotFoundError: If the project doesn't exist.
        """
        result = await self._db.execute(
            select(ProjectSuggestionORM).where(ProjectSuggestionORM.id == project_id)
        )
        project = result.scalar_one_or_none()
        if project is None:
            raise ProjectNotFoundError()
        return project

    def _extract_skills_from_plan(self, plan: WeeklyPlanORM) -> list[str]:
        """Extract unique skill names from a weekly plan's tasks."""
        skills: list[str] = []
        for task in plan.tasks:
            if task.skill_name and task.skill_name not in skills:
                skills.append(task.skill_name)
        return skills

    async def _fetch_career_context(self, user_id: UUID) -> tuple[str | None, str | None]:
        """Fetch the user's current job title and target role title.

        Returns:
            A tuple of (current_role, target_role) — either may be None.
        """
        from app.models.profile import Profile as ProfileORM
        from app.models.target_role import TargetRole as TargetRoleORM

        current_role: str | None = None
        target_role: str | None = None

        # Get current job title from profile
        profile_result = await self._db.execute(
            select(ProfileORM).where(ProfileORM.user_id == user_id)
        )
        profile = profile_result.scalar_one_or_none()
        if profile and profile.current_job_title:
            current_role = profile.current_job_title

        # Get target role title
        target_result = await self._db.execute(
            select(TargetRoleORM)
            .where(TargetRoleORM.user_id == user_id)
            .order_by(TargetRoleORM.created_at.desc())
            .limit(1)
        )
        target = target_result.scalar_one_or_none()
        if target:
            target_role = target.role_title

        return current_role, target_role

    # ── Public service methods ────────────────────────────────────────────────

    async def get_best_plan_id_for_user(self, user_id: UUID) -> UUID | None:
        """Return the most appropriate plan ID to use for project suggestions.

        Prefers the current in-progress plan. Falls back to the first
        upcoming plan, then the most recently completed plan.

        Returns None if the user has no weekly plans at all.
        """
        from app.models.roadmap import LearningRoadmap as LearningRoadmapORM
        from app.models.weekly_plan import WeeklyPlan as WeeklyPlanORM
        from sqlalchemy.orm import selectinload

        # Get the user's latest roadmap
        roadmap_result = await self._db.execute(
            select(LearningRoadmapORM)
            .where(LearningRoadmapORM.user_id == user_id)
            .order_by(LearningRoadmapORM.created_at.desc())
            .limit(1)
        )
        roadmap = roadmap_result.scalar_one_or_none()
        if roadmap is None:
            return None

        # Try in-progress first, then upcoming, then completed
        for preferred_status in ("in-progress", "upcoming", "completed"):
            plan_result = await self._db.execute(
                select(WeeklyPlanORM)
                .where(
                    WeeklyPlanORM.roadmap_id == roadmap.id,
                    WeeklyPlanORM.status == preferred_status,
                )
                .order_by(WeeklyPlanORM.week_number)
                .limit(1)
            )
            plan = plan_result.scalar_one_or_none()
            if plan is not None:
                return plan.id

        return None

    async def suggest_projects(
        self, weekly_plan_id: UUID, user_skill_level: ProficiencyLevel,
        user_id: UUID | None = None,
    ) -> list[ProjectSuggestionSchema]:
        """Suggest projects relevant to the user's career trajectory.

        Fetches the user's current role and target role for context, then
        generates project suggestions aligned to their career path.

        Args:
            weekly_plan_id: The ID of the weekly plan (practical milestone).
            user_skill_level: The user's current skill level.
            user_id: The user's ID for fetching profile/target role context.

        Returns:
            A list of ProjectSuggestion schemas.
        """
        # Load the weekly plan with its tasks
        result = await self._db.execute(
            select(WeeklyPlanORM)
            .where(WeeklyPlanORM.id == weekly_plan_id)
            .options(selectinload(WeeklyPlanORM.tasks))
        )
        plan = result.scalar_one_or_none()
        if plan is None:
            from app.services.weekly_plan_service import WeeklyPlanNotFoundError
            raise WeeklyPlanNotFoundError()

        # Extract skills from the milestone's tasks
        skills = self._extract_skills_from_plan(plan)

        # Fetch career context for better relevance
        current_role: str | None = None
        target_role: str | None = None

        if user_id:
            current_role, target_role = await self._fetch_career_context(user_id)

        # Call AI provider to generate project suggestions
        ai_suggestions = await self._ai_provider.suggest_projects(
            skills=skills,
            level=user_skill_level,
            current_role=current_role,
            target_role=target_role,
        )

        # Persist suggestions to DB linked to the weekly_plan_id
        persisted: list[ProjectSuggestionORM] = []
        for suggestion in ai_suggestions:
            project_orm = ProjectSuggestionORM(
                id=suggestion.id,
                weekly_plan_id=weekly_plan_id,
                title=suggestion.title,
                objectives=suggestion.objectives,
                deliverables=suggestion.deliverables,
                technologies=suggestion.technologies,
                estimated_weeks=suggestion.estimated_weeks,
                complexity=suggestion.complexity,
                completed=False,
                dismissed=False,
            )
            self._db.add(project_orm)
            persisted.append(project_orm)

        await self._db.flush()
        return [self._project_orm_to_schema(p) for p in persisted]

    async def mark_project_completed(self, project_id: UUID, outcome: str) -> None:
        """Mark a project as completed with an outcome description.

        Args:
            project_id: The project suggestion ID.
            outcome: A text description of what the user accomplished (max 500 chars).

        Raises:
            ProjectNotFoundError: If the project doesn't exist.
            OutcomeTooLongError: If the outcome exceeds 500 characters.
        """
        if len(outcome) > _MAX_OUTCOME_LENGTH:
            raise OutcomeTooLongError()

        project = await self._get_project(project_id)
        project.completed = True
        project.outcome_description = outcome
        await self._db.flush()

    async def dismiss_project(self, project_id: UUID) -> None:
        """Dismiss a single project suggestion.

        Args:
            project_id: The project suggestion ID.

        Raises:
            ProjectNotFoundError: If the project doesn't exist.
        """
        project = await self._get_project(project_id)
        project.dismissed = True
        await self._db.flush()

    async def skip_all_projects(self, weekly_plan_id: UUID) -> None:
        """Dismiss all project suggestions for a given milestone plan.

        This allows the user to proceed without completing any project.

        Args:
            weekly_plan_id: The weekly plan (milestone) ID.
        """
        result = await self._db.execute(
            select(ProjectSuggestionORM).where(
                ProjectSuggestionORM.weekly_plan_id == weekly_plan_id,
                ProjectSuggestionORM.completed == False,  # noqa: E712
                ProjectSuggestionORM.dismissed == False,  # noqa: E712
            )
        )
        projects = result.scalars().all()
        for project in projects:
            project.dismissed = True
        await self._db.flush()

    async def get_suggestions_for_plan(
        self, weekly_plan_id: UUID
    ) -> list[ProjectSuggestionSchema]:
        """Get all non-dismissed project suggestions for a weekly plan.

        Args:
            weekly_plan_id: The weekly plan ID.

        Returns:
            List of active project suggestions.
        """
        result = await self._db.execute(
            select(ProjectSuggestionORM).where(
                ProjectSuggestionORM.weekly_plan_id == weekly_plan_id,
                ProjectSuggestionORM.dismissed == False,  # noqa: E712
            )
        )
        projects = result.scalars().all()
        return [self._project_orm_to_schema(p) for p in projects]
