"""add_forward_message

Revision ID: a9ae85ea3ba9
Revises: d46c966d1123
Create Date: 2025-02-28 14:45:05.692171

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a9ae85ea3ba9'
down_revision: Union[str, None] = 'd46c966d1123'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('forwarded_messages',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('entity_id', sa.BigInteger(), nullable=False),
    sa.Column('message_id', sa.BigInteger(), nullable=False),
    sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('forwarded_messages')
