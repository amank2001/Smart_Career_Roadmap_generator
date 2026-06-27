"""Profile and Skill ORM models."""

import uuid

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Profile(Base):
    """Extended profile information for a user."""

    __tablename__ = "profiles"

    __table_args__ = (
        sa.CheckConstraint(
            "years_of_experience >= 0 AND years_of_experience <= 50",
            name="ck_profiles_years_of_experience",
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
        unique=True,
        nullable=False,
    )
    current_job_title: Mapped[str | None] = mapped_column(
        sa.String(100),
        nullable=True,
    )
    years_of_experience: Mapped[int | None] = mapped_column(
        sa.Integer,
        nullable=True,
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
        "User", back_populates="profile"
    )
    skills: Mapped[list["Skill"]] = relationship(
        "Skill", back_populates="profile", cascade="all, delete-orphan"
    )


class Skill(Base):
    """A skill associated with a user profile."""

    __tablename__ = "skills"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(
        sa.String(60),
        nullable=False,
    )
    proficiency_level: Mapped[str | None] = mapped_column(
        sa.String(20),
        nullable=True,
    )

    # Relationships
    profile: Mapped["Profile"] = relationship("Profile", back_populates="skills")
