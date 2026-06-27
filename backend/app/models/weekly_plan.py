"""WeeklyPlan and WeeklyTask ORM models."""

import uuid

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class WeeklyPlan(Base):
    """A single week's study plan within a learning roadmap."""

    __tablename__ = "weekly_plans"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    roadmap_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("learning_roadmaps.id", ondelete="CASCADE"),
        nullable=False,
    )
    week_number: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        sa.String(20),
        nullable=False,
        default="upcoming",
        server_default=sa.text("'upcoming'"),
    )
    is_practical_milestone: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        default=False,
        server_default=sa.text("false"),
    )
    start_date: Mapped[sa.DateTime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
    )
    end_date: Mapped[sa.DateTime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    roadmap: Mapped["LearningRoadmap"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "LearningRoadmap", back_populates="weekly_plans"
    )
    tasks: Mapped[list["WeeklyTask"]] = relationship(
        "WeeklyTask", back_populates="weekly_plan", cascade="all, delete-orphan"
    )
    project_suggestions: Mapped[list["ProjectSuggestion"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "ProjectSuggestion", back_populates="weekly_plan", cascade="all, delete-orphan"
    )


class WeeklyTask(Base):
    """An individual task within a weekly study plan."""

    __tablename__ = "weekly_tasks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    weekly_plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("weekly_plans.id", ondelete="CASCADE"),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(
        sa.Text,
        nullable=False,
    )
    estimated_hours: Mapped[float] = mapped_column(
        sa.Float,
        nullable=False,
    )
    skill_name: Mapped[str] = mapped_column(
        sa.String(100),
        nullable=False,
    )
    completion_criterion: Mapped[str] = mapped_column(
        sa.Text,
        nullable=False,
    )
    completed: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        default=False,
        server_default=sa.text("false"),
    )
    completed_at: Mapped[sa.DateTime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    weekly_plan: Mapped["WeeklyPlan"] = relationship(
        "WeeklyPlan", back_populates="tasks"
    )
