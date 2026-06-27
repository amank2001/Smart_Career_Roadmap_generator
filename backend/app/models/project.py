"""ProjectSuggestion ORM model."""

import uuid

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ProjectSuggestion(Base):
    """A suggested hands-on project for a weekly milestone."""

    __tablename__ = "project_suggestions"

    __table_args__ = (
        sa.CheckConstraint(
            "estimated_weeks >= 1 AND estimated_weeks <= 4",
            name="ck_project_suggestions_estimated_weeks",
        ),
    )

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
    title: Mapped[str] = mapped_column(
        sa.String(255),
        nullable=False,
    )
    objectives: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
    )
    deliverables: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
    )
    technologies: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
    )
    estimated_weeks: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
    )
    complexity: Mapped[str] = mapped_column(
        sa.String(20),
        nullable=False,
    )
    completed: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        default=False,
        server_default=sa.text("false"),
    )
    outcome_description: Mapped[str | None] = mapped_column(
        sa.String(500),
        nullable=True,
    )
    dismissed: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        default=False,
        server_default=sa.text("false"),
    )

    # Relationships
    weekly_plan: Mapped["WeeklyPlan"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "WeeklyPlan", back_populates="project_suggestions"
    )
