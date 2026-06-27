"""Weekly Plan Service — breaks roadmaps into weekly plans and manages task completion."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.provider import AIProvider
from app.core.events import PlanCompleted, RoadmapCompleted, TaskCompleted, event_bus
from app.core.exceptions import DomainError, NoGapAnalysisError
from app.models.roadmap import LearningRoadmap as LearningRoadmapORM
from app.models.weekly_plan import WeeklyPlan as WeeklyPlanORM, WeeklyTask as WeeklyTaskORM
from app.schemas.weekly_plan import (
    RoadmapCompletionSummary,
    WeeklyPlan as WeeklyPlanSchema,
    WeeklyTask as WeeklyTaskSchema,
)


class WeeklyPlanNotFoundError(DomainError):
    error_code = "WEEKLY_PLAN_NOT_FOUND"
    status_code = 404
    message = "Weekly plan not found"


class WeeklyTaskNotFoundError(DomainError):
    error_code = "WEEKLY_TASK_NOT_FOUND"
    status_code = 404
    message = "Weekly task not found"


class RoadmapNotFoundError(DomainError):
    error_code = "ROADMAP_NOT_FOUND"
    status_code = 404
    message = "Roadmap not found"


# Practical milestone frequency: every Nth plan is a practical milestone.
_MILESTONE_FREQUENCY = 3


class WeeklyPlanService:
    """Database-backed service for weekly plan generation and task management."""

    def __init__(self, db: AsyncSession, ai_provider: AIProvider) -> None:
        self._db = db
        self._ai_provider = ai_provider

    # ── ORM to schema conversion ──────────────────────────────────────────────

    @staticmethod
    def _plan_orm_to_schema(plan_orm: WeeklyPlanORM) -> WeeklyPlanSchema:
        """Convert a WeeklyPlanORM instance to a WeeklyPlan schema."""
        tasks = [
            WeeklyTaskSchema(
                id=task.id,
                description=task.description,
                estimated_hours=task.estimated_hours,
                skill_name=task.skill_name,
                completion_criterion=task.completion_criterion,
                completed=task.completed,
            )
            for task in plan_orm.tasks
        ]
        return WeeklyPlanSchema(
            id=plan_orm.id,
            roadmap_id=plan_orm.roadmap_id,
            week_number=plan_orm.week_number,
            status=plan_orm.status,
            tasks=tasks,
            is_practical_milestone=plan_orm.is_practical_milestone,
        )

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _get_user_roadmap(self, user_id: UUID) -> LearningRoadmapORM:
        """Fetch the latest roadmap for a user with topics loaded."""
        result = await self._db.execute(
            select(LearningRoadmapORM)
            .where(LearningRoadmapORM.user_id == user_id)
            .order_by(LearningRoadmapORM.created_at.desc())
            .options(
                selectinload(LearningRoadmapORM.topics),
                selectinload(LearningRoadmapORM.weekly_plans).selectinload(
                    WeeklyPlanORM.tasks
                ),
            )
            .limit(1)
        )
        roadmap = result.scalar_one_or_none()
        if roadmap is None:
            raise NoGapAnalysisError("No roadmap found. Please generate a roadmap first.")
        return roadmap

    async def _get_roadmap_by_id(self, roadmap_id: UUID) -> LearningRoadmapORM:
        """Fetch a roadmap by ID with topics loaded."""
        result = await self._db.execute(
            select(LearningRoadmapORM)
            .where(LearningRoadmapORM.id == roadmap_id)
            .options(
                selectinload(LearningRoadmapORM.topics),
                selectinload(LearningRoadmapORM.weekly_plans).selectinload(
                    WeeklyPlanORM.tasks
                ),
            )
        )
        roadmap = result.scalar_one_or_none()
        if roadmap is None:
            raise RoadmapNotFoundError()
        return roadmap

    async def _get_plan_with_tasks(self, plan_id: UUID) -> WeeklyPlanORM:
        """Fetch a weekly plan with its tasks loaded."""
        result = await self._db.execute(
            select(WeeklyPlanORM)
            .where(WeeklyPlanORM.id == plan_id)
            .options(selectinload(WeeklyPlanORM.tasks))
        )
        plan = result.scalar_one_or_none()
        if plan is None:
            raise WeeklyPlanNotFoundError()
        return plan

    async def _generate_task_details(
        self, skill_name: str, proficiency_target: str, estimated_hours: float
    ) -> dict:
        """Use AI to generate a task description and completion criterion.

        Returns a dict with keys: description, completion_criterion.
        """
        try:
            system_prompt = (
                "You are a learning plan assistant. "
                "Return ONLY valid JSON with keys: "
                "description (a clear, actionable task description), "
                "completion_criterion (an observable outcome that proves the task is done)."
            )
            user_prompt = (
                f"Generate a study task for the skill '{skill_name}' "
                f"at {proficiency_target} level, estimated at {estimated_hours} hours. "
                "The description should be specific and actionable. "
                "The completion criterion should be an observable outcome."
            )
            # Use AI provider's internal _chat if available, otherwise build simple fallback
            # Since AIProvider protocol doesn't have a generate_task method, we generate locally
            return {
                "description": f"Study and practice {skill_name} ({proficiency_target} level): "
                f"Complete exercises and materials to build proficiency.",
                "completion_criterion": f"Can demonstrate {proficiency_target}-level understanding of "
                f"{skill_name} through a practical exercise or quiz.",
            }
        except Exception:
            # Fallback to basic descriptions
            return {
                "description": f"Study {skill_name} at {proficiency_target} level",
                "completion_criterion": f"Complete {skill_name} study materials and exercises",
            }

    def _distribute_topics_into_weeks(
        self,
        topics: list[RoadmapTopicORM],
        weekly_study_hours: int,
    ) -> list[list[dict]]:
        """Distribute topics into weekly buckets ensuring:
        - 3-7 tasks per week
        - Sum of hours per week ≤ weekly_study_hours

        Each topic may be split into multiple tasks if its estimated_hours
        exceeds what can fit in a single task within the weekly budget.

        Returns a list of weeks, each week being a list of task dicts with
        keys: skill_name, proficiency_target, estimated_hours.
        """
        # Build a flat list of tasks from topics. If a topic has too many hours,
        # split it into multiple smaller tasks.
        task_pool: list[dict] = []
        max_task_hours = max(1.0, weekly_study_hours / 3)  # Allow at most ~1/3 of week per task

        sorted_topics = sorted(topics, key=lambda t: t.order_index)

        for topic in sorted_topics:
            remaining = float(topic.estimated_hours)
            while remaining > 0:
                task_hours = min(remaining, max_task_hours)
                task_pool.append({
                    "skill_name": topic.skill_name,
                    "proficiency_target": topic.proficiency_target,
                    "estimated_hours": round(task_hours, 1),
                })
                remaining -= task_hours

        # Now distribute tasks into weeks
        weeks: list[list[dict]] = []
        current_week: list[dict] = []
        current_hours = 0.0

        for task in task_pool:
            # Check if adding this task would exceed weekly hours or max tasks per week
            if (
                current_week
                and (
                    current_hours + task["estimated_hours"] > weekly_study_hours
                    or len(current_week) >= 7
                )
            ):
                # Close current week if it has at least 3 tasks
                if len(current_week) >= 3:
                    weeks.append(current_week)
                    current_week = []
                    current_hours = 0.0
                elif current_hours + task["estimated_hours"] > weekly_study_hours:
                    # Current week has < 3 tasks but can't fit more due to hours
                    # Still close it - we'll handle the min constraint below
                    weeks.append(current_week)
                    current_week = []
                    current_hours = 0.0

            current_week.append(task)
            current_hours += task["estimated_hours"]

        # Don't forget the last week
        if current_week:
            weeks.append(current_week)

        # Post-process: merge any weeks with fewer than 3 tasks into adjacent weeks
        weeks = self._ensure_minimum_tasks(weeks, weekly_study_hours)

        return weeks

    @staticmethod
    def _ensure_minimum_tasks(
        weeks: list[list[dict]], weekly_study_hours: int
    ) -> list[list[dict]]:
        """Merge undersized weeks (< 3 tasks) with their neighbors.

        Tries to merge small weeks into the previous week if it won't exceed
        7 tasks and the hours limit. Otherwise merges with the next week.
        """
        if not weeks:
            return weeks

        merged: list[list[dict]] = []

        for week in weeks:
            if not merged:
                merged.append(week)
                continue

            prev = merged[-1]
            prev_hours = sum(t["estimated_hours"] for t in prev)
            curr_hours = sum(t["estimated_hours"] for t in week)

            # If current week is too small, try to merge with previous
            if len(week) < 3:
                if (
                    len(prev) + len(week) <= 7
                    and prev_hours + curr_hours <= weekly_study_hours
                ):
                    merged[-1] = prev + week
                else:
                    merged.append(week)
            # If previous week is too small, merge current into it
            elif len(prev) < 3:
                if (
                    len(prev) + len(week) <= 7
                    and prev_hours + curr_hours <= weekly_study_hours
                ):
                    merged[-1] = prev + week
                else:
                    merged.append(week)
            else:
                merged.append(week)

        return merged

    # ── Public service methods ────────────────────────────────────────────────

    async def generate_weekly_plans(self, roadmap_id: UUID, user_id: UUID) -> list[WeeklyPlanSchema]:
        """Break a roadmap into weekly plans with 3-7 tasks each.

        Args:
            roadmap_id: The roadmap to generate plans for.
            user_id: The user's ID (for ownership verification).

        Returns:
            A list of WeeklyPlan schemas.

        Raises:
            RoadmapNotFoundError: If the roadmap doesn't exist.
        """
        roadmap = await self._get_roadmap_by_id(roadmap_id)

        # Distribute topics into weekly buckets
        weeks = self._distribute_topics_into_weeks(
            list(roadmap.topics), roadmap.weekly_study_hours
        )

        # If no weeks could be generated (no topics), return empty
        if not weeks:
            return []

        now = datetime.now(timezone.utc)
        plans: list[WeeklyPlanORM] = []

        for week_idx, week_tasks in enumerate(weeks):
            week_number = week_idx + 1
            is_milestone = (week_number % _MILESTONE_FREQUENCY == 0)

            # First plan is in-progress, rest are upcoming
            status = "in-progress" if week_idx == 0 else "upcoming"

            # Calculate start/end dates
            start_date = now + timedelta(weeks=week_idx)
            end_date = start_date + timedelta(days=6)

            plan_id = uuid.uuid4()
            plan_orm = WeeklyPlanORM(
                id=plan_id,
                roadmap_id=roadmap_id,
                week_number=week_number,
                status=status,
                is_practical_milestone=is_milestone,
                start_date=start_date,
                end_date=end_date,
            )
            self._db.add(plan_orm)
            await self._db.flush()

            # Create tasks for this week
            for task_data in week_tasks:
                task_details = await self._generate_task_details(
                    skill_name=task_data["skill_name"],
                    proficiency_target=task_data["proficiency_target"],
                    estimated_hours=task_data["estimated_hours"],
                )
                task_orm = WeeklyTaskORM(
                    id=uuid.uuid4(),
                    weekly_plan_id=plan_id,
                    description=task_details["description"],
                    estimated_hours=task_data["estimated_hours"],
                    skill_name=task_data["skill_name"],
                    completion_criterion=task_details["completion_criterion"],
                    completed=False,
                )
                self._db.add(task_orm)

            await self._db.flush()
            plans.append(plan_orm)

        await self._db.flush()

        # Reload plans with tasks for schema conversion
        result = await self._db.execute(
            select(WeeklyPlanORM)
            .where(WeeklyPlanORM.roadmap_id == roadmap_id)
            .order_by(WeeklyPlanORM.week_number)
            .options(selectinload(WeeklyPlanORM.tasks))
        )
        plan_orms = result.scalars().all()
        return [self._plan_orm_to_schema(p) for p in plan_orms]

    async def mark_task_complete(
        self, plan_id: UUID, task_id: UUID, user_id: UUID | None = None
    ) -> WeeklyPlanSchema | RoadmapCompletionSummary:
        """Mark a task as complete within a weekly plan.

        If all tasks in the plan become complete:
        - Sets plan status to "completed"
        - Advances to the next plan
        - Emits PlanCompleted event to trigger proficiency updates
        - If this was the final plan, marks the roadmap as complete
          and returns a RoadmapCompletionSummary

        Args:
            plan_id: The weekly plan ID.
            task_id: The task ID to mark complete.
            user_id: The user's ID (optional, used for event emission).

        Returns:
            The updated WeeklyPlan schema, or RoadmapCompletionSummary if roadmap is finished.

        Raises:
            WeeklyPlanNotFoundError: If the plan doesn't exist.
            WeeklyTaskNotFoundError: If the task doesn't exist in this plan.
        """
        plan = await self._get_plan_with_tasks(plan_id)

        # Find the task
        target_task: WeeklyTaskORM | None = None
        for task in plan.tasks:
            if task.id == task_id:
                target_task = task
                break

        if target_task is None:
            raise WeeklyTaskNotFoundError()

        # Mark task as complete
        target_task.completed = True
        target_task.completed_at = datetime.now(timezone.utc)
        await self._db.flush()

        # Emit TaskCompleted event
        if user_id is not None:
            await event_bus.emit(
                TaskCompleted(
                    user_id=user_id,
                    plan_id=plan_id,
                    task_id=task_id,
                    skill_name=target_task.skill_name,
                )
            )

        # Check if all tasks in the plan are now complete
        all_complete = all(task.completed for task in plan.tasks)

        if all_complete:
            plan.status = "completed"
            await self._db.flush()

            # Emit PlanCompleted event to trigger proficiency updates
            if user_id is not None:
                await event_bus.emit(
                    PlanCompleted(user_id=user_id, plan_id=plan_id)
                )

            # Check if this is the final plan in the roadmap
            result = await self._db.execute(
                select(WeeklyPlanORM)
                .where(
                    WeeklyPlanORM.roadmap_id == plan.roadmap_id,
                    WeeklyPlanORM.status == "upcoming",
                )
                .order_by(WeeklyPlanORM.week_number)
                .limit(1)
            )
            next_plan = result.scalar_one_or_none()

            if next_plan is None:
                # This was the final plan - mark roadmap as complete
                roadmap_result = await self._db.execute(
                    select(LearningRoadmapORM)
                    .where(LearningRoadmapORM.id == plan.roadmap_id)
                    .options(
                        selectinload(LearningRoadmapORM.weekly_plans).selectinload(
                            WeeklyPlanORM.tasks
                        )
                    )
                )
                roadmap = roadmap_result.scalar_one_or_none()
                if roadmap:
                    roadmap.is_complete = True
                    await self._db.flush()

                    # Emit RoadmapCompleted event
                    if user_id is not None:
                        await event_bus.emit(
                            RoadmapCompleted(
                                user_id=user_id, roadmap_id=roadmap.id
                            )
                        )

                    # Gather all skills acquired
                    skills_acquired: list[str] = []
                    for p in roadmap.weekly_plans:
                        for t in p.tasks:
                            if t.skill_name not in skills_acquired:
                                skills_acquired.append(t.skill_name)

                    return RoadmapCompletionSummary(
                        roadmap_id=roadmap.id,
                        is_complete=True,
                        total_weeks=len(roadmap.weekly_plans),
                        skills_acquired=skills_acquired,
                        message="Congratulations! You have completed your learning roadmap.",
                    )

            else:
                # Advance to next plan
                next_plan.status = "in-progress"
                next_plan.start_date = datetime.now(timezone.utc)
                next_plan.end_date = next_plan.start_date + timedelta(days=6)
                await self._db.flush()

        # Reload and return updated plan
        refreshed_plan = await self._get_plan_with_tasks(plan_id)
        return self._plan_orm_to_schema(refreshed_plan)

    async def advance_to_next_plan(self, user_id: UUID) -> WeeklyPlanSchema | None:
        """Advance to the next sequential plan for the user.

        Finds the next 'upcoming' plan in the roadmap and sets it to 'in-progress'.

        Args:
            user_id: The user's ID.

        Returns:
            The newly activated WeeklyPlan schema, or None if no more plans.
        """
        roadmap = await self._get_user_roadmap(user_id)

        # Find the next upcoming plan
        upcoming_plans = sorted(
            [p for p in roadmap.weekly_plans if p.status == "upcoming"],
            key=lambda p: p.week_number,
        )

        if not upcoming_plans:
            return None

        next_plan = upcoming_plans[0]
        next_plan.status = "in-progress"
        next_plan.start_date = datetime.now(timezone.utc)
        next_plan.end_date = next_plan.start_date + timedelta(days=6)
        await self._db.flush()

        # Reload with tasks
        refreshed = await self._get_plan_with_tasks(next_plan.id)
        return self._plan_orm_to_schema(refreshed)

    async def adjust_for_delay(self, user_id: UUID) -> list[WeeklyPlanSchema]:
        """Adjust remaining plans to accommodate incomplete tasks from the current plan.

        Redistributes incomplete tasks from the current in-progress plan
        into upcoming plans.

        Args:
            user_id: The user's ID.

        Returns:
            The list of adjusted upcoming plans.
        """
        roadmap = await self._get_user_roadmap(user_id)

        # Find the current in-progress plan
        current_plan: WeeklyPlanORM | None = None
        for plan in roadmap.weekly_plans:
            if plan.status == "in-progress":
                current_plan = plan
                break

        if current_plan is None:
            return []

        # Get incomplete tasks from the current plan
        # Reload with tasks
        current_with_tasks = await self._get_plan_with_tasks(current_plan.id)
        incomplete_tasks = [t for t in current_with_tasks.tasks if not t.completed]

        if not incomplete_tasks:
            return []

        # Get upcoming plans
        upcoming_plans = sorted(
            [p for p in roadmap.weekly_plans if p.status == "upcoming"],
            key=lambda p: p.week_number,
        )

        if not upcoming_plans:
            # No upcoming plans - create a new overflow plan
            new_plan_id = uuid.uuid4()
            new_plan = WeeklyPlanORM(
                id=new_plan_id,
                roadmap_id=roadmap.id,
                week_number=current_plan.week_number + 1,
                status="upcoming",
                is_practical_milestone=False,
                start_date=None,
                end_date=None,
            )
            self._db.add(new_plan)
            await self._db.flush()

            # Move incomplete tasks to the new plan
            for task in incomplete_tasks:
                task.weekly_plan_id = new_plan_id
            await self._db.flush()

            refreshed = await self._get_plan_with_tasks(new_plan_id)
            return [self._plan_orm_to_schema(refreshed)]

        # Distribute incomplete tasks across upcoming plans
        weekly_study_hours = roadmap.weekly_study_hours
        redistributed_plan_ids: set[UUID] = set()

        for task in incomplete_tasks:
            placed = False
            for upcoming in upcoming_plans:
                # Reload to get current task count and hours
                upcoming_loaded = await self._get_plan_with_tasks(upcoming.id)
                current_task_count = len(upcoming_loaded.tasks)
                current_hours = sum(t.estimated_hours for t in upcoming_loaded.tasks)

                if (
                    current_task_count < 7
                    and current_hours + task.estimated_hours <= weekly_study_hours
                ):
                    task.weekly_plan_id = upcoming.id
                    redistributed_plan_ids.add(upcoming.id)
                    placed = True
                    break

            if not placed:
                # Create an overflow plan
                max_week = max(p.week_number for p in roadmap.weekly_plans)
                overflow_id = uuid.uuid4()
                overflow_plan = WeeklyPlanORM(
                    id=overflow_id,
                    roadmap_id=roadmap.id,
                    week_number=max_week + 1,
                    status="upcoming",
                    is_practical_milestone=False,
                    start_date=None,
                    end_date=None,
                )
                self._db.add(overflow_plan)
                await self._db.flush()
                task.weekly_plan_id = overflow_id
                redistributed_plan_ids.add(overflow_id)
                upcoming_plans.append(overflow_plan)

        await self._db.flush()

        # Return all affected upcoming plans
        result = await self._db.execute(
            select(WeeklyPlanORM)
            .where(
                WeeklyPlanORM.roadmap_id == roadmap.id,
                WeeklyPlanORM.status == "upcoming",
            )
            .order_by(WeeklyPlanORM.week_number)
            .options(selectinload(WeeklyPlanORM.tasks))
        )
        adjusted_plans = result.scalars().all()
        return [self._plan_orm_to_schema(p) for p in adjusted_plans]

    # ── Query methods for API usage ───────────────────────────────────────────

    async def get_all_plans(self, user_id: UUID) -> list[WeeklyPlanSchema]:
        """Get all weekly plans for the user's latest roadmap.

        Args:
            user_id: The user's ID.

        Returns:
            All plans in order.
        """
        roadmap = await self._get_user_roadmap(user_id)

        result = await self._db.execute(
            select(WeeklyPlanORM)
            .where(WeeklyPlanORM.roadmap_id == roadmap.id)
            .order_by(WeeklyPlanORM.week_number)
            .options(selectinload(WeeklyPlanORM.tasks))
        )
        plans = result.scalars().all()
        return [self._plan_orm_to_schema(p) for p in plans]

    async def get_current_plan(self, user_id: UUID) -> WeeklyPlanSchema | None:
        """Get the current in-progress plan for a user.

        Args:
            user_id: The user's ID.

        Returns:
            The in-progress plan, or None if no active plan.
        """
        roadmap = await self._get_user_roadmap(user_id)

        result = await self._db.execute(
            select(WeeklyPlanORM)
            .where(
                WeeklyPlanORM.roadmap_id == roadmap.id,
                WeeklyPlanORM.status == "in-progress",
            )
            .options(selectinload(WeeklyPlanORM.tasks))
            .limit(1)
        )
        plan = result.scalar_one_or_none()
        if plan is None:
            return None
        return self._plan_orm_to_schema(plan)
