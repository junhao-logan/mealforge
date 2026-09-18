"""add nutrition basis to ingredients (A2 unit-native)

给 ingredients 加营养基准两列, 支持"单位本位"用户食材:
营养 = 每 nutrition_basis_amount 个 nutrition_basis_unit。
现有食材回填 (100, 'g') —— 与旧 per-100g 语义一致, 无行为变化(server_default 自动覆盖存量行)。

Revision ID: f1a2b3c4d5e6
Revises: d5a8c3f10e29
Create Date: 2026-09-18 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: str | None = 'd5a8c3f10e29'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # server_default 让存量行自动回填 (100, 'g'); NOT NULL 安全
    op.add_column(
        "ingredients",
        sa.Column(
            "nutrition_basis_amount",
            sa.Numeric(precision=8, scale=2),
            nullable=False,
            server_default=sa.text("100"),
        ),
    )
    op.add_column(
        "ingredients",
        sa.Column(
            "nutrition_basis_unit",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'g'"),
        ),
    )


def downgrade() -> None:
    op.drop_column("ingredients", "nutrition_basis_unit")
    op.drop_column("ingredients", "nutrition_basis_amount")
