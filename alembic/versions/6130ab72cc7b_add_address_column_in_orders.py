"""add_address_column_in_orders

Revision ID: 6130ab72cc7b
Revises: fe6c58c25011
Create Date: 2025-09-11 10:30:47.999444
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = '6130ab72cc7b'
down_revision: Union[str, None] = 'fe6c58c25011'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop carts foreign key safely
    conn = op.get_bind()
    inspector = inspect(conn)
    fk_names = [fk['name'] for fk in inspector.get_foreign_keys('carts')]
    if 'carts_ibfk_1' in fk_names:
        op.drop_constraint('carts_ibfk_1', 'carts', type_='foreignkey')

    # Recreate carts foreign key with safer name
    op.create_foreign_key(
        'carts_user_id_fkey',  # nama constraint eksplisit
        'carts', 'users',
        ['user_id'], ['id'],
        ondelete='CASCADE'
    )

    # Add new address-related columns
    op.add_column('orders', sa.Column('first_name', sa.String(length=50), nullable=True))
    op.add_column('orders', sa.Column('last_name', sa.String(length=50), nullable=True))
    op.add_column('orders', sa.Column('address', sa.Text(), nullable=False))
    op.add_column('orders', sa.Column('city', sa.String(length=50), nullable=False))
    op.add_column('orders', sa.Column('postal_code', sa.String(length=20), nullable=False))
    op.add_column('orders', sa.Column('phone', sa.String(length=20), nullable=False))

    # Drop old shipping_address column
    if 'shipping_address' in [c['name'] for c in inspector.get_columns('orders')]:
        op.drop_column('orders', 'shipping_address')


def downgrade() -> None:
    # Re-add shipping_address column safely
    conn = op.get_bind()
    inspector = inspect(conn)
    if 'shipping_address' not in [c['name'] for c in inspector.get_columns('orders')]:
        op.add_column('orders', sa.Column('shipping_address', sa.Text(), nullable=False))

    # Drop added columns
    for col in ['phone', 'postal_code', 'city', 'address', 'last_name', 'first_name']:
        if col in [c['name'] for c in inspector.get_columns('orders')]:
            op.drop_column('orders', col)

    # Drop the foreign key safely
    fk_names = [fk['name'] for fk in inspector.get_foreign_keys('carts')]
    if 'carts_user_id_fkey' in fk_names:
        op.drop_constraint('carts_user_id_fkey', 'carts', type_='foreignkey')

    # Recreate original foreign key
    op.create_foreign_key(
        'carts_ibfk_1',
        'carts', 'users',
        ['user_id'], ['id'],
        ondelete='CASCADE'
    )
