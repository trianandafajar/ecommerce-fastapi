"""add stripe fields to orders

Revision ID: 5e1f5af4b9c7
Revises: b7f1d2c9e4a8
Create Date: 2026-07-06 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "5e1f5af4b9c7"
down_revision: Union[str, None] = "b7f1d2c9e4a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_cols = [c["name"] for c in inspector.get_columns("orders")]

    if "payment_provider" not in existing_cols:
        op.add_column("orders", sa.Column("payment_provider", sa.String(length=36), nullable=True))
    if "stripe_checkout_session_id" not in existing_cols:
        op.add_column(
            "orders",
            sa.Column("stripe_checkout_session_id", sa.String(length=255), nullable=True),
        )
    if "stripe_payment_intent_id" not in existing_cols:
        op.add_column(
            "orders",
            sa.Column("stripe_payment_intent_id", sa.String(length=255), nullable=True),
        )
    if "stripe_customer_id" not in existing_cols:
        op.add_column(
            "orders",
            sa.Column("stripe_customer_id", sa.String(length=255), nullable=True),
        )

    index_names = [idx["name"] for idx in inspector.get_indexes("orders")]
    if "ix_orders_stripe_checkout_session_id" not in index_names:
        op.create_index(
            "ix_orders_stripe_checkout_session_id",
            "orders",
            ["stripe_checkout_session_id"],
            unique=True,
        )
    if "ix_orders_stripe_payment_intent_id" not in index_names:
        op.create_index(
            "ix_orders_stripe_payment_intent_id",
            "orders",
            ["stripe_payment_intent_id"],
            unique=False,
        )
    if "ix_orders_stripe_customer_id" not in index_names:
        op.create_index(
            "ix_orders_stripe_customer_id",
            "orders",
            ["stripe_customer_id"],
            unique=False,
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    index_names = [idx["name"] for idx in inspector.get_indexes("orders")]

    for index_name in [
        "ix_orders_stripe_customer_id",
        "ix_orders_stripe_payment_intent_id",
        "ix_orders_stripe_checkout_session_id",
    ]:
        if index_name in index_names:
            op.drop_index(index_name, table_name="orders")

    existing_cols = [c["name"] for c in inspector.get_columns("orders")]
    for column_name in [
        "stripe_customer_id",
        "stripe_payment_intent_id",
        "stripe_checkout_session_id",
        "payment_provider",
    ]:
        if column_name in existing_cols:
            op.drop_column("orders", column_name)

