"""Mock interview preparation routes."""

from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.openai_provider import OpenAIProvider
from app.api.deps import get_current_user_id
from app.core.database import get_db
from app.schemas.interview import (
    AnswerFeedback,
    InterviewQuestion,
    ProgressInfo,
)
from app.schemas.target_role import TargetRole
from app.services.interview_service import InterviewPreparerService

router = APIRouter()


# ── Request body models ────────────────────────────────────────────────────────


class GenerateQuestionsRequest(BaseModel):
    """Request body for generating interview questions."""

    target_role: TargetRole
    progress: ProgressInfo


class AnswerRequest(BaseModel):
    """Request body for submitting an answer to an interview question."""

    answer: str = Field(min_length=1)


# ── Dependency helpers ─────────────────────────────────────────────────────────


def get_interview_service(
    db: AsyncSession = Depends(get_db),
) -> InterviewPreparerService:
    """Dependency that constructs an InterviewPreparerService with the current DB session and AI provider."""
    ai_provider = OpenAIProvider()
    return InterviewPreparerService(db=db, ai_provider=ai_provider)


# ── Endpoints ──────────────────────────────────────────────────────────────────


@router.post(
    "/generate",
    response_model=list[InterviewQuestion],
    summary="Generate mock interview questions",
)
async def generate_questions(
    body: GenerateQuestionsRequest,
    user_id: UUID = Depends(get_current_user_id),
    service: InterviewPreparerService = Depends(get_interview_service),
) -> list[InterviewQuestion]:
    """Generate a set of mock interview questions tailored to the target role and user progress.

    Requirements: 6.1, 6.2, 6.3, 6.4, 6.6
    """
    return await service.generate_questions(
        target_role=body.target_role,
        user_progress=body.progress,
    )


@router.get(
    "/sessions/{session_id}",
    response_model=list[InterviewQuestion],
    summary="Get questions for an interview session",
)
async def get_session(
    session_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    service: InterviewPreparerService = Depends(get_interview_service),
) -> list[InterviewQuestion]:
    """Retrieve all questions for a specific mock interview session.

    Requirements: 6.1
    """
    return await service.get_session_questions(session_id=session_id, user_id=user_id)


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
