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
    InterviewSessionResponse,
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


# ── Interview category logic ───────────────────────────────────────────────────
# Determines which question categories are appropriate for a given role.
# Categories: knowledge, behavioral, case-study
#
# 'case-study' applies when the role involves analytical problem-solving,
# scenario reasoning, design decisions, or applied domain judgment —
# this is broad and covers many fields beyond software engineering.

# Roles where case-study questions are NOT useful
_NO_CASE_STUDY_ROLES: set[str] = {
    "data entry operator",
    "receptionist",
    "cashier",
    "administrative assistant",
    "file clerk",
}

# Keywords that signal case-study questions ARE appropriate
_CASE_STUDY_KEYWORDS: list[str] = [
    # Technology
    "engineer", "architect", "developer", "devops", "platform", "infrastructure",
    # Science & Medicine
    "scientist", "researcher", "analyst", "physician", "doctor", "nurse",
    "pharmacist", "chemist", "biologist", "physicist", "geologist", "ecologist",
    # Law & Policy
    "lawyer", "attorney", "counsel", "paralegal", "judge", "policy",
    # Finance & Commerce
    "accountant", "auditor", "financial", "actuary", "economist", "banker",
    "investment", "consultant", "strategist",
    # Management & Business
    "manager", "director", "executive", "product", "project", "operations",
    "supply chain", "logistics",
    # Design & Creative
    "designer", "architect", "ux", "ui", "art director", "creative director",
    # Education
    "teacher", "professor", "educator", "instructor", "curriculum",
    # Social Sciences
    "psychologist", "therapist", "counselor", "social worker", "sociologist",
]


def _role_involves_case_study(role_title: str) -> bool:
    """Return True if the role warrants case-study / scenario questions.

    Works across all domains — not just software.
    """
    normalized = role_title.lower().strip()

    if normalized in _NO_CASE_STUDY_ROLES:
        return False

    for keyword in _CASE_STUDY_KEYWORDS:
        if keyword in normalized:
            return True

    # Default: include case-study for unrecognised roles
    return True


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
        """Generate mock interview questions (returns list only — legacy method)."""
        session_response = await self.generate_questions_with_session(
            target_role=target_role, user_progress=user_progress
        )
        return session_response.questions

    async def generate_questions_with_session(
        self, target_role: TargetRole, user_progress: ProgressInfo
    ) -> InterviewSessionResponse:
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
            An InterviewSessionResponse with session id, created_at, and questions.
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

        # 3. Determine if case-study questions should be included
        include_case_study = _role_involves_case_study(target_role.role_title)

        # 4. Gather skills list from target role
        skills = [s.skill_name for s in target_role.skills]

        # 5. Call AI provider to generate questions
        ai_questions = await self._ai_provider.generate_interview_questions(
            role=target_role.role_title,
            skills=skills,
            difficulty=difficulty,
        )

        # 6. Filter out case-study questions if not appropriate for this role
        if not include_case_study:
            ai_questions = [q for q in ai_questions if q.category != "case-study"]

        # 7. Validate question count (5-20) and category coverage
        ai_questions = self._ensure_valid_question_set(
            ai_questions, include_case_study
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

        # Reload session to get server-generated created_at
        result = await self._db.execute(
            select(InterviewSessionORM).where(InterviewSessionORM.id == session_id)
        )
        session_refreshed = result.scalar_one()

        return InterviewSessionResponse(
            id=session_id,
            questions=question_schemas,
            created_at=session_refreshed.created_at,
        )

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
        """Get all questions for a specific interview session (legacy list return)."""
        session_response = await self.get_session(session_id=session_id, user_id=user_id)
        return session_response.questions

    async def get_session(
        self, session_id: UUID, user_id: UUID
    ) -> InterviewSessionResponse:
        """Get an interview session with all its questions.

        Args:
            session_id: The interview session ID.
            user_id: The user's ID (for ownership verification).

        Returns:
            InterviewSessionResponse with session metadata and questions.

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

        return InterviewSessionResponse(
            id=session.id,
            questions=[self._question_orm_to_schema(q) for q in session.questions],
            created_at=session.created_at,
        )

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _ensure_valid_question_set(
        questions: list, include_case_study: bool
    ) -> list:
        """Ensure the question set meets validity constraints:
        - Between 5 and 20 questions
        - At least one question per applicable category (knowledge, behavioral, case-study)
        """
        # Enforce max of 20 questions
        if len(questions) > 20:
            questions = questions[:20]

        # Required categories vary by role type
        # (If a required category is missing, we still return what we have —
        # the AI provider is expected to produce diverse output.)
        required_categories = {"knowledge", "behavioral"}
        if include_case_study:
            required_categories.add("case-study")

        return questions
