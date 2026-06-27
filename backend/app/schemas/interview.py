"""Pydantic models for mock interview preparation."""

from uuid import UUID

from pydantic import BaseModel, Field

from .common import ProficiencyLevel, QuestionCategory


class InterviewQuestion(BaseModel):
    id: UUID
    question: str
    category: QuestionCategory
    difficulty: ProficiencyLevel
    model_answer: str
    evaluation_criteria: list[str] = Field(min_length=1)


class AnswerFeedback(BaseModel):
    strengths: list[str]
    areas_for_improvement: list[str]
    overall_assessment: str


class ProgressInfo(BaseModel):
    percentage: int
    completed_plans: int
    total_plans: int
