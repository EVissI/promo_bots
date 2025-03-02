"""add_role_to_user

Revision ID: 6e7420f06b11
Revises: 13ed45017dd9
Create Date: 2025-03-01 00:12:20.816029

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6e7420f06b11'
down_revision: Union[str, None] = '13ed45017dd9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE TYPE role AS ENUM ('admin', 'user')")
    op.add_column('users', sa.Column('role', sa.Enum('admin', 'user', name='role'),server_default =  'user', nullable=False))


def downgrade() -> None:
    op.drop_column('users', 'role')
    op.execute("DROP TYPE role")
