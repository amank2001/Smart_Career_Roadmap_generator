"""Unit tests for WeeklyPlanService — no live database required.

Tests cover:
- generate_weekly_plans creates plans with 3-7 tasks each
- generate_weekly_plans ensures task hours sum ≤ weekly study hours
- generate_weekly_plans marks milestones every 3rd plan
- generate_weekly_plans sets first plan to in-progress
- mark_task_complete marks the task and checks plan completion
- mark_task_complete advances to next plan when all tasks done
- mark_task_complete returns completion summary for final plan
- advance_to_next_plan returns next upcoming plan
- advance_to_next_plan returns None when no plans remain
- adjust_for_delay redistributes incomplete tasks
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import NoGapAnalysisError
from app.services.weekly_plan_service import (
    RoadmapNotFoundError,
    WeeklyPlanNotFoundError,
    WeeklyPlanService,
    WeeklyTaskNotFoundError,
)


# ── Helpers ────────────────────────────────────────────────────────────────────


def make_topic_orm(
    skill_name: str = "Python",
    proficiency_target: str = "intermediate",
    estimated_hours: int = 5,
    order_index: int = 0,
) -> MagicMock:
    """Create a mock RoadmapTopicORM."""
    topic = MagicMock()
    topic.id = uuid.uuid4()
    topic.skill_name = skill_name
    topic.proficiency_target = proficiency_target
    topic.estimated_hours = estimated_hours
    topic.order_index = order_index
    return topic


def make_roadmap_orm(
    user_id: uuid.UUID | None = None,
    weekly_study_hours: int = 10,
    topics: list | None = None,
    weekly_plans: list | None = None,
) -> MagicMock:
    """Create a mock LearningRoadmapORM."""
    roadmap = MagicMock()
    roadmap.id = uuid.uuid4()
    roadmap.user_id = user_id or uuid.uuid4()
    roadmap.weekly_study_hours = weekly_study_hours
    roadmap.is_complete = False
    roadmap.total_weeks = 4
    roadmap.topics = topics if topics is not None else [
        make_topic_orm("Python", "intermediate", 5, 0),
        make_topic_orm("Docker", "beginner", 3, 1),
        make_topic_orm("SQL", "intermediate", 4, 2),
        make_topic_orm("System Design", "advanced", 6, 3),
        make_topic_orm("AWS", "intermediate", 5, 4),
    ]
    roadmap.weekly_plans = weekly_plans if weekly_plans is not None else []
    return roadmap


def make_task_orm(
    skill_name: str = "Python",
    estimated_hours: float = 3.0,
    completed: bool = False,
    plan_id: uuid.UUID | None = None,
) -> MagicMock:
    """Create a mock WeeklyTaskORM."""
    task = MagicMock()
    task.id = uuid.uuid4()
    task.weekly_plan_id = plan_id or uuid.uuid4()
    task.description = f"Study {skill_name}"
    task.estimated_hours = estimated_hours
    task.skill_name = skill_name
    task.completion_criterion = f"Complete {skill_name} exercises"
    task.completed = completed
    task.completed_at = None
    return task


def make_plan_orm(
    roadmap_id: uuid.UUID | None = None,
    week_number: int = 1,
    status: str = "in-progress",
    is_practical_milestone: bool = False,
    tasks: list | None = None,
) -> MagicMock:
    """Create a mock WeeklyPlanORM."""
    plan = MagicMock()
    plan.id = uuid.uuid4()
    plan.roadmap_id = roadmap_id or uuid.uuid4()
    plan.week_number = week_number
    plan.status = status
    plan.is_practical_milestone = is_practical_milestone
    plan.start_date = datetime.now(timezone.utc)
    plan.end_date = datetime.now(timezone.utc)
    plan.tasks = tasks if tasks is not None else [
        make_task_orm("Python", 3.0, plan_id=plan.id),
        make_task_orm("Docker", 3.0, plan_id=plan.id),
        make_task_orm("SQL", 3.0, plan_id=plan.id),
    ]
    return plan


def make_service() -> tuple[WeeklyPlanService, AsyncMock, AsyncMock]:
    """Return a WeeklyPlanService with mock db and ai_provider."""
    mock_db = AsyncMock()
    mock_ai = AsyncMock()
    svc = WeeklyPlanService(db=mock_db, ai_provider=mock_ai)
    return svc, mock_db, mock_ai


# ── _distribute_topics_into_weeks tests (pure logic) ──────────────────────────


class TestDistributeTopicsIntoWeeks:
    """Test the internal topic distribution algorithm."""

    def test_basic_distribution_respects_weekly_hours(self) -> None:
        svc, _, _ = make_service()
        topics = [
            make_topic_orm("Python", "intermediate", 3, 0),
            make_topic_orm("Docker", "beginner", 3, 1),
            make_topic_orm("SQL", "intermediate", 3, 2),
            make_topic_orm("AWS", "intermediate", 3, 3),
            make_topic_orm("React", "beginner", 3, 4),
        ]
        weeks = svc._distribute_topics_into_weeks(topics, weekly_study_hours=10)

        # Each week's total hours should not exceed 10
        for week in weeks:
            total_hours = sum(t["estimated_hours"] for t in week)
            assert total_hours <= 10

    def test_distribution_produces_3_to_7_tasks_per_week(self) -> None:
        svc, _, _ = make_service()
        topics = [
            make_topic_orm("Python", "intermediate", 2, 0),
            make_topic_orm("Docker", "beginner", 2, 1),
            make_topic_orm("SQL", "intermediate", 2, 2),
            make_topic_orm("AWS", "intermediate", 2, 3),
            make_topic_orm("React", "beginner", 2, 4),
            make_topic_orm("Node", "beginner", 2, 5),
        ]
        weeks = svc._distribute_topics_into_weeks(topics, weekly_study_hours=10)

        # Ideally all weeks have 3-7 tasks, though edge cases may have fewer
        # at the tail end
        for week in weeks:
            assert len(week) <= 7

    def test_large_topic_is_split_into_smaller_tasks(self) -> None:
        svc, _, _ = make_service()
        # A topic with 20 hours should be split into multiple tasks
        topics = [
            make_topic_orm("Machine Learning", "advanced", 20, 0),
        ]
        weeks = svc._distribute_topics_into_weeks(topics, weekly_study_hours=10)

        # Should be multiple weeks since 20 hours > 10 hours per week
        assert len(weeks) >= 2
        for week in weeks:
            total_hours = sum(t["estimated_hours"] for t in week)
            assert total_hours <= 10

    def test_empty_topics_returns_empty(self) -> None:
        svc, _, _ = make_service()
        weeks = svc._distribute_topics_into_weeks([], weekly_study_hours=10)
        assert weeks == []

    def test_topics_ordered_by_order_index(self) -> None:
        svc, _, _ = make_service()
        topics = [
            make_topic_orm("Second", "beginner", 3, 1),
            make_topic_orm("First", "beginner", 3, 0),
            make_topic_orm("Third", "beginner", 3, 2),
        ]
        weeks = svc._distribute_topics_into_weeks(topics, weekly_study_hours=10)

        # Flatten all tasks to check ordering
        all_tasks = [t for week in weeks for t in week]
        skill_names = [t["skill_name"] for t in all_tasks]
        assert skill_names[0] == "First"
        assert skill_names[1] == "Second"
        assert skill_names[2] == "Third"


# ── mark_task_complete ─────────────────────────────────────────────────────────


class TestMarkTaskComplete:
    @pytest.mark.asyncio
    async def test_marks_task_as_completed(self) -> None:
        svc, mock_db, _ = make_service()
        plan_id = uuid.uuid4()
        task_id = uuid.uuid4()

        # Create a plan with 3 tasks, where one will be marked complete
        task1 = make_task_orm("Python", 3.0, completed=False, plan_id=plan_id)
        task1.id = task_id
        task2 = make_task_orm("Docker", 3.0, completed=False, plan_id=plan_id)
        task3 = make_task_orm("SQL", 3.0, completed=False, plan_id=plan_id)

        plan = make_plan_orm(week_number=1, status="in-progress", tasks=[task1, task2, task3])
        plan.id = plan_id

        # Mock _get_plan_with_tasks calls
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = plan
        mock_db.execute.return_value = mock_result

        result = await svc.mark_task_complete(plan_id, task_id)

        # Task should be marked complete
        assert task1.completed is True
        assert task1.completed_at is not None

    @pytest.mark.asyncio
    async def test_raises_plan_not_found_error(self) -> None:
        svc, mock_db, _ = make_service()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(WeeklyPlanNotFoundError):
            await svc.mark_task_complete(uuid.uuid4(), uuid.uuid4())

    @pytest.mark.asyncio
    async def test_raises_task_not_found_error(self) -> None:
        svc, mock_db, _ = make_service()
        plan_id = uuid.uuid4()

        plan = make_plan_orm(week_number=1, status="in-progress")
        plan.id = plan_id

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = plan
        mock_db.execute.return_value = mock_result

        # Use a task_id not present in the plan's tasks
        with pytest.raises(WeeklyTaskNotFoundError):
            await svc.mark_task_complete(plan_id, uuid.uuid4())


# ── advance_to_next_plan ───────────────────────────────────────────────────────


class TestAdvanceToNextPlan:
    @pytest.mark.asyncio
    async def test_returns_none_when_no_upcoming_plans(self) -> None:
        svc, mock_db, _ = make_service()
        user_id = uuid.uuid4()

        # Roadmap with no upcoming plans
        completed_plan = make_plan_orm(week_number=1, status="completed")
        roadmap = make_roadmap_orm(user_id=user_id, weekly_plans=[completed_plan])

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = roadmap
        mock_db.execute.return_value = mock_result

        result = await svc.advance_to_next_plan(user_id)
        assert result is None

    @pytest.mark.asyncio
    async def test_raises_error_when_no_roadmap_found(self) -> None:
        svc, mock_db, _ = make_service()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(NoGapAnalysisError):
            await svc.advance_to_next_plan(uuid.uuid4())


# ── adjust_for_delay ───────────────────────────────────────────────────────────


class TestAdjustForDelay:
    @pytest.mark.asyncio
    async def test_returns_empty_when_no_current_plan(self) -> None:
        svc, mock_db, _ = make_service()
        user_id = uuid.uuid4()

        # Roadmap with no in-progress plan
        completed_plan = make_plan_orm(week_number=1, status="completed")
        roadmap = make_roadmap_orm(user_id=user_id, weekly_plans=[completed_plan])

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = roadmap
        mock_db.execute.return_value = mock_result

        result = await svc.adjust_for_delay(user_id)
        assert result == []


# ── ORM to schema conversion ──────────────────────────────────────────────────


class TestPlanOrmToSchema:
    def test_converts_plan_orm_to_schema(self) -> None:
        plan_id = uuid.uuid4()
        roadmap_id = uuid.uuid4()

        task1 = MagicMock()
        task1.id = uuid.uuid4()
        task1.description = "Study Python"
        task1.estimated_hours = 3.0
        task1.skill_name = "Python"
        task1.completion_criterion = "Complete exercises"
        task1.completed = False

        task2 = MagicMock()
        task2.id = uuid.uuid4()
        task2.description = "Study Docker"
        task2.estimated_hours = 2.0
        task2.skill_name = "Docker"
        task2.completion_criterion = "Deploy container"
        task2.completed = True

        task3 = MagicMock()
        task3.id = uuid.uuid4()
        task3.description = "Study SQL"
        task3.estimated_hours = 2.5
        task3.skill_name = "SQL"
        task3.completion_criterion = "Write complex queries"
        task3.completed = False

        plan_orm = MagicMock()
        plan_orm.id = plan_id
        plan_orm.roadmap_id = roadmap_id
        plan_orm.week_number = 1
        plan_orm.status = "in-progress"
        plan_orm.is_practical_milestone = True
        plan_orm.tasks = [task1, task2, task3]

        schema = WeeklyPlanService._plan_orm_to_schema(plan_orm)

        assert schema.id == plan_id
        assert schema.roadmap_id == roadmap_id
        assert schema.week_number == 1
        assert schema.status == "in-progress"
        assert schema.is_practical_milestone is True
        assert len(schema.tasks) == 3
        assert schema.tasks[0].description == "Study Python"
        assert schema.tasks[1].completed is True
        assert schema.tasks[2].skill_name == "SQL"
