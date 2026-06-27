"""User ORM model."""

import uuid

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    """Registered application user."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    email: Mapped[str] = mapped_column(
        sa.String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    password_hash: Mapped[str] = mapped_column(
        sa.String(255),
        nullable=False,
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
    profile: Mapped["Profile"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Profile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    target_roles: Mapped[list["TargetRole"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "TargetRole", back_populates="user", cascade="all, delete-orphan"
    )
    skill_gap_analyses: Mapped[list["SkillGapAnalysis"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "SkillGapAnalysis", back_populates="user", cascade="all, delete-orphan"
    )
    learning_roadmaps: Mapped[list["LearningRoadmap"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "LearningRoadmap", back_populates="user", cascade="all, delete-orphan"
    )
    interview_sessions: Mapped[list["InterviewSession"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "InterviewSession", back_populates="user", cascade="all, delete-orphan"
    )
