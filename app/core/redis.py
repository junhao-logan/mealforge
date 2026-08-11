# app/core/redis.py
"""Redis 连接层 —— 缓存用。组织方式对齐 database.py:
一个全局 client(内部自带连接池, 复用连接), 通过 get_redis 依赖注入端点。

Redis 是"可丢的加速副本": 真相永远在 Postgres, 缓存只为加速。
故所有缓存操作都应容忍 Redis 不可用(降级为直接查库), 见 cache.py。
"""
from __future__ import annotations

from collections.abc import AsyncGenerator

from redis.asyncio import Redis, from_url

from app.core.config import get_settings

settings = get_settings()

# 全局 client: 建一次全 app 复用(内部连接池)。
# decode_responses=True: 存取直接用 str, 不用手动 encode/decode bytes。
redis_client: Redis = from_url(
    settings.redis_url,
    decode_responses=True,
)


async def get_redis() -> AsyncGenerator[Redis, None]:
    """FastAPI 依赖: 端点用 redis: Redis = Depends(get_redis) 取 client。"""
    yield redis_client