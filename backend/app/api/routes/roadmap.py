"""Learning roadmap generation and management routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.openai_provider import OpenAIProvider
from app.api.deps import get_current_user_id
from app.core.database import get_db
from app.schemas.roadmap import LearningRoadmap
from app.services.roadmap_service import RoadmapService

router = APIRouter()


# ── Request models ─────────────────────────────────────────────────────────────


class GenerateRoadmapRequest(BaseModel):
    weekly_hours: int | None = Field(default=None, ge=1, le=40)


class UpdateHoursRequest(BaseModel):
    weekly_hours: int = Field(..., ge=1, le=40)


# ── Dependency helpers ─────────────────────────────────────────────────────────


def get_roadmap_service(
    db: AsyncSession = Depends(get_db),
) -> RoadmapService:
    """Dependency that constructs a RoadmapService with the current DB session and AI provider."""
    ai_provider = OpenAIProvider()
    return RoadmapService(db=db, ai_provider=ai_provider)


# ── Endpoints ──────────────────────────────────────────────────────────────────


@router.post(
    "/generate",
    response_model=LearningRoadmap,
    summary="Generate a personalised learning roadmap",
)
async def generate_roadmap(
    body: GenerateRoadmapRequest = GenerateRoadmapRequest(),
    user_id: UUID = Depends(get_current_user_id),
    service: RoadmapService = Depends(get_roadmap_service),
) -> LearningRoadmap:
    """Generate an AI-powered learning roadmap based on the skill gap analysis.

    Accepts optional weekly_hours (1-40). Defaults to 10 if not provided.
    Requires a completed skill gap analysis.

    Domain exceptions (InvalidWeeklyHoursError, NoGapAnalysisError) are handled
    by the registered exception handlers automatically.

    Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6
    """
    return await service.generate_roadmap(user_id=user_id, weekly_hours=body.weekly_hours)


@router.get(
    "/",
    response_model=LearningRoadmap,
    summary="Get the current learning roadmap",
)
async def get_roadmap(
    user_id: UUID = Depends(get_current_user_id),
    service: RoadmapService = Depends(get_roadmap_service),
) -> LearningRoadmap:
    """Retrieve the authenticated user's current learning roadmap.

    Returns 404 if no roadmap has been generated yet.

    Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6
    """
    roadmap = await service.get_roadmap(user_id=user_id)
    if roadmap is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "NO_ROADMAP_FOUND",
                "message": "No roadmap found. Please generate a roadmap first.",
            },
        )
    return roadmap


@router.put(
    "/hours",
    response_model=LearningRoadmap,
    summary="Update weekly study hours",
)
async def update_weekly_hours(
    body: UpdateHoursRequest,
    user_id: UUID = Depends(get_current_user_id),
    service: RoadmapService = Depends(get_roadmap_service),
) -> LearningRoadmap:
    """Update the number of weekly study hours and recalculate the roadmap timeline.

    Requires an existing roadmap. Returns 404 if no roadmap exists.

    Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6
    """
    roadmap = await service.get_roadmap(user_id=user_id)
    if roadmap is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "NO_ROADMAP_FOUND",
                "message": "No roadmap found. Please generate a roadmap first.",
            },
        )
    return await service.recalculate_timeline(
        roadmap_id=roadmap.id, new_weekly_hours=body.weekly_hours
    )
