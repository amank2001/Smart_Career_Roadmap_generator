"""Pydantic models for target role selection and requirements."""

from uuid import UUID

from pydantic import BaseModel, Field

from .common import ProficiencyLevel, GapCategory


class SkillRequirement(BaseModel):
    skill_name: str
    required_proficiency: ProficiencyLevel
    category: GapCategory


class CustomRoleInput(BaseModel):
    role_title: str = Field(max_length=100)
    skills: list[SkillRequirement] = Field(min_length=3)
    responsibilities: str = Field(min_length=1)


class TargetRole(BaseModel):
    id: UUID
    user_id: UUID
    role_title: str
    is_recognized: bool
    skills: list[SkillRequirement]


class TargetRoleRequirements(BaseModel):
    role_title: str
    skills: list[SkillRequirement]  # at least 5 for recognized roles
    recognized: bool
