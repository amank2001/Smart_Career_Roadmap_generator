"""Unit tests for ProjectSuggesterService — no live database required.

Tests cover:
- suggest_projects returns at least 2 suggestions
- suggest_projects persists suggestions to DB
- suggest_projects extracts skills from plan tasks
- suggest_projects raises WeeklyPlanNotFoundError for missing plan
- mark_project_completed marks project and stores outcome
- mark_project_completed raises OutcomeTooLongError for long outcomes
- mark_project_completed raises ProjectNotFoundError for missing project
- dismiss_project marks project as dismissed
- dismiss_project raises ProjectNotFoundError for missing project
- skip_all_projects dismisses all active projects for a plan
- get_suggestions_for_plan returns non-dismissed suggestions
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import OutcomeTooLongError, ProjectNotFoundError
from app.services.project_service import ProjectSuggesterService


# ── Helpers ────────────────────────────────────────────────────────────────────


def make_task_orm(skill_name: str = "Python", plan_id: uuid.UUID | None = None) -> MagicMock:
    """Create a mock WeeklyTaskORM."""
    task = MagicMock()
    task.id = uuid.uuid4()
    task.weekly_plan_id = plan_id or uuid.uuid4()
    task.skill_name = skill_name
    task.description = f"Study {skill_name}"
    task.estimated_hours = 3.0
    task.completion_criterion = f"Complete {skill_name} exercises"
    task.completed = True
    return task


def make_plan_orm(
    plan_id: uuid.UUID | None = None,
    tasks: list | None = None,
) -> MagicMock:
    """Create a mock WeeklyPlanORM."""
    plan = MagicMock()
    plan.id = plan_id or uuid.uuid4()
    plan.roadmap_id = uuid.uuid4()
    plan.week_number = 3
    plan.status = "completed"
    plan.is_practical_milestone = True
    plan.tasks = tasks if tasks is not None else [
        make_task_orm("Python", plan_id=plan.id),
        make_task_orm("Docker", plan_id=plan.id),
        make_task_orm("SQL", plan_id=plan.id),
    ]
    return plan


def make_ai_project_suggestion(
    title: str = "Build a REST API",
    complexity: str = "intermediate",
) -> MagicMock:
    """Create a mock AI project suggestion (Pydantic model)."""
    suggestion = MagicMock()
    suggestion.id = uuid.uuid4()
    suggestion.title = title
    suggestion.objectives = ["Learn REST principles", "Build CRUD endpoints"]
    suggestion.deliverables = ["Working API", "API documentation"]
    suggestion.technologies = ["Python", "FastAPI", "PostgreSQL"]
    suggestion.estimated_weeks = 2
    suggestion.complexity = complexity
    return suggestion


def make_project_orm(
    project_id: uuid.UUID | None = None,
    weekly_plan_id: uuid.UUID | None = None,
    completed: bool = False,
    dismissed: bool = False,
) -> MagicMock:
    """Create a mock ProjectSuggestionORM."""
    project = MagicMock()
    project.id = project_id or uuid.uuid4()
    project.weekly_plan_id = weekly_plan_id or uuid.uuid4()
    project.title = "Build a REST API"
    project.objectives = ["Learn REST principles"]
    project.deliverables = ["Working API"]
    project.technologies = ["Python", "FastAPI"]
    project.estimated_weeks = 2
    project.complexity = "intermediate"
    project.completed = completed
    project.dismissed = dismissed
    project.outcome_description = None
    return project


def make_service() -> tuple[ProjectSuggesterService, AsyncMock, AsyncMock]:
    """Return a ProjectSuggesterService with mock db and ai_provider."""
    mock_db = AsyncMock()
    mock_ai = AsyncMock()
    svc = ProjectSuggesterService(db=mock_db, ai_provider=mock_ai)
    return svc, mock_db, mock_ai


# ── suggest_projects tests ─────────────────────────────────────────────────────


class TestSuggestProjects:
    @pytest.mark.asyncio
    async def test_returns_at_least_2_suggestions(self) -> None:
        svc, mock_db, mock_ai = make_service()
        plan_id = uuid.uuid4()
        plan = make_plan_orm(plan_id=plan_id)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = plan
        mock_db.execute.return_value = mock_result

        # AI returns 2 suggestions
        mock_ai.suggest_projects.return_value = [
            make_ai_project_suggestion("Build a REST API", "intermediate"),
            make_ai_project_suggestion("Deploy with Docker", "intermediate"),
        ]

        result = await svc.suggest_projects(plan_id, "intermediate")

        assert len(result) >= 2
        assert result[0].title == "Build a REST API"
        assert result[1].title == "Deploy with Docker"

    @pytest.mark.asyncio
    async def test_extracts_skills_from_plan_tasks(self) -> None:
        svc, mock_db, mock_ai = make_service()
        plan_id = uuid.uuid4()

        tasks = [
            make_task_orm("Python", plan_id=plan_id),
            make_task_orm("Docker", plan_id=plan_id),
            make_task_orm("Python", plan_id=plan_id),  # duplicate
        ]
        plan = make_plan_orm(plan_id=plan_id, tasks=tasks)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = plan
        mock_db.execute.return_value = mock_result

        mock_ai.suggest_projects.return_value = [
            make_ai_project_suggestion("Project 1"),
            make_ai_project_suggestion("Project 2"),
        ]

        await svc.suggest_projects(plan_id, "beginner")

        # AI should be called with deduplicated skills
        called_skills = mock_ai.suggest_projects.call_args[1]["skills"]
        assert called_skills == ["Python", "Docker"]

    @pytest.mark.asyncio
    async def test_persists_suggestions_to_db(self) -> None:
        svc, mock_db, mock_ai = make_service()
        plan_id = uuid.uuid4()
        plan = make_plan_orm(plan_id=plan_id)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = plan
        mock_db.execute.return_value = mock_result

        mock_ai.suggest_projects.return_value = [
            make_ai_project_suggestion("Project A"),
            make_ai_project_suggestion("Project B"),
        ]

        await svc.suggest_projects(plan_id, "advanced")

        # db.add should be called twice (one per suggestion)
        assert mock_db.add.call_count == 2
        # db.flush should be called
        mock_db.flush.assert_called()

    @pytest.mark.asyncio
    async def test_raises_not_found_for_missing_plan(self) -> None:
        svc, mock_db, mock_ai = make_service()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        from app.services.weekly_plan_service import WeeklyPlanNotFoundError

        with pytest.raises(WeeklyPlanNotFoundError):
            await svc.suggest_projects(uuid.uuid4(), "beginner")

    @pytest.mark.asyncio
    async def test_aligns_complexity_with_skill_level(self) -> None:
        svc, mock_db, mock_ai = make_service()
        plan_id = uuid.uuid4()
        plan = make_plan_orm(plan_id=plan_id)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = plan
        mock_db.execute.return_value = mock_result

        mock_ai.suggest_projects.return_value = [
            make_ai_project_suggestion("Simple Project", "beginner"),
            make_ai_project_suggestion("Another Simple", "beginner"),
        ]

        await svc.suggest_projects(plan_id, "beginner")

        # AI should be called with the user's skill level
        mock_ai.suggest_projects.assert_called_once_with(
            skills=["Python", "Docker", "SQL"],
            level="beginner",
        )


# ── mark_project_completed tests ──────────────────────────────────────────────


class TestMarkProjectCompleted:
    @pytest.mark.asyncio
    async def test_marks_project_completed_with_outcome(self) -> None:
        svc, mock_db, _ = make_service()
        project_id = uuid.uuid4()
        project = make_project_orm(project_id=project_id)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = project
        mock_db.execute.return_value = mock_result

        await svc.mark_project_completed(project_id, "Built a full REST API with auth")

        assert project.completed is True
        assert project.outcome_description == "Built a full REST API with auth"
        mock_db.flush.assert_called()

    @pytest.mark.asyncio
    async def test_accepts_outcome_at_exactly_500_chars(self) -> None:
        svc, mock_db, _ = make_service()
        project_id = uuid.uuid4()
        project = make_project_orm(project_id=project_id)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = project
        mock_db.execute.return_value = mock_result

        outcome = "x" * 500
        await svc.mark_project_completed(project_id, outcome)

        assert project.completed is True
        assert project.outcome_description == outcome

    @pytest.mark.asyncio
    async def test_raises_outcome_too_long_error(self) -> None:
        svc, mock_db, _ = make_service()

        outcome = "x" * 501
        with pytest.raises(OutcomeTooLongError):
            await svc.mark_project_completed(uuid.uuid4(), outcome)

        # DB should not be queried since validation fails first
        mock_db.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_raises_project_not_found_error(self) -> None:
        svc, mock_db, _ = make_service()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(ProjectNotFoundError):
            await svc.mark_project_completed(uuid.uuid4(), "Done")

    @pytest.mark.asyncio
    async def test_accepts_empty_outcome(self) -> None:
        svc, mock_db, _ = make_service()
        project_id = uuid.uuid4()
        project = make_project_orm(project_id=project_id)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = project
        mock_db.execute.return_value = mock_result

        await svc.mark_project_completed(project_id, "")

        assert project.completed is True
        assert project.outcome_description == ""


# ── dismiss_project tests ─────────────────────────────────────────────────────


class TestDismissProject:
    @pytest.mark.asyncio
    async def test_marks_project_as_dismissed(self) -> None:
        svc, mock_db, _ = make_service()
        project_id = uuid.uuid4()
        project = make_project_orm(project_id=project_id)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = project
        mock_db.execute.return_value = mock_result

        await svc.dismiss_project(project_id)

        assert project.dismissed is True
        mock_db.flush.assert_called()

    @pytest.mark.asyncio
    async def test_raises_project_not_found_error(self) -> None:
        svc, mock_db, _ = make_service()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(ProjectNotFoundError):
            await svc.dismiss_project(uuid.uuid4())


# ── skip_all_projects tests ───────────────────────────────────────────────────


class TestSkipAllProjects:
    @pytest.mark.asyncio
    async def test_dismisses_all_active_projects(self) -> None:
        svc, mock_db, _ = make_service()
        plan_id = uuid.uuid4()

        project1 = make_project_orm(weekly_plan_id=plan_id)
        project2 = make_project_orm(weekly_plan_id=plan_id)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [project1, project2]
        mock_db.execute.return_value = mock_result

        await svc.skip_all_projects(plan_id)

        assert project1.dismissed is True
        assert project2.dismissed is True
        mock_db.flush.assert_called()

    @pytest.mark.asyncio
    async def test_no_op_when_no_active_projects(self) -> None:
        svc, mock_db, _ = make_service()
        plan_id = uuid.uuid4()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        await svc.skip_all_projects(plan_id)

        # Should still flush (no-op effectively)
        mock_db.flush.assert_called()


# ── get_suggestions_for_plan tests ────────────────────────────────────────────


class TestGetSuggestionsForPlan:
    @pytest.mark.asyncio
    async def test_returns_non_dismissed_suggestions(self) -> None:
        svc, mock_db, _ = make_service()
        plan_id = uuid.uuid4()

        project1 = make_project_orm(weekly_plan_id=plan_id, dismissed=False)
        project2 = make_project_orm(weekly_plan_id=plan_id, dismissed=False)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [project1, project2]
        mock_db.execute.return_value = mock_result

        result = await svc.get_suggestions_for_plan(plan_id)

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_returns_empty_when_all_dismissed(self) -> None:
        svc, mock_db, _ = make_service()
        plan_id = uuid.uuid4()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        result = await svc.get_suggestions_for_plan(plan_id)

        assert result == []


# ── ORM to schema conversion ──────────────────────────────────────────────────


class TestProjectOrmToSchema:
    def test_converts_orm_to_schema_correctly(self) -> None:
        project_id = uuid.uuid4()
        project_orm = MagicMock()
        project_orm.id = project_id
        project_orm.title = "Build a Chat App"
        project_orm.objectives = ["Learn WebSockets", "Build real-time features"]
        project_orm.deliverables = ["Working chat app", "Deployment guide"]
        project_orm.technologies = ["Python", "FastAPI", "WebSocket"]
        project_orm.estimated_weeks = 3
        project_orm.complexity = "advanced"

        schema = ProjectSuggesterService._project_orm_to_schema(project_orm)

        assert schema.id == project_id
        assert schema.title == "Build a Chat App"
        assert schema.objectives == ["Learn WebSockets", "Build real-time features"]
        assert schema.deliverables == ["Working chat app", "Deployment guide"]
        assert schema.technologies == ["Python", "FastAPI", "WebSocket"]
        assert schema.estimated_weeks == 3
        assert schema.complexity == "advanced"
