"""add non-negative check to inventory quantity

Revision ID: 7ce8329404eb
Revises: 0b3cad604b77
Create Date: 2026-07-23 16:50:27.241842

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7ce8329404eb'
down_revision: str | None = '0b3cad604b77'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_check_constraint(
        "qty_non_negative",              # 约束名（naming_convention 会加 ck_inventory_items_ 前缀）
        "inventory_items",
        "quantity_grams >= 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_inventory_items_qty_non_negative",   # drop 要用完整名
        "inventory_items",
        type_="check",
    )