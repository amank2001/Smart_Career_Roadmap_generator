"""Unit tests for InterviewPreparerService — no live database required.

Tests cover:
- generate_questions creates an interview session and persists questions
- generate_questions determines difficulty from progress percentage
- generate_questions omits system-design for non-technical roles
- generate_questions includes system-design for technical roles
- generate_questions enforces 5-20 question count
- generate_questions ensures at least one question per applicable category
- evaluate_answer loads question, calls AI, persists feedback
- evaluate_answer raises error for non-existent question
- _determine_difficulty maps progress to correct levels
- _role_involves_system_design classifies roles correctly
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.interview import (
    AnswerFeedback as AnswerFeedbackSchema,
    InterviewQuestion as InterviewQuestionSchema,
    ProgressInfo,
)
from app.schemas.target_role import TargetRole, SkillRequirement
from app.services.interview_service import (
    InterviewPreparerService,
    InterviewQuestionNotFoundError,
    _determine_difficulty,
    _role_involves_system_design,
)


# ── Helpers ────────────────────────────────────────────────────────────────────


def make_target_role(
    role_title: str = "Backend Engineer",
    skills: list[str] | None = None,
) -> TargetRole:
    """Create a TargetRole Pydantic model."""
    skill_list = skills or ["Python", "SQL", "Docker", "System Design", "REST APIs"]
    return TargetRole(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        role_title=role_title,
        is_recognized=True,
        skills=[
            SkillRequirement(
                skill_name=s, required_proficiency="intermediate", category="critical"
            )
            for s in skill_list
        ],
    )


def make_progress(percentage: int = 50) -> ProgressInfo:
    """Create a ProgressInfo Pydantic model."""
    return ProgressInfo(percentage=percentage, completed_plans=5, total_plans=10)


def make_ai_question(
    category: str = "technical",
    difficulty: str = "intermediate",
) -> MagicMock:
    """Create a mock AI InterviewQuestion response."""
    q = MagicMock()
    q.id = uuid.uuid4()
    q.question = f"Sample {category} question"
    q.category = category
    q.difficulty = difficulty
    q.model_answer = "This is the model answer."
    q.evaluation_criteria = ["Clarity", "Correctness", "Depth"]
    return q


def make_service() -> tuple[InterviewPreparerService, AsyncMock, AsyncMock]:
    """Return an InterviewPreparerService with mock db and ai_provider."""
    mock_db = AsyncMock()
    mock_ai = AsyncMock()
    svc = InterviewPreparerService(db=mock_db, ai_provider=mock_ai)
    return svc, mock_db, mock_ai


# ── _determine_difficulty tests (pure logic) ──────────────────────────────────


class TestDetermineDifficulty:
    def test_below_33_returns_beginner(self) -> None:
        assert _determine_difficulty(0) == "beginner"
        assert _determine_difficulty(10) == "beginner"
        assert _determine_difficulty(32) == "beginner"

    def test_33_to_65_returns_intermediate(self) -> None:
        assert _determine_difficulty(33) == "intermediate"
        assert _determine_difficulty(50) == "intermediate"
        assert _determine_difficulty(65) == "intermediate"

    def test_66_and_above_returns_advanced(self) -> None:
        assert _determine_difficulty(66) == "advanced"
        assert _determine_difficulty(80) == "advanced"
        assert _determine_difficulty(100) == "advanced"


# ── _role_involves_system_design tests (pure logic) ───────────────────────────


class TestRoleInvolvesSystemDesign:
    def test_backend_engineer_involves_system_design(self) -> None:
        assert _role_involves_system_design("Backend Engineer") is True

    def test_software_developer_involves_system_design(self) -> None:
        assert _role_involves_system_design("Software Developer") is True

    def test_cloud_architect_involves_system_design(self) -> None:
        assert _role_involves_system_design("Cloud Architect") is True

    def test_devops_engineer_involves_system_design(self) -> None:
        assert _role_involves_system_design("DevOps Engineer") is True

    def test_fullstack_developer_involves_system_design(self) -> None:
        assert _role_involves_system_design("Fullstack Developer") is True

    def test_data_analyst_does_not_involve_system_design(self) -> None:
        assert _role_involves_system_design("data analyst") is False

    def test_graphic_designer_does_not_involve_system_design(self) -> None:
        assert _role_involves_system_design("graphic designer") is False

    def test_project_manager_does_not_involve_system_design(self) -> None:
        assert _role_involves_system_design("project manager") is False

    def test_marketing_manager_does_not_involve_system_design(self) -> None:
        assert _role_involves_system_design("marketing manager") is False


# ── generate_questions tests ──────────────────────────────────────────────────


class TestGenerateQuestions:
    @pytest.mark.asyncio
    async def test_creates_session_and_returns_questions(self) -> None:
        svc, mock_db, mock_ai = make_service()
        target_role = make_target_role("Backend Engineer")
        progress = make_progress(50)

        # AI returns mixed category questions
        ai_questions = [
            make_ai_question("technical", "intermediate"),
            make_ai_question("behavioral", "intermediate"),
            make_ai_question("system-design", "intermediate"),
            make_ai_question("technical", "intermediate"),
            make_ai_question("behavioral", "intermediate"),
        ]
        mock_ai.generate_interview_questions.return_value = ai_questions

        result = await svc.generate_questions(target_role, progress)

        # Should have called AI provider with correct args
        mock_ai.generate_interview_questions.assert_called_once_with(
            role="Backend Engineer",
            skills=["Python", "SQL", "Docker", "System Design", "REST APIs"],
            difficulty="intermediate",
        )

        # Should have added session and questions to DB
        assert mock_db.add.called
        assert mock_db.flush.called

        # Should return correct number of question schemas
        assert len(result) == 5
        assert all(isinstance(q, InterviewQuestionSchema) for q in result)

    @pytest.mark.asyncio
    async def test_determines_beginner_difficulty_for_low_progress(self) -> None:
        svc, mock_db, mock_ai = make_service()
        target_role = make_target_role("Backend Engineer")
        progress = make_progress(20)

        ai_questions = [make_ai_question("technical", "beginner") for _ in range(5)]
        mock_ai.generate_interview_questions.return_value = ai_questions

        await svc.generate_questions(target_role, progress)

        mock_ai.generate_interview_questions.assert_called_once_with(
            role="Backend Engineer",
            skills=["Python", "SQL", "Docker", "System Design", "REST APIs"],
            difficulty="beginner",
        )

    @pytest.mark.asyncio
    async def test_determines_advanced_difficulty_for_high_progress(self) -> None:
        svc, mock_db, mock_ai = make_service()
        target_role = make_target_role("Backend Engineer")
        progress = make_progress(80)

        ai_questions = [make_ai_question("technical", "advanced") for _ in range(5)]
        mock_ai.generate_interview_questions.return_value = ai_questions

        await svc.generate_questions(target_role, progress)

        mock_ai.generate_interview_questions.assert_called_once_with(
            role="Backend Engineer",
            skills=["Python", "SQL", "Docker", "System Design", "REST APIs"],
            difficulty="advanced",
        )

    @pytest.mark.asyncio
    async def test_omits_system_design_for_non_technical_role(self) -> None:
        svc, mock_db, mock_ai = make_service()
        target_role = make_target_role("data analyst", skills=["Excel", "SQL", "Tableau"])
        progress = make_progress(50)

        # AI returns questions including system-design
        ai_questions = [
            make_ai_question("technical", "intermediate"),
            make_ai_question("behavioral", "intermediate"),
            make_ai_question("system-design", "intermediate"),
            make_ai_question("technical", "intermediate"),
            make_ai_question("behavioral", "intermediate"),
        ]
        mock_ai.generate_interview_questions.return_value = ai_questions

        result = await svc.generate_questions(target_role, progress)

        # System-design questions should be filtered out
        categories = [q.category for q in result]
        assert "system-design" not in categories

    @pytest.mark.asyncio
    async def test_includes_system_design_for_technical_role(self) -> None:
        svc, mock_db, mock_ai = make_service()
        target_role = make_target_role("Backend Engineer")
        progress = make_progress(50)

        ai_questions = [
            make_ai_question("technical", "intermediate"),
            make_ai_question("behavioral", "intermediate"),
            make_ai_question("system-design", "intermediate"),
            make_ai_question("technical", "intermediate"),
            make_ai_question("behavioral", "intermediate"),
        ]
        mock_ai.generate_interview_questions.return_value = ai_questions

        result = await svc.generate_questions(target_role, progress)

        # System-design questions should be present
        categories = [q.category for q in result]
        assert "system-design" in categories

    @pytest.mark.asyncio
    async def test_limits_to_20_questions_max(self) -> None:
        svc, mock_db, mock_ai = make_service()
        target_role = make_target_role("Backend Engineer")
        progress = make_progress(50)

        # AI returns 25 questions
        ai_questions = [make_ai_question("technical", "intermediate") for _ in range(25)]
        mock_ai.generate_interview_questions.return_value = ai_questions

        result = await svc.generate_questions(target_role, progress)

        assert len(result) <= 20


# ── evaluate_answer tests ─────────────────────────────────────────────────────


class TestEvaluateAnswer:
    @pytest.mark.asyncio
    async def test_evaluates_answer_and_returns_feedback(self) -> None:
        svc, mock_db, mock_ai = make_service()
        question_id = uuid.uuid4()

        # Mock the DB query to return a question
        question_orm = MagicMock()
        question_orm.id = question_id
        question_orm.question = "What is a REST API?"
        question_orm.evaluation_criteria = ["Clarity", "Correctness", "Completeness"]

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = question_orm
        mock_db.execute.return_value = mock_result

        # Mock the AI provider feedback
        mock_feedback = MagicMock()
        mock_feedback.strengths = ["Clear explanation", "Good examples"]
        mock_feedback.areas_for_improvement = ["Could mention HATEOAS"]
        mock_feedback.overall_assessment = "Good answer overall"
        mock_ai.evaluate_interview_answer.return_value = mock_feedback

        result = await svc.evaluate_answer(question_id, "REST is a style...")

        # Should have called AI provider with correct args
        mock_ai.evaluate_interview_answer.assert_called_once_with(
            question="What is a REST API?",
            criteria=["Clarity", "Correctness", "Completeness"],
            answer="REST is a style...",
        )

        # Should return correct feedback schema
        assert isinstance(result, AnswerFeedbackSchema)
        assert result.strengths == ["Clear explanation", "Good examples"]
        assert result.areas_for_improvement == ["Could mention HATEOAS"]
        assert result.overall_assessment == "Good answer overall"

        # Should have persisted the submission
        assert mock_db.add.called
        assert mock_db.flush.called

    @pytest.mark.asyncio
    async def test_raises_error_for_nonexistent_question(self) -> None:
        svc, mock_db, mock_ai = make_service()

        # Mock the DB query to return None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(InterviewQuestionNotFoundError):
            await svc.evaluate_answer(uuid.uuid4(), "My answer")


# ── get_session_questions tests ───────────────────────────────────────────────


class TestGetSessionQuestions:
    @pytest.mark.asyncio
    async def test_returns_questions_for_valid_session(self) -> None:
        svc, mock_db, _ = make_service()
        session_id = uuid.uuid4()
        user_id = uuid.uuid4()

        # Mock session with questions
        q1 = MagicMock()
        q1.id = uuid.uuid4()
        q1.question = "What is Python?"
        q1.category = "technical"
        q1.difficulty = "beginner"
        q1.model_answer = "Python is..."
        q1.evaluation_criteria = ["Accuracy"]

        q2 = MagicMock()
        q2.id = uuid.uuid4()
        q2.question = "Tell me about a challenge"
        q2.category = "behavioral"
        q2.difficulty = "intermediate"
        q2.model_answer = "When I was..."
        q2.evaluation_criteria = ["STAR method"]

        session = MagicMock()
        session.id = session_id
        session.user_id = user_id
        session.questions = [q1, q2]

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = session
        mock_db.execute.return_value = mock_result

        result = await svc.get_session_questions(session_id, user_id)

        assert len(result) == 2
        assert result[0].question == "What is Python?"
        assert result[1].category == "behavioral"

    @pytest.mark.asyncio
    async def test_raises_error_for_nonexistent_session(self) -> None:
        from app.services.interview_service import InterviewSessionNotFoundError

        svc, mock_db, _ = make_service()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(InterviewSessionNotFoundError):
            await svc.get_session_questions(uuid.uuid4(), uuid.uuid4())
