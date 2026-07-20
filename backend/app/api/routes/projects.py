"""Project suggestion routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.openai_provider import OpenAIProvider
from app.api.deps import get_current_user_id
from app.core.database import get_db
from app.schemas.common import ProficiencyLevel
from app.schemas.project import ProjectSuggestion
from app.services.project_service import ProjectSuggesterService

router = APIRouter()


# A complete portfolio exposes meaningful choices at every difficulty level.
_MIN_PROJECTS_PER_COMPLEXITY = 3
_PROJECT_COMPLEXITIES = ("beginner", "intermediate", "advanced")


def _has_balanced_portfolio(projects: list[ProjectSuggestion]) -> bool:
    """Return whether active suggestions contain at least three of each level."""
    counts = {complexity: 0 for complexity in _PROJECT_COMPLEXITIES}
    for project in projects:
        if project.complexity in counts:
            counts[project.complexity] += 1
    return all(
        counts[complexity] >= _MIN_PROJECTS_PER_COMPLEXITY
        for complexity in _PROJECT_COMPLEXITIES
    )


async def _get_or_expand_suggestions(
    service: ProjectSuggesterService,
    plan_id: UUID,
    user_skill_level: ProficiencyLevel,
) -> list[ProjectSuggestion]:
    """Return a balanced portfolio, preserving and expanding legacy suggestions."""
    existing = await service.get_suggestions_for_plan(weekly_plan_id=plan_id)
    if _has_balanced_portfolio(existing):
        return existing

    generated = await service.suggest_projects(
        weekly_plan_id=plan_id,
        user_skill_level=user_skill_level,
    )
    # Preserve completed or previously shown work instead of destructively replacing it.
    return [*existing, *generated]


# ── Request body models ────────────────────────────────────────────────────────


class CompleteProjectRequest(BaseModel):
    """Request body for marking a project as complete."""

    outcome: str = Field(min_length=1, max_length=500)


# ── Dependency helpers ─────────────────────────────────────────────────────────


def get_project_service(
    db: AsyncSession = Depends(get_db),
) -> ProjectSuggesterService:
    """Dependency that constructs a ProjectSuggesterService."""
    ai_provider = OpenAIProvider()
    return ProjectSuggesterService(db=db, ai_provider=ai_provider)


# ── Endpoints ──────────────────────────────────────────────────────────────────


@router.get(
    "/suggestions",
    response_model=list[ProjectSuggestion],
    summary="Get project suggestions for the current user",
)
async def get_suggestions_for_user(
    response: Response,
    user_skill_level: ProficiencyLevel = Query(default="beginner"),
    user_id: UUID = Depends(get_current_user_id),
    service: ProjectSuggesterService = Depends(get_project_service),
) -> list[ProjectSuggestion]:
    """Retrieve a balanced 2026 project portfolio for the authenticated user.

    Uses the current in-progress weekly plan if available, otherwise uses
    the first available plan in the user's roadmap. Legacy suggestion sets
    are expanded without deleting completed or previously shown projects.
    Includes X-Plan-Id header so the client can reference the plan for skip-all.

    Requirements: 7.1, 7.2, 7.3, 7.5
    """
    plan_id = await service.get_best_plan_id_for_user(user_id=user_id)
    if plan_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "NO_WEEKLY_PLAN",
                "message": "No weekly plans found. Please generate a roadmap first.",
            },
        )

    response.headers["X-Plan-Id"] = str(plan_id)
    return await _get_or_expand_suggestions(
        service=service,
        plan_id=plan_id,
        user_skill_level=user_skill_level,
    )


@router.get(
    "/suggestions/{plan_id}",
    response_model=list[ProjectSuggestion],
    summary="Get project suggestions for a specific weekly plan",
)
async def get_suggestions(
    plan_id: UUID,
    user_skill_level: ProficiencyLevel = Query(default="beginner"),
    user_id: UUID = Depends(get_current_user_id),
    service: ProjectSuggesterService = Depends(get_project_service),
) -> list[ProjectSuggestion]:
    """Retrieve or expand a balanced project portfolio for a weekly plan."""
    return await _get_or_expand_suggestions(
        service=service,
        plan_id=plan_id,
        user_skill_level=user_skill_level,
    )


@router.put(
    "/{project_id}/complete",
    response_model=ProjectSuggestion,
    summary="Mark a project as complete",
)
async def complete_project(
    project_id: UUID,
    body: CompleteProjectRequest,
    user_id: UUID = Depends(get_current_user_id),
    service: ProjectSuggesterService = Depends(get_project_service),
) -> ProjectSuggestion:
    """Mark a project suggestion as completed with an outcome description.

    Requirements: 7.4
    """
    await service.mark_project_completed(project_id=project_id, outcome=body.outcome)
    project = await service._get_project(project_id)
    return service._project_orm_to_schema(project)


@router.put(
    "/{project_id}/dismiss",
    response_model=ProjectSuggestion,
    summary="Dismiss a project suggestion",
)
async def dismiss_project(
    project_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    service: ProjectSuggesterService = Depends(get_project_service),
) -> ProjectSuggestion:
    """Dismiss a project suggestion so it no longer appears.

    Requirements: 7.6
    """
    await service.dismiss_project(project_id=project_id)
    project = await service._get_project(project_id)
    return service._project_orm_to_schema(project)


@router.post(
    "/skip/{plan_id}",
    summary="Skip all projects for a weekly plan milestone",
)
async def skip_projects(
    plan_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    service: ProjectSuggesterService = Depends(get_project_service),
) -> dict:
    """Skip all project suggestions for a given weekly plan milestone.

    Requirements: 7.6
    """
    await service.skip_all_projects(weekly_plan_id=plan_id)
    return {"message": "All projects for this milestone have been skipped"}
