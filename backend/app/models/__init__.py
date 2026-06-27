"""ORM models package — imports all models so Alembic autogenerate can detect them."""

from .user import User
from .profile import Profile, Skill
from .target_role import TargetRole, SkillRequirement
from .skill_gap import SkillGapAnalysis, SkillGap
from .roadmap import LearningRoadmap, RoadmapTopic, LearningResource
from .weekly_plan import WeeklyPlan, WeeklyTask
from .project import ProjectSuggestion
from .interview import InterviewSession, InterviewQuestion, AnswerSubmission

__all__ = [
    "User",
    "Profile",
    "Skill",
    "TargetRole",
    "SkillRequirement",
    "SkillGapAnalysis",
    "SkillGap",
    "LearningRoadmap",
    "RoadmapTopic",
    "LearningResource",
    "WeeklyPlan",
    "WeeklyTask",
    "ProjectSuggestion",
    "InterviewSession",
    "InterviewQuestion",
    "AnswerSubmission",
]
