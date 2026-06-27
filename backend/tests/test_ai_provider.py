"""Tests for the AI provider abstraction layer.

Tests cover:
  - Protocol structural subtyping (OpenAIProvider satisfies AIProvider)
  - Correct parsing of well-formed mock responses for each method
  - AITimeoutError raised on timeout conditions
  - AIUnavailableError raised on connection / rate-limit errors
  - AIResponseError raised on malformed JSON / unexpected structure
  - Retry logic: up to 3 attempts on transient errors
"""

from __future__ import annotations

import json
import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import openai
import pytest

from app.ai import (
    AIProvider,
    AIResponseError,
    AITimeoutError,
    AIUnavailableError,
    AnswerFeedback,
    InterviewQuestion,
    OpenAIProvider,
    ProjectSuggestion,
    RoadmapTopic,
    Skill,
    SkillGap,
    SkillRequirement,
)


# ── Fixtures ───────────────────────────────────────────────────────────────────


@pytest.fixture
def provider() -> OpenAIProvider:
    """Return an OpenAIProvider with a dummy API key (no real HTTP calls)."""
    return OpenAIProvider(api_key="sk-test-dummy", model="gpt-4o-mini", timeout=5.0)


def _make_chat_response(content: str) -> MagicMock:
    """Build a minimal mock that mimics an openai ChatCompletion response."""
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


# ── 1. Protocol conformance ────────────────────────────────────────────────────


def test_openai_provider_satisfies_ai_provider_protocol(provider: OpenAIProvider) -> None:
    """OpenAIProvider must be a structural subtype of AIProvider at runtime."""
    assert isinstance(provider, AIProvider), (
        "OpenAIProvider does not satisfy the AIProvider Protocol"
    )


# ── 2. analyze_resume ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_analyze_resume_parses_well_formed_response(provider: OpenAIProvider) -> None:
    payload = {
        "skills": ["Python", "FastAPI"],
        "job_history": [{"title": "Engineer", "company": "Acme", "years": 2}],
        "years_of_experience": 2,
    }
    mock_resp = _make_chat_response(json.dumps(payload))

    with patch.object(
        provider._client.chat.completions, "create", new=AsyncMock(return_value=mock_resp)
    ):
        result = await provider.analyze_resume("Resume text here", "text/plain")

    assert result["skills"] == ["Python", "FastAPI"]
    assert result["years_of_experience"] == 2


@pytest.mark.asyncio
async def test_analyze_resume_raises_ai_response_error_on_invalid_json(
    provider: OpenAIProvider,
) -> None:
    mock_resp = _make_chat_response("not-valid-json{{{")

    with patch.object(
        provider._client.chat.completions, "create", new=AsyncMock(return_value=mock_resp)
    ):
        with pytest.raises(AIResponseError):
            await provider.analyze_resume("text", "text/plain")


# ── 3. identify_role_skills ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_identify_role_skills_parses_well_formed_response(
    provider: OpenAIProvider,
) -> None:
    payload = {
        "skills": [
            {
                "skill_name": "Python",
                "required_proficiency": "advanced",
                "category": "critical",
            },
            {
                "skill_name": "Docker",
                "required_proficiency": "intermediate",
                "category": "important",
            },
        ]
    }
    mock_resp = _make_chat_response(json.dumps(payload))

    with patch.object(
        provider._client.chat.completions, "create", new=AsyncMock(return_value=mock_resp)
    ):
        result = await provider.identify_role_skills("Backend Engineer")

    assert len(result) == 2
    assert all(isinstance(r, SkillRequirement) for r in result)
    assert result[0].skill_name == "Python"
    assert result[0].category == "critical"


# ── 4. analyze_skill_gaps ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_analyze_skill_gaps_parses_well_formed_response(
    provider: OpenAIProvider,
) -> None:
    payload = {
        "gaps": [
            {
                "skill_name": "Kubernetes",
                "category": "critical",
                "current_proficiency": None,
                "required_proficiency": "intermediate",
            }
        ]
    }
    mock_resp = _make_chat_response(json.dumps(payload))
    current = [Skill(name="Python", proficiency_level="advanced")]
    target = [
        SkillRequirement(
            skill_name="Kubernetes",
            required_proficiency="intermediate",
            category="critical",
        )
    ]

    with patch.object(
        provider._client.chat.completions, "create", new=AsyncMock(return_value=mock_resp)
    ):
        result = await provider.analyze_skill_gaps(current, target)

    assert len(result) == 1
    assert isinstance(result[0], SkillGap)
    assert result[0].skill_name == "Kubernetes"
    assert result[0].current_proficiency is None


