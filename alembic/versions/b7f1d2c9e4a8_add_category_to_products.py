"""add category to products

Revision ID: b7f1d2c9e4a8
Revises: a8c3d5c1f6e2
Create Date: 2026-07-04 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b7f1d2c9e4a8"
down_revision: Union[str, None] = "a8c3d5c1f6e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("products", sa.Column("category", sa.String(length=120), nullable=True))
    op.create_index(op.f("ix_products_category"), "products", ["category"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_products_category"), table_name="products")
    op.drop_column("products", "category")
