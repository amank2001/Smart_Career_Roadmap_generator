"""Mock interview preparation routes."""

import math
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.openai_provider import OpenAIProvider
from app.api.deps import get_current_user_id
from app.core.database import get_db
from app.models.roadmap import LearningRoadmap as LearningRoadmapORM
from app.models.target_role import TargetRole as TargetRoleORM
from app.models.weekly_plan import WeeklyPlan as WeeklyPlanORM
from app.schemas.interview import (
    AnswerFeedback,
    InterviewQuestion,
    InterviewSessionResponse,
    ProgressInfo,
)
from app.schemas.target_role import SkillRequirement, TargetRole
from app.services.interview_service import InterviewPreparerService

router = APIRouter()


# ── Request body models ────────────────────────────────────────────────────────


class AnswerRequest(BaseModel):
    """Request body for submitting an answer to an interview question."""

    answer: str = Field(min_length=1)


# ── Dependency helpers ─────────────────────────────────────────────────────────


def get_interview_service(
    db: AsyncSession = Depends(get_db),
) -> InterviewPreparerService:
    """Dependency that constructs an InterviewPreparerService."""
    ai_provider = OpenAIProvider()
    return InterviewPreparerService(db=db, ai_provider=ai_provider)


# ── Internal helpers ───────────────────────────────────────────────────────────


async def _fetch_target_role(db: AsyncSession, user_id: UUID) -> TargetRole:
    """Fetch the user's saved target role or raise 422."""
    result = await db.execute(
        select(TargetRoleORM)
        .where(TargetRoleORM.user_id == user_id)
        .options(selectinload(TargetRoleORM.skill_requirements))
    )
    orm = result.scalar_one_or_none()
    if orm is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "NO_TARGET_ROLE",
                "message": "Please set a target role before generating interview questions.",
            },
        )
    return TargetRole(
        id=orm.id,
        user_id=orm.user_id,
        role_title=orm.role_title,
        is_recognized=orm.is_recognized,
        skills=[
            SkillRequirement(
                skill_name=sr.skill_name,
                required_proficiency=sr.required_proficiency,
                category=sr.category,
            )
            for sr in orm.skill_requirements
        ],
    )


async def _fetch_progress(db: AsyncSession, user_id: UUID) -> ProgressInfo:
    """Compute a lightweight progress summary directly from the DB."""
    # Get the latest roadmap
    result = await db.execute(
        select(LearningRoadmapORM)
        .where(LearningRoadmapORM.user_id == user_id)
        .order_by(LearningRoadmapORM.created_at.desc())
        .options(selectinload(LearningRoadmapORM.weekly_plans))
        .limit(1)
    )
    roadmap = result.scalar_one_or_none()

    if roadmap is None or not roadmap.weekly_plans:
        return ProgressInfo(percentage=0, completed_plans=0, total_plans=0)

    total = len(roadmap.weekly_plans)
    completed = sum(1 for p in roadmap.weekly_plans if p.status == "completed")
    percentage = math.floor(completed / total * 100)
    return ProgressInfo(percentage=percentage, completed_plans=completed, total_plans=total)


# ── Endpoints ──────────────────────────────────────────────────────────────────


@router.post(
    "/generate",
    response_model=InterviewSessionResponse,
    summary="Generate mock interview questions",
)
async def generate_questions(
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    service: InterviewPreparerService = Depends(get_interview_service),
) -> InterviewSessionResponse:
    """Generate mock interview questions tailored to the user's target role and progress.

    Fetches target role and progress automatically from the database — no
    request body needed.

    Requirements: 6.1, 6.2, 6.3, 6.4, 6.6
    """
    target_role = await _fetch_target_role(db, user_id)
    progress = await _fetch_progress(db, user_id)

    return await service.generate_questions_with_session(
        target_role=target_role,
        user_progress=progress,
    )


@router.get(
    "/sessions/{session_id}",
    response_model=InterviewSessionResponse,
    summary="Get questions for an interview session",
)
async def get_session(
    session_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    service: InterviewPreparerService = Depends(get_interview_service),
) -> InterviewSessionResponse:
    """Retrieve all questions for a specific mock interview session.

    Requirements: 6.1
    """
    return await service.get_session(session_id=session_id, user_id=user_id)


@router.post(
    "/questions/{question_id}/answer",
    response_model=AnswerFeedback,
    summary="Submit an answer and receive AI feedback",
)
async def answer_question(
    question_id: UUID,
    body: AnswerRequest,
    user_id: UUID = Depends(get_current_user_id),
    service: InterviewPreparerService = Depends(get_interview_service),
) -> AnswerFeedback:
    """Submit a user's answer to a mock interview question and get AI-generated feedback.

    Requirements: 6.5
    """
    return await service.evaluate_answer(
        question_id=question_id,
        user_answer=body.answer,
    )
