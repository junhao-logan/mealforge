# app/shopping/models.py
from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ShoppingList(Base):
    """采购清单 —— 可由 meal_plan 缺口自动生成, 也可纯手动建立。
    生成时用 compute_shortfall 物化一次 auto 项快照(I7/I8); 之后清单稳定可交互。
    """
    __tablename__ = "shopping_lists"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    # user_id UUID 对齐真实 users.id(identity shadow); 删用户带走清单
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    name: Mapped[str | None] = mapped_column(String(100))  # NULL = 自动命名

    # 清单从哪个计划生成; 计划删了清单仍留存(历史采购记录) → SET NULL
    source_meal_plan_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("meal_plans.id", ondelete="SET NULL")
    )

    # 生成该清单时用的预测视界(I7): 缺口 = [start, end] 内需求 − 库存
    # 落库(决策1): 重算沿用同一区间, 清单语义边界稳定; 纯手动清单两列全 NULL
    forecast_start: Mapped[date | None] = mapped_column(Date)
    forecast_end: Mapped[date | None] = mapped_column(Date)

    # active / completed / archived
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        server_default=func.now(), onupdate=func.now(),
    )

    # 一个清单含多项; 删清单级联删其所有项(与 meal_plans → entries 同构)
    items: Mapped[list[ShoppingListItem]] = relationship(
        back_populates="shopping_list", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_shopping_lists_user_status", "user_id", "status"),
        # 预测视界成对存在(全 NULL 或全有值)且 end >= start
        # 对齐 meal_plans.chk_date_range 先例; NULL 比较得 NULL, CHECK 放行纯手动清单
        CheckConstraint(
            "(forecast_start IS NULL) = (forecast_end IS NULL) "
            "AND (forecast_end IS NULL OR forecast_end >= forecast_start)",
            name="forecast_range",
        ),
    )


class ShoppingListItem(Base):
    """采购项 —— auto(缺口生成)与 manual(手动加)双来源(I8), 食材/非食材双形态(I10)。"""
    __tablename__ = "shopping_list_items"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    # 依附于清单, 删清单带走 → CASCADE
    shopping_list_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("shopping_lists.id", ondelete="CASCADE"),
        nullable=False,
    )

    # 食材关联可空(I10): auto 项与"选已有食材"的 manual 项有值;
    # 纯文本 manual 项(厨房纸)为 NULL, 用 item_name 显示。引用的食材不准删 → RESTRICT
    ingredient_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("ingredients.id", ondelete="RESTRICT")
    )
    # 非食材/纯文本项的显示名; 有 ingredient_id 时可空(用食材名显示)
    item_name: Mapped[str | None] = mapped_column(String(100))

    # 来源(I8): 'auto'=缺口生成(重算覆盖) / 'manual'=手动加(重算保留)
    # 默认 manual: 用户手动添加是常态, auto 由生成逻辑显式写入
    source: Mapped[str] = mapped_column(String(10), nullable=False, default="manual")

    # 需求量(I7 缺口, 克本位): auto 项有克数; 非食材 manual 项无克数 → nullable(I10)
    needed_grams: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))

    # 买完是否入库(I10): 食材=true(→ I9 回流建批次) / 厨房纸等=false(纯提醒, 打勾即完)
    add_to_inventory: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )

    # 采购回填(I9): 勾选购买时回流入库
    is_purchased: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    purchased_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2)
    )  # 实际购买量(用户原始单位, 展示)
    purchased_unit: Mapped[str | None] = mapped_column(String(20))
    # 归一化克数(经 I3 换算): 回流时直接抄进 inventory_items.quantity_grams(免二次换算)
    purchased_grams: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    purchased_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    category_override: Mapped[str | None] = mapped_column(String(50))  # UI 分区显示
    notes: Mapped[str | None] = mapped_column(String(200))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    shopping_list: Mapped[ShoppingList] = relationship(back_populates="items")

    __table_args__ = (
        # 主查询路径: 加载某清单全部项(manual + auto + 已购)。FK 不自动建索引
        Index("idx_shopping_list_items_list", "shopping_list_id"),
        # auto 未购项按 (清单, 食材) 唯一 → 重算 upsert 幂等(决策2)
        # 已购 auto 移出索引管辖(is_purchased=false), 与"保留已购"重算语义对齐(决策3)
        # manual 不受此约束: 允许同食材多行
        Index(
            "idx_shopping_list_items_auto_dedup",
            "shopping_list_id", "ingredient_id",
            unique=True,
            postgresql_where=text(
                "source = 'auto' AND ingredient_id IS NOT NULL "
                "AND is_purchased = false"
            ),
        ),
        # 数据完整性: 要么关联食材, 要么有文本名(不能两者皆空)
        CheckConstraint(
            "ingredient_id IS NOT NULL OR item_name IS NOT NULL",
            name="has_identity",
        ),
    )