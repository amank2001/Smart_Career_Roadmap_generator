"""Project suggestion routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.openai_provider import OpenAIProvider
from app.api.deps import get_current_user_id
from app.core.database import get_db
from app.schemas.common import ProficiencyLevel
from app.schemas.project import ProjectSuggestion
from app.services.project_service import ProjectSuggesterService

router = APIRouter()


# ── Request body models ────────────────────────────────────────────────────────


class CompleteProjectRequest(BaseModel):
    """Request body for marking a project as complete."""

    outcome: str = Field(min_length=1, max_length=500)


# ── Dependency helpers ─────────────────────────────────────────────────────────


def get_project_service(
    db: AsyncSession = Depends(get_db),
) -> ProjectSuggesterService:
    """Dependency that constructs a ProjectSuggesterService with the current DB session and AI provider."""
    ai_provider = OpenAIProvider()
    return ProjectSuggesterService(db=db, ai_provider=ai_provider)


# ── Endpoints ──────────────────────────────────────────────────────────────────


@router.get(
    "/suggestions/{plan_id}",
    response_model=list[ProjectSuggestion],
    summary="Get project suggestions for a weekly plan",
)
async def get_suggestions(
    plan_id: UUID,
    user_skill_level: ProficiencyLevel = Query(default="beginner"),
    user_id: UUID = Depends(get_current_user_id),
    service: ProjectSuggesterService = Depends(get_project_service),
) -> list[ProjectSuggestion]:
    """Retrieve AI-generated project suggestions for a specific weekly plan milestone.

    If suggestions already exist for this plan, returns the existing ones.
    Otherwise, generates new suggestions based on the milestone's skills.

    Requirements: 7.1, 7.2, 7.3, 7.5
    """
    # Check if suggestions already exist for this plan
    existing = await service.get_suggestions_for_plan(weekly_plan_id=plan_id)
    if existing:
        return existing

    # Generate new suggestions
    return await service.suggest_projects(
        weekly_plan_id=plan_id,
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
    # Return the updated project
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
    # Return the updated project
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

    This dismisses all active projects for the plan, allowing the user
    to proceed without completing any project.

    Requirements: 7.6
    """
    await service.skip_all_projects(weekly_plan_id=plan_id)
    return {"message": "All projects for this milestone have been skipped"}
