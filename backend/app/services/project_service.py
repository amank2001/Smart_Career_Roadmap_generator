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

    # ── Public service methods ────────────────────────────────────────────────

    async def suggest_projects(
        self, weekly_plan_id: UUID, user_skill_level: ProficiencyLevel
    ) -> list[ProjectSuggestionSchema]:
        """Suggest at least 2 projects when a practical milestone is completed.

        Extracts skill names from the milestone's tasks, calls the AI provider
        to generate project suggestions, and persists them to the database.

        Args:
            weekly_plan_id: The ID of the weekly plan (practical milestone).
            user_skill_level: The user's current skill level.

        Returns:
            A list of at least 2 ProjectSuggestion schemas.
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

        # Call AI provider to generate project suggestions
        ai_suggestions = await self._ai_provider.suggest_projects(
            skills=skills,
            level=user_skill_level,
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
