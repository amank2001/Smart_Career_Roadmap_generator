"""Pydantic models for learning roadmap generation."""

from uuid import UUID

from pydantic import BaseModel, Field

from .common import GapCategory, ProficiencyLevel, ResourceType


class LearningResource(BaseModel):
    title: str
    type: ResourceType
    url: str | None = None


class RoadmapTopic(BaseModel):
    id: UUID
    skill_name: str
    category: GapCategory
    proficiency_target: ProficiencyLevel
    prerequisites: list[UUID]  # IDs of prerequisite topics
    resources: list[LearningResource] = Field(min_length=2)
    estimated_hours: int
    order: int


class LearningRoadmap(BaseModel):
    id: UUID
    user_id: UUID
    topics: list[RoadmapTopic]
    total_weeks: int
    weekly_study_hours: int
