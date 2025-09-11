"""create_otp_table

Revision ID: fe6c58c25011
Revises: 0e304c083049
Create Date: 2025-09-10 11:37:31.040123
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = 'fe6c58c25011'
down_revision: Union[str, None] = '0e304c083049'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop table otps if exists (compatible)
    conn = op.get_bind()
    inspector = inspect(conn)
    if 'otps' in inspector.get_table_names():
        op.drop_table('otps')

    # Create table otps
    op.create_table(
        'otps',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('code', sa.String(length=6), nullable=False),
        sa.Column('is_used', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )

    # Modify carts.user_id safely
    conn = op.get_bind()
    inspector = inspect(conn)
    fk_names = [fk['name'] for fk in inspector.get_foreign_keys('carts')]

    if 'carts_user_id_fkey' in fk_names:
        op.drop_constraint('carts_user_id_fkey', 'carts', type_='foreignkey')

    op.alter_column(
        'carts', 'user_id',
        existing_type=sa.String(length=36),
        type_=sa.String(length=225),
        existing_nullable=True
    )

    op.create_foreign_key(
        'carts_user_id_fkey',
        'carts', 'users',
        ['user_id'], ['id'],
        ondelete='CASCADE'
    )


def downgrade() -> None:
    # Downgrade carts.user_id safely
    conn = op.get_bind()
    inspector = inspect(conn)
    fk_names = [fk['name'] for fk in inspector.get_foreign_keys('carts')]

    if 'carts_user_id_fkey' in fk_names:
        op.drop_constraint('carts_user_id_fkey', 'carts', type_='foreignkey')

    op.alter_column(
        'carts', 'user_id',
        existing_type=sa.String(length=225),
        type_=sa.String(length=36),
        existing_nullable=True
    )

    op.create_foreign_key(
        'carts_user_id_fkey',
        'carts', 'users',
        ['user_id'], ['id'],
        ondelete='CASCADE'
    )

    # Drop otps table safely
    conn = op.get_bind()
    inspector = inspect(conn)
    if 'otps' in inspector.get_table_names():
        op.drop_table('otps')
