"""Concrete OpenAI implementation of the AIProvider Protocol.

Each public method:
  1. Builds a structured prompt requesting a JSON response.
  2. Calls the OpenAI chat completions API using the async client.
  3. Parses and validates the JSON response with Pydantic.
  4. Wraps errors in the appropriate domain exception.
  5. Is decorated with tenacity retry logic (3 attempts, exponential backoff)
     for transient failures (timeout / unavailability).
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

import httpx
import openai
from openai import AsyncOpenAI
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)

from app.ai.exceptions import AIResponseError, AITimeoutError, AIUnavailableError
from app.ai.provider import (
    AnswerFeedback,
    GapCategory,
    InterviewQuestion,
    LearningResource,
    ProficiencyLevel,
    ProjectSuggestion,
    RoadmapTopic,
    Skill,
    SkillGap,
    SkillRequirement,
)
from app.core.config import settings

logger = logging.getLogger(__name__)

# ── Retry decorator factory ───────────────────────────────────────────────────
# Retries on transient errors only; validation / auth errors are not retried.

_TRANSIENT_EXCEPTIONS = (
    openai.APITimeoutError,
    openai.APIConnectionError,
    openai.RateLimitError,
    openai.InternalServerError,
    httpx.TimeoutException,
    httpx.ConnectError,
)

_retry_transient = retry(
    retry=retry_if_exception_type(_TRANSIENT_EXCEPTIONS),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=False,  # We handle the final exception ourselves
)


# ── Helper ────────────────────────────────────────────────────────────────────


def _parse_json(raw: str | None, context: str) -> Any:
    """Parse JSON string from an AI response; raise AIResponseError on failure."""
    if not raw:
        raise AIResponseError(f"Empty response from AI for {context}")
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AIResponseError(
            f"Malformed JSON in AI response for {context}: {exc}"
        ) from exc


# ── OpenAI Provider ───────────────────────────────────────────────────────────


class OpenAIProvider:
    """Async OpenAI-backed implementation of AIProvider.

    Uses ``gpt-4o-mini`` by default for cost efficiency; override via
    ``model`` constructor argument.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gpt-4o-mini",
        timeout: float | None = None,
    ) -> None:
        self._model = model
        resolved_key = api_key or settings.openai_api_key
        resolved_timeout = timeout or float(settings.ai_timeout_seconds)
        self._client = AsyncOpenAI(
            api_key=resolved_key,
            timeout=resolved_timeout,
        )

    # ── Internal call helper ──────────────────────────────────────────────────

    async def _chat(self, system_prompt: str, user_prompt: str) -> str:
        """Call OpenAI chat completions and return the assistant message text.

        Wraps tenacity retry inside this helper so that all public methods
        share a single retry policy without repeating the decorator.
        """

        async def _call_with_retry() -> str:
            last_exc: Exception | None = None
            for attempt in range(1, 4):  # up to 3 attempts
                try:
                    response = await self._client.chat.completions.create(
                        model=self._model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        response_format={"type": "json_object"},
                        temperature=0.2,
                    )
                    content = response.choices[0].message.content
                    if content is None:
                        raise AIResponseError("OpenAI returned a null message content")
                    return content
                except (
                    openai.APITimeoutError,
                    httpx.TimeoutException,
                ) as exc:
                    last_exc = exc
                    logger.warning(
                        "OpenAI timeout on attempt %d/3: %s", attempt, exc
                    )
                    if attempt == 3:
                        raise AITimeoutError() from exc
                except (
                    openai.APIConnectionError,
                    openai.RateLimitError,
                    openai.InternalServerError,
                    httpx.ConnectError,
                ) as exc:
                    last_exc = exc
                    logger.warning(
                        "OpenAI unavailable on attempt %d/3: %s", attempt, exc
                    )
                    if attempt == 3:
                        raise AIUnavailableError() from exc
                except openai.AuthenticationError as exc:
                    # Non-transient: don't retry
                    raise AIUnavailableError(
                        "OpenAI authentication failed. Check OPENAI_API_KEY."
                    ) from exc
                except AIResponseError:
                    raise
                except Exception as exc:
                    raise AIResponseError(
                        f"Unexpected error during OpenAI call: {exc}"
                    ) from exc

                # Exponential back-off between attempts: 1s, 2s
                import asyncio
                await asyncio.sleep(2 ** (attempt - 1))

            # Should not reach here, but satisfy type checker
            raise AIUnavailableError() from last_exc

        return await _call_with_retry()

    # ── Public methods ────────────────────────────────────────────────────────

    async def analyze_resume(self, content: str, format: str) -> dict:
        """Extract structured information from resume text.

        Returns a dict with keys: skills, job_history, years_of_experience.
        """
        system = (
            "You are an expert resume parser. "
            "Extract information from the resume and return ONLY valid JSON "
            "with keys: skills (array of strings), job_history "
            "(array of {title, company, years}), years_of_experience (integer)."
        )
        user = f"Resume format: {format}\n\nResume content:\n{content}"
        raw = await self._chat(system, user)
        data = _parse_json(raw, "analyze_resume")
        if not isinstance(data, dict):
            raise AIResponseError("analyze_resume: expected a JSON object")
        return data

    async def identify_role_skills(self, role_title: str) -> list[SkillRequirement]:
        """Return at least 5 skills required for the given role."""
        system = (
            "You are a career coach with deep knowledge of role requirements. "
            "Return ONLY valid JSON: an object with a 'skills' key containing "
            "an array of skill objects. Each object must have: "
            "skill_name (string), required_proficiency (beginner|intermediate|advanced), "
            "category (critical|important|nice-to-have)."
        )
        user = f"List the skills and competencies required for: {role_title}"
        raw = await self._chat(system, user)
        data = _parse_json(raw, "identify_role_skills")
        try:
            items: list[dict] = data.get("skills", data) if isinstance(data, dict) else data
            return [SkillRequirement(**item) for item in items]
        except (KeyError, TypeError, ValueError) as exc:
            raise AIResponseError(
                f"identify_role_skills: invalid structure: {exc}"
            ) from exc

    async def analyze_skill_gaps(
        self,
        current_skills: list[Skill],
        target_skills: list[SkillRequirement],
    ) -> list[SkillGap]:
        """Compare user skills against target role requirements."""
        system = (
            "You are a skill gap analysis expert. "
            "Return ONLY valid JSON: an object with a 'gaps' key containing "
            "an array of gap objects. Each object must have: "
            "skill_name (string), category (critical|important|nice-to-have), "
            "current_proficiency (beginner|intermediate|advanced or null), "
            "required_proficiency (beginner|intermediate|advanced)."
        )
        current = [s.model_dump() for s in current_skills]
        target = [r.model_dump() for r in target_skills]
        user = (
            f"Current skills: {json.dumps(current)}\n"
            f"Target role requirements: {json.dumps(target)}\n"
            "Identify which skills are missing or insufficient."
        )
        raw = await self._chat(system, user)
        data = _parse_json(raw, "analyze_skill_gaps")
        try:
            items: list[dict] = data.get("gaps", data) if isinstance(data, dict) else data
            return [SkillGap(**item) for item in items]
        except (KeyError, TypeError, ValueError) as exc:
            raise AIResponseError(
                f"analyze_skill_gaps: invalid structure: {exc}"
            ) from exc

    async def generate_roadmap(
        self,
        gaps: list[SkillGap],
        constraints: dict,
    ) -> list[RoadmapTopic]:
        """Generate an ordered learning roadmap for the given gaps."""
        system = (
            "You are a learning roadmap designer. "
            "Return ONLY valid JSON: an object with a 'topics' key containing "
            "an array of topic objects. Each object must have: "
            "id (UUID string), skill_name, category (critical|important|nice-to-have), "
            "proficiency_target (beginner|intermediate|advanced), "
            "prerequisites (array of UUID strings), "
            "resources (array of {title, type, url} with type in "
            "course|book|tutorial|documentation — at least 2 per topic), "
            "estimated_hours (integer), order (integer starting at 1). "
            "Order topics so prerequisites appear before dependents, "
            "and critical gaps are ordered before important before nice-to-have."
        )
        gap_data = [g.model_dump() for g in gaps]
        user = (
            f"Skill gaps: {json.dumps(gap_data)}\n"
            f"Constraints: {json.dumps(constraints)}\n"
            "Generate the learning roadmap."
        )
        raw = await self._chat(system, user)
        data = _parse_json(raw, "generate_roadmap")
        try:
            items: list[dict] = (
                data.get("topics", data) if isinstance(data, dict) else data
            )
            # Build a mapping from AI-generated IDs to real UUIDs so
            # prerequisite references stay consistent across topics.
            id_mapping: dict[str, str] = {}
            for item in items:
                original_id = str(item.get("id", ""))
                real_id = str(uuid.uuid4())
                id_mapping[original_id] = real_id
                item["id"] = real_id

            topics = []
            for item in items:
                # Remap prerequisite IDs to real UUIDs; drop any that
                # don't correspond to a topic in this set.
                raw_prereqs = item.get("prerequisites", [])
                item["prerequisites"] = [
                    id_mapping[str(p)]
                    for p in raw_prereqs
                    if str(p) in id_mapping
                ]
                topics.append(RoadmapTopic(**item))
            return topics
        except (KeyError, TypeError, ValueError) as exc:
            raise AIResponseError(
                f"generate_roadmap: invalid structure: {exc}"
            ) from exc

    async def generate_interview_questions(
        self,
        role: str,
        skills: list[str],
        difficulty: ProficiencyLevel,
    ) -> list[InterviewQuestion]:
        """Generate 5-20 mock interview questions for the given role."""
        system = (
            "You are an experienced technical interviewer. "
            "Return ONLY valid JSON: an object with a 'questions' key containing "
            "an array of question objects. Each object must have: "
            "id (UUID string), question (string), "
            "category (technical|behavioral|system-design), "
            "difficulty (beginner|intermediate|advanced), "
            "model_answer (string), evaluation_criteria (array of strings, min 1). "
            "Include at least one question from each applicable category. "
            "Generate between 5 and 20 questions."
        )
        user = (
            f"Role: {role}\n"
            f"Relevant skills: {json.dumps(skills)}\n"
            f"Difficulty level: {difficulty}\n"
            "Generate mock interview questions."
        )
        raw = await self._chat(system, user)
        data = _parse_json(raw, "generate_interview_questions")
        try:
            items: list[dict] = (
                data.get("questions", data) if isinstance(data, dict) else data
            )
            questions = []
            for item in items:
                # Always generate a proper UUID regardless of what AI returns
                item["id"] = str(uuid.uuid4())
                questions.append(InterviewQuestion(**item))
            return questions
        except (KeyError, TypeError, ValueError) as exc:
            raise AIResponseError(
                f"generate_interview_questions: invalid structure: {exc}"
            ) from exc

    async def evaluate_interview_answer(
        self,
        question: str,
        criteria: list[str],
        answer: str,
    ) -> AnswerFeedback:
        """Evaluate a user's answer and return structured feedback."""
        system = (
            "You are a rigorous interview coach providing constructive feedback. "
            "Return ONLY valid JSON with keys: "
            "strengths (array of strings), "
            "areas_for_improvement (array of strings), "
            "overall_assessment (string)."
        )
        user = (
            f"Question: {question}\n"
            f"Evaluation criteria: {json.dumps(criteria)}\n"
            f"Candidate answer: {answer}\n"
            "Evaluate the answer and provide feedback."
        )
        raw = await self._chat(system, user)
        data = _parse_json(raw, "evaluate_interview_answer")
        try:
            return AnswerFeedback(**data)
        except (TypeError, ValueError) as exc:
            raise AIResponseError(
                f"evaluate_interview_answer: invalid structure: {exc}"
            ) from exc

    async def suggest_projects(
        self,
        skills: list[str],
        level: ProficiencyLevel,
    ) -> list[ProjectSuggestion]:
        """Suggest at least two hands-on projects for the given skills."""
        system = (
            "You are a project mentor specializing in practical skill development. "
            "Return ONLY valid JSON: an object with a 'projects' key containing "
            "an array of project objects. Each object must have: "
            "id (UUID string), title (string), objectives (array of strings), "
            "deliverables (array of strings), technologies (array of strings), "
            "estimated_weeks (integer 1-4), complexity (beginner|intermediate|advanced). "
            "Return at least 2 projects."
        )
        user = (
            f"Skills: {json.dumps(skills)}\n"
            f"Skill level: {level}\n"
            "Suggest practical projects to build these skills."
        )
        raw = await self._chat(system, user)
        data = _parse_json(raw, "suggest_projects")
        try:
            items: list[dict] = (
                data.get("projects", data) if isinstance(data, dict) else data
            )
            projects = []
            for item in items:
                # Always generate a proper UUID regardless of what AI returns
                item["id"] = str(uuid.uuid4())
                projects.append(ProjectSuggestion(**item))
            return projects
        except (KeyError, TypeError, ValueError) as exc:
            raise AIResponseError(
                f"suggest_projects: invalid structure: {exc}"
            ) from exc
