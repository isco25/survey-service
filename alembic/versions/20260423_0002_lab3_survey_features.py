"""lab3 survey features and idempotency

Revision ID: 20260423_0002
Revises: 20260327_0001
Create Date: 2026-04-23 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260423_0002"
down_revision = "20260327_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("surveys") as batch_op:
        batch_op.add_column(
            sa.Column("author_id", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.add_column(
            sa.Column("category", sa.String(length=64), nullable=False, server_default="general")
        )
        batch_op.add_column(sa.Column("questions", sa.JSON(), nullable=False, server_default="[]"))

    op.create_index("ix_surveys_author_id", "surveys", ["author_id"])
    op.create_index("ix_surveys_category", "surveys", ["category"])

    with op.batch_alter_table("answers") as batch_op:
        batch_op.add_column(
            sa.Column("respondent_id", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.add_column(
            sa.Column("business_key", sa.String(length=255), nullable=False, server_default="")
        )
        batch_op.add_column(
            sa.Column(
                "source_service",
                sa.String(length=64),
                nullable=False,
                server_default="legacy-survey-service",
            )
        )

    op.execute("UPDATE answers SET respondent_id = id WHERE respondent_id = 0")
    op.execute(
        "UPDATE answers "
        "SET business_key = 'legacy-survey:' || survey_id || ':respondent:' || respondent_id "
        "WHERE business_key = ''"
    )
    op.create_index("ix_answers_respondent_id", "answers", ["respondent_id"])
    op.create_index("ix_answers_business_key", "answers", ["business_key"], unique=True)
    op.create_index(
        "uq_answers_survey_respondent",
        "answers",
        ["survey_id", "respondent_id"],
        unique=True,
    )

    op.create_table(
        "idempotency_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_service", sa.String(length=64), nullable=False),
        sa.Column("operation", sa.String(length=64), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("business_key", sa.String(length=255), nullable=True),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="in_progress"),
        sa.Column("response_code", sa.Integer(), nullable=True),
        sa.Column("response_body", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("resource_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "source_service",
            "operation",
            "idempotency_key",
            name="uq_idempotency_source_operation_key",
        ),
    )
    op.create_index(
        "ix_idempotency_records_source_service",
        "idempotency_records",
        ["source_service"],
    )
    op.create_index(
        "ix_idempotency_records_business_key",
        "idempotency_records",
        ["business_key"],
    )


def downgrade() -> None:
    op.drop_index("ix_idempotency_records_business_key", table_name="idempotency_records")
    op.drop_index("ix_idempotency_records_source_service", table_name="idempotency_records")
    op.drop_table("idempotency_records")

    op.drop_index("uq_answers_survey_respondent", table_name="answers")
    op.drop_index("ix_answers_business_key", table_name="answers")
    op.drop_index("ix_answers_respondent_id", table_name="answers")
    with op.batch_alter_table("answers") as batch_op:
        batch_op.drop_column("source_service")
        batch_op.drop_column("business_key")
        batch_op.drop_column("respondent_id")

    op.drop_index("ix_surveys_category", table_name="surveys")
    op.drop_index("ix_surveys_author_id", table_name="surveys")
    with op.batch_alter_table("surveys") as batch_op:
        batch_op.drop_column("questions")
        batch_op.drop_column("category")
        batch_op.drop_column("author_id")
