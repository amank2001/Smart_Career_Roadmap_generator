"""Pydantic models for skill gap analysis results."""

from pydantic import BaseModel

from .common import GapCategory, ProficiencyLevel


class SkillGap(BaseModel):
    skill_name: str
    category: GapCategory
    current_proficiency: ProficiencyLevel | None
    required_proficiency: ProficiencyLevel


class SkillGapAnalysis(BaseModel):
    gaps: list[SkillGap]
    all_requirements_met: bool
    advanced_specializations: list[str] | None = None  # at least 3 when all requirements met