# ── 5. generate_roadmap ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_generate_roadmap_parses_well_formed_response(
    provider: OpenAIProvider,
) -> None:
    topic_id = str(uuid.uuid4())
    payload = {
        "topics": [
            {
                "id": topic_id,
                "skill_name": "Kubernetes",
                "category": "critical",
                "proficiency_target": "intermediate",
                "prerequisites": [],
                "resources": [
                    {"title": "Kubernetes Docs", "type": "documentation", "url": None},
                    {"title": "K8s Course", "type": "course", "url": "https://example.com"},
                ],
                "estimated_hours": 20,
                "order": 1,
            }
        ]
    }
    mock_resp = _make_chat_response(json.dumps(payload))
    gaps = [
        SkillGap(
            skill_name="Kubernetes",
            category="critical",
            current_proficiency=None,
            required_proficiency="intermediate",
        )
    ]

    with patch.object(
        provider._client.chat.completions, "create", new=AsyncMock(return_value=mock_resp)
    ):
        result = await provider.generate_roadmap(gaps, {"weekly_hours": 10})

    assert len(result) == 1
    assert isinstance(result[0], RoadmapTopic)
    assert result[0].skill_name == "Kubernetes"
    assert len(result[0].resources) == 2


# ── 6. generate_interview_questions ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_generate_interview_questions_parses_well_formed_response(
    provider: OpenAIProvider,
) -> None:
    q_id = str(uuid.uuid4())
    payload = {
        "questions": [
            {
                "id": q_id,
                "question": "Explain Python GIL.",
                "category": "technical",
                "difficulty": "intermediate",
                "model_answer": "The GIL is ...",
                "evaluation_criteria": ["Mentions threading", "Explains impact"],
            }
        ]
    }
    mock_resp = _make_chat_response(json.dumps(payload))

    with patch.object(
        provider._client.chat.completions, "create", new=AsyncMock(return_value=mock_resp)
    ):
        result = await provider.generate_interview_questions(
            "Backend Engineer", ["Python"], "intermediate"
        )

    assert len(result) == 1
    assert isinstance(result[0], InterviewQuestion)
    assert result[0].category == "technical"
    assert len(result[0].evaluation_criteria) == 2


# ── 7. evaluate_interview_answer ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_evaluate_interview_answer_parses_well_formed_response(
    provider: OpenAIProvider,
) -> None:
    payload = {
        "strengths": ["Clear explanation"],
        "areas_for_improvement": ["Could add an example"],
        "overall_assessment": "Good answer overall.",
    }
    mock_resp = _make_chat_response(json.dumps(payload))

    with patch.object(
        provider._client.chat.completions, "create", new=AsyncMock(return_value=mock_resp)
    ):
        result = await provider.evaluate_interview_answer(
            question="Explain the GIL.",
            criteria=["Mentions threading"],
            answer="The GIL prevents true parallelism.",
        )

    assert isinstance(result, AnswerFeedback)
    assert result.strengths == ["Clear explanation"]
    assert "example" in result.areas_for_improvement[0]


# ── 8. suggest_projects ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_suggest_projects_parses_well_formed_response(
    provider: OpenAIProvider,
) -> None:
    p_id = str(uuid.uuid4())
    payload = {
        "projects": [
            {
                "id": p_id,
                "title": "Build a CLI tool",
                "objectives": ["Learn argparse"],
                "deliverables": ["Working CLI"],
                "technologies": ["Python"],
                "estimated_weeks": 1,
                "complexity": "beginner",
            },
            {
                "id": str(uuid.uuid4()),
                "title": "REST API project",
                "objectives": ["Apply FastAPI"],
                "deliverables": ["Deployed API"],
                "technologies": ["Python", "FastAPI"],
                "estimated_weeks": 2,
                "complexity": "intermediate",
            },
        ]
    }
    mock_resp = _make_chat_response(json.dumps(payload))

    with patch.object(
        provider._client.chat.completions, "create", new=AsyncMock(return_value=mock_resp)
    ):
        result = await provider.suggest_projects(["Python", "FastAPI"], "beginner")

    assert len(result) == 2
    assert all(isinstance(p, ProjectSuggestion) for p in result)
    assert result[0].estimated_weeks == 1


# ── 9. Error handling: AITimeoutError ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_analyze_resume_raises_ai_timeout_on_openai_timeout(
    provider: OpenAIProvider,
) -> None:
    """Persistent openai.APITimeoutError should eventually raise AITimeoutError."""
    with patch.object(
        provider._client.chat.completions,
        "create",
        new=AsyncMock(side_effect=openai.APITimeoutError(request=MagicMock())),
    ):
        with pytest.raises(AITimeoutError):
            await provider.analyze_resume("Resume text", "text/plain")


# ── 10. Error handling: AIUnavailableError ────────────────────────────────────


