"""Initial schema — all 16 tables.

Revision ID: 0001_initial_schema
Revises: None
Create Date: 2025-01-01 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# ── Revision identifiers ──────────────────────────────────────────────────────
revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


# ── Helpers ───────────────────────────────────────────────────────────────────
UUID = postgresql.UUID


def upgrade() -> None:
    # 1. users
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # 2. profiles
    op.create_table(
        "profiles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("current_job_title", sa.String(100), nullable=True),
        sa.Column("years_of_experience", sa.Integer, nullable=True),
        sa.Column(
            "is_complete",
            sa.Boolean,
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_profiles_user_id", ondelete="CASCADE"
        ),
        sa.UniqueConstraint("user_id", name="uq_profiles_user_id"),
        sa.CheckConstraint(
            "years_of_experience >= 0 AND years_of_experience <= 50",
            name="ck_profiles_years_of_experience",
        ),
    )

    # 3. skills
    op.create_table(
        "skills",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("profile_id", UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(60), nullable=False),
        sa.Column("proficiency_level", sa.String(20), nullable=True),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["profiles.id"],
            name="fk_skills_profile_id",
            ondelete="CASCADE",
        ),
    )

    # 4. target_roles
    op.create_table(
        "target_roles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("role_title", sa.String(100), nullable=False),
        sa.Column(
            "is_recognized",
            sa.Boolean,
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column("responsibilities", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_target_roles_user_id",
            ondelete="CASCADE",
        ),
    )

    # 5. skill_requirements
    op.create_table(
        "skill_requirements",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("target_role_id", UUID(as_uuid=True), nullable=False),
        sa.Column("skill_name", sa.String(100), nullable=False),
        sa.Column("required_proficiency", sa.String(20), nullable=False),
        sa.Column("category", sa.String(20), nullable=False),
        sa.ForeignKeyConstraint(
            ["target_role_id"],
            ["target_roles.id"],
            name="fk_skill_requirements_target_role_id",
            ondelete="CASCADE",
        ),
    )

    # 6. skill_gap_analyses
    op.create_table(
        "skill_gap_analyses",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "all_requirements_met",
            sa.Boolean,
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("advanced_specializations", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "analyzed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_skill_gap_analyses_user_id",
            ondelete="CASCADE",
        ),
    )

    # 7. skill_gaps
    op.create_table(
        "skill_gaps",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("analysis_id", UUID(as_uuid=True), nullable=False),
        sa.Column("skill_name", sa.String(100), nullable=False),
        sa.Column("category", sa.String(20), nullable=False),
        sa.Column("current_proficiency", sa.String(20), nullable=True),
        sa.Column("required_proficiency", sa.String(20), nullable=False),
        sa.ForeignKeyConstraint(
            ["analysis_id"],
            ["skill_gap_analyses.id"],
            name="fk_skill_gaps_analysis_id",
            ondelete="CASCADE",
        ),
    )

    # 8. learning_roadmaps
    op.create_table(
        "learning_roadmaps",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("total_weeks", sa.Integer, nullable=False),
        sa.Column("weekly_study_hours", sa.Integer, nullable=False),
        sa.Column(
            "is_complete",
            sa.Boolean,
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_learning_roadmaps_user_id",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "weekly_study_hours >= 1 AND weekly_study_hours <= 40",
            name="ck_learning_roadmaps_weekly_study_hours",
        ),
    )

    # 9. roadmap_topics
    op.create_table(
        "roadmap_topics",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("roadmap_id", UUID(as_uuid=True), nullable=False),
        sa.Column("skill_name", sa.String(100), nullable=False),
        sa.Column("category", sa.String(20), nullable=False),
        sa.Column("proficiency_target", sa.String(20), nullable=False),
        sa.Column(
            "prerequisites",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("estimated_hours", sa.Integer, nullable=False),
        sa.Column("order_index", sa.Integer, nullable=False),
        sa.ForeignKeyConstraint(
            ["roadmap_id"],
            ["learning_roadmaps.id"],
            name="fk_roadmap_topics_roadmap_id",
            ondelete="CASCADE",
        ),
    )

    # 10. learning_resources
    op.create_table(
        "learning_resources",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("topic_id", UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("url", sa.String(500), nullable=True),
        sa.ForeignKeyConstraint(
            ["topic_id"],
            ["roadmap_topics.id"],
            name="fk_learning_resources_topic_id",
            ondelete="CASCADE",
        ),
    )

    # 11. weekly_plans
    op.create_table(
        "weekly_plans",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("roadmap_id", UUID(as_uuid=True), nullable=False),
        sa.Column("week_number", sa.Integer, nullable=False),
        sa.Column(
            "status",
            sa.String(20),
            server_default=sa.text("'upcoming'"),
            nullable=False,
        ),
        sa.Column(
            "is_practical_milestone",
            sa.Boolean,
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["roadmap_id"],
            ["learning_roadmaps.id"],
            name="fk_weekly_plans_roadmap_id",
            ondelete="CASCADE",
        ),
    )

    # 12. weekly_tasks
    op.create_table(
        "weekly_tasks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("weekly_plan_id", UUID(as_uuid=True), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("estimated_hours", sa.Float, nullable=False),
        sa.Column("skill_name", sa.String(100), nullable=False),
        sa.Column("completion_criterion", sa.Text, nullable=False),
        sa.Column(
            "completed",
            sa.Boolean,
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["weekly_plan_id"],
            ["weekly_plans.id"],
            name="fk_weekly_tasks_weekly_plan_id",
            ondelete="CASCADE",
        ),
    )

    # 13. project_suggestions
    op.create_table(
        "project_suggestions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("weekly_plan_id", UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("objectives", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("deliverables", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("technologies", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("estimated_weeks", sa.Integer, nullable=False),
        sa.Column("complexity", sa.String(20), nullable=False),
        sa.Column(
            "completed",
            sa.Boolean,
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("outcome_description", sa.String(500), nullable=True),
        sa.Column(
            "dismissed",
            sa.Boolean,
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["weekly_plan_id"],
            ["weekly_plans.id"],
            name="fk_project_suggestions_weekly_plan_id",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "estimated_weeks >= 1 AND estimated_weeks <= 4",
            name="ck_project_suggestions_estimated_weeks",
        ),
    )

    # 14. interview_sessions
    op.create_table(
        "interview_sessions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_interview_sessions_user_id",
            ondelete="CASCADE",
        ),
    )

    # 15. interview_questions
    op.create_table(
        "interview_questions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("session_id", UUID(as_uuid=True), nullable=False),
        sa.Column("question", sa.Text, nullable=False),
        sa.Column("category", sa.String(20), nullable=False),
        sa.Column("difficulty", sa.String(20), nullable=False),
        sa.Column("model_answer", sa.Text, nullable=False),
        sa.Column("evaluation_criteria", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["interview_sessions.id"],
            name="fk_interview_questions_session_id",
            ondelete="CASCADE",
        ),
    )

    # 16. answer_submissions
    op.create_table(
        "answer_submissions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("question_id", UUID(as_uuid=True), nullable=False),
        sa.Column("user_answer", sa.Text, nullable=False),
        sa.Column("strengths", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("areas_for_improvement", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("overall_assessment", sa.Text, nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["question_id"],
            ["interview_questions.id"],
            name="fk_answer_submissions_question_id",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("question_id", name="uq_answer_submissions_question_id"),
    )


def downgrade() -> None:
    # Drop in reverse FK order
    op.drop_table("answer_submissions")
    op.drop_table("interview_questions")
    op.drop_table("interview_sessions")
    op.drop_table("project_suggestions")
    op.drop_table("weekly_tasks")
    op.drop_table("weekly_plans")
    op.drop_table("learning_resources")
    op.drop_table("roadmap_topics")
    op.drop_table("learning_roadmaps")
    op.drop_table("skill_gaps")
    op.drop_table("skill_gap_analyses")
    op.drop_table("skill_requirements")
    op.drop_table("target_roles")
    op.drop_table("skills")
    op.drop_table("profiles")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
