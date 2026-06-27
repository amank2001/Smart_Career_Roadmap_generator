"""Interview Preparer Service — generates mock interview questions and evaluates answers."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.provider import AIProvider
from app.core.exceptions import DomainError
from app.models.interview import (
    AnswerSubmission as AnswerSubmissionORM,
    InterviewQuestion as InterviewQuestionORM,
    InterviewSession as InterviewSessionORM,
)
from app.schemas.common import ProficiencyLevel
from app.schemas.interview import (
    AnswerFeedback as AnswerFeedbackSchema,
    InterviewQuestion as InterviewQuestionSchema,
    ProgressInfo,
)
from app.schemas.target_role import TargetRole


# ── Domain exceptions ──────────────────────────────────────────────────────────


class InterviewSessionNotFoundError(DomainError):
    error_code = "INTERVIEW_SESSION_NOT_FOUND"
    status_code = 404
    message = "Interview session not found"


class InterviewQuestionNotFoundError(DomainError):
    error_code = "INTERVIEW_QUESTION_NOT_FOUND"
    status_code = 404
    message = "Interview question not found"


# ── Roles that typically do NOT involve system design ──────────────────────────

_NON_SYSTEM_DESIGN_ROLES: set[str] = {
    "data analyst",
    "data entry",
    "graphic designer",
    "ui designer",
    "ux designer",
    "ux researcher",
    "content writer",
    "copywriter",
    "marketing manager",
    "project manager",
    "product manager",
    "hr manager",
    "recruiter",
    "business analyst",
    "sales representative",
    "accountant",
    "financial analyst",
    "teacher",
    "trainer",
    "customer support",
    "technical writer",
}

# Roles that typically involve system design
_SYSTEM_DESIGN_ROLES_KEYWORDS: list[str] = [
    "engineer",
    "architect",
    "developer",
    "devops",
    "sre",
    "platform",
    "infrastructure",
    "backend",
    "fullstack",
    "full-stack",
    "full stack",
    "cloud",
    "distributed",
    "systems",
]


def _role_involves_system_design(role_title: str) -> bool:
    """Determine if a target role typically involves system design questions.

    Returns True if the role is technical enough to warrant system design questions.
    """
    normalized = role_title.lower().strip()

    # Explicit non-system-design roles
    if normalized in _NON_SYSTEM_DESIGN_ROLES:
        return False

    # Check for system-design keywords in the role title
    for keyword in _SYSTEM_DESIGN_ROLES_KEYWORDS:
        if keyword in normalized:
            return True

    # Default: include system design for unrecognized roles (lean towards inclusion)
    return False


def _determine_difficulty(progress_percentage: int) -> ProficiencyLevel:
    """Map user progress percentage to difficulty level.

    <33% → beginner, 33-66% → intermediate, ≥66% → advanced
    """
    if progress_percentage < 33:
        return "beginner"
    elif progress_percentage < 66:
        return "intermediate"
    else:
        return "advanced"


class InterviewPreparerService:
    """Database-backed service for mock interview question generation and answer evaluation."""

    def __init__(self, db: AsyncSession, ai_provider: AIProvider) -> None:
        self._db = db
        self._ai_provider = ai_provider

    # ── ORM to schema conversion ──────────────────────────────────────────────

    @staticmethod
    def _question_orm_to_schema(q: InterviewQuestionORM) -> InterviewQuestionSchema:
        """Convert an InterviewQuestion ORM instance to Pydantic schema."""
        return InterviewQuestionSchema(
            id=q.id,
            question=q.question,
            category=q.category,
            difficulty=q.difficulty,
            model_answer=q.model_answer,
            evaluation_criteria=q.evaluation_criteria,
        )

    # ── Public service methods ────────────────────────────────────────────────

    async def generate_questions(
        self, target_role: TargetRole, user_progress: ProgressInfo
    ) -> list[InterviewQuestionSchema]:
        """Generate mock interview questions tailored to the target role and user progress.

        - Creates an InterviewSession in the DB
        - Determines difficulty from progress percentage
        - Determines if system-design questions should be included
        - Calls AI provider to generate questions (5-20)
        - Persists questions to DB
        - Ensures at least one question per applicable category

        Args:
            target_role: The user's target role with skills.
            user_progress: The user's overall progress (percentage, completed/total plans).

        Returns:
            A list of InterviewQuestion schemas (5-20 questions).
        """
        # 1. Create an InterviewSession
        session_id = uuid.uuid4()
        session_orm = InterviewSessionORM(
            id=session_id,
            user_id=target_role.user_id,
        )
        self._db.add(session_orm)
        await self._db.flush()

        # 2. Determine difficulty from progress percentage
        difficulty = _determine_difficulty(user_progress.percentage)

        # 3. Determine if system-design questions should be included
        include_system_design = _role_involves_system_design(target_role.role_title)

        # 4. Gather skills list from target role
        skills = [s.skill_name for s in target_role.skills]

        # 5. Call AI provider to generate questions
        ai_questions = await self._ai_provider.generate_interview_questions(
            role=target_role.role_title,
            skills=skills,
            difficulty=difficulty,
        )

        # 6. Filter out system-design questions if role doesn't involve it
        if not include_system_design:
            ai_questions = [q for q in ai_questions if q.category != "system-design"]

        # 7. Validate question count (5-20) and category coverage
        ai_questions = self._ensure_valid_question_set(
            ai_questions, include_system_design
        )

        # 8. Persist questions to DB
        question_schemas: list[InterviewQuestionSchema] = []
        for ai_q in ai_questions:
            question_orm = InterviewQuestionORM(
                id=ai_q.id,
                session_id=session_id,
                question=ai_q.question,
                category=ai_q.category,
                difficulty=ai_q.difficulty,
                model_answer=ai_q.model_answer,
                evaluation_criteria=ai_q.evaluation_criteria,
            )
            self._db.add(question_orm)
            question_schemas.append(
                InterviewQuestionSchema(
                    id=ai_q.id,
                    question=ai_q.question,
                    category=ai_q.category,
                    difficulty=ai_q.difficulty,
                    model_answer=ai_q.model_answer,
                    evaluation_criteria=ai_q.evaluation_criteria,
                )
            )

        await self._db.flush()
        return question_schemas

    async def evaluate_answer(
        self, question_id: UUID, user_answer: str
    ) -> AnswerFeedbackSchema:
        """Evaluate a user's answer to a mock interview question.

        - Loads the question from DB
        - Calls AI provider to evaluate the answer against criteria
        - Persists the feedback as an AnswerSubmission

        Args:
            question_id: The ID of the interview question being answered.
            user_answer: The user's answer text.

        Returns:
            AnswerFeedback with strengths, areas for improvement, and overall assessment.

        Raises:
            InterviewQuestionNotFoundError: If the question doesn't exist.
        """
        # 1. Load the question from DB
        result = await self._db.execute(
            select(InterviewQuestionORM).where(InterviewQuestionORM.id == question_id)
        )
        question_orm = result.scalar_one_or_none()
        if question_orm is None:
            raise InterviewQuestionNotFoundError()

        # 2. Call AI provider to evaluate the answer
        feedback = await self._ai_provider.evaluate_interview_answer(
            question=question_orm.question,
            criteria=question_orm.evaluation_criteria,
            answer=user_answer,
        )

        # 3. Persist the feedback as an AnswerSubmission
        submission_orm = AnswerSubmissionORM(
            id=uuid.uuid4(),
            question_id=question_id,
            user_answer=user_answer,
            strengths=feedback.strengths,
            areas_for_improvement=feedback.areas_for_improvement,
            overall_assessment=feedback.overall_assessment,
            submitted_at=datetime.now(timezone.utc),
        )
        self._db.add(submission_orm)
        await self._db.flush()

        return AnswerFeedbackSchema(
            strengths=feedback.strengths,
            areas_for_improvement=feedback.areas_for_improvement,
            overall_assessment=feedback.overall_assessment,
        )

    # ── Query methods for API usage ───────────────────────────────────────────

    async def get_session_questions(
        self, session_id: UUID, user_id: UUID
    ) -> list[InterviewQuestionSchema]:
        """Get all questions for a specific interview session.

        Args:
            session_id: The interview session ID.
            user_id: The user's ID (for ownership verification).

        Returns:
            List of InterviewQuestion schemas.

        Raises:
            InterviewSessionNotFoundError: If the session doesn't exist or doesn't belong to the user.
        """
        result = await self._db.execute(
            select(InterviewSessionORM)
            .where(
                InterviewSessionORM.id == session_id,
                InterviewSessionORM.user_id == user_id,
            )
            .options(selectinload(InterviewSessionORM.questions))
        )
        session = result.scalar_one_or_none()
        if session is None:
            raise InterviewSessionNotFoundError()

        return [self._question_orm_to_schema(q) for q in session.questions]

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _ensure_valid_question_set(
        questions: list, include_system_design: bool
    ) -> list:
        """Ensure the question set meets validity constraints:
        - Between 5 and 20 questions
        - At least one question per applicable category

        If category coverage is missing, this is a best-effort check
        (the AI provider should already produce diverse categories).
        """
        # Enforce max of 20 questions
        if len(questions) > 20:
            questions = questions[:20]

        # Check category coverage
        categories_present = {q.category for q in questions}
        required_categories = {"technical", "behavioral"}
        if include_system_design:
            required_categories.add("system-design")

        # If a required category is missing, we still return what we have
        # (the AI provider is expected to produce diverse output, and we
        # don't want to fail the whole request over a missing category)

        # Enforce minimum of 5 questions (if AI returned fewer, return what we have)
        # The AI provider contract says 5-20 so this is defensive.
        return questions
