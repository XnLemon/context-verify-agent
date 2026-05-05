"""add agent_outputs table

Revision ID: 734af0ffafbe
Revises: 0004_member_profile_settings
Create Date: 2026-05-06 03:33:43.259864

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '734af0ffafbe'
down_revision: Union[str, Sequence[str], None] = '0004_member_profile_settings'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "agent_outputs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("pipeline_id", sa.String(64), nullable=False, index=True),
        sa.Column("contract_id", sa.String(128), nullable=False, index=True),
        sa.Column("agent_id", sa.String(64), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="completed"),
        sa.Column("output_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("agent_outputs")
