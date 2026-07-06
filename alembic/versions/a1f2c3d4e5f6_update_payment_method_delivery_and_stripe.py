"""update payment method to delivery and stripe

Revision ID: a1f2c3d4e5f6
Revises: 5e1f5af4b9c7
Create Date: 2026-07-06 10:00:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "a1f2c3d4e5f6"
down_revision: Union[str, None] = "5e1f5af4b9c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE orders MODIFY payment_method ENUM('cod', 'bank_transfer', 'delivery', 'stripe') NOT NULL"
    )
    op.execute(
        """
        UPDATE orders
        SET payment_method = 'delivery'
        WHERE payment_method IN ('cod', 'bank_transfer')
        """
    )

    op.execute("ALTER TABLE orders MODIFY payment_method ENUM('delivery', 'stripe') NOT NULL")


def downgrade() -> None:
    op.execute(
        "ALTER TABLE orders MODIFY payment_method ENUM('cod', 'bank_transfer', 'stripe') NOT NULL"
    )