@pytest.mark.asyncio
async def test_analyze_resume_raises_ai_unavailable_on_connection_error(
    provider: OpenAIProvider,
) -> None:
    """Persistent openai.APIConnectionError should raise AIUnavailableError."""
    with patch.object(
        provider._client.chat.completions,
        "create",
        new=AsyncMock(
            side_effect=openai.APIConnectionError(request=MagicMock())
        ),
    ):
        with pytest.raises(AIUnavailableError):
            await provider.analyze_resume("Resume text", "text/plain")


@pytest.mark.asyncio
async def test_analyze_resume_raises_ai_unavailable_on_rate_limit(
    provider: OpenAIProvider,
) -> None:
    """Persistent RateLimitError should raise AIUnavailableError after retries."""
    rate_limit_resp = MagicMock()
    rate_limit_resp.status_code = 429
    with patch.object(
        provider._client.chat.completions,
        "create",
        new=AsyncMock(
            side_effect=openai.RateLimitError(
                "rate limit exceeded",
                response=rate_limit_resp,
                body=None,
            )
        ),
    ):
        with pytest.raises(AIUnavailableError):
            await provider.analyze_resume("Resume text", "text/plain")


# ── 11. Error handling: AIResponseError ───────────────────────────────────────


@pytest.mark.asyncio
async def test_identify_role_skills_raises_ai_response_error_on_bad_structure(
    provider: OpenAIProvider,
) -> None:
    """Well-formed JSON but wrong field names should raise AIResponseError."""
    payload = {"skills": [{"wrong_field": "value"}]}
    mock_resp = _make_chat_response(json.dumps(payload))

    with patch.object(
        provider._client.chat.completions, "create", new=AsyncMock(return_value=mock_resp)
    ):
        with pytest.raises(AIResponseError):
            await provider.identify_role_skills("Data Engineer")


@pytest.mark.asyncio
async def test_evaluate_interview_answer_raises_ai_response_error_on_missing_keys(
    provider: OpenAIProvider,
) -> None:
    """Response missing required keys should raise AIResponseError."""
    payload = {"strengths": ["Good"]}  # missing areas_for_improvement, overall_assessment
    mock_resp = _make_chat_response(json.dumps(payload))

    with patch.object(
        provider._client.chat.completions, "create", new=AsyncMock(return_value=mock_resp)
    ):
        with pytest.raises(AIResponseError):
            await provider.evaluate_interview_answer("Q?", ["criteria"], "My answer")


# ── 12. Retry count verification ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_retry_logic_attempts_up_to_3_times_on_timeout(
    provider: OpenAIProvider,
) -> None:
    """Verify the implementation retries exactly 3 times (total) on timeout."""
    call_count = 0

    async def _side_effect(*args: Any, **kwargs: Any) -> None:
        nonlocal call_count
        call_count += 1
        raise openai.APITimeoutError(request=MagicMock())

    with patch.object(
        provider._client.chat.completions, "create", new=AsyncMock(side_effect=_side_effect)
    ):
        with pytest.raises(AITimeoutError):
            await provider.analyze_resume("text", "text/plain")

    assert call_count == 3, f"Expected 3 retry attempts, got {call_count}"


@pytest.mark.asyncio
async def test_retry_logic_succeeds_on_second_attempt(
    provider: OpenAIProvider,
) -> None:
    """If the first attempt fails with a timeout but the second succeeds, return the result."""
    payload = {
        "skills": ["Go"],
        "job_history": [],
        "years_of_experience": 1,
    }
    good_response = _make_chat_response(json.dumps(payload))
    call_count = 0

    async def _side_effect(*args: Any, **kwargs: Any) -> Any:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise openai.APITimeoutError(request=MagicMock())
        return good_response

    with patch.object(
        provider._client.chat.completions, "create", new=AsyncMock(side_effect=_side_effect)
    ):
        result = await provider.analyze_resume("text", "text/plain")

    assert call_count == 2
    assert result["skills"] == ["Go"]


# ── 13. AIProvider exception classes ──────────────────────────────────────────


def test_ai_timeout_error_has_correct_status_code() -> None:
    exc = AITimeoutError()
    assert exc.status_code == 504
    assert exc.error_code == "AI_TIMEOUT"


def test_ai_unavailable_error_has_correct_status_code() -> None:
    exc = AIUnavailableError()
    assert exc.status_code == 503
    assert exc.error_code == "AI_UNAVAILABLE"


def test_ai_response_error_has_correct_status_code() -> None:
    exc = AIResponseError()
    assert exc.status_code == 500
    assert exc.error_code == "AI_RESPONSE_ERROR"


def test_ai_errors_accept_custom_message() -> None:
    exc = AITimeoutError("custom message")
    assert exc.message == "custom message"
    assert str(exc) == "custom message"
