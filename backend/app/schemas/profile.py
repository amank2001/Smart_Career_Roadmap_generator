"""Pydantic models for user profile management."""

from uuid import UUID

from pydantic import BaseModel, Field

from .common import ProficiencyLevel


class Skill(BaseModel):
    name: str = Field(max_length=60)
    proficiency_level: ProficiencyLevel | None = None


class CreateProfileInput(BaseModel):
    current_job_title: str = Field(max_length=100)
    years_of_experience: int = Field(ge=0, le=50)
    skills: list[Skill] = Field(min_length=1, max_length=50)


class UpdateProfileInput(BaseModel):
    current_job_title: str | None = Field(default=None, max_length=100)
    years_of_experience: int | None = Field(default=None, ge=0, le=50)
    skills: list[Skill] | None = Field(default=None, min_length=1, max_length=50)


class Profile(BaseModel):
    id: UUID
    user_id: UUID
    current_job_title: str
    years_of_experience: int
    skills: list[Skill]
    is_complete: bool
