"""InterviewSession, InterviewQuestion, and AnswerSubmission ORM models."""

import uuid

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class InterviewSession(Base):
    """A mock interview session for a user."""

    __tablename__ = "interview_sessions"

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
    created_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "User", back_populates="interview_sessions"
    )
    questions: Mapped[list["InterviewQuestion"]] = relationship(
        "InterviewQuestion", back_populates="session", cascade="all, delete-orphan"
    )


class InterviewQuestion(Base):
    """A question within an interview session."""

    __tablename__ = "interview_questions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    question: Mapped[str] = mapped_column(
        sa.Text,
        nullable=False,
    )
    category: Mapped[str] = mapped_column(
        sa.String(20),
        nullable=False,
    )
    difficulty: Mapped[str] = mapped_column(
        sa.String(20),
        nullable=False,
    )
    model_answer: Mapped[str] = mapped_column(
        sa.Text,
        nullable=False,
    )
    evaluation_criteria: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
    )

    # Relationships
    session: Mapped["InterviewSession"] = relationship(
        "InterviewSession", back_populates="questions"
    )
    answer_submission: Mapped["AnswerSubmission | None"] = relationship(
        "AnswerSubmission", back_populates="question", uselist=False, cascade="all, delete-orphan"
    )


class AnswerSubmission(Base):
    """A user's answer to an interview question, with AI feedback."""

    __tablename__ = "answer_submissions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("interview_questions.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    user_answer: Mapped[str] = mapped_column(
        sa.Text,
        nullable=False,
    )
    strengths: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
    )
    areas_for_improvement: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
    )
    overall_assessment: Mapped[str] = mapped_column(
        sa.Text,
        nullable=False,
    )
    submitted_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
    )

    # Relationships
    question: Mapped["InterviewQuestion"] = relationship(
        "InterviewQuestion", back_populates="answer_submission"
    )
