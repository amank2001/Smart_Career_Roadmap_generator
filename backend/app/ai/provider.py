"""AI provider Protocol and Pydantic domain types for the AI abstraction layer."""

from __future__ import annotations

from typing import Literal, Protocol, runtime_checkable
from uuid import UUID

from pydantic import BaseModel, Field


# ── Shared type aliases ────────────────────────────────────────────────────────

ProficiencyLevel = Literal["beginner", "intermediate", "advanced"]
GapCategory = Literal["critical", "important", "nice-to-have"]


# ── Domain value objects (Pydantic) ────────────────────────────────────────────
# These are lightweight data-transfer objects used by the AI layer. They are
# intentionally separate from the SQLAlchemy ORM models so that AI responses
# can be validated without a database session.


class Skill(BaseModel):
    """A skill with an optional proficiency level."""

    name: str = Field(max_length=60)
    proficiency_level: ProficiencyLevel | None = None


class SkillRequirement(BaseModel):
    """A skill required by a target role."""

    skill_name: str
    required_proficiency: ProficiencyLevel
    category: GapCategory


class SkillGap(BaseModel):
    """A single skill gap between the user's current skills and target role."""

    skill_name: str
    category: GapCategory
    current_proficiency: ProficiencyLevel | None
    required_proficiency: ProficiencyLevel


class LearningResource(BaseModel):
    """A learning resource (course, book, tutorial, or documentation)."""

    title: str
    type: Literal["course", "book", "tutorial", "documentation"]
    url: str | None = None


class RoadmapTopic(BaseModel):
    """A topic in a generated learning roadmap."""

    id: UUID
    skill_name: str
    category: GapCategory
    proficiency_target: ProficiencyLevel
    prerequisites: list[UUID]
    resources: list[LearningResource] = Field(min_length=2)
    estimated_hours: int
    order: int


class InterviewQuestion(BaseModel):
    """A mock interview question with model answer and evaluation criteria."""

    id: UUID
    question: str
    category: Literal["technical", "behavioral", "system-design"]
    difficulty: ProficiencyLevel
    model_answer: str
    evaluation_criteria: list[str] = Field(min_length=1)


class AnswerFeedback(BaseModel):
    """Feedback for a user's answer to a mock interview question."""

    strengths: list[str]
    areas_for_improvement: list[str]
    overall_assessment: str


class ProjectSuggestion(BaseModel):
    """A hands-on project suggestion for a learning milestone."""

    id: UUID
    title: str
    objectives: list[str]
    deliverables: list[str]
    technologies: list[str]
    estimated_weeks: int = Field(ge=1, le=4)
    complexity: ProficiencyLevel


# ── AIProvider Protocol ────────────────────────────────────────────────────────


@runtime_checkable
class AIProvider(Protocol):
    """Protocol that all AI provider implementations must satisfy.

    Implementations should raise the appropriate domain exception from
    ``app.core.exceptions`` when an error occurs:

    * ``AITimeoutError``      – request timed out (→ HTTP 504)
    * ``AIUnavailableError``  – provider is down / rate-limited (→ HTTP 503)
    * ``AIResponseError``     – malformed or unexpected response (→ HTTP 500)
    """

    async def analyze_resume(self, content: str, format: str) -> dict:
        """Extract skills, job history, and experience from resume text."""
        ...

    async def identify_role_skills(self, role_title: str) -> list[SkillRequirement]:
        """Return the skills and competencies required for the given role."""
        ...

    async def analyze_skill_gaps(
        self,
        current_skills: list[Skill],
        target_skills: list[SkillRequirement],
    ) -> list[SkillGap]:
        """Compare the user's skills against target role requirements."""
        ...

    async def generate_roadmap(
        self,
        gaps: list[SkillGap],
        constraints: dict,
    ) -> list[RoadmapTopic]:
        """Generate an ordered learning roadmap for the given skill gaps."""
        ...

    async def generate_interview_questions(
        self,
        role: str,
        skills: list[str],
        difficulty: ProficiencyLevel,
    ) -> list[InterviewQuestion]:
        """Generate mock interview questions for the given role and skills."""
        ...

    async def evaluate_interview_answer(
        self,
        question: str,
        criteria: list[str],
        answer: str,
    ) -> AnswerFeedback:
        """Evaluate a user's answer and return structured feedback."""
        ...

    async def suggest_projects(
        self,
        skills: list[str],
        level: ProficiencyLevel,
    ) -> list[ProjectSuggestion]:
        """Suggest at least two hands-on projects for the given skills."""
        ...
