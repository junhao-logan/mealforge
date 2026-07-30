# app/ai/models.py
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AiGenerationLog(Base):
    """每次 AI 生成的审计/成本/调试账本(Week 7 起)。成功失败都记一行。"""
    __tablename__ = "ai_generation_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    # 生成类型: 'recipe'(Week7) / 'meal_plan'(Week8)。一表多用, 预留扩展
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    # 'success' / 'failed' —— 失败也记(debug 幻觉/超时/非法输出)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    model: Mapped[str] = mapped_column(String(50), nullable=False)

    prompt: Mapped[str] = mapped_column(Text, nullable=False)      # 可复现
    raw_response: Mapped[str | None] = mapped_column(Text)         # 原始返回, debug 用
    # 分开存: 输入/输出单价不同, 分开才能准确算成本
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    error_message: Mapped[str | None] = mapped_column(Text)        # status=failed 时填

    # 成功时生成的菜谱 id; 删菜谱保留日志 -> SET NULL
    created_recipe_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("recipes.id", ondelete="SET NULL")
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        # 按用户查(限流/审计); 带 created_at 支持"某人最近 N 次"
        Index("idx_ai_logs_user_created", "user_id", "created_at"),
    )