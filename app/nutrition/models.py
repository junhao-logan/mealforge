from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UserNutritionGoal(Base):
    """用户的每日营养目标。一个用户一条(user_id unique)。
    系统按身体数据算出建议值存入(is_custom=False);
    用户手动覆盖后存用户的值(is_custom=True)。
    """
    __tablename__ = "user_nutrition_goals"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # FK 指向 users.id —— 注意类型是 UUID(对齐真实 users 表, 非 ERD 草图的 BIGINT)
    # 一个用户至多一条目标 → unique; 删用户带走目标 → CASCADE
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    goal_type: Mapped[str] = mapped_column(String(20), nullable=False)
    # fat_loss / muscle_gain / maintenance

    # 目标值(NOT NULL —— 一条目标必有完整四项)
    daily_calories: Mapped[Decimal] = mapped_column(Numeric(7, 1), nullable=False)
    daily_protein_g: Mapped[Decimal] = mapped_column(Numeric(6, 1), nullable=False)
    daily_carbs_g: Mapped[Decimal] = mapped_column(Numeric(6, 1), nullable=False)
    daily_fat_g: Mapped[Decimal] = mapped_column(Numeric(6, 1), nullable=False)

    is_custom: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        server_default=func.now(), onupdate=func.now(),
    )