"""Pydantic models for progress tracking."""

from uuid import UUID

from pydantic import BaseModel

from .common import PlanStatus


class ProgressSummary(BaseModel):
    percentage: int  # 0-100
    completed_plans: int
    total_plans: int
    skills_acquired: list[str]


class TimelineEntry(BaseModel):
    week_number: int
    plan_id: UUID
    status: PlanStatus
    skills: list[str]
