"""Shared literal types and enums used across multiple schema modules."""

from typing import Literal

ProficiencyLevel = Literal["beginner", "intermediate", "advanced"]
GapCategory = Literal["critical", "important", "nice-to-have"]
PlanStatus = Literal["completed", "in-progress", "upcoming"]
ResourceType = Literal["course", "book", "tutorial", "documentation"]
QuestionCategory = Literal["technical", "behavioral", "system-design"]
