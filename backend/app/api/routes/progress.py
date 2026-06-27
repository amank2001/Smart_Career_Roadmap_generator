"""Progress tracking routes."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id
from app.core.database import get_db
from app.schemas.progress import ProgressSummary, TimelineEntry
from app.services.progress_service import ProgressService

router = APIRouter()


# ── Dependency helpers ─────────────────────────────────────────────────────────


def get_progress_service(
    db: AsyncSession = Depends(get_db),
) -> ProgressService:
    """Dependency that constructs a ProgressService with the current DB session."""
    return ProgressService(db=db)


# ── Endpoints ──────────────────────────────────────────────────────────────────


@router.get("", response_model=ProgressSummary, summary="Get overall progress summary")
async def get_progress(
    user_id: UUID = Depends(get_current_user_id),
    service: ProgressService = Depends(get_progress_service),
) -> ProgressSummary:
    """Retrieve a summary of the authenticated user's overall learning progress.

    Returns the completion percentage (0-100), count of completed and total plans,
    and a list of skills acquired from completed plans.

    Domain exceptions (RoadmapNotFoundError) are handled by the registered
    exception handlers automatically.

    Requirements: 8.1, 8.4, 8.5
    """
    return await service.get_overall_progress(user_id=user_id)


@router.get(
    "/timeline",
    response_model=list[TimelineEntry],
    summary="Get progress timeline",
)
async def get_timeline(
    user_id: UUID = Depends(get_current_user_id),
    service: ProgressService = Depends(get_progress_service),
) -> list[TimelineEntry]:
    """Retrieve the full timeline of weekly plan completions and statuses.

    Returns an ordered list showing each plan's status (completed, in-progress,
    upcoming) and the skills covered in each week.

    Domain exceptions (RoadmapNotFoundError) are handled by the registered
    exception handlers automatically.

    Requirements: 8.1, 8.3, 8.5
    """
    return await service.get_timeline(user_id=user_id)
