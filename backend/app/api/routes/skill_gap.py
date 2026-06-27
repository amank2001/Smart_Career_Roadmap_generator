"""Skill gap analysis routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.openai_provider import OpenAIProvider
from app.api.deps import get_current_user_id
from app.core.database import get_db
from app.schemas.skill_gap import SkillGapAnalysis
from app.services.skill_gap_service import SkillGapService

router = APIRouter()


# ── Dependency helpers ─────────────────────────────────────────────────────────


def get_skill_gap_service(
    db: AsyncSession = Depends(get_db),
) -> SkillGapService:
    """Dependency that constructs a SkillGapService with the current DB session and AI provider."""
    ai_provider = OpenAIProvider()
    return SkillGapService(db=db, ai_provider=ai_provider)


# ── Endpoints ──────────────────────────────────────────────────────────────────


@router.post(
    "/analyze",
    response_model=SkillGapAnalysis,
    summary="Run skill gap analysis",
)
async def analyze_skill_gap(
    user_id: UUID = Depends(get_current_user_id),
    service: SkillGapService = Depends(get_skill_gap_service),
) -> SkillGapAnalysis:
    """Run AI-powered skill gap analysis comparing profile skills to target role requirements.

    Compares the user's current skills against their target role requirements
    using AI analysis. Persists the result and returns it.

    Domain exceptions (IncompleteProfileError, NoTargetRoleError) are handled
    by the registered exception handlers automatically.

    Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6
    """
    return await service.analyze_gaps(user_id=user_id)


@router.get(
    "/results",
    response_model=SkillGapAnalysis,
    summary="Get latest skill gap analysis results",
)
async def get_results(
    user_id: UUID = Depends(get_current_user_id),
    service: SkillGapService = Depends(get_skill_gap_service),
) -> SkillGapAnalysis:
    """Retrieve the most recent skill gap analysis results for the authenticated user.

    Returns results grouped by category (core_technical, soft_skill,
    domain_knowledge, tools_platforms). Returns 404 if no analysis exists.

    Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6
    """
    result = await service.get_latest_analysis(user_id=user_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "NO_ANALYSIS_FOUND",
                "message": "No skill gap analysis found. Please run an analysis first.",
            },
        )
    return result
