"""Service Protocol interfaces for all domain services.

These Protocol classes define the contracts that concrete service
implementations must satisfy, enabling dependency injection and testability.
"""

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from app.schemas.common import ProficiencyLevel
from app.schemas.interview import AnswerFeedback, InterviewQuestion, ProgressInfo
from app.schemas.profile import CreateProfileInput, Profile, Skill, UpdateProfileInput
from app.schemas.progress import ProgressSummary, TimelineEntry
from app.schemas.project import ProjectSuggestion
from app.schemas.roadmap import LearningRoadmap, RoadmapTopic
from app.schemas.skill_gap import SkillGap, SkillGapAnalysis
from app.schemas.target_role import CustomRoleInput, SkillRequirement, TargetRole, TargetRoleRequirements
from app.schemas.weekly_plan import WeeklyPlan


# ── Resume Analyzer supporting types ──────────────────────────────────────────

class ValidationResult(Protocol):
    valid: bool
    error: str | None


class ResumeAnalysisResult(Protocol):
    success: bool
    extracted_data: dict | None  # skills, job_history, years_of_experience
    error: str | None


@dataclass
class UploadedFile:
    content: bytes
    mime_type: str
    original_name: str
    size_bytes: int


# ── 1. Profile Service ─────────────────────────────────────────────────────────

class ProfileService(Protocol):
    async def create_profile(self, user_id: UUID, data: CreateProfileInput) -> Profile: ...
    async def update_profile(self, user_id: UUID, data: UpdateProfileInput) -> Profile: ...
    async def get_profile(self, user_id: UUID) -> Profile | None: ...
    def is_profile_complete(self, profile: Profile) -> bool: ...


# ── 2. Resume Analyzer Service ─────────────────────────────────────────────────

class ResumeAnalyzerService(Protocol):
    async def analyze_resume(self, file: UploadedFile) -> "ResumeAnalysisResultModel": ...
    def get_supported_formats(self) -> list[str]: ...
    def validate_file_format(self, file: UploadedFile) -> "ValidationResultModel": ...


# ── 3. Target Role Service ─────────────────────────────────────────────────────

class TargetRoleService(Protocol):
    async def set_target_role(self, user_id: UUID, role_title: str) -> TargetRole: ...
    async def get_target_role_requirements(self, role_title: str) -> TargetRoleRequirements: ...
    async def update_target_role_skills(
        self, user_id: UUID, skills: list[SkillRequirement]
    ) -> TargetRole: ...
    async def is_role_recognized(self, role_title: str) -> bool: ...
    async def set_custom_role(self, user_id: UUID, data: CustomRoleInput) -> TargetRole: ...


# ── 4. Skill Gap Analyzer Service ─────────────────────────────────────────────

class SkillGapAnalyzerService(Protocol):
    async def analyze_gaps(self, profile: Profile, target_role: TargetRole) -> SkillGapAnalysis: ...


# ── 5. Roadmap Generator Service ──────────────────────────────────────────────

class RoadmapGeneratorService(Protocol):
    async def generate_roadmap(
        self, gaps: SkillGapAnalysis, weekly_hours: int
    ) -> LearningRoadmap: ...
    async def recalculate_timeline(
        self, roadmap_id: UUID, new_weekly_hours: int
    ) -> LearningRoadmap: ...


# ── 6. Weekly Plan Service ─────────────────────────────────────────────────────

class WeeklyPlanService(Protocol):
    async def generate_weekly_plans(self, roadmap: LearningRoadmap) -> list[WeeklyPlan]: ...
    async def mark_task_complete(self, plan_id: UUID, task_id: UUID) -> WeeklyPlan: ...
    async def advance_to_next_plan(self, user_id: UUID) -> WeeklyPlan | None: ...
    async def adjust_for_delay(self, user_id: UUID) -> list[WeeklyPlan]: ...


# ── 7. Interview Preparer Service ─────────────────────────────────────────────

class InterviewPreparerService(Protocol):
    async def generate_questions(
        self, target_role: TargetRole, user_progress: ProgressInfo
    ) -> list[InterviewQuestion]: ...
    async def evaluate_answer(
        self, question_id: UUID, user_answer: str
    ) -> AnswerFeedback: ...


# ── 8. Project Suggester Service ──────────────────────────────────────────────

class ProjectSuggesterService(Protocol):
    async def suggest_projects(
        self, milestone: WeeklyPlan, user_skill_level: ProficiencyLevel
    ) -> list[ProjectSuggestion]: ...  # at least 2
    async def mark_project_completed(self, project_id: UUID, outcome: str) -> None: ...


# ── 9. Progress Tracking Service ──────────────────────────────────────────────

class ProgressTrackingService(Protocol):
    async def get_overall_progress(self, user_id: UUID) -> ProgressSummary: ...
    async def update_skill_proficiency(self, user_id: UUID, plan_id: UUID) -> None: ...
    async def get_timeline(self, user_id: UUID) -> list[TimelineEntry]: ...


# ── Concrete return-type models used by ResumeAnalyzerService ─────────────────
# (defined here as Pydantic models to avoid circular imports)

from pydantic import BaseModel


class ValidationResultModel(BaseModel):
    valid: bool
    error: str | None = None


class ResumeAnalysisResultModel(BaseModel):
    success: bool
    extracted_data: dict | None = None  # skills, job_history, years_of_experience
    error: str | None = None
