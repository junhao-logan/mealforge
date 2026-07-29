"""recipe visibility and uuid owner, drop is_public (I11)

Revision ID: b8e4d1a6f927
Revises: f3a9c1e7b204
Create Date: 2026-07-28 00:00:01.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'b8e4d1a6f927'
down_revision: str | None = 'f3a9c1e7b204'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # created_by_user_id: BigInteger -> UUID + FK->users(清类型债 #5, 同 ingredients)
    # 此列此前从未写入(留列不加FK), USING NULL::uuid 安全无损
    op.alter_column(
        'recipes', 'created_by_user_id',
        existing_type=sa.BigInteger(),
        type_=sa.UUID(),
        existing_nullable=True,
        postgresql_using='NULL::uuid',
    )
    op.create_foreign_key(
        op.f('fk_recipes_created_by_user_id_users'),
        'recipes', 'users',
        ['created_by_user_id'], ['id'],
        ondelete='SET NULL',
    )

    # visibility: 'private'(默认) / 'global'
    op.add_column(
        'recipes',
        sa.Column(
            'visibility', sa.String(length=20),
            server_default=sa.text("'private'"), nullable=False,
        ),
    )
    # 回填: 现有菜谱一律 global。此前 is_public 从未用于过滤(所有菜谱对所有人可见),
    # 故全设 global 恰好保持现有行为不变; 新建用户菜谱才是 private。
    op.execute("UPDATE recipes SET visibility = 'global'")

    # 决策 A: is_public 收敛进 visibility, 删掉旧字段(单一概念)
    op.drop_column('recipes', 'is_public')


def downgrade() -> None:
    op.add_column(
        'recipes',
        sa.Column(
            'is_public', sa.Boolean(),
            server_default=sa.text('false'), nullable=False,
        ),
    )
    # visibility=global 反推 is_public=true
    op.execute("UPDATE recipes SET is_public = (visibility = 'global')")
    op.drop_column('recipes', 'visibility')
    op.drop_constraint(
        op.f('fk_recipes_created_by_user_id_users'),
        'recipes', type_='foreignkey',
    )
    op.alter_column(
        'recipes', 'created_by_user_id',
        existing_type=sa.UUID(),
        type_=sa.BigInteger(),
        existing_nullable=True,
        postgresql_using='NULL::bigint',
    )