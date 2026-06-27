"""AI provider abstraction package.

Public API
----------
AIProvider        – Protocol (structural interface)
OpenAIProvider    – Concrete implementation backed by the OpenAI API
AITimeoutError    – Raised when an AI call times out            (→ HTTP 504)
AIUnavailableError – Raised when the AI service is unreachable  (→ HTTP 503)
AIResponseError   – Raised on malformed / unexpected responses  (→ HTTP 500)

Domain value objects (Pydantic) re-exported for convenience:
    Skill, SkillRequirement, SkillGap,
    RoadmapTopic, LearningResource,
    InterviewQuestion, AnswerFeedback,
    ProjectSuggestion,
    ProficiencyLevel, GapCategory
"""

from app.ai.exceptions import AIResponseError, AITimeoutError, AIUnavailableError
from app.ai.openai_provider import OpenAIProvider
from app.ai.provider import (
    AIProvider,
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

__all__ = [
    # Protocol
    "AIProvider",
    # Concrete provider
    "OpenAIProvider",
    # Exceptions
    "AITimeoutError",
    "AIUnavailableError",
    "AIResponseError",
    # Domain types
    "Skill",
    "SkillRequirement",
    "SkillGap",
    "RoadmapTopic",
    "LearningResource",
    "InterviewQuestion",
    "AnswerFeedback",
    "ProjectSuggestion",
    "ProficiencyLevel",
    "GapCategory",
]
