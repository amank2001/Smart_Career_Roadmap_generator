"""TargetRole and SkillRequirement ORM models."""

import uuid

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TargetRole(Base):
    """A desired job role that the user is working towards."""

    __tablename__ = "target_roles"

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
    role_title: Mapped[str] = mapped_column(
        sa.String(100),
        nullable=False,
    )
    is_recognized: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        default=True,
        server_default=sa.text("true"),
    )
    responsibilities: Mapped[str | None] = mapped_column(
        sa.Text,
        nullable=True,
    )
    created_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "User", back_populates="target_roles"
    )
    skill_requirements: Mapped[list["SkillRequirement"]] = relationship(
        "SkillRequirement", back_populates="target_role", cascade="all, delete-orphan"
    )


class SkillRequirement(Base):
    """A skill required for a particular target role."""

    __tablename__ = "skill_requirements"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    target_role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("target_roles.id", ondelete="CASCADE"),
        nullable=False,
    )
    skill_name: Mapped[str] = mapped_column(
        sa.String(100),
        nullable=False,
    )
    required_proficiency: Mapped[str] = mapped_column(
        sa.String(20),
        nullable=False,
    )
    category: Mapped[str] = mapped_column(
        sa.String(20),
        nullable=False,
    )

    # Relationships
    target_role: Mapped["TargetRole"] = relationship(
        "TargetRole", back_populates="skill_requirements"
    )
