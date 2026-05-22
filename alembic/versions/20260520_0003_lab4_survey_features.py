"""lab4 survey features

Revision ID: 20260520_0003
Revises: 20260423_0002
Create Date: 2026-05-20 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260520_0003"
down_revision = "20260423_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("surveys") as batch_op:
        batch_op.add_column(sa.Column("image_url", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("surveys") as batch_op:
        batch_op.drop_column("image_url")
