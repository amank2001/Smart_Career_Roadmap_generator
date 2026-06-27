"""Weekly learning plan routes."""

from typing import Union
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.openai_provider import OpenAIProvider
from app.api.deps import get_current_user_id
from app.core.database import get_db
from app.schemas.weekly_plan import RoadmapCompletionSummary, WeeklyPlan
from app.services.weekly_plan_service import WeeklyPlanService

router = APIRouter()


# ── Dependency helpers ─────────────────────────────────────────────────────────


def get_weekly_plan_service(
    db: AsyncSession = Depends(get_db),
) -> WeeklyPlanService:
    """Dependency that constructs a WeeklyPlanService with the current DB session and AI provider."""
    ai_provider = OpenAIProvider()
    return WeeklyPlanService(db=db, ai_provider=ai_provider)


# ── Endpoints ──────────────────────────────────────────────────────────────────


@router.get(
    "",
    response_model=list[WeeklyPlan],
    summary="List all weekly plans",
)
async def list_weekly_plans(
    user_id: UUID = Depends(get_current_user_id),
    service: WeeklyPlanService = Depends(get_weekly_plan_service),
) -> list[WeeklyPlan]:
    """Retrieve all weekly plans for the authenticated user's current roadmap.

    Returns plans ordered by week number.

    Domain exceptions (NoGapAnalysisError) are handled by the registered
    exception handlers automatically.

    Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6
    """
    return await service.get_all_plans(user_id=user_id)


@router.get(
    "/current",
    response_model=WeeklyPlan,
    summary="Get the current active weekly plan",
)
async def get_current_plan(
    user_id: UUID = Depends(get_current_user_id),
    service: WeeklyPlanService = Depends(get_weekly_plan_service),
) -> WeeklyPlan:
    """Retrieve the user's active (in-progress) weekly plan.

    Returns 404 if there is no active plan.

    Requirements: 5.1, 5.2, 5.3
    """
    plan = await service.get_current_plan(user_id=user_id)
    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "NO_ACTIVE_PLAN",
                "message": "No active weekly plan found.",
            },
        )
    return plan


@router.put(
    "/{plan_id}/tasks/{task_id}/complete",
    response_model=Union[WeeklyPlan, RoadmapCompletionSummary],
    summary="Mark a task as complete",
)
async def complete_task(
    plan_id: UUID,
    task_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    service: WeeklyPlanService = Depends(get_weekly_plan_service),
) -> Union[WeeklyPlan, RoadmapCompletionSummary]:
    """Mark a specific task within a weekly plan as completed.

    When all tasks in a plan are completed, the plan status advances to
    'completed' and the next plan becomes 'in-progress'. If this was the
    final plan in the roadmap, a RoadmapCompletionSummary is returned instead.

    Domain exceptions (WeeklyPlanNotFoundError, WeeklyTaskNotFoundError) are
    handled by the registered exception handlers automatically.

    Requirements: 5.3, 5.4, 5.6
    """
    return await service.mark_task_complete(plan_id=plan_id, task_id=task_id, user_id=user_id)


@router.post(
    "/adjust",
    response_model=list[WeeklyPlan],
    summary="Adjust remaining plans for delay",
)
async def adjust_plan(
    user_id: UUID = Depends(get_current_user_id),
    service: WeeklyPlanService = Depends(get_weekly_plan_service),
) -> list[WeeklyPlan]:
    """Adjust remaining weekly plans to accommodate incomplete tasks from the current plan.

    Redistributes incomplete tasks from the current in-progress plan into
    upcoming plans. Does not require a request body since it operates on the
    user's current in-progress plan.

    Domain exceptions (NoGapAnalysisError) are handled by the registered
    exception handlers automatically.

    Requirements: 5.5
    """
    return await service.adjust_for_delay(user_id=user_id)
