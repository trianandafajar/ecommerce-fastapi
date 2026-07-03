"""add user roles and order updated_at

Revision ID: a8c3d5c1f6e2
Revises: 6130ab72cc7b
Create Date: 2026-07-02 12:05:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "a8c3d5c1f6e2"
down_revision: Union[str, None] = "6130ab72cc7b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)

    user_columns = [c["name"] for c in inspector.get_columns("users")]
    if "role" not in user_columns:
        op.add_column(
            "users",
            sa.Column("role", sa.String(length=20), nullable=False, server_default=sa.text("'customer'")),
        )
    if "is_active" not in user_columns:
        op.add_column(
            "users",
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        )

    op.execute(sa.text("UPDATE users SET role = 'customer' WHERE role IS NULL OR role = ''"))
    op.execute(sa.text("UPDATE users SET is_active = 1 WHERE is_active IS NULL"))

    order_columns = [c["name"] for c in inspector.get_columns("orders")]
    if "updated_at" not in order_columns:
        op.add_column(
            "orders",
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=True,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)

    order_columns = [c["name"] for c in inspector.get_columns("orders")]
    if "updated_at" in order_columns:
        op.drop_column("orders", "updated_at")

    user_columns = [c["name"] for c in inspector.get_columns("users")]
    if "is_active" in user_columns:
        op.drop_column("users", "is_active")
    if "role" in user_columns:
        op.drop_column("users", "role")
