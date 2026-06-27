"""LearningRoadmap, RoadmapTopic, and LearningResource ORM models."""

import uuid

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class LearningRoadmap(Base):
    """A personalised learning roadmap generated for a user."""

    __tablename__ = "learning_roadmaps"

    __table_args__ = (
        sa.CheckConstraint(
            "weekly_study_hours >= 1 AND weekly_study_hours <= 40",
            name="ck_learning_roadmaps_weekly_study_hours",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    total_weeks: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
    )
    weekly_study_hours: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
    )
    is_complete: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        default=False,
        server_default=sa.text("false"),
    )
    created_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        nullable=False,
    )
    updated_at: Mapped[sa.DateTime | None] = mapped_column(
        sa.DateTime(timezone=True),
        onupdate=sa.func.now(),
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "User", back_populates="learning_roadmaps"
    )
    topics: Mapped[list["RoadmapTopic"]] = relationship(
        "RoadmapTopic", back_populates="roadmap", cascade="all, delete-orphan"
    )
    weekly_plans: Mapped[list["WeeklyPlan"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "WeeklyPlan", back_populates="roadmap", cascade="all, delete-orphan"
    )


class RoadmapTopic(Base):
    """A skill topic that forms part of a learning roadmap."""

    __tablename__ = "roadmap_topics"

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
    skill_name: Mapped[str] = mapped_column(
        sa.String(100),
        nullable=False,
    )
    category: Mapped[str] = mapped_column(
        sa.String(20),
        nullable=False,
    )
    proficiency_target: Mapped[str] = mapped_column(
        sa.String(20),
        nullable=False,
    )
    prerequisites: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=sa.text("'[]'::jsonb"),
    )
    estimated_hours: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
    )
    order_index: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
    )

    # Relationships
    roadmap: Mapped["LearningRoadmap"] = relationship(
        "LearningRoadmap", back_populates="topics"
    )
    resources: Mapped[list["LearningResource"]] = relationship(
        "LearningResource", back_populates="topic", cascade="all, delete-orphan"
    )


class LearningResource(Base):
    """A learning resource (course, book, etc.) tied to a roadmap topic."""

    __tablename__ = "learning_resources"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    topic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("roadmap_topics.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        sa.String(255),
        nullable=False,
    )
    type: Mapped[str] = mapped_column(
        sa.String(20),
        nullable=False,
    )
    url: Mapped[str | None] = mapped_column(
        sa.String(500),
        nullable=True,
    )

    # Relationships
    topic: Mapped["RoadmapTopic"] = relationship(
        "RoadmapTopic", back_populates="resources"
    )
