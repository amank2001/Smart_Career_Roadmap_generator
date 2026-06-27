"""SkillGapAnalysis and SkillGap ORM models."""

import uuid

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class SkillGapAnalysis(Base):
    """Result of a skill gap analysis for a user against their target role."""

    __tablename__ = "skill_gap_analyses"

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
    all_requirements_met: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        default=False,
        server_default=sa.text("false"),
    )
    advanced_specializations: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    analyzed_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "User", back_populates="skill_gap_analyses"
    )
    skill_gaps: Mapped[list["SkillGap"]] = relationship(
        "SkillGap", back_populates="analysis", cascade="all, delete-orphan"
    )


class SkillGap(Base):
    """An individual skill gap identified in an analysis."""

    __tablename__ = "skill_gaps"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("skill_gap_analyses.id", ondelete="CASCADE"),
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
    current_proficiency: Mapped[str | None] = mapped_column(
        sa.String(20),
        nullable=True,
    )
    required_proficiency: Mapped[str] = mapped_column(
        sa.String(20),
        nullable=False,
    )

    # Relationships
    analysis: Mapped["SkillGapAnalysis"] = relationship(
        "SkillGapAnalysis", back_populates="skill_gaps"
    )
