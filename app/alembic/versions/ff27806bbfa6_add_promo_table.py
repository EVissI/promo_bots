"""add_promo_table

Revision ID: ff27806bbfa6
Revises: 91cd43af728c
Create Date: 2025-03-01 10:03:51.994973

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ff27806bbfa6'
down_revision: Union[str, None] = '91cd43af728c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('promocodes',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('promo_name', sa.String(), nullable=False),
    sa.Column('duration', sa.Integer(), nullable=False),
    sa.Column('usage_limit', sa.Integer(), nullable=False),
    sa.Column('used_count', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('promo_name')
    )
    op.alter_column('users', 'promo_code',
               existing_type=sa.BOOLEAN(),
               type_=sa.String(),
               existing_nullable=True)


def downgrade() -> None:
    op.alter_column('users', 'promo_code',
               existing_type=sa.String(),
               type_=sa.BOOLEAN(),
               existing_nullable=True)
    op.drop_table('promocodes')
