"""Pydantic models for project suggestions."""

from uuid import UUID

from pydantic import BaseModel, Field

from .common import ProficiencyLevel


class ProjectSuggestion(BaseModel):
    id: UUID
    title: str
    objectives: list[str]
    deliverables: list[str]
    technologies: list[str]
    estimated_weeks: int = Field(ge=1, le=4)
    complexity: ProficiencyLevel
