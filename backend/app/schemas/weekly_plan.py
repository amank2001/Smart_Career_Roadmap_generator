"""Pydantic models for weekly learning plans."""

from uuid import UUID

from pydantic import BaseModel, Field

from .common import PlanStatus


class WeeklyTask(BaseModel):
    id: UUID
    description: str
    estimated_hours: float
    skill_name: str
    completion_criterion: str
    completed: bool


class WeeklyPlan(BaseModel):
    id: UUID
    roadmap_id: UUID
    week_number: int
    status: PlanStatus
    tasks: list[WeeklyTask] = Field(min_length=3, max_length=7)
    is_practical_milestone: bool


class RoadmapCompletionSummary(BaseModel):
    """Response schema returned when the final plan is completed."""

    roadmap_id: UUID
    is_complete: bool
    total_weeks: int
    skills_acquired: list[str]
    message: str
