"""Pydantic schema package — convenience re-exports of key types."""

# Common literal types
from .common import (
    GapCategory,
    PlanStatus,
    ProficiencyLevel,
    QuestionCategory,
    ResourceType,
)

# Auth
from .auth import Token, TokenData, UserCreate, UserLogin

# Profile
from .profile import CreateProfileInput, Profile, Skill, UpdateProfileInput

# Target Role
from .target_role import CustomRoleInput, SkillRequirement, TargetRole, TargetRoleRequirements

# Skill Gap
from .skill_gap import SkillGap, SkillGapAnalysis

# Roadmap
from .roadmap import LearningResource, LearningRoadmap, RoadmapTopic

# Weekly Plan
from .weekly_plan import RoadmapCompletionSummary, WeeklyPlan, WeeklyTask

# Interview
from .interview import AnswerFeedback, InterviewQuestion, ProgressInfo

# Project
from .project import ProjectSuggestion

# Progress
from .progress import ProgressSummary, TimelineEntry

__all__ = [
    # common
    "GapCategory",
    "PlanStatus",
    "ProficiencyLevel",
    "QuestionCategory",
    "ResourceType",
    # auth
    "Token",
    "TokenData",
    "UserCreate",
    "UserLogin",
    # profile
    "CreateProfileInput",
    "Profile",
    "Skill",
    "UpdateProfileInput",
    # target role
    "CustomRoleInput",
    "SkillRequirement",
    "TargetRole",
    "TargetRoleRequirements",
    # skill gap
    "SkillGap",
    "SkillGapAnalysis",
    # roadmap
    "LearningResource",
    "LearningRoadmap",
    "RoadmapTopic",
    # weekly plan
    "RoadmapCompletionSummary",
    "WeeklyPlan",
    "WeeklyTask",
    # interview
    "AnswerFeedback",
    "InterviewQuestion",
    "ProgressInfo",
    # project
    "ProjectSuggestion",
    # progress
    "ProgressSummary",
    "TimelineEntry",
]
