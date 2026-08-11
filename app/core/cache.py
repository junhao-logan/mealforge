# app/core/cache.py
"""缓存助手 —— 封装"查/存/删 + 出错降级"。

设计原则(优雅降级): 缓存是可丢的加速副本, 真相在 Postgres。
Redis 任何错误都不向上抛 —— 最坏是"没缓存, 慢一点", 绝不拖垮业务。
故所有函数 try/except 兜底: get 出错当未命中, set/delete 出错静默忽略。
"""
from __future__ import annotations

import json
import logging
from typing import Any

from redis.asyncio import Redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)

DEFAULT_TTL = 3600   # 缓存默认存活 1 小时(兜底失效: 即便漏了主动删也不会太旧)


async def cache_get(redis: Redis, key: str) -> Any | None:
    """查缓存。命中返回反序列化后的值; 未命中或 Redis 出错都返回 None。

    返回 None = 调用方应去 Postgres 算(未命中和降级对调用方是同一件事)。
    """
    try:
        raw = await redis.get(key)
        return json.loads(raw) if raw is not None else None
    except RedisError as e:
        logger.warning("cache_get failed for %s: %s", key, e)
        return None   # 降级: 当作未命中


async def cache_set(redis: Redis, key: str, value: Any, ttl: int = DEFAULT_TTL) -> None:
    """存缓存(带过期时间)。出错静默忽略 —— 存不了缓存不影响主流程。"""
    try:
        await redis.set(key, json.dumps(value, default=str), ex=ttl)
    except RedisError as e:
        logger.warning("cache_set failed for %s: %s", key, e)


async def cache_delete(redis: Redis, *keys: str) -> None:
    """删缓存(失效用)。出错静默忽略。"""
    if not keys:
        return
    try:
        await redis.delete(*keys)
    except RedisError as e:
        logger.warning("cache_delete failed for %s: %s", keys, e)


# ── daily-summary 缓存的 key 与失效 ──
# 存(daily_summary 端点)和删(下面各写操作)必须用同一套 key 生成, 否则删不掉。

def summary_key(user_id, day) -> str:
    """每日营养汇总的缓存 key。day 可为 date 或 ISO 字符串。"""
    d = day.isoformat() if hasattr(day, "isoformat") else str(day)
    return f"summary:{user_id}:{d}"


async def invalidate_summary(redis: Redis, user_id, *days) -> None:
    """失效某用户某些天的营养汇总缓存(写操作后调用)。

    days: 一个或多个 date/字符串。删掉这些天的 key, 下次请求会重算。
    出错静默忽略(降级): 删不掉缓存最坏是短暂过时, 不该让写操作失败。
    """
    if not days:
        return
    keys = [summary_key(user_id, d) for d in days]
    await cache_delete(redis, *keys)