"""entry batch picks (A4 manual batch selection)

餐次手选批次: 某餐某食材用哪几批(按 position 顺序取够)。
手选是硬预留, 持久化; 自动分配仍是读时模拟 FEFO(I6 不落库)。

Revision ID: a4b7c2d9e813
Revises: f1a2b3c4d5e6
Create Date: 2026-09-24 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a4b7c2d9e813'
down_revision: str | None = 'f1a2b3c4d5e6'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "entry_batch_picks",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("entry_id", sa.BigInteger(), nullable=False),
        sa.Column("ingredient_id", sa.BigInteger(), nullable=False),
        sa.Column("inventory_item_id", sa.BigInteger(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["entry_id"], ["meal_plan_entries.id"],
            name=op.f("fk_entry_batch_picks_entry_id_meal_plan_entries"), ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["ingredient_id"], ["ingredients.id"],
            name=op.f("fk_entry_batch_picks_ingredient_id_ingredients"), ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["inventory_item_id"], ["inventory_items.id"],
            name=op.f("fk_entry_batch_picks_inventory_item_id_inventory_items"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_entry_batch_picks")),
        sa.UniqueConstraint(
            "entry_id", "inventory_item_id", name=op.f("uq_entry_batch_picks_entry_id")
        ),
    )
    op.create_index("idx_entry_batch_picks_entry", "entry_batch_picks", ["entry_id"])
    op.create_index("idx_entry_batch_picks_item", "entry_batch_picks", ["inventory_item_id"])


def downgrade() -> None:
    op.drop_index("idx_entry_batch_picks_item", table_name="entry_batch_picks")
    op.drop_index("idx_entry_batch_picks_entry", table_name="entry_batch_picks")
    op.drop_table("entry_batch_picks")
