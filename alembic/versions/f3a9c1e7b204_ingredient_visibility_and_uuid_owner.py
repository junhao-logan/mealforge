"""ingredient visibility and uuid owner (I11)

Revision ID: f3a9c1e7b204
Revises: 1338b40ff5cc
Create Date: 2026-07-28 00:00:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'f3a9c1e7b204'
down_revision: str | None = '1338b40ff5cc'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # created_by_user_id: BigInteger -> UUID + FK->users(清 Week2 类型债 #5)
    # 全列已验证为 NULL(15 行 USDA seed, 均无归属), 故 USING NULL::uuid 安全无损。
    # BigInteger 值与 UUID 本就不可互转; 此列此前从未写入。
    op.alter_column(
        'ingredients', 'created_by_user_id',
        existing_type=sa.BigInteger(),
        type_=sa.UUID(),
        existing_nullable=True,
        postgresql_using='NULL::uuid',
    )
    # 用户删除时不销毁其创建的食材, 仅置空归属 -> SET NULL
    op.create_foreign_key(
        op.f('fk_ingredients_created_by_user_id_users'),
        'ingredients', 'users',
        ['created_by_user_id'], ['id'],
        ondelete='SET NULL',
    )
    op.create_index(
        'idx_ingredients_created_by', 'ingredients',
        ['created_by_user_id'], unique=False,
    )

    # visibility: 'private'(默认) / 'global'。与 source 正交(source=哪来的, visibility=谁能看)
    op.add_column(
        'ingredients',
        sa.Column(
            'visibility', sa.String(length=20),
            server_default=sa.text("'private'"), nullable=False,
        ),
    )
    # 回填: 现有 15 条均为 USDA 共享参考数据 -> global
    # (否则新列默认 private, 用户将看不见已有食材)
    op.execute("UPDATE ingredients SET visibility = 'global'")


def downgrade() -> None:
    op.drop_column('ingredients', 'visibility')
    op.drop_index('idx_ingredients_created_by', table_name='ingredients')
    op.drop_constraint(
        op.f('fk_ingredients_created_by_user_id_users'),
        'ingredients', type_='foreignkey',
    )
    op.alter_column(
        'ingredients', 'created_by_user_id',
        existing_type=sa.UUID(),
        type_=sa.BigInteger(),
        existing_nullable=True,
        postgresql_using='NULL::bigint',
    )