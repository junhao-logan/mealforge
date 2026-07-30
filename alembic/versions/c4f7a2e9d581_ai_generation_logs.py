"""ai generation logs + recipes fk (Week 7)

Revision ID: c4f7a2e9d581
Revises: b8e4d1a6f927
Create Date: 2026-07-28 00:00:02.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'c4f7a2e9d581'
down_revision: str | None = 'b8e4d1a6f927'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 先建 ai_generation_logs(其 created_recipe_id FK 指向已存在的 recipes)
    op.create_table(
        'ai_generation_logs',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('kind', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('model', sa.String(length=50), nullable=False),
        sa.Column('prompt', sa.Text(), nullable=False),
        sa.Column('raw_response', sa.Text(), nullable=True),
        sa.Column('input_tokens', sa.Integer(), nullable=True),
        sa.Column('output_tokens', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_recipe_id', sa.BigInteger(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(
            ['user_id'], ['users.id'],
            name=op.f('fk_ai_generation_logs_user_id_users'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(
            ['created_recipe_id'], ['recipes.id'],
            name=op.f('fk_ai_generation_logs_created_recipe_id_recipes'),
            ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_ai_generation_logs')),
    )
    op.create_index('idx_ai_logs_user_created', 'ai_generation_logs',
                    ['user_id', 'created_at'], unique=False)

    # 再给 recipes.ai_generation_log_id 补 FK(现在 ai_generation_logs 已存在)
    op.create_foreign_key(
        op.f('fk_recipes_ai_generation_log_id_ai_generation_logs'),
        'recipes', 'ai_generation_logs',
        ['ai_generation_log_id'], ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f('fk_recipes_ai_generation_log_id_ai_generation_logs'),
        'recipes', type_='foreignkey',
    )
    op.drop_index('idx_ai_logs_user_created', table_name='ai_generation_logs')
    op.drop_table('ai_generation_logs')