"""create voice calls table

Revision ID: 51db386fd417
Revises:
Create Date: 2026-08-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "51db386fd417"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create voice_calls table."""

    op.create_table(
        "voice_calls",

        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
            nullable=False
        ),

        sa.Column(
            "call_id",
            sa.String(length=50),
            nullable=False,
            unique=True
        ),

        sa.Column(
            "customer_id",
            sa.Integer(),
            sa.ForeignKey(
                "users.id",
                ondelete="CASCADE"
            ),
            nullable=False
        ),

        sa.Column(
            "creator_id",
            sa.Integer(),
            sa.ForeignKey(
                "users.id",
                ondelete="CASCADE"
            ),
            nullable=False
        ),

        sa.Column(
            "start_time",
            sa.DateTime(timezone=True),
            nullable=True
        ),

        sa.Column(
            "end_time",
            sa.DateTime(timezone=True),
            nullable=True
        ),

        sa.Column(
            "duration",
            sa.Integer(),
            nullable=True,
            server_default="0"
        ),

        sa.Column(
            "coins",
            sa.Integer(),
            nullable=True,
            server_default="0"
        ),

        sa.Column(
            "revenue",
            sa.DECIMAL(10, 2),
            nullable=True,
            server_default="0.00"
        ),

        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="ongoing"
        ),

        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True
        ),

        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True
        ),
    )

    # Indexes
    op.create_index(
        "ix_voice_calls_id",
        "voice_calls",
        ["id"],
        unique=False
    )

    op.create_index(
        "ix_voice_calls_call_id",
        "voice_calls",
        ["call_id"],
        unique=True
    )


def downgrade() -> None:
    """Remove voice_calls table."""

    op.drop_index(
        "ix_voice_calls_call_id",
        table_name="voice_calls"
    )

    op.drop_index(
        "ix_voice_calls_id",
        table_name="voice_calls"
    )

    op.drop_table("voice_calls")