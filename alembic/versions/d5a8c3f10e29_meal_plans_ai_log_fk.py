"""meal_plans ai_generation_log_id fk (Week 8)

Revision ID: d5a8c3f10e29
Revises: c4f7a2e9d581
Create Date: 2026-08-07 00:00:00.000000

"""
from collections.abc import Sequence

from alembic import op


revision: str = 'd5a8c3f10e29'
down_revision: str | None = 'c4f7a2e9d581'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 补 FK: 由哪次 AI 生成建立此计划(ai_generation_logs 已存在, 同 recipes 的处理)
    op.create_foreign_key(
        op.f('fk_meal_plans_ai_generation_log_id_ai_generation_logs'),
        'meal_plans', 'ai_generation_logs',
        ['ai_generation_log_id'], ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f('fk_meal_plans_ai_generation_log_id_ai_generation_logs'),
        'meal_plans', type_='foreignkey',
    )